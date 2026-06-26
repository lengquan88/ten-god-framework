"""
TenGod Python SDK Client
A Python client for the TenGod API v3.0.0
"""
import json
from typing import Any, Dict, List, Optional

import requests


__version__ = "3.0.0"


class BaziRequest:
    """八字排盘请求"""
    def __init__(self, year: int, month: int, day: int, hour: int,
                 minute: int = 0, gender: str = "male"):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.gender = gender

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year, "month": self.month, "day": self.day,
            "hour": self.hour, "minute": self.minute, "gender": self.gender,
        }


class BaziResponse:
    """八字排盘响应"""
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.pillars = data.get("pillars", {})
        self.day_master = data.get("day_master", "")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaziResponse":
        return cls(data)


class TenGodClient:
    """TenGod API Python 客户端

    用法：
        client = TenGodClient("http://localhost:8000", api_key="...")
        result = client.bazi_calc(1990, 6, 15, 10, gender="male")
    """

    def __init__(self, base_url: str = "http://localhost:8000",
                 api_key: Optional[str] = None, token: Optional[str] = None,
                 timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.token = token
        self.timeout = timeout
        self._session = requests.Session()

    @property
    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _unwrap(self, data: Any) -> Any:
        """解包内在小孩门禁响应"""
        if isinstance(data, dict) and "output" in data and "confidence" in data:
            return data["output"]
        return data

    def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        r = self._session.get(f"{self.base_url}{path}", params=params,
                              headers=self._headers, timeout=self.timeout)
        r.raise_for_status()
        return self._unwrap(r.json())

    def _post(self, path: str, json_data: Optional[Dict] = None,
              params: Optional[Dict] = None) -> Any:
        r = self._session.post(f"{self.base_url}{path}", json=json_data or {},
                               params=params, headers=self._headers,
                               timeout=self.timeout)
        r.raise_for_status()
        return self._unwrap(r.json())

    def _put(self, path: str, json_data: Optional[Dict] = None) -> Any:
        r = self._session.put(f"{self.base_url}{path}", json=json_data or {},
                              headers=self._headers, timeout=self.timeout)
        r.raise_for_status()
        return self._unwrap(r.json())

    def _delete(self, path: str) -> Any:
        r = self._session.delete(f"{self.base_url}{path}",
                                 headers=self._headers, timeout=self.timeout)
        r.raise_for_status()
        return self._unwrap(r.json())

    # ── 健康检查 ──
    def health(self) -> Dict[str, Any]:
        return self._get("/api/health")

    # ── 认证 ──
    def login(self, username: str, password: str) -> Dict[str, Any]:
        return self._post("/api/auth/login", {"username": username, "password": password})

    def register(self, username: str, password: str, email: str = "") -> Dict[str, Any]:
        return self._post("/api/auth/register", {"username": username, "password": password, "email": email})

    # ── 八字排盘 ──
    def bazi_calc(self, year: int, month: int, day: int, hour: int,
                  minute: int = 0, gender: str = "male") -> Dict[str, Any]:
        return self._post("/api/bazi/calc", {
            "year": year, "month": month, "day": day,
            "hour": hour, "minute": minute, "gender": gender,
        })

    def bazi_full(self, year: int, month: int, day: int, hour: int,
                  minute: int = 0, gender: str = "male") -> Dict[str, Any]:
        return self._post("/api/bazi/full", {
            "year": year, "month": month, "day": day,
            "hour": hour, "minute": minute, "gender": gender,
        })

    def bazi_shensha(self, year: int, month: int, day: int, hour: int,
                     minute: int = 0, gender: str = "male") -> Dict[str, Any]:
        return self._post("/api/bazi/shensha", {
            "year": year, "month": month, "day": day,
            "hour": hour, "minute": minute, "gender": gender,
        })

    # ── 案例库 ──
    def list_cases(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        return self._get("/api/cases", {"limit": limit, "offset": offset})

    def get_case(self, case_id: int) -> Dict[str, Any]:
        return self._get(f"/api/cases/{case_id}")

    def create_case(self, title: str, bazi_data: Dict[str, Any],
                    category: str = "", tags: Optional[List[str]] = None,
                    description: str = "") -> Dict[str, Any]:
        return self._post("/api/cases", {
            "title": title, "bazi_data": bazi_data,
            "category": category, "tags": tags or [],
            "description": description,
        })

    def search_cases(self, keyword: str, limit: int = 20) -> Dict[str, Any]:
        return self._get("/api/cases/search", {"keyword": keyword, "limit": limit})

    def similar_cases(self, case_id: int, limit: int = 5) -> Dict[str, Any]:
        return self._get(f"/api/cases/{case_id}/similar", {"limit": limit})

    def case_categories(self) -> Dict[str, Any]:
        return self._get("/api/cases/categories/list")

    def case_tags(self) -> Dict[str, Any]:
        return self._get("/api/cases/tags/list")

    def case_stats(self) -> Dict[str, Any]:
        return self._get("/api/cases/stats/summary")

    def export_cases(self, format: str = "json", case_ids: Optional[List[int]] = None) -> Any:
        return self._post("/api/cases/export", {"format": format, "case_ids": case_ids or []})

    def favorite_case(self, case_id: int) -> Dict[str, Any]:
        return self._post(f"/api/cases/{case_id}/favorite")

    def like_case(self, case_id: int) -> Dict[str, Any]:
        return self._post(f"/api/cases/{case_id}/like")

    # ── Webhook ──
    def list_webhook_events(self) -> Dict[str, Any]:
        return self._get("/api/webhooks/events")

    def create_webhook(self, url: str, events: List[str],
                       secret: str = "", description: str = "") -> Dict[str, Any]:
        return self._post("/api/webhooks", {
            "url": url, "events": events,
            "secret": secret, "description": description,
        })

    def list_webhooks(self, active_only: bool = False) -> Dict[str, Any]:
        return self._get("/api/webhooks", {"active_only": active_only})

    def delete_webhook(self, webhook_id: int) -> Dict[str, Any]:
        return self._delete(f"/api/webhooks/{webhook_id}")

    def trigger_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/api/webhooks/trigger", {
            "event_type": event_type, "payload": payload,
        })

    def webhook_stats(self) -> Dict[str, Any]:
        return self._get("/api/webhooks/stats/summary")

    # ── 插件 ──
    def list_plugins(self) -> Dict[str, Any]:
        return self._get("/api/plugins")

    def plugin_stats(self) -> Dict[str, Any]:
        return self._get("/api/plugins/stats/summary")

    # ── 版本 ──
    def api_version(self) -> Dict[str, Any]:
        return self._get("/api/version")


# 别名：兼容小写 g 的用法
TengodClient = TenGodClient
