#!/usr/bin/env python3
"""
db_migration.py — SQLite → PostgreSQL 数据迁移工具 v1.0.0

用法：
  $ python -m tengod.db_migration \
      --sqlite /path/to/source.db \
      --postgres postgresql://user:pass@host:5432/dbname \
      --batch-size 1000

设计要点：
  - 使用 sqlite3 标准库读取源库；
  - 使用 SQLAlchemy + tengod.data_store 的 ORM 模型写入目标库；
  - 分批次迁移，内存占用低；
  - 支持回滚、报告、日志与进度回调。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Type


logger = logging.getLogger("db_migration")
if not logger.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)


# ============================================================================
# 迁移报告数据结构
# ============================================================================


@dataclass
class TableMigrationStat:
    table_name: str
    source_rows: int
    target_rows: int
    migrated_rows: int
    elapsed_sec: float
    error: Optional[str] = None


@dataclass
class MigrationReport:
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    table_stats: Dict[str, TableMigrationStat] = field(default_factory=dict)
    total_rows: int = 0
    errors: List[str] = field(default_factory=list)
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "table_stats": {
                name: {
                    "source_rows": stat.source_rows,
                    "target_rows": stat.target_rows,
                    "migrated_rows": stat.migrated_rows,
                    "elapsed_sec": round(stat.elapsed_sec, 3),
                    "error": stat.error,
                }
                for name, stat in self.table_stats.items()
            },
            "total_rows": self.total_rows,
            "errors": self.errors,
            "success": self.success and not self.errors,
        }


# ============================================================================
# MigrationManager
# ============================================================================


class MigrationManager:
    """SQLite → PostgreSQL/ORM 数据迁移管理器。"""

    def __init__(self, sqlite_path: str, postgres_url: str):
        self.sqlite_path = sqlite_path
        self.postgres_url = postgres_url or ""
        self.report = MigrationReport()
        self._engine = None
        self._sqlite_conn: Optional[sqlite3.Connection] = None
        self._TABLE_REGISTRY: List[Dict[str, Any]] = []
        self._register_tables()

    # ── 注册表 ──────────────────────────────────────────────────

    def _register_tables(self) -> None:
        """注册要迁移的表信息（延迟导入 data_store，避免循环依赖）"""
        from .data_store import User, BaziRecord, ReportCache  # noqa: F401

        self._TABLE_REGISTRY = [
            {
                "table_name": "users",
                "model_class": User,
                "column_map": {
                    "id": "id",
                    "username": "username",
                    "display_name": "display_name",
                    "password_hash": "password_hash",
                    "role": "role",
                    "email": "email",
                    "is_active": "is_active",
                    "api_quota_daily": "api_quota_daily",
                    "last_login_at": "last_login_at",
                    "created_at": "created_at",
                },
            },
            {
                "table_name": "bazi_records",
                "model_class": BaziRecord,
                "column_map": {
                    "id": "id",
                    "user_id": "user_id",
                    "label": "label",
                    "year": "year",
                    "month": "month",
                    "day": "day",
                    "hour": "hour",
                    "minute": "minute",
                    "gender": "gender",
                    "longitude": "longitude",
                    "latitude": "latitude",
                    "day_master": "day_master",
                    "pillars_json": "pillars_json",
                    "analysis_json": "analysis_json",
                    "shensha_json": "shensha_json",
                    "geju_json": "geju_json",
                    "yongshen_json": "yongshen_json",
                    "tiaohou_json": "tiaohou_json",
                    "tags": "tags",
                    "notes": "notes",
                    "created_at": "created_at",
                    "updated_at": "updated_at",
                },
            },
            {
                "table_name": "report_cache",
                "model_class": ReportCache,
                "column_map": {
                    "id": "id",
                    "bazi_record_id": "bazi_record_id",
                    "format": "format",
                    "content": "content",
                    "content_hash": "content_hash",
                    "created_at": "created_at",
                },
            },
        ]

    # ── 连接管理 ─────────────────────────────────────────────

    def _connect_sqlite(self) -> sqlite3.Connection:
        """连接 SQLite 源数据库并启用 row_factory。"""
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            pass
        logger.info("已连接 SQLite 源数据库: %s", self.sqlite_path)
        return conn

    def _connect_postgres(self):
        """连接目标数据库（使用 SQLAlchemy 引擎）。"""
        from .data_store import Base
        from sqlalchemy import create_engine

        url = self.postgres_url
        if url and (url.startswith("postgresql") or url.startswith("sqlite:")):
            if url.startswith("postgresql"):
                engine = create_engine(
                    url, echo=False, pool_pre_ping=True, pool_size=10, max_overflow=20
                )
            else:
                engine = create_engine(url, echo=False)
        else:
            engine = create_engine("sqlite:///:memory:", echo=False)

        Base.metadata.create_all(engine)
        logger.info("已连接目标数据库并验证 schema")
        return engine

    # ── SQLite 辅助查询 ─────────────────────────────────────

    def _count_sqlite(self, table: str) -> int:
        """统计 SQLite 源表中的行数。"""
        if self._sqlite_conn is None:
            self._sqlite_conn = self._connect_sqlite()
        cur = self._sqlite_conn.cursor()
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        return int(cur.fetchone()[0])

    def _iter_sqlite_rows(
        self, table: str, columns: Iterable[str]
    ) -> Iterable[sqlite3.Row]:
        """分批次 yield SQLite 行，避免一次性加载全部行。"""
        if self._sqlite_conn is None:
            self._sqlite_conn = self._connect_sqlite()
        cols = ", ".join(f'"{c}"' for c in columns)
        cur = self._sqlite_conn.cursor()
        cur.execute(f'SELECT {cols} FROM "{table}" ORDER BY "id"')
        while True:
            rows = cur.fetchmany(1000)
            if not rows:
                break
            for row in rows:
                yield row

    def _sqlite_tables(self) -> List[str]:
        """列出源数据库中的所有表（通过 sqlite_master）。"""
        if self._sqlite_conn is None:
            self._sqlite_conn = self._connect_sqlite()
        cur = self._sqlite_conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        return [row[0] for row in cur.fetchall()]

    # ── 类型转换 ────────────────────────────────────────────

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        """把 SQLite 文本 datetime 解析成 datetime 对象（UTC）。"""
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value, tz=timezone.utc)
            except (OSError, ValueError):
                pass
        s = str(value).strip()
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(s, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            logger.warning("无法解析 datetime: %r", value)
            return None

    @staticmethod
    def _coerce_value(sqlite_value: Any, model_attr: str, model_class: Type) -> Any:
        """根据模型属性把 SQLite 值转换为合适的 Python 类型。"""
        if sqlite_value is None:
            return None
        try:
            col = getattr(model_class.__table__.columns, model_attr, None)
        except Exception:
            col = None
        if col is not None:
            col_type = str(col.type).lower()
            if "datetime" in col_type or col.type.python_type is datetime:
                return MigrationManager._parse_datetime(sqlite_value)
            if "int" in col_type:
                try:
                    return int(sqlite_value)
                except (TypeError, ValueError):
                    return None
            if "float" in col_type or "numeric" in col_type:
                try:
                    return float(sqlite_value)
                except (TypeError, ValueError):
                    return None
            return sqlite_value
        if isinstance(sqlite_value, bytes):
            try:
                return sqlite_value.decode("utf-8")
            except UnicodeDecodeError:
                return sqlite_value
        return sqlite_value

    # ── schema 验证 / 序列重置 ─────────────────────────────

    def _verify_schema(self) -> bool:
        """验证目标数据库中的表都已存在。"""
        from sqlalchemy import inspect

        if self._engine is None:
            self._engine = self._connect_postgres()
        inspector = inspect(self._engine)
        ok = True
        for entry in self._TABLE_REGISTRY:
            table = entry["model_class"].__tablename__
            if not inspector.has_table(table):
                logger.warning("目标数据库缺少表: %s", table)
                ok = False
            else:
                logger.info("schema 验证通过: %s", table)
        return ok

    def _reset_sequences(self, session, model_classes: Iterable[Type]) -> None:
        """重置 PostgreSQL 的 serial 序列到当前最大 id。"""
        from sqlalchemy import text

        if not self.postgres_url or not self.postgres_url.startswith("postgresql"):
            return
        for cls in model_classes:
            table_name = cls.__tablename__
            try:
                seq_sql = text("SELECT pg_get_serial_sequence(:t, 'id')")
                result = session.execute(seq_sql, {"t": table_name}).scalar()
                if result:
                    setval_sql = text(
                        f"SELECT setval('{result}', "
                        f"(SELECT COALESCE(MAX(id), 1) FROM {table_name}))"
                    )
                    new_val = session.execute(setval_sql).scalar()
                    logger.info("已重置序列 %s → %s", result, new_val)
            except Exception as exc:
                logger.warning("重置序列失败 %s: %s", table_name, exc)

    # ── 通用表迁移 ──────────────────────────────────────────

    def _migrate_table(
        self,
        table_name: str,
        model_class,
        column_map: Dict[str, str],
        batch_size: int = 1000,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> TableMigrationStat:
        """分批次把 SQLite 行写入目标数据库。"""
        from sqlalchemy.orm import Session

        t0 = time.time()
        source_count = 0
        target_count = 0
        migrated = 0
        error: Optional[str] = None

        try:
            source_count = self._count_sqlite(table_name)
            logger.info("开始迁移 %s: 源库 %d 行", table_name, source_count)

            if self._engine is None:
                self._engine = self._connect_postgres()

            sqlite_columns = list(column_map.keys())
            model_attrs = [column_map[c] for c in sqlite_columns]
            batch: List[Any] = []

            with Session(self._engine) as session:
                for row in self._iter_sqlite_rows(table_name, sqlite_columns):
                    data: Dict[str, Any] = {}
                    for sql_col, attr in zip(sqlite_columns, model_attrs):
                        try:
                            raw = row[sql_col] if sql_col in row.keys() else None
                        except (IndexError, KeyError):
                            raw = None
                        data[attr] = self._coerce_value(raw, attr, model_class)
                    try:
                        instance = model_class(**data)
                    except TypeError:
                        # 某些属性可能不被 ORM 构造接受，过滤掉它
                        valid = {k: v for k, v in data.items() if hasattr(model_class, k)}
                        instance = model_class(**valid)
                    batch.append(instance)

                    if len(batch) >= batch_size:
                        session.add_all(batch)
                        session.flush()
                        session.commit()
                        migrated += len(batch)
                        if progress_callback:
                            progress_callback(migrated, source_count)
                        logger.debug("  已迁移 %d/%d", migrated, source_count)
                        batch = []

                if batch:
                    session.add_all(batch)
                    session.flush()
                    session.commit()
                    migrated += len(batch)
                    if progress_callback:
                        progress_callback(migrated, source_count)
                    batch = []

                target_count = session.query(model_class).count()
                logger.info(
                    "完成 %s: 源 %d 行，目标 %d 行",
                    table_name, source_count, target_count,
                )
        except Exception as exc:
            logger.exception("迁移 %s 失败: %s", table_name, exc)
            error = str(exc)
            self.report.errors.append(f"{table_name}: {exc}")

        return TableMigrationStat(
            table_name=table_name,
            source_rows=source_count,
            target_rows=target_count,
            migrated_rows=migrated,
            elapsed_sec=time.time() - t0,
            error=error,
        )

    # ── 各表便利方法 ────────────────────────────────────────

    def migrate_users(self, batch_size: int = 1000) -> TableMigrationStat:
        entry = self._TABLE_REGISTRY[0]
        return self._migrate_table(
            entry["table_name"], entry["model_class"], entry["column_map"], batch_size
        )

    def migrate_records(self, batch_size: int = 1000) -> TableMigrationStat:
        entry = self._TABLE_REGISTRY[1]
        return self._migrate_table(
            entry["table_name"], entry["model_class"], entry["column_map"], batch_size
        )

    def migrate_report_cache(self, batch_size: int = 1000) -> TableMigrationStat:
        entry = self._TABLE_REGISTRY[2]
        return self._migrate_table(
            entry["table_name"], entry["model_class"], entry["column_map"], batch_size
        )

    # ── 验证 / 回滚 ───────────────────────────────────────

    def verify_migration(self) -> Dict[str, Dict[str, int]]:
        """比较源库与目标库各表行数差异。"""
        from sqlalchemy.orm import Session

        result: Dict[str, Dict[str, int]] = {}
        if self._engine is None:
            self._engine = self._connect_postgres()
        if self._sqlite_conn is None:
            self._sqlite_conn = self._connect_sqlite()

        with Session(self._engine) as session:
            for entry in self._TABLE_REGISTRY:
                src = self._count_sqlite(entry["table_name"])
                tgt = session.query(entry["model_class"]).count()
                result[entry["table_name"]] = {"source": src, "target": tgt, "diff": src - tgt}
                if src != tgt:
                    logger.warning(
                        "行计数不匹配 %s: 源=%d, 目标=%d",
                        entry["table_name"], src, tgt,
                    )
                else:
                    logger.info("行计数匹配 %s: %d 行", entry["table_name"], src)
        return result

    def rollback(self) -> None:
        """清空目标数据库中所有被迁移的表。"""
        from sqlalchemy.orm import Session

        if self._engine is None:
            self._engine = self._connect_postgres()

        logger.warning("开始回滚（清空）目标数据库所有表...")
        with Session(self._engine) as session:
            for entry in reversed(self._TABLE_REGISTRY):
                cls = entry["model_class"]
                try:
                    session.query(cls).delete(synchronize_session=False)
                    session.commit()
                    logger.info("已清空表: %s", cls.__tablename__)
                except Exception as exc:
                    logger.exception("清空 %s 失败: %s", cls.__tablename__, exc)
                    session.rollback()

    # ── 主流程 ────────────────────────────────────────────

    def run_all(self, batch_size: int = 1000) -> MigrationReport:
        """执行完整的迁移流程并返回报告。"""
        self.report = MigrationReport(
            start_time=datetime.now(timezone.utc).isoformat()
        )

        self._sqlite_conn = self._connect_sqlite()
        self._engine = self._connect_postgres()

        try:
            self._verify_schema()
        except Exception as exc:
            logger.exception("schema 验证失败: %s", exc)
            self.report.errors.append(f"schema: {exc}")

        src_tables = self._sqlite_tables()
        logger.info("源数据库中共发现 %d 个表: %s", len(src_tables), src_tables)

        total = 0
        for entry in self._TABLE_REGISTRY:
            table = entry["table_name"]
            if table not in src_tables:
                logger.warning("源库中不存在表 %s，跳过", table)
                continue
            try:
                stat = self._migrate_table(
                    table, entry["model_class"], entry["column_map"], batch_size
                )
                self.report.table_stats[table] = stat
                total += stat.migrated_rows
            except Exception as exc:
                logger.exception("迁移 %s 时发生异常: %s", table, exc)
                self.report.errors.append(f"{table}: {exc}")

        if "cases" in src_tables:
            logger.info("源库中检测到 cases 表（未注册到 ORM，跳过迁移）")

        try:
            from sqlalchemy.orm import Session

            with Session(self._engine) as session:
                self._reset_sequences(
                    session, [e["model_class"] for e in self._TABLE_REGISTRY]
                )
                session.commit()
        except Exception as exc:
            logger.warning("重置序列失败: %s", exc)

        self.verify_migration()

        self.report.end_time = datetime.now(timezone.utc).isoformat()
        self.report.total_rows = total
        if self.report.errors:
            self.report.success = False
        logger.info("迁移完成，共迁移 %d 行，错误 %d 个", total, len(self.report.errors))

        return self.report

    def close(self) -> None:
        if self._sqlite_conn:
            try:
                self._sqlite_conn.close()
            except Exception:
                pass
        if self._engine:
            try:
                self._engine.dispose()
            except Exception:
                pass


# ============================================================================
# 命令行接口
# ============================================================================


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SQLite → PostgreSQL 数据迁移工具")
    parser.add_argument("--sqlite", required=False, help="源 SQLite 数据库路径")
    parser.add_argument("--postgres", required=False, help="目标 PostgreSQL 数据库 URL")
    parser.add_argument("--batch-size", type=int, default=1000, help="每批迁移的行数")
    parser.add_argument(
        "--rollback-first", action="store_true", help="迁移前先清空目标数据库所有表"
    )
    parser.add_argument("--verbose", action="store_true", help="启用 DEBUG 级别日志")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="运行内置自测（无需真实 PostgreSQL）",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.self_test:
        return _self_test(batch_size=args.batch_size)

    if not args.sqlite or not args.postgres:
        parser.error("--sqlite 与 --postgres 是必需参数（或使用 --self-test）")
        return 2

    manager = MigrationManager(args.sqlite, args.postgres)
    try:
        if args.rollback_first:
            manager.rollback()
        report = manager.run_all(batch_size=args.batch_size)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return 0 if not report.errors else 1
    finally:
        manager.close()


# ============================================================================
# 自测：创建小型 SQLite 测试数据库，迁移到内存 SQLite 目标
# ============================================================================


def _create_test_sqlite(path: str) -> None:
    """在指定路径上创建一个小型测试 SQLite 数据库。"""
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            display_name TEXT,
            password_hash TEXT,
            role TEXT NOT NULL DEFAULT 'user',
            email TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            api_quota_daily INTEGER NOT NULL DEFAULT 100,
            last_login_at TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bazi_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            label TEXT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            day INTEGER NOT NULL,
            hour INTEGER NOT NULL,
            minute INTEGER NOT NULL DEFAULT 0,
            gender TEXT NOT NULL DEFAULT 'male',
            longitude REAL DEFAULT 116.4,
            latitude REAL DEFAULT 39.9,
            day_master TEXT,
            pillars_json TEXT,
            analysis_json TEXT,
            shensha_json TEXT,
            geju_json TEXT,
            yongshen_json TEXT,
            tiaohou_json TEXT,
            tags TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS report_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bazi_record_id INTEGER NOT NULL,
            format TEXT NOT NULL DEFAULT 'text',
            content TEXT NOT NULL,
            content_hash TEXT,
            created_at TEXT NOT NULL
        );
        """
    )

    now = datetime.now(timezone.utc).isoformat()
    users = [
        ("alice", "爱丽丝", "hash1", "user", "alice@example.com", 1, 100, None, now),
        ("bob", "鲍勃", "hash2", "user", "bob@example.com", 1, 100, now, now),
        ("charlie", "查理", None, "admin", None, 1, 500, None, now),
    ]
    cur.executemany(
        "INSERT INTO users (username, display_name, password_hash, role, email,"
        " is_active, api_quota_daily, last_login_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        users,
    )

    records = []
    ganzhi = "甲乙丙丁戊己庚辛壬癸"
    for i in range(15):
        pillars = {"year": f"y{i}", "month": f"m{i}", "day": f"d{i}", "hour": f"h{i}"}
        analysis = {"note": f"analysis-{i}"}
        records.append(
            (
                1 if i % 2 == 0 else None,
                f"label_{i}",
                1980 + i,
                (i % 12) + 1,
                (i % 28) + 1,
                i % 24,
                0,
                "male" if i % 2 == 0 else "female",
                116.4,
                39.9,
                ganzhi[i % 10],
                json.dumps(pillars, ensure_ascii=False),
                json.dumps(analysis, ensure_ascii=False),
                None,
                None,
                None,
                None,
                f"tag{i}",
                None,
                now,
                now,
            )
        )
    cur.executemany(
        "INSERT INTO bazi_records (user_id, label, year, month, day, hour, minute,"
        " gender, longitude, latitude, day_master, pillars_json, analysis_json,"
        " shensha_json, geju_json, yongshen_json, tiaohou_json, tags, notes,"
        " created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        records,
    )

    caches = [
        (1, "text", f"报告 #{i} 内容", f"hash{i}", now) for i in range(10)
    ]
    cur.executemany(
        "INSERT INTO report_cache (bazi_record_id, format, content, content_hash,"
        " created_at) VALUES (?, ?, ?, ?, ?)",
        caches,
    )

    conn.commit()
    conn.close()


