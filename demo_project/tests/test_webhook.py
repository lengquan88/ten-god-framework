#!/usr/bin/env python3
"""
test_webhook.py — Webhook 系统单元测试
覆盖：EVENT_TYPES、ORM 模型、WebhookManager 所有方法、单例、边界情况
"""
import json
import os
import sys
import threading
from unittest.mock import MagicMock, patch, ANY

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


# ─── Mock 辅助 ────────────────────────────────────────────────────────────


class MockQuery:
    """模拟 SQLAlchemy Query 对象，支持链式调用"""

    def __init__(self, model_class, results=None):
        self._model_class = model_class
        self._results = results or []
        self._filters = {}
        self._order_by_clauses = []
        self._limit_val = None
        self._offset_val = 0

    def filter_by(self, **kwargs):
        self._filters.update(kwargs)
        return self

    def filter(self, *args):
        return self

    def order_by(self, *args):
        self._order_by_clauses = args
        return self

    def limit(self, n):
        self._limit_val = n
        return self

    def offset(self, n):
        self._offset_val = n
        return self

    def _apply_filters(self):
        results = list(self._results)
        for key, value in self._filters.items():
            results = [r for r in results if getattr(r, key, None) == value]
        return results

    def all(self):
        results = self._apply_filters()
        if self._limit_val is not None:
            results = results[self._offset_val:self._offset_val + self._limit_val]
        return results

    def first(self):
        results = self._apply_filters()
        return results[0] if results else None

    def count(self):
        return len(self._apply_filters())

    def scalar(self):
        return self.count()

    def delete(self):
        return len(self._apply_filters())


class MockSession:
    """模拟 SQLAlchemy Session，支持上下文管理器"""

    def __init__(self, query_results=None):
        self._query_results = query_results or {}
        self.added = []
        self.deleted = []
        self.committed = False
        self._query_factory = self._query_results

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        pass

    def query(self, model_class):
        results = self._query_factory.get(model_class, [])
        return MockQuery(model_class, results)

    def add(self, obj):
        self.added.append(obj)

    def delete(self, obj):
        self.deleted.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        pass


class MockStore:
    """模拟 DataStore"""

    def __init__(self, session=None):
        self._engine = MagicMock()
        self._session_to_return = session

    def _session(self):
        return self._session_to_return if self._session_to_return else MockSession()


def make_sub(id=1, url="https://example.com/webhook", events='["case.created"]',
             secret="secret123", is_active=True, description="test sub",
             created_at="2025-01-01T00:00:00", updated_at="2025-01-01T00:00:00",
             total_delivered=0, total_failed=0):
    """创建模拟的 WebhookSubscription 对象"""
    sub = MagicMock()
    sub.id = id
    sub.url = url
    sub.events = events
    sub.secret = secret
    sub.is_active = is_active
    sub.description = description
    sub.created_at = created_at
    sub.updated_at = updated_at
    sub.total_delivered = total_delivered
    sub.total_failed = total_failed
    return sub


def make_delivery(id=1, subscription_id=1, event_type="case.created",
                  payload='{"event":"case.created"}', status_code=200,
                  response_body="OK", success=True, attempt=1, error="",
                  created_at="2025-01-01T00:00:00", delivered_at="2025-01-01T00:00:00"):
    """创建模拟的 WebhookDelivery 对象"""
    d = MagicMock()
    d.id = id
    d.subscription_id = subscription_id
    d.event_type = event_type
    d.payload = payload
    d.status_code = status_code
    d.response_body = response_body
    d.success = success
    d.attempt = attempt
    d.error = error
    d.created_at = created_at
    d.delivered_at = delivered_at
    return d


# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def mock_base():
    """创建模拟的 SQLAlchemy Base 类"""
    base = MagicMock()
    base.metadata = MagicMock()
    base.metadata.create_all = MagicMock()
    return base


@pytest.fixture
def mock_store_factory():
    """创建模拟的 DataStore 工厂"""
    def _make(session=None):
        return MockStore(session=session)
    return _make


@pytest.fixture
def webhook_module(mock_base, mock_store_factory):
    """在隔离的 mock 环境中导入 webhook 模块"""
    with patch("tengod.webhook.Base", mock_base), \
         patch("tengod.webhook.get_data_store", return_value=MockStore()):
        import tengod.webhook as wh
        # 重置单例
        wh._library = None
        yield wh
        wh._library = None


@pytest.fixture
def manager(webhook_module, mock_base, mock_store_factory):
    """创建 WebhookManager 实例"""
    session = MockSession()
    store = MockStore(session=session)
    with patch.object(webhook_module, "Base", mock_base), \
         patch.object(webhook_module, "get_data_store", return_value=store):
        mgr = webhook_module.WebhookManager(store=store)
        return mgr, session, store


# ─── 1. EVENT_TYPES 常量 ──────────────────────────────────────────────────


