#!/usr/bin/env python3
"""
test_critical_fixes.py — 关键缺陷修复测试

覆盖以下修复：
1. JWT 签名算法修复（hexdigest → base64url）
2. Admin API 认证保护
3. QuotaManager 线程安全
"""

import threading
import time
import pytest
from unittest.mock import MagicMock, patch


class TestJWTManagerSign:
    """JWT 签名算法修复测试"""

    def test_sign_returns_base64url(self):
        """验证 _sign 返回 base64url 编码而非 hex 字符串"""
        from tengod.auth import JWTManager
        message = "test.signing.input"
        signature = JWTManager._sign(message)
        
        import base64
        try:
            padding = 4 - len(signature) % 4
            if padding != 4:
                signature += "=" * padding
            decoded = base64.urlsafe_b64decode(signature)
            assert len(decoded) == 32
        except Exception:
            pytest.fail("Signature is not valid base64url encoding")

    def test_create_and_verify_token(self):
        """验证创建的令牌能被正确验证"""
        from tengod.auth import JWTManager
        token = JWTManager.create_access_token(1, "testuser", "user")
        payload = JWTManager.verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["username"] == "testuser"
        assert payload["role"] == "user"
        assert payload["type"] == "access"

    def test_verify_token_invalid_signature(self):
        """验证无效签名被正确拒绝"""
        from tengod.auth import JWTManager
        token = JWTManager.create_access_token(1, "testuser", "user")
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{parts[1]}.invalid_signature"
        
        payload = JWTManager.verify_token(tampered_token)
        assert payload is None

    def test_token_format_compatibility(self):
        """验证令牌格式符合 JWT 规范"""
        from tengod.auth import JWTManager
        token = JWTManager.create_access_token(1, "testuser", "user")
        parts = token.split(".")
        
        assert len(parts) == 3
        
        import base64
        for part in parts[:2]:
            padding = 4 - len(part) % 4
            if padding != 4:
                part += "=" * padding
            decoded = base64.urlsafe_b64decode(part)
            assert len(decoded) > 0


class TestQuotaManagerThreadSafety:
    """QuotaManager 线程安全测试"""

    def test_concurrent_consume(self):
        """验证并发消耗配额不会导致计数丢失"""
        from tengod.auth import QuotaManager
        
        QuotaManager.reset(999)
        expected_count = 100
        errors = []

        def worker():
            try:
                for _ in range(10):
                    QuotaManager.consume(999)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"
        usage = QuotaManager.get_usage(999)
        today = list(usage.keys())[0] if usage else None
        assert today is not None, "No usage record"
        assert usage[today] == expected_count, f"Expected {expected_count}, got {usage[today]}"

    def test_concurrent_check_and_consume(self):
        """验证并发检查和消耗不会导致竞态条件"""
        from tengod.auth import QuotaManager
        
        QuotaManager.reset(888)
        quota = 50
        success_count = 0
        failure_count = 0
        errors = []

        def worker():
            nonlocal success_count, failure_count
            try:
                for _ in range(10):
                    allowed, _, _ = QuotaManager.check(888, quota)
                    if allowed:
                        QuotaManager.consume(888)
                        success_count += 1
                    else:
                        failure_count += 1
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"
        usage = QuotaManager.get_usage(888)
        today = list(usage.keys())[0] if usage else None
        assert today is not None, "No usage record"
        assert usage[today] == min(100, quota), f"Expected {min(100, quota)}, got {usage[today]}"

    def test_reset_during_concurrent_access(self):
        """验证重置操作在并发访问时的安全性"""
        from tengod.auth import QuotaManager
        
        QuotaManager.reset(777)
        for _ in range(50):
            QuotaManager.consume(777)

        completed = []

        def consumer():
            for _ in range(10):
                QuotaManager.consume(777)
            completed.append(True)

        def reseter():
            time.sleep(0.01)
            QuotaManager.reset(777)
            completed.append(True)

        t1 = threading.Thread(target=consumer)
        t2 = threading.Thread(target=reseter)
        t3 = threading.Thread(target=consumer)
        
        t1.start()
        t2.start()
        t3.start()
        t1.join()
        t2.join()
        t3.join()

        assert len(completed) == 3
        usage = QuotaManager.get_usage(777)
        assert sum(usage.values()) >= 0


