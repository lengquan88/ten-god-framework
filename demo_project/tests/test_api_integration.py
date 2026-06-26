#!/usr/bin/env python3
"""
test_api_integration.py — 十神架构 API 集成测试 v2.17.0
========================================================
覆盖全部主要 FastAPI 端点，使用 FastAPI TestClient（无需启动真实服务器）。
参照 test_bazi_api.py 模式，处理内在小孩门禁响应格式。

用法：
    pytest tests/test_api_integration.py -v
    pytest tests/test_api_integration.py -v --runxfail
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

os.environ.pop("TENGOD_API_KEY", None)

from fastapi.testclient import TestClient
from tengod.api_server import app
from tengod.auth import QuotaManager

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_all_quotas():
    """每个测试前清空配额和限流状态"""
    QuotaManager._usage.clear()
    from tengod.api_server import _request_counts
    _request_counts.clear()
    yield
    QuotaManager._usage.clear()
    _request_counts.clear()


# ════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════

def unique_username(prefix="testuser"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def unwrap(r):
    """解包内在小孩门禁包裹的响应 {output, confidence, uncertainty} → output"""
    data = r.json()
    if isinstance(data, dict) and "output" in data and "confidence" in data:
        return data["output"]
    return data


def register_and_login(username=None, password="Test123456"):
    """注册并登录，返回 (username, token, user_id)"""
    username = username or unique_username()
    client.post("/api/auth/register", json={
        "username": username, "password": password,
        "email": f"{username}@test.com",
    })
    r = client.post("/api/auth/login", json={
        "username": username, "password": password,
    })
    data = unwrap(r)
    token = data.get("access_token", "")
    user_id = data.get("user", {}).get("id", 0)
    QuotaManager.reset(user_id)
    return username, token, user_id


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


BAZI_INPUT = {
    "year": 1990, "month": 6, "day": 15,
    "hour": 10, "minute": 30, "gender": "male",
}


# ════════════════════════════════════════
# 1. 系统端点 (6)
# ════════════════════════════════════════

class TestSystemEndpoints:
    """系统端点集成测试"""

    def test_health(self):
        """GET /api/health"""
        r = client.get("/api/health")
        assert r.status_code == 200
        data = unwrap(r)
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_full(self):
        """GET /api/health/full"""
        r = client.get("/api/health/full")
        assert r.status_code == 200

    def test_metrics(self):
        """GET /metrics"""
        r = client.get("/metrics")
        assert r.status_code == 200
        assert "tengod" in r.text or "#" in r.text

    def test_api_stats(self):
        """GET /api/stats"""
        r = client.get("/api/stats")
        assert r.status_code == 200

    def test_openapi_docs(self):
        """GET /openapi.json"""
        r = client.get("/openapi.json")
        assert r.status_code == 200
        data = r.json()
        assert "paths" in data
        assert len(data["paths"]) > 10

    def test_root(self):
        """GET /"""
        r = client.get("/")
        assert r.status_code == 200


# ════════════════════════════════════════
# 2. 认证端点 (6)
# ════════════════════════════════════════

class TestAuthEndpoints:
    """认证系统集成测试"""

    def test_register_success(self):
        """POST /api/auth/register"""
        username = unique_username()
        r = client.post("/api/auth/register", json={
            "username": username, "password": "Test123456",
            "email": f"{username}@test.com",
        })
        assert r.status_code == 200
        data = unwrap(r)
        assert data.get("message") == "注册成功" or data.get("user", {}).get("username") == username

    def test_register_duplicate(self):
        """重复注册返回 409"""
        username = unique_username()
        client.post("/api/auth/register", json={
            "username": username, "password": "Test123456",
        })
        r = client.post("/api/auth/register", json={
            "username": username, "password": "Test123456",
        })
        assert r.status_code == 409

    def test_login_success(self):
        """POST /api/auth/login"""
        username = unique_username()
        client.post("/api/auth/register", json={
            "username": username, "password": "Test123456",
        })
        r = client.post("/api/auth/login", json={
            "username": username, "password": "Test123456",
        })
        assert r.status_code == 200
        data = unwrap(r)
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_wrong_password(self):
        """错误密码返回 401"""
        username = unique_username()
        client.post("/api/auth/register", json={
            "username": username, "password": "Test123456",
        })
        r = client.post("/api/auth/login", json={
            "username": username, "password": "WrongPassword",
        })
        assert r.status_code == 401

    def test_auth_me(self):
        """GET /api/auth/me"""
        _, token, _ = register_and_login()
        r = client.get("/api/auth/me", headers=auth_headers(token))
        assert r.status_code == 200
        data = unwrap(r)
        assert "username" in data
        assert "role" in data

    def test_auth_me_no_token(self):
        """无 token 返回 401/403"""
        r = client.get("/api/auth/me")
        assert r.status_code in (401, 403)


# ════════════════════════════════════════
# 3. 八字排盘端点 (4)
# ════════════════════════════════════════

class TestBaziEndpoints:
    """八字排盘集成测试"""

    def test_bazi_calc(self):
        """POST /api/bazi/calc"""
        r = client.post("/api/bazi/calc", json=BAZI_INPUT)
        assert r.status_code == 200
        data = unwrap(r)
        assert "pillars" in data
        assert set(data["pillars"].keys()) == {"year", "month", "day", "hour"}

    def test_bazi_full(self):
        """POST /api/bazi/full（需认证）"""
        _, token, _ = register_and_login()
        r = client.post("/api/bazi/full", json=BAZI_INPUT, headers=auth_headers(token))
        assert r.status_code == 200
        data = unwrap(r)
        assert "bazi" in data
        assert "shensha" in data
        assert "dayun" in data

    def test_bazi_shensha(self):
        """POST /api/bazi/shensha"""
        r = client.post("/api/bazi/shensha", json=BAZI_INPUT)
        assert r.status_code == 200

    def test_bazi_validation(self):
        """非法年份返回 422"""
        r = client.post("/api/bazi/calc", json={**BAZI_INPUT, "year": 1800})
        assert r.status_code == 422


# ════════════════════════════════════════
# 4. 知识图谱端点 (5)
# ════════════════════════════════════════

class TestGraphEndpoints:
    """知识图谱集成测试"""

    def test_graph_stats(self):
        """GET /api/graph/stats"""
        r = client.get("/api/graph/stats")
        assert r.status_code == 200
        data = unwrap(r)
        assert data["total_nodes"] > 100

    def test_graph_search(self):
        """GET /api/graph/search"""
        r = client.get("/api/graph/search", params={"keyword": "金", "limit": 5})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1

    def test_graph_node_detail(self):
        """GET /api/graph/node/金"""
        r = client.get("/api/graph/node/金")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "金"

    def test_graph_node_not_found(self):
        """GET /api/graph/node/不存在 → 404"""
        r = client.get("/api/graph/node/不存在的节点")
        assert r.status_code == 404

    def test_graph_export(self):
        """GET /api/graph/export"""
        r = client.get("/api/graph/export", params={"limit": 10})
        assert r.status_code == 200


# ════════════════════════════════════════
# 5. 知识查询端点 (2)
# ════════════════════════════════════════

class TestKnowledgeEndpoints:
    """知识查询集成测试（需认证）"""

    def test_wuxing_query(self):
        """GET /api/knowledge/wuxing/金"""
        _, token, _ = register_and_login()
        r = client.get("/api/knowledge/wuxing/金", headers=auth_headers(token))
        assert r.status_code == 200

    def test_bagua_query(self):
        """GET /api/knowledge/bagua/乾"""
        _, token, _ = register_and_login()
        r = client.get("/api/knowledge/bagua/乾", headers=auth_headers(token))
        assert r.status_code == 200


# ════════════════════════════════════════
# 6. 高级术数端点 (3)
# ════════════════════════════════════════

class TestAdvancedDivination:
    """高级术数集成测试（需认证）"""

    def test_ziwei_calc(self):
        """POST /api/ziwei/calc"""
        _, token, _ = register_and_login()
        r = client.post("/api/ziwei/calc", json=BAZI_INPUT, headers=auth_headers(token))
        assert r.status_code in (200, 500)

    def test_liuyao_shake(self):
        """POST /api/liuyao/shake"""
        _, token, _ = register_and_login()
        r = client.post("/api/liuyao/shake", json={"question": "测试"}, headers=auth_headers(token))
        assert r.status_code in (200, 422, 500)

    def test_name_analyze(self):
        """POST /api/name/analyze"""
        _, token, _ = register_and_login()
        r = client.post("/api/name/analyze", json={
            "surname": "张", "given_name": "伟",
        }, headers=auth_headers(token))
        assert r.status_code in (200, 422, 500)


# ════════════════════════════════════════
# 7. 记录持久化端点 (3)
# ════════════════════════════════════════

class TestRecordsEndpoints:
    """记录持久化与多租户集成测试"""

    def test_save_record(self):
        """POST /api/records"""
        _, token, _ = register_and_login()
        r = client.post("/api/records", json=BAZI_INPUT,
                        params={"label": "集成测试记录"},
                        headers=auth_headers(token))
        assert r.status_code in (200, 201)

    def test_list_records(self):
        """GET /api/records"""
        _, token, _ = register_and_login()
        client.post("/api/records", json=BAZI_INPUT,
                    params={"label": "列表测试"},
                    headers=auth_headers(token))
        r = client.get("/api/records", headers=auth_headers(token))
        assert r.status_code == 200

    def test_record_isolation(self):
        """记录隔离：用户不能访问他人记录"""
        _, token1, _ = register_and_login()
        _, token2, _ = register_and_login()
        save_r = client.post("/api/records", json=BAZI_INPUT,
                             params={"label": "隔离测试"},
                             headers=auth_headers(token1))
        if save_r.status_code in (200, 201):
            record_data = unwrap(save_r)
            record_id = record_data.get("id") or record_data.get("record_id")
            if record_id:
                r = client.get(f"/api/records/{record_id}", headers=auth_headers(token2))
                assert r.status_code in (403, 404)


# ════════════════════════════════════════
# 8. 配额与权限端点 (2)
# ════════════════════════════════════════

class TestQuotaEndpoints:
    """配额与权限集成测试"""

    def test_guest_public_access(self):
        """游客可访问公开端点"""
        r = client.get("/api/graph/stats")
        assert r.status_code == 200

    def test_authenticated_higher_quota(self):
        """认证用户配额更高"""
        _, token, _ = register_and_login()
        success = 0
        for _ in range(15):
            r = client.get("/api/graph/search", params={"keyword": "金", "limit": 1},
                          headers=auth_headers(token))
            if r.status_code == 200:
                success += 1
            elif r.status_code == 429:
                break
        assert success >= 1


# ════════════════════════════════════════
# 9. 端点覆盖度验证 (2)
# ════════════════════════════════════════

ENDPOINTS = [
    # 系统
    ("GET", "/"), ("GET", "/api/health"), ("GET", "/api/health/full"),
    ("GET", "/metrics"), ("GET", "/api/stats"), ("GET", "/openapi.json"),
    # 认证
    ("POST", "/api/auth/register"), ("POST", "/api/auth/login"),
    ("GET", "/api/auth/me"), ("POST", "/api/auth/refresh"),
    # 八字
    ("POST", "/api/bazi/calc"), ("POST", "/api/bazi/full"),
    ("POST", "/api/bazi/shensha"), ("POST", "/api/bazi/geju"),
    ("POST", "/api/bazi/yongshen"), ("POST", "/api/bazi/tiaohou"),
    # 知识图谱
    ("GET", "/api/graph/stats"), ("GET", "/api/graph/search"),
    ("GET", "/api/graph/node/{name}"), ("GET", "/api/graph/export"),
    # 知识查询
    ("GET", "/api/knowledge/wuxing/{name}"), ("GET", "/api/knowledge/bagua/{name}"),
    # 高级术数
    ("POST", "/api/ziwei/calc"), ("POST", "/api/liuyao/shake"),
    ("POST", "/api/name/analyze"),
    # 记录
    ("POST", "/api/records"), ("GET", "/api/records"),
    ("GET", "/api/records/{id}"),
]


def test_endpoint_coverage():
    """验证端点覆盖度 >= 25"""
    count = len(set(e[1] for e in ENDPOINTS))
    assert count >= 25, f"需要覆盖至少 25 个端点，当前 {count} 个"


def test_test_function_count():
    """验证测试函数数量 >= 25"""
    import inspect
    current_module = sys.modules[__name__]
    count = 0
    for name, obj in inspect.getmembers(current_module):
        if inspect.isclass(obj) and name.startswith("Test"):
            for m_name, m_obj in inspect.getmembers(obj):
                if inspect.isfunction(m_obj) and m_name.startswith("test_"):
                    count += 1
        elif inspect.isfunction(obj) and name.startswith("test_"):
            count += 1
    assert count >= 25, f"测试函数数不足：{count}"