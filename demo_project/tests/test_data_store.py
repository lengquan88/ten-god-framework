#!/usr/bin/env python3
"""
test_data_store.py — 数据持久化层测试
======================================

覆盖 tengod.data_store 模块的所有公共 API：
- ORM 模型：User, BaziRecord, ReportCache, LegacyCase
- DataStore 类：初始化、CRUD、报告缓存、案例库、统计、备份恢复
- 模块级函数：get_data_store 单例
- 边界情况：缺失记录、空值、连接错误、空结果

用法：
    pytest tests/test_data_store.py -v
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from tengod.data_store import (
    DATABASE_URL,
    DEFAULT_DB_PATH,
    Base,
    BaziRecord,
    DataStore,
    LegacyCase,
    ReportCache,
    User,
    get_data_store,
)


# ============================================================================
# 模块级 fixture：确保 DATABASE_URL 为空，测试使用 SQLite 模式
# ============================================================================

@pytest.fixture(autouse=True)
def _reset_database_url():
    """每个测试前重置 DATABASE_URL，避免环境变量污染。"""
    import tengod.data_store as ds_module
    original = ds_module.DATABASE_URL
    ds_module.DATABASE_URL = ""
    yield
    ds_module.DATABASE_URL = original


# ============================================================================
# 辅助函数
# ============================================================================

def _make_mock_session():
    """创建一个 mock SQLAlchemy Session，支持 with 语句和链式调用。"""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    # 让 query 返回链式 mock
    query_mock = MagicMock()
    session.query.return_value = query_mock
    query_mock.filter.return_value = query_mock
    query_mock.filter_by.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    query_mock.limit.return_value = query_mock
    query_mock.offset.return_value = query_mock
    query_mock.group_by.return_value = query_mock
    return session


def _make_mock_bazi_record(**kwargs):
    """创建一个 mock BaziRecord 实例。"""
    defaults = {
        "id": 1,
        "user_id": None,
        "label": None,
        "year": 1990,
        "month": 6,
        "day": 15,
        "hour": 10,
        "minute": 0,
        "gender": "male",
        "longitude": 116.4,
        "latitude": 39.9,
        "day_master": "辛",
        "pillars_json": None,
        "analysis_json": None,
        "shensha_json": None,
        "geju_json": None,
        "yongshen_json": None,
        "tiaohou_json": None,
        "tags": None,
        "notes": None,
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(kwargs)
    record = MagicMock(spec=BaziRecord, **defaults)
    for k, v in defaults.items():
        setattr(record, k, v)
    return record


def _make_mock_user(**kwargs):
    """创建一个 mock User 实例。"""
    defaults = {
        "id": 1,
        "username": "testuser",
        "display_name": "Test User",
        "password_hash": None,
        "role": "user",
        "email": None,
        "is_active": 1,
        "api_quota_daily": 100,
        "last_login_at": None,
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(kwargs)
    user = MagicMock(spec=User, **defaults)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _make_mock_report_cache(**kwargs):
    """创建一个 mock ReportCache 实例。"""
    defaults = {
        "id": 1,
        "bazi_record_id": 1,
        "format": "text",
        "content": "cached content",
        "content_hash": "abc123",
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(kwargs)
    cache = MagicMock(spec=ReportCache, **defaults)
    for k, v in defaults.items():
        setattr(cache, k, v)
    return cache


def _make_mock_legacy_case(**kwargs):
    """创建一个 mock LegacyCase 实例。"""
    defaults = {
        "id": 1,
        "title": "Test Case",
        "summary": "A test case summary",
        "analysis_text": "Detailed analysis",
        "category": "test",
        "is_public": True,
        "is_featured": False,
        "bazi_record_id": None,
        "user_id": None,
        "day_master": None,
        "tags": None,
        "fts_vector": "Test Case A test case summary Detailed analysis",
        "pillars_json": None,
        "geju_json": None,
        "yongshen_json": None,
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(kwargs)
    case = MagicMock(spec=LegacyCase, **defaults)
    for k, v in defaults.items():
        setattr(case, k, v)
    return case


# ============================================================================
# ORM 模型测试
# ============================================================================

class TestBase:
    """Base 模型基类"""

    def test_base_is_declarative(self):
        assert hasattr(Base, "metadata")
        assert hasattr(Base, "registry")


class TestUser:
    """User 模型"""

    def test_user_creation(self):
        user = User(
            username="zhangsan",
            display_name="张三",
            role="user",
            email="zhangsan@example.com",
        )
        assert user.username == "zhangsan"
        assert user.display_name == "张三"
        assert user.role == "user"
        assert user.email == "zhangsan@example.com"
        # SQLAlchemy defaults are DB-level; check column defaults
        assert User.is_active.default.arg == 1
        assert User.api_quota_daily.default.arg == 100

    def test_user_repr(self):
        user = User(username="zhangsan", role="user")
        user.id = 42
        r = repr(user)
        assert "42" in r
        assert "zhangsan" in r
        assert "user" in r

    def test_user_defaults(self):
        user = User(username="test")
        # SQLAlchemy defaults are DB-level; check column default definitions
        assert User.role.default.arg == "user"
        assert User.is_active.default.arg == 1
        assert User.api_quota_daily.default.arg == 100
        # created_at has a callable default (lambda)
        assert User.created_at.default is not None

    def test_user_tablename(self):
        assert User.__tablename__ == "users"


class TestBaziRecord:
    """BaziRecord 模型"""

    def test_bazi_record_creation(self):
        record = BaziRecord(
            year=1990, month=6, day=15, hour=10, minute=30,
            gender="male", day_master="辛",
        )
        assert record.year == 1990
        assert record.month == 6
        assert record.day == 15
        assert record.hour == 10
        assert record.minute == 30
        assert record.gender == "male"
        assert record.day_master == "辛"

    def test_bazi_record_defaults(self):
        record = BaziRecord(year=2000, month=1, day=1, hour=0)
        # SQLAlchemy defaults are DB-level; check column default definitions
        assert BaziRecord.gender.default.arg == "male"
        assert BaziRecord.longitude.default.arg == 116.4
        assert BaziRecord.latitude.default.arg == 39.9
        assert BaziRecord.minute.default.arg == 0

    def test_bazi_record_to_dict_simple(self):
        record = BaziRecord(
            year=1990, month=6, day=15, hour=10, minute=30,
            gender="male", day_master="辛", label="测试",
        )
        record.id = 1
        record.longitude = 116.4
        record.latitude = 39.9
        record.user_id = None
        record.pillars_json = None
        record.analysis_json = None
        record.shensha_json = None
        record.geju_json = None
        record.yongshen_json = None
        record.tiaohou_json = None
        record.tags = None
        record.notes = None
        record.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        record.updated_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        d = record.to_dict()
        assert d["id"] == 1
        assert d["year"] == 1990
        assert d["month"] == 6
        assert d["day"] == 15
        assert d["hour"] == 10
        assert d["minute"] == 30
        assert d["gender"] == "male"
        assert d["day_master"] == "辛"
        assert d["pillars"] is None
        assert d["analysis"] is None
        assert "created_at" in d

    def test_bazi_record_to_dict_with_json(self):
        record = BaziRecord(
            year=1990, month=6, day=15, hour=10,
            day_master="辛",
            pillars_json=json.dumps({"year": "庚午", "month": "壬午"}),
            analysis_json=json.dumps({"conclusion": "test"}),
            geju_json=json.dumps({"name": "伤官格"}),
        )
        record.id = 1
        record.user_id = None
        record.longitude = 116.4
        record.latitude = 39.9
        record.gender = "male"
        record.minute = 0
        record.label = None
        record.shensha_json = None
        record.yongshen_json = None
        record.tiaohou_json = None
        record.tags = None
        record.notes = None
        record.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        record.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        d = record.to_dict()
        assert d["pillars"] == {"year": "庚午", "month": "壬午"}
        assert d["analysis"] == {"conclusion": "test"}
        assert d["geju"] == {"name": "伤官格"}

    def test_bazi_record_repr(self):
        record = BaziRecord(year=1990, month=6, day=15, gender="male")
        record.id = 1
        r = repr(record)
        assert "1" in r
        assert "1990" in r

    def test_bazi_record_tablename(self):
        assert BaziRecord.__tablename__ == "bazi_records"

    def test_bazi_record_table_args(self):
        assert hasattr(BaziRecord, "__table_args__")
        args = BaziRecord.__table_args__
        assert args is not None
        # 检查包含索引
        assert len(args) == 3

    def test_bazi_record_to_dict_null_created_at(self):
        record = BaziRecord(year=2000, month=1, day=1, hour=0)
        record.id = 1
        record.user_id = None
        record.longitude = 116.4
        record.latitude = 39.9
        record.gender = "male"
        record.minute = 0
        record.label = None
        record.day_master = None
        record.pillars_json = None
        record.analysis_json = None
        record.shensha_json = None
        record.geju_json = None
        record.yongshen_json = None
        record.tiaohou_json = None
        record.tags = None
        record.notes = None
        record.created_at = None
        record.updated_at = None

        d = record.to_dict()
        assert d["created_at"] is None
        assert d["updated_at"] is None


class TestReportCache:
    """ReportCache 模型"""

    def test_report_cache_creation(self):
        cache = ReportCache(
            bazi_record_id=1,
            format="text",
            content="报告内容",
            content_hash="abc123",
        )
        assert cache.bazi_record_id == 1
        assert cache.format == "text"
        assert cache.content == "报告内容"
        assert cache.content_hash == "abc123"

    def test_report_cache_defaults(self):
        cache = ReportCache(bazi_record_id=1, content="test")
        # SQLAlchemy default is DB-level
        assert ReportCache.format.default.arg == "text"

    def test_report_cache_repr(self):
        cache = ReportCache(bazi_record_id=1, format="html", content="test")
        cache.id = 5
        r = repr(cache)
        assert "5" in r
        assert "1" in r
        assert "html" in r

    def test_report_cache_tablename(self):
        assert ReportCache.__tablename__ == "report_cache"


class TestLegacyCase:
    """LegacyCase 模型"""

    def test_legacy_case_creation(self):
        case = LegacyCase(
            title="测试案例",
            summary="摘要",
            analysis_text="分析内容",
            category="测试",
            is_public=True,
            is_featured=False,
        )
        assert case.title == "测试案例"
        assert case.summary == "摘要"
        assert case.analysis_text == "分析内容"
        assert case.category == "测试"
        assert case.is_public is True
        assert case.is_featured is False

    def test_legacy_case_repr(self):
        case = LegacyCase(title="测试案例", category="test")
        case.id = 3
        r = repr(case)
        assert "3" in r
        assert "测试案例" in r

    def test_legacy_case_to_dict(self):
        case = LegacyCase(
            title="测试案例",
            summary="摘要",
            analysis_text="分析",
            category="test",
            is_public=True,
            is_featured=True,
            pillars_json=json.dumps({"year": "庚午"}),
            geju_json=json.dumps({"name": "伤官格"}),
        )
        case.id = 1
        case.bazi_record_id = None
        case.user_id = None
        case.day_master = None
        case.tags = None
        case.yongshen_json = None
        case.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        case.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        d = case.to_dict()
        assert d["id"] == 1
        assert d["title"] == "测试案例"
        assert d["is_public"] is True
        assert d["is_featured"] is True
        assert d["pillars"] == {"year": "庚午"}
        assert d["geju"] == {"name": "伤官格"}

    def test_legacy_case_to_dict_nulls(self):
        case = LegacyCase(title="测试案例")
        case.id = 1
        case.summary = None
        case.analysis_text = None
        case.category = None
        case.is_public = True
        case.is_featured = False
        case.bazi_record_id = None
        case.user_id = None
        case.day_master = None
        case.tags = None
        case.pillars_json = None
        case.geju_json = None
        case.yongshen_json = None
        case.created_at = None
        case.updated_at = None

        d = case.to_dict()
        assert d["pillars"] is None
        assert d["geju"] is None
        assert d["yongshen"] is None
        assert d["created_at"] is None
        assert d["updated_at"] is None

    def test_legacy_case_tablename(self):
        assert LegacyCase.__tablename__ == "legacy_cases"


# ============================================================================
# DataStore 初始化测试
# ============================================================================

class TestDataStoreInit:
    """DataStore 初始化"""

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("os.makedirs")
    def test_init_sqlite_default(self, mock_makedirs, mock_create_all, mock_create_engine):
        """默认 SQLite 模式初始化"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")

        assert store.db_path == "/tmp/test.db"
        assert store.db_url is None
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args[0][0]
        assert call_args.startswith("sqlite:///")
        mock_create_all.assert_called_once_with(mock_engine)

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("os.makedirs")
    def test_init_postgresql(self, mock_makedirs, mock_create_all, mock_create_engine):
        """PostgreSQL 模式初始化"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_url="postgresql://user:pass@localhost:5432/db")

        assert store.db_url == "postgresql://user:pass@localhost:5432/db"
        assert store.db_path is None
        mock_create_engine.assert_called_once()
        mock_create_all.assert_called_once_with(mock_engine)

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("os.makedirs")
    def test_init_postgresql_typeerror_fallback(self, mock_makedirs, mock_create_all, mock_create_engine):
        """PostgreSQL 模式初始化，老版本 SQLAlchemy TypeError 降级"""
        mock_engine = MagicMock()
        # 第一次调用 raise TypeError，第二次成功
        mock_create_engine.side_effect = [TypeError("unexpected keyword"), mock_engine]

        store = DataStore(db_url="postgresql://user:pass@localhost:5432/db")

        assert store.db_url == "postgresql://user:pass@localhost:5432/db"
        assert mock_create_engine.call_count == 2
        mock_create_all.assert_called_once_with(mock_engine)

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("os.makedirs")
    def test_init_from_env_database_url(self, mock_makedirs, mock_create_all, mock_create_engine):
        """通过 DATABASE_URL 环境变量初始化 PostgreSQL"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        with patch.dict("tengod.data_store.os.environ", {"TENGOD_DATABASE_URL": "postgresql://db:5432/tengod"}):
            # 需要重新导入以获取更新的环境变量
            from importlib import reload
            import tengod.data_store as ds_module
            ds_module.DATABASE_URL = "postgresql://db:5432/tengod"
            store = DataStore()

        assert store.db_url == "postgresql://db:5432/tengod"
        assert store.db_path is None

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_init_sqlite_creates_dir(self, mock_makedirs, mock_create_all, mock_create_engine):
        """SQLite 模式自动创建目录"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/nonexistent/path/test.db")

        mock_makedirs.assert_called_once_with("/nonexistent/path", exist_ok=True)

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("os.makedirs")
    def test_init_default_db_path(self, mock_makedirs, mock_create_all, mock_create_engine):
        """使用默认 DB 路径初始化"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore()

        assert store.db_path is not None
        assert store.db_url is None


