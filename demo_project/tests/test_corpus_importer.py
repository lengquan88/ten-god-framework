#!/usr/bin/env python3
"""test_corpus_importer.py — 语料库导入器全面测试

覆盖 CorpusImporter 的所有关键逻辑路径:
  - 初始化参数校验与默认值
  - import_all: 全量/增量/强制模式, 批量处理, 进度回调
  - import_by_category: 按分类导入, 单条目ndim边界
  - _exists: 存在性检查两种实现路径(有/无_ids属性)
  - get_store_stats: 存储统计的有/无_ids分支
  - 边界: 空语料库、batch_size=1、force=True覆盖行为
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from tengod.corpus.importer import CorpusImporter
from tengod.corpus.classics_corpus import ClassicsCorpus


# ============================================================================
# Mock 对象
# ============================================================================

@dataclass
class FakeVectorEntry:
    """模拟 VectorEntry"""
    id: str
    text: str
    embedding: Any
    category: str = ""
    metadata: Optional[Dict] = None


class FakeEmbedder:
    """模拟语义嵌入器: encode 返回确定性的伪向量"""

    def __init__(self, dim: int = 8):
        self.dim = dim
        self.encode_calls: List[str] = []
        self.encode_batch_calls: List[List[str]] = []

    def encode(self, text: str) -> np.ndarray:
        self.encode_calls.append(text)
        # 确定性: 基于 text hash 的向量
        rng = np.random.RandomState(hash(text) & 0xFFFFFFFF)
        vec = rng.randn(self.dim).astype(np.float32)
        # 归一化
        norm = np.linalg.norm(vec) + 1e-8
        return vec / norm

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        self.encode_batch_calls.append(texts)
        rows = [self.encode(t) for t in texts]
        return np.vstack(rows) if rows else np.zeros((0, self.dim), dtype=np.float32)


class FakeStore:
    """模拟向量存储 (带 _ids 属性的版本)"""

    def __init__(self, dim: int = 8, db_path: str = ":memory:"):
        self.dim = dim
        self.db_path = db_path
        self._ids: set = set()
        self._entries: Dict[str, FakeVectorEntry] = {}
        self._conn = None
        self.add_calls: List[List[FakeVectorEntry]] = []
        self.connect_calls = 0

    def connect(self):
        self.connect_calls += 1
        self._conn = "connected"

    def add(self, entries: List[FakeVectorEntry]):
        self.add_calls.append(entries)
        for e in entries:
            self._ids.add(e.id)
            self._entries[e.id] = e


class FakeStoreNoIds:
    """模拟向量存储 (无 _ids 属性的版本)"""

    def __init__(self, dim: int = 8):
        self.dim = dim
        self.db_path = "test.db"
        self._conn = None
        self.add_calls = 0

    def connect(self):
        self._conn = "ok"

    def add(self, entries):
        self.add_calls += len(entries)


class FakeCorpus:
    """模拟 ClassicsCorpus"""

    def __init__(self, entries: List[Dict]):
        self._entries = entries
        self._loaded = False
        self.load_all_calls = 0

    def load_all(self):
        self.load_all_calls += 1
        self._loaded = True
        return self

    def get_by_category(self, category: str) -> List[Dict]:
        return [e for e in self._entries if e.get("category") == category]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_entries():
    """示例语料条目: 3 个条目"""
    return [
        {
            "id": "doc_001",
            "text": "甲木参天，脱胎要火。春不容金，秋不容土。",
            "category": "滴天髓",
            "source": "滴天髓·通神论",
            "chapter": "甲木",
            "keywords": ["甲木", "五行"],
        },
        {
            "id": "doc_002",
            "text": "乙木虽柔，刲羊解牛。怀丁抱丙，跨凤乘猴。",
            "category": "滴天髓",
            "source": "滴天髓·通神论",
            "chapter": "乙木",
            "keywords": ["乙木", "五行"],
        },
        {
            "id": "doc_003",
            "text": "丙火猛烈，欺霜侮雪。能煅庚金，逢辛反怯。",
            "category": "穷通宝鉴",
            "source": "穷通宝鉴·三春丙火",
            "chapter": "丙火",
            "keywords": ["丙火", "调候"],
        },
    ]


@pytest.fixture
def fake_corpus(sample_entries):
    return FakeCorpus(sample_entries)


@pytest.fixture
def fake_embedder():
    return FakeEmbedder(dim=8)


@pytest.fixture
def fake_store():
    return FakeStore(dim=8)


# ============================================================================
# 初始化测试
# ============================================================================

class TestCorpusImporterInit:
    """初始化参数测试"""

    def test_default_batch_size(self, fake_corpus, fake_embedder, fake_store):
        """默认 batch_size = 8"""
        importer = CorpusImporter(fake_corpus, fake_store, fake_embedder)
        assert importer.batch_size == 8
        assert importer.progress_callback is None

    def test_custom_batch_size(self, fake_corpus, fake_embedder, fake_store):
        importer = CorpusImporter(
            fake_corpus, fake_store, fake_embedder,
            batch_size=3,
        )
        assert importer.batch_size == 3

    def test_progress_callback_preserved(self, fake_corpus, fake_embedder, fake_store):
        cb = lambda *a, **kw: None
        importer = CorpusImporter(
            fake_corpus, fake_store, fake_embedder,
            progress_callback=cb,
        )
        assert importer.progress_callback is cb

    def test_zero_batch_size_allowed(self, fake_corpus, fake_embedder, fake_store):
        """batch_size=0 不会在 __init__ 报错（实际行为：range 步长为0会在导入时出错，但此处不预先限制）"""
        imp = CorpusImporter(fake_corpus, fake_store, fake_embedder, batch_size=0)
        assert imp.batch_size == 0


# ============================================================================
# _exists 存在性检查分支
# ============================================================================

class TestExistsBranches:
    """_exists 方法的两种实现路径"""

    def test_exists_with_ids_attribute(self, fake_corpus, fake_embedder):
        store = FakeStore()
        store._ids = {"doc_001", "doc_999"}
        importer = CorpusImporter(fake_corpus, store, fake_embedder)
        assert importer._exists("doc_001") is True
        assert importer._exists("doc_999") is True
        assert importer._exists("doc_002") is False

    def test_exists_without_ids_attribute(self, fake_corpus, fake_embedder):
        """当 store 没有 _ids 属性时，始终返回 False"""
        store = FakeStoreNoIds()
        importer = CorpusImporter(fake_corpus, store, fake_embedder)
        assert importer._exists("anything") is False
        assert importer._exists("") is False


# ============================================================================
# get_store_stats 分支
# ============================================================================

class TestGetStoreStats:
    """存储统计信息"""

    def test_stats_with_ids(self, fake_corpus, fake_embedder):
        store = FakeStore(dim=16, db_path="/tmp/x.db")
        store._ids = {"a", "b", "c"}
        importer = CorpusImporter(fake_corpus, store, fake_embedder)
        stats = importer.get_store_stats()
        assert stats["total_vectors"] == 3
        assert stats["dim"] == 16
        assert stats["db_path"] == "/tmp/x.db"

    def test_stats_without_ids(self, fake_corpus, fake_embedder):
        store = FakeStoreNoIds()
        importer = CorpusImporter(fake_corpus, store, fake_embedder)
        stats = importer.get_store_stats()
        assert stats == {"total_vectors": 0}


# ============================================================================
# import_all 测试
# ============================================================================

class TestImportAll:
    """import_all 全量导入测试"""

    def test_basic_import_all(self, fake_corpus, fake_embedder, fake_store, sample_entries):
        """基本全量导入: 正确数量导入 + 正确统计"""
        importer = CorpusImporter(
            fake_corpus, fake_store, fake_embedder, batch_size=2,
        )
        stats = importer.import_all()

        assert stats["imported"] == len(sample_entries)
        assert stats["skipped"] == 0
        assert stats["total"] == len(sample_entries)
        assert "duration_ms" in stats
        assert isinstance(stats["duration_ms"], float)

        # store 中应存在所有条目
        assert len(fake_store._ids) == len(sample_entries)
        for e in sample_entries:
            assert e["id"] in fake_store._ids
            stored = fake_store._entries[e["id"]]
            assert stored.text == e["text"]
            assert stored.category == e["category"]
            # metadata 字段完整
            assert stored.metadata["source"] == e["source"]
            assert stored.metadata["chapter"] == e["chapter"]
            assert stored.metadata["keywords"] == e["keywords"]

    def test_auto_load_corpus_if_not_loaded(self, fake_embedder, fake_store, sample_entries):
        """_loaded=False 时自动调用 load_all"""
        corpus = FakeCorpus(sample_entries)
        corpus._loaded = False
        importer = CorpusImporter(corpus, fake_store, fake_embedder)
        importer.import_all()
        assert corpus.load_all_calls == 1

    def test_skip_on_second_import_without_force(
        self, fake_corpus, fake_embedder, fake_store, sample_entries,
    ):
        """第二次导入且 force=False → 全部跳过"""
        importer = CorpusImporter(fake_corpus, fake_store, fake_embedder)
        first = importer.import_all()
        assert first["imported"] == len(sample_entries)

        second = importer.import_all(force=False)
        assert second["imported"] == 0
        assert second["skipped"] == len(sample_entries)

    def test_force_overrides_existence_check(
        self, fake_corpus, fake_embedder, fake_store, sample_entries,
    ):
        """force=True 绕过存在性检查，重新全部导入"""
        importer = CorpusImporter(fake_corpus, fake_store, fake_embedder)
        first = importer.import_all()
        assert first["imported"] == len(sample_entries)

        second = importer.import_all(force=True)
        # force=True 会重新 add，所以 imported 等于总数
        assert second["imported"] == len(sample_entries)
        assert second["skipped"] == 0

    def test_progress_callback_invoked(
        self, fake_corpus, fake_embedder, fake_store, sample_entries,
    ):
        """进度回调会被每个条目调用一次"""
        progress_log = []

        def cb(current, total, entry):
            progress_log.append((current, total, entry["id"]))

        importer = CorpusImporter(
            fake_corpus, fake_store, fake_embedder,
            batch_size=2, progress_callback=cb,
        )
        importer.import_all()

        assert len(progress_log) == len(sample_entries)
        # 顺序: 1..total
        for i in range(len(sample_entries)):
            cur, tot, _ = progress_log[i]
            assert cur == i + 1
            assert tot == len(sample_entries)

    def test_progress_callback_on_skipped_entries(
        self, fake_corpus, fake_embedder, fake_store, sample_entries,
    ):
        """跳过的条目同样触发进度回调"""
        # 先导入一次
        importer = CorpusImporter(fake_corpus, fake_store, fake_embedder)
        importer.import_all()

        # 第二次导入并追踪
        log = []
        importer.progress_callback = lambda c, t, e: log.append(c)
        importer.import_all(force=False)

        # 即使全部跳过，进度仍应推进
        assert len(log) == len(sample_entries)

    def test_encode_batch_is_used_when_available(
        self, fake_corpus, fake_embedder, fake_store,
    ):
        """当 embedder 有 encode_batch 时，优先使用（而非逐条 encode）"""
        importer = CorpusImporter(
            fake_corpus, fake_store, fake_embedder, batch_size=2,
        )
        importer.import_all()
        # 应该调用 encode_batch，而不是逐次 encode
        assert len(fake_embedder.encode_batch_calls) > 0
        # 3 个条目 batch_size=2 → 2 批 (2+1)
        assert len(fake_embedder.encode_batch_calls) == 2
        assert [len(b) for b in fake_embedder.encode_batch_calls] == [2, 1]

    def test_fallback_to_encode_when_no_batch_method(
        self, fake_corpus, fake_store, sample_entries,
    ):
        """当 embedder 没有 encode_batch 时，回退到逐条 encode"""
        class DummyEmbedder:
            def __init__(self, dim=8):
                self.dim = dim
                self.calls = []

            def encode(self, text):
                self.calls.append(text)
                rng = np.random.RandomState(hash(text) & 0xFFFFFFFF)
                return rng.randn(self.dim).astype(np.float32)

        emb = DummyEmbedder(dim=8)
        importer = CorpusImporter(fake_corpus, fake_store, emb, batch_size=2)
        importer.import_all()

        # 每个文本都调用过 encode
        assert len(emb.calls) == len(sample_entries)

    def test_empty_corpus_import_all(self, fake_embedder, fake_store):
        """空语料库 → imported=0, skipped=0, total=0"""
        corpus = FakeCorpus([])
        corpus._loaded = True
        importer = CorpusImporter(corpus, fake_store, fake_embedder)
        stats = importer.import_all()
        assert stats["imported"] == 0
        assert stats["skipped"] == 0
        assert stats["total"] == 0
        assert len(fake_store._ids) == 0

    def test_store_connect_not_called_if_already_connected(
        self, fake_corpus, fake_embedder, fake_store,
    ):
        """如果 store 已经 _conn，不重复调用 connect"""
        fake_store.connect()  # 预先连接
        importer = CorpusImporter(fake_corpus, fake_store, fake_embedder)
        fake_store.connect_calls = 1  # reset
        importer.import_all()
        # 不应该再次调用 connect
        assert fake_store.connect_calls == 1


# ============================================================================
# import_by_category 测试
# ============================================================================

class TestImportByCategory:
    """按分类导入"""

    def test_category_filter(self, fake_corpus, fake_embedder, fake_store, sample_entries):
        """仅导入指定分类"""
        importer = CorpusImporter(fake_corpus, fake_store, fake_embedder)
        stats = importer.import_by_category("滴天髓")

        target = [e for e in sample_entries if e["category"] == "滴天髓"]
        assert stats["imported"] == len(target)
        assert stats["skipped"] == 0
        assert stats["total"] == len(target)
        assert stats["category"] == "滴天髓"
        # 仅该分类条目在存储中
        assert len(fake_store._ids) == len(target)

    def test_category_not_found(self, fake_corpus, fake_embedder, fake_store):
        """分类不存在 → 结果为0"""
        importer = CorpusImporter(fake_corpus, fake_store, fake_embedder)
        stats = importer.import_by_category("不存在的分类")
        assert stats["imported"] == 0
        assert stats["total"] == 0
        assert stats["skipped"] == 0

    def test_single_entry_ndim_1_reshape(
        self, fake_corpus, fake_embedder, fake_store,
    ):
        """单条目时 embedder 返回 ndim=1，需要 reshape 为 (1, D)"""
        # 构造仅1条分类
        corpus = FakeCorpus([
            {"id": "x1", "text": "测试文本", "category": "C"},
        ])
        corpus._loaded = True

        # encode 返回一维向量
        class SingletonEmbedder:
            def encode(self, t):
                return np.array([1.0, 2.0, 3.0, 4.0])  # ndim=1 shape=(4,)

        imp = CorpusImporter(corpus, fake_store, SingletonEmbedder())
        stats = imp.import_by_category("C")
        assert stats["imported"] == 1

    def test_skip_existing(
        self, fake_corpus, fake_embedder, fake_store, sample_entries,
    ):
        """同分类第二次导入会跳过已存在"""
        importer = CorpusImporter(fake_corpus, fake_store, fake_embedder)
        importer.import_by_category("滴天髓")
        stats = importer.import_by_category("滴天髓")
        assert stats["imported"] == 0
        target = [e for e in sample_entries if e["category"] == "滴天髓"]
        assert stats["skipped"] == len(target)


# ============================================================================
# 边界 / 异常防护
# ============================================================================

class TestImporterEdgeCases:
    """边界条件与防护"""

    def test_embedding_dtype_is_float32(
        self, fake_corpus, fake_embedder, fake_store,
    ):
        """写入 store 的 embedding 必须是 float32（避免精度不一致导致索引失败）"""
        emb = FakeEmbedder(dim=8)
        # 构造一个 encode 返回 float64 的场景
        emb.encode = lambda t: np.random.randn(8).astype(np.float64)
        importer = CorpusImporter(fake_corpus, fake_store, emb)
        importer.import_all()

        for entry in fake_store._entries.values():
            assert entry.embedding.dtype == np.float32, \
                f"embedding dtype 应为 float32，实际 {entry.embedding.dtype}"

    def test_add_not_called_for_empty_entries(
        self, fake_embedder, fake_store,
    ):
        """当没有可导入条目时，不调用 store.add"""
        corpus = FakeCorpus([])
        corpus._loaded = True
        importer = CorpusImporter(corpus, fake_store, fake_embedder)
        importer.import_all()
        assert len(fake_store.add_calls) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