class TestEventTypes:
    """测试 EVENT_TYPES 常量"""

    def test_all_13_event_types(self, webhook_module):
        assert len(webhook_module.EVENT_TYPES) == 13

    def test_case_events(self, webhook_module):
        assert "case.created" in webhook_module.EVENT_TYPES
        assert "case.updated" in webhook_module.EVENT_TYPES
        assert "case.deleted" in webhook_module.EVENT_TYPES
        assert "case.viewed" in webhook_module.EVENT_TYPES
        assert webhook_module.EVENT_TYPES["case.created"] == "案例创建"
        assert webhook_module.EVENT_TYPES["case.updated"] == "案例更新"
        assert webhook_module.EVENT_TYPES["case.deleted"] == "案例删除"
        assert webhook_module.EVENT_TYPES["case.viewed"] == "案例被浏览"

    def test_bazi_events(self, webhook_module):
        assert "bazi.computed" in webhook_module.EVENT_TYPES
        assert "bazi.record_saved" in webhook_module.EVENT_TYPES
        assert webhook_module.EVENT_TYPES["bazi.computed"] == "八字排盘完成"
        assert webhook_module.EVENT_TYPES["bazi.record_saved"] == "八字记录保存"

    def test_oracle_events(self, webhook_module):
        assert "oracle.consulted" in webhook_module.EVENT_TYPES
        assert webhook_module.EVENT_TYPES["oracle.consulted"] == "Oracle 咨询"

    def test_user_events(self, webhook_module):
        assert "user.registered" in webhook_module.EVENT_TYPES
        assert "user.login" in webhook_module.EVENT_TYPES
        assert webhook_module.EVENT_TYPES["user.registered"] == "用户注册"
        assert webhook_module.EVENT_TYPES["user.login"] == "用户登录"

    def test_system_events(self, webhook_module):
        assert "system.started" in webhook_module.EVENT_TYPES
        assert "system.error" in webhook_module.EVENT_TYPES
        assert webhook_module.EVENT_TYPES["system.started"] == "系统启动"
        assert webhook_module.EVENT_TYPES["system.error"] == "系统错误"

    def test_plugin_events(self, webhook_module):
        assert "plugin.loaded" in webhook_module.EVENT_TYPES
        assert "plugin.activated" in webhook_module.EVENT_TYPES
        assert webhook_module.EVENT_TYPES["plugin.loaded"] == "插件加载"
        assert webhook_module.EVENT_TYPES["plugin.activated"] == "插件激活"


# ─── 2. ORM 模型实例化 ────────────────────────────────────────────────────


class TestModelInstantiation:
    """测试 WebhookSubscription 和 WebhookDelivery 模型"""

    def test_subscription_model_attributes(self, webhook_module):
        sub = webhook_module.WebhookSubscription()
        sub.id = 1
        sub.url = "https://example.com/hook"
        sub.events = '["case.created"]'
        sub.secret = "secret"
        sub.is_active = True
        sub.description = "测试"
        sub.total_delivered = 5
        sub.total_failed = 2
        assert sub.id == 1
        assert sub.url == "https://example.com/hook"
        assert sub.is_active is True
        assert sub.total_delivered == 5
        assert sub.total_failed == 2

    def test_subscription_tablename(self, webhook_module):
        assert webhook_module.WebhookSubscription.__tablename__ == "webhook_subscriptions"

    def test_delivery_model_attributes(self, webhook_module):
        d = webhook_module.WebhookDelivery()
        d.id = 1
        d.subscription_id = 5
        d.event_type = "case.created"
        d.payload = "{}"
        d.status_code = 200
        d.response_body = "OK"
        d.success = True
        d.attempt = 1
        d.error = ""
        assert d.id == 1
        assert d.subscription_id == 5
        assert d.event_type == "case.created"
        assert d.status_code == 200
        assert d.success is True
        assert d.attempt == 1

    def test_delivery_tablename(self, webhook_module):
        assert webhook_module.WebhookDelivery.__tablename__ == "webhook_deliveries"


# ─── 3. subscribe() ────────────────────────────────────────────────────────


class TestSubscribe:
    """测试订阅创建"""

    def test_subscribe_returns_dict(self, manager, webhook_module):
        mgr, session, store = manager
        result = mgr.subscribe(
            url="https://example.com/hook",
            events=["case.created", "bazi.computed"],
            secret="mysecret",
            description="我的订阅",
        )
        assert isinstance(result, dict)
        assert result["url"] == "https://example.com/hook"
        assert "case.created" in result["events"]
        assert "bazi.computed" in result["events"]
        assert result["has_secret"] is True
        assert result["secret"] == "***"
        assert result["is_active"] is True
        assert result["description"] == "我的订阅"

    def test_subscribe_without_secret(self, manager):
        mgr, session, store = manager
        result = mgr.subscribe(
            url="https://example.com/hook",
            events=["case.created"],
            secret="",
            description="",
        )
        assert result["has_secret"] is False
        assert result["secret"] == ""

    def test_subscribe_with_empty_events(self, manager):
        mgr, session, store = manager
        result = mgr.subscribe(
            url="https://example.com/hook",
            events=[],
        )
        assert result["events"] == []

    def test_subscribe_session_add_called(self, manager):
        mgr, session, store = manager
        mgr.subscribe(url="https://example.com/hook", events=["case.created"])
        assert len(session.added) == 1
        assert session.committed is True


