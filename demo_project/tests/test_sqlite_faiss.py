"""
test_sqlite_faiss.py — SQLiteFAISSVectorStore 回归测试

覆盖 VectorEntry、SQLiteFAISSVectorStore 的核心数据路径：
  1. connect / add / search / delete / close 全流程
  2. brute-force 降级（FAISS 不可用）
  3. 按分类过滤、元数据透传、边界 top_k
  4. 空集合搜索、空分类过滤、删除不存在条目
  5. REPLACE 语义覆盖（重复 id）
  6. get_stats 一致性
  7. 持久化：关闭后重连仍可检索
"""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest

from tengod.vector_store.sqlite_faiss import (
    SQLiteFAISSVectorStore,
    VectorEntry,
    _HAS_FAISS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def store(db_path):
    s = SQLiteFAISSVectorStore(db_path, dim=8)
    s.connect()
    yield s
    try:
        s.close()
    except Exception:
        pass


def _vec(values):
    return np.array(values, dtype=np.float32)


def _build_entries(n, dim=8, category="cat"):
    entries = []
    for i in range(n):
        entries.append(
            VectorEntry(
                id=f"id_{i}",
                text=f"text {i}",
                embedding=np.random.default_rng(42 + i).standard_normal(dim).astype(np.float32),
                category=f"{category}_{i % 3}",
                metadata={"idx": i, "tag": f"t{i}"},
            )
        )
    return entries


# ---------------------------------------------------------------------------
# VectorEntry
# ---------------------------------------------------------------------------

class TestVectorEntry:
    def test_defaults(self):
        v = VectorEntry("a", "hello", _vec([1, 0, 0, 0, 0, 0, 0, 0]))
        assert v.id == "a"
        assert v.text == "hello"
        assert v.category == ""
        assert v.metadata == {}
        assert v.embedding.dtype == np.float32
        assert v.embedding.shape == (8,)

    def test_custom_fields(self):
        v = VectorEntry(
            "b", "world", _vec([0] * 8),
            category="news", metadata={"k": "v"},
        )
        assert v.category == "news"
        assert v.metadata == {"k": "v"}

    def test_embedding_casts_to_float32(self):
        v = VectorEntry("c", "t", np.array([1, 2, 3, 4, 5, 6, 7, 8], dtype=np.float64))
        assert v.embedding.dtype == np.float32


# ---------------------------------------------------------------------------
# SQLiteFAISSVectorStore: connect / add / search / delete / close
# ---------------------------------------------------------------------------

class TestSQLiteFAISSVectorStore:
    def test_connect_creates_table(self, db_path):
        s = SQLiteFAISSVectorStore(db_path, dim=4)
        s.connect()
        assert s._conn is not None
        stats = s.get_stats()
        assert stats["total_entries"] == 0
        assert stats["dim"] == 4
        assert stats["faiss_available"] == _HAS_FAISS
        s.close()

    def test_add_and_search_smoke(self, store):
        entries = _build_entries(5)
        store.add(entries)
        assert store.get_stats()["total_entries"] == 5

        # 用第一个向量作为查询，应最相似
        q = entries[0].embedding
        results = store.search(q, top_k=2)
        assert len(results) == 2
        assert results[0]["id"] == entries[0].id
        assert results[0]["distance"] == pytest.approx(0.0, abs=1e-4)
        # 元数据完整透传
        assert results[0]["metadata"] == {"idx": 0, "tag": "t0"}

    def test_duplicate_id_replaces(self, store):
        a = VectorEntry("dup", "v1", _vec([1] * 8), category="c1")
        b = VectorEntry("dup", "v2", _vec([0] * 8), category="c2")
        store.add([a])
        store.add([b])
        assert store.get_stats()["total_entries"] == 1

        results = store.search(_vec([0] * 8), top_k=1)
        assert results[0]["id"] == "dup"
        assert results[0]["text"] == "v2"
        assert results[0]["category"] == "c2"

    def test_delete_removes_entry(self, store):
        store.add(_build_entries(3))
        assert store.get_stats()["total_entries"] == 3

        deleted = store.delete("id_1")
        assert deleted is True
        assert store.get_stats()["total_entries"] == 2

        results = store.search(_vec([0] * 8), top_k=10)
        ids = [r["id"] for r in results]
        assert "id_1" not in ids

    def test_delete_nonexistent_returns_false(self, store):
        assert store.delete("nope") is False

    def test_search_top_k_clamped_to_results(self, store):
        store.add(_build_entries(2))
        results = store.search(_vec([1] * 8), top_k=100)
        assert len(results) == 2

    def test_search_empty_store(self, store):
        results = store.search(_vec([1] * 8), top_k=5)
        assert results == []

    def test_category_filter(self, store):
        store.add(_build_entries(6))
        results = store.search(_vec([1] * 8), top_k=10, category="cat_1")
        assert all(r["category"] == "cat_1" for r in results)
        # 其他分类应当没有
        results_other = store.search(_vec([1] * 8), top_k=10, category="cat_none")
        assert results_other == []

    def test_close_is_idempotent(self, store):
        store.close()
        store.close()
        assert store._conn is None

    def test_persistence_across_reconnect(self, db_path):
        s1 = SQLiteFAISSVectorStore(db_path, dim=8)
        s1.connect()
        s1.add(_build_entries(4))
        s1.close()

        s2 = SQLiteFAISSVectorStore(db_path, dim=8)
        s2.connect()
        assert s2.get_stats()["total_entries"] == 4
        q = np.array(
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8], dtype=np.float32
        )
        results = s2.search(q, top_k=2)
        assert len(results) == 2
        s2.close()

    def test_get_stats_reports_categories(self, store):
        store.add(_build_entries(9))
        stats = store.get_stats()
        assert stats["total_entries"] == 9
        assert sorted(stats["categories"]) == ["cat_0", "cat_1", "cat_2"]
        assert stats["dim"] == 8
        assert stats["faiss_index_type"] == ("flat" if _HAS_FAISS else None)

    def test_vector_entry_preserves_l2_ordering(self, store):
        """暴力/FAISS 搜索都应按 L2 距离升序返回。"""
        # 构造正交基，距离可预测
        entries = [
            VectorEntry("e1", "a", _vec([0, 0, 0, 0, 0, 0, 0, 0]), "c"),
            VectorEntry("e2", "b", _vec([1, 0, 0, 0, 0, 0, 0, 0]), "c"),
            VectorEntry("e3", "c", _vec([2, 0, 0, 0, 0, 0, 0, 0]), "c"),
        ]
        store.add(entries)

        q = _vec([0.5, 0, 0, 0, 0, 0, 0, 0])
        results = store.search(q, top_k=3)
        ids = [r["id"] for r in results]
        # 距离升序
        distances = [r["distance"] for r in results]
        assert distances == sorted(distances)
        # e1 距离 0.5，应最接近
        assert ids[0] == "e1"


