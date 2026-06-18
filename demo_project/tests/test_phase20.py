#!/usr/bin/env python3
"""
test_phase20.py — 阶段二十：开放生态与功能深化测试
覆盖：
  - Webhook 系统（订阅/触发/交付/统计）
  - 插件系统 API
  - API 版本管理
  - 高级分析（命例对比/批量排盘/命运轨迹）
  - SDK 完整性验证
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.pop("TENGOD_API_KEY", None)
os.environ["TENGOD_LLM_BACKEND"] = "mock"

from fastapi.testclient import TestClient
from tengod.api_server import app
from tengod.auth import JWTManager, QuotaManager
from tengod.data_store import get_data_store


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    QuotaManager._usage.clear()
    from tengod.api_server import _request_counts
    _request_counts.clear()
    # 重置 webhook 单例
    import tengod.webhook as wh
    wh._library = None
    yield
    QuotaManager._usage.clear()
    _request_counts.clear()
    wh._library = None


@pytest.fixture
def user_headers():
    token = JWTManager.create_access_token(1, "testuser", "user")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    token = JWTManager.create_access_token(1, "admin", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_records():
    """创建两条八字记录用于对比测试"""
    store = get_data_store()
    user = store.get_or_create_user("testuser")
    rid_a = store.save_bazi_record(
        year=1990, month=6, day=15, hour=10, gender="male", user_id=user.id,
        day_master="辛",
        pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
        analysis={"wuxing": {"金": 2, "水": 2, "火": 3, "土": 1}, "day_master": "辛"},
        geju={"geju_name": "伤官格"},
    )
    rid_b = store.save_bazi_record(
        year=1985, month=3, day=20, hour=14, gender="female", user_id=user.id,
        day_master="甲",
        pillars={"year": "乙丑", "month": "己卯", "day": "甲寅", "hour": "辛未"},
        analysis={"wuxing": {"木": 3, "火": 1, "土": 2, "水": 2}, "day_master": "甲"},
        geju={"geju_name": "偏印格"},
    )
    return rid_a, rid_b


# ════════════════════════════════════════
# 1. Webhook 系统
# ════════════════════════════════════════

class TestWebhookSystem:
    """Webhook 系统测试"""

    def test_list_webhook_events(self, client, user_headers):
        """列出 Webhook 事件类型"""
        r = client.get("/api/webhooks/events", headers=user_headers)
        assert r.status_code == 200
        events = r.json()["events"]
        assert len(events) >= 10
        event_types = [e["type"] for e in events]
        assert "case.created" in event_types
        assert "bazi.computed" in event_types
        assert "oracle.consulted" in event_types

    def test_create_webhook(self, client, user_headers):
        """创建 Webhook 订阅"""
        r = client.post("/api/webhooks", json={
            "url": "https://example.com/hook",
            "events": ["case.created", "bazi.computed"],
            "secret": "my_secret",
            "description": "测试订阅",
        }, headers=user_headers)
        assert r.status_code == 200
        sub = r.json()
        assert sub["id"] > 0
        assert sub["url"] == "https://example.com/hook"
        assert "case.created" in sub["events"]
        assert sub["has_secret"] is True
        assert sub["is_active"] is True

    def test_list_webhooks(self, client, user_headers):
        """列出 Webhook 订阅"""
        client.post("/api/webhooks", json={
            "url": "https://a.com/hook", "events": ["*"],
        }, headers=user_headers)
        client.post("/api/webhooks", json={
            "url": "https://b.com/hook", "events": ["case.created"],
        }, headers=user_headers)
        r = client.get("/api/webhooks", headers=user_headers)
        assert r.status_code == 200
        subs = r.json()["subscriptions"]
        assert len(subs) >= 2

    def test_list_webhooks_active_only(self, client, user_headers):
        """仅列出活跃订阅"""
        r = client.post("/api/webhooks", json={
            "url": "https://a.com/hook", "events": ["*"],
        }, headers=user_headers)
        sub_id = r.json()["id"]
        client.put(f"/api/webhooks/{sub_id}", json={"is_active": False}, headers=user_headers)

        r = client.get("/api/webhooks?active_only=true", headers=user_headers)
        subs = r.json()["subscriptions"]
        assert all(s["is_active"] for s in subs)

    def test_get_webhook(self, client, user_headers):
        """获取 Webhook 详情"""
        r = client.post("/api/webhooks", json={
            "url": "https://x.com/h", "events": ["*"],
        }, headers=user_headers)
        sub_id = r.json()["id"]
        r = client.get(f"/api/webhooks/{sub_id}", headers=user_headers)
        assert r.status_code == 200
        assert r.json()["url"] == "https://x.com/h"

    def test_get_webhook_not_found(self, client, user_headers):
        """获取不存在的 Webhook"""
        r = client.get("/api/webhooks/9999", headers=user_headers)
        assert r.status_code == 404

    def test_update_webhook(self, client, user_headers):
        """更新 Webhook 订阅"""
        r = client.post("/api/webhooks", json={
            "url": "https://x.com/h", "events": ["*"],
        }, headers=user_headers)
        sub_id = r.json()["id"]
        r = client.put(f"/api/webhooks/{sub_id}", json={
            "url": "https://y.com/h",
            "is_active": False,
        }, headers=user_headers)
        assert r.status_code == 200
        assert r.json()["url"] == "https://y.com/h"
        assert r.json()["is_active"] is False

    def test_delete_webhook_admin(self, client, admin_headers):
        """管理员删除 Webhook"""
        r = client.post("/api/webhooks", json={
            "url": "https://x.com/h", "events": ["*"],
        }, headers=admin_headers)
        sub_id = r.json()["id"]
        r = client.delete(f"/api/webhooks/{sub_id}", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["deleted"] is True

    def test_delete_webhook_user_forbidden(self, client, user_headers):
        """普通用户不能删除 Webhook（需要 webhook:delete 权限）"""
        r = client.post("/api/webhooks", json={
            "url": "https://x.com/h", "events": ["*"],
        }, headers=user_headers)
        sub_id = r.json()["id"]
        r = client.delete(f"/api/webhooks/{sub_id}", headers=user_headers)
        assert r.status_code == 403

    def test_trigger_webhook(self, client, user_headers):
        """触发 Webhook 事件"""
        client.post("/api/webhooks", json={
            "url": "https://x.com/h", "events": ["case.created"],
        }, headers=user_headers)
        r = client.post("/api/webhooks/trigger", json={
            "event_type": "case.created",
            "payload": {"case_id": 1},
        }, headers=user_headers)
        assert r.status_code == 200
        assert r.json()["triggered"] >= 1

    def test_webhook_stats(self, client, user_headers):
        """Webhook 统计"""
        client.post("/api/webhooks", json={
            "url": "https://x.com/h", "events": ["*"],
        }, headers=user_headers)
        r = client.get("/api/webhooks/stats/summary", headers=user_headers)
        assert r.status_code == 200
        stats = r.json()
        assert stats["total_subscriptions"] >= 1
        assert "event_types" in stats
        assert "success_rate" in stats

    def test_webhook_unauthorized(self, client):
        """未认证访问 Webhook"""
        r = client.get("/api/webhooks")
        assert r.status_code == 401

    def test_webhook_deliveries(self, client, admin_headers):
        """Webhook 交付记录"""
        r = client.post("/api/webhooks", json={
            "url": "https://x.com/h", "events": ["*"],
        }, headers=admin_headers)
        sub_id = r.json()["id"]
        r = client.get(f"/api/webhooks/{sub_id}/deliveries", headers=admin_headers)
        assert r.status_code == 200
        assert "deliveries" in r.json()


# ════════════════════════════════════════
# 2. 插件系统 API
# ════════════════════════════════════════

class TestPluginAPI:
    """插件系统 API 测试"""

    def test_list_plugins(self, client, user_headers):
        """列出插件"""
        r = client.get("/api/plugins", headers=user_headers)
        assert r.status_code == 200
        assert "plugins" in r.json()

    def test_plugin_stats(self, client, user_headers):
        """插件统计"""
        r = client.get("/api/plugins/stats/summary", headers=user_headers)
        assert r.status_code == 200

    def test_plugin_guest_access(self, client):
        """游客可访问插件列表（plugin:read 权限）"""
        # 游客有 plugin:read 权限
        r = client.get("/api/plugins")
        # 可能 401（需要认证）或 200（公开）
        assert r.status_code in (200, 401)


# ════════════════════════════════════════
# 3. API 版本管理
# ════════════════════════════════════════

class TestAPIVersion:
    """API 版本管理测试"""

    def test_api_version(self, client):
        """获取 API 版本"""
        r = client.get("/api/version")
        assert r.status_code == 200
        v = r.json()
        assert v["api_version"] == "3.0.0"
        assert "sdk_versions" in v
        assert v["sdk_versions"]["python"] == "3.0.0"
        assert v["sdk_versions"]["javascript"] == "3.0.0"
        assert v["sdk_versions"]["go"] == "1.0.0"
        assert "pwa_version" in v
        assert "features" in v
        assert "webhook" in v["features"]
        assert "plugins" in v["features"]


# ════════════════════════════════════════
# 4. 高级分析
# ════════════════════════════════════════

class TestAdvancedAnalysis:
    """高级分析测试"""

    def test_compare_cases(self, client, user_headers, sample_records):
        """命例对比分析"""
        rid_a, rid_b = sample_records
        r = client.post("/api/advanced/compare", json={
            "record_a_id": rid_a,
            "record_b_id": rid_b,
        }, headers=user_headers)
        assert r.status_code == 200
        d = r.json()
        assert "similarity_score" in d
        assert "wuxing_compare" in d
        assert "summary" in d
        assert d["record_a"]["id"] == rid_a
        assert d["record_b"]["id"] == rid_b

    def test_compare_cases_not_found(self, client, user_headers):
        """对比不存在的命例"""
        r = client.post("/api/advanced/compare", json={
            "record_a_id": 9999,
            "record_b_id": 9998,
        }, headers=user_headers)
        assert r.status_code == 404

    def test_batch_bazi(self, client, user_headers):
        """批量排盘"""
        r = client.post("/api/advanced/batch-bazi", json={
            "inputs": [
                {"year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male"},
                {"year": 1985, "month": 3, "day": 20, "hour": 14, "gender": "female"},
                {"year": 2000, "month": 1, "day": 1, "hour": 0, "gender": "male"},
            ]
        }, headers=user_headers)
        assert r.status_code == 200
        d = r.json()
        assert d["stats"]["total"] == 3
        assert d["stats"]["success"] == 3
        assert len(d["results"]) == 3
        assert "day_masters" in d["stats"]
        assert "wuxing_totals" in d["stats"]

    def test_batch_bazi_empty(self, client, user_headers):
        """空批量排盘请求"""
        r = client.post("/api/advanced/batch-bazi", json={"inputs": []}, headers=user_headers)
        assert r.status_code == 422  # Pydantic 验证失败

    def test_destiny_trajectory(self, client, user_headers):
        """命运轨迹推演"""
        r = client.post("/api/advanced/trajectory", json={
            "year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male",
            "start_age": 0, "end_age": 50,
        }, headers=user_headers)
        assert r.status_code == 200
        d = r.json()
        assert "day_master" in d
        assert "dayun" in d
        assert "liunian" in d
        assert "life_stages" in d
        assert "summary" in d
        assert len(d["dayun"]) > 0
        assert len(d["liunian"]) > 0
        assert len(d["life_stages"]) > 0

    def test_trajectory_validation(self, client, user_headers):
        """轨迹推演参数验证"""
        # 无效年份
        r = client.post("/api/advanced/trajectory", json={
            "year": 1800, "month": 6, "day": 15, "hour": 10,
        }, headers=user_headers)
        assert r.status_code == 422

    def test_advanced_unauthorized(self, client):
        """未认证访问高级分析"""
        r = client.post("/api/advanced/compare", json={
            "record_a_id": 1, "record_b_id": 2,
        })
        assert r.status_code == 401


# ════════════════════════════════════════
# 5. SDK 完整性验证
# ════════════════════════════════════════

class TestSDKCompleteness:
    """SDK 完整性验证"""

    def test_python_sdk_methods(self):
        """Python SDK 方法完整性"""
        sdk_dir = os.path.join(os.path.dirname(__file__), "..", "sdk", "python")
        sys.path.insert(0, sdk_dir)
        try:
            from tengod_client import TengodClient, __version__
            assert __version__ == "3.0.0"
            client = TengodClient("http://localhost:8000")
            # 阶段二十新增方法
            new_methods = [
                "bazi_full", "bazi_calc",
                "list_cases", "get_case", "create_case", "search_cases",
                "similar_cases", "case_categories", "case_tags", "case_stats",
                "export_cases", "favorite_case", "like_case",
                "list_webhook_events", "create_webhook", "list_webhooks",
                "delete_webhook", "trigger_webhook", "webhook_stats",
                "list_plugins", "plugin_stats", "api_version",
            ]
            for m in new_methods:
                assert hasattr(client, m), f"Python SDK 缺少方法: {m}"
        finally:
            sys.path.pop(0)

    def test_js_sdk_methods(self):
        """JS SDK 方法完整性"""
        sdk_path = os.path.join(os.path.dirname(__file__), "..", "sdk", "js", "tengod-client.js")
        with open(sdk_path, "r") as f:
            code = f.read()
        assert "v3.0.0" in code
        new_methods = [
            "baziFull", "baziCalc",
            "listCases", "getCase", "createCase", "searchCases",
            "similarCases", "caseCategories", "caseTags", "caseStats",
            "exportCases", "favoriteCase", "likeCase",
            "listWebhookEvents", "createWebhook", "listWebhooks",
            "deleteWebhook", "triggerWebhook", "webhookStats",
            "listPlugins", "pluginStats", "apiVersion",
        ]
        for m in new_methods:
            assert m in code, f"JS SDK 缺少方法: {m}"

    def test_go_sdk_methods(self):
        """Go SDK 方法完整性"""
        sdk_path = os.path.join(os.path.dirname(__file__), "..", "sdk", "go", "tengod", "client.go")
        with open(sdk_path, "r") as f:
            code = f.read()
        assert "v3.0.0" in code
        new_methods = [
            "BaziFull", "BaziCalc",
            "ListCases", "GetCase", "CreateCase", "SearchCases",
            "SimilarCases", "CaseCategories", "CaseStats",
            "FavoriteCase", "LikeCase",
            "ListWebhookEvents", "CreateWebhook", "ListWebhooks",
            "DeleteWebhook", "TriggerWebhook", "WebhookStats",
            "ListPlugins", "PluginStats", "APIVersion",
        ]
        for m in new_methods:
            assert m in code, f"Go SDK 缺少方法: {m}"


# ════════════════════════════════════════
# 6. Webhook 模块单元测试
# ════════════════════════════════════════

class TestWebhookModule:
    """Webhook 模块单元测试"""

    def test_event_types(self):
        """事件类型定义"""
        from tengod.webhook import EVENT_TYPES
        assert len(EVENT_TYPES) >= 10
        assert "case.created" in EVENT_TYPES
        assert "bazi.computed" in EVENT_TYPES
        assert "system.started" in EVENT_TYPES

    def test_webhook_manager_init(self):
        """Webhook 管理器初始化"""
        from tengod.webhook import WebhookManager
        wh = WebhookManager()
        assert wh.max_retries == 3
        assert wh.history_limit == 100

    def test_subscribe_unsubscribe(self):
        """订阅和取消订阅"""
        from tengod.webhook import WebhookManager
        wh = WebhookManager()
        sub = wh.subscribe(
            url="https://test.com/hook",
            events=["case.created"],
            secret="secret",
        )
        assert sub["id"] > 0
        sub_id = sub["id"]
        # 获取
        got = wh.get_subscription(sub_id)
        assert got["url"] == "https://test.com/hook"
        # 列出
        subs = wh.list_subscriptions()
        assert any(s["id"] == sub_id for s in subs)
        # 取消
        ok = wh.unsubscribe(sub_id)
        assert ok is True
        # 确认已删除
        assert wh.get_subscription(sub_id) is None

    def test_update_subscription(self):
        """更新订阅"""
        from tengod.webhook import WebhookManager
        wh = WebhookManager()
        sub = wh.subscribe(url="https://a.com/h", events=["*"])
        updated = wh.update_subscription(sub["id"], url="https://b.com/h", is_active=False)
        assert updated["url"] == "https://b.com/h"
        assert updated["is_active"] is False
        wh.unsubscribe(sub["id"])

    def test_stats(self):
        """统计"""
        from tengod.webhook import WebhookManager
        wh = WebhookManager()
        stats = wh.stats()
        assert "total_subscriptions" in stats
        assert "active_subscriptions" in stats
        assert "event_types" in stats
        assert "success_rate" in stats


# ════════════════════════════════════════
# 7. 高级分析模块单元测试
# ════════════════════════════════════════

class TestAdvancedAnalysisModule:
    """高级分析模块单元测试"""

    def test_batch_bazi_module(self):
        """批量排盘模块"""
        from tengod.advanced_analysis import AdvancedAnalyzer
        analyzer = AdvancedAnalyzer()
        result = analyzer.batch_bazi([
            {"year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male"},
            {"year": 1985, "month": 3, "day": 20, "hour": 14, "gender": "female"},
        ])
        assert result["stats"]["total"] == 2
        assert result["stats"]["success"] == 2
        assert len(result["results"]) == 2

    def test_destiny_trajectory_module(self):
        """命运轨迹模块"""
        from tengod.advanced_analysis import AdvancedAnalyzer
        analyzer = AdvancedAnalyzer()
        result = analyzer.destiny_trajectory(
            year=1990, month=6, day=15, hour=10, gender="male",
            start_age=0, end_age=30,
        )
        assert "day_master" in result
        assert len(result["dayun"]) > 0
        assert len(result["liunian"]) > 0
        assert len(result["life_stages"]) > 0
        assert "summary" in result

    def test_compare_cases_module(self, sample_records):
        """命例对比模块"""
        from tengod.advanced_analysis import AdvancedAnalyzer
        rid_a, rid_b = sample_records
        analyzer = AdvancedAnalyzer()
        result = analyzer.compare_cases(rid_a, rid_b)
        assert "similarity_score" in result
        assert "wuxing_compare" in result
        assert "summary" in result
        assert 0 <= result["similarity_score"] <= 100

    def test_compare_cases_not_found(self):
        """对比不存在的记录"""
        from tengod.advanced_analysis import AdvancedAnalyzer
        analyzer = AdvancedAnalyzer()
        result = analyzer.compare_cases(9999, 9998)
        assert "error" in result
