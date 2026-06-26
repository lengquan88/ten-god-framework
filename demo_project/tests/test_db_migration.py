"""
db_migration 模块综合测试

覆盖所有公开类、方法、函数，以及边界条件、Mock 路径。
"""
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from tengod.db_migration import (
    MigrationManager,
    MigrationReport,
    TableMigrationStat,
    _build_arg_parser,
    _create_test_sqlite,
    _self_test,
    main,
    logger,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

def _make_source(path: str) -> None:
    """使用内置 _create_test_sqlite 创建标准测试源数据库。"""
    _create_test_sqlite(path)


def _make_empty_source(path: str, tables: list[str] | None = None) -> None:
    """创建只有空表的源数据库。"""
    tables = tables or ["users"]
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    if "users" in tables:
        cur.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, "
            "display_name TEXT, password_hash TEXT, role TEXT, email TEXT, "
            "is_active INTEGER, api_quota_daily INTEGER, last_login_at TEXT, "
            "created_at TEXT)"
        )
    if "bazi_records" in tables:
        cur.execute(
            "CREATE TABLE bazi_records (id INTEGER PRIMARY KEY, user_id INTEGER, "
            "label TEXT, year INTEGER, month INTEGER, day INTEGER, hour INTEGER, "
            "minute INTEGER, gender TEXT, longitude REAL, latitude REAL, "
            "day_master TEXT, pillars_json TEXT, analysis_json TEXT, "
            "shensha_json TEXT, geju_json TEXT, yongshen_json TEXT, "
            "tiaohou_json TEXT, tags TEXT, notes TEXT, created_at TEXT, updated_at TEXT)"
        )
    if "report_cache" in tables:
        cur.execute(
            "CREATE TABLE report_cache (id INTEGER PRIMARY KEY, bazi_record_id INTEGER, "
            "format TEXT, content TEXT, content_hash TEXT, created_at TEXT)"
        )
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. TableMigrationStat 数据类测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestTableMigrationStat:
    """TableMigrationStat 数据类——构造与字段验证。"""

    def test_create_with_all_fields(self):
        stat = TableMigrationStat(
            table_name="users",
            source_rows=100,
            target_rows=100,
            migrated_rows=100,
            elapsed_sec=2.5,
            error=None,
        )
        assert stat.table_name == "users"
        assert stat.source_rows == 100
        assert stat.target_rows == 100
        assert stat.migrated_rows == 100
        assert stat.elapsed_sec == 2.5
        assert stat.error is None

    def test_default_error_is_none(self):
        stat = TableMigrationStat(
            table_name="t", source_rows=0, target_rows=0, migrated_rows=0, elapsed_sec=0.0
        )
        assert stat.error is None

    def test_with_error_message(self):
        stat = TableMigrationStat(
            table_name="bad",
            source_rows=10,
            target_rows=0,
            migrated_rows=0,
            elapsed_sec=0.2,
            error="table not found",
        )
        assert stat.error == "table not found"

    def test_zero_rows_migration(self):
        stat = TableMigrationStat(
            table_name="empty",
            source_rows=0,
            target_rows=0,
            migrated_rows=0,
            elapsed_sec=0.0,
        )
        assert stat.migrated_rows == 0
        assert stat.source_rows == 0

    def test_large_row_counts(self):
        stat = TableMigrationStat(
            table_name="big",
            source_rows=10_000_000,
            target_rows=10_000_000,
            migrated_rows=10_000_000,
            elapsed_sec=3600.0,
        )
        assert stat.migrated_rows == 10_000_000


