#!/usr/bin/env python3
"""
knowledge_base.py — 知识库
正财主理固化，提供轻量级知识图谱与查询能力。
支持内存存储和数据库持久化（SQLite/PostgreSQL）。
"""

import time
import uuid
import json
import os
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class StorageBackend(Enum):
    """存储后端"""
    MEMORY = "memory"     # 内存（默认）
    SQLITE = "sqlite"     # SQLite
    POSTGRES = "postgres" # PostgreSQL
    JSON = "json"         # JSON 文件


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
        """初始化 SQLite"""
        try:
            import sqlite3
            db_path = self._db_path or "knowledge.db"
            self._db_conn = sqlite3.connect(db_path)
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
                    self._edges.append(KnowledgeEdge(
                        source=e["source"],
                        target=e["target"],
                        relation=e["relation"],
                        weight=e.get("weight", 1.0),
                    ))
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
            self._edges.append(KnowledgeEdge(
                source=row[0],
                target=row[1],
                relation=row[2],
                weight=row[3],
            ))

    def _load_from_postgres(self) -> None:
        """从 PostgreSQL 加载"""
        self._load_from_sqlite()  # 相同逻辑

    def _save_node(self, node: KnowledgeNode) -> None:
        """保存节点到数据库"""
        if self._backend == StorageBackend.SQLITE and self._db_conn:
            self._db_conn.execute(
                "INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?, ?)",
                (node.id, node.name, node.node_type, json.dumps(node.properties), node.created_at),
            )
            self._db_conn.commit()
        elif self._backend == StorageBackend.POSTGRES and self._db_conn:
            self._db_conn.execute(
                "INSERT INTO nodes VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET name=%s, node_type=%s, properties=%s",
                (node.id, node.name, node.node_type, json.dumps(node.properties), node.created_at, node.name, node.node_type, json.dumps(node.properties)),
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
        edge = KnowledgeEdge(source=source, target=target, relation=relation, weight=weight)
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

    def neighbors(self, node_id: str, relation: Optional[str] = None) -> List[KnowledgeNode]:
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
        self._edges = [e for e in self._edges if e.source != node_id and e.target != node_id]
        if self._backend == StorageBackend.SQLITE and self._db_conn:
            self._db_conn.execute("DELETE FROM nodes WHERE id=?", (node_id,))
            self._db_conn.execute("DELETE FROM edges WHERE source=? OR target=?", (node_id, node_id))
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


__all__ = ["KnowledgeBase", "KnowledgeNode", "KnowledgeEdge", "StorageBackend"]
__version__ = "1.1.0"