# ─── 4. unsubscribe() ──────────────────────────────────────────────────────


class TestUnsubscribe:
    """测试取消订阅"""

    def test_unsubscribe_existing(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription
        sub = make_sub(id=10)
        new_session = MockSession({WebhookSubscription: [sub]})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.unsubscribe(10)
            assert result is True
            assert len(new_session.deleted) == 1
            assert new_session.committed is True

    def test_unsubscribe_nonexistent(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: []})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.unsubscribe(999)
            assert result is False
            assert len(new_session.deleted) == 0


# ─── 5. get_subscription() ─────────────────────────────────────────────────


class TestGetSubscription:
    """测试获取订阅"""

    def test_get_existing(self, manager):
        mgr, session, store = manager
        sub = make_sub(id=5, url="https://example.com/hook", events='["case.created","bazi.computed"]',
                       secret="s", description="desc")
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub]})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.get_subscription(5)
            assert result is not None
            assert result["id"] == 5
            assert result["url"] == "https://example.com/hook"
            assert "case.created" in result["events"]
            assert result["has_secret"] is True
            assert result["description"] == "desc"

    def test_get_nonexistent(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: []})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.get_subscription(999)
            assert result is None


# ─── 6. list_subscriptions() ───────────────────────────────────────────────


class TestListSubscriptions:
    """测试列出订阅"""

    def test_list_all(self, manager):
        mgr, session, store = manager
        sub1 = make_sub(id=1, is_active=True)
        sub2 = make_sub(id=2, is_active=False)
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub1, sub2]})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.list_subscriptions()
            assert len(result) == 2
            assert result[0]["id"] == 1
            assert result[1]["id"] == 2

    def test_list_active_only(self, manager):
        mgr, session, store = manager
        sub1 = make_sub(id=1, is_active=True)
        sub2 = make_sub(id=2, is_active=False)
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub1, sub2]})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.list_subscriptions(active_only=True)
            assert len(result) == 1
            assert result[0]["id"] == 1

    def test_list_empty(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: []})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.list_subscriptions()
            assert result == []


# ─── 7. update_subscription() ──────────────────────────────────────────────


class TestUpdateSubscription:
    """测试更新订阅"""

    def test_update_url(self, manager):
        mgr, session, store = manager
        sub = make_sub(id=1, url="https://old.example.com/hook")
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub]})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.update_subscription(1, url="https://new.example.com/hook")
            assert result is not None
            assert result["url"] == "https://new.example.com/hook"

    def test_update_events(self, manager):
        mgr, session, store = manager
        sub = make_sub(id=1, events='["case.created"]')
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub]})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.update_subscription(1, events=["case.created", "bazi.computed"])
            assert result is not None
            assert "case.created" in result["events"]
            assert "bazi.computed" in result["events"]

    def test_update_secret(self, manager):
        mgr, session, store = manager
        sub = make_sub(id=1, secret="oldsecret")
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub]})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.update_subscription(1, secret="newsecret")
            assert result is not None
            assert sub.secret == "newsecret"

    def test_update_is_active(self, manager):
        mgr, session, store = manager
        sub = make_sub(id=1, is_active=True)
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub]})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.update_subscription(1, is_active=False)
            assert result is not None
            assert sub.is_active is False

    def test_update_description(self, manager):
        mgr, session, store = manager
        sub = make_sub(id=1, description="old")
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub]})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.update_subscription(1, description="new desc")
            assert result is not None
            assert sub.description == "new desc"

    def test_update_nonexistent(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: []})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.update_subscription(999, url="https://example.com/hook")
            assert result is None

    def test_update_no_params_does_nothing(self, manager):
        mgr, session, store = manager
        sub = make_sub(id=1, url="https://keep.example.com/hook")
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub]})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.update_subscription(1)
            assert result is not None
            assert result["url"] == "https://keep.example.com/hook"


# ─── 8. trigger() ──────────────────────────────────────────────────────────


