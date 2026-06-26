#!/usr/bin/env python3
"""
webhook.py — 十神架构 Webhook 事件推送系统 v1.0.0
=====================================================
阶段二十 20.1：开放 API 与 Webhook

功能：
  - Webhook 订阅注册/查询/删除/测试
  - 事件触发时异步推送到所有订阅者
  - HMAC-SHA256 签名验证
  - 重试机制（指数退避）
  - 交付历史记录
  - 内置事件类型（case.created/oracle.consulted/bazi.computed 等）

用法：
    from tengod.webhook import WebhookManager, get_webhook_manager
    wh = get_webhook_manager()
    sub_id = wh.subscribe(
        url="https://example.com/webhook",
        events=["case.created", "bazi.computed"],
        secret="my_secret",
    )
    wh.trigger("case.created", {"case_id": 1, "title": "测试案例"})
"""

import hashlib
import hmac
import json
import threading
import time
import uuid
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
)

from .data_store import Base, get_data_store

__all__ = ["WebhookSubscription", "WebhookDelivery", "WebhookManager", "get_webhook_manager", "EVENT_TYPES"]
__version__ = "1.0.0"


# ─── 内置事件类型 ────────────────────────────────────────

EVENT_TYPES = {
    # 案例库事件
    "case.created": "案例创建",
    "case.updated": "案例更新",
    "case.deleted": "案例删除",
    "case.viewed": "案例被浏览",
    # 八字排盘事件
    "bazi.computed": "八字排盘完成",
    "bazi.record_saved": "八字记录保存",
    # Oracle 事件
    "oracle.consulted": "Oracle 咨询",
    # 用户事件
    "user.registered": "用户注册",
    "user.login": "用户登录",
    # 系统事件
    "system.started": "系统启动",
    "system.error": "系统错误",
    # 插件事件
    "plugin.loaded": "插件加载",
    "plugin.activated": "插件激活",
}


# ─── ORM 模型 ────────────────────────────────────────────

