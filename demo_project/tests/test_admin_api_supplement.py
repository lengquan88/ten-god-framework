"""
tests/test_admin_api_supplement.py — admin_api 模块补充测试

目标：将覆盖率从 68% 提升至 85%+。

覆盖范围：
  - Pydantic 模型 (model_dump/dict)
  - AdminService 错误路径 / 边界情况
  - FastAPI 端点 (config, users, cases CRUD, 错误路径)
  - 工具函数 (_to_dict, _ensure_serializable)
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from tengod.admin_api import AdminService, _to_dict


# ---------------------------------------------------------------------------
# 帮助函数
# ---------------------------------------------------------------------------

def _unique_db_path(suffix: str = "") -> str:
    name = f"tengod_admin_suppl_{uuid.uuid4().hex}{suffix}.db"
    return os.path.join(tempfile.gettempdir(), name)


# ============================================================================
# 1. Pydantic 模型测试
# ============================================================================

class TestPydanticModels:
    """测试 Pydantic 模型的 model_dump() 和 dict() 方法"""

    def test_bazi_record_input_model_dump(self):
        """BaziRecordInput.model_dump() 返回字典"""
        from tengod.admin_api import BaziRecordInput
        record = BaziRecordInput(year=1990, month=6, day=15, hour=10, gender="male")
        dumped = record.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["year"] == 1990
        assert dumped["gender"] == "male"

    def test_bazi_record_input_dict(self):
        """BaziRecordInput.dict() 返回字典"""
        from tengod.admin_api import BaziRecordInput
        record = BaziRecordInput(year=2000, month=1, day=1, hour=0, gender="female")
        d = record.dict()
        assert isinstance(d, dict)
        assert d["year"] == 2000
        assert d["gender"] == "female"

    def test_bazi_record_update_model_dump(self):
        """BaziRecordUpdate.model_dump() 返回字典"""
        from tengod.admin_api import BaziRecordUpdate
        update = BaziRecordUpdate(label="新标签", notes="备注")
        dumped = update.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["label"] == "新标签"
        assert dumped["notes"] == "备注"

    def test_case_input_model_dump(self):
        """CaseInput.model_dump() 返回字典"""
        from tengod.admin_api import CaseInput
        case = CaseInput(title="测试案例", category="test", is_public=True)
        dumped = case.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["title"] == "测试案例"
        assert dumped["category"] == "test"

    def test_case_update_dict(self):
        """CaseUpdate.dict() 返回字典"""
        from tengod.admin_api import CaseUpdate
        update = CaseUpdate(title="更新标题", summary="新摘要")
        d = update.dict()
        assert isinstance(d, dict)
        assert d["title"] == "更新标题"

    def test_user_create_model_dump(self):
        """UserCreate.model_dump() 返回字典"""
        from tengod.admin_api import UserCreate
        user = UserCreate(username="testuser", role="user", api_quota_daily=200)
        dumped = user.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["username"] == "testuser"
        assert dumped["api_quota_daily"] == 200

    def test_user_update_dict(self):
        """UserUpdate.dict() 返回字典"""
        from tengod.admin_api import UserUpdate
        update = UserUpdate(display_name="新名字", is_active=True)
        d = update.dict()
        assert isinstance(d, dict)
        assert d["display_name"] == "新名字"

    def test_trajectory_query_model_dump(self):
        """TrajectoryQuery.model_dump() 返回字典"""
        from tengod.admin_api import TrajectoryQuery
        query = TrajectoryQuery(
            year=1990, month=6, day=15, hour=10, gender="male",
            start_year=1990, end_year=2030,
        )
        dumped = query.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["year"] == 1990

    @pytest.mark.parametrize("model_cls,kwargs", [
        pytest.param("BaziRecordInput", {"year": 1990, "month": 6, "day": 15, "hour": 10}, id="BaziRecordInput"),
        pytest.param("BaziRecordUpdate", {"label": "test"}, id="BaziRecordUpdate"),
        pytest.param("CaseInput", {"title": "test"}, id="CaseInput"),
        pytest.param("CaseUpdate", {"title": "updated"}, id="CaseUpdate"),
        pytest.param("UserCreate", {"username": "testuser"}, id="UserCreate"),
        pytest.param("UserUpdate", {"display_name": "dn"}, id="UserUpdate"),
    ])
    def test_model_dump_and_dict_consistency(self, model_cls, kwargs):
        """model_dump() 和 dict() 返回一致的字典"""
        import importlib
        mod = importlib.import_module("tengod.admin_api")
        cls = getattr(mod, model_cls)
        instance = cls(**kwargs)
        dump = instance.model_dump()
        d = instance.dict()
        for key in kwargs:
            assert dump.get(key) == kwargs[key]
            assert d.get(key) == kwargs[key]


# ============================================================================
# 2. AdminService 错误路径 / 边界测试
# ============================================================================

class TestAdminServiceErrorPaths:
    """AdminService 错误路径和边界情况"""

    def setup_method(self, method):
        self.path = _unique_db_path(f"err_{method.__name__}")
        self.service = AdminService(db_path=self.path)

    def teardown_method(self, method):
        try:
            self.service = None
            if os.path.exists(self.path):
                os.remove(self.path)
        except Exception:
            pass

    # ── create_record 错误路径 ──────────────────────────────

    def test_create_record_missing_required_fields(self):
        """create_record 缺少必填字段返回 error"""
        result = self.service.create_record({"year": 1990})
        assert "error" in result
        assert "create_record failed" in result["error"]

    def test_create_record_empty_dict(self):
        """create_record 空字典返回 error"""
        result = self.service.create_record({})
        assert "error" in result

    # ── update_record 错误路径 ──────────────────────────────

    def test_update_record_empty_update(self):
        """update_record 空更新数据返回 False"""
        rid = self.service.create_record({
            "year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male",
        })["id"]
        ok = self.service.update_record(rid, {})
        assert ok is False

    def test_update_record_nonexistent(self):
        """update_record 不存在的记录返回 False"""
        ok = self.service.update_record(99999, {"label": "不可能"})
        assert ok is False

    # ── delete_record 错误路径 ──────────────────────────────

    def test_delete_record_nonexistent(self):
        """delete_record 不存在的记录返回 False"""
        ok = self.service.delete_record(99999)
        assert ok is False

    # ── create_case 错误路径 ─────────────────────────────────

    def test_create_case_missing_title(self):
        """create_case 缺少 title 返回 error"""
        result = self.service.create_case({"summary": "没有标题"})
        assert "error" in result

    def test_create_case_empty_title(self):
        """create_case title 为空字符串返回 error"""
        result = self.service.create_case({"title": "   "})
        assert "error" in result

    # ── update_case / delete_case ────────────────────────────

    def test_update_case(self):
        """update_case 成功更新案例"""
        case = self.service.create_case({"title": "原始案例", "category": "test"})
        ok = self.service.update_case(case["id"], {"title": "更新后", "summary": "新摘要"})
        assert ok is True

    def test_update_case_nonexistent(self):
        """update_case 不存在的案例返回 False"""
        ok = self.service.update_case(99999, {"title": "不存在"})
        assert ok is False

    def test_update_case_empty(self):
        """update_case 空更新返回 False"""
        case = self.service.create_case({"title": "测试"})
        ok = self.service.update_case(case["id"], {})
        assert ok is False

    def test_delete_case(self):
        """delete_case 成功删除案例"""
        case = self.service.create_case({"title": "待删除案例"})
        ok = self.service.delete_case(case["id"])
        assert ok is True

    def test_delete_case_nonexistent(self):
        """delete_case 不存在的案例返回 False"""
        ok = self.service.delete_case(99999)
        assert ok is False

    # ── create_user 错误路径 ─────────────────────────────────

    def test_create_user_missing_username(self):
        """create_user 缺少 username 返回 error"""
        result = self.service.create_user({"display_name": "无名"})
        assert "error" in result

    def test_create_user_duplicate_username(self):
        """create_user 重复 username 返回 error"""
        self.service.create_user({"username": "dup"})
        result = self.service.create_user({"username": "dup"})
        assert "error" in result

    # ── update_user 错误路径 ─────────────────────────────────

    def test_update_user_empty(self):
        """update_user 空更新返回 False"""
        user = self.service.create_user({"username": "empty_update"})
        ok = self.service.update_user(user["id"], {})
        assert ok is False

    def test_update_user_nonexistent(self):
        """update_user 不存在的用户返回 False"""
        ok = self.service.update_user(99999, {"display_name": "不存在"})
        assert ok is False

    def test_update_user_is_active(self):
        """update_user 设置 is_active 字段"""
        user = self.service.create_user({"username": "active_test"})
        ok = self.service.update_user(user["id"], {"is_active": False})
        assert ok is True
        updated = self.service.get_user(user["id"])
        assert updated["is_active"] is False

    # ── toggle_user_active ───────────────────────────────────

    def test_toggle_user_active(self):
        """toggle_user_active 切换用户激活状态"""
        user = self.service.create_user({"username": "toggle_me"})
        assert user["is_active"] is True
        ok = self.service.toggle_user_active(user["id"])
        assert ok is True
        updated = self.service.get_user(user["id"])
        assert updated["is_active"] is False
        ok2 = self.service.toggle_user_active(user["id"])
        assert ok2 is True
        updated2 = self.service.get_user(user["id"])
        assert updated2["is_active"] is True

    def test_toggle_user_active_nonexistent(self):
        """toggle_user_active 不存在的用户返回 False"""
        ok = self.service.toggle_user_active(99999)
        assert ok is False

    # ── get_user 边界 ────────────────────────────────────────

    def test_get_user_nonexistent(self):
        """get_user 不存在的用户返回 None"""
        user = self.service.get_user(99999)
        assert user is None

    # ── get_trajectory 错误路径 ─────────────────────────────

    def test_trajectory_nonexistent_record(self):
        """get_trajectory 不存在的记录返回 error"""
        traj = self.service.get_trajectory(99999, 1990, 2030)
        assert "error" in traj

    # ── get_trajectory_from_bazi 错误路径 ───────────────────

    def test_trajectory_from_bazi_invalid_input(self):
        """get_trajectory_from_bazi 无效输入返回 error"""
        traj = self.service.get_trajectory_from_bazi({}, 1990, 2030)
        assert "error" in traj

    # ── compare_cases 错误路径 ──────────────────────────────

    def test_compare_nonexistent_record(self):
        """compare_cases 不存在的记录返回 error"""
        result = self.service.compare_cases(99999, 99998)
        assert "error" in result

    # ── get_records_paginated 边界 ──────────────────────────

    def test_get_records_paginated_empty(self):
        """get_records_paginated 空数据库返回 []"""
        records = self.service.get_records_paginated()
        assert records == []

    def test_get_records_paginated_with_offset(self):
        """get_records_paginated offset 跳过头几条"""
        for i in range(5):
            self.service.create_record({
                "year": 1980 + i, "month": 1, "day": 1, "hour": 8, "gender": "male",
            })
        records = self.service.get_records_paginated(limit=2, offset=1)
        assert len(records) == 2

    # ── get_cases_paginated 边界 ────────────────────────────

    def test_get_cases_paginated_empty(self):
        """get_cases_paginated 空数据库返回 []"""
        cases = self.service.get_cases_paginated()
        assert cases == []

    # ── get_users 边界 ───────────────────────────────────────

    def test_get_users_empty(self):
        """get_users 空数据库返回 []"""
        users = self.service.get_users()
        assert users == []

    # ── batch_bazi 边界 ─────────────────────────────────────

    def test_batch_bazi_empty(self):
        """batch_bazi 空列表返回空结果"""
        result = self.service.batch_bazi([])
        assert result["results"] == []
        assert result["stats"]["total"] == 0

    # ── 配置管理 ────────────────────────────────────────────

    def test_set_config(self):
        """set_config 设置配置项"""
        ok = self.service.set_config("key1", "value1")
        assert ok is True

    def test_get_config(self):
        """get_config 读取配置项"""
        self.service.set_config("k", "v")
        assert self.service.get_config("k") == "v"

    def test_get_config_default(self):
        """get_config 不存在的 key 返回默认值"""
        assert self.service.get_config("no_key", "default") == "default"

    def test_list_config(self):
        """list_config 列出所有配置"""
        self.service.set_config("a", 1)
        self.service.set_config("b", 2)
        cfg = self.service.list_config()
        assert isinstance(cfg, dict)
        assert cfg["a"] == 1
        assert cfg["b"] == 2

    def test_list_config_empty(self):
        """list_config 空配置返回 {}"""
        cfg = self.service.list_config()
        assert cfg == {}


# ============================================================================
# 3. 工具函数测试
# ============================================================================

class TestUtils:
    """测试 _to_dict 和 _ensure_serializable"""

    def test_to_dict_none(self):
        """_to_dict(None) 返回 {}"""
        assert _to_dict(None) == {}

    def test_to_dict_dict(self):
        """_to_dict(dict) 返回原 dict"""
        d = {"a": 1, "b": 2}
        assert _to_dict(d) is d

    def test_to_dict_pydantic_model(self):
        """_to_dict(pydantic model) 调用 model_dump"""
        from tengod.admin_api import BaziRecordInput
        record = BaziRecordInput(year=1990, month=6, day=15, hour=10, gender="male")
        d = _to_dict(record)
        assert isinstance(d, dict)
        assert d["year"] == 1990

    def test_to_dict_fallback_to_dict_method(self):
        """_to_dict 回退到 .dict() 方法"""
        class ObjWithDict:
            def __init__(self):
                self.a = 1
            def dict(self, exclude_none=True):
                return {"a": self.a}
        obj = ObjWithDict()
        d = _to_dict(obj)
        assert d == {"a": 1}

    def test_to_dict_fallback_to_vars(self):
        """_to_dict 回退到 __dict__"""
        class PlainObj:
            def __init__(self):
                self.x = 42
                self.y = "hello"
        obj = PlainObj()
        d = _to_dict(obj)
        assert d["x"] == 42
        assert d["y"] == "hello"

    def test_ensure_serializable_datetime(self):
        """_ensure_serializable 处理 datetime"""
        dt = datetime(2025, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
        result = AdminService._ensure_serializable(dt)
        assert isinstance(result, str)
        assert "2025" in result

    def test_ensure_serializable_nested(self):
        """_ensure_serializable 递归处理嵌套结构"""
        data = {
            "a": 1,
            "b": [datetime(2025, 1, 1, tzinfo=timezone.utc), "hello"],
            "c": {"d": True, "e": None},
        }
        result = AdminService._ensure_serializable(data)
        assert isinstance(result["b"][0], str)
        assert result["c"]["d"] is True
        assert result["c"]["e"] is None

    def test_ensure_serializable_complex_object(self):
        """_ensure_serializable 处理不可序列化对象"""
        class Custom:
            def __str__(self):
                return "custom_str"
        result = AdminService._ensure_serializable(Custom())
        assert result == "custom_str"

    def test_ensure_serializable_tuple(self):
        """_ensure_serializable 处理 tuple"""
        result = AdminService._ensure_serializable((1, 2, "three"))
        assert result == [1, 2, "three"]
        assert isinstance(result, list)

    def test_to_dict_model_dump_raises_fallback_to_dict(self):
        """_to_dict: model_dump 抛出异常时回退到 dict()"""
        class BadModel:
            def model_dump(self, exclude_none=True):
                raise RuntimeError("model_dump failed")
            def dict(self, exclude_none=True):
                return {"key": "from_dict"}
        obj = BadModel()
        d = _to_dict(obj)
        assert d == {"key": "from_dict"}

    def test_to_dict_both_raise_fallback_to_vars(self):
        """_to_dict: model_dump 和 dict() 都抛出异常时回退到 __dict__"""
        class VeryBadModel:
            def __init__(self):
                self.fallback = "vars"
            def model_dump(self, exclude_none=True):
                raise RuntimeError("model_dump failed")
            def dict(self, exclude_none=True):
                raise RuntimeError("dict failed")
        obj = VeryBadModel()
        d = _to_dict(obj)
        assert d["fallback"] == "vars"

    def test_to_dict_no_attrs(self):
        """_to_dict: 无任何可转换属性返回 {}"""
        class Empty:
            pass
        obj = Empty()
        d = _to_dict(obj)
        assert d == {}

    def test_ensure_serializable_jsonable_object(self):
        """_ensure_serializable 处理 json.dumps 可序列化的非标准对象"""
        import decimal
        d = decimal.Decimal("3.14")
        result = AdminService._ensure_serializable(d)
        # Decimal 支持 json.dumps(str(obj)) 但实际 dumps 会失败
        # 最终回退到 str()
        assert isinstance(result, str)


# ============================================================================
# 4. FastAPI 端点补充测试
# ============================================================================

class TestAdminFastAPISupplement:
    """FastAPI 端点补充测试（覆盖 config, users, cases CRUD, 错误路径）"""

    def setup_method(self, method):
        pytest.importorskip("fastapi", reason="fastapi 未安装")
        self.path = _unique_db_path(f"api_{method.__name__}")
        self.service = AdminService(db_path=self.path)
        from tengod.admin_api import create_admin_app
        self.app = create_admin_app(service=self.service)
        from fastapi.testclient import TestClient
        self.client = TestClient(self.app)

    def teardown_method(self, method):
        try:
            self.service = None
            if os.path.exists(self.path):
                os.remove(self.path)
        except Exception:
            pass

    # ── 系统 ────────────────────────────────────────────────

    def test_config_set_and_list(self):
        """POST /api/admin/config 设置 + GET /api/admin/config 列出"""
        resp = self.client.post("/api/admin/config", json={"key": "test_k", "value": "test_v"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        resp2 = self.client.get("/api/admin/config")
        assert resp2.status_code == 200
        data = resp2.json()
        assert data.get("test_k") == "test_v"

    # ── 八字记录 API ────────────────────────────────────────

    def test_list_records(self):
        """GET /api/admin/records 返回列表"""
        resp = self.client.get("/api/admin/records")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_record_invalid(self):
        """POST /api/admin/records 无效数据返回 422"""
        resp = self.client.post("/api/admin/records", json={})
        assert resp.status_code == 422

    def test_get_record_404(self):
        """GET /api/admin/records/99999 返回 404"""
        resp = self.client.get("/api/admin/records/99999")
        assert resp.status_code == 404

    def test_update_record_404(self):
        """PATCH /api/admin/records/99999 返回 404"""
        resp = self.client.patch("/api/admin/records/99999", json={"label": "x"})
        assert resp.status_code == 404

    def test_delete_record_404(self):
        """DELETE /api/admin/records/99999 返回 404"""
        resp = self.client.delete("/api/admin/records/99999")
        assert resp.status_code == 404

    def test_update_record_success(self):
        """PATCH /api/admin/records/{id} 成功更新"""
        rec = self.service.create_record({
            "year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male",
        })
        resp = self.client.patch(
            f"/api/admin/records/{rec['id']}",
            json={"label": "updated_label"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_delete_record_success(self):
        """DELETE /api/admin/records/{id} 成功删除"""
        rec = self.service.create_record({
            "year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male",
        })
        resp = self.client.delete(f"/api/admin/records/{rec['id']}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    # ── 案例管理 API ─────────────────────────────────────────

    def test_list_cases(self):
        """GET /api/admin/cases 返回列表"""
        resp = self.client.get("/api/admin/cases")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_case_endpoint(self):
        """POST /api/admin/cases 创建案例"""
        resp = self.client.post("/api/admin/cases", json={
            "title": "API案例", "category": "api_test", "is_public": True,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "API案例"

    def test_create_case_invalid(self):
        """POST /api/admin/cases 无效数据返回 422"""
        resp = self.client.post("/api/admin/cases", json={})
        assert resp.status_code == 422

    def test_update_case_endpoint(self):
        """PATCH /api/admin/cases/{id} 更新案例"""
        case = self.service.create_case({"title": "待更新案例"})
        resp = self.client.patch(
            f"/api/admin/cases/{case['id']}",
            json={"title": "已更新", "summary": "新摘要"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_update_case_404(self):
        """PATCH /api/admin/cases/99999 返回 404"""
        resp = self.client.patch("/api/admin/cases/99999", json={"title": "x"})
        assert resp.status_code == 404

    def test_delete_case_endpoint(self):
        """DELETE /api/admin/cases/{id} 删除案例"""
        case = self.service.create_case({"title": "待删除"})
        resp = self.client.delete(f"/api/admin/cases/{case['id']}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_delete_case_404(self):
        """DELETE /api/admin/cases/99999 返回 404"""
        resp = self.client.delete("/api/admin/cases/99999")
        assert resp.status_code == 404

    # ── 用户管理 API ─────────────────────────────────────────

    def test_list_users(self):
        """GET /api/admin/users 返回列表"""
        resp = self.client.get("/api/admin/users")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_user_404(self):
        """GET /api/admin/users/99999 返回 404"""
        resp = self.client.get("/api/admin/users/99999")
        assert resp.status_code == 404

    def test_update_user_endpoint(self):
        """PATCH /api/admin/users/{id} 更新用户"""
        user = self.service.create_user({"username": "api_user"})
        resp = self.client.patch(
            f"/api/admin/users/{user['id']}",
            json={"display_name": "API更新"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_update_user_404(self):
        """PATCH /api/admin/users/99999 返回 404"""
        resp = self.client.patch("/api/admin/users/99999", json={"display_name": "x"})
        assert resp.status_code == 404

    # ── 高级分析 API ────────────────────────────────────────

    def test_trajectory_inline_bazi(self):
        """POST /api/admin/analysis/trajectory 内联八字数据"""
        resp = self.client.post(
            "/api/admin/analysis/trajectory",
            json={
                "year": 1990, "month": 6, "day": 15, "hour": 10,
                "gender": "male", "start_year": 1990, "end_year": 2030,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "dayun" in data

    def test_trajectory_missing_params(self):
        """POST /api/admin/analysis/trajectory 缺少参数返回 400"""
        resp = self.client.post(
            "/api/admin/analysis/trajectory",
            json={"start_year": 1990, "end_year": 2030},
        )
        assert resp.status_code == 400

    # ── 获取记录详情 ────────────────────────────────────────

    def test_get_record_endpoint(self):
        """GET /api/admin/records/{id} 成功获取记录"""
        rec = self.service.create_record({
            "year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male",
        })
        resp = self.client.get(f"/api/admin/records/{rec['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == rec["id"]

    def test_get_user_endpoint(self):
        """GET /api/admin/users/{id} 成功获取用户"""
        user = self.service.create_user({"username": "api_get_user"})
        resp = self.client.get(f"/api/admin/users/{user['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == user["id"]


# ============================================================================
# 5. 集成 / 边缘情况
# ============================================================================

class TestIntegrationEdgeCases:
    """集成测试和边缘情况"""

    def setup_method(self, method):
        self.path = _unique_db_path(f"ie_{method.__name__}")
        self.service = AdminService(db_path=self.path)

    def teardown_method(self, method):
        try:
            self.service = None
            if os.path.exists(self.path):
                os.remove(self.path)
        except Exception:
            pass

    def test_full_crud_cycle(self):
        """完整的 CRUD 周期：创建 → 读取 → 更新 → 删除"""
        # 创建
        rec = self.service.create_record({
            "year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male",
        })
        assert "id" in rec
        rid = rec["id"]

        # 读取
        got = self.service.get_record(rid)
        assert got is not None
        assert got["year"] == 1990

        # 更新
        ok = self.service.update_record(rid, {"label": "CRUD测试"})
        assert ok is True
        updated = self.service.get_record(rid)
        assert updated["label"] == "CRUD测试"

        # 删除
        ok = self.service.delete_record(rid)
        assert ok is True
        assert self.service.get_record(rid) is None

    def test_case_full_crud_cycle(self):
        """案例完整 CRUD 周期"""
        case = self.service.create_case({"title": "CRUD案例"})
        assert "id" in case
        cid = case["id"]

        ok = self.service.update_case(cid, {"title": "更新后案例"})
        assert ok is True

        ok = self.service.delete_case(cid)
        assert ok is True

    def test_user_full_crud_cycle(self):
        """用户完整 CRUD 周期"""
        user = self.service.create_user({"username": "crud_user"})
        assert "id" in user
        uid = user["id"]

        got = self.service.get_user(uid)
        assert got is not None
        assert got["username"] == "crud_user"

        ok = self.service.update_user(uid, {"display_name": "CRUD用户"})
        assert ok is True

    def test_pagination_boundary(self):
        """分页边界测试"""
        for i in range(10):
            self.service.create_record({
                "year": 1990 + i, "month": 1, "day": 1, "hour": 8, "gender": "male",
            })
        # 第一页
        page1 = self.service.get_records_paginated(limit=5, offset=0)
        assert len(page1) == 5
        # 第二页
        page2 = self.service.get_records_paginated(limit=5, offset=5)
        assert len(page2) == 5
        # 超出范围
        page3 = self.service.get_records_paginated(limit=5, offset=20)
        assert len(page3) == 0

    def test_create_record_with_all_fields(self):
        """create_record 包含所有可选字段"""
        result = self.service.create_record({
            "year": 1990, "month": 6, "day": 15, "hour": 10,
            "minute": 30, "gender": "female",
            "longitude": 121.5, "latitude": 31.2,
            "user_id": 1, "label": "完整记录",
            "tags": "tag1,tag2", "notes": "详细备注",
        })
        assert "error" not in result
        assert result["year"] == 1990
        assert result["gender"] == "female"
        assert result["label"] == "完整记录"

    def test_compare_same_record_returns_100(self):
        """相同记录对比返回 100%"""
        rid = self.service.create_record({
            "year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male",
        })["id"]
        comp = self.service.compare_cases(rid, rid)
        assert comp["similarity_score"] == 100.0

    def test_stats_after_data_creation(self):
        """创建数据后统计正确"""
        self.service.create_user({"username": "s1"})
        self.service.create_user({"username": "s2"})
        for i in range(3):
            self.service.create_record({
                "year": 1990 + i, "month": 1, "day": 1, "hour": 8, "gender": "male",
            })
        self.service.create_case({"title": "案例1"})
        stats = self.service.get_system_stats()
        assert stats["total_users"] >= 2
        assert stats["total_records"] >= 3
        assert stats["total_cases"] >= 1

    def test_stats_with_callable_recent_activity(self):
        """get_system_stats 处理 callable 的 recent_activity"""
        # 注入 callable 到 base.stats()
        mock_stats = {
            "total_records": 5,
            "total_cases": 2,
            "db_path": "/test/path.db",
            "db_size_mb": 10.5,
            "recent_activity": lambda: "called",
            "top_day_masters": [{"dm": "甲", "count": 2}],
        }
        with patch.object(self.service.store, 'stats', return_value=mock_stats):
            stats = self.service.get_system_stats()
            assert stats["recent_activity"] == "called"

    def test_stats_with_int_recent_activity(self):
        """get_system_stats 处理 int 类型的 recent_activity"""
        mock_stats = {
            "total_records": 5, "total_cases": 2, "recent_activity": 12345,
        }
        with patch.object(self.service.store, 'stats', return_value=mock_stats):
            stats = self.service.get_system_stats()
            assert stats["recent_activity"] == "12345"

    def test_stats_with_none_recent_activity(self):
        """get_system_stats 处理 None 的 recent_activity"""
        mock_stats = {
            "total_records": 5, "total_cases": 2, "recent_activity": None,
        }
        with patch.object(self.service.store, 'stats', return_value=mock_stats):
            stats = self.service.get_system_stats()
            assert stats["recent_activity"] == ""

    def test_get_system_stats_exception_handling(self):
        """get_system_stats 捕获异常返回默认值"""
        with patch.object(self.service.store, 'stats', side_effect=Exception("boom")):
            stats = self.service.get_system_stats()
            assert "error" in stats
            assert stats["total_users"] == 0
            assert stats["total_records"] == 0


# ============================================================================
# 6. 冒烟测试
# ============================================================================

def test_smoke_version():
    """确认模块版本号"""
    from tengod.admin_api import __version__
    assert __version__ == "1.0.0"


def test_smoke_all_exports():
    """确认所有导出可用"""
    from tengod.admin_api import (
        AdminService, create_admin_app,
        BaziRecordInput, BaziRecordUpdate,
        CaseInput, CaseUpdate,
        UserCreate, UserUpdate,
        TrajectoryQuery, BatchBaziQuery,
        CompareQuery, ConfigUpdate,
    )
    assert AdminService is not None
    assert create_admin_app is not None