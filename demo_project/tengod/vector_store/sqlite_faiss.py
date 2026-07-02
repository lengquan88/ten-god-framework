"""
sqlite_faiss.py — 向量存储 v3.7.0
===============================================
道曰："积土成山，风雨兴焉；积水成渊，蛟龙生焉。"

SQLite + FAISS 向量存储，支持：
  - 语义检索（六维门禁化）
  - 增量添加
  - 按分类过滤
  - 门禁系数调整
  - 持久化

依赖：
  - sqlite3 (Python 标准库，无需额外安装)
  - faiss-cpu (可选，pip install faiss-cpu)
  - 如果 FAISS 不可用，降级为 brute-force 搜索
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


_HAS_FAISS = False
_faiss = None

try:
    import faiss
    _faiss = faiss
    _HAS_FAISS = True
except ImportError:
    pass


class VectorEntry:
    """单个向量条目"""

    def __init__(
        self,
        id: str,
        text: str,
        embedding: np.ndarray,
        category: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.text = text
        self.embedding = embedding.astype(np.float32)
        self.category = category
        self.metadata = metadata or {}


class SQLiteFAISSVectorStore:
    """SQLite + FAISS 向量存储

    架构：
      - SQLite：存储元数据、文本、分类
      - FAISS：向量索引（IVF 加速搜索）
      - 降级：无 FAISS 时 brute-force
    """

    def __init__(
        self,
        db_path: str,
        dim: int = 384,
        faiss_index_type: str = "flat",  # "flat" | "ivf"
    ):
        """初始化向量存储

        Args:
            db_path: SQLite 数据库文件路径
            dim: 向量维度
            faiss_index_type: FAISS 索引类型
        """
        self.db_path = db_path
        self.dim = dim
        self.faiss_index_type = faiss_index_type
        self._conn: Optional[sqlite3.Connection] = None
        self._index: Any = None
        self._ids: List[str] = []
        self._embeddings: List[np.ndarray] = []

    def connect(self) -> "SQLiteFAISSVectorStore":
        """连接数据库并加载索引"""
        # SQLite 连接
        self._conn = sqlite3.connect(self.db_path)
        cursor = self._conn.cursor()

        # 创建表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                category TEXT,
                embedding BLOB NOT NULL,
                metadata TEXT
            )
        """)
        self._conn.commit()

        # 加载所有向量
        cursor.execute("SELECT id, embedding FROM vectors ORDER BY id")
        self._ids = []
        self._embeddings = []
        for row in cursor.fetchall():
            id_, blob = row
            embedding = np.frombuffer(blob, dtype=np.float32)
            self._ids.append(id_)
            self._embeddings.append(embedding)

        # 构建 FAISS 索引
        if self._embeddings:
            self._build_index()

        return self

    def _build_index(self) -> None:
        """构建 FAISS 索引"""
        if not _HAS_FAISS or not self._embeddings:
            return

        embeddings_np = np.stack(self._embeddings, axis=0)
        n, d = embeddings_np.shape

        if self.faiss_index_type == "ivf" and n > 1000:
            nlist = min(int(np.sqrt(n)), 200)
            quantizer = _faiss.IndexFlatL2(d)
            index = _faiss.IndexIVFFlat(quantizer, d, nlist)
            index.train(embeddings_np)
            index.add(embeddings_np)
        else:
            index = _faiss.IndexFlatL2(d)
            index.add(embeddings_np)

        self._index = index

    def add(
        self,
        entries: List[VectorEntry],
    ) -> None:
        """批量添加向量条目"""
        assert self._conn is not None

        cursor = self._conn.cursor()
        for entry in entries:
            # SQLite 存储 blob
            metadata_json = json.dumps(entry.metadata)
            cursor.execute(
                """
                REPLACE INTO vectors (id, text, category, embedding, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (entry.id, entry.text, entry.category, entry.embedding.tobytes(), metadata_json),
            )
            # 更新内存索引
            if entry.id in self._ids:
                idx = self._ids.index(entry.id)
                self._embeddings[idx] = entry.embedding
            else:
                self._ids.append(entry.id)
                self._embeddings.append(entry.embedding)

        self._conn.commit()

        # 重建 FAISS 索引
        if _HAS_FAISS:
            self._build_index()

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """语义相似性搜索

        Args:
            query_embedding: 查询向量 (dim,)
            top_k: 返回数量
            category: 可选分类过滤

        Returns:
            结果列表，含 id, text, category, distance, metadata
        """
        if _HAS_FAISS and self._index is not None:
            return self._search_faiss(query_embedding, top_k, category)
        else:
            return self._search_bruteforce(query_embedding, top_k, category)

    def _search_faiss(
        self,
        query_embedding: np.ndarray,
        top_k: int,
        category: Optional[str],
    ) -> List[Dict[str, Any]]:
        """FAISS 加速搜索"""
        q = query_embedding.reshape(1, self.dim).astype(np.float32)
        distances, indices = self._index.search(q, top_k)
        results = []

        cursor = self._conn.cursor()
        for d, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._ids):
                continue
            id_ = self._ids[idx]
            cursor.execute(
                "SELECT text, category, metadata FROM vectors WHERE id = ?", (id_,)
            )
            row = cursor.fetchone()
            if row is None:
                continue
            text, cat, meta_json = row
            if category is not None and cat != category:
                continue
            metadata = json.loads(meta_json) if meta_json else {}
            results.append({
                "id": id_,
                "text": text,
                "category": cat,
                "distance": float(d),
                "metadata": metadata,
            })

        return results

    def _search_bruteforce(
        self,
        query_embedding: np.ndarray,
        top_k: int,
        category: Optional[str],
    ) -> List[Dict[str, Any]]:
        """暴力搜索（FAISS 降级）"""
        q = query_embedding.astype(np.float32)
        q_norm = np.linalg.norm(q)
        candidates: List[Tuple[float, str, str, str, Dict]] = []

        cursor = self._conn.cursor()
        cursor.execute("SELECT id, text, category, embedding, metadata FROM vectors")
        for id_, text, cat, blob, meta_json in cursor.fetchall():
            if category is not None and cat != category:
                continue
            emb = np.frombuffer(blob, dtype=np.float32)
            # L2 距离
            diff = q - emb
            dist = float(np.sqrt((diff ** 2).sum()))
            metadata = json.loads(meta_json) if meta_json else {}
            candidates.append((dist, id_, text, cat, metadata))

        candidates.sort(key=lambda x: x[0])
        return [
            {
                "id": id_,
                "text": text,
                "category": cat,
                "distance": dist,
                "metadata": metadata,
            }
            for dist, id_, text, cat, metadata in candidates[:top_k]
        ]

    def search_with_gates(
        self,
        query_embedding: np.ndarray,
        projector: Any,
        threshold: float = 0.3,
        top_k: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """门禁化搜索：六维投影 + 测地线距离

        与 projector.gate_mods 结合，可由九宫格动态调整搜索权重。

        Args:
            query_embedding: 原始查询 embedding
            projector: TBCESixDimProjector 实例
            threshold: 测地线距离阈值
            top_k: 返回数量
            category: 分类过滤

        Returns:
            门禁化搜索结果
        """
        from ...gate_torch import geodesic_distance

        # 六维投影查询
        q_6d = projector.forward(query_embedding).reshape(-1)

        # 投影所有候选
        results = []
        cursor = self._conn.cursor()
        cond = "WHERE category = ?" if category else ""
        params = (category,) if category else ()

        cursor.execute(f"SELECT id, text, category, embedding, metadata FROM vectors {cond}", params)
        for id_, text, cat, blob, meta_json in cursor.fetchall():
            emb = np.frombuffer(blob, dtype=np.float32)
            c_6d = projector.forward(emb).reshape(-1)
            dist = geodesic_distance(q_6d, c_6d)
            if dist < threshold:
                metadata = json.loads(meta_json) if meta_json else {}
                results.append((dist, {
                    "id": id_,
                    "text": text,
                    "category": cat,
                    "distance": dist,
                    "metadata": metadata,
                }))

        results.sort(key=lambda x: x[0])
        return [r for _, r in results[:top_k]]

    def delete(self, entry_id: str) -> bool:
        """删除条目"""
        assert self._conn is not None
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM vectors WHERE id = ?", (entry_id,))
        self._conn.commit()
        if entry_id in self._ids:
            idx = self._ids.index(entry_id)
            del self._ids[idx]
            del self._embeddings[idx]
            if _HAS_FAISS:
                self._build_index()
        return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计"""
        assert self._conn is not None
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vectors")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT DISTINCT category FROM vectors")
        categories = [row[0] for row in cursor.fetchall() if row[0]]
        return {
            "total_entries": total,
            "categories": categories,
            "dim": self.dim,
            "faiss_available": _HAS_FAISS,
            "faiss_index_type": self.faiss_index_type if _HAS_FAISS else None,
        }

    def close(self) -> None:
        """关闭连接"""
        if self._conn:
            self._conn.close()
            self._conn = None