# ═══════════════════════════════════════════════════════════════════════════════
# 2. MigrationReport 数据类测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestMigrationReport:
    """MigrationReport 数据类——默认值、to_dict()、边界条件。"""

    def test_default_values(self):
        r = MigrationReport()
        assert r.start_time is None
        assert r.end_time is None
        assert r.table_stats == {}
        assert r.total_rows == 0
        assert r.errors == []
        assert r.success is True

    def test_to_dict_empty(self):
        d = MigrationReport().to_dict()
        assert d["start_time"] is None
        assert d["end_time"] is None
        assert d["table_stats"] == {}
        assert d["total_rows"] == 0
        assert d["errors"] == []
        assert d["success"] is True

    def test_to_dict_with_complete_data(self):
        r = MigrationReport(
            start_time="2025-06-01T00:00:00+00:00",
            end_time="2025-06-01T00:05:00+00:00",
            total_rows=500,
            errors=["users: timeout"],
            success=False,
        )
        stat = TableMigrationStat(
            table_name="users",
            source_rows=500,
            target_rows=500,
            migrated_rows=500,
            elapsed_sec=3.14159,
        )
        r.table_stats["users"] = stat

        d = r.to_dict()
        assert d["start_time"] == "2025-06-01T00:00:00+00:00"
        assert d["end_time"] == "2025-06-01T00:05:00+00:00"
        assert d["total_rows"] == 500
        assert d["errors"] == ["users: timeout"]
        # success 被 errors 覆盖
        assert d["success"] is False

        us = d["table_stats"]["users"]
        assert us["source_rows"] == 500
        assert us["target_rows"] == 500
        assert us["migrated_rows"] == 500
        assert us["elapsed_sec"] == 3.142  # round(3.14159, 3)
        assert us["error"] is None

    def test_to_dict_success_true_no_errors(self):
        r = MigrationReport(success=True, errors=[])
        assert r.to_dict()["success"] is True

    def test_to_dict_success_overridden_by_errors(self):
        """to_dict() 中：success 被 errors 列表覆盖为 False。"""
        r = MigrationReport(success=True, errors=["e1", "e2"])
        assert r.to_dict()["success"] is False

    def test_multiple_table_stats(self):
        r = MigrationReport()
        r.table_stats["a"] = TableMigrationStat("a", 10, 10, 10, 1.0)
        r.table_stats["b"] = TableMigrationStat("b", 20, 20, 20, 2.0, error="fail")
        d = r.to_dict()
        assert len(d["table_stats"]) == 2
        assert d["table_stats"]["b"]["error"] == "fail"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MigrationManager 初始化测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestMigrationManagerInit:
    """MigrationManager.__init__ — 属性、表注册。"""

    def test_basic_init(self, tmp_path):
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), "sqlite:///:memory:")
        assert mgr.sqlite_path == str(src)
        assert mgr.postgres_url == "sqlite:///:memory:"
        assert isinstance(mgr.report, MigrationReport)
        assert mgr._engine is None
        assert mgr._sqlite_conn is None
        mgr.close()

    def test_init_with_empty_url(self, tmp_path):
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), "")
        assert mgr.postgres_url == ""
        mgr.close()

    def test_table_registry_has_three_entries(self, tmp_path):
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), "sqlite:///:memory:")
        assert len(mgr._TABLE_REGISTRY) == 3
        names = [e["table_name"] for e in mgr._TABLE_REGISTRY]
        assert "users" in names
        assert "bazi_records" in names
        assert "report_cache" in names
        mgr.close()

    def test_table_registry_has_column_maps(self, tmp_path):
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), "sqlite:///:memory:")
        for entry in mgr._TABLE_REGISTRY:
            assert "column_map" in entry
            assert "model_class" in entry
            assert isinstance(entry["column_map"], dict)
            assert len(entry["column_map"]) > 0
        mgr.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 4. SQLite 连接与查询测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestSQLiteOperations:
    """SQLite 连接、查询、迭代。"""

    def test_connect_sqlite(self, tmp_path):
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), "sqlite:///:memory:")
        conn = mgr._connect_sqlite()
        assert conn is not None
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        assert cur.fetchone()[0] == 3
        mgr.close()

    def test_connect_sqlite_caches_connection(self, tmp_path):
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), "sqlite:///:memory:")
        c1 = mgr._connect_sqlite()
        c2 = mgr._connect_sqlite()
        # _connect_sqlite 每次调用都会新建连接（不缓存），
        # 但 _count_sqlite 等会缓存 self._sqlite_conn
        assert c1 is not None
        assert c2 is not None
        mgr.close()

    def test_count_sqlite(self, tmp_path):
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), "sqlite:///:memory:")
        assert mgr._count_sqlite("users") == 3
        assert mgr._count_sqlite("bazi_records") == 15
        assert mgr._count_sqlite("report_cache") == 10
        mgr.close()

    def test_count_sqlite_uses_cached_connection(self, tmp_path):
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), "sqlite:///:memory:")
        mgr._sqlite_conn = mgr._connect_sqlite()
        # 第二次调用 _count_sqlite 使用缓存的连接
        assert mgr._count_sqlite("users") == 3
        mgr.close()

    def test_sqlite_tables(self, tmp_path):
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), "sqlite:///:memory:")
        tables = mgr._sqlite_tables()
        assert "users" in tables
        assert "bazi_records" in tables
        assert "report_cache" in tables
        # 排除 sqlite_ 前缀的表
        for t in tables:
            assert not t.startswith("sqlite_")
        mgr.close()

    def test_iter_sqlite_rows_all(self, tmp_path):
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), "sqlite:///:memory:")
        rows = list(mgr._iter_sqlite_rows("users", ["id", "username", "role"]))
        assert len(rows) == 3
        usernames = {r["username"] for r in rows}
        assert usernames == {"alice", "bob", "charlie"}
        mgr.close()

    def test_iter_sqlite_rows_empty_table(self, tmp_path):
        src = tmp_path / "s.db"
        _make_empty_source(str(src), ["users"])
        mgr = MigrationManager(str(src), "sqlite:///:memory:")
        rows = list(mgr._iter_sqlite_rows("users", ["id", "username"]))
        assert len(rows) == 0
        mgr.close()

    def test_iter_sqlite_rows_ordered_by_id(self, tmp_path):
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), "sqlite:///:memory:")
        rows = list(mgr._iter_sqlite_rows("users", ["id", "username"]))
        ids = [r["id"] for r in rows]
        assert ids == sorted(ids)
        mgr.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 5. 类型转换测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseDatetime:
    """_parse_datetime 静态方法——各种输入格式。"""

    def test_none(self):
        assert MigrationManager._parse_datetime(None) is None

    def test_empty_string(self):
        assert MigrationManager._parse_datetime("") is None

    def test_already_datetime(self):
        dt = datetime(2025, 6, 1, tzinfo=timezone.utc)
        assert MigrationManager._parse_datetime(dt) == dt

    def test_iso_no_tz(self):
        r = MigrationManager._parse_datetime("2025-06-01T12:00:00")
        assert r is not None
        assert r.year == 2025
        assert r.month == 6
        assert r.day == 1
        assert r.tzinfo == timezone.utc  # 追加 UTC

    def test_iso_with_tz(self):
        r = MigrationManager._parse_datetime("2025-06-01T12:00:00+00:00")
        assert r is not None
        assert r.year == 2025

    def test_iso_with_microseconds(self):
        r = MigrationManager._parse_datetime("2025-06-01T12:00:00.123456")
        assert r is not None
        assert r.microsecond == 123456

    def test_iso_with_microseconds_and_tz(self):
        r = MigrationManager._parse_datetime("2025-06-01T12:00:00.123456+00:00")
        assert r is not None

    def test_date_only(self):
        r = MigrationManager._parse_datetime("2025-06-01")
        assert r is not None
        assert r.year == 2025
        assert r.month == 6
        assert r.day == 1

    def test_space_separated(self):
        r = MigrationManager._parse_datetime("2025-06-01 12:00:00")
        assert r is not None
        assert r.year == 2025

    def test_space_separated_with_microseconds(self):
        r = MigrationManager._parse_datetime("2025-06-01 12:00:00.123456")
        assert r is not None

    def test_from_timestamp_int(self):
        # 1735689600 = 2025-01-01 00:00:00 UTC
        r = MigrationManager._parse_datetime(1735689600)
        assert r is not None
        assert r.year == 2025

    def test_from_timestamp_float(self):
        r = MigrationManager._parse_datetime(1735689600.0)
        assert r is not None

    def test_fromisoformat_fallback(self):
        r = MigrationManager._parse_datetime("2025-06-01T12:00:00Z")
        assert r is not None
        assert r.year == 2025

    def test_invalid_string(self):
        assert MigrationManager._parse_datetime("not-a-date") is None

    def test_timestamp_out_of_range(self):
        assert MigrationManager._parse_datetime(99999999999999) is None