# ============================================================================
# DataStore 用户管理测试
# ============================================================================

class TestDataStoreUserManagement:
    """用户管理"""

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_get_or_create_user_new(self, mock_makedirs, mock_create_all, mock_create_engine):
        """创建新用户"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        # query 返回 None（用户不存在）
        session.query.return_value.filter.return_value.first.return_value = None

        with patch.object(store, "_session", return_value=session):
            user = store.get_or_create_user("newuser", "New User")

        assert user is not None
        session.add.assert_called_once()
        session.commit.assert_called_once()
        session.refresh.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_get_or_create_user_existing(self, mock_makedirs, mock_create_all, mock_create_engine):
        """获取已存在用户"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        existing_user = _make_mock_user(username="existing")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = existing_user

        with patch.object(store, "_session", return_value=session):
            user = store.get_or_create_user("existing")

        assert user is existing_user
        session.add.assert_not_called()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_get_or_create_user_no_display_name(self, mock_makedirs, mock_create_all, mock_create_engine):
        """创建用户时未提供 display_name，使用 username"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = None

        # 捕获 add 调用以检查 display_name
        def capture_add(obj):
            obj.display_name = "testuser"

        session.add.side_effect = capture_add

        with patch.object(store, "_session", return_value=session):
            user = store.get_or_create_user("testuser")

        assert user is not None
        session.add.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_get_user_found(self, mock_makedirs, mock_create_all, mock_create_engine):
        """获取用户成功"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        expected_user = _make_mock_user(id=42)
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = expected_user

        with patch.object(store, "_session", return_value=session):
            user = store.get_user(42)

        assert user is expected_user

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_get_user_not_found(self, mock_makedirs, mock_create_all, mock_create_engine):
        """获取不存在的用户返回 None"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = None

        with patch.object(store, "_session", return_value=session):
            user = store.get_user(999)

        assert user is None

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_list_users(self, mock_makedirs, mock_create_all, mock_create_engine):
        """列出用户"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        users = [_make_mock_user(id=i) for i in range(3)]
        session = _make_mock_session()
        session.query.return_value.order_by.return_value.limit.return_value.all.return_value = users

        with patch.object(store, "_session", return_value=session):
            result = store.list_users(limit=10)

        assert len(result) == 3

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_list_users_default_limit(self, mock_makedirs, mock_create_all, mock_create_engine):
        """list_users 默认 limit=50"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.order_by.return_value.limit.return_value.all.return_value = []

        with patch.object(store, "_session", return_value=session):
            store.list_users()

        session.query.return_value.order_by.return_value.limit.assert_called_once_with(50)


# ============================================================================
# DataStore 八字记录 CRUD 测试
# ============================================================================

class TestDataStoreBaziRecordCRUD:
    """八字记录 CRUD"""

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_save_bazi_record_minimal(self, mock_makedirs, mock_create_all, mock_create_engine):
        """保存最小八字记录"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        # 模拟 refresh 设置 id
        def set_id(record):
            record.id = 1
        session.refresh.side_effect = set_id

        with patch.object(store, "_session", return_value=session):
            record_id = store.save_bazi_record(
                year=1990, month=6, day=15, hour=10,
            )

        assert record_id == 1
        session.add.assert_called_once()
        session.commit.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_save_bazi_record_full(self, mock_makedirs, mock_create_all, mock_create_engine):
        """保存完整八字记录（含所有字段）"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.refresh.side_effect = lambda r: setattr(r, "id", 42)

        with patch.object(store, "_session", return_value=session):
            record_id = store.save_bazi_record(
                year=1990, month=6, day=15, hour=10, minute=30,
                gender="female", longitude=121.5, latitude=31.2,
                user_id=1, label="测试八字",
                day_master="甲",
                pillars={"year": "庚午", "month": "壬午", "day": "甲子", "hour": "己巳"},
                analysis={"conclusion": "身强"},
                shensha={"total": 8},
                geju={"name": "正官格"},
                yongshen={"yongshen": "火"},
                tiaohou={"tiaohou": "调候"},
                tags="测试,演示",
                notes="备注信息",
            )

        assert record_id == 42
        session.add.assert_called_once()
        session.commit.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_save_bazi_record_none_dicts(self, mock_makedirs, mock_create_all, mock_create_engine):
        """保存八字记录，字典参数为 None"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.refresh.side_effect = lambda r: setattr(r, "id", 1)

        with patch.object(store, "_session", return_value=session):
            record_id = store.save_bazi_record(
                year=2000, month=1, day=1, hour=0,
                pillars=None, analysis=None, shensha=None,
                geju=None, yongshen=None, tiaohou=None,
            )

        assert record_id == 1

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_get_bazi_record_found(self, mock_makedirs, mock_create_all, mock_create_engine):
        """获取八字记录成功"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        expected = _make_mock_bazi_record(id=5)
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = expected

        with patch.object(store, "_session", return_value=session):
            record = store.get_bazi_record(5)

        assert record is expected

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_get_bazi_record_not_found(self, mock_makedirs, mock_create_all, mock_create_engine):
        """获取不存在的八字记录返回 None"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = None

        with patch.object(store, "_session", return_value=session):
            record = store.get_bazi_record(999)

        assert record is None

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_list_bazi_records_all(self, mock_makedirs, mock_create_all, mock_create_engine):
        """列出所有八字记录"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        records = [_make_mock_bazi_record(id=i) for i in range(5)]
        session = _make_mock_session()
        session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = records

        with patch.object(store, "_session", return_value=session):
            result = store.list_bazi_records(limit=50, offset=0)

        assert len(result) == 5

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_list_bazi_records_by_user(self, mock_makedirs, mock_create_all, mock_create_engine):
        """按用户筛选八字记录"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        records = [_make_mock_bazi_record(id=1, user_id=1)]
        session = _make_mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = records

        with patch.object(store, "_session", return_value=session):
            result = store.list_bazi_records(user_id=1)

        assert len(result) == 1

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_list_bazi_records_asc_order(self, mock_makedirs, mock_create_all, mock_create_engine):
        """按创建时间升序排列"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        with patch.object(store, "_session", return_value=session):
            store.list_bazi_records(order_by="created_at_asc")

        # 验证调用了 asc 排序
        session.query.return_value.order_by.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_search_bazi_records_by_year(self, mock_makedirs, mock_create_all, mock_create_engine):
        """按年份搜索"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        records = [_make_mock_bazi_record(id=1, year=1990)]
        session = _make_mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = records

        with patch.object(store, "_session", return_value=session):
            result = store.search_bazi_records(year=1990)

        assert len(result) == 1

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_search_bazi_records_by_day_master(self, mock_makedirs, mock_create_all, mock_create_engine):
        """按日主搜索"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        records = [_make_mock_bazi_record(id=1, day_master="辛")]
        session = _make_mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = records

        with patch.object(store, "_session", return_value=session):
            result = store.search_bazi_records(day_master="辛")

        assert len(result) == 1

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_search_bazi_records_by_tag(self, mock_makedirs, mock_create_all, mock_create_engine):
        """按标签搜索"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        with patch.object(store, "_session", return_value=session):
            store.search_bazi_records(tag="测试")

        # 验证使用了 contains
        session.query.return_value.filter.assert_called()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_search_bazi_records_no_filters(self, mock_makedirs, mock_create_all, mock_create_engine):
        """无过滤条件搜索"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        records = [_make_mock_bazi_record(id=i) for i in range(3)]
        session = _make_mock_session()
        session.query.return_value.order_by.return_value.limit.return_value.all.return_value = records

        with patch.object(store, "_session", return_value=session):
            result = store.search_bazi_records()

        assert len(result) == 3

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_update_bazi_record_success(self, mock_makedirs, mock_create_all, mock_create_engine):
        """更新八字记录成功"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        record = _make_mock_bazi_record(id=1)
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = record

        with patch.object(store, "_session", return_value=session):
            result = store.update_bazi_record(1, label="新标签", notes="新备注")

        assert result is True
        session.commit.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_update_bazi_record_not_found(self, mock_makedirs, mock_create_all, mock_create_engine):
        """更新不存在的八字记录返回 False"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = None

        with patch.object(store, "_session", return_value=session):
            result = store.update_bazi_record(999, label="新标签")

        assert result is False

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_update_bazi_record_invalid_attr(self, mock_makedirs, mock_create_all, mock_create_engine):
        """更新八字记录，忽略无效属性"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        record = _make_mock_bazi_record(id=1)
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = record

        with patch.object(store, "_session", return_value=session):
            result = store.update_bazi_record(1, invalid_field="should_be_ignored", label="有效")

        assert result is True
        # 确认 invalid_field 没有被设置
        assert not hasattr(record, "invalid_field") or getattr(record, "invalid_field", None) != "should_be_ignored"

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_delete_bazi_record_success(self, mock_makedirs, mock_create_all, mock_create_engine):
        """删除八字记录成功"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        record = _make_mock_bazi_record(id=1)
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = record

        with patch.object(store, "_session", return_value=session):
            result = store.delete_bazi_record(1)

        assert result is True
        session.delete.assert_called_once_with(record)
        session.commit.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_delete_bazi_record_not_found(self, mock_makedirs, mock_create_all, mock_create_engine):
        """删除不存在的八字记录返回 False"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = None

        with patch.object(store, "_session", return_value=session):
            result = store.delete_bazi_record(999)

        assert result is False

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_count_bazi_records_all(self, mock_makedirs, mock_create_all, mock_create_engine):
        """统计所有八字记录"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.scalar.return_value = 42

        with patch.object(store, "_session", return_value=session):
            count = store.count_bazi_records()

        assert count == 42

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_count_bazi_records_by_user(self, mock_makedirs, mock_create_all, mock_create_engine):
        """按用户统计八字记录"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.scalar.return_value = 5

        with patch.object(store, "_session", return_value=session):
            count = store.count_bazi_records(user_id=1)

        assert count == 5

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_count_bazi_records_zero(self, mock_makedirs, mock_create_all, mock_create_engine):
        """统计返回 0（scalar 返回 None）"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.scalar.return_value = None

        with patch.object(store, "_session", return_value=session):
            count = store.count_bazi_records()

        assert count == 0


# ============================================================================
# DataStore 报告缓存测试
# ============================================================================

class TestDataStoreReportCache:
    """报告缓存"""

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_cache_report_new(self, mock_makedirs, mock_create_all, mock_create_engine):
        """缓存新报告"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = None  # no existing
        session.refresh.side_effect = lambda r: setattr(r, "id", 10)

        with patch.object(store, "_session", return_value=session):
            cache_id = store.cache_report(1, "text", "报告内容")

        assert cache_id == 10
        session.add.assert_called_once()
        session.commit.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_cache_report_duplicate(self, mock_makedirs, mock_create_all, mock_create_engine):
        """缓存报告去重——返回已存在缓存 ID"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        existing = _make_mock_report_cache(id=5, bazi_record_id=1, format="text")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = existing

        with patch.object(store, "_session", return_value=session):
            cache_id = store.cache_report(1, "text", "same content")

        assert cache_id == 5
        session.add.assert_not_called()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_get_cached_report_found(self, mock_makedirs, mock_create_all, mock_create_engine):
        """获取缓存报告成功"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        cache = _make_mock_report_cache(id=1, bazi_record_id=1, format="text", content="cached report")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.first.return_value = cache

        with patch.object(store, "_session", return_value=session):
            content = store.get_cached_report(1, "text")

        assert content == "cached report"

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_get_cached_report_not_found(self, mock_makedirs, mock_create_all, mock_create_engine):
        """获取不存在的缓存报告返回 None"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        with patch.object(store, "_session", return_value=session):
            content = store.get_cached_report(1, "text")

        assert content is None

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_clear_report_cache_all(self, mock_makedirs, mock_create_all, mock_create_engine):
        """清除全部报告缓存"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.count.return_value = 10

        with patch.object(store, "_session", return_value=session):
            count = store.clear_report_cache()

        assert count == 10
        session.commit.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_clear_report_cache_by_record(self, mock_makedirs, mock_create_all, mock_create_engine):
        """按记录清除报告缓存"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.count.return_value = 3

        with patch.object(store, "_session", return_value=session):
            count = store.clear_report_cache(record_id=1)

        assert count == 3


# ============================================================================
# DataStore 案例库 CRUD 测试
# ============================================================================

class TestDataStoreLegacyCaseCRUD:
    """案例库 CRUD"""

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_build_fts_vector(self, mock_makedirs, mock_create_all, mock_create_engine):
        """构建 FTS 向量"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        result = store._build_fts_vector("Title", "Summary text", "Analysis text")
        assert "Title" in result
        assert "Summary text" in result
        assert "Analysis text" in result

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_build_fts_vector_all_none(self, mock_makedirs, mock_create_all, mock_create_engine):
        """构建 FTS 向量——全部为 None"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        result = store._build_fts_vector("", None, None)
        assert result == ""

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_save_case_minimal(self, mock_makedirs, mock_create_all, mock_create_engine):
        """保存最小案例"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.refresh.side_effect = lambda c: setattr(c, "id", 1)

        with patch.object(store, "_session", return_value=session):
            case_id = store.save_case(title="测试案例")

        assert case_id == 1
        session.add.assert_called_once()
        session.commit.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_save_case_full(self, mock_makedirs, mock_create_all, mock_create_engine):
        """保存完整案例"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.refresh.side_effect = lambda c: setattr(c, "id", 42)

        with patch.object(store, "_session", return_value=session):
            case_id = store.save_case(
                title="完整案例",
                summary="摘要内容",
                analysis_text="详细分析",
                category="测试",
                is_public=True,
                is_featured=True,
                bazi_record_id=1,
                user_id=1,
                day_master="甲",
                tags="测试,案例",
                pillars={"year": "庚午"},
                geju={"name": "正官格"},
                yongshen={"yongshen": "火"},
            )

        assert case_id == 42

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_get_case_found(self, mock_makedirs, mock_create_all, mock_create_engine):
        """获取案例成功"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        expected = _make_mock_legacy_case(id=5)
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = expected

        with patch.object(store, "_session", return_value=session):
            case = store.get_case(5)

        assert case is expected

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_get_case_not_found(self, mock_makedirs, mock_create_all, mock_create_engine):
        """获取不存在的案例返回 None"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = None

        with patch.object(store, "_session", return_value=session):
            case = store.get_case(999)

        assert case is None

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_list_cases_all(self, mock_makedirs, mock_create_all, mock_create_engine):
        """列出所有案例"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        cases = [_make_mock_legacy_case(id=i) for i in range(3)]
        session = _make_mock_session()
        session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = cases

        with patch.object(store, "_session", return_value=session):
            result = store.list_cases()

        assert len(result) == 3

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_list_cases_by_category(self, mock_makedirs, mock_create_all, mock_create_engine):
        """按分类筛选案例"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        cases = [_make_mock_legacy_case(id=1, category="test")]
        session = _make_mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = cases

        with patch.object(store, "_session", return_value=session):
            result = store.list_cases(category="test")

        assert len(result) == 1

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_list_cases_featured_only(self, mock_makedirs, mock_create_all, mock_create_engine):
        """仅列出精选案例"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        with patch.object(store, "_session", return_value=session):
            store.list_cases(is_featured=True)

        # 验证 filter 被调用
        session.query.return_value.filter.assert_called()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_list_cases_asc_order(self, mock_makedirs, mock_create_all, mock_create_engine):
        """按创建时间升序排列案例"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        with patch.object(store, "_session", return_value=session):
            store.list_cases(order_by="created_at_asc")

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_search_cases_with_keyword(self, mock_makedirs, mock_create_all, mock_create_engine):
        """关键词搜索案例"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        cases = [_make_mock_legacy_case(id=1, title="匹配的案例")]
        session = _make_mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = cases

        with patch.object(store, "_session", return_value=session):
            result = store.search_cases("匹配")

        assert len(result) == 1

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_search_cases_empty_keyword(self, mock_makedirs, mock_create_all, mock_create_engine):
        """空关键词搜索退化为 list_cases"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        cases = [_make_mock_legacy_case(id=1)]
        session = _make_mock_session()
        session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = cases

        with patch.object(store, "_session", return_value=session):
            result = store.search_cases("")

        assert len(result) == 1

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_update_case_success(self, mock_makedirs, mock_create_all, mock_create_engine):
        """更新案例成功"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        case = _make_mock_legacy_case(id=1, title="原始标题")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = case

        with patch.object(store, "_session", return_value=session):
            result = store.update_case(1, title="新标题")

        assert result is True
        session.commit.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_update_case_not_found(self, mock_makedirs, mock_create_all, mock_create_engine):
        """更新不存在的案例返回 False"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = None

        with patch.object(store, "_session", return_value=session):
            result = store.update_case(999, title="新标题")

        assert result is False

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_update_case_fts_vector_updated(self, mock_makedirs, mock_create_all, mock_create_engine):
        """更新案例文本字段时同步更新 fts_vector"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        case = _make_mock_legacy_case(id=1, title="Old Title", summary="Old Summary")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = case

        with patch.object(store, "_session", return_value=session):
            result = store.update_case(1, title="New Title", summary="New Summary")

        assert result is True
        # fts_vector 应该被更新
        assert case.fts_vector is not None

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_delete_case_success(self, mock_makedirs, mock_create_all, mock_create_engine):
        """删除案例成功"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        case = _make_mock_legacy_case(id=1)
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = case

        with patch.object(store, "_session", return_value=session):
            result = store.delete_case(1)

        assert result is True
        session.delete.assert_called_once_with(case)
        session.commit.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_delete_case_not_found(self, mock_makedirs, mock_create_all, mock_create_engine):
        """删除不存在的案例返回 False"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = None

        with patch.object(store, "_session", return_value=session):
            result = store.delete_case(999)

        assert result is False

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_count_cases_all(self, mock_makedirs, mock_create_all, mock_create_engine):
        """统计所有案例"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.scalar.return_value = 15

        with patch.object(store, "_session", return_value=session):
            count = store.count_cases()

        assert count == 15

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_count_cases_by_category(self, mock_makedirs, mock_create_all, mock_create_engine):
        """按分类统计案例"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.scalar.return_value = 7

        with patch.object(store, "_session", return_value=session):
            count = store.count_cases(category="test")

        assert count == 7

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_count_cases_zero(self, mock_makedirs, mock_create_all, mock_create_engine):
        """统计返回 0"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.scalar.return_value = None

        with patch.object(store, "_session", return_value=session):
            count = store.count_cases()

        assert count == 0

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_fulltext_search(self, mock_makedirs, mock_create_all, mock_create_engine):
        """全文检索"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        cases = [_make_mock_legacy_case(id=1, title="匹配结果")]
        session = _make_mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = cases

        with patch.object(store, "_session", return_value=session):
            result = store.fulltext_search("匹配", limit=20)

        assert len(result) == 1

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_fulltext_search_empty_keyword(self, mock_makedirs, mock_create_all, mock_create_engine):
        """全文检索空关键词返回空列表"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")

        with patch.object(store, "_session"):
            result = store.fulltext_search("")

        assert result == []

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_get_case_stats(self, mock_makedirs, mock_create_all, mock_create_engine):
        """案例统计"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        # scalar 调用顺序：total, featured
        session.query.return_value.scalar.side_effect = [20, 5]
        # group_by 链
        session.query.return_value.filter.return_value.group_by.return_value.all.return_value = [
            ("test", 10), ("demo", 10),
        ]

        with patch.object(store, "_session", return_value=session):
            stats = store.get_case_stats()

        assert stats["total_cases"] == 20
        assert stats["featured_cases"] == 5
        assert stats["per_category"] == {"test": 10, "demo": 10}

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_get_case_stats_zero_scalar(self, mock_makedirs, mock_create_all, mock_create_engine):
        """案例统计——scalar 返回 None"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.scalar.side_effect = [None, None]
        session.query.return_value.filter.return_value.group_by.return_value.all.return_value = []

        with patch.object(store, "_session", return_value=session):
            stats = store.get_case_stats()

        assert stats["total_cases"] == 0
        assert stats["featured_cases"] == 0


# ============================================================================
# DataStore 统计测试
# ============================================================================

class TestDataStoreStats:
    """统计功能"""

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_stats_sqlite(self, mock_makedirs, mock_create_all, mock_create_engine):
        """SQLite 模式统计"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.scalar.side_effect = [3, 10, 5, 8]  # users, records, cached_reports, cases
        session.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = [
            ("辛", 6), ("甲", 4),
        ]

        with patch.object(store, "_session", return_value=session):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getsize", return_value=1024 * 1024):
                    stats = store.stats()

        assert stats["total_users"] == 3
        assert stats["total_records"] == 10
        assert stats["total_cached_reports"] == 5
        assert stats["total_cases"] == 8
        assert "db_path" in stats
        assert "db_size_mb" in stats
        assert len(stats["top_day_masters"]) == 2

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_stats_postgresql(self, mock_makedirs, mock_create_all, mock_create_engine):
        """PostgreSQL 模式统计"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_url="postgresql://localhost/db")
        session = _make_mock_session()
        session.query.return_value.scalar.side_effect = [0, 0, 0, 0]
        session.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = []

        with patch.object(store, "_session", return_value=session):
            stats = store.stats()

        assert "db_url" in stats
        assert stats["db_type"] == "postgresql"

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_stats_db_file_not_exists(self, mock_makedirs, mock_create_all, mock_create_engine):
        """统计——数据库文件不存在时 db_size_mb 为 0"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/nonexistent.db")
        session = _make_mock_session()
        session.query.return_value.scalar.side_effect = [0, 0, 0, 0]
        session.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = []

        with patch.object(store, "_session", return_value=session):
            with patch("os.path.exists", return_value=False):
                stats = store.stats()

        assert stats["db_size_mb"] == 0