# ---------------------------------------------------------------------------
# FAISS 特定路径
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _HAS_FAISS, reason="faiss-cpu 未安装")
class TestSQLiteFAISSWithFaiss:
    def test_faiss_index_rebuilt_on_add(self, store):
        entries = _build_entries(10)
        store.add(entries)
        assert store._index is not None
        # 追加条目 -> 索引应重建
        store.add(_build_entries(2, category="extra"))
        assert store._index is not None
        assert store.get_stats()["total_entries"] == 12

    def test_ivf_index_used_for_large_dataset(self, db_path):
        s = SQLiteFAISSVectorStore(db_path, dim=8, faiss_index_type="ivf")
        s.connect()
        # IVF 仅在 n > 1000 时使用
        entries = _build_entries(1001)
        s.add(entries)
        assert s._index is not None
        assert s.get_stats()["total_entries"] == 1001
        s.close()

    def test_faiss_search_returns_results(self, store):
        entries = _build_entries(8)
        store.add(entries)
        q = entries[3].embedding
        results = store.search(q, top_k=3)
        assert results[0]["id"] == entries[3].id
        assert results[0]["distance"] == pytest.approx(0.0, abs=1e-4)

    def test_faiss_category_filter(self, store):
        entries = _build_entries(12)
        store.add(entries)
        results = store.search(_vec([0] * 8), top_k=5, category="cat_0")
        assert all(r["category"] == "cat_0" for r in results)


# ---------------------------------------------------------------------------
# 边界 / 回归用例
# ---------------------------------------------------------------------------

class TestSQLiteFAISSRegression:
    def test_empty_metadata_roundtrip(self, store):
        """空元数据不应抛异常。"""
        v = VectorEntry("m", "text", _vec([1] * 8), metadata={})
        store.add([v])
        results = store.search(_vec([1] * 8), top_k=1)
        assert results[0]["metadata"] == {}

    def test_non_float32_embedding_coerced(self, store):
        """float64 / int 数组应被安全转换。"""
        v = VectorEntry(
            "wide", "text",
            np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float64),
        )
        store.add([v])
        results = store.search(
            np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float32),
            top_k=1,
        )
        assert results[0]["id"] == "wide"

    def test_large_batch_add(self, store):
        """一次添加 1000 条（无 FAISS 时）应不崩溃。"""
        entries = _build_entries(1000)
        store.add(entries)
        assert store.get_stats()["total_entries"] == 1000

    def test_delete_all_and_research(self, store):
        store.add(_build_entries(5))
        for i in range(5):
            assert store.delete(f"id_{i}") is True
        assert store.get_stats()["total_entries"] == 0
        results = store.search(_vec([1] * 8), top_k=5)
        assert results == []

    def test_get_stats_after_add_delete(self, store):
        store.add(_build_entries(3))
        store.delete("id_0")
        stats = store.get_stats()
        assert stats["total_entries"] == 2
        # 分类去重，只应剩 cat_1 / cat_2
        assert sorted(stats["categories"]) == ["cat_1", "cat_2"]
