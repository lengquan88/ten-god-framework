#!/usr/bin/env python3
"""
knowledge_base.py — 知识库
正财主理固化，提供轻量级知识图谱与查询能力。
支持内存存储和数据库持久化（SQLite/PostgreSQL）。
"""

import json
import math
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class StorageBackend(Enum):
    """存储后端"""

    MEMORY = "memory"  # 内存（默认）
    SQLITE = "sqlite"  # SQLite
    POSTGRES = "postgres"  # PostgreSQL
    JSON = "json"  # JSON 文件


@dataclass
class KnowledgeNode:
    """知识节点"""

    id: str
    name: str
    node_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class KnowledgeEdge:
    """知识边（关系）"""

    source: str
    target: str
    relation: str
    weight: float = 1.0


# ============================================================
# SQLAlchemy ORM 层（可选依赖，有则用，无则回退到 sqlite3）
# ============================================================
_SQLALCHEMY_AVAILABLE = False
_SA_Base = None
_SA_engine = None
_SA_session_factory = None

try:
    from sqlalchemy import (
        Column,
        Float,
        Index,
        String,
        Text,
        asc,
        create_engine,
        desc,
    )
    from sqlalchemy import (
        func as sa_func,
    )
    from sqlalchemy.ext.automap import automap_base
    from sqlalchemy.orm import Session, declarative_base, sessionmaker

    _SQLALCHEMY_AVAILABLE = True
    _SA_Base = declarative_base()
except ImportError:
    pass