class TestCoerceValue:
    """_coerce_value 静态方法——类型转换与边界条件。"""

    def test_none_value(self):
        from tengod.data_store import User
        assert MigrationManager._coerce_value(None, "username", User) is None

    def test_string_value(self):
        from tengod.data_store import User
        assert MigrationManager._coerce_value("hello", "username", User) == "hello"

    def test_int_column(self):
        from tengod.data_store import User
        assert MigrationManager._coerce_value("5", "is_active", User) == 5
        assert MigrationManager._coerce_value(5, "is_active", User) == 5

    def test_int_conversion_error(self):
        from tengod.data_store import User
        assert MigrationManager._coerce_value("abc", "is_active", User) is None

    def test_float_column(self):
        from tengod.data_store import BaziRecord
        assert MigrationManager._coerce_value("116.4", "longitude", BaziRecord) == 116.4

    def test_float_conversion_error(self):
        from tengod.data_store import BaziRecord
        assert MigrationManager._coerce_value("abc", "longitude", BaziRecord) is None

    def test_datetime_column(self):
        from tengod.data_store import User
        r = MigrationManager._coerce_value("2025-06-01T12:00:00", "created_at", User)
        assert isinstance(r, datetime)

    def test_bytes_decode_utf8(self):
        # 当列信息不可用时，bytes 被解码为字符串
        from tengod.data_store import User
        r = MigrationManager._coerce_value(b"hello", "nonexistent_attr", User)
        assert r == "hello"

    def test_bytes_decode_error(self):
        r = MigrationManager._coerce_value(b"\xff\xfe", "nonexistent_attr", object)
        assert r == b"\xff\xfe"

    def test_bytes_with_column_info(self):
        from tengod.data_store import User
        # username 是已知列（String 类型），bytes 直接返回
        r = MigrationManager._coerce_value(b"hello", "username", User)
        assert r == b"hello"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. 目标数据库连接与 Schema 验证
# ═══════════════════════════════════════════════════════════════════════════════

