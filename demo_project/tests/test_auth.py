#!/usr/bin/env python3
"""test_auth.py — 认证模块全面测试

覆盖:
  - PasswordHasher: 密码哈希与验证
  - JWTManager: 令牌创建与验证
  - CurrentUser: 用户上下文与权限检查
  - get_current_user / get_current_user_optional: 认证依赖
  - require_permission / require_role: 权限/角色依赖工厂
  - QuotaManager: API 配额管理
  - auth_middleware: 认证中间件
  - authorize: 端点权限检查 + 配额消耗
  - create_token_pair: 便捷令牌对创建
  - ROLE_PERMISSIONS: 角色权限配置
  - sync_user_to_db / load_users_from_db / check_db_quota / update_db_quota: DB 集成
"""

from __future__ import annotations

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from tengod.auth import (
    PasswordHasher,
    JWTManager,
    CurrentUser,
    get_current_user,
    get_current_user_optional,
    require_permission,
    require_role,
    QuotaManager,
    auth_middleware,
    authorize,
    create_token_pair,
    ROLE_PERMISSIONS,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    sync_user_to_db,
    load_users_from_db,
    check_db_quota,
    update_db_quota,
    _generate_api_key,
)


# ============================================================================
# PasswordHasher
# ============================================================================

class TestPasswordHasher:
    """密码哈希器测试"""

    def test_hash_returns_string(self):
        """hash 返回字符串"""
        result = PasswordHasher.hash("my_password")
        assert isinstance(result, str)
        assert result.startswith("pbkdf2_sha256$")

    def test_hash_format(self):
        """hash 返回正确格式: pbkdf2_sha256$iterations$salt$key"""
        result = PasswordHasher.hash("test123")
        parts = result.split("$")
        assert len(parts) == 4
        assert parts[0] == "pbkdf2_sha256"
        assert parts[1] == "100000"

    def test_hash_is_deterministic_per_call(self):
        """每次调用 hash 生成不同结果（盐不同）"""
        h1 = PasswordHasher.hash("same_password")
        h2 = PasswordHasher.hash("same_password")
        assert h1 != h2

    def test_verify_correct_password(self):
        """验证正确密码返回 True"""
        hashed = PasswordHasher.hash("secret123")
        assert PasswordHasher.verify("secret123", hashed) is True

    def test_verify_wrong_password(self):
        """验证错误密码返回 False"""
        hashed = PasswordHasher.hash("secret123")
        assert PasswordHasher.verify("wrong_password", hashed) is False

    def test_verify_invalid_hash_format(self):
        """无效哈希格式返回 False"""
        assert PasswordHasher.verify("anything", "not_a_valid_hash") is False
        assert PasswordHasher.verify("anything", "bad$format") is False

    def test_verify_empty_hashed(self):
        """空哈希字符串返回 False"""
        assert PasswordHasher.verify("password", "") is False

    def test_verify_empty_password(self):
        """空密码验证"""
        hashed = PasswordHasher.hash("")
        assert PasswordHasher.verify("", hashed) is True
        assert PasswordHasher.verify("not_empty", hashed) is False

    def test_verify_unicode_password(self):
        """Unicode 密码验证"""
        hashed = PasswordHasher.hash("密码测试🔑")
        assert PasswordHasher.verify("密码测试🔑", hashed) is True
        assert PasswordHasher.verify("密码测试", hashed) is False

    def test_verify_tampered_hash(self):
        """篡改过的哈希验证失败"""
        hashed = PasswordHasher.hash("password")
        # 修改最后一个字符
        tampered = hashed[:-1] + ("A" if hashed[-1] != "A" else "B")
        assert PasswordHasher.verify("password", tampered) is False

    def test_verify_handles_exception(self):
        """验证异常时返回 False（如 base64 解码失败）"""
        invalid = "pbkdf2_sha256$100000$!!!not_base64!!!$!!!not_base64!!!"
        assert PasswordHasher.verify("password", invalid) is False

    def test_hash_long_password(self):
        """长密码也能正确哈希和验证"""
        long_pw = "x" * 1000
        hashed = PasswordHasher.hash(long_pw)
        assert PasswordHasher.verify(long_pw, hashed) is True


# ============================================================================
# JWTManager
# ============================================================================