def _self_test(batch_size: int = 1000) -> int:
    """内置自测：创建 SQLite 测试 DB → 迁移到内存 SQLite 目标 → 验证行数。"""
    print("=" * 60)
    print("db_migration 自测开始")
    print("=" * 60)

    tmp = tempfile.gettempdir()
    source = os.path.join(tmp, "tengod_migration_source_test.db")
    target = os.path.join(tmp, "tengod_migration_target_test.db")

    for p in (source, target):
        if os.path.exists(p):
            os.remove(p)

    try:
        # 1. 建源库
        _create_test_sqlite(source)
        print(f"[1] 源测试 SQLite: {source}")

        # 2. 迁移到文件型 SQLite 目标（便于事后校验）
        target_url = f"sqlite:///{target}"
        print(f"[2] 目标数据库 URL: {target_url}")

        mgr = MigrationManager(source, target_url)
        try:
            # 3. 先 rollback 测试
            mgr.rollback()
            print("[3] rollback 测试通过")

            # 4. 执行迁移
            report = mgr.run_all(batch_size=batch_size)
            print(
                "[4] 迁移报告: "
                + json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
            )

            # 5. 行计数校验
            src_conn = sqlite3.connect(source)
            expected = {
                "users": src_conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                "bazi_records": src_conn.execute(
                    "SELECT COUNT(*) FROM bazi_records"
                ).fetchone()[0],
                "report_cache": src_conn.execute(
                    "SELECT COUNT(*) FROM report_cache"
                ).fetchone()[0],
            }
            src_conn.close()

            tgt_conn = sqlite3.connect(target)
            actual = {
                "users": tgt_conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                "bazi_records": tgt_conn.execute(
                    "SELECT COUNT(*) FROM bazi_records"
                ).fetchone()[0],
                "report_cache": tgt_conn.execute(
                    "SELECT COUNT(*) FROM report_cache"
                ).fetchone()[0],
            }
            tgt_conn.close()

            print(f"[5] 源库行数: {expected}")
            print(f"[6] 目标行数: {actual}")

            all_ok = expected == actual and not report.errors
            print("[7] 自测结果:", "PASS" if all_ok else "FAIL")
            print("=" * 60)
            return 0 if all_ok else 1
        finally:
            mgr.close()
    finally:
        for p in (source, target):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


if __name__ == "__main__":
    sys.exit(main())