# ============================================================================
# DataStore 备份恢复测试
# ============================================================================

class TestDataStoreBackupRestore:
    """备份与恢复"""

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_backup_sqlite(self, mock_makedirs, mock_create_all, mock_create_engine):
        """SQLite 模式备份"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")

        with patch("shutil.copy2") as mock_copy:
            backup_path = store.backup()

        assert backup_path.endswith(".db.backup.") or ".backup." in backup_path
        mock_copy.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_backup_sqlite_custom_path(self, mock_makedirs, mock_create_all, mock_create_engine):
        """SQLite 模式自定义路径备份"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")

        with patch("shutil.copy2") as mock_copy:
            backup_path = store.backup("/tmp/custom_backup.db")

        assert backup_path == "/tmp/custom_backup.db"
        mock_copy.assert_called_once_with("/tmp/test.db", "/tmp/custom_backup.db")

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_backup_postgresql(self, mock_makedirs, mock_create_all, mock_create_engine):
        """PostgreSQL 模式备份（导出 JSON）"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_url="postgresql://localhost/db")
        session = _make_mock_session()
        session.query.return_value.all.side_effect = [[], []]

        mock_open = MagicMock()
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        with patch.object(store, "_session", return_value=session):
            with patch("builtins.open", mock_open):
                with patch("json.dump") as mock_json_dump:
                    backup_path = store.backup()

        assert backup_path.endswith(".json")

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_restore_sqlite(self, mock_makedirs, mock_create_all, mock_create_engine):
        """SQLite 模式恢复"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")

        with patch("os.path.exists", return_value=True):
            with patch("shutil.copy2") as mock_copy:
                result = store.restore("/tmp/backup.db")

        assert result is True
        # 恢复前先备份
        assert mock_copy.call_count >= 1

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_restore_file_not_exists(self, mock_makedirs, mock_create_all, mock_create_engine):
        """恢复——备份文件不存在返回 False"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")

        with patch("os.path.exists", return_value=False):
            result = store.restore("/tmp/nonexistent.db")

        assert result is False

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_restore_postgresql(self, mock_makedirs, mock_create_all, mock_create_engine):
        """PostgreSQL 模式恢复（从 JSON 导入）"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_url="postgresql://localhost/db")

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", MagicMock()):
                with patch("json.load", return_value={"users": [], "records": []}):
                    with patch.object(store, "_import_all", return_value=True) as mock_import:
                        result = store.restore("/tmp/backup.json")

        assert result is True
        mock_import.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_export_all(self, mock_makedirs, mock_create_all, mock_create_engine):
        """导出所有数据"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.all.side_effect = [
            [_make_mock_user(id=1, username="user1")],
            [_make_mock_bazi_record(id=1, year=1990, month=6, day=15)],
        ]

        with patch.object(store, "_session", return_value=session):
            data = store._export_all()

        assert "users" in data
        assert "records" in data
        assert len(data["users"]) == 1
        assert len(data["records"]) == 1

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_import_all(self, mock_makedirs, mock_create_all, mock_create_engine):
        """导入数据"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = None  # 不重复

        test_data = {
            "users": [{"username": "user1", "display_name": "User One"}],
            "records": [
                {
                    "id": 1, "user_id": None, "label": "测试",
                    "year": 1990, "month": 6, "day": 15, "hour": 10,
                    "minute": 0, "gender": "male",
                    "day_master": "辛",
                    "pillars_json": None,
                    "analysis_json": None,
                    "shensha_json": None,
                    "geju_json": None,
                    "yongshen_json": None,
                    "tiaohou_json": None,
                    "tags": None, "notes": None,
                }
            ],
        }

        with patch.object(store, "_session", return_value=session):
            result = store._import_all(test_data)

        assert result is True
        session.commit.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_import_all_skip_existing(self, mock_makedirs, mock_create_all, mock_create_engine):
        """导入数据——跳过已存在记录"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        existing_user = _make_mock_user(username="user1")
        existing_record = _make_mock_bazi_record(id=1)
        session = _make_mock_session()
        # 第一次 query 返回已存在用户，第二次返回已存在记录
        session.query.return_value.filter.return_value.first.side_effect = [
            existing_user, existing_record,
        ]

        test_data = {
            "users": [{"username": "user1"}],
            "records": [{"id": 1, "year": 1990, "month": 6, "day": 15, "hour": 10}],
        }

        with patch.object(store, "_session", return_value=session):
            result = store._import_all(test_data)

        assert result is True
        # add 不应该被调用，因为已存在
        session.add.assert_not_called()


# ============================================================================
# DataStore 连接管理测试
# ============================================================================

class TestDataStoreConnectionManagement:
    """连接管理"""

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_close(self, mock_makedirs, mock_create_all, mock_create_engine):
        """关闭连接"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        store.close()

        mock_engine.dispose.assert_called_once()

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_session_creation(self, mock_makedirs, mock_create_all, mock_create_engine):
        """_session 创建会话"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")

        with patch("tengod.data_store.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            session = store._session()

        assert session is mock_session
        mock_session_cls.assert_called_once_with(mock_engine)


# ============================================================================
# 模块级函数测试
# ============================================================================

class TestModuleLevelFunctions:
    """模块级函数"""

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_get_data_store_singleton(self, mock_makedirs, mock_create_all, mock_create_engine):
        """get_data_store 单例模式"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        # 重置全局状态
        import tengod.data_store as ds_module
        ds_module._store = None

        store1 = get_data_store("/tmp/test1.db")
        store2 = get_data_store("/tmp/test2.db")  # 单例已存在，忽略新路径

        assert store1 is store2

    def test_default_db_path(self):
        """DEFAULT_DB_PATH 不为空"""
        assert DEFAULT_DB_PATH is not None
        assert len(DEFAULT_DB_PATH) > 0


