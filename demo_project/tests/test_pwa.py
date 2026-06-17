#!/usr/bin/env python3
"""
test_pwa.py — 阶段十九 PWA 移动端测试
覆盖：
  - PWA 静态资源挂载（/app/*）
  - manifest.json 完整性
  - service-worker.js 可用性
  - offline.html 离线回退页
  - offline-store.js 离线存储模块
  - 根路由重定向
  - index.html 关键元素（移动端布局、PWA 集成）
  - 案例库 API 与 PWA 集成
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.pop("TENGOD_API_KEY", None)
os.environ["TENGOD_LLM_BACKEND"] = "mock"

from fastapi.testclient import TestClient
from tengod.api_server import app
from tengod.auth import JWTManager, QuotaManager


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """每个测试前清空配额和限流状态"""
    QuotaManager._usage.clear()
    from tengod.api_server import _request_counts
    _request_counts.clear()
    yield
    QuotaManager._usage.clear()
    _request_counts.clear()


@pytest.fixture
def auth_headers():
    token = JWTManager.create_access_token(1, "testuser", "user")
    return {"Authorization": f"Bearer {token}"}


# ════════════════════════════════════════
# 1. PWA 静态资源挂载
# ════════════════════════════════════════

class TestPWAStaticMount:
    """PWA 静态资源挂载测试"""

    def test_root_redirect_to_app(self, client):
        """根路由重定向到 PWA 应用"""
        r = client.get("/", follow_redirects=False)
        assert r.status_code in (302, 307)
        assert "/app/" in r.headers["location"]

    def test_index_html_served(self, client):
        """index.html 可访问"""
        r = client.get("/app/index.html")
        assert r.status_code == 200
        assert "<!DOCTYPE html>" in r.text
        assert "十神架构" in r.text

    def test_manifest_json_served(self, client):
        """manifest.json 可访问"""
        r = client.get("/app/manifest.json")
        assert r.status_code == 200
        m = r.json()
        assert m["name"]
        assert m["short_name"]
        assert m["start_url"] == "/app/index.html"
        assert m["scope"] == "/app/"
        assert m["display"] == "standalone"

    def test_service_worker_served(self, client):
        """service-worker.js 可访问"""
        r = client.get("/app/service-worker.js")
        assert r.status_code == 200
        assert "service-worker" in r.text.lower() or "SW_VERSION" in r.text
        assert "install" in r.text
        assert "fetch" in r.text
        assert "sync" in r.text

    def test_offline_html_served(self, client):
        """offline.html 离线回退页可访问"""
        r = client.get("/app/offline.html")
        assert r.status_code == 200
        assert "离线" in r.text
        assert "十神" in r.text

    def test_offline_store_js_served(self, client):
        """offline-store.js 离线存储模块可访问"""
        r = client.get("/app/offline-store.js")
        assert r.status_code == 200
        assert "OfflineStore" in r.text
        assert "saveBaziRecord" in r.text
        assert "cacheCases" in r.text


# ════════════════════════════════════════
# 2. Manifest 完整性
# ════════════════════════════════════════

class TestManifestCompleteness:
    """manifest.json 完整性测试"""

    def test_manifest_required_fields(self, client):
        """manifest 包含所有必需字段"""
        r = client.get("/app/manifest.json")
        m = r.json()
        # PWA 必需字段
        for field in ["name", "short_name", "start_url", "display", "background_color", "theme_color", "icons"]:
            assert field in m, f"manifest 缺少必需字段: {field}"

    def test_manifest_icons(self, client):
        """manifest icons 配置"""
        m = client.get("/app/manifest.json").json()
        assert len(m["icons"]) >= 2
        sizes = [icon["sizes"] for icon in m["icons"]]
        assert "192x192" in sizes
        assert "512x512" in sizes

    def test_manifest_shortcuts(self, client):
        """manifest shortcuts 快捷方式"""
        m = client.get("/app/manifest.json").json()
        assert "shortcuts" in m
        assert len(m["shortcuts"]) >= 3
        shortcut_urls = [s["url"] for s in m["shortcuts"]]
        # 至少包含排盘和案例的快捷方式
        assert any("bazi" in u for u in shortcut_urls)
        assert any("cases" in u for u in shortcut_urls)

    def test_manifest_display_override(self, client):
        """manifest display_override 配置"""
        m = client.get("/app/manifest.json").json()
        assert "display_override" in m
        assert "standalone" in m["display_override"]

    def test_manifest_scope(self, client):
        """manifest scope 配置"""
        m = client.get("/app/manifest.json").json()
        assert m["scope"] == "/app/"

    def test_manifest_lang(self, client):
        """manifest 语言配置"""
        m = client.get("/app/manifest.json").json()
        assert m["lang"] == "zh-CN"


# ════════════════════════════════════════
# 3. Service Worker 内容验证
# ════════════════════════════════════════

class TestServiceWorkerContent:
    """service-worker.js 内容验证"""

    def test_sw_version(self, client):
        """SW 包含版本号"""
        r = client.get("/app/service-worker.js")
        assert "SW_VERSION" in r.text
        assert "3.0.0" in r.text

    def test_sw_cache_strategy(self, client):
        """SW 包含分层缓存策略"""
        r = client.get("/app/service-worker.js")
        assert "cacheFirst" in r.text
        assert "staleWhileRevalidate" in r.text
        assert "networkFirst" in r.text

    def test_sw_precache_urls(self, client):
        """SW 包含预缓存列表"""
        r = client.get("/app/service-worker.js")
        assert "PRECACHE_URLS" in r.text
        assert "/app/index.html" in r.text
        assert "/app/offline.html" in r.text

    def test_sw_offline_fallback(self, client):
        """SW 包含离线回退逻辑"""
        r = client.get("/app/service-worker.js")
        assert "OFFLINE_URL" in r.text
        assert "/app/offline.html" in r.text

    def test_sw_background_sync(self, client):
        """SW 包含后台同步逻辑"""
        r = client.get("/app/service-worker.js")
        assert "processSyncQueue" in r.text
        assert "SYNC_TAG" in r.text
        assert "handleOfflineWrite" in r.text

    def test_sw_push_notification(self, client):
        """SW 包含推送通知"""
        r = client.get("/app/service-worker.js")
        assert "push" in r.text
        assert "showNotification" in r.text

    def test_sw_message_handler(self, client):
        """SW 包含消息通信"""
        r = client.get("/app/service-worker.js")
        assert "GET_VERSION" in r.text
        assert "GET_QUEUE_SIZE" in r.text
        assert "SKIP_WAITING" in r.text


# ════════════════════════════════════════
# 4. Index.html 关键元素
# ════════════════════════════════════════

class TestIndexHtmlElements:
    """index.html 关键元素测试"""

    def test_mobile_meta_tags(self, client):
        """移动端 meta 标签"""
        r = client.get("/app/index.html")
        assert 'viewport-fit=cover' in r.text
        assert 'apple-mobile-web-app-capable' in r.text
        assert 'apple-mobile-web-app-status-bar-style' in r.text
        assert 'theme-color' in r.text

    def test_pwa_manifest_link(self, client):
        """manifest 链接"""
        r = client.get("/app/index.html")
        assert 'rel="manifest"' in r.text
        assert '/app/manifest.json' in r.text

    def test_pwa_sw_registration(self, client):
        """SW 注册代码"""
        r = client.get("/app/index.html")
        assert 'serviceWorker' in r.text
        assert '/app/service-worker.js' in r.text

    def test_offline_store_import(self, client):
        """离线存储模块引入"""
        r = client.get("/app/index.html")
        assert '/app/offline-store.js' in r.text
        assert 'OfflineStore' in r.text

    def test_mobile_bottom_nav(self, client):
        """移动端底部导航"""
        r = client.get("/app/index.html")
        assert 'nav-bottom' in r.text
        assert 'nav-bottom-btn' in r.text

    def test_safe_area_inset(self, client):
        """安全区域适配"""
        r = client.get("/app/index.html")
        assert 'safe-area-inset' in r.text
        assert 'env(safe-area-inset' in r.text

    def test_bazi_page(self, client):
        """八字排盘页面"""
        r = client.get("/app/index.html")
        assert 'BaziPage' in r.text
        assert 'pillars-grid' in r.text
        assert 'wuxing-bar' in r.text

    def test_cases_page(self, client):
        """案例库页面"""
        r = client.get("/app/index.html")
        assert 'CasesPage' in r.text
        assert 'case-card' in r.text
        assert 'case-filter' in r.text

    def test_pwa_install_hook(self, client):
        """PWA 安装提示 Hook"""
        r = client.get("/app/index.html")
        assert 'usePWAInstall' in r.text
        assert 'beforeinstallprompt' in r.text
        assert 'install-banner' in r.text

    def test_network_status_hook(self, client):
        """网络状态检测 Hook"""
        r = client.get("/app/index.html")
        assert 'useNetworkStatus' in r.text
        assert 'navigator.onLine' in r.text

    def test_touch_friendly_buttons(self, client):
        """触摸友好按钮（44px 最小高度）"""
        r = client.get("/app/index.html")
        assert 'min-height: 44px' in r.text

    def test_responsive_breakpoints(self, client):
        """响应式断点"""
        r = client.get("/app/index.html")
        assert '@media (min-width: 768px)' in r.text
        assert '@media (max-width: 767px)' in r.text


# ════════════════════════════════════════
# 5. Offline Store 模块验证
# ════════════════════════════════════════

class TestOfflineStoreModule:
    """offline-store.js 模块验证"""

    def test_offline_store_api(self, client):
        """离线存储 API 完整性"""
        r = client.get("/app/offline-store.js")
        code = r.text
        # 八字记录 API
        for method in ["saveBaziRecord", "listBaziRecords", "getBaziRecord", "deleteBaziRecord", "clearBaziRecords"]:
            assert method in code, f"缺少方法: {method}"
        # 案例缓存 API
        for method in ["cacheCases", "listCachedCases", "getCachedCase", "clearCasesCache"]:
            assert method in code, f"缺少方法: {method}"
        # 同步队列 API
        for method in ["getPendingOpsCount", "listPendingOps", "triggerSync"]:
            assert method in code, f"缺少方法: {method}"
        # 元数据 API
        for method in ["setMeta", "getMeta", "markSynced", "getLastSync"]:
            assert method in code, f"缺少方法: {method}"
        # 网络状态 API
        for method in ["isOnline", "onNetworkChange", "getStats"]:
            assert method in code, f"缺少方法: {method}"

    def test_offline_store_stores(self, client):
        """离线存储包含所有 store"""
        r = client.get("/app/offline-store.js")
        code = r.text
        assert "bazi_records" in code
        assert "cases_cache" in code
        assert "pending-ops" in code
        assert "meta" in code

    def test_offline_store_db_name(self, client):
        """离线存储数据库名称"""
        r = client.get("/app/offline-store.js")
        assert "tengod-offline" in r.text


# ════════════════════════════════════════
# 6. API 与 PWA 集成
# ════════════════════════════════════════

class TestPWAApiIntegration:
    """PWA 与后端 API 集成测试"""

    def test_bazi_api_for_pwa(self, client, auth_headers):
        """八字 API 可供 PWA 调用"""
        r = client.post("/api/bazi/full", json={
            "year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 0, "gender": "male"
        }, headers=auth_headers)
        assert r.status_code == 200

    def test_cases_api_for_pwa(self, client, auth_headers):
        """案例库 API 可供 PWA 调用"""
        r = client.get("/api/cases", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "total" in data or "cases" in data

    def test_cases_categories_for_pwa(self, client, auth_headers):
        """案例分类 API 可供 PWA 调用"""
        r = client.get("/api/cases/categories/list", headers=auth_headers)
        assert r.status_code == 200
        assert "categories" in r.json()

    def test_health_for_sw_precache(self, client):
        """健康检查端点（SW 预缓存）"""
        r = client.get("/api/health")
        assert r.status_code == 200


# ════════════════════════════════════════
# 7. 离线回退页验证
# ════════════════════════════════════════

class TestOfflinePage:
    """offline.html 离线回退页验证"""

    def test_offline_page_content(self, client):
        """离线页内容"""
        r = client.get("/app/offline.html")
        assert r.status_code == 200
        assert "离线" in r.text
        assert "十神" in r.text
        assert "重新连接" in r.text

    def test_offline_page_mobile_meta(self, client):
        """离线页移动端 meta"""
        r = client.get("/app/offline.html")
        assert "viewport" in r.text
        assert "user-scalable" in r.text

    def test_offline_page_styling(self, client):
        """离线页样式"""
        r = client.get("/app/offline.html")
        assert "<style>" in r.text
        assert "background" in r.text