class WebhookSubscription(Base):
    """Webhook 订阅"""
    __tablename__ = "webhook_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(512), nullable=False)
    events = Column(Text, nullable=False, default="[]")  # JSON 数组
    secret = Column(String(256), default="")
    is_active = Column(Boolean, default=True)
    description = Column(String(256), default="")
    created_at = Column(DateTime, default=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    updated_at = Column(DateTime, default=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                        onupdate=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    total_delivered = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)


class WebhookDelivery(Base):
    """Webhook 交付记录"""
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id = Column(Integer, nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    payload = Column(Text, nullable=False)
    status_code = Column(Integer, default=0)
    response_body = Column(Text, default="")
    success = Column(Boolean, default=False)
    attempt = Column(Integer, default=0)
    error = Column(String(512), default="")
    created_at = Column(DateTime, default=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    delivered_at = Column(DateTime, nullable=True)


# ─── Webhook 管理器 ──────────────────────────────────────

class WebhookManager:
    """Webhook 事件推送管理器"""

    def __init__(self, store=None):
        self._store = store or get_data_store()
        self._ensure_tables()
        self._lock = threading.RLock()
        # 最大重试次数
        self.max_retries = 3
        # 交付历史保留数
        self.history_limit = 100

    def _ensure_tables(self):
        """确保表存在"""
        try:
            Base.metadata.create_all(self._store._engine)
        except Exception:
            pass

    def _session(self):
        return self._store._session()

    # ── 订阅管理 ──────────────────────────────────────

    def subscribe(
        self,
        url: str,
        events: List[str],
        secret: str = "",
        description: str = "",
    ) -> Dict[str, Any]:
        """注册 Webhook 订阅"""
        with self._lock:
            with self._session() as s:
                sub = WebhookSubscription(
                    url=url,
                    events=json.dumps(events, ensure_ascii=False),
                    secret=secret,
                    description=description,
                    is_active=True,
                )
                s.add(sub)
                s.commit()
                return self._subscription_to_dict(sub)

    def unsubscribe(self, sub_id: int) -> bool:
        """取消订阅"""
        with self._lock:
            with self._session() as s:
                sub = s.query(WebhookSubscription).filter_by(id=sub_id).first()
                if not sub:
                    return False
                s.delete(sub)
                s.commit()
                return True

    def get_subscription(self, sub_id: int) -> Optional[Dict[str, Any]]:
        """获取订阅详情"""
        with self._session() as s:
            sub = s.query(WebhookSubscription).filter_by(id=sub_id).first()
            return self._subscription_to_dict(sub) if sub else None

    def list_subscriptions(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """列出所有订阅"""
        with self._session() as s:
            q = s.query(WebhookSubscription)
            if active_only:
                q = q.filter_by(is_active=True)
            subs = q.order_by(WebhookSubscription.id.desc()).all()
            return [self._subscription_to_dict(sub) for sub in subs]

    def update_subscription(
        self,
        sub_id: int,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        secret: Optional[str] = None,
        is_active: Optional[bool] = None,
        description: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """更新订阅"""
        with self._lock:
            with self._session() as s:
                sub = s.query(WebhookSubscription).filter_by(id=sub_id).first()
                if not sub:
                    return None
                if url is not None:
                    sub.url = url
                if events is not None:
                    sub.events = json.dumps(events, ensure_ascii=False)
                if secret is not None:
                    sub.secret = secret
                if is_active is not None:
                    sub.is_active = is_active
                if description is not None:
                    sub.description = description
                s.commit()
                return self._subscription_to_dict(sub)

    # ── 事件触发 ──────────────────────────────────────

    def trigger(self, event_type: str, payload: Dict[str, Any]) -> int:
        """触发事件，异步推送到所有匹配订阅。返回推送数量。"""
        if event_type not in EVENT_TYPES:
            # 允许自定义事件，但记录警告
            pass

        matching_subs = []
        with self._session() as s:
            subs = s.query(WebhookSubscription).filter_by(is_active=True).all()
            for sub in subs:
                try:
                    events = json.loads(sub.events or "[]")
                    if "*" in events or event_type in events:
                        matching_subs.append(sub)
                except Exception:
                    continue

        # 异步推送（不阻塞调用方）
        for sub in matching_subs:
            thread = threading.Thread(
                target=self._deliver,
                args=(sub.id, sub.url, sub.secret, event_type, payload),
                daemon=True,
            )
            thread.start()

        return len(matching_subs)

    def _deliver(
        self,
        sub_id: int,
        url: str,
        secret: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """实际推送（带重试）"""
        body = json.dumps(
            {
                "event": event_type,
                "payload": payload,
                "timestamp": int(time.time()),
                "delivery_id": str(uuid.uuid4()),
            },
            ensure_ascii=False,
        ).encode("utf-8")

        # HMAC-SHA256 签名
        signature = ""
        if secret:
            signature = hmac.new(
                secret.encode("utf-8"), body, hashlib.sha256
            ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Tengod-Event": event_type,
            "X-Tengod-Delivery": str(uuid.uuid4()),
        }
        if signature:
            headers["X-Tengod-Signature"] = signature

        last_error = ""
        status_code = 0
        response_body = ""
        success = False

        for attempt in range(1, self.max_retries + 1):
            try:
                req = Request(url, data=body, headers=headers, method="POST")
                resp = urlopen(req, timeout=10)
                status_code = resp.status
                response_body = resp.read().decode("utf-8", errors="replace")[:500]
                if 200 <= status_code < 300:
                    success = True
                    break
                else:
                    last_error = f"HTTP {status_code}"
            except HTTPError as e:
                status_code = e.code
                last_error = f"HTTP {e.code}: {e.reason}"
            except URLError as e:
                last_error = f"连接失败: {e.reason}"
            except Exception as e:
                last_error = str(e)

            # 指数退避
            if attempt < self.max_retries:
                time.sleep(0.5 * (2 ** (attempt - 1)))

        # 记录交付历史
        try:
            with self._session() as s:
                sub = s.query(WebhookSubscription).filter_by(id=sub_id).first()
                if sub:
                    if success:
                        sub.total_delivered += 1
                    else:
                        sub.total_failed += 1

                    delivery = WebhookDelivery(
                        subscription_id=sub_id,
                        event_type=event_type,
                        payload=body.decode("utf-8"),
                        status_code=status_code,
                        response_body=response_body,
                        success=success,
                        attempt=attempt,
                        error=last_error,
                        delivered_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc) if success else None,
                    )
                    s.add(delivery)
                    s.commit()

                    # 清理旧记录
                    count = s.query(WebhookDelivery).filter_by(subscription_id=sub_id).count()
                    if count > self.history_limit:
                        old = (
                            s.query(WebhookDelivery)
                            .filter_by(subscription_id=sub_id)
                            .order_by(WebhookDelivery.id.asc())
                            .limit(count - self.history_limit)
                            .all()
                        )
                        for o in old:
                            s.delete(o)
                        s.commit()
        except Exception:
            pass

    # ── 交付历史 ──────────────────────────────────────

    def list_deliveries(self, sub_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """列出交付记录"""
        with self._session() as s:
            q = s.query(WebhookDelivery)
            if sub_id:
                q = q.filter_by(subscription_id=sub_id)
            deliveries = q.order_by(WebhookDelivery.id.desc()).limit(limit).all()
            return [self._delivery_to_dict(d) for d in deliveries]

    # ── 测试 ──────────────────────────────────────────

    def test_subscription(self, sub_id: int) -> Dict[str, Any]:
        """发送测试事件"""
        sub = self.get_subscription(sub_id)
        if not sub:
            return {"error": "订阅不存在"}

        payload = {
            "test": True,
            "message": "十神架构 Webhook 测试事件",
            "subscription_id": sub_id,
        }
        self._deliver(sub_id, sub["url"], sub["secret"], "test.ping", payload)
        return {"sent": True, "subscription_id": sub_id}

    # ── 统计 ──────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        """Webhook 统计"""
        with self._session() as s:
            total_subs = s.query(WebhookSubscription).count()
            active_subs = s.query(WebhookSubscription).filter_by(is_active=True).count()
            total_deliveries = s.query(WebhookDelivery).count()
            success_deliveries = s.query(WebhookDelivery).filter_by(success=True).count()
            failed_deliveries = s.query(WebhookDelivery).filter_by(success=False).count()
            return {
                "total_subscriptions": total_subs,
                "active_subscriptions": active_subs,
                "total_deliveries": total_deliveries,
                "success_deliveries": success_deliveries,
                "failed_deliveries": failed_deliveries,
                "success_rate": (success_deliveries / total_deliveries * 100) if total_deliveries else 0,
                "event_types": list(EVENT_TYPES.keys()),
            }

    # ─── 工具方法 ──────────────────────────────────────

    def _subscription_to_dict(self, sub) -> Dict[str, Any]:
        return {
            "id": sub.id,
            "url": sub.url,
            "events": json.loads(sub.events or "[]"),
            "secret": "***" if sub.secret else "",
            "has_secret": bool(sub.secret),
            "is_active": sub.is_active,
            "description": sub.description,
            "created_at": str(sub.created_at) if sub.created_at else None,
            "updated_at": str(sub.updated_at) if sub.updated_at else None,
            "total_delivered": sub.total_delivered or 0,
            "total_failed": sub.total_failed or 0,
        }

    def _delivery_to_dict(self, d) -> Dict[str, Any]:
        return {
            "id": d.id,
            "subscription_id": d.subscription_id,
            "event_type": d.event_type,
            "payload": d.payload,
            "status_code": d.status_code,
            "response_body": d.response_body,
            "success": d.success,
            "attempt": d.attempt,
            "error": d.error,
            "created_at": str(d.created_at) if d.created_at else None,
            "delivered_at": str(d.delivered_at) if d.delivered_at else None,
        }


# ─── 模块级单例 ──────────────────────────────────────────

_library: Optional[WebhookManager] = None


def get_webhook_manager() -> WebhookManager:
    global _library
    if _library is None:
        _library = WebhookManager()
    return _library