class TestTrigger:
    """测试事件触发"""

    def test_trigger_matching_event(self, manager):
        mgr, session, store = manager
        sub1 = make_sub(id=1, events='["case.created"]', is_active=True, url="https://h1.com")
        sub2 = make_sub(id=2, events='["bazi.computed"]', is_active=True, url="https://h2.com")
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub1, sub2]})
        with patch.object(mgr, "_session", return_value=new_session), \
             patch.object(mgr, "_deliver") as mock_deliver:
            count = mgr.trigger("case.created", {"case_id": 1})
            assert count == 1

    def test_trigger_wildcard_matches_all(self, manager):
        mgr, session, store = manager
        sub1 = make_sub(id=1, events='["*"]', is_active=True, url="https://h1.com")
        sub2 = make_sub(id=2, events='["case.created"]', is_active=True, url="https://h2.com")
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub1, sub2]})
        with patch.object(mgr, "_session", return_value=new_session), \
             patch.object(mgr, "_deliver") as mock_deliver:
            # 使用 "case.created" 事件，wildcard("*") 和具体事件都匹配
            count = mgr.trigger("case.created", {"data": 1})
            assert count == 2

    def test_trigger_non_matching_event(self, manager):
        mgr, session, store = manager
        sub1 = make_sub(id=1, events='["case.created"]', is_active=True, url="https://h1.com")
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub1]})
        with patch.object(mgr, "_session", return_value=new_session), \
             patch.object(mgr, "_deliver") as mock_deliver:
            count = mgr.trigger("bazi.computed", {"data": 1})
            assert count == 0

    def test_trigger_inactive_sub_ignored(self, manager):
        mgr, session, store = manager
        sub1 = make_sub(id=1, events='["case.created"]', is_active=False, url="https://h1.com")
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub1]})
        with patch.object(mgr, "_session", return_value=new_session), \
             patch.object(mgr, "_deliver") as mock_deliver:
            count = mgr.trigger("case.created", {"case_id": 1})
            assert count == 0

    def test_trigger_custom_event(self, manager):
        """自定义事件（不在 EVENT_TYPES 中）也能触发"""
        mgr, session, store = manager
        sub1 = make_sub(id=1, events='["custom.event"]', is_active=True, url="https://h1.com")
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub1]})
        with patch.object(mgr, "_session", return_value=new_session), \
             patch.object(mgr, "_deliver") as mock_deliver:
            count = mgr.trigger("custom.event", {"data": 1})
            assert count == 1

    def test_trigger_with_empty_events_in_sub(self, manager):
        """订阅的 events 为空列表时不应匹配"""
        mgr, session, store = manager
        sub1 = make_sub(id=1, events='[]', is_active=True, url="https://h1.com")
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub1]})
        with patch.object(mgr, "_session", return_value=new_session), \
             patch.object(mgr, "_deliver") as mock_deliver:
            count = mgr.trigger("case.created", {"case_id": 1})
            assert count == 0

    def test_trigger_with_invalid_events_json(self, manager):
        """订阅的 events 为无效 JSON 时不崩溃"""
        mgr, session, store = manager
        sub1 = make_sub(id=1, events='invalid-json', is_active=True, url="https://h1.com")
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub1]})
        with patch.object(mgr, "_session", return_value=new_session), \
             patch.object(mgr, "_deliver") as mock_deliver:
            count = mgr.trigger("case.created", {"case_id": 1})
            assert count == 0

    def test_trigger_deliver_runs_in_thread(self, manager):
        """验证 _deliver 在独立线程中调用"""
        mgr, session, store = manager
        sub1 = make_sub(id=1, events='["case.created"]', is_active=True, url="https://h1.com",
                        secret="secret123")
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub1]})
        with patch.object(mgr, "_session", return_value=new_session):
            # 用 threading.Event 来检测 _deliver 是否被调用
            deliver_called = threading.Event()
            original_deliver = mgr._deliver

            def tracking_deliver(*args, **kwargs):
                deliver_called.set()
                # 不调用原始方法，避免网络请求

            mgr._deliver = tracking_deliver
            try:
                count = mgr.trigger("case.created", {"case_id": 1})
                assert count == 1
                # 等待线程完成
                deliver_called.wait(timeout=2)
                assert deliver_called.is_set()
            finally:
                mgr._deliver = original_deliver


# ─── 9. _deliver() ─────────────────────────────────────────────────────────