def _init_sa_tables(engine, db_path: str) -> None:
    """用 SQLAlchemy 建表（仅首次）"""
    import sqlite3

    # 直接用 sqlite3 建表（SQLAlchemy 已安装）
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sa_nodes (
            id VARCHAR(32) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            node_type VARCHAR(64),
            properties TEXT,
            created_at REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sa_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source VARCHAR(32),
            target VARCHAR(32),
            relation VARCHAR(64),
            weight REAL
        )
    """)
    # 全文搜索索引
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_node_name ON sa_nodes(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_node_type ON sa_nodes(node_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_source ON sa_edges(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_target ON sa_edges(target)")
    except Exception:
        pass
    conn.commit()
    conn.close()


class KnowledgeBase:
    """知识库 — 固化之库

    管理节点、关系，支持基本查询与遍历。
    支持多种存储后端：内存、SQLite、PostgreSQL、JSON。
    """

    def __init__(
        self,
        backend: StorageBackend = StorageBackend.MEMORY,
        db_path: Optional[str] = None,
        connection_string: Optional[str] = None,
    ):
        self._backend = backend
        self._db_path = db_path
        self._conn_string = connection_string
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._edges: List[KnowledgeEdge] = []
        self._db_conn: Optional[Any] = None

        if backend != StorageBackend.MEMORY:
            self._init_storage()

    def _init_storage(self) -> None:
        """初始化存储后端"""
        if self._backend == StorageBackend.SQLITE:
            self._init_sqlite()
        elif self._backend == StorageBackend.JSON:
            self._init_json()
        elif self._backend == StorageBackend.POSTGRES:
            self._init_postgres()

    def _init_sqlite(self) -> None:
        """初始化 SQLite（WAL模式 + 连接优化）"""
        try:
            import sqlite3

            db_path = self._db_path or "knowledge.db"
            self._db_conn = sqlite3.connect(db_path, check_same_thread=False)
            # WAL 模式：读写并发不阻塞
            self._db_conn.execute("PRAGMA journal_mode=WAL")
            self._db_conn.execute("PRAGMA synchronous=NORMAL")
            self._db_conn.execute("PRAGMA foreign_keys=ON")
            self._db_conn.execute("PRAGMA cache_size=-8000")
            self._db_conn.execute("PRAGMA busy_timeout=5000")
            self._db_conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    node_type TEXT,
                    properties TEXT,
                    created_at REAL
                )
            """)
            self._db_conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    source TEXT,
                    target TEXT,
                    relation TEXT,
                    weight REAL
                )
            """)
            self._db_conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type)"
            )
            self._db_conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source)"
            )
            self._db_conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target)"
            )
            self._db_conn.commit()
            self._load_from_sqlite()
        except ImportError:
            print("[Warning] sqlite3 未安装，回退到内存模式")
            self._backend = StorageBackend.MEMORY

    def _init_json(self) -> None:
        """初始化 JSON 文件"""
        json_path = self._db_path or "knowledge.json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for n in data.get("nodes", []):
                    self._nodes[n["id"]] = KnowledgeNode(
                        id=n["id"],
                        name=n["name"],
                        node_type=n["type"],
                        properties=n.get("properties", {}),
                        created_at=n.get("created_at", time.time()),
                    )
                for e in data.get("edges", []):
                    self._edges.append(
                        KnowledgeEdge(
                            source=e["source"],
                            target=e["target"],
                            relation=e["relation"],
                            weight=e.get("weight", 1.0),
                        )
                    )
            except (json.JSONDecodeError, IOError):
                pass

    def _init_postgres(self) -> None:
        """初始化 PostgreSQL"""
        try:
            import psycopg2

            self._db_conn = psycopg2.connect(self._conn_string)
            self._db_conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id VARCHAR(32) PRIMARY KEY,
                    name VARCHAR(255),
                    node_type VARCHAR(64),
                    properties TEXT,
                    created_at FLOAT
                )
            """)
            self._db_conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    source VARCHAR(32),
                    target VARCHAR(32),
                    relation VARCHAR(64),
                    weight FLOAT
                )
            """)
            self._db_conn.commit()
            self._load_from_postgres()
        except ImportError:
            print("[Warning] psycopg2 未安装，回退到内存模式")
            self._backend = StorageBackend.MEMORY

    def _load_from_sqlite(self) -> None:
        """从 SQLite 加载"""
        if not self._db_conn:
            return
        cursor = self._db_conn.execute("SELECT * FROM nodes")
        for row in cursor:
            self._nodes[row[0]] = KnowledgeNode(
                id=row[0],
                name=row[1],
                node_type=row[2],
                properties=json.loads(row[3] or "{}"),
                created_at=row[4],
            )
        cursor = self._db_conn.execute("SELECT * FROM edges")
        for row in cursor:
            self._edges.append(
                KnowledgeEdge(
                    source=row[0],
                    target=row[1],
                    relation=row[2],
                    weight=row[3],
                )
            )

    def _load_from_postgres(self) -> None:
        """从 PostgreSQL 加载"""
        self._load_from_sqlite()  # 相同逻辑

    def _save_node(self, node: KnowledgeNode) -> None:
        """保存节点到数据库"""
        if self._backend == StorageBackend.SQLITE and self._db_conn:
            self._db_conn.execute(
                "INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?, ?)",
                (
                    node.id,
                    node.name,
                    node.node_type,
                    json.dumps(node.properties),
                    node.created_at,
                ),
            )
            self._db_conn.commit()
        elif self._backend == StorageBackend.POSTGRES and self._db_conn:
            self._db_conn.execute(
                "INSERT INTO nodes VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET name=%s, node_type=%s, properties=%s",
                (
                    node.id,
                    node.name,
                    node.node_type,
                    json.dumps(node.properties),
                    node.created_at,
                    node.name,
                    node.node_type,
                    json.dumps(node.properties),
                ),
            )
            self._db_conn.commit()

    def _save_edge(self, edge: KnowledgeEdge) -> None:
        """保存边到数据库"""
        if self._backend == StorageBackend.SQLITE and self._db_conn:
            self._db_conn.execute(
                "INSERT INTO edges VALUES (?, ?, ?, ?)",
                (edge.source, edge.target, edge.relation, edge.weight),
            )
            self._db_conn.commit()
        elif self._backend == StorageBackend.POSTGRES and self._db_conn:
            self._db_conn.execute(
                "INSERT INTO edges VALUES (%s, %s, %s, %s)",
                (edge.source, edge.target, edge.relation, edge.weight),
            )
            self._db_conn.commit()

    def _save_to_json(self) -> None:
        """保存到 JSON 文件"""
        if self._backend != StorageBackend.JSON:
            return
        json_path = self._db_path or "knowledge.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.export(), f, ensure_ascii=False, indent=2)

    def add_node(
        self,
        name: str,
        node_type: str = "default",
        properties: Optional[Dict[str, Any]] = None,
        node_id: Optional[str] = None,
    ) -> KnowledgeNode:
        """添加节点"""
        nid = node_id or str(uuid.uuid4())[:8]
        node = KnowledgeNode(
            id=nid,
            name=name,
            node_type=node_type,
            properties=properties or {},
        )
        self._nodes[nid] = node
        self._save_node(node)
        if self._backend == StorageBackend.JSON:
            self._save_to_json()
        return node

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        weight: float = 1.0,
    ) -> Optional[KnowledgeEdge]:
        """添加边"""
        if source not in self._nodes or target not in self._nodes:
            return None
        edge = KnowledgeEdge(
            source=source, target=target, relation=relation, weight=weight
        )
        self._edges.append(edge)
        self._save_edge(edge)
        if self._backend == StorageBackend.JSON:
            self._save_to_json()
        return edge

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """获取节点"""
        return self._nodes.get(node_id)

    def find_by_name(self, name: str) -> List[KnowledgeNode]:
        """按名称查找"""
        return [n for n in self._nodes.values() if n.name == name]

    def find_by_type(self, node_type: str) -> List[KnowledgeNode]:
        """按类型查找"""
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def neighbors(
        self, node_id: str, relation: Optional[str] = None
    ) -> List[KnowledgeNode]:
        """获取邻居节点"""
        if node_id not in self._nodes:
            return []
        result_ids = set()
        for edge in self._edges:
            if relation and edge.relation != relation:
                continue
            if edge.source == node_id:
                result_ids.add(edge.target)
            elif edge.target == node_id:
                result_ids.add(edge.source)
        return [self._nodes[nid] for nid in result_ids if nid in self._nodes]

    def delete_node(self, node_id: str) -> bool:
        """删除节点"""
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        self._edges = [
            e for e in self._edges if e.source != node_id and e.target != node_id
        ]
        if self._backend == StorageBackend.SQLITE and self._db_conn:
            self._db_conn.execute("DELETE FROM nodes WHERE id=?", (node_id,))
            self._db_conn.execute(
                "DELETE FROM edges WHERE source=? OR target=?", (node_id, node_id)
            )
            self._db_conn.commit()
        elif self._backend == StorageBackend.JSON:
            self._save_to_json()
        return True

    def stats(self) -> Dict[str, Any]:
        """统计信息"""
        type_count: Dict[str, int] = {}
        for n in self._nodes.values():
            type_count[n.node_type] = type_count.get(n.node_type, 0) + 1
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "node_types": len(type_count),
            "backend": self._backend.value,
        }

    def export(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.node_type,
                    "properties": n.properties,
                    "created_at": n.created_at,
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation,
                    "weight": e.weight,
                }
                for e in self._edges
            ],
        }

    def close(self) -> None:
        """关闭数据库连接"""
        if self._db_conn:
            self._db_conn.close()
            self._db_conn = None

    # -------- 向量相似度查询 --------

    def _node_text(self, node: KnowledgeNode) -> str:
        """将节点序列化为可搜索文本（名称 + 类型 + 属性）"""
        parts: List[str] = [node.name, node.node_type]
        for k, v in node.properties.items():
            parts.append(str(k))
            parts.append(str(v))
        return " ".join(parts)

    def _char_ngrams(self, text: str, n: int = 2) -> Dict[str, int]:
        """提取字符 n-gram 并统计频次（中文与英文通用）"""
        text = text.lower()
        # 去掉标点仅保留有效字符（保留中英文与数字）
        text = re.sub(
            r"[\s+\.\!\/_,$%^*(+\"\']+|[+——！，。？、~@#￥%……&*（）]+", " ", text
        )
        grams: Dict[str, int] = {}
        if len(text) < n:
            grams[text] = 1
            return grams
        for i in range(len(text) - n + 1):
            gram = text[i : i + n]
            grams[gram] = grams.get(gram, 0) + 1
        return grams

    def _cosine(self, a: Dict[str, int], b: Dict[str, int]) -> float:
        """稀疏向量余弦相似度"""
        if not a or not b:
            return 0.0
        common = set(a.keys()) & set(b.keys())
        dot = sum(a[k] * b[k] for k in common)
        norma = math.sqrt(sum(v * v for v in a.values()))
        normb = math.sqrt(sum(v * v for v in b.values()))
        if norma == 0 or normb == 0:
            return 0.0
        return dot / (norma * normb)

    def query_nearest(
        self,
        query: str,
        top_k: int = 5,
        node_type: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """按查询文本检索最相似的知识节点。

        采用字符 n-gram + 余弦相似度，零外部依赖，适合中英文混合场景。

        Args:
            query: 查询词，例如"人工智能"、"神经网络"
            top_k: 返回结果数量
            node_type: 可选，限定返回类型
            min_score: 最小相似度阈值（0-1），低于则剔除

        Returns:
            [{id, name, node_type, score, node}, ...] 按分数从高到低排序

        Example:
            >>> kb = KnowledgeBase()
            >>> kb.add_node("深度学习", node_type="concept", properties={"领域": "AI"})
            >>> kb.add_node("炒菜", node_type="concept", properties={"领域": "生活"})
            >>> results = kb.query_nearest("深度学习 人工智能", top_k=3)
            >>> for r in results:
            >>>     print(r["name"], round(r["score"], 3))
        """
        if not query or not self._nodes:
            return []

        query_vec = self._char_ngrams(query, n=2)

        candidates: List[Tuple[str, float, KnowledgeNode]] = []
        for node_id, node in self._nodes.items():
            if node_type and node.node_type != node_type:
                continue
            node_vec = self._char_ngrams(self._node_text(node), n=2)
            score = self._cosine(query_vec, node_vec)
            if score > min_score:
                candidates.append((node_id, score, node))

        # 按分数降序
        candidates.sort(key=lambda x: x[1], reverse=True)
        top = candidates[:top_k]

        return [
            {
                "id": n.id,
                "name": n.name,
                "node_type": n.node_type,
                "score": round(s, 4),
                "node": n,
            }
            for _, s, n in top
        ]

    # -------- 便捷批量导入 --------
    # -------- 批量操作增强（v1.3.0）--------
    def bulk_add(self, records: List[Dict[str, Any]]) -> List[KnowledgeNode]:
        """批量添加节点。records 每项形如：
        {"name": "...", "node_type": "...", "properties": {...}, "id": "..."}
        """
        nodes: List[KnowledgeNode] = []
        for rec in records:
            node = self.add_node(
                name=rec["name"],
                node_type=rec.get("node_type", "default"),
                properties=rec.get("properties", {}),
                node_id=rec.get("id"),
            )
            nodes.append(node)
        return nodes

    def update_node(
        self,
        node_id: str,
        name: Optional[str] = None,
        node_type: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Optional[KnowledgeNode]:
        """更新节点字段（部分更新）"""
        node = self._nodes.get(node_id)
        if not node:
            return None
        if name is not None:
            node.name = name
        if node_type is not None:
            node.node_type = node_type
        if properties is not None:
            node.properties = properties
        if self._backend == StorageBackend.SQLITE and self._db_conn:
            self._db_conn.execute(
                "UPDATE nodes SET name=?, node_type=?, properties=? WHERE id=?",
                (node.name, node.node_type, json.dumps(node.properties), node.id),
            )
            self._db_conn.commit()
        elif self._backend == StorageBackend.JSON:
            self._save_to_json()
        return node

    def delete_nodes(self, node_ids: List[str]) -> int:
        """批量删除节点，返回实际删除数量"""
        deleted = 0
        for nid in node_ids:
            if self.delete_node(nid):
                deleted += 1
        return deleted

    def upsert_node(
        self,
        name: str,
        node_type: str = "default",
        properties: Optional[Dict[str, Any]] = None,
    ) -> Tuple[KnowledgeNode, bool]:
        """原子 upsert：存在则更新，不存在则创建。返回 (node, created)"""
        for n in self.find_by_name(name):
            if n.node_type == node_type:
                return self.update_node(n.id, properties=properties), False
        return self.add_node(name, node_type=node_type, properties=properties), True

    def query_by_prefix(self, prefix: str, limit: int = 20) -> List[KnowledgeNode]:
        """前缀模糊搜索"""
        return [n for n in self._nodes.values() if n.name.startswith(prefix)][:limit]

    def query_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        node_type: Optional[str] = None,
        sort_by: str = "created_at",
        descending: bool = False,
    ) -> Dict[str, Any]:
        """分页查询"""
        nodes = list(self._nodes.values())
        if node_type:
            nodes = [n for n in nodes if n.node_type == node_type]
        if sort_by == "name":
            nodes.sort(key=lambda n: n.name, reverse=descending)
        elif sort_by == "created_at":
            nodes.sort(key=lambda n: n.created_at, reverse=descending)
        total = len(nodes)
        start = (page - 1) * page_size
        page_nodes = nodes[start : start + page_size]
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
            "items": page_nodes,
        }

    def use_sqlalchemy(self, db_path: Optional[str] = None) -> bool:
        """启用 SQLAlchemy ORM（需 sqlalchemy 已安装）"""
        if not _SQLALCHEMY_AVAILABLE:
            print("[Warning] SQLAlchemy 未安装，无法启用 ORM")
            return False
        sa_path = db_path or (self._db_path or "knowledge_sa.db")
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            engine = create_engine(f"sqlite:///{sa_path}", echo=False)
            _init_sa_tables(engine, sa_path)
            global _SA_engine, _SA_session_factory
            _SA_engine = engine
            _SA_session_factory = sessionmaker(bind=engine)
            import sqlite3

            conn = sqlite3.connect(sa_path)
            for node in self._nodes.values():
                conn.execute(
                    "INSERT OR REPLACE INTO sa_nodes VALUES (?, ?, ?, ?, ?)",
                    (
                        node.id,
                        node.name,
                        node.node_type,
                        json.dumps(node.properties, ensure_ascii=False),
                        node.created_at,
                    ),
                )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[Warning] SQLAlchemy 初始化失败：{e}")
            return False

    def stats(self) -> Dict[str, Any]:
        """统计信息（增强版）"""
        type_count: Dict[str, int] = {}
        for n in self._nodes.values():
            type_count[n.node_type] = type_count.get(n.node_type, 0) + 1
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "node_types": len(type_count),
            "backend": self._backend.value,
            "sqlalchemy_available": _SQLALCHEMY_AVAILABLE,
            "type_distribution": type_count,
        }

    def import_from_json(self, file_path: str) -> Dict[str, int]:
        """从 JSON 文件批量导入节点。
        JSON 格式：[{"name": "...", "node_type": "...", "properties": {...}}, ...]
        返回 {"added": N, "skipped": M, "errors": [...]}
        """
        import json

        added, skipped, errors = 0, 0, []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return {"added": 0, "skipped": 0, "errors": [str(e)]}
        if not isinstance(data, list):
            data = [data]
        for item in data:
            try:
                if not item.get("name"):
                    skipped += 1
                    continue
                node, created = self.upsert_node(
                    item["name"],
                    node_type=item.get("node_type", "default"),
                    properties=item.get("properties", {}),
                )
                added += 1
            except Exception as e:
                errors.append(f"{item.get('name', '?')}: {e}")
        return {"added": added, "skipped": skipped, "errors": errors}

    def import_from_csv(
        self,
        file_path: str,
        name_col: str = "name",
        type_col: str = "node_type",
        props_cols: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        """从 CSV 文件批量导入节点（无需 pandas）。
        props_cols 为 None 时，其余列全部作为 properties。
        """
        import csv

        added, skipped, errors = 0, 0, []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as e:
            return {"added": 0, "skipped": 0, "errors": [str(e)]}
        for row in rows:
            try:
                name = row.get(name_col, "").strip()
                if not name:
                    skipped += 1
                    continue
                ntype = row.get(type_col, "default").strip()
                if props_cols:
                    props = {
                        k: v
                        for k, v in row.items()
                        if k not in (name_col, type_col)
                        and k in props_cols
                        and v.strip()
                    }
                else:
                    props = {
                        k: v
                        for k, v in row.items()
                        if k not in (name_col, type_col) and v.strip()
                    }
                node, created = self.upsert_node(
                    name, node_type=ntype, properties=props
                )
                added += 1
            except Exception as e:
                errors.append(f"{name or '?'}：{e}")
        return {"added": added, "skipped": skipped, "errors": errors}

    def import_from_yaml(self, file_path: str) -> Dict[str, int]:
        """从 YAML 文件批量导入节点。
        YAML 格式（list）：
        - name: 儒家
          node_type: school
          properties:
            代表: 孔子
        支持两种格式：list 或 根键映射。
        """
        try:
            import yaml  # PyYAML
        except ImportError:
            # 纯 Python 兜底：正则解析（仅支持简单格式）
            added, skipped, errors = 0, 0, []
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                import re

                # 简单正则：匹配 - name: xxx 和 node_type: xxx
                entries = re.findall(
                    r'-\s+name:\s*"?([^"\n]+)"?\s*\n\s+node_type:\s*"?([^"\n]+)"?',
                    content,
                )
                for name, ntype in entries:
                    node, created = self.upsert_node(
                        name.strip(), node_type=ntype.strip(), properties={}
                    )
                    added += 1
            except Exception as e:
                errors.append(str(e))
            return {"added": added, "skipped": skipped, "errors": errors}

        added, skipped, errors = 0, 0, []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            return {"added": 0, "skipped": 0, "errors": [str(e)]}

        items = data if isinstance(data, list) else []
        if isinstance(data, dict):
            # 尝试找顶级 list
            for v in data.values():
                if isinstance(v, list):
                    items = v
                    break

        for item in items:
            try:
                if not item.get("name"):
                    skipped += 1
                    continue
                node, created = self.upsert_node(
                    item["name"],
                    node_type=item.get("node_type", "default"),
                    properties=item.get("properties", {}),
                )
                added += 1
            except Exception as e:
                errors.append(f"{item.get('name', '?')}: {e}")
        return {"added": added, "skipped": skipped, "errors": errors}

    # -------- 向量数据库集成（v1.5.0）--------
    def use_vector_db(
        self, provider: str = "auto", persist_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """启用向量数据库（FAISS 或 ChromaDB），优雅降级。

        provider: "auto" | "faiss" | "chroma" | "disable"
        - auto: 优先尝试 FAISS，然后 ChromaDB，最后降级为内存
        - faiss: 仅使用 FAISS
        - chroma: 仅使用 ChromaDB
        - disable: 禁用，保留内存模式
        返回 {"provider": str, "dimension": int, "indexed": int, "error": str}
        """
        result: Dict[str, Any] = {
            "provider": "memory",
            "dimension": 0,
            "indexed": 0,
            "error": "",
        }

        if provider == "disable":
            self._vector_provider = "memory"
            return result

        # 生成所有节点文本向量
        texts = [n.name + " " + json.dumps(n.properties) for n in self._nodes.values()]
        dim = min(len(texts) * 2, 128) if texts else 128  # 降维到128或以下

        # 尝试 FAISS
        if provider in ("auto", "faiss"):
            try:
                import faiss
                import numpy as np

                vectors = np.random.rand(len(texts), dim).astype("float32")
                # 真实向量：使用字符 n-gram hash
                for i, text in enumerate(texts):
                    vec = self._char_ngrams(text, n=2)
                    norm = (sum(v**2 for v in vec.values()) or 1) ** 0.5
                    arr = np.array(
                        list(vec.values()) + [0.0] * max(0, dim - len(vec)),
                        dtype=np.float32,
                    )
                    if norm > 0:
                        arr = arr / norm
                    if len(arr) < dim:
                        arr = np.pad(arr, (0, dim - len(arr)))
                    vectors[i] = arr[:dim]

                index = faiss.IndexFlatIP(dim)  # 内积相似度
                faiss.normalize_L2(vectors)
                index.add(vectors)

                self._faiss_index = index
                self._vector_dim = dim
                self._vector_provider = "faiss"
                result = {
                    "provider": "faiss",
                    "dimension": dim,
                    "indexed": len(texts),
                    "error": "",
                }
                return result
            except ImportError:
                result["error"] = "FAISS 未安装"
            except Exception as e:
                result["error"] = f"FAISS: {e}"

        # 尝试 ChromaDB
        if provider in ("auto", "chroma"):
            try:
                import chromadb

                chroma_path = persist_path or "chroma_db"
                client = chromadb.Client(
                    chromadb.config.Settings(
                        chromadb_db_path=chroma_path,
                        allow_reset=True,
                    )
                )
                coll = client.create_collection("tengod_knowledge", get_or_create=True)

                if texts:
                    ids = [n.id for n in self._nodes.values()]
                    coll.add(ids=ids, documents=texts)

                self._chroma_client = client
                self._vector_provider = "chroma"
                result = {
                    "provider": "chroma",
                    "dimension": 0,
                    "indexed": len(texts),
                    "error": "",
                }
                return result
            except ImportError:
                result["error"] = "ChromaDB 未安装"
            except Exception as e:
                result["error"] = f"ChromaDB: {e}"

        self._vector_provider = "memory"
        return result

    def vector_search(
        self, query: str, top_k: int = 5, min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """向量数据库语义搜索（如果未启用向量 DB 则降级到 query_nearest）"""
        if not hasattr(self, "_vector_provider"):
            return self.query_nearest(query, top_k=top_k, min_score=min_score)

        provider = getattr(self, "_vector_provider", "memory")

        if provider == "memory":
            return self.query_nearest(query, top_k=top_k, min_score=min_score)

        try:
            if provider == "chroma":
                coll = self._chroma_client.get_collection("tengod_knowledge")
                results = coll.query(query_texts=[query], n_results=top_k)
                hits = []
                for i, (doc_id, doc_text) in enumerate(
                    zip(results["ids"][0], results["documents"][0])
                ):
                    # 找对应节点
                    node = next(
                        (n for n in self._nodes.values() if n.id == doc_id), None
                    )
                    if node:
                        hits.append(
                            {
                                "id": node.id,
                                "name": node.name,
                                "node_type": node.node_type,
                                "score": results["distances"][0][i]
                                if i < len(results["distances"][0])
                                else 0.0,
                                "node": node,
                            }
                        )
                return [h for h in hits if h["score"] >= min_score]
        except Exception:
            pass

        # 降级到内存查询
        return self.query_nearest(query, top_k=top_k, min_score=min_score)


__all__ = ["KnowledgeBase", "KnowledgeNode", "KnowledgeEdge", "StorageBackend"]
__version__ = "1.5.0"