# ============================================================================
# 自检
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SQLite + FAISS 向量存储 v3.7.0")
    print("=" * 60)

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    store = SQLiteFAISSVectorStore(db_path, dim=384)
    store.connect()
    print(f"\n  FAISS 可用: {_HAS_FAISS}")

    # 添加测试条目
    entries = [
        VectorEntry(
            id="test_001",
            text="八字排盘：年柱月柱日柱时柱，天干地支六十甲子。",
            embedding=np.random.randn(384).astype(np.float32),
            category="八字命理",
        ),
        VectorEntry(
            id="test_002",
            text="紫微斗数十二宫：命宫兄弟宫夫妻宫子女宫财帛宫疾厄宫迁移宫交友宫官禄宫田宅宫福德宫父母宫。",
            embedding=np.random.randn(384).astype(np.float32),
            category="紫微斗数",
        ),
    ]
    store.add(entries)
    stats = store.get_stats()
    print(f"\n  添加后: {stats['total_entries']} entries")
    print(f"    categories: {stats['categories']}")

    # 搜索测试
    query = np.random.randn(384).astype(np.float32)
    results = store.search(query, top_k=2)
    print(f"\n  搜索测试: 找到 {len(results)} 结果")
    for r in results:
        print(f"    {r['id']}: distance={r['distance']:.3f}  [{r['category']}] {r['text'][:40]}...")

    store.close()
    os.unlink(db_path)

    print("\n" + "=" * 60)
    print("  自检完成")
    print("=" * 60)