class TestJWTManager:
    """JWT 令牌管理器测试"""

    # ── create_token ──

    def test_create_access_token_returns_string(self):
        """创建 access token 返回字符串"""
        token = JWTManager.create_token(1, "testuser", "user", "access")
        assert isinstance(token, str)
        assert token.count(".") == 2

    def test_create_refresh_token_returns_string(self):
        """创建 refresh token 返回字符串"""
        token = JWTManager.create_token(1, "testuser", "user", "refresh")
        assert isinstance(token, str)
        assert token.count(".") == 2

    def test_create_token_default_expires_in_access(self):
        """access token 默认使用 ACCESS_TOKEN_EXPIRE_MINUTES"""
        with patch("tengod.auth.ACCESS_TOKEN_EXPIRE_MINUTES", 1):
            payload = JWTManager.verify_token(
                JWTManager.create_token(1, "u", "user", "access")
            )
            assert payload is not None
            # 有效期约 60 秒
            assert payload["exp"] - payload["iat"] == 60

    def test_create_token_default_expires_in_refresh(self):
        """refresh token 默认使用 REFRESH_TOKEN_EXPIRE_DAYS"""
        with patch("tengod.auth.REFRESH_TOKEN_EXPIRE_DAYS", 1):
            payload = JWTManager.verify_token(
                JWTManager.create_token(1, "u", "user", "refresh")
            )
            assert payload is not None
            assert payload["exp"] - payload["iat"] == 86400

    def test_create_token_custom_expires_in(self):
        """自定义 expires_in"""
        token = JWTManager.create_token(1, "u", "user", "access", expires_in=30)
        payload = JWTManager.verify_token(token)
        assert payload is not None
        assert payload["exp"] - payload["iat"] == 30

    def test_create_token_payload_fields(self):
        """token payload 包含所有必要字段"""
        token = JWTManager.create_token(42, "alice", "admin", "access")
        payload = JWTManager.verify_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["username"] == "alice"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"
        assert "iat" in payload
        assert "exp" in payload

    # ── verify_token ──

    def test_verify_valid_token(self):
        """验证有效 token 返回 payload"""
        token = JWTManager.create_access_token(1, "user", "user")
        payload = JWTManager.verify_token(token)
        assert payload is not None
        assert payload["username"] == "user"

    def test_verify_expired_token(self):
        """验证过期 token 返回 None"""
        token = JWTManager.create_token(1, "u", "user", "access", expires_in=-1)
        payload = JWTManager.verify_token(token)
        assert payload is None

    def test_verify_invalid_format(self):
        """无效格式返回 None"""
        assert JWTManager.verify_token("not.a.token.extra") is None
        assert JWTManager.verify_token("no_dots") is None
        assert JWTManager.verify_token("") is None

    def test_verify_tampered_signature(self):
        """篡改签名返回 None"""
        token = JWTManager.create_access_token(1, "user", "user")
        parts = token.split(".")
        # 修改 payload 部分
        tampered = parts[0] + ".tampered_payload." + parts[2]
        assert JWTManager.verify_token(tampered) is None

    def test_verify_tampered_payload(self):
        """篡改 payload 返回 None"""
        token = JWTManager.create_access_token(1, "user", "user")
        parts = token.split(".")
        # 修改 payload 前面部分（签名不匹配）
        tampered = parts[0] + "." + "X" + parts[1][1:] + "." + parts[2]
        assert JWTManager.verify_token(tampered) is None

    def test_verify_with_different_secret(self):
        """不同密钥签名的 token 验证失败"""
        token = JWTManager.create_access_token(1, "user", "user")
        with patch("tengod.auth.JWT_SECRET", "different_secret"):
            assert JWTManager.verify_token(token) is None

    def test_verify_handles_exception(self):
        """验证时异常返回 None"""
        assert JWTManager.verify_token(None) is None  # type: ignore

    # ── create_access_token ──

    def test_create_access_token(self):
        """create_access_token 快捷方法"""
        token = JWTManager.create_access_token(1, "user", "user")
        payload = JWTManager.verify_token(token)
        assert payload is not None
        assert payload["type"] == "access"

    # ── create_refresh_token ──

    def test_create_refresh_token(self):
        """create_refresh_token 快捷方法"""
        token = JWTManager.create_refresh_token(1, "user", "user")
        payload = JWTManager.verify_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"

    # ── 边界情况 ──

    def test_token_with_zero_user_id(self):
        """user_id=0 的 token"""
        token = JWTManager.create_access_token(0, "guest", "guest")
        payload = JWTManager.verify_token(token)
        assert payload is not None
        assert payload["sub"] == "0"

    def test_token_with_special_chars_username(self):
        """用户名含特殊字符"""
        token = JWTManager.create_access_token(1, "user@name!test", "user")
        payload = JWTManager.verify_token(token)
        assert payload is not None
        assert payload["username"] == "user@name!test"


# ============================================================================
# CurrentUser
# ============================================================================