class TestAdminApiAuthentication:
    """Admin API 认证保护测试"""

    def test_admin_endpoints_require_admin_role(self):
        """验证管理端点需要管理员角色"""
        from tengod.admin_api import create_admin_app
        from fastapi.testclient import TestClient
        
        app = create_admin_app()
        client = TestClient(app)

        response = client.get("/api/admin/stats")
        assert response.status_code == 401, "未认证请求应返回 401"

        response = client.get("/api/admin/records")
        assert response.status_code == 401, "未认证请求应返回 401"

        response = client.delete("/api/admin/records/1")
        assert response.status_code == 401, "未认证请求应返回 401"

    def test_health_endpoint_public(self):
        """验证健康检查端点无需认证"""
        from tengod.admin_api import create_admin_app
        from fastapi.testclient import TestClient
        
        app = create_admin_app()
        client = TestClient(app)

        response = client.get("/api/admin/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_non_admin_cannot_access_admin_endpoints(self):
        """验证非管理员角色无法访问管理端点"""
        from tengod.admin_api import create_admin_app
        from tengod.auth import JWTManager
        from fastapi.testclient import TestClient
        
        app = create_admin_app()
        client = TestClient(app)

        user_token = JWTManager.create_access_token(1, "user", "user")
        headers = {"Authorization": f"Bearer {user_token}"}

        response = client.get("/api/admin/stats", headers=headers)
        assert response.status_code == 403, "普通用户应返回 403"

    def test_admin_can_access_admin_endpoints(self):
        """验证管理员角色可以访问管理端点"""
        from tengod.admin_api import create_admin_app
        from tengod.auth import JWTManager
        from fastapi.testclient import TestClient
        
        app = create_admin_app()
        client = TestClient(app)

        admin_token = JWTManager.create_access_token(1, "admin", "admin")
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/admin/health")
        assert response.status_code == 200

        response = client.get("/api/admin/stats", headers=headers)
        assert response.status_code == 200


# ============================================================================
# FastAPI Depends 集成级认证 / 授权依赖注入修复测试
#
# 触发场景（修复前）：
#   1. 开发者按文档用法使用 Depends(get_current_user) 或 Depends(require_permission(...))
#   2. 用户请求携带合法的 Bearer token
#   3. 修复前：
#      - get_current_user 的 credentials 参数未声明 Depends(security)，故 FastAPI
#        不会解析 Authorization header，credentials 始终为 None -> 永远 401
#      - require_permission / require_role 内部 check_perm / check_role 的 user
#        参数未声明 Depends(get_current_user)，FastAPI 无法注入，user 永远 = None
#        -> 永远 401
#   4. 修复后：上述依赖能正确通过 Depends 链解析 Authorization 并校验权限
# ============================================================================


class TestAuthDependsIntegration:
    """FastAPI Depends 级认证与权限依赖注入测试"""

    def _build_app(self):
        from fastapi import Depends, FastAPI
        from tengod.auth import (
            CurrentUser,
            get_current_user,
            get_current_user_optional,
            require_permission,
            require_role,
        )

        app = FastAPI()

        @app.get("/me")
        def me(user: CurrentUser = Depends(get_current_user)):
            return {"id": user.id, "username": user.username, "role": user.role}

        @app.get("/me-optional")
        def me_opt(user: CurrentUser = Depends(get_current_user_optional)):
            return {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "is_authenticated": user.is_authenticated,
            }

        @app.get("/need-bazi-calc", dependencies=[Depends(require_permission("bazi:calc"))])
        def need_bazi_calc():
            return {"ok": True}

        @app.get(
            "/need-admin",
            dependencies=[Depends(require_role("admin"))],
        )
        def need_admin():
            return {"ok": True}

        @app.get("/inject-user", response_model=dict)
        def inject_user(
            user: CurrentUser = Depends(require_permission("bazi:report")),
        ):
            return {"id": user.id, "username": user.username}

        return app

    def test_get_current_user_injects_via_bearer_header(self):
        """Depends(get_current_user) 能通过 HTTP Bearer token 解析出用户"""
        from fastapi.testclient import TestClient
        from tengod.auth import JWTManager

        app = self._build_app()
        client = TestClient(app)

        token = JWTManager.create_access_token(7, "alice", "user")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/me", headers=headers)
        assert resp.status_code == 200, f"expected 200 got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["id"] == 7
        assert body["username"] == "alice"
        assert body["role"] == "user"

    def test_get_current_user_missing_header_returns_401(self):
        """Depends(get_current_user) 缺少认证头时返回 401"""
        from fastapi.testclient import TestClient

        client = TestClient(self._build_app())
        resp = client.get("/me")
        assert resp.status_code == 401
        # 错误消息应当和 401 语义匹配
        assert resp.json()["detail"] in ("未提供认证令牌", "令牌无效或已过期", "未认证")

    def test_get_current_user_optional_returns_guest_when_no_header(self):
        """Depends(get_current_user_optional) 无 header 时返回 guest"""
        from fastapi.testclient import TestClient

        client = TestClient(self._build_app())
        resp = client.get("/me-optional")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == 0
        assert body["username"] == "guest"
        assert body["role"] == "guest"

    def test_get_current_user_optional_with_header_returns_user(self):
        """Depends(get_current_user_optional) 有 header 时返回已认证用户"""
        from fastapi.testclient import TestClient
        from tengod.auth import JWTManager

        client = TestClient(self._build_app())
        token = JWTManager.create_access_token(42, "bob", "user")
        resp = client.get("/me-optional", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["id"] == 42
        assert resp.json()["username"] == "bob"

    def test_require_permission_injects_user_and_passes(self):
        """Depends(require_permission(...)) 有合法 token 且有权限时通过"""
        from fastapi.testclient import TestClient
        from tengod.auth import JWTManager

        client = TestClient(self._build_app())
        token = JWTManager.create_access_token(1, "user1", "user")  # user 有 bazi:calc
        resp = client.get("/need-bazi-calc", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, f"unexpected {resp.status_code}: {resp.text}"
        assert resp.json()["ok"] is True

    def test_require_permission_no_token_returns_401_not_internal_error(self):
        """Depends(require_permission(...)) 无 token 时返回 401（而不是永远 401/注入失败时的其他异常）"""
        from fastapi.testclient import TestClient

        client = TestClient(self._build_app())
        resp = client.get("/need-bazi-calc")
        assert resp.status_code == 401
        # 保证是标准 HTTPException 响应而不是 500/422
        assert "detail" in resp.json()

    def test_require_permission_wrong_permission_returns_403(self):
        """Depends(require_permission(...)) 无对应权限时返回 403"""
        from fastapi.testclient import TestClient
        from tengod.auth import JWTManager

        client = TestClient(self._build_app())
        # guest 只有 bazi:calc，没有 bazi:report
        token = JWTManager.create_access_token(0, "guest", "guest")
        resp = client.get(
            "/inject-user", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, f"expected 403 got {resp.status_code}: {resp.text}"
        assert "权限不足" in resp.json()["detail"]

    def test_require_role_admin_blocks_user(self):
        """Depends(require_role("admin")) 普通用户被 403 拒绝"""
        from fastapi.testclient import TestClient
        from tengod.auth import JWTManager

        client = TestClient(self._build_app())
        token = JWTManager.create_access_token(5, "staff", "user")
        resp = client.get("/need-admin", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
        assert "角色不足" in resp.json()["detail"]

    def test_require_role_admin_allows_admin(self):
        """Depends(require_role("admin")) 管理员通过"""
        from fastapi.testclient import TestClient
        from tengod.auth import JWTManager

        client = TestClient(self._build_app())
        token = JWTManager.create_access_token(9, "boss", "admin")
        resp = client.get("/need-admin", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_require_permission_injects_user_into_endpoint_param(self):
        """require_permission 通过 Depends 注入当前用户到路由参数"""
        from fastapi.testclient import TestClient
        from tengod.auth import JWTManager, ROLE_PERMISSIONS

        client = TestClient(self._build_app())
        # admin 有 * 权限，包含 bazi:report
        token = JWTManager.create_access_token(100, "chief", "admin")
        resp = client.get(
            "/inject-user", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200, f"{resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["id"] == 100
        assert body["username"] == "chief"