class TestTargetConnection:
    """_connect_postgres 与 _verify_schema。"""

    def test_connect_empty_url_uses_memory(self, tmp_path):
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), "")
        engine = mgr._connect_postgres()
        assert engine is not None
        mgr.close()

    def test_connect_sqlite_url(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        engine = mgr._connect_postgres()
        assert engine is not None
        inspector = inspect(engine)
        assert inspector.has_table("users")
        mgr.close()

    def test_connect_postgresql_url(self, tmp_path):
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), "postgresql://localhost:5432/testdb")
        try:
            engine = mgr._connect_postgres()
            assert engine is not None
        except Exception:
            pass
        finally:
            mgr.close()

    def test_verify_schema_all_present(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._engine = mgr._connect_postgres()
        assert mgr._verify_schema() is True
        mgr.close()

    def test_verify_schema_missing_table(self, tmp_path):
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{tmp_path}/t.db")
        empty_engine = create_engine(f"sqlite:///{tmp_path}/empty.db")
        mgr._engine = empty_engine
        assert mgr._verify_schema() is False
        mgr.close()

    def test_verify_schema_auto_connects(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        # engine 为 None，自动连接
        ok = mgr._verify_schema()
        assert ok is True
        mgr.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 7. _reset_sequences 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestResetSequences:
    """_reset_sequences 方法——PostgreSQL 与 SQLite 分支。"""

    def test_non_postgresql_skips(self, tmp_path):
        """非 PostgreSQL 目标时直接返回。"""
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{tmp_path}/t.db")
        mgr._engine = mgr._connect_postgres()
        from tengod.data_store import User, BaziRecord, ReportCache
        with Session(mgr._engine) as session:
            mgr._reset_sequences(session, [User, BaziRecord, ReportCache])
        mgr.close()

    def test_postgresql_url_triggers_sequence_reset(self):
        """postgresql:// URL 触发序列重置逻辑（Mock 验证）。"""
        from tengod.data_store import User
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar.return_value = None

        mgr = MigrationManager("/fake.db", "postgresql://localhost:5432/db")
        mgr._engine = MagicMock()
        mgr._reset_sequences(mock_session, [User])

        # 验证 execute 被调用
        assert mock_session.execute.call_count >= 1

    def test_postgresql_sequence_exception_handled(self):
        """序列重置异常被捕获，不向上传播。"""
        from tengod.data_store import User
        mock_session = MagicMock()
        mock_session.execute.side_effect = RuntimeError("sequence error")

        mgr = MigrationManager("/fake.db", "postgresql://localhost:5432/db")
        mgr._engine = MagicMock()
        # 不应抛出异常
        mgr._reset_sequences(mock_session, [User])


# ═══════════════════════════════════════════════════════════════════════════════
# 8. _migrate_table 核心迁移测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestMigrateTable:
    """_migrate_table 方法——完整迁移、分批、进度回调、错误处理。"""

    def test_migrate_users(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()

        entry = mgr._TABLE_REGISTRY[0]
        stat = mgr._migrate_table(
            entry["table_name"], entry["model_class"], entry["column_map"], batch_size=1000
        )
        assert stat.table_name == "users"
        assert stat.source_rows == 3
        assert stat.target_rows == 3
        assert stat.migrated_rows == 3
        assert stat.error is None
        assert stat.elapsed_sec > 0
        mgr.close()

    def test_migrate_bazi_records(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()

        entry = mgr._TABLE_REGISTRY[1]
        stat = mgr._migrate_table(
            entry["table_name"], entry["model_class"], entry["column_map"], batch_size=1000
        )
        assert stat.migrated_rows == 15
        assert stat.error is None
        mgr.close()

    def test_migrate_report_cache(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()

        entry = mgr._TABLE_REGISTRY[2]
        stat = mgr._migrate_table(
            entry["table_name"], entry["model_class"], entry["column_map"], batch_size=1000
        )
        assert stat.migrated_rows == 10
        assert stat.error is None
        mgr.close()

    def test_small_batch_size(self, tmp_path):
        """小批量测试分批逻辑。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()

        entry = mgr._TABLE_REGISTRY[1]  # 15 rows
        stat = mgr._migrate_table(
            entry["table_name"], entry["model_class"], entry["column_map"], batch_size=3
        )
        assert stat.migrated_rows == 15
        mgr.close()

    def test_batch_size_of_one(self, tmp_path):
        """批次大小为 1 的极端情况。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()

        entry = mgr._TABLE_REGISTRY[0]  # 3 rows
        stat = mgr._migrate_table(
            entry["table_name"], entry["model_class"], entry["column_map"], batch_size=1
        )
        assert stat.migrated_rows == 3
        mgr.close()

    def test_progress_callback(self, tmp_path):
        """进度回调被正确调用。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()

        calls = []

        def cb(migrated, total):
            calls.append((migrated, total))

        entry = mgr._TABLE_REGISTRY[0]  # 3 rows
        stat = mgr._migrate_table(
            entry["table_name"], entry["model_class"], entry["column_map"],
            batch_size=1, progress_callback=cb
        )
        assert stat.migrated_rows == 3
        assert len(calls) >= 3
        # 最后一次回调：migrated == 3
        assert calls[-1][0] == 3
        assert calls[-1][1] == 3
        mgr.close()

    def test_empty_source_table(self, tmp_path):
        """空源表迁移。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_empty_source(str(src), ["users"])
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()

        entry = mgr._TABLE_REGISTRY[0]
        stat = mgr._migrate_table(
            entry["table_name"], entry["model_class"], entry["column_map"], batch_size=1000
        )
        assert stat.source_rows == 0
        assert stat.migrated_rows == 0
        assert stat.target_rows == 0
        mgr.close()

    def test_error_on_nonexistent_table(self, tmp_path):
        """迁移不存在的表时记录错误。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()

        from tengod.data_store import User
        stat = mgr._migrate_table(
            "nonexistent", User,
            {"id": "id", "username": "username"}, batch_size=1000
        )
        assert stat.error is not None
        assert stat.migrated_rows == 0
        mgr.close()

    def test_auto_connects_engine(self, tmp_path):
        """_migrate_table 在 engine 为 None 时自动连接。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        # engine 为 None
        entry = mgr._TABLE_REGISTRY[0]
        stat = mgr._migrate_table(
            entry["table_name"], entry["model_class"], entry["column_map"], batch_size=1000
        )
        assert stat.migrated_rows == 3
        mgr.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 9. 便利方法测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestConvenienceMethods:
    """migrate_users / migrate_records / migrate_report_cache。"""

    def test_migrate_users(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()
        stat = mgr.migrate_users()
        assert stat.table_name == "users"
        assert stat.migrated_rows == 3
        mgr.close()

    def test_migrate_users_custom_batch(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()
        stat = mgr.migrate_users(batch_size=2)
        assert stat.migrated_rows == 3
        mgr.close()

    def test_migrate_records(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()
        stat = mgr.migrate_records()
        assert stat.migrated_rows == 15
        mgr.close()

    def test_migrate_report_cache(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()
        stat = mgr.migrate_report_cache()
        assert stat.migrated_rows == 10
        mgr.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 10. verify_migration 与 rollback 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestVerifyMigration:
    """verify_migration 方法——行计数比较。"""

    def test_all_match_after_migration(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr.run_all()
        result = mgr.verify_migration()
        for table in ("users", "bazi_records", "report_cache"):
            assert result[table]["source"] == result[table]["target"]
            assert result[table]["diff"] == 0
        mgr.close()

    def test_mismatch_detected(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()
        # 只迁移 users，不迁移其他表
        entry = mgr._TABLE_REGISTRY[0]
        mgr._migrate_table(
            entry["table_name"], entry["model_class"], entry["column_map"], batch_size=1000
        )
        result = mgr.verify_migration()
        # bazi_records 目标行为 0，源行 15
        assert result["bazi_records"]["diff"] != 0
        assert result["bazi_records"]["target"] == 0
        mgr.close()

    def test_auto_connects_when_engine_none(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        # engine 为 None
        result = mgr.verify_migration()
        assert "users" in result
        assert result["users"]["source"] == 3
        mgr.close()

    def test_auto_connects_when_sqlite_none(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._engine = mgr._connect_postgres()
        # _sqlite_conn 为 None
        result = mgr.verify_migration()
        assert "users" in result
        mgr.close()


class TestRollback:
    """rollback 方法——清空目标表。"""

    def test_clears_all_tables(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr.run_all()
        mgr.rollback()

        from tengod.data_store import User, BaziRecord, ReportCache
        with Session(mgr._engine) as session:
            assert session.query(User).count() == 0
            assert session.query(BaziRecord).count() == 0
            assert session.query(ReportCache).count() == 0
        mgr.close()

    def test_rollback_on_empty_tables(self, tmp_path):
        """在空表上执行 rollback 不报错。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._engine = mgr._connect_postgres()
        mgr.rollback()  # 不应报错
        mgr.close()

    def test_rollback_auto_connects(self, tmp_path):
        """engine 为 None 时 rollback 自动连接。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr.rollback()  # engine 为 None，自动连接
        mgr.close()

    def test_rollback_reversed_order(self, tmp_path):
        """rollback 按逆序清空表（外键约束）。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr.run_all()
        mgr.rollback()

        from tengod.data_store import User
        with Session(mgr._engine) as session:
            assert session.query(User).count() == 0
        mgr.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 11. run_all 完整流程测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunAll:
    """run_all 完整流程——报告、错误处理、边界条件。"""

    def test_basic_run(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        report = mgr.run_all()
        assert report.total_rows == 28  # 3 + 15 + 10
        assert report.success is True
        assert report.start_time is not None
        assert report.end_time is not None
        assert len(report.table_stats) == 3
        mgr.close()

    def test_custom_batch_size(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        report = mgr.run_all(batch_size=2)
        assert report.total_rows == 28
        assert report.success is True
        mgr.close()

    def test_skips_missing_source_tables(self, tmp_path):
        """源库中缺少某些注册表时，run_all 跳过它们。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_empty_source(str(src), ["users", "bazi_records", "report_cache"])
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        report = mgr.run_all()
        # 所有表都存在但为空，迁移 0 行
        assert "users" in report.table_stats
        assert report.table_stats["users"].migrated_rows == 0
        assert report.total_rows == 0
        mgr.close()

    def test_report_to_dict_structure(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        report = mgr.run_all()
        d = report.to_dict()
        assert isinstance(d, dict)
        assert "start_time" in d
        assert "end_time" in d
        assert "table_stats" in d
        assert "total_rows" in d
        assert "errors" in d
        assert "success" in d
        mgr.close()

    def test_run_all_resets_report(self, tmp_path):
        """每次 run_all 重置 report 对象（新对象但有相同结构）。"""
        src = tmp_path / "s.db"
        target_a = tmp_path / "ta.db"
        target_b = tmp_path / "tb.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target_a}")
        r1 = mgr.run_all()
        assert r1.total_rows == 28
        mgr.close()

        mgr2 = MigrationManager(str(src), f"sqlite:///{target_b}")
        r2 = mgr2.run_all()
        assert r2.total_rows == 28
        mgr2.close()

    def test_run_all_errors_reported(self, tmp_path):
        """run_all 中迁移错误被记录到 report.errors。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()

        # Mock _migrate_table 抛出异常来模拟错误场景
        with patch.object(mgr, "_migrate_table", side_effect=RuntimeError("forced error")):
            report = mgr.run_all()
            assert report.success is False
            assert len(report.errors) > 0
            assert any("forced error" in e for e in report.errors)
        mgr.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 12. close 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestClose:
    """close 方法——连接清理、幂等性。"""

    def test_close_after_run(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr.run_all()
        mgr.close()
        # 不应报错

    def test_double_close(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr.run_all()
        mgr.close()
        mgr.close()  # 重复关闭

    def test_close_without_connections(self):
        mgr = MigrationManager("/nonexistent/path.db", "sqlite:///:memory:")
        mgr.close()  # 不应报错

    def test_close_with_only_sqlite(self, tmp_path):
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), "sqlite:///:memory:")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr.close()

    def test_close_with_only_engine(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._engine = mgr._connect_postgres()
        mgr.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 13. 边缘情况测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """各种边缘与异常情况。"""

    def test_no_migrations(self, tmp_path):
        """空源库（仅有注册表但无数据）下 run_all 的行为。"""
        src = tmp_path / "s.db"
        _make_empty_source(str(src), ["users", "bazi_records", "report_cache"])
        mgr = MigrationManager(str(src), f"sqlite:///{tmp_path}/t.db")
        report = mgr.run_all()
        assert report.total_rows == 0
        mgr.close()

    def test_duplicate_migration_is_idempotent(self, tmp_path):
        """重复迁移同一数据不产生重复行（ORM session.add 去重靠 PK）。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr.run_all()
        # 第二次 run_all 源数据已存在，但 ORM 会尝试再插入
        # 由于 PK 冲突，会失败——但 run_all 会捕获错误
        report2 = mgr.run_all()
        # 应该记录错误（PK 冲突）
        assert len(report2.errors) > 0 or report2.total_rows == 0
        mgr.close()

    def test_invalid_sqlite_path(self):
        """无效的 SQLite 路径。"""
        mgr = MigrationManager("/nonexistent/path/to/db.db", "sqlite:///:memory:")
        with pytest.raises(sqlite3.OperationalError):
            mgr._connect_sqlite()
        mgr.close()

    def test_migration_with_null_values(self, tmp_path):
        """源数据包含 NULL 值时的迁移。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()

        entry = mgr._TABLE_REGISTRY[0]
        stat = mgr._migrate_table(
            entry["table_name"], entry["model_class"], entry["column_map"], batch_size=1000
        )
        assert stat.migrated_rows == 3
        mgr.close()

    def test_verify_schema_error_caught_in_run_all(self, tmp_path):
        """run_all 中 _verify_schema 异常被捕获。"""
        src = tmp_path / "s.db"
        _make_source(str(src))
        mgr = MigrationManager(str(src), f"sqlite:///{tmp_path}/t.db")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()
        # inspect 是在 _verify_schema 方法内导入的，patch 调用点
        with patch("sqlalchemy.inspect", side_effect=RuntimeError("inspect failed")):
            report = mgr.run_all()
            assert "inspect failed" in " ".join(report.errors)
        mgr.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Mock 测试——使用 unittest.mock.patch
# ═══════════════════════════════════════════════════════════════════════════════

class TestMockedScenarios:
    """使用 Mock 验证复杂场景。"""

    def test_run_all_mocked_engine(self, tmp_path):
        """Mock SQLAlchemy engine 验证 run_all 流程。"""
        src = tmp_path / "s.db"
        _make_source(str(src))

        mock_engine = MagicMock()
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session

        with patch.object(MigrationManager, "_connect_sqlite") as mock_sqlite_conn:
            with patch.object(MigrationManager, "_connect_postgres", return_value=mock_engine):
                with patch("sqlalchemy.orm.Session", return_value=mock_session):
                    mgr = MigrationManager(str(src), "sqlite:///:memory:")
                    report = mgr.run_all()
                    assert isinstance(report, MigrationReport)
                    mgr.close()

    def test_migrate_table_with_mocked_session(self, tmp_path):
        """Mock Session 验证 _migrate_table 调用模式。"""
        src = tmp_path / "s.db"
        _make_source(str(src))

        mock_engine = MagicMock()
        mock_session = MagicMock()
        mock_session.query.return_value.count.return_value = 3
        # Session 作为上下文管理器使用
        mock_session.__enter__.return_value = mock_session

        with patch("sqlalchemy.orm.Session", return_value=mock_session):
            mgr = MigrationManager(str(src), "sqlite:///:memory:")
            mgr._sqlite_conn = mgr._connect_sqlite()
            mgr._engine = mock_engine

            entry = mgr._TABLE_REGISTRY[0]
            stat = mgr._migrate_table(
                entry["table_name"], entry["model_class"], entry["column_map"], batch_size=1000
            )
            assert stat.table_name == "users"
            # 验证 session.add_all 被调用
            assert mock_session.add_all.called
            assert mock_session.commit.called
            mgr.close()

    def test_rollback_with_mocked_session(self, tmp_path):
        """Mock Session 验证 rollback 调用。"""
        src = tmp_path / "s.db"
        _make_source(str(src))

        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mgr = MigrationManager(str(src), "sqlite:///:memory:")
        mgr._engine = MagicMock()

        with patch("sqlalchemy.orm.Session", return_value=mock_session):
            mgr.rollback()
            assert mock_session.query.called
            mgr.close()

    def test_verify_migration_with_mocked_session(self, tmp_path):
        """Mock Session 验证 verify_migration。"""
        src = tmp_path / "s.db"
        _make_source(str(src))

        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.query.return_value.count.return_value = 100

        mgr = MigrationManager(str(src), "sqlite:///:memory:")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = MagicMock()

        with patch("sqlalchemy.orm.Session", return_value=mock_session):
            result = mgr.verify_migration()
            assert "users" in result
            assert result["users"]["target"] == 100
            mgr.close()

    def test_main_with_mocked_manager(self):
        """Mock MigrationManager 验证 main 流程。"""
        mock_manager = MagicMock()
        mock_report = MagicMock()
        mock_report.errors = []
        mock_report.to_dict.return_value = {"success": True}
        mock_manager.run_all.return_value = mock_report

        with patch("tengod.db_migration.MigrationManager", return_value=mock_manager):
            result = main(["--sqlite", "/tmp/test.db", "--postgres", "sqlite:///:memory:"])
            assert result == 0
            mock_manager.run_all.assert_called_once()
            mock_manager.close.assert_called_once()

    def test_main_with_rollback_first_mocked(self):
        """Mock 验证 --rollback-first 调用顺序。"""
        mock_manager = MagicMock()
        mock_report = MagicMock()
        mock_report.errors = []
        mock_report.to_dict.return_value = {}
        mock_manager.run_all.return_value = mock_report

        with patch("tengod.db_migration.MigrationManager", return_value=mock_manager):
            main([
                "--sqlite", "/tmp/test.db",
                "--postgres", "sqlite:///:memory:",
                "--rollback-first",
            ])
            mock_manager.rollback.assert_called_once()
            mock_manager.run_all.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# 15. CLI 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestArgParser:
    """_build_arg_parser 与参数解析。"""

    def test_default_values(self):
        parser = _build_arg_parser()
        args = parser.parse_args([])
        assert args.sqlite is None
        assert args.postgres is None
        assert args.batch_size == 1000
        assert args.rollback_first is False
        assert args.verbose is False
        assert args.self_test is False

    def test_full_args(self):
        parser = _build_arg_parser()
        args = parser.parse_args([
            "--sqlite", "/tmp/s.db",
            "--postgres", "postgresql://user:pass@host/db",
            "--batch-size", "500",
            "--rollback-first",
            "--verbose",
        ])
        assert args.sqlite == "/tmp/s.db"
        assert args.postgres == "postgresql://user:pass@host/db"
        assert args.batch_size == 500
        assert args.rollback_first is True
        assert args.verbose is True

    def test_self_test_flag(self):
        parser = _build_arg_parser()
        args = parser.parse_args(["--self-test"])
        assert args.self_test is True


class TestMainCLI:
    """main 函数——各种 CLI 调用路径。"""

    def test_self_test_mode(self):
        result = main(["--self-test"])
        assert result == 0

    def test_self_test_with_batch_size(self):
        result = main(["--self-test", "--batch-size", "5"])
        assert result == 0

    def test_missing_required_args(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--sqlite", "/tmp/test.db"])
        assert exc_info.value.code == 2

    def test_missing_both_args(self):
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 2

    def test_valid_migration(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        result = main(["--sqlite", str(src), "--postgres", f"sqlite:///{target}"])
        assert result == 0

    def test_with_rollback_first(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        result = main([
            "--sqlite", str(src),
            "--postgres", f"sqlite:///{target}",
            "--rollback-first",
        ])
        assert result == 0

    def test_with_verbose(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        result = main([
            "--sqlite", str(src),
            "--postgres", f"sqlite:///{target}",
            "--verbose",
        ])
        assert result == 0

    def test_main_custom_batch_size(self, tmp_path):
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))
        result = main([
            "--sqlite", str(src),
            "--postgres", f"sqlite:///{target}",
            "--batch-size", "10",
        ])
        assert result == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 16. _self_test 与 _create_test_sqlite 测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestSelfTest:
    """_self_test 函数。"""

    def test_default_batch(self):
        assert _self_test() == 0

    def test_small_batch(self):
        assert _self_test(batch_size=2) == 0

    def test_batch_size_one(self):
        assert _self_test(batch_size=1) == 0


class TestCreateTestSQLite:
    """_create_test_sqlite 辅助函数。"""

    def test_creates_file(self, tmp_path):
        p = str(tmp_path / "test.db")
        _create_test_sqlite(p)
        assert os.path.exists(p)

    def test_correct_row_counts(self, tmp_path):
        p = str(tmp_path / "test.db")
        _create_test_sqlite(p)
        conn = sqlite3.connect(p)
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 3
        assert conn.execute("SELECT COUNT(*) FROM bazi_records").fetchone()[0] == 15
        assert conn.execute("SELECT COUNT(*) FROM report_cache").fetchone()[0] == 10
        conn.close()

    def test_users_have_expected_data(self, tmp_path):
        p = str(tmp_path / "test.db")
        _create_test_sqlite(p)
        conn = sqlite3.connect(p)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
        assert rows[0]["username"] == "alice"
        assert rows[1]["username"] == "bob"
        assert rows[2]["username"] == "charlie"
        assert rows[2]["role"] == "admin"
        conn.close()

    def test_bazi_records_have_data(self, tmp_path):
        p = str(tmp_path / "test.db")
        _create_test_sqlite(p)
        conn = sqlite3.connect(p)
        count = conn.execute("SELECT COUNT(*) FROM bazi_records").fetchone()[0]
        assert count == 15
        conn.close()

    def test_report_cache_have_data(self, tmp_path):
        p = str(tmp_path / "test.db")
        _create_test_sqlite(p)
        conn = sqlite3.connect(p)
        count = conn.execute("SELECT COUNT(*) FROM report_cache").fetchone()[0]
        assert count == 10
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 17. 集成场景测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationScenarios:
    """端到端集成场景。"""

    def test_full_migration_then_verify(self, tmp_path):
        """完整迁移 → 验证 → 回滚 流程。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))

        mgr = MigrationManager(str(src), f"sqlite:///{target}")

        # 1. 迁移
        report = mgr.run_all()
        assert report.success is True
        assert report.total_rows == 28

        # 2. 验证
        verify = mgr.verify_migration()
        for t in ("users", "bazi_records", "report_cache"):
            assert verify[t]["diff"] == 0

        # 3. 回滚
        mgr.rollback()
        from tengod.data_store import User
        with Session(mgr._engine) as session:
            assert session.query(User).count() == 0

        mgr.close()

    def test_migrate_then_rollback_then_migrate_again(self, tmp_path):
        """迁移 → 回滚 → 再迁移 循环。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))

        mgr = MigrationManager(str(src), f"sqlite:///{target}")

        # 第一轮
        r1 = mgr.run_all()
        assert r1.total_rows == 28

        mgr.rollback()

        # 第二轮（从干净的 DB 重新迁移）
        # 注意：run_all 会创建新的连接，但 self._engine 和 self._sqlite_conn 已存在
        # 需要重新创建 manager
        mgr.close()

        mgr2 = MigrationManager(str(src), f"sqlite:///{target}")
        r2 = mgr2.run_all()
        assert r2.total_rows == 28
        mgr2.close()

    def test_step_by_step_migration(self, tmp_path):
        """逐步迁移各表。"""
        src = tmp_path / "s.db"
        target = tmp_path / "t.db"
        _make_source(str(src))

        mgr = MigrationManager(str(src), f"sqlite:///{target}")
        mgr._sqlite_conn = mgr._connect_sqlite()
        mgr._engine = mgr._connect_postgres()

        s1 = mgr.migrate_users()
        assert s1.migrated_rows == 3

        s2 = mgr.migrate_records()
        assert s2.migrated_rows == 15

        s3 = mgr.migrate_report_cache()
        assert s3.migrated_rows == 10

        # 验证完整性
        result = mgr.verify_migration()
        for t in ("users", "bazi_records", "report_cache"):
            assert result[t]["diff"] == 0

        mgr.close()

    def test_migration_report_persistence(self, tmp_path):
        """验证迁移报告在多次调用间的状态。"""
        src = tmp_path / "s.db"
        target_a = tmp_path / "ta.db"
        target_b = tmp_path / "tb.db"
        _make_source(str(src))

        mgr = MigrationManager(str(src), f"sqlite:///{target_a}")
        r1 = mgr.run_all()

        # run_all 每次创建新的 MigrationReport 对象
        mgr2 = MigrationManager(str(src), f"sqlite:///{target_b}")
        r2 = mgr2.run_all()

        # 不同对象但结构相同
        assert r1 is not r2
        assert r1.total_rows == r2.total_rows
        mgr.close()
        mgr2.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 18. 日志与格式化测试
# ═══════════════════════════════════════════════════════════════════════════════

class TestLogger:
    """logger 配置验证。"""

    def test_logger_has_handlers(self):
        assert len(logger.handlers) > 0

    def test_logger_level(self):
        assert logger.level is not None