class TestCurrentUser:
    """当前用户数据类测试"""

    def test_has_permission_admin_wildcard(self):
        """admin 拥有所有权限（通配符 *）"""
        user = CurrentUser(id=1, username="admin", role="admin", permissions=["*"])
        assert user.has_permission("any_permission") is True
        assert user.has_permission("bazi:calc") is True
        assert user.has_permission("nonexistent") is True

    def test_has_permission_exact_match(self):
        """普通用户精确匹配权限"""
        user = CurrentUser(id=2, username="user", role="user",
                           permissions=["bazi:calc", "chat:send"])
        assert user.has_permission("bazi:calc") is True
        assert user.has_permission("chat:send") is True

    def test_has_permission_no_match(self):
        """用户没有对应权限"""
        user = CurrentUser(id=2, username="user", role="user",
                           permissions=["bazi:calc"])
        assert user.has_permission("admin:delete") is False

    def test_has_permission_empty_permissions(self):
        """空权限列表"""
        user = CurrentUser(id=3, username="guest", role="guest", permissions=[])
        assert user.has_permission("anything") is False

    def test_is_admin_true(self):
        """admin 角色 is_admin=True"""
        user = CurrentUser(id=1, username="admin", role="admin", permissions=["*"])
        assert user.is_admin is True

    def test_is_admin_false(self):
        """非 admin 角色 is_admin=False"""
        user = CurrentUser(id=2, username="user", role="user", permissions=[])
        assert user.is_admin is False

    def test_is_authenticated_default(self):
        """默认 is_authenticated=True"""
        user = CurrentUser(id=1, username="u", role="user", permissions=[])
        assert user.is_authenticated is True

    def test_is_authenticated_false(self):
        """显式设置 is_authenticated=False"""
        user = CurrentUser(id=0, username="guest", role="guest", permissions=[],
                           is_authenticated=False)
        assert user.is_authenticated is False


# ============================================================================
# get_current_user
# ============================================================================

