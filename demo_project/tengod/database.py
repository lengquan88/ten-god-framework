"""
database.py — SQLite 数据持久化层 v2.11
========================================
零依赖 SQLite 数据库，6 张表覆盖案例/反馈/对话/知识图谱/用户/配额。

特性：
  - 标准库 sqlite3，零外部依赖
  - WAL 模式，支持并发读
  - 外键约束 + 索引优化
  - JSON 字段自动序列化
  - 向后兼容：STORAGE_BACKEND=sqlite 启用，默认内存模式

用法：
  >>> from tengod.database import get_db, STORAGE_BACKEND
  >>> db = get_db()
  >>> db.insert_case({"name": "测试", "bazi_data": {...}})
  >>> cases = db.list_cases(limit=10)
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Union

# ============================================================================
# 配置
# ============================================================================

STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "memory")
DB_PATH = os.environ.get("TENGOD_DB_PATH", "tengod.db")

# ============================================================================
# Schema
# ============================================================================

SCHEMA_VERSION = 1

CREATE_TABLES_SQL = [
    # ── 案例表 ──
    """
    CREATE TABLE IF NOT EXISTS cases (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        bazi_data   TEXT NOT NULL DEFAULT '{}',
        analysis    TEXT NOT NULL DEFAULT '{}',
        tags        TEXT NOT NULL DEFAULT '[]',
        category    TEXT NOT NULL DEFAULT 'general',
        metadata    TEXT NOT NULL DEFAULT '{}',
        created_at  REAL NOT NULL DEFAULT (strftime('%s', 'now')),
        updated_at  REAL NOT NULL DEFAULT (strftime('%s', 'now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_cases_category ON cases(category)",
    "CREATE INDEX IF NOT EXISTS idx_cases_created ON cases(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_cases_name ON cases(name)",

    # ── 反馈表 ──
    """
    CREATE TABLE IF NOT EXISTS feedback (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id    TEXT NOT NULL,
        domain        TEXT NOT NULL DEFAULT 'general',
        accuracy      INTEGER NOT NULL DEFAULT 3,
        satisfaction  INTEGER NOT NULL DEFAULT 3,
        usefulness    INTEGER NOT NULL DEFAULT 3,
        comment       TEXT NOT NULL DEFAULT '',
        analysis_type TEXT NOT NULL DEFAULT '',
        corrections   TEXT NOT NULL DEFAULT '[]',
        tags          TEXT NOT NULL DEFAULT '[]',
        created_at    REAL NOT NULL DEFAULT (strftime('%s', 'now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_feedback_domain ON feedback(domain)",
    "CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at)",

    # ── 对话表 ──
    """
    CREATE TABLE IF NOT EXISTS conversations (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id  TEXT NOT NULL,
        role        TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
        message     TEXT NOT NULL,
        intent      TEXT NOT NULL DEFAULT '{}',
        created_at  REAL NOT NULL DEFAULT (strftime('%s', 'now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at)",

    # ── 知识图谱节点表 ──
    """
    CREATE TABLE IF NOT EXISTS kg_nodes (
        id          TEXT PRIMARY KEY,
        domain      TEXT NOT NULL,
        concept     TEXT NOT NULL,
        confidence  REAL NOT NULL DEFAULT 0.5,
        properties  TEXT NOT NULL DEFAULT '{}',
        sources     TEXT NOT NULL DEFAULT '[]',
        created_at  REAL NOT NULL DEFAULT (strftime('%s', 'now')),
        updated_at  REAL NOT NULL DEFAULT (strftime('%s', 'now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_kg_nodes_domain ON kg_nodes(domain)",
    "CREATE INDEX IF NOT EXISTS idx_kg_nodes_concept ON kg_nodes(concept)",

    # ── 知识图谱边表 ──
    """
    CREATE TABLE IF NOT EXISTS kg_edges (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id   TEXT NOT NULL,
        target_id   TEXT NOT NULL,
        relation    TEXT NOT NULL DEFAULT 'correlates',
        weight      REAL NOT NULL DEFAULT 0.5,
        confidence  REAL NOT NULL DEFAULT 0.5,
        created_at  REAL NOT NULL DEFAULT (strftime('%s', 'now')),
        FOREIGN KEY (source_id) REFERENCES kg_nodes(id) ON DELETE CASCADE,
        FOREIGN KEY (target_id) REFERENCES kg_nodes(id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_kg_edges_source ON kg_edges(source_id)",
    "CREATE INDEX IF NOT EXISTS idx_kg_edges_target ON kg_edges(target_id)",
    "CREATE INDEX IF NOT EXISTS idx_kg_edges_relation ON kg_edges(relation)",

    # ── 用户/配额表 ──
    """
    CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT NOT NULL UNIQUE,
        api_key     TEXT NOT NULL DEFAULT '',
        role        TEXT NOT NULL DEFAULT 'user',
        quota_used  INTEGER NOT NULL DEFAULT 0,
        quota_limit INTEGER NOT NULL DEFAULT 1000,
        metadata    TEXT NOT NULL DEFAULT '{}',
        created_at  REAL NOT NULL DEFAULT (strftime('%s', 'now')),
        updated_at  REAL NOT NULL DEFAULT (strftime('%s', 'now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
    "CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key)",

    # ── Schema 版本表 ──
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
    )
    """,
]


# ============================================================================
# 数据库管理器
# ============================================================================

class DatabaseManager:
    """SQLite 数据库管理器

    线程安全，自动管理连接和事务。
    """

    def __init__(self, db_path: str = DB_PATH):
        self._db_path = db_path
        self._local = threading.local()

    @property
    def _conn(self) -> sqlite3.Connection:
        """获取线程本地连接"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = self._create_connection()
        return self._local.conn

    def _create_connection(self) -> sqlite3.Connection:
        """创建数据库连接"""
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _cursor(self):
        """获取游标的上下文管理器"""
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cur.close()

    def close(self) -> None:
        """关闭连接"""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    # ── 生命周期 ──────────────────────────────────────────────────────────

    def init(self) -> None:
        """初始化数据库：创建所有表"""
        with self._cursor() as cur:
            for sql in CREATE_TABLES_SQL:
                cur.execute(sql)

            # 检查 schema 版本
            cur.execute("SELECT COUNT(*) FROM schema_version")
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )

    def is_initialized(self) -> bool:
        """检查数据库是否已初始化"""
        try:
            with self._cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM schema_version")
                return cur.fetchone()[0] > 0
        except Exception:
            return False

    def get_stats(self) -> Dict[str, int]:
        """获取数据库统计"""
        with self._cursor() as cur:
            stats = {}
            for table in ["cases", "feedback", "conversations", "kg_nodes", "kg_edges", "users"]:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cur.fetchone()[0]
            return stats

    # ── 案例 CRUD ─────────────────────────────────────────────────────────

    def insert_case(self, data: Dict[str, Any]) -> int:
        """插入案例，返回 ID"""
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO cases (name, bazi_data, analysis, tags, category, metadata)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    data.get("name", ""),
                    json.dumps(data.get("bazi_data", {}), ensure_ascii=False),
                    json.dumps(data.get("analysis", {}), ensure_ascii=False),
                    json.dumps(data.get("tags", []), ensure_ascii=False),
                    data.get("category", "general"),
                    json.dumps(data.get("metadata", {}), ensure_ascii=False),
                ),
            )
            return cur.lastrowid

    def update_case(self, case_id: int, data: Dict[str, Any]) -> bool:
        """更新案例"""
        fields = []
        values = []
        for key in ["name", "category"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        for key in ["bazi_data", "analysis", "tags", "metadata"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(json.dumps(data[key], ensure_ascii=False))
        if not fields:
            return False
        fields.append("updated_at = ?")
        values.append(time.time())
        values.append(case_id)

        with self._cursor() as cur:
            cur.execute(f"UPDATE cases SET {', '.join(fields)} WHERE id = ?", values)
            return cur.rowcount > 0

    def get_case(self, case_id: int) -> Optional[Dict[str, Any]]:
        """获取单个案例"""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
            row = cur.fetchone()
            return self._row_to_case(row) if row else None

    def list_cases(
        self,
        limit: int = 20,
        offset: int = 0,
        category: str = "",
        search: str = "",
    ) -> List[Dict[str, Any]]:
        """列出案例，支持分类过滤和搜索"""
        query = "SELECT * FROM cases WHERE 1=1"
        params: List[Any] = []

        if category:
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND (name LIKE ? OR bazi_data LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._cursor() as cur:
            cur.execute(query, params)
            return [self._row_to_case(row) for row in cur.fetchall()]

    def count_cases(self, category: str = "", search: str = "") -> int:
        """统计案例数"""
        query = "SELECT COUNT(*) FROM cases WHERE 1=1"
        params: List[Any] = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if search:
            query += " AND (name LIKE ? OR bazi_data LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        with self._cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()[0]

    def delete_case(self, case_id: int) -> bool:
        """删除案例"""
        with self._cursor() as cur:
            cur.execute("DELETE FROM cases WHERE id = ?", (case_id,))
            return cur.rowcount > 0

    def _row_to_case(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转为案例字典"""
        return {
            "id": row["id"],
            "name": row["name"],
            "bazi_data": json.loads(row["bazi_data"]),
            "analysis": json.loads(row["analysis"]),
            "tags": json.loads(row["tags"]),
            "category": row["category"],
            "metadata": json.loads(row["metadata"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # ── 反馈 CRUD ─────────────────────────────────────────────────────────

    def insert_feedback(self, data: Dict[str, Any]) -> int:
        """插入反馈"""
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO feedback (session_id, domain, accuracy, satisfaction, usefulness,
                   comment, analysis_type, corrections, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data.get("session_id", ""),
                    data.get("domain", "general"),
                    data.get("accuracy", 3),
                    data.get("satisfaction", 3),
                    data.get("usefulness", 3),
                    data.get("comment", ""),
                    data.get("analysis_type", ""),
                    json.dumps(data.get("corrections", []), ensure_ascii=False),
                    json.dumps(data.get("tags", []), ensure_ascii=False),
                ),
            )
            return cur.lastrowid

    def list_feedback(
        self,
        limit: int = 20,
        offset: int = 0,
        domain: str = "",
        session_id: str = "",
    ) -> List[Dict[str, Any]]:
        """列出反馈"""
        query = "SELECT * FROM feedback WHERE 1=1"
        params: List[Any] = []
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._cursor() as cur:
            cur.execute(query, params)
            return [self._row_to_feedback(row) for row in cur.fetchall()]

    def count_feedback(self, domain: str = "") -> int:
        """统计反馈数"""
        query = "SELECT COUNT(*) FROM feedback"
        params: List[Any] = []
        if domain:
            query += " WHERE domain = ?"
            params.append(domain)
        with self._cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()[0]

    def get_feedback_stats(self) -> Dict[str, Any]:
        """获取反馈统计"""
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) as total, AVG(accuracy) as avg_acc, "
                        "AVG(satisfaction) as avg_sat, AVG(usefulness) as avg_use "
                        "FROM feedback")
            row = cur.fetchone()
            return {
                "total": row["total"] or 0,
                "avg_accuracy": round(row["avg_acc"] or 0, 2),
                "avg_satisfaction": round(row["avg_sat"] or 0, 2),
                "avg_usefulness": round(row["avg_use"] or 0, 2),
            }

    def _row_to_feedback(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "domain": row["domain"],
            "accuracy": row["accuracy"],
            "satisfaction": row["satisfaction"],
            "usefulness": row["usefulness"],
            "comment": row["comment"],
            "analysis_type": row["analysis_type"],
            "corrections": json.loads(row["corrections"]),
            "tags": json.loads(row["tags"]),
            "created_at": row["created_at"],
        }

    # ── 对话 CRUD ─────────────────────────────────────────────────────────

    def insert_message(self, session_id: str, role: str, message: str, intent: Optional[Dict] = None) -> int:
        """插入对话消息"""
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO conversations (session_id, role, message, intent) VALUES (?, ?, ?, ?)",
                (session_id, role, message, json.dumps(intent or {}, ensure_ascii=False)),
            )
            return cur.lastrowid

    def get_conversation(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取会话消息"""
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM conversations WHERE session_id = ? "
                "ORDER BY created_at ASC LIMIT ?",
                (session_id, limit),
            )
            return [self._row_to_message(row) for row in cur.fetchall()]

    def get_recent_conversations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近会话摘要"""
        with self._cursor() as cur:
            cur.execute(
                "SELECT session_id, COUNT(*) as msg_count, MAX(created_at) as last_msg "
                "FROM conversations GROUP BY session_id ORDER BY last_msg DESC LIMIT ?",
                (limit,),
            )
            return [{"session_id": r["session_id"], "message_count": r["msg_count"],
                     "last_message": r["last_msg"]} for r in cur.fetchall()]

    def delete_conversation(self, session_id: str) -> bool:
        """删除会话"""
        with self._cursor() as cur:
            cur.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
            return cur.rowcount > 0

    def _row_to_message(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "role": row["role"],
            "message": row["message"],
            "intent": json.loads(row["intent"]),
            "created_at": row["created_at"],
        }

    # ── 知识图谱 CRUD ─────────────────────────────────────────────────────

    def insert_kg_node(self, data: Dict[str, Any]) -> None:
        """插入/更新知识图谱节点"""
        with self._cursor() as cur:
            cur.execute(
                """INSERT OR REPLACE INTO kg_nodes (id, domain, concept, confidence, properties, sources, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    data["id"],
                    data.get("domain", ""),
                    data.get("concept", ""),
                    data.get("confidence", 0.5),
                    json.dumps(data.get("properties", {}), ensure_ascii=False),
                    json.dumps(data.get("sources", []), ensure_ascii=False),
                    time.time(),
                ),
            )

    def get_kg_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """获取知识图谱节点"""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM kg_nodes WHERE id = ?", (node_id,))
            row = cur.fetchone()
            return self._row_to_kg_node(row) if row else None

    def list_kg_nodes(self, domain: str = "") -> List[Dict[str, Any]]:
        """列出知识图谱节点"""
        query = "SELECT * FROM kg_nodes"
        params: List[Any] = []
        if domain:
            query += " WHERE domain = ?"
            params.append(domain)
        with self._cursor() as cur:
            cur.execute(query, params)
            return [self._row_to_kg_node(row) for row in cur.fetchall()]

    def _row_to_kg_node(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "domain": row["domain"],
            "concept": row["concept"],
            "confidence": row["confidence"],
            "properties": json.loads(row["properties"]),
            "sources": json.loads(row["sources"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def insert_kg_edge(self, data: Dict[str, Any]) -> int:
        """插入知识图谱边"""
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO kg_edges (source_id, target_id, relation, weight, confidence) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    data["source_id"],
                    data["target_id"],
                    data.get("relation", "correlates"),
                    data.get("weight", 0.5),
                    data.get("confidence", 0.5),
                ),
            )
            return cur.lastrowid

    def list_kg_edges(self, source_id: str = "", target_id: str = "") -> List[Dict[str, Any]]:
        """列出知识图谱边"""
        query = "SELECT * FROM kg_edges WHERE 1=1"
        params: List[Any] = []
        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)
        if target_id:
            query += " AND target_id = ?"
            params.append(target_id)
        with self._cursor() as cur:
            cur.execute(query, params)
            return [self._row_to_kg_edge(row) for row in cur.fetchall()]

    def _row_to_kg_edge(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "source_id": row["source_id"],
            "target_id": row["target_id"],
            "relation": row["relation"],
            "weight": row["weight"],
            "confidence": row["confidence"],
            "created_at": row["created_at"],
        }

    # ── 用户 CRUD ─────────────────────────────────────────────────────────

    def get_user(self, username: str = "", api_key: str = "") -> Optional[Dict[str, Any]]:
        """获取用户"""
        with self._cursor() as cur:
            if api_key:
                cur.execute("SELECT * FROM users WHERE api_key = ?", (api_key,))
            elif username:
                cur.execute("SELECT * FROM users WHERE username = ?", (username,))
            else:
                return None
            row = cur.fetchone()
            return self._row_to_user(row) if row else None

    def create_user(self, data: Dict[str, Any]) -> int:
        """创建用户"""
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, api_key, role, quota_limit, metadata) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    data["username"],
                    data.get("api_key", ""),
                    data.get("role", "user"),
                    data.get("quota_limit", 1000),
                    json.dumps(data.get("metadata", {}), ensure_ascii=False),
                ),
            )
            return cur.lastrowid

    def update_quota(self, username: str, delta: int = 1) -> bool:
        """更新用户配额"""
        with self._cursor() as cur:
            cur.execute(
                "UPDATE users SET quota_used = quota_used + ?, updated_at = ? WHERE username = ?",
                (delta, time.time(), username),
            )
            return cur.rowcount > 0

    def check_quota(self, username: str) -> Tuple[bool, int, int]:
        """检查配额：返回 (是否可用, 已用, 上限)"""
        user = self.get_user(username=username)
        if not user:
            return False, 0, 0
        return user["quota_used"] < user["quota_limit"], user["quota_used"], user["quota_limit"]

    def _row_to_user(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "username": row["username"],
            "api_key": row["api_key"],
            "role": row["role"],
            "quota_used": row["quota_used"],
            "quota_limit": row["quota_limit"],
            "metadata": json.loads(row["metadata"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # ── 导入导出 ──────────────────────────────────────────────────────────

    def export_all(self) -> Dict[str, Any]:
        """导出全部数据为 JSON"""
        with self._cursor() as cur:
            tables = {}
            for table in ["cases", "feedback", "conversations", "kg_nodes", "kg_edges", "users"]:
                cur.execute(f"SELECT * FROM {table}")
                tables[table] = [dict(row) for row in cur.fetchall()]
            return {"schema_version": SCHEMA_VERSION, "exported_at": time.time(), "tables": tables}

    def import_all(self, data: Dict[str, Any]) -> Dict[str, int]:
        """从 JSON 导入全部数据"""
        counts = {}
        tables = data.get("tables", {})
        for table_name, rows in tables.items():
            if not rows:
                counts[table_name] = 0
                continue
            with self._cursor() as cur:
                columns = list(rows[0].keys())
                placeholders = ", ".join(["?"] * len(columns))
                col_names = ", ".join(columns)
                sql = f"INSERT OR REPLACE INTO {table_name} ({col_names}) VALUES ({placeholders})"
                cur.executemany(sql, [tuple(r[c] for c in columns) for r in rows])
                counts[table_name] = len(rows)
        return counts


# ============================================================================
# 全局数据库实例
# ============================================================================

_db_instance: Optional[DatabaseManager] = None
_db_lock = threading.Lock()


def get_db(db_path: str = "") -> DatabaseManager:
    """获取全局数据库实例（线程安全单例）"""
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                path = db_path or DB_PATH
                _db_instance = DatabaseManager(path)
                if STORAGE_BACKEND == "sqlite":
                    _db_instance.init()
    return _db_instance


def reset_db() -> None:
    """重置数据库实例（测试用）"""
    global _db_instance
    _db_instance = None


def is_persistent() -> bool:
    """检查是否启用持久化（运行时读取环境变量）"""
    return os.environ.get("STORAGE_BACKEND", "memory") == "sqlite"


__all__ = [
    "DatabaseManager",
    "get_db",
    "reset_db",
    "is_persistent",
    "STORAGE_BACKEND",
    "DB_PATH",
]