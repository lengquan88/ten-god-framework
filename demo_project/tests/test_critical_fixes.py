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