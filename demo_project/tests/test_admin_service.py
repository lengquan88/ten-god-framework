#!/usr/bin/env python3
"""test_admin_service.py — 管理后台服务层全面测试

聚焦数据验证、边界条件和字段白名单（业务关键路径）：
  - _to_dict: dict/pydantic/__dict__/None 四种分支全覆盖
  - 八字记录 CRUD: 必填字段校验/分页边界/更新字段白名单/删除
  - 案例 CRUD: 必填 title/更新字段白名单
  - 用户管理: 重复 username/更新白名单(含 is_active 特殊转换)/toggle_active
  - 命运轨迹: 无效年份范围保护 (end<start, end<=birth_year)
  - batch_bazi: 空输入 → 空结构返回, 50条截断保护
  - compare_cases: 相同 record_id 短路分支（相似度 100%）
  - 配置 KV: set/get/list
  - _ensure_serializable: 递归序列化(datetime/不可序列化类型)
  - _user_to_dict: 属性缺失容错 (无 id/username/is_active 等)
  - get_system_stats: callable recent_activity, 各种类型转换
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from tengod.admin_api import AdminService, _to_dict


# ============================================================================
# Mock 辅助
# ============================================================================

@dataclass
class FakeRecord:
    """模拟 BaziRecord 数据模型"""
    id: int
    year: int
    month: int
    day: int
    hour: int
    minute: int = 0
    gender: str = "male"
    longitude: float = 116.4
    latitude: float = 39.9
    user_id: Optional[int] = None
    label: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "year": self.year, "month": self.month,
            "day": self.day, "hour": self.hour, "minute": self.minute,
            "gender": self.gender, "longitude": self.longitude,
            "latitude": self.latitude, "user_id": self.user_id,
            "label": self.label, "tags": self.tags, "notes": self.notes,
        }


@dataclass
class FakeCase:
    id: int
    title: str
    summary: Optional[str] = None
    analysis_text: Optional[str] = None
    category: Optional[str] = None
    is_public: bool = True
    is_featured: bool = False
    bazi_record_id: Optional[int] = None
    user_id: Optional[int] = None
    tags: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "title": self.title, "summary": self.summary,
            "analysis_text": self.analysis_text, "category": self.category,
            "is_public": self.is_public, "is_featured": self.is_featured,
            "bazi_record_id": self.bazi_record_id, "user_id": self.user_id,
            "tags": self.tags,
        }


@dataclass
class FakeUser:
    id: int
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    role: str = "user"
    is_active: int = 1
    api_quota_daily: int = 100
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class FakeSessionContext:
    """模拟 session context manager"""

    def __init__(self, users: Optional[List[FakeUser]] = None):
        self._users = {u.id: u for u in (users or [])}
        self._report_cache_count = 0

    def __enter__(self):
        class _Query:
            def __init__(self, model):
                self._model = model
                self._filters = []
                self._items = []
                # 从外部 users 注入
                if hasattr(FakeUser, "__name__") and self._model.__name__ == "User":
                    self._items = list(SESSION_USERS.values())

            def filter(self, *args):
                # 简化：不解析 filter 参数，返回全量
                return self

            def count(self):
                return len(self._items)

            def first(self):
                return self._items[0] if self._items else None

            def all(self):
                return list(self._items)

        class S:
            def __init__(self):
                self.added = []
                self.committed = False
                self.refreshed = []

            def query(self, model):
                return _Query(model)

            def add(self, o):
                self.added.append(o)
                if hasattr(o, "id") and o.id is None:
                    o.id = max(list(SESSION_USERS.keys()) or [0]) + 1

            def commit(self):
                self.committed = True
                for u in self.added:
                    if hasattr(u, "id"):
                        SESSION_USERS[u.id] = u

            def refresh(self, o):
                self.refreshed.append(o)

        self._s = S()
        return self._s

    def __exit__(self, *a, **kw):
        return False


# 全局 session users 存储（因为 FakeSession 需要跨方法访问）
SESSION_USERS: Dict[int, FakeUser] = {}


class FakeDataStore:
    """模拟 DataStore，用于 AdminService 测试"""

    def __init__(self):
        self._next_rid = 100
        self._next_cid = 200
        self._records: Dict[int, FakeRecord] = {}
        self._cases: Dict[int, FakeCase] = {}
        self._session_users_backup: Dict[int, FakeUser] = {}
        self._report_cache_count = 0

    # ── session ──
    def _session(self):
        return FakeSessionContext()

    # ── bazi records ──
    def list_bazi_records(self, limit: int = 50, offset: int = 0) -> List[FakeRecord]:
        items = sorted(self._records.values(), key=lambda r: r.id)
        return items[offset:offset + limit]

    def get_bazi_record(self, rid: int) -> Optional[FakeRecord]:
        return self._records.get(rid)

    def save_bazi_record(self, **kwargs) -> int:
        rid = self._next_rid
        self._next_rid += 1
        r = FakeRecord(id=rid, **kwargs)
        self._records[rid] = r
        return rid

    def update_bazi_record(self, rid: int, **kwargs) -> bool:
        if rid not in self._records:
            return False
        r = self._records[rid]
        for k, v in kwargs.items():
            if hasattr(r, k):
                setattr(r, k, v)
        return True

    def delete_bazi_record(self, rid: int) -> bool:
        if rid in self._records:
            del self._records[rid]
            return True
        return False

    # ── cases ──
    def list_cases(self, limit: int = 50, offset: int = 0, category=None):
        items = sorted(self._cases.values(), key=lambda c: c.id)
        if category:
            items = [c for c in items if c.category == category]
        return items[offset:offset + limit]

    def get_case(self, cid: int) -> Optional[FakeCase]:
        return self._cases.get(cid)

    def save_case(self, **kwargs) -> int:
        cid = self._next_cid
        self._next_cid += 1
        c = FakeCase(id=cid, **kwargs)
        self._cases[cid] = c
        return cid

    def update_case(self, cid: int, **kwargs) -> bool:
        if cid not in self._cases:
            return False
        c = self._cases[cid]
        for k, v in kwargs.items():
            if hasattr(c, k):
                setattr(c, k, v)
        return True

    def delete_case(self, cid: int) -> bool:
        if cid in self._cases:
            del self._cases[cid]
            return True
        return False

    def list_users(self, limit: int = 50) -> List[FakeUser]:
        items = sorted(SESSION_USERS.values(), key=lambda u: u.id)
        return items[:limit]

    def get_user(self, uid: int) -> Optional[FakeUser]:
        return SESSION_USERS.get(uid)

    def stats(self) -> Dict[str, Any]:
        return {
            "total_records": len(self._records),
            "total_cases": len(self._cases),
            "top_day_masters": [
                {"dm": "甲木", "count": 12},
                {"dm": "乙木", "count": 8},
            ],
            "db_path": "/tmp/test.db",
            "db_size_mb": 4.56,
            "recent_activity": "2026-01-01",
        }


class FakeAnalyzer:
    """模拟 AdvancedAnalyzer"""

    def __init__(self):
        self.batch_bazi_calls = []
        self.compare_cases_calls = []
        self.destiny_trajectory_calls = []

    def batch_bazi(self, inputs):
        self.batch_bazi_calls.append(inputs)
        return {
            "results": [{"status": "ok"} for _ in inputs],
            "stats": {
                "total": len(inputs), "success": len(inputs), "failed": 0,
                "day_masters": {}, "gejus": {},
                "wuxing_totals": {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0},
            },
        }

    def compare_cases(self, a, b):
        self.compare_cases_calls.append((a, b))
        return {
            "similarity_score": 75.0, "summary": "mock compare",
            "day_master_same": False, "geju_same": False,
        }

    def destiny_trajectory(self, **kwargs):
        self.destiny_trajectory_calls.append(kwargs)
        return {
            "birth": {"year": kwargs.get("year")},
            "dayun": [{"age": 10}, {"age": 20}],
            "liunian": [{"year": kwargs.get("year") + 5}],
            "life_stages": [{"label": "少年"}],
            "summary": "mock trajectory",
        }


@pytest.fixture(autouse=True)
def reset_session_users():
    """每个测试前清空全局 SESSION_USERS"""
    SESSION_USERS.clear()
    yield
    SESSION_USERS.clear()


@pytest.fixture
def fake_store():
    return FakeDataStore()


@pytest.fixture
def fake_analyzer():
    return FakeAnalyzer()


@pytest.fixture
def svc(fake_store, fake_analyzer):
    return AdminService(store=fake_store, analyzer=fake_analyzer)


@pytest.fixture
def sample_record_data():
    """标准八字记录输入"""
    return {"year": 1990, "month": 5, "day": 15, "hour": 8}


# ============================================================================
# _to_dict 工具函数
# ============================================================================

class TestToDict:
    """_to_dict 所有分支覆盖"""

    def test_none_returns_empty_dict(self):
        assert _to_dict(None) == {}

    def test_dict_passthrough(self):
        d = {"a": 1, "b": "x"}
        assert _to_dict(d) is d

    def test_pydantic_like_model_dump(self):
        class Obj:
            def model_dump(self, exclude_none=False):
                return {"field": "value", "excluded": None} if not exclude_none \
                    else {"field": "value"}

        result = _to_dict(Obj())
        # exclude_none=True → 排除 None 字段
        assert "field" in result
        assert "excluded" not in result

    def test_fallback_dict_method(self):
        class Obj:
            def dict(self, exclude_none=False):
                return {"k": "v"}
            # 没有 model_dump 属性 → 走 dict 分支

        assert _to_dict(Obj()) == {"k": "v"}

    def test_model_dump_exception_fallback_to_dict(self):
        class Obj:
            def model_dump(self, **kw):
                raise RuntimeError("boom")

            def dict(self, **kw):
                return {"fallback": "dict"}

        assert _to_dict(Obj()) == {"fallback": "dict"}

    def test_fallback_to_instance_dict(self):
        class Obj:
            def __init__(self):
                self.a = 1
                self.b = 2
                self._private = "ignored"  # _ 开头排除

        assert _to_dict(Obj()) == {"a": 1, "b": 2}

    def test_unknown_type_returns_empty(self):
        assert _to_dict(42) == {}
        assert _to_dict("string") == {}


# ============================================================================
# 八字记录 CRUD 测试
# ============================================================================

class TestBaziRecordCRUD:
    """八字记录 CRUD + 必填字段校验 + 分页边界 + 更新白名单"""

    # ── create 必填字段校验 ──
    def test_create_success(self, svc, sample_record_data):
        result = svc.create_record(sample_record_data)
        assert "error" not in result
        assert result["id"] >= 100
        assert result["year"] == 1990
        assert result["month"] == 5
        assert result["day"] == 15
        assert result["hour"] == 8

    def test_create_missing_year(self, svc, sample_record_data):
        del sample_record_data["year"]
        result = svc.create_record(sample_record_data)
        assert "error" in result
        assert "缺少必填字段" in result["error"]
        assert "year" in result["error"]

    def test_create_missing_month(self, svc, sample_record_data):
        del sample_record_data["month"]
        result = svc.create_record(sample_record_data)
        assert "error" in result and "month" in result["error"]

    def test_create_missing_day(self, svc, sample_record_data):
        del sample_record_data["day"]
        result = svc.create_record(sample_record_data)
        assert "error" in result and "day" in result["error"]

    def test_create_missing_hour(self, svc, sample_record_data):
        del sample_record_data["hour"]
        result = svc.create_record(sample_record_data)
        assert "error" in result and "hour" in result["error"]

    def test_create_defaults_applied(self, svc, sample_record_data):
        """gender/minute/longitude/latitude 缺失时应用默认值"""
        result = svc.create_record(sample_record_data)
        # 默认 gender=male, minute=0
        assert result["gender"] == "male"
        assert result["minute"] == 0
        assert result["longitude"] == 116.4
        assert result["latitude"] == 39.9

    def test_create_with_all_fields(self, svc):
        d = {
            "year": 2000, "month": 1, "day": 1, "hour": 12, "minute": 34,
            "gender": "female", "longitude": 121.5, "latitude": 31.2,
            "user_id": 7, "label": "测试标签", "notes": "详细备注", "tags": "a,b",
        }
        r = svc.create_record(d)
        assert "error" not in r
        assert r["gender"] == "female"
        assert r["minute"] == 34
        assert r["longitude"] == 121.5
        assert r["latitude"] == 31.2
        assert r["user_id"] == 7
        assert r["label"] == "测试标签"
        assert r["notes"] == "详细备注"
        assert r["tags"] == "a,b"

    # ── 分页边界 ──
    def test_get_records_paginated_boundaries(self, svc, sample_record_data):
        # 创建 5 条
        for _ in range(5):
            svc.create_record(sample_record_data)

        # limit 被强制至少 1
        r = svc.get_records_paginated(limit=0, offset=0)
        assert len(r) >= 1  # max(1, int(0)) = 1

        # limit 负数 → max(1, ...)
        r = svc.get_records_paginated(limit=-10, offset=0)
        assert len(r) >= 1

        # offset 负数 → max(0, ...)
        r = svc.get_records_paginated(limit=10, offset=-5)
        assert len(r) == 5

        # offset 超出 → 空
        r = svc.get_records_paginated(limit=10, offset=100)
        assert r == []

    def test_get_record_existing(self, svc, sample_record_data):
        created = svc.create_record(sample_record_data)
        fetched = svc.get_record(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]

    def test_get_record_nonexistent(self, svc):
        assert svc.get_record(99999) is None

    # ── 更新字段白名单 ──
    def test_update_only_allowed_fields(self, svc, sample_record_data):
        """更新时只允许指定字段，其它字段会被剥离"""
        created = svc.create_record(sample_record_data)
        rid = created["id"]

        # 注入 "id" 试图篡改主键，以及注入不在白名单中的 "malicious"
        ok = svc.update_record(rid, {
            "label": "new_label",
            "notes": "new_notes",
            "id": 99999,          # 不在白名单 → 剥离
            "malicious": "haha",  # 不在白名单 → 剥离
        })
        assert ok is True

        updated = svc.get_record(rid)
        assert updated["label"] == "new_label"
        assert updated["notes"] == "new_notes"
        # 确保 id 没被篡改
        assert updated["id"] == rid

    def test_update_empty_clean_returns_false(self, svc, sample_record_data):
        """仅传入 None 值或非白名单字段 → clean 为空 → False"""
        created = svc.create_record(sample_record_data)
        # 全是 None 值 → 全部被过滤
        ok = svc.update_record(created["id"], {"label": None, "notes": None})
        assert ok is False

    def test_update_nonexistent(self, svc):
        assert svc.update_record(9999, {"label": "x"}) is False

    # ── 删除 ──
    def test_delete_existing(self, svc, sample_record_data):
        created = svc.create_record(sample_record_data)
        assert svc.delete_record(created["id"]) is True
        assert svc.get_record(created["id"]) is None

    def test_delete_nonexistent(self, svc):
        assert svc.delete_record(9999) is False


# ============================================================================
# 案例 CRUD 测试
# ============================================================================

class TestCaseCRUD:
    """案例管理：必填 title、更新字段白名单"""

    def test_create_success(self, svc):
        result = svc.create_case({"title": "测试案例", "category": "事业"})
        assert "error" not in result
        assert result["id"] >= 200
        assert result["title"] == "测试案例"
        assert result["category"] == "事业"
        # 默认值
        assert result["is_public"] is True
        assert result["is_featured"] is False

    def test_create_missing_title(self, svc):
        result = svc.create_case({})
        assert "error" in result
        assert "title" in result["error"]

    def test_create_empty_title(self, svc):
        result = svc.create_case({"title": "   "})
        assert "error" in result and "title" in result["error"]

    def test_list_filter_by_category(self, svc):
        svc.create_case({"title": "C1", "category": "事业"})
        svc.create_case({"title": "C2", "category": "婚姻"})
        svc.create_case({"title": "C3", "category": "事业"})

        career = svc.get_cases_paginated(category="事业")
        assert len(career) == 2
        for c in career:
            assert c["category"] == "事业"

    def test_update_allowed_fields_only(self, svc):
        created = svc.create_case({"title": "T"})
        cid = created["id"]
        ok = svc.update_case(cid, {
            "title": "New Title",
            "category": "健康",
            "id": 9999,  # 不在白名单，应被剥离
            "extra": "nope",
        })
        assert ok is True

        fetched = svc.get_cases_paginated()[0]
        assert fetched["title"] == "New Title"
        assert fetched["category"] == "健康"
        assert fetched["id"] == cid

    def test_update_empty_clean(self, svc):
        created = svc.create_case({"title": "T"})
        assert svc.update_case(created["id"], {"title": None}) is False

    def test_delete(self, svc):
        created = svc.create_case({"title": "T"})
        assert svc.delete_case(created["id"]) is True
        assert len(svc.get_cases_paginated()) == 0


# ============================================================================
# 用户管理测试
# ============================================================================

class TestUserManagement:
    """用户管理：重复用户名、更新白名单、is_active 特殊转换、toggle"""

    def test_create_user_success(self, svc):
        r = svc.create_user({"username": "alice", "role": "admin", "email": "a@b.com"})
        assert "error" not in r
        assert r["username"] == "alice"
        assert r["role"] == "admin"
        assert r["email"] == "a@b.com"
        assert r["is_active"] is True
        assert r["api_quota_daily"] == 100
        assert r["display_name"] == "alice"  # 缺失 display_name 回退到 username

    def test_create_user_missing_username(self, svc):
        r = svc.create_user({})
        assert "error" in r and "username" in r["error"]

    def test_create_user_duplicate_username(self, svc):
        svc.create_user({"username": "bob"})
        r = svc.create_user({"username": "bob"})
        assert "error" in r and "已存在" in r["error"]

    def test_update_user_allowed_fields(self, svc):
        created = svc.create_user({"username": "charlie"})
        uid = created["id"]
        ok = svc.update_user(uid, {
            "display_name": "查理",
            "email": "c@c.com",
            "role": "admin",
            "api_quota_daily": 200,
            "username": "hacker",  # 不在白名单 → 应剥离
        })
        assert ok is True
        fetched = svc.get_user(uid)
        assert fetched["display_name"] == "查理"
        assert fetched["email"] == "c@c.com"
        assert fetched["role"] == "admin"
        assert fetched["api_quota_daily"] == 200
        # username 不能通过 update_user 修改
        assert fetched["username"] == "charlie"

    def test_update_user_is_active_special_conversion(self, svc):
        """is_active 需要特殊处理: int 存储，但接受 bool/int"""
        created = svc.create_user({"username": "dave"})
        uid = created["id"]

        # False → 0
        ok = svc.update_user(uid, {"is_active": False})
        assert ok is True
        assert svc.get_user(uid)["is_active"] is False

        # True → 1
        ok = svc.update_user(uid, {"is_active": True})
        assert ok is True
        assert svc.get_user(uid)["is_active"] is True

    def test_update_empty_clean(self, svc):
        created = svc.create_user({"username": "eve"})
        assert svc.update_user(created["id"], {"display_name": None}) is False

    def test_update_nonexistent(self, svc):
        assert svc.update_user(99999, {"display_name": "x"}) is False

    def test_toggle_user_active(self, svc):
        created = svc.create_user({"username": "frank"})
        uid = created["id"]
        assert svc.get_user(uid)["is_active"] is True

        # 第一次 toggle → False
        assert svc.toggle_user_active(uid) is True
        assert svc.get_user(uid)["is_active"] is False

        # 第二次 toggle → True
        assert svc.toggle_user_active(uid) is True
        assert svc.get_user(uid)["is_active"] is True

    def test_toggle_nonexistent(self, svc):
        assert svc.toggle_user_active(99999) is False

    def test_get_user_nonexistent(self, svc):
        assert svc.get_user(99999) is None

    def test_get_users_limit(self, svc):
        for i in range(5):
            svc.create_user({"username": f"u{i}"})
        users = svc.get_users(limit=3)
        # max(1, int(3)) = 3
        assert 0 < len(users) <= 3


# ============================================================================
# 命运轨迹：年份范围保护
# ============================================================================

class TestTrajectoryYearRange:
    """无效年份范围返回空结构但不抛异常"""

    def test_end_year_less_than_start(self, svc, sample_record_data):
        r = svc.create_record(sample_record_data)
        traj = svc.get_trajectory(r["id"], 2010, 2000)
        # 应返回空 dayun/liunian/life_stages 及 summary 提示
        assert traj["dayun"] == []
        assert traj["liunian"] == []
        assert traj["life_stages"] == []
        assert "年份范围无效" in traj.get("summary", "")
        # birth 信息仍保留
        assert traj["birth"]["year"] == sample_record_data["year"]

    def test_end_year_less_than_or_equal_birth_year(self, svc, sample_record_data):
        """end_year <= birth_year → 同样视为无效"""
        r = svc.create_record(sample_record_data)
        # birth year = 1990, end = 1990
        traj = svc.get_trajectory(r["id"], 1990, 1990)
        assert traj["dayun"] == []
        assert traj["liunian"] == []
        assert "年份范围无效" in traj.get("summary", "")

    def test_record_not_found(self, svc):
        traj = svc.get_trajectory(99999, 2000, 2020)
        assert "error" in traj and "不存在" in traj["error"]

    def test_valid_range_delegates_to_analyzer(
        self, svc, sample_record_data, fake_analyzer,
    ):
        r = svc.create_record(sample_record_data)
        traj = svc.get_trajectory(r["id"], 2000, 2030)
        assert len(fake_analyzer.destiny_trajectory_calls) == 1
        call = fake_analyzer.destiny_trajectory_calls[0]
        # start_age = 2000 - 1990 = 10, end_age = 2030 - 1990 = 40
        assert call["start_age"] == 10
        assert call["end_age"] == 40


# ============================================================================
# batch_bazi: 空输入 / 50 条截断
# ============================================================================

class TestBatchBazi:
    """批量排盘边界"""

    def test_empty_inputs_returns_empty_struct(self, svc):
        r = svc.batch_bazi([])
        assert r["results"] == []
        assert r["stats"]["total"] == 0
        assert r["stats"]["success"] == 0
        assert r["stats"]["failed"] == 0
        # wuxing_totals 完整
        assert set(r["stats"]["wuxing_totals"].keys()) == {"金", "木", "水", "火", "土"}

    def test_50_cap_truncation(self, svc, fake_analyzer, sample_record_data):
        """超过 50 条时截断为前 50 条"""
        many = [dict(sample_record_data) for _ in range(75)]
        svc.batch_bazi(many)
        # analyzer 只收到 50 条
        assert len(fake_analyzer.batch_bazi_calls) == 1
        assert len(fake_analyzer.batch_bazi_calls[0]) == 50


# ============================================================================
# compare_cases: 相同 ID 的短路分支
# ============================================================================

class TestCompareCases:
    """相同 ID 短路返回 100% 相似度"""

    def test_same_id_shortcut(self, svc, sample_record_data):
        created = svc.create_record(sample_record_data)
        rid = created["id"]
        r = svc.compare_cases(rid, rid)
        assert r["similarity_score"] == 100.0
        assert "100%" in r["summary"]
        assert r["day_master_same"] is True
        assert r["geju_same"] is True

    def test_same_id_nonexistent_returns_error(self, svc):
        r = svc.compare_cases(99999, 99999)
        assert "error" in r and "不存在" in r["error"]

    def test_different_ids_delegates_to_analyzer(
        self, svc, fake_analyzer, sample_record_data,
    ):
        a = svc.create_record(sample_record_data)
        data2 = dict(sample_record_data)
        data2["year"] = 2000
        b = svc.create_record(data2)
        r = svc.compare_cases(a["id"], b["id"])
        assert len(fake_analyzer.compare_cases_calls) == 1
        assert r["similarity_score"] == 75.0  # mock 返回值


# ============================================================================
# 配置 KV
# ============================================================================

class TestConfigKV:
    """简易 KV 配置管理"""

    def test_set_and_get(self, svc):
        assert svc.set_config("theme", "dark") is True
        assert svc.get_config("theme") == "dark"
        # 不存在 → None
        assert svc.get_config("nope") is None
        # 默认值
        assert svc.get_config("nope", "default") == "default"

    def test_list_config(self, svc):
        svc.set_config("a", 1)
        svc.set_config("b", "two")
        cfg = svc.list_config()
        assert cfg == {"a": 1, "b": "two"}
        # 返回的是副本，修改不影响内部
        cfg["c"] = 3
        assert "c" not in svc.list_config()

    def test_overwrite_key(self, svc):
        svc.set_config("k", "v1")
        svc.set_config("k", "v2")
        assert svc.get_config("k") == "v2"


# ============================================================================
# _ensure_serializable 递归序列化
# ============================================================================

class TestEnsureSerializable:
    """不可序列化对象的 str() 回退 + datetime isoformat"""

    def test_primitives_unchanged(self, svc):
        assert svc._ensure_serializable(42) == 42
        assert svc._ensure_serializable("s") == "s"
        assert svc._ensure_serializable(3.14) == 3.14
        assert svc._ensure_serializable(True) is True
        assert svc._ensure_serializable(None) is None

    def test_datetime_isoformat(self, svc):
        dt = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        r = svc._ensure_serializable(dt)
        assert r == "2026-01-02T03:04:05+00:00"

    def test_recursive_dict_and_list(self, svc):
        dt = datetime(2026, 6, 1)
        obj = {
            1: "int_key_cast_to_str",
            "dt": dt,
            "list": [1, "x", dt, {"a": 1}],
            "tuple": (1, 2, 3),
        }
        r = svc._ensure_serializable(obj)
        # int 键被 str()
        assert "1" in r and 1 not in r
        assert isinstance(r["1"], str)
        assert r["dt"] == "2026-06-01T00:00:00"
        # list/tuple 都转为 list
        assert isinstance(r["list"], list)
        assert isinstance(r["tuple"], list)
        # 嵌套 dict 也被处理
        assert r["list"][3] == {"a": 1}

    def test_unserializable_object(self, svc):
        """含 lambda/函数的复杂对象 → str() 回退"""
        class Obj:
            def __str__(self):
                return "<Obj>"

        r = svc._ensure_serializable({"obj": Obj()})
        assert r["obj"] == "<Obj>"

    def test_output_is_json_serializable(self, svc):
        """最终产出必须能 json.dumps"""
        dt = datetime(2026, 1, 1)
        data = {
            "a": [1, 2, {"k": dt}],
            "b": (True, False),
        }
        cleaned = svc._ensure_serializable(data)
        # 必须不抛异常
        s = json.dumps(cleaned)
        assert isinstance(s, str)


# ============================================================================
# _user_to_dict 属性缺失容错
# ============================================================================

class TestUserToDict:
    """_user_to_dict 在部分属性缺失时不崩溃"""

    def test_minimal_user(self, svc):
        class BareUser:
            pass
        u = BareUser()
        d = svc._user_to_dict(u)
        # 所有缺失属性安全回退
        assert d["id"] is None
        assert d["username"] is None
        assert d["display_name"] is None
        assert d["email"] is None
        assert d["role"] == "user"
        assert d["is_active"] is True  # bool(int(1 or 0))
        assert d["api_quota_daily"] == 100
        assert d["last_login_at"] is None
        assert d["created_at"] is None

    def test_user_with_datetime(self, svc):
        u = FakeUser(
            id=1, username="x",
            last_login_at=datetime(2026, 3, 4, 5, 6),
            created_at=datetime(2025, 1, 1),
        )
        d = svc._user_to_dict(u)
        assert d["last_login_at"] == "2026-03-04T05:06:00"
        assert d["created_at"] == "2025-01-01T00:00:00"

    def test_is_active_coercion(self, svc):
        class U:
            is_active = None
        assert svc._user_to_dict(U())["is_active"] is False  # bool(int(0))

        class U2:
            is_active = 0
        assert svc._user_to_dict(U2())["is_active"] is False

        class U3:
            is_active = 1
        assert svc._user_to_dict(U3())["is_active"] is True


# ============================================================================
# get_system_stats 的各种分支
# ============================================================================

class TestGetSystemStats:
    """统计信息序列化 + callable recent_activity 处理"""

    def test_basic_stats(self, svc, sample_record_data):
        svc.create_record(sample_record_data)
        svc.create_case({"title": "C1"})
        stats = svc.get_system_stats()
        assert stats["total_records"] == 1
        assert stats["total_cases"] == 1
        assert stats["cache_entries"] == 0  # 无 set_config
        # top_day_masters 正常序列化
        assert len(stats["top_day_masters"]) == 2
        assert stats["top_day_masters"][0]["dm"] == "甲木"
        assert stats["top_day_masters"][0]["count"] == 12
        assert stats["db_path"] == "/tmp/test.db"
        assert stats["db_size_mb"] == 4.56

    def test_stats_with_config_entries(self, svc):
        svc.set_config("x", 1)
        svc.set_config("y", 2)
        assert svc.get_system_stats()["cache_entries"] == 2

    def test_callable_recent_activity(self, svc, fake_store):
        """recent_activity 是 callable 时调用它"""
        fake_store.stats = lambda: {
            "recent_activity": lambda: "2026-08-02T10:00:00",
        }
        stats = svc.get_system_stats()
        assert stats["recent_activity"] == "2026-08-02T10:00:00"

    def test_callable_recent_activity_exception(self, svc, fake_store):
        def boom():
            raise RuntimeError("boom")
        fake_store.stats = lambda: {"recent_activity": boom}
        stats = svc.get_system_stats()
        # 异常后回退到 ""
        assert stats["recent_activity"] == ""

    def test_recent_activity_numeric_types(self, svc, fake_store):
        """数值型 recent_activity 转为字符串"""
        fake_store.stats = lambda: {"recent_activity": 1704067200}
        assert svc.get_system_stats()["recent_activity"] == "1704067200"
        fake_store.stats = lambda: {"recent_activity": 1704067200.5}
        assert svc.get_system_stats()["recent_activity"] == "1704067200.5"

    def test_recent_activity_none(self, svc, fake_store):
        fake_store.stats = lambda: {"recent_activity": None}
        assert svc.get_system_stats()["recent_activity"] == ""

    def test_top_day_masters_non_dict_items(self, svc, fake_store):
        """top_day_masters 元素不是 dict（如 tuple）时走 str 分支"""
        fake_store.stats = lambda: {
            "top_day_masters": [("甲木", 10), ("乙木", 7)]
        }
        stats = svc.get_system_stats()
        dms = {d["dm"]: d["count"] for d in stats["top_day_masters"]}
        assert "('甲木', 10)" in dms

    def test_stats_base_is_none(self, svc, fake_store):
        """store.stats() 返回 None → 走默认值保护"""
        fake_store.stats = lambda: None
        stats = svc.get_system_stats()
        assert stats["total_records"] == 0
        assert stats["total_cases"] == 0
        assert stats["top_day_masters"] == []
        assert stats["db_path"] == ""
        assert stats["db_size_mb"] == 0.0

    def test_output_is_json_serializable(self, svc):
        """get_system_stats 产出必须可 JSON 序列化"""
        s = json.dumps(svc.get_system_stats())
        assert isinstance(s, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
