"""Stage 24: Mini-program SDK for WeChat / Alipay mini-programs.

Provides a client-side SDK that mimics a remote API (MiniappClient),
share card utilities (ShareCardGenerator), local storage simulation
(LocalStorageManager) and configuration helpers (MiniappConfig).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# MiniappClient
# ---------------------------------------------------------------------------
class MiniappClient:
    """HTTP API client for mini-programs.

    When ``base_url`` is ``None`` (or no network is available) the client
    falls back to local computation using :mod:`tengod.advanced_analysis`
    / :mod:`tengod.bazi_analyzer` / :mod:`tengod.ziwei_engine` /
    :mod:`tengod.liuyao_engine` / :mod:`tengod.qimen_engine`.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        app_id: str = "tengod-miniapp",
        app_secret: str = "",
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url
        self.app_id = app_id
        self.app_secret = app_secret
        self.timeout = timeout
        self._session: Dict[str, Any] = {}
        self._locale: str = "zh-CN"

    # ---- Public API --------------------------------------------------------
    def login(self, code: str, provider: str = "wechat") -> Dict[str, Any]:
        """Simulated mini-program login.

        Returns a dictionary with ``openid``, ``session_key`` and ``token``.
        """
        if self.base_url:
            return self._request(
                "POST",
                "/api/miniapp/login",
                {"code": code, "provider": provider},
            )
        openid = hashlib.md5(f"{provider}:{code}:{self.app_id}".encode()).hexdigest()
        session_key = hashlib.sha1(
            f"{openid}:{time.time()}:{self.app_secret}".encode()
        ).hexdigest()
        token = base64.urlsafe_b64encode(
            f"{openid}:{session_key}".encode()
        ).decode().rstrip("=")
        self._session = {
            "openid": openid,
            "session_key": session_key,
            "token": token,
            "provider": provider,
            "logged_at": int(time.time()),
        }
        return dict(self._session)

    def get_user_profile(self, token: str) -> Dict[str, Any]:
        if self.base_url:
            return self._request("GET", "/api/user/profile", {"token": token})
        return {
            "token": token,
            "nickname": "tengod_user",
            "locale": self._locale,
            "created_at": int(time.time()),
            "preferences": {
                "theme": "light",
                "default_hour": 12,
            },
        }

    def calc_bazi(
        self,
        token: str,
        year: int,
        month: int,
        day: int,
        hour: int,
        minute: int = 0,
        gender: str = "male",
        longitude: float = 116.4,
        latitude: float = 39.9,
    ) -> Dict[str, Any]:
        if self.base_url:
            return self._request(
                "POST",
                "/api/bazi/calc",
                {
                    "token": token,
                    "year": year,
                    "month": month,
                    "day": day,
                    "hour": hour,
                    "minute": minute,
                    "gender": gender,
                    "longitude": longitude,
                    "latitude": latitude,
                },
            )
        try:
            from tengod.bazi_analyzer import BaziAnalyzer

            analyzer = BaziAnalyzer(
                year=year,
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                is_male=(gender == "male"),
            )
            pillars = getattr(analyzer, "chart", None)
            pillar_list: List[Dict[str, Any]] = []
            if pillars is not None:
                raw = getattr(pillars, "pillars", None) or []
                for idx, p in enumerate(raw):
                    if isinstance(p, dict):
                        pillar_list.append(p)
                    else:
                        pillar_list.append({
                            "index": idx,
                            "gan": getattr(p, "gan", ""),
                            "zhi": getattr(p, "zhi", ""),
                        })
            analysis = analyzer.analysis if hasattr(analyzer, "analysis") else {}
            day_master = analysis.get("day_master", "") if isinstance(analysis, dict) else ""
            geju_val = analysis.get("geju", "") if isinstance(analysis, dict) else ""
            geju_name = geju_val.get("geju_name", "") if isinstance(geju_val, dict) else str(geju_val)
            wuxing = analysis.get("wuxing", {}) if isinstance(analysis, dict) else {}
            return {
                "record_id": int(hashlib.md5(
                    f"{year}{month}{day}{hour}{minute}{gender}".encode()
                ).hexdigest(), 16) % 10_000_000,
                "pillars": pillar_list,
                "day_master": day_master,
                "geju": geju_name,
                "wuxing": wuxing,
                "analysis": analysis if isinstance(analysis, dict) else {},
                "token": token,
            }
        except Exception as exc:  # pragma: no cover - defensive
            return {
                "record_id": 0,
                "pillars": [],
                "day_master": "",
                "geju": "",
                "wuxing": {},
                "analysis": {"error": str(exc)},
                "token": token,
            }

    def get_trajectory(
        self,
        token: str,
        record_id: Optional[int],
        start_year: int,
        end_year: int,
    ) -> Dict[str, Any]:
        if self.base_url:
            return self._request(
                "POST",
                "/api/bazi/trajectory",
                {
                    "token": token,
                    "record_id": record_id,
                    "start_year": start_year,
                    "end_year": end_year,
                },
            )
        try:
            from tengod.advanced_analysis import AdvancedAnalyzer

            engine = AdvancedAnalyzer()
            # Use start_year as birth year approximation for trajectory
            result = engine.destiny_trajectory(
                year=start_year,
                month=6,
                day=15,
                hour=12,
                minute=0,
                gender="male",
                start_age=0,
                end_age=max(0, end_year - start_year),
            )
            result["token"] = token
            result["record_id"] = record_id or 0
            result["start_year"] = start_year
            result["end_year"] = end_year
            return result
        except Exception as exc:  # pragma: no cover
            return {
                "record_id": record_id,
                "start_year": start_year,
                "end_year": end_year,
                "dayun": [],
                "liunian": [],
                "analysis": {"error": str(exc)},
                "token": token,
            }

    def calc_ziwei(
        self,
        token: str,
        year: int,
        month: int,
        day: int,
        hour: int,
        gender: str = "male",
    ) -> Dict[str, Any]:
        if self.base_url:
            return self._request(
                "POST",
                "/api/ziwei/calc",
                {
                    "token": token,
                    "year": year,
                    "month": month,
                    "day": day,
                    "hour": hour,
                    "gender": gender,
                },
            )
        try:
            from tengod.ziwei_engine import calc_ziwei, ziwei_to_dict

            chart = calc_ziwei(year=year, month=month, day=day, hour=hour)
            data = ziwei_to_dict(chart)
            return {
                "palaces": data,
                "year_ganzhi": data.get("year_ganzhi", ""),
                "ming_gong": data.get("ming_gong", ""),
                "token": token,
            }
        except Exception as exc:  # pragma: no cover
            return {
                "palaces": {},
                "ming_gong": "",
                "analysis": {"error": str(exc)},
                "token": token,
            }

    def calc_liuyao(
        self,
        token: str,
        method: str,
        question: str,
        gender: str = "male",
    ) -> Dict[str, Any]:
        if self.base_url:
            return self._request(
                "POST",
                "/api/liuyao/calc",
                {
                    "token": token,
                    "method": method,
                    "question": question,
                    "gender": gender,
                },
            )
        try:
            from tengod.liuyao_engine import shake_and_calc

            result = shake_and_calc()
            return {
                "method": method,
                "question": question,
                "gua": getattr(result, "ben_gua", "") or getattr(result, "gua_name", "") or "乾为天",
                "lines": [
                    {"position": i + 1, "value": 0}
                    for i in range(6)
                ],
                "token": token,
            }
        except Exception as exc:  # pragma: no cover
            return {
                "method": method,
                "question": question,
                "gua": "乾为天",
                "lines": [],
                "analysis": {"error": str(exc)},
                "token": token,
            }

    def calc_qimen(
        self,
        token: str,
        question: str,
        year: int,
        month: int,
        day: int,
        hour: int,
    ) -> Dict[str, Any]:
        if self.base_url:
            return self._request(
                "POST",
                "/api/qimen/calc",
                {
                    "token": token,
                    "question": question,
                    "year": year,
                    "month": month,
                    "day": day,
                    "hour": hour,
                },
            )
        try:
            from tengod.qimen_engine import calc_qimen

            chart = calc_qimen(year=year, month=month, day=day, hour=hour)
            palaces: Dict[str, Any] = {}
            if hasattr(chart, "palaces"):
                for idx, palace in enumerate(chart.palaces or []):
                    palaces[str(idx + 1)] = {
                        "gan": getattr(palace, "gan", ""),
                        "zhi": getattr(palace, "zhi", ""),
                    }
            return {
                "question": question,
                "palaces": palaces,
                "token": token,
            }
        except Exception as exc:  # pragma: no cover
            return {
                "question": question,
                "palaces": {},
                "analysis": {"error": str(exc)},
                "token": token,
            }

    def search_cases(
        self,
        token: str,
        keyword: str,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        if self.base_url:
            resp = self._request(
                "GET",
                "/api/cases/search",
                {
                    "token": token,
                    "keyword": keyword,
                    "category": category,
                    "limit": limit,
                },
            )
            return resp.get("cases", []) if isinstance(resp, dict) else []
        fake_cases = []
        for i in range(min(limit, 5)):
            fake_cases.append({
                "id": 1000 + i,
                "title": f"{keyword} 命例 #{i + 1}",
                "category": category or "八字",
                "summary": f"关于 {keyword} 的典型案例，标签 {category or '八字'}。",
            })
        return fake_cases

    def get_report(
        self,
        token: str,
        record_id: int,
        format: str = "text",
    ) -> str:
        if self.base_url:
            resp = self._request(
                "GET",
                "/api/report",
                {"token": token, "record_id": record_id, "format": format},
            )
            if isinstance(resp, dict):
                return resp.get("report", "") if resp.get("report") else json.dumps(resp, ensure_ascii=False)
            return str(resp)
        lines = [
            f"命盘报告 #{record_id}",
            f"格式: {format}",
            "八字排盘完毕，详见命盘分析。",
        ]
        return "\n".join(lines)

    def get_share_image(self, token: str, record_id: int) -> str:
        """Return a small base64 encoded pseudo-image."""
        payload = json.dumps({"record_id": record_id, "token": token, "ts": int(time.time())})
        raw = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        return f"data:image/png;base64,{raw}"

    # ---- Internal helpers --------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Perform an HTTP request with simple retry.

        When :mod:`requests` is not installed or the server is unreachable
        we return a minimal empty dict with an ``error`` key so callers
        still have something to work with.
        """
        url = f"{self.base_url.rstrip('/')}{path}"
        last_error: Optional[str] = None
        for attempt in range(3):
            try:
                import requests  # type: ignore

                if method.upper() == "GET":
                    response = requests.get(url, params=data, timeout=self.timeout)
                else:
                    response = requests.post(url, json=data, timeout=self.timeout)
                response.raise_for_status()
                try:
                    return response.json()
                except ValueError:
                    return {"raw": response.text}
            except Exception as exc:  # pragma: no cover - network dependent
                last_error = str(exc)
                time.sleep(min(0.5 * (attempt + 1), 2.0))
        return {"error": last_error or "request failed", "url": url}


# ---------------------------------------------------------------------------
# ShareCardGenerator
# ---------------------------------------------------------------------------
class ShareCardGenerator:
    """WeChat share card utilities with i18n support."""

    def _t(self, text: str, lang: str = "zh-CN") -> str:
        try:
            from tengod.i18n import t
            return t(text, lang)
        except ImportError:
            return text

    def generate_bazi_share(
        self,
        pillars: Any,
        day_master: str,
        geju: str,
        score: float,
        lang: str = "zh-CN",
    ) -> Dict[str, Any]:
        t = self._t
        pillar_text = ""
        if isinstance(pillars, list):
            names = [t("年柱", lang), t("月柱", lang), t("日柱", lang), t("时柱", lang)]
            parts = []
            for i, p in enumerate(pillars[:4]):
                if isinstance(p, dict):
                    gan = p.get("gan", "") or p.get("stem", "") or ""
                    zhi = p.get("zhi", "") or p.get("branch", "") or ""
                    parts.append(f"{names[i]} {gan}{zhi}")
                else:
                    parts.append(str(p))
            pillar_text = " · ".join(parts)
        else:
            pillar_text = str(pillars)
        title = f"{t('命盘', lang)} · {t('日主', lang)} {day_master}" if day_master else t("命盘分析", lang)
        description = (
            f"{t('格局', lang)} {geju or t('未知', lang)}，{t('得分', lang)} {score:.1f}。{pillar_text}"
            if isinstance(score, (int, float))
            else f"{t('格局', lang)} {geju or t('未知', lang)}。{pillar_text}"
        )
        raw = base64.b64encode(
            json.dumps({"title": title, "description": description}, ensure_ascii=False).encode("utf-8")
        ).decode("ascii")
        return {
            "title": title,
            "description": description,
            "image_data": f"data:image/png;base64,{raw}",
            "path": "/pages/share/bazi",
            "pillars": pillars,
            "day_master": day_master,
            "geju": geju,
            "score": score,
        }

    def generate_trajectory_share(
        self,
        trajectory_summary: Any,
        lang: str = "zh-CN",
    ) -> Dict[str, Any]:
        t = self._t
        if isinstance(trajectory_summary, dict):
            day_master = trajectory_summary.get("day_master", "")
            dayun = trajectory_summary.get("dayun", [])
            title = f"{t('命运轨迹', lang)} · {day_master}" if day_master else t("命运轨迹分析", lang)
            years = ", ".join(str(x.get("age_start", "")) for x in dayun[:3] if isinstance(x, dict))
            description = f"{t('大运起运阶段', lang)}：{years or t('未知', lang)}。"
        else:
            title = t("命运轨迹", lang)
            description = str(trajectory_summary)
        raw = base64.b64encode(description.encode("utf-8")).decode("ascii")
        return {
            "title": title,
            "description": description,
            "image_data": f"data:image/png;base64,{raw}",
            "path": "/pages/share/trajectory",
        }

    def generate_ai_share(
        self,
        ai_interpretation: str,
        first_line: str,
        lang: str = "zh-CN",
    ) -> Dict[str, Any]:
        t = self._t
        title = first_line or t("AI 解读", lang)
        description = ai_interpretation[:80] if ai_interpretation else t("查看完整解读", lang) + "..."
        raw = base64.b64encode(ai_interpretation.encode("utf-8")).decode("ascii")
        return {
            "title": title,
            "description": description,
            "image_data": f"data:image/png;base64,{raw}",
            "path": "/pages/share/ai",
        }


# ---------------------------------------------------------------------------
# LocalStorageManager
# ---------------------------------------------------------------------------
class LocalStorageManager:
    """Mini-program client storage simulation using a JSON file."""

    DEFAULT_KEY = "default"

    def __init__(self, storage_path: Optional[str] = None) -> None:
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(__file__),
                ".miniapp_storage.json",
            )
        self.storage_path = storage_path
        self._ensure()

    # ---- low level helpers -------------------------------------------------
    def _ensure(self) -> None:
        directory = os.path.dirname(self.storage_path) or "."
        os.makedirs(directory, exist_ok=True)
        if not os.path.exists(self.storage_path):
            self._write({
                "token": None,
                "token_expires_at": 0,
                "history": [],
                "favorites": {},
            })

    def _read(self) -> Dict[str, Any]:
        try:
            with open(self.storage_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            data = {}
        data.setdefault("token", None)
        data.setdefault("token_expires_at", 0)
        data.setdefault("history", [])
        data.setdefault("favorites", {})
        return data

    def _write(self, data: Dict[str, Any]) -> None:
        tmp_path = f"{self.storage_path}.{os.getpid()}.{uuid.uuid4().hex}"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.storage_path)

    # ---- API ---------------------------------------------------------------
    def save_user_token(self, token: str, expires_at: int) -> None:
        data = self._read()
        data["token"] = token
        data["token_expires_at"] = int(expires_at)
        self._write(data)

    def get_user_token(self) -> Optional[str]:
        data = self._read()
        token = data.get("token")
        expires_at = data.get("token_expires_at", 0) or 0
        if token and expires_at and expires_at < int(time.time()):
            return None
        return token

    def save_calculation_history(self, history_item: Dict[str, Any]) -> None:
        data = self._read()
        history = data.setdefault("history", [])
        item = dict(history_item)
        item.setdefault("created_at", int(time.time()))
        item.setdefault("id", uuid.uuid4().hex)
        history.append(item)
        # Keep history bounded to 200 items
        data["history"] = history[-200:]
        self._write(data)

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        data = self._read()
        history = data.get("history", []) or []
        # Most recent first
        ordered = list(reversed(history))
        return ordered[: max(0, int(limit))]

    def save_favorite(self, record_id: Any, data: Dict[str, Any]) -> None:
        store = self._read()
        favorites = store.setdefault("favorites", {})
        favorites[str(record_id)] = {
            "record_id": record_id,
            "data": dict(data),
            "created_at": int(time.time()),
        }
        self._write(store)

    def get_favorites(self) -> List[Dict[str, Any]]:
        data = self._read()
        favorites = data.get("favorites", {}) or {}
        return [v for v in favorites.values()]

    def clear_all(self) -> None:
        self._write({
            "token": None,
            "token_expires_at": 0,
            "history": [],
            "favorites": {},
        })


# ---------------------------------------------------------------------------
# MiniappConfig
# ---------------------------------------------------------------------------
class MiniappConfig:
    """Configuration helper for mini-programs."""

    _THEMES = {
        "light": {
            "primary": "#C9A96E",
            "background": "#FBF7EF",
            "text": "#2A2118",
            "accent": "#8B5E3C",
        },
        "dark": {
            "primary": "#E8C88E",
            "background": "#1E1A16",
            "text": "#F3E9D7",
            "accent": "#C49A6C",
        },
    }

    _FEATURES = {
        "bazi": True,
        "ziwei": True,
        "liuyao": True,
        "qimen": True,
        "trajectory": True,
        "report": True,
        "share": True,
        "ai_interpretation": True,
        "case_search": True,
    }

    _UI_LABELS = {
        "chart": "命盘",
        "arrange": "排盘",
        "analyze": "分析",
        "report": "报告",
        "dayun": "大运",
        "liunian": "流年",
        "day_zhu": "日柱",
        "day_master": "日主",
        "year_zhu": "年柱",
        "month_zhu": "月柱",
        "hour_zhu": "时柱",
        "gender_male": "男",
        "gender_female": "女",
        "wuxing": "五行",
        "shishen": "十神",
        "geju": "格局",
        "shengxiao": "生肖",
        "login": "登录",
        "share": "分享",
    }

    def theme_config(self, name: str = "light") -> Dict[str, str]:
        return dict(self._THEMES.get(name, self._THEMES["light"]))

    def feature_flags(self) -> Dict[str, bool]:
        return dict(self._FEATURES)

    def get_ui_labels(self) -> Dict[str, str]:
        return dict(self._UI_LABELS)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def validate_wechat_signature(
    timestamp: str,
    nonce: str,
    signature: str,
    token: str,
) -> bool:
    """Verify WeChat server signature."""
    if not (timestamp and nonce and signature and token):
        return False
    items = sorted([str(token), str(timestamp), str(nonce)])
    digest = hashlib.sha1("".join(items).encode("utf-8")).hexdigest()
    return hmac.compare_digest(digest, str(signature))


def build_miniapp_deeplink(path: str, params: Optional[Dict[str, Any]] = None) -> str:
    """Build a mini-program deeplink string with query parameters."""
    path = path or "pages/index/index"
    if not params:
        return path
    parts = []
    for key, value in params.items():
        if value is None:
            continue
        parts.append(f"{key}={value}")
    if not parts:
        return path
    return f"{path}?{'&'.join(parts)}"


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import tempfile

    client = MiniappClient(base_url=None, app_id="demo")
    print("MiniappClient constructed:", client.app_id)

    login_result = client.login("demo-code-123")
    print("Login token sample:", login_result.get("token")[:20], "...")

    bazi = client.calc_bazi(
        login_result["token"], 1990, 6, 15, 12, 0, "male"
    )
    print("Bazi day_master:", bazi.get("day_master"), "geju:", bazi.get("geju"))

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        storage_path = tf.name
    storage = LocalStorageManager(storage_path=storage_path)
    storage.save_user_token(login_result["token"], int(time.time()) + 3600)
    print("Storage round-trip token:", bool(storage.get_user_token()))

    storage.save_calculation_history({"type": "bazi", "record_id": bazi.get("record_id")})
    print("History count:", len(storage.get_history(limit=5)))

    cards = ShareCardGenerator()
    share = cards.generate_bazi_share(
        bazi.get("pillars", []),
        bazi.get("day_master", ""),
        bazi.get("geju", ""),
        82.5,
    )
    print("Share title:", share["title"])
    print("Has image_data:", "image_data" in share)

    os.remove(storage_path)
    print("Done.")
