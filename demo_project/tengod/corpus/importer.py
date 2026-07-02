"""
corpus/importer.py — 语料库→向量存储灌入管道 v4.2.0
=======================================================
道曰："天下大事，必作于细。"

将命理经典语料库灌入 SQLite+FAISS 向量存储，支持：
  - 全量导入：加载全部语料 → embed → 写入向量存储
  - 增量导入：仅导入向量存储中不存在的条目
  - 批量处理：分批 embed 避免 OOM
  - 进度回调：支持进度报告

用法：
    from tengod.corpus import ClassicsCorpus, CorpusImporter
    from tengod.vector_store import SQLiteFAISSVectorStore
    from tengod.local_embedding import create_embedder

    corpus = ClassicsCorpus().load_all()
    store = SQLiteFAISSVectorStore("/data/vectors.db", dim=384)
    embedder = create_embedder("sentence_transformer")

    importer = CorpusImporter(corpus, store, embedder)
    stats = importer.import_all()
    # → {"imported": 25, "skipped": 0, "total": 25}
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from .classics_corpus import ClassicsCorpus


class CorpusImporter:
    """语料库 → 向量存储灌入器

    Attributes:
        corpus: 经典语料库实例
        store: SQLiteFAISSVectorStore 实例
        embedder: 语义嵌入器 (encode 方法)
        batch_size: 批量处理大小
        progress_callback: 进度回调 (current, total, entry)
    """

    def __init__(
        self,
        corpus: ClassicsCorpus,
        store: Any,  # SQLiteFAISSVectorStore
        embedder: Any,  # LocalEmbedder
        batch_size: int = 8,
        progress_callback: Optional[Callable[[int, int, Dict], None]] = None,
    ):
        self.corpus = corpus
        self.store = store
        self.embedder = embedder
        self.batch_size = batch_size
        self.progress_callback = progress_callback

    def import_all(self, force: bool = False) -> Dict[str, Any]:
        """全量导入：将语料库全部灌入向量存储

        Args:
            force: 是否强制重新导入已存在的条目

        Returns:
            {"imported": N, "skipped": N, "total": N, "duration_ms": ...}
        """
        if not self.corpus._loaded:
            self.corpus.load_all()

        from ..vector_store.sqlite_faiss import VectorEntry, SQLiteFAISSVectorStore

        entries = self.corpus._entries
        total = len(entries)
        imported = 0
        skipped = 0
        t0 = time.time()

        texts = [e["text"] for e in entries]
        ids = [e["id"] for e in entries]

        # 分批 embed
        all_embeddings = []
        for i in range(0, total, self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            if hasattr(self.embedder, 'encode_batch'):
                batch_embeddings = self.embedder.encode_batch(batch_texts)
            else:
                batch_embeddings = np.stack([self.embedder.encode(t) for t in batch_texts])
            all_embeddings.append(batch_embeddings)

        embeddings = np.vstack(all_embeddings) if all_embeddings else np.array([])

        # 构建 VectorEntry 并写入
        vector_entries = []
        for i, entry in enumerate(entries):
            eid = ids[i]
            # 检查是否已存在
            if not force and self._exists(eid):
                skipped += 1
                if self.progress_callback:
                    self.progress_callback(i + 1, total, entry)
                continue

            ve = VectorEntry(
                id=eid,
                text=entry["text"],
                embedding=embeddings[i].astype(np.float32),
                category=entry.get("category", ""),
                metadata={
                    "source": entry.get("source", ""),
                    "chapter": entry.get("chapter", ""),
                    "keywords": entry.get("keywords", []),
                },
            )
            vector_entries.append(ve)
            imported += 1

            if self.progress_callback:
                self.progress_callback(i + 1, total, entry)

        if vector_entries:
            if hasattr(self.store, 'connect'):
                if self.store._conn is None:
                    self.store.connect()
            self.store.add(vector_entries)

        t1 = time.time()

        return {
            "imported": imported,
            "skipped": skipped,
            "total": total,
            "duration_ms": round((t1 - t0) * 1000, 1),
        }

    def import_by_category(self, category: str, force: bool = False) -> Dict[str, Any]:
        """按分类导入"""
        entries = self.corpus.get_by_category(category)
        total = len(entries)

        from ..vector_store.sqlite_faiss import VectorEntry

        texts = [e["text"] for e in entries]
        if hasattr(self.embedder, 'encode_batch'):
            embeddings = self.embedder.encode_batch(texts)
        else:
            embeddings = np.stack([self.embedder.encode(t) for t in texts])
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        imported = 0
        skipped = 0

        vector_entries = []
        for i, entry in enumerate(entries):
            eid = entry["id"]
            if not force and self._exists(eid):
                skipped += 1
                continue

            ve = VectorEntry(
                id=eid,
                text=entry["text"],
                embedding=embeddings[i].astype(np.float32),
                category=category,
                metadata={
                    "source": entry.get("source", ""),
                    "chapter": entry.get("chapter", ""),
                    "keywords": entry.get("keywords", []),
                },
            )
            vector_entries.append(ve)
            imported += 1

        if vector_entries:
            if hasattr(self.store, 'connect') and self.store._conn is None:
                self.store.connect()
            self.store.add(vector_entries)

        return {
            "imported": imported,
            "skipped": skipped,
            "total": total,
            "category": category,
        }

    def _exists(self, entry_id: str) -> bool:
        """检查条目是否已在向量存储中"""
        if hasattr(self.store, '_ids'):
            return entry_id in self.store._ids
        return False

    def get_store_stats(self) -> Dict[str, Any]:
        """获取向量存储统计"""
        if hasattr(self.store, '_ids'):
            return {
                "total_vectors": len(self.store._ids),
                "dim": self.store.dim,
                "db_path": self.store.db_path,
            }
        return {"total_vectors": 0}


# ============================================================================
# 自检
# ============================================================================

if __name__ == "__main__":
    import os
    import sys
    import tempfile

    _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    _TENGOD_DIR = os.path.dirname(_THIS_DIR)
    if _TENGOD_DIR not in sys.path:
        sys.path.insert(0, _TENGOD_DIR)

    from .classics_corpus import ClassicsCorpus
    from ..vector_store.sqlite_faiss import SQLiteFAISSVectorStore
    from ..local_embedding import create_embedder

    print("=" * 60)
    print("  CorpusImporter v4.2.0 自检")
    print("=" * 60)

    # 加载语料库
    corpus = ClassicsCorpus()
    corpus.load_all()
    print(f"\n  语料库条目: {len(corpus._entries)}")

    # 创建 embedder
    embedder = create_embedder("tfidf_svd", dim=384)
    print(f"  Embedder: {embedder.mode}")

    # 创建临时向量存储
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        store = SQLiteFAISSVectorStore(db_path, dim=384)
        store.connect()
        print(f"  向量存储: {db_path}")

        # 导入
        importer = CorpusImporter(corpus, store, embedder)
        stats = importer.import_all()
        print(f"\n  导入结果: {stats}")

        # 验证
        store_stats = importer.get_store_stats()
        print(f"  存储统计: {store_stats}")
        assert store_stats["total_vectors"] == stats["imported"], "向量数不匹配"
        print("\n✅ CorpusImporter 自检通过")
    finally:
        os.unlink(db_path)