class TestGetCurrentUser:
    """认证依赖 get_current_user 测试"""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        """有效 token 返回 CurrentUser"""
        token = JWTManager.create_access_token(1, "testuser", "user")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = await get_current_user(credentials=creds)
        assert isinstance(user, CurrentUser)
        assert user.id == 1
        assert user.username == "testuser"
        assert user.role == "user"

    @pytest.mark.asyncio
    async def test_missing_credentials_raises_401(self):
        """无凭据抛 401"""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_scheme_raises_401(self):
        """非 Bearer scheme 抛 401"""
        token = JWTManager.create_access_token(1, "u", "user")
        creds = HTTPAuthorizationCredentials(scheme="Basic", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        """无效 token 抛 401"""
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.token")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self):
        """过期 token 抛 401"""
        token = JWTManager.create_token(1, "u", "user", "access", expires_in=-1)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_raises_401(self):
        """refresh token 抛 401（类型错误）"""
        token = JWTManager.create_refresh_token(1, "u", "user")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_role_gets_all_permissions(self):
        """admin 角色获得完整权限"""
        token = JWTManager.create_access_token(1, "adminuser", "admin")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = await get_current_user(credentials=creds)
        assert user.has_permission("any_permission") is True

    @pytest.mark.asyncio
    async def test_unknown_role_defaults_to_guest(self):
        """未知角色默认获得 guest 权限"""
        token = JWTManager.create_access_token(1, "u", "nonexistent_role")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = await get_current_user(credentials=creds)
        assert user.role == "nonexistent_role"
        assert user.permissions == []


# ============================================================================
# get_current_user_optional
# ============================================================================

class TestGetCurrentUserOptional:
    """可选认证依赖 get_current_user_optional 测试"""

    @pytest.mark.asyncio
    async def test_valid_token_returns_authenticated_user(self):
        """有效 token 返回已认证用户"""
        token = JWTManager.create_access_token(1, "testuser", "user")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = await get_current_user_optional(credentials=creds)
        assert user.id == 1
        assert user.is_authenticated is True

    @pytest.mark.asyncio
    async def test_missing_credentials_returns_guest(self):
        """无凭据返回 guest 用户"""
        user = await get_current_user_optional(credentials=None)
        assert user.id == 0
        assert user.username == "guest"
        assert user.role == "guest"
        assert user.is_authenticated is True  # dataclass default

    @pytest.mark.asyncio
    async def test_invalid_scheme_returns_guest(self):
        """非 Bearer scheme 返回 guest"""
        token = JWTManager.create_access_token(1, "u", "user")
        creds = HTTPAuthorizationCredentials(scheme="Basic", credentials=token)
        user = await get_current_user_optional(credentials=creds)
        assert user.role == "guest"

    @pytest.mark.asyncio
    async def test_invalid_token_returns_guest(self):
        """无效 token 返回 guest"""
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token")
        user = await get_current_user_optional(credentials=creds)
        assert user.role == "guest"
        assert user.id == 0

    @pytest.mark.asyncio
    async def test_expired_token_returns_guest(self):
        """过期 token 返回 guest"""
        token = JWTManager.create_token(1, "u", "user", "access", expires_in=-1)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = await get_current_user_optional(credentials=creds)
        assert user.role == "guest"


# ============================================================================
# require_permission
# ============================================================================

class TestRequirePermission:
    """权限检查依赖工厂 require_permission 测试"""

    @pytest.mark.asyncio
    async def test_user_with_permission_passes(self):
        """拥有权限的用户通过检查"""
        user = CurrentUser(id=1, username="u", role="user",
                           permissions=["bazi:calc", "chat:send"])
        checker = require_permission("bazi:calc")
        result = await checker(user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_user_without_permission_raises_403(self):
        """无权限用户抛 403"""
        user = CurrentUser(id=1, username="u", role="user",
                           permissions=["chat:send"])
        checker = require_permission("bazi:calc")
        with pytest.raises(HTTPException) as exc_info:
            await checker(user=user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_none_user_raises_401(self):
        """None 用户抛 401"""
        checker = require_permission("bazi:calc")
        with pytest.raises(HTTPException) as exc_info:
            await checker(user=None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_wildcard_passes(self):
        """admin 通配符权限通过所有检查"""
        user = CurrentUser(id=1, username="admin", role="admin", permissions=["*"])
        checker = require_permission("any_permission")
        result = await checker(user=user)
        assert result is user


# ============================================================================
# require_role
# ============================================================================

class TestRequireRole:
    """角色检查依赖工厂 require_role 测试"""

    @pytest.mark.asyncio
    async def test_user_with_role_passes(self):
        """拥有角色的用户通过检查"""
        user = CurrentUser(id=1, username="admin", role="admin", permissions=["*"])
        checker = require_role("admin")
        result = await checker(user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_user_without_role_raises_403(self):
        """无角色用户抛 403"""
        user = CurrentUser(id=1, username="u", role="user", permissions=[])
        checker = require_role("admin")
        with pytest.raises(HTTPException) as exc_info:
            await checker(user=user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_none_user_raises_401(self):
        """None 用户抛 401"""
        checker = require_role("admin")
        with pytest.raises(HTTPException) as exc_info:
            await checker(user=None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_multiple_roles_match(self):
        """多角色中任一匹配即通过"""
        user = CurrentUser(id=1, username="u", role="user", permissions=[])
        checker = require_role("admin", "user", "moderator")
        result = await checker(user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_multiple_roles_no_match(self):
        """多角色无一匹配抛 403"""
        user = CurrentUser(id=1, username="guest", role="guest", permissions=[])
        checker = require_role("admin", "user")
        with pytest.raises(HTTPException) as exc_info:
            await checker(user=user)
        assert exc_info.value.status_code == 403


# ============================================================================
# QuotaManager
# ============================================================================

class TestQuotaManager:
    """API 配额管理器测试"""

    def test_check_first_call_allows(self):
        """首次调用允许"""
        QuotaManager.reset(1)
        allowed, used, remaining = QuotaManager.check(1, 100)
        assert allowed is True
        assert used == 0
        assert remaining == 100

    def test_check_under_quota(self):
        """未达配额允许"""
        QuotaManager.reset(1)
        for _ in range(50):
            QuotaManager.consume(1)
        allowed, used, remaining = QuotaManager.check(1, 100)
        assert allowed is True
        assert used == 50
        assert remaining == 50

    def test_check_at_quota_limit(self):
        """达到配额限制拒绝"""
        QuotaManager.reset(1)
        for _ in range(100):
            QuotaManager.consume(1)
        allowed, used, remaining = QuotaManager.check(1, 100)
        assert allowed is False
        assert used == 100
        assert remaining == 0

    def test_check_over_quota(self):
        """超过配额拒绝"""
        QuotaManager.reset(1)
        for _ in range(101):
            QuotaManager.consume(1)
        allowed, used, remaining = QuotaManager.check(1, 100)
        assert allowed is False
        assert used == 101
        assert remaining == 0

    def test_consume_increments_usage(self):
        """consume 递增使用次数"""
        QuotaManager.reset(1)
        QuotaManager.consume(1)
        QuotaManager.consume(1)
        allowed, used, _ = QuotaManager.check(1, 100)
        assert used == 2

    def test_get_usage_returns_dict(self):
        """get_usage 返回使用情况"""
        QuotaManager.reset(1)
        QuotaManager.consume(1)
        usage = QuotaManager.get_usage(1)
        assert isinstance(usage, dict)
        today = QuotaManager._today()
        assert today in usage
        assert usage[today] == 1

    def test_get_usage_nonexistent_user(self):
        """不存在用户返回空字典"""
        assert QuotaManager.get_usage(99999) == {}

    def test_reset_clears_usage(self):
        """reset 清除使用记录"""
        QuotaManager.consume(1)
        QuotaManager.reset(1)
        allowed, used, remaining = QuotaManager.check(1, 100)
        assert allowed is True
        assert used == 0
        assert remaining == 100

    def test_quota_per_user_isolated(self):
        """不同用户配额隔离"""
        QuotaManager.reset(1)
        QuotaManager.reset(2)
        QuotaManager.consume(1)
        QuotaManager.consume(1)
        allowed, used, _ = QuotaManager.check(2, 100)
        assert allowed is True
        assert used == 0

    def test_consume_creates_new_entry(self):
        """consume 为新用户创建条目"""
        QuotaManager.reset(999)
        QuotaManager.consume(999)
        usage = QuotaManager.get_usage(999)
        assert len(usage) > 0

    def test_check_cleans_old_dates(self):
        """check 清理旧日期数据"""
        QuotaManager.reset(1)
        QuotaManager.consume(1)
        # 注入旧日期
        QuotaManager._usage["1"]["2000-01-01"] = 50
        QuotaManager.check(1, 100)
        assert "2000-01-01" not in QuotaManager._usage.get("1", {})


# ============================================================================
# auth_middleware
# ============================================================================

class TestAuthMiddleware:
    """认证中间件测试"""

    @pytest.mark.asyncio
    async def test_no_auth_header_sets_none(self):
        """无 Authorization header 时 current_user=None"""
        request = MagicMock()
        request.headers = {"Authorization": ""}
        request.state = MagicMock()
        call_next = AsyncMock(return_value=MagicMock())

        await auth_middleware(request, call_next)
        assert request.state.current_user is None

    @pytest.mark.asyncio
    async def test_valid_bearer_sets_user(self):
        """有效 Bearer token 设置 current_user"""
        token = JWTManager.create_access_token(1, "testuser", "user")
        request = MagicMock()
        request.headers = {"Authorization": f"Bearer {token}"}
        request.state = MagicMock()
        call_next = AsyncMock(return_value=MagicMock())

        await auth_middleware(request, call_next)
        assert request.state.current_user is not None
        assert request.state.current_user.id == 1
        assert request.state.current_user.username == "testuser"

    @pytest.mark.asyncio
    async def test_invalid_token_sets_none(self):
        """无效 token 时 current_user=None"""
        request = MagicMock()
        request.headers = {"Authorization": "Bearer invalid.token.here"}
        request.state = MagicMock()
        call_next = AsyncMock(return_value=MagicMock())

        await auth_middleware(request, call_next)
        assert request.state.current_user is None

    @pytest.mark.asyncio
    async def test_refresh_token_sets_none(self):
        """refresh token 不设置 current_user"""
        token = JWTManager.create_refresh_token(1, "u", "user")
        request = MagicMock()
        request.headers = {"Authorization": f"Bearer {token}"}
        request.state = MagicMock()
        call_next = AsyncMock(return_value=MagicMock())

        await auth_middleware(request, call_next)
        assert request.state.current_user is None

    @pytest.mark.asyncio
    async def test_non_bearer_scheme_ignored(self):
        """非 Bearer scheme 忽略"""
        token = JWTManager.create_access_token(1, "u", "user")
        request = MagicMock()
        request.headers = {"Authorization": f"Basic {token}"}
        request.state = MagicMock()
        call_next = AsyncMock(return_value=MagicMock())

        await auth_middleware(request, call_next)
        assert request.state.current_user is None

    @pytest.mark.asyncio
    async def test_expired_token_sets_none(self):
        """过期 token 不设置 current_user"""
        token = JWTManager.create_token(1, "u", "user", "access", expires_in=-1)
        request = MagicMock()
        request.headers = {"Authorization": f"Bearer {token}"}
        request.state = MagicMock()
        call_next = AsyncMock(return_value=MagicMock())

        await auth_middleware(request, call_next)
        assert request.state.current_user is None

    @pytest.mark.asyncio
    async def test_calls_next(self):
        """中间件调用 call_next 并返回响应"""
        response = MagicMock()
        call_next = AsyncMock(return_value=response)
        request = MagicMock()
        request.headers = {"Authorization": ""}
        request.state = MagicMock()

        result = await auth_middleware(request, call_next)
        assert result is response
        call_next.assert_awaited_once_with(request)


# ============================================================================
# authorize
# ============================================================================

class TestAuthorize:
    """端点权限检查 authorize 测试"""

    def test_authenticated_user_with_permission(self):
        """已认证用户有权限通过"""
        request = MagicMock()
        user = CurrentUser(id=1, username="u", role="user",
                           permissions=["bazi:calc"])
        request.state.current_user = user

        with patch("tengod.auth.QuotaManager.check", return_value=(True, 0, 100)):
            with patch("tengod.auth.QuotaManager.consume"):
                result = authorize(request, "bazi:calc")
                assert result is user

    def test_authenticated_user_without_permission_raises_403(self):
        """已认证用户无权限抛 403"""
        request = MagicMock()
        user = CurrentUser(id=1, username="u", role="user",
                           permissions=["chat:send"])
        request.state.current_user = user

        with pytest.raises(HTTPException) as exc_info:
            authorize(request, "admin:delete")
        assert exc_info.value.status_code == 403

    def test_no_current_user_raises_401(self):
        """无 current_user 抛 401（guest 无此权限）"""
        request = MagicMock()
        request.state.current_user = None

        with pytest.raises(HTTPException) as exc_info:
            authorize(request, "admin:delete")
        assert exc_info.value.status_code == 401

    def test_guest_with_permission_passes(self):
        """guest 拥有 guest 权限时通过"""
        request = MagicMock()
        request.state.current_user = None

        # guest 有 bazi:calc 权限
        with patch("tengod.auth.QuotaManager.check", return_value=(True, 0, 10)):
            with patch("tengod.auth.QuotaManager.consume"):
                result = authorize(request, "bazi:calc")
                assert result.role == "guest"
                assert result.is_authenticated is False

    def test_quota_exceeded_raises_429(self):
        """配额耗尽抛 429"""
        request = MagicMock()
        user = CurrentUser(id=1, username="u", role="user",
                           permissions=["bazi:calc"])
        request.state.current_user = user

        with patch("tengod.auth.QuotaManager.check", return_value=(False, 100, 0)):
            with pytest.raises(HTTPException) as exc_info:
                authorize(request, "bazi:calc")
            assert exc_info.value.status_code == 429

    def test_consume_quota_false_skips_quota_check(self):
        """consume_quota=False 跳过配额检查"""
        request = MagicMock()
        user = CurrentUser(id=1, username="u", role="user",
                           permissions=["bazi:calc"])
        request.state.current_user = user

        with patch("tengod.auth.QuotaManager.check") as mock_check:
            with patch("tengod.auth.QuotaManager.consume") as mock_consume:
                result = authorize(request, "bazi:calc", consume_quota=False)
                assert result is user
                mock_check.assert_not_called()
                mock_consume.assert_not_called()

    def test_admin_wildcard_permission(self):
        """admin 通配符权限通过任意检查"""
        request = MagicMock()
        user = CurrentUser(id=1, username="admin", role="admin", permissions=["*"])
        request.state.current_user = user

        with patch("tengod.auth.QuotaManager.check", return_value=(True, 0, 10000)):
            with patch("tengod.auth.QuotaManager.consume"):
                result = authorize(request, "any_arbitrary_permission")
                assert result is user


# ============================================================================
# create_token_pair
# ============================================================================

class TestCreateTokenPair:
    """便捷令牌对创建测试"""

    def test_returns_dict_with_all_keys(self):
        """返回包含所有必要字段的字典"""
        result = create_token_pair(1, "testuser", "user")
        assert "access_token" in result
        assert "refresh_token" in result
        assert "token_type" in result
        assert "expires_in" in result

    def test_token_type_is_bearer(self):
        """token_type 为 bearer"""
        result = create_token_pair(1, "u", "user")
        assert result["token_type"] == "bearer"

    def test_expires_in_matches_config(self):
        """expires_in 匹配 ACCESS_TOKEN_EXPIRE_MINUTES"""
        result = create_token_pair(1, "u", "user")
        assert result["expires_in"] == ACCESS_TOKEN_EXPIRE_MINUTES * 60

    def test_access_token_is_valid(self):
        """access_token 可被验证"""
        result = create_token_pair(1, "testuser", "user")
        payload = JWTManager.verify_token(result["access_token"])
        assert payload is not None
        assert payload["type"] == "access"
        assert payload["username"] == "testuser"

    def test_refresh_token_is_valid(self):
        """refresh_token 可被验证"""
        result = create_token_pair(1, "testuser", "user")
        payload = JWTManager.verify_token(result["refresh_token"])
        assert payload is not None
        assert payload["type"] == "refresh"
        assert payload["username"] == "testuser"

    def test_tokens_are_different(self):
        """access_token 和 refresh_token 不同"""
        result = create_token_pair(1, "u", "user")
        assert result["access_token"] != result["refresh_token"]


# ============================================================================
# ROLE_PERMISSIONS
# ============================================================================

class TestRolePermissions:
    """角色权限配置测试"""

    def test_has_admin_role(self):
        """存在 admin 角色"""
        assert "admin" in ROLE_PERMISSIONS
        assert ROLE_PERMISSIONS["admin"]["name"] == "管理员"
        assert "*" in ROLE_PERMISSIONS["admin"]["permissions"]
        assert ROLE_PERMISSIONS["admin"]["quota_daily"] == 10000

    def test_has_user_role(self):
        """存在 user 角色"""
        assert "user" in ROLE_PERMISSIONS
        assert ROLE_PERMISSIONS["user"]["name"] == "普通用户"
        assert "bazi:calc" in ROLE_PERMISSIONS["user"]["permissions"]
        assert ROLE_PERMISSIONS["user"]["quota_daily"] == 100

    def test_has_guest_role(self):
        """存在 guest 角色"""
        assert "guest" in ROLE_PERMISSIONS
        assert ROLE_PERMISSIONS["guest"]["name"] == "访客"
        assert "bazi:calc" in ROLE_PERMISSIONS["guest"]["permissions"]
        assert ROLE_PERMISSIONS["guest"]["quota_daily"] == 10

    def test_guest_has_fewer_permissions_than_user(self):
        """guest 权限少于 user"""
        guest_perms = set(ROLE_PERMISSIONS["guest"]["permissions"])
        user_perms = set(ROLE_PERMISSIONS["user"]["permissions"])
        assert guest_perms.issubset(user_perms)

    def test_guest_quota_less_than_user(self):
        """guest 配额少于 user"""
        assert ROLE_PERMISSIONS["guest"]["quota_daily"] < ROLE_PERMISSIONS["user"]["quota_daily"]


# ============================================================================
# 配置常量
# ============================================================================

class TestConfig:
    """配置常量测试"""

    def test_access_token_expire_minutes(self):
        """ACCESS_TOKEN_EXPIRE_MINUTES 为正值"""
        assert ACCESS_TOKEN_EXPIRE_MINUTES > 0

    def test_refresh_token_expire_days(self):
        """REFRESH_TOKEN_EXPIRE_DAYS 为正值"""
        assert REFRESH_TOKEN_EXPIRE_DAYS > 0


# ============================================================================
# DB 集成函数
# ============================================================================

class TestDBIntegration:
    """数据库集成函数测试"""

    def test_sync_user_to_db_non_persistent(self):
        """非持久化模式返回用户信息"""
        with patch("tengod.database.is_persistent", return_value=False):
            result = sync_user_to_db("testuser", "password123", "user")
            assert result["username"] == "testuser"
            assert result["role"] == "user"
            assert "user_id" in result

    def test_sync_user_to_db_persistent_new_user(self):
        """持久化模式创建新用户"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None

        with patch("tengod.database.is_persistent", return_value=True):
            with patch("tengod.database.get_db", return_value=mock_db):
                with patch("tengod.auth._generate_api_key", return_value="test_api_key_32bytes_long!"):
                    result = sync_user_to_db("newuser", "pass", "user")
                    assert result["username"] == "newuser"
                    mock_db.get_user.assert_called_once_with(username="newuser")
                    mock_db.create_user.assert_called_once()
                    call_args = mock_db.create_user.call_args[0][0]
                    assert call_args["username"] == "newuser"
                    assert call_args["api_key"] == "test_api_key_32bytes_long!"
                    assert call_args["role"] == "user"

    def test_sync_user_to_db_persistent_existing_user(self):
        """持久化模式已有用户不重复创建"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = {"username": "existing", "role": "user"}

        with patch("tengod.database.is_persistent", return_value=True):
            with patch("tengod.database.get_db", return_value=mock_db):
                result = sync_user_to_db("existing", "pass", "user")
                assert result["username"] == "existing"
                mock_db.create_user.assert_not_called()

    def test_load_users_from_db_non_persistent(self):
        """非持久化模式返回 0"""
        with patch("tengod.database.is_persistent", return_value=False):
            result = load_users_from_db()
            assert result == 0

    def test_load_users_from_db_persistent(self):
        """持久化模式创建种子管理员"""
        mock_db = MagicMock()
        mock_db.get_user.return_value = None

        with patch("tengod.database.is_persistent", return_value=True):
            with patch("tengod.database.get_db", return_value=mock_db):
                with patch("tengod.auth._generate_api_key", return_value="admin_key_32bytes"):
                    with patch.dict("os.environ", {"ADMIN_PASSWORD": "admin123"}):
                        result = load_users_from_db()
                        assert result == 1
                        mock_db.create_user.assert_called_once()

    def test_check_db_quota_non_persistent(self):
        """非持久化模式返回 True"""
        with patch("tengod.database.is_persistent", return_value=False):
            result = check_db_quota("testuser")
            assert result == (True, 0, 0)

    def test_check_db_quota_persistent(self):
        """持久化模式调用 db.check_quota"""
        mock_db = MagicMock()
        mock_db.check_quota.return_value = (True, 5, 95)

        with patch("tengod.database.is_persistent", return_value=True):
            with patch("tengod.database.get_db", return_value=mock_db):
                result = check_db_quota("testuser")
                assert result == (True, 5, 95)
                mock_db.check_quota.assert_called_once_with("testuser")

    def test_update_db_quota_non_persistent(self):
        """非持久化模式返回 True"""
        with patch("tengod.database.is_persistent", return_value=False):
            result = update_db_quota("testuser", 1)
            assert result is True

    def test_update_db_quota_persistent(self):
        """持久化模式调用 db.update_quota"""
        mock_db = MagicMock()
        mock_db.update_quota.return_value = True

        with patch("tengod.database.is_persistent", return_value=True):
            with patch("tengod.database.get_db", return_value=mock_db):
                result = update_db_quota("testuser", 5)
                assert result is True
                mock_db.update_quota.assert_called_once_with("testuser", 5)


# ============================================================================
# _generate_api_key
# ============================================================================

class TestGenerateApiKey:
    """API Key 生成测试"""

    def test_default_length(self):
        """默认长度 32"""
        key = _generate_api_key()
        assert len(key) == 32
        assert isinstance(key, str)

    def test_custom_length(self):
        """自定义长度"""
        key = _generate_api_key(64)
        assert len(key) == 64

    def test_keys_are_unique(self):
        """生成的 key 不重复"""
        keys = {_generate_api_key() for _ in range(20)}
        assert len(keys) == 20

    def test_key_is_hex(self):
        """key 是十六进制字符串"""
        key = _generate_api_key()
        assert all(c in "0123456789abcdef" for c in key)


# ============================================================================
# 综合场景测试
# ============================================================================

class TestIntegrationScenarios:
    """综合场景测试"""

    def test_full_auth_flow(self):
        """完整认证流程：创建令牌 → 验证 → 获取用户 → 权限检查"""
        # 1. 创建令牌对
        pair = create_token_pair(42, "alice", "user")
        assert pair["token_type"] == "bearer"

        # 2. 验证 access token
        payload = JWTManager.verify_token(pair["access_token"])
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["type"] == "access"

        # 3. 验证 refresh token
        payload = JWTManager.verify_token(pair["refresh_token"])
        assert payload is not None
        assert payload["type"] == "refresh"

        # 4. 构造 CurrentUser
        role = payload["role"]
        perms = ROLE_PERMISSIONS[role]["permissions"]
        user = CurrentUser(id=42, username="alice", role=role, permissions=perms)
        assert user.has_permission("bazi:calc") is True
        assert user.is_admin is False

    @pytest.mark.asyncio
    async def test_get_current_user_then_check_permission(self):
        """认证后检查权限的完整流程"""
        token = JWTManager.create_access_token(1, "testuser", "user")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # 获取当前用户
        user = await get_current_user(credentials=creds)
        assert user.username == "testuser"

        # 检查权限
        checker = require_permission("bazi:calc")
        result = await checker(user=user)
        assert result is user

        # 检查无权限场景
        checker = require_permission("admin:delete")
        with pytest.raises(HTTPException) as exc_info:
            await checker(user=user)
        assert exc_info.value.status_code == 403

    def test_quota_exhaustion_flow(self):
        """配额耗尽完整流程"""
        QuotaManager.reset(100)
        # 管理员配额 10000
        allowed, _, remaining = QuotaManager.check(100, 10000)
        assert allowed is True
        assert remaining == 10000

        for _ in range(10000):
            QuotaManager.consume(100)

        allowed, used, remaining = QuotaManager.check(100, 10000)
        assert allowed is False
        assert remaining == 0

    def test_password_hash_and_jwt_flow(self):
        """密码哈希 + JWT 综合流程"""
        # 用户注册：哈希密码
        hashed = PasswordHasher.hash("my_secret_123")
        assert PasswordHasher.verify("my_secret_123", hashed) is True

        # 登录成功：创建令牌
        tokens = create_token_pair(99, "bob", "user")
        payload = JWTManager.verify_token(tokens["access_token"])
        assert payload["username"] == "bob"
        assert payload["sub"] == "99"