class TestDeliver:
    """测试 _deliver 推送"""

    def test_deliver_success(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription, WebhookDelivery

        sub = make_sub(id=1, total_delivered=0, total_failed=0)
        new_session = MockSession({
            WebhookSubscription: [sub],
            WebhookDelivery: [],
        })

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"OK"

        with patch.object(mgr, "_session", return_value=new_session), \
             patch("tengod.webhook.urlopen", return_value=mock_response), \
             patch("tengod.webhook.Request") as mock_req:
            mgr._deliver(1, "https://example.com/hook", "secret123", "case.created", {"id": 1})
            assert new_session.committed is True
            assert len(new_session.added) >= 1
            # 检查 delivery 记录
            delivery = new_session.added[-1]
            assert delivery.success is True
            assert sub.total_delivered == 1
            assert sub.total_failed == 0

    def test_deliver_http_error(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription, WebhookDelivery

        sub = make_sub(id=1, total_delivered=0, total_failed=0)
        new_session = MockSession({
            WebhookSubscription: [sub],
            WebhookDelivery: [],
        })

        from urllib.error import HTTPError
        http_error = HTTPError("https://example.com/hook", 500, "Internal Error",
                               MagicMock(), MagicMock())
        http_error.read = MagicMock(return_value=b"Server Error")

        with patch.object(mgr, "_session", return_value=new_session), \
             patch("tengod.webhook.urlopen", side_effect=http_error), \
             patch("tengod.webhook.Request") as mock_req:
            mgr._deliver(1, "https://example.com/hook", "secret123", "case.created", {"id": 1})
            assert new_session.committed is True
            delivery = new_session.added[-1]
            assert delivery.success is False
            assert sub.total_delivered == 0
            assert sub.total_failed == 1

    def test_deliver_connection_error(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription, WebhookDelivery

        sub = make_sub(id=1, total_delivered=0, total_failed=0)
        new_session = MockSession({
            WebhookSubscription: [sub],
            WebhookDelivery: [],
        })

        from urllib.error import URLError
        url_error = URLError("Connection refused")

        with patch.object(mgr, "_session", return_value=new_session), \
             patch("tengod.webhook.urlopen", side_effect=url_error), \
             patch("tengod.webhook.Request") as mock_req:
            mgr._deliver(1, "https://example.com/hook", "secret123", "case.created", {"id": 1})
            delivery = new_session.added[-1]
            assert delivery.success is False
            assert "连接失败" in delivery.error

    def test_deliver_retry_logic(self, manager):
        """验证重试逻辑：max_retries=3，应重试 3 次"""
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription, WebhookDelivery

        sub = make_sub(id=1, total_delivered=0, total_failed=0)
        new_session = MockSession({
            WebhookSubscription: [sub],
            WebhookDelivery: [],
        })

        from urllib.error import URLError
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            raise URLError("Connection refused")

        mgr.max_retries = 3
        with patch.object(mgr, "_session", return_value=new_session), \
             patch("tengod.webhook.urlopen", side_effect=side_effect), \
             patch("tengod.webhook.Request") as mock_req, \
             patch("tengod.webhook.time.sleep") as mock_sleep:
            mgr._deliver(1, "https://example.com/hook", "secret123", "case.created", {"id": 1})
            assert call_count[0] == 3
            assert mock_sleep.call_count == 2  # 最后一次不 sleep

    def test_deliver_hmac_signature(self, manager):
        """验证 HMAC-SHA256 签名"""
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription, WebhookDelivery

        sub = make_sub(id=1, total_delivered=0, total_failed=0)
        new_session = MockSession({
            WebhookSubscription: [sub],
            WebhookDelivery: [],
        })

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"OK"

        with patch.object(mgr, "_session", return_value=new_session), \
             patch("tengod.webhook.urlopen", return_value=mock_response), \
             patch("tengod.webhook.Request") as mock_req_class:
            mgr._deliver(1, "https://example.com/hook", "secret123", "case.created", {"id": 1})
            # 验证 Request 被调用时 headers 包含签名
            call_args = mock_req_class.call_args
            args, kwargs = call_args[0], call_args[1] if len(call_args) > 1 else ({},)
            # 第一个参数是 url
            assert args[0] == "https://example.com/hook"
            # headers 应该在 kwargs 中
            headers = kwargs.get("headers", {})
            assert "X-Tengod-Signature" in headers
            assert headers["X-Tengod-Event"] == "case.created"

    def test_deliver_no_signature_without_secret(self, manager):
        """无 secret 时不设置签名头"""
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription, WebhookDelivery

        sub = make_sub(id=1, total_delivered=0, total_failed=0)
        new_session = MockSession({
            WebhookSubscription: [sub],
            WebhookDelivery: [],
        })

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"OK"

        with patch.object(mgr, "_session", return_value=new_session), \
             patch("tengod.webhook.urlopen", return_value=mock_response), \
             patch("tengod.webhook.Request") as mock_req_class:
            mgr._deliver(1, "https://example.com/hook", "", "case.created", {"id": 1})
            call_args = mock_req_class.call_args
            args, kwargs = call_args[0], call_args[1] if len(call_args) > 1 else ({},)
            headers = kwargs.get("headers", {})
            assert "X-Tengod-Signature" not in headers

    def test_deliver_success_on_retry(self, manager):
        """第一次失败、第二次成功的情况"""
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription, WebhookDelivery

        sub = make_sub(id=1, total_delivered=0, total_failed=0)
        new_session = MockSession({
            WebhookSubscription: [sub],
            WebhookDelivery: [],
        })

        from urllib.error import URLError

        mock_success = MagicMock()
        mock_success.status = 200
        mock_success.read.return_value = b"OK"

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise URLError("Connection refused")
            return mock_success

        mgr.max_retries = 3
        with patch.object(mgr, "_session", return_value=new_session), \
             patch("tengod.webhook.urlopen", side_effect=side_effect), \
             patch("tengod.webhook.Request") as mock_req, \
             patch("tengod.webhook.time.sleep") as mock_sleep:
            mgr._deliver(1, "https://example.com/hook", "secret123", "case.created", {"id": 1})
            assert call_count[0] == 2
            delivery = new_session.added[-1]
            assert delivery.success is True
            assert delivery.attempt == 2

    def test_deliver_generic_exception(self, manager):
        """测试通用异常处理"""
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription, WebhookDelivery

        sub = make_sub(id=1, total_delivered=0, total_failed=0)
        new_session = MockSession({
            WebhookSubscription: [sub],
            WebhookDelivery: [],
        })

        with patch.object(mgr, "_session", return_value=new_session), \
             patch("tengod.webhook.urlopen", side_effect=ValueError("unexpected error")), \
             patch("tengod.webhook.Request") as mock_req:
            mgr._deliver(1, "https://example.com/hook", "secret123", "case.created", {"id": 1})
            delivery = new_session.added[-1]
            assert delivery.success is False
            assert "unexpected error" in delivery.error

    def test_deliver_sub_not_found_during_record(self, manager):
        """交付过程中订阅被删除，仍然记录交付"""
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription, WebhookDelivery

        # 返回空订阅列表
        new_session = MockSession({
            WebhookSubscription: [],
            WebhookDelivery: [],
        })

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"OK"

        with patch.object(mgr, "_session", return_value=new_session), \
             patch("tengod.webhook.urlopen", return_value=mock_response), \
             patch("tengod.webhook.Request") as mock_req:
            # 不应崩溃
            mgr._deliver(1, "https://example.com/hook", "secret123", "case.created", {"id": 1})

    def test_deliver_record_exception_silent(self, manager):
        """记录交付时发生异常不抛出"""
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription, WebhookDelivery

        sub = make_sub(id=1, total_delivered=0, total_failed=0)
        new_session = MockSession({
            WebhookSubscription: [sub],
            WebhookDelivery: [],
        })
        # 让 commit 抛出异常
        new_session.commit = MagicMock(side_effect=RuntimeError("DB error"))

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"OK"

        with patch.object(mgr, "_session", return_value=new_session), \
             patch("tengod.webhook.urlopen", return_value=mock_response), \
             patch("tengod.webhook.Request") as mock_req:
            # 不应抛出异常
            mgr._deliver(1, "https://example.com/hook", "secret123", "case.created", {"id": 1})


# ─── 10. list_deliveries() ─────────────────────────────────────────────────


class TestListDeliveries:
    """测试列出交付记录"""

    def test_list_all_deliveries(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookDelivery
        d1 = make_delivery(id=1, subscription_id=1, event_type="case.created")
        d2 = make_delivery(id=2, subscription_id=2, event_type="bazi.computed", success=False)
        new_session = MockSession({WebhookDelivery: [d1, d2]})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.list_deliveries()
            assert len(result) == 2

    def test_list_deliveries_filtered_by_sub_id(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookDelivery
        d1 = make_delivery(id=1, subscription_id=1)
        d2 = make_delivery(id=2, subscription_id=2)
        d3 = make_delivery(id=3, subscription_id=1)
        new_session = MockSession({WebhookDelivery: [d1, d2, d3]})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.list_deliveries(sub_id=1)
            # MockQuery.filter_by 会过滤
            # 但实际上我们的 MockQuery 是按 model class 来的，filter_by 会过滤
            assert len(result) == 2

    def test_list_deliveries_empty(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookDelivery
        new_session = MockSession({WebhookDelivery: []})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.list_deliveries()
            assert result == []

    def test_list_deliveries_with_limit(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookDelivery
        deliveries = [make_delivery(id=i) for i in range(100)]
        new_session = MockSession({WebhookDelivery: deliveries})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.list_deliveries(limit=10)
            assert len(result) == 10


# ─── 11. test_subscription() ───────────────────────────────────────────────


class TestTestSubscription:
    """测试 test_subscription"""

    def test_test_existing_sub(self, manager):
        mgr, session, store = manager
        sub = make_sub(id=1, url="https://example.com/hook", secret="s",
                       events='["case.created"]')
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: [sub]})
        with patch.object(mgr, "_session", return_value=new_session), \
             patch.object(mgr, "_deliver") as mock_deliver:
            result = mgr.test_subscription(1)
            assert result == {"sent": True, "subscription_id": 1}
            mock_deliver.assert_called_once()
            call_args = mock_deliver.call_args
            assert call_args[0][0] == 1  # sub_id
            assert call_args[0][3] == "test.ping"  # event_type

    def test_test_nonexistent_sub(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription
        new_session = MockSession({WebhookSubscription: []})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.test_subscription(999)
            assert result == {"error": "订阅不存在"}


# ─── 12. stats() ───────────────────────────────────────────────────────────


class TestStats:
    """测试统计"""

    def test_stats_structure(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription, WebhookDelivery
        sub1 = make_sub(id=1, is_active=True)
        sub2 = make_sub(id=2, is_active=False)
        d1 = make_delivery(id=1, success=True)
        d2 = make_delivery(id=2, success=False)
        new_session = MockSession({
            WebhookSubscription: [sub1, sub2],
            WebhookDelivery: [d1, d2],
        })
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.stats()
            assert result["total_subscriptions"] == 2
            assert result["active_subscriptions"] == 1
            assert result["total_deliveries"] == 2
            assert result["success_deliveries"] == 1
            assert result["failed_deliveries"] == 1
            assert result["success_rate"] == 50.0
            assert "event_types" in result
            assert len(result["event_types"]) == 13

    def test_stats_zero_deliveries(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription, WebhookDelivery
        new_session = MockSession({
            WebhookSubscription: [],
            WebhookDelivery: [],
        })
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.stats()
            assert result["total_subscriptions"] == 0
            assert result["total_deliveries"] == 0
            assert result["success_rate"] == 0


# ─── 13. _subscription_to_dict / _delivery_to_dict ─────────────────────────


class TestConverters:
    """测试转换辅助方法"""

    def test_subscription_to_dict_full(self, manager):
        mgr, session, store = manager
        sub = make_sub(
            id=42, url="https://example.com/hook",
            events='["case.created","bazi.computed"]',
            secret="secret123", is_active=True, description="test",
            created_at="2025-06-01T00:00:00", updated_at="2025-06-01T00:00:00",
            total_delivered=10, total_failed=3,
        )
        result = mgr._subscription_to_dict(sub)
        assert result["id"] == 42
        assert result["url"] == "https://example.com/hook"
        assert result["events"] == ["case.created", "bazi.computed"]
        assert result["secret"] == "***"
        assert result["has_secret"] is True
        assert result["is_active"] is True
        assert result["description"] == "test"
        assert result["created_at"] == "2025-06-01T00:00:00"
        assert result["updated_at"] == "2025-06-01T00:00:00"
        assert result["total_delivered"] == 10
        assert result["total_failed"] == 3

    def test_subscription_to_dict_no_secret(self, manager):
        mgr, session, store = manager
        sub = make_sub(id=1, secret="", events='[]')
        result = mgr._subscription_to_dict(sub)
        assert result["secret"] == ""
        assert result["has_secret"] is False

    def test_subscription_to_dict_none_created_at(self, manager):
        mgr, session, store = manager
        sub = make_sub(id=1, created_at=None, updated_at=None, events='[]')
        result = mgr._subscription_to_dict(sub)
        assert result["created_at"] is None
        assert result["updated_at"] is None

    def test_subscription_to_dict_none_totals(self, manager):
        mgr, session, store = manager
        sub = make_sub(id=1, total_delivered=None, total_failed=None, events='[]')
        result = mgr._subscription_to_dict(sub)
        assert result["total_delivered"] == 0
        assert result["total_failed"] == 0

    def test_delivery_to_dict(self, manager):
        mgr, session, store = manager
        d = make_delivery(
            id=7, subscription_id=3, event_type="case.created",
            payload='{"event":"case.created","payload":{"id":1}}',
            status_code=200, response_body="OK", success=True,
            attempt=1, error="",
            created_at="2025-06-01T00:00:00", delivered_at="2025-06-01T00:00:01",
        )
        result = mgr._delivery_to_dict(d)
        assert result["id"] == 7
        assert result["subscription_id"] == 3
        assert result["event_type"] == "case.created"
        assert result["payload"] == '{"event":"case.created","payload":{"id":1}}'
        assert result["status_code"] == 200
        assert result["response_body"] == "OK"
        assert result["success"] is True
        assert result["attempt"] == 1
        assert result["error"] == ""
        assert result["created_at"] == "2025-06-01T00:00:00"
        assert result["delivered_at"] == "2025-06-01T00:00:01"

    def test_delivery_to_dict_none_dates(self, manager):
        mgr, session, store = manager
        d = make_delivery(id=1, created_at=None, delivered_at=None)
        result = mgr._delivery_to_dict(d)
        assert result["created_at"] is None
        assert result["delivered_at"] is None


# ─── 14. get_webhook_manager 单例 ──────────────────────────────────────────


class TestSingleton:
    """测试单例模式"""

    def test_get_webhook_manager_returns_same_instance(self, webhook_module, mock_base):
        with patch.object(webhook_module, "Base", mock_base), \
             patch.object(webhook_module, "get_data_store", return_value=MockStore()):
            # 重置单例
            webhook_module._library = None
            mgr1 = webhook_module.get_webhook_manager()
            mgr2 = webhook_module.get_webhook_manager()
            assert mgr1 is mgr2

    def test_get_webhook_manager_creates_instance(self, webhook_module, mock_base):
        with patch.object(webhook_module, "Base", mock_base), \
             patch.object(webhook_module, "get_data_store", return_value=MockStore()):
            webhook_module._library = None
            mgr = webhook_module.get_webhook_manager()
            assert mgr is not None
            assert isinstance(mgr, webhook_module.WebhookManager)


# ─── 15. 边界情况 ──────────────────────────────────────────────────────────


class TestEdgeCases:
    """测试边界情况"""

    def test_ensure_tables_exception_handling(self, webhook_module, mock_base):
        """_ensure_tables 异常被静默处理"""
        mock_base.metadata.create_all.side_effect = RuntimeError("Table creation failed")
        with patch.object(webhook_module, "Base", mock_base), \
             patch.object(webhook_module, "get_data_store", return_value=MockStore()):
            # 不应抛出异常
            mgr = webhook_module.WebhookManager(store=MockStore())
            assert mgr is not None

    def test_manager_default_attributes(self, manager):
        mgr, session, store = manager
        assert mgr.max_retries == 3
        assert mgr.history_limit == 100
        assert mgr._lock is not None

    def test_list_subscriptions_active_only_no_results(self, manager):
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription
        sub1 = make_sub(id=1, is_active=False)
        new_session = MockSession({WebhookSubscription: [sub1]})
        with patch.object(mgr, "_session", return_value=new_session):
            result = mgr.list_subscriptions(active_only=True)
            assert result == []

    def test_subscription_to_dict_with_empty_events(self, manager):
        mgr, session, store = manager
        sub = make_sub(id=1, events=None)
        # events=None 时 json.loads(None or "[]") → json.loads("[]")
        sub.events = None
        result = mgr._subscription_to_dict(sub)
        assert result["events"] == []

    def test_subscription_to_dict_with_none_events(self, manager):
        mgr, session, store = manager
        sub = make_sub(id=1, events="")
        result = mgr._subscription_to_dict(sub)
        assert result["events"] == []

    def test_deliver_with_non_2xx_status(self, manager):
        """HTTP 返回非 2xx 状态码"""
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription, WebhookDelivery

        sub = make_sub(id=1, total_delivered=0, total_failed=0)
        new_session = MockSession({
            WebhookSubscription: [sub],
            WebhookDelivery: [],
        })

        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.read.return_value = b"Not Found"

        with patch.object(mgr, "_session", return_value=new_session), \
             patch("tengod.webhook.urlopen", return_value=mock_response), \
             patch("tengod.webhook.Request") as mock_req:
            mgr._deliver(1, "https://example.com/hook", "secret123", "case.created", {"id": 1})
            delivery = new_session.added[-1]
            assert delivery.success is False
            assert "HTTP 404" in delivery.error

    def test_history_cleanup(self, manager):
        """测试历史记录清理：超过 history_limit 时删除旧记录"""
        mgr, session, store = manager
        from tengod.webhook import WebhookSubscription, WebhookDelivery

        sub = make_sub(id=1, total_delivered=0, total_failed=0)
        # 创建超过 history_limit 的 deliveries
        deliveries = [make_delivery(id=i, subscription_id=1) for i in range(150)]
        new_session = MockSession({
            WebhookSubscription: [sub],
            WebhookDelivery: deliveries,
        })

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"OK"

        mgr.history_limit = 100
        with patch.object(mgr, "_session", return_value=new_session), \
             patch("tengod.webhook.urlopen", return_value=mock_response), \
             patch("tengod.webhook.Request") as mock_req:
            mgr._deliver(1, "https://example.com/hook", "secret123", "case.created", {"id": 1})
            # 旧记录被删除（150 - 100 = 50 条 + 新增 1 条 delivery）
            # 验证有删除操作
            assert len(new_session.deleted) == 50


# ─── 16. __all__ 导出 ──────────────────────────────────────────────────────


class TestExports:
    """测试模块导出"""

    def test_all_exports(self, webhook_module):
        expected = [
            "WebhookSubscription",
            "WebhookDelivery",
            "WebhookManager",
            "get_webhook_manager",
            "EVENT_TYPES",
        ]
        for name in expected:
            assert name in webhook_module.__all__

    def test_version(self, webhook_module):
        assert webhook_module.__version__ == "1.0.0"