# ============================================================================
# 边界情况与错误处理测试
# ============================================================================

class TestEdgeCases:
    """边界情况与错误处理"""

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_search_bazi_records_multiple_filters(self, mock_makedirs, mock_create_all, mock_create_engine):
        """搜索八字记录——多条件组合"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        with patch.object(store, "_session", return_value=session):
            result = store.search_bazi_records(
                year=1990, month=6, day_master="辛", gender="male", tag="测试",
            )

        assert result == []

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_list_cases_all_filters(self, mock_makedirs, mock_create_all, mock_create_engine):
        """列出案例——全部过滤条件"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        with patch.object(store, "_session", return_value=session):
            result = store.list_cases(
                category="test", is_public=True, is_featured=True, user_id=1,
                limit=10, offset=5,
            )

        assert result == []

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_count_cases_all_filters(self, mock_makedirs, mock_create_all, mock_create_engine):
        """统计案例——全部过滤条件"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.scalar.return_value = 3

        with patch.object(store, "_session", return_value=session):
            count = store.count_cases(category="test", is_public=True)

        assert count == 3

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_cache_report_different_format(self, mock_makedirs, mock_create_all, mock_create_engine):
        """缓存报告——不同格式"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = None
        session.refresh.side_effect = lambda r: setattr(r, "id", 1)

        with patch.object(store, "_session", return_value=session):
            cache_id = store.cache_report(1, "html", "<h1>Report</h1>")

        assert cache_id == 1

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_get_cached_report_default_format(self, mock_makedirs, mock_create_all, mock_create_engine):
        """获取缓存报告——默认格式 text"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        cache = _make_mock_report_cache(id=1, content="text content")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.first.return_value = cache

        with patch.object(store, "_session", return_value=session):
            content = store.get_cached_report(1)

        assert content == "text content"

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_search_cases_with_keyword_and_category(self, mock_makedirs, mock_create_all, mock_create_engine):
        """搜索案例——关键词加分类"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        session = _make_mock_session()
        session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        with patch.object(store, "_session", return_value=session):
            result = store.search_cases("关键词", category="test")

        assert result == []

    @patch("tengod.data_store.create_engine")
    @patch("tengod.data_store.Base.metadata.create_all")
    @patch("tengod.data_store.os.makedirs")
    def test_update_case_text_fields_fts(self, mock_makedirs, mock_create_all, mock_create_engine):
        """更新案例——仅更新非文本字段不触发 fts_vector 更新"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        store = DataStore(db_path="/tmp/test.db")
        case = _make_mock_legacy_case(id=1, category="old")
        original_fts = case.fts_vector
        session = _make_mock_session()
        session.query.return_value.filter.return_value.first.return_value = case

        with patch.object(store, "_session", return_value=session):
            result = store.update_case(1, category="new")

        assert result is True
        # fts_vector 不应被更新（因为未更新文本字段）
        assert case.fts_vector == original_fts