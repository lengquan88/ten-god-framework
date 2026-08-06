#!/usr/bin/env python3
"""test_src_auth_service.py — src/auth_service.py 认证与权限校验模块测试

覆盖:
  - VALID_USERS: 有效用户集合的完整性与不可变性
  - authenticate: 身份验证的正向/负向/边界路径
  - check_permission: 资源访问权限校验，包括通配符、未注册资源、未知用户
"""

from __future__ import annotations

import copy

import pytest

from src.auth_service import VALID_USERS, authenticate, check_permission


# ============================================================================
# VALID_USERS 数据契约
# ============================================================================

class TestValidUsers:
    """有效用户集合契约"""

    def test_contains_expected_roles(self):
        """VALID_USERS 覆盖 admin / developer / viewer 三类角色"""
        assert "admin" in VALID_USERS
        assert "developer" in VALID_USERS
        assert "viewer" in VALID_USERS

    def test_is_frozen_to_contract(self):
        """集合大小固定为 3，防止无意新增/删除角色"""
        assert len(VALID_USERS) == 3

    def test_members_are_strings(self):
        """所有成员为字符串，避免非字符串类型混入"""
        assert all(isinstance(u, str) for u in VALID_USERS)


# ============================================================================
# authenticate
# ============================================================================

class TestAuthenticate:
    """身份验证"""

    @pytest.mark.parametrize("username", ["admin", "developer", "viewer"])
    def test_valid_users_authenticate(self, username):
        """三类有效角色均能通过认证"""
        assert authenticate(username) is True

    @pytest.mark.parametrize(
        "username",
        [
            "",
            "Admin",       # 大小写敏感
            "ADMIN",
            "root",
            "administrator",
            "guest",
            None,          # 非字符串
            123,           # 非字符串
        ],
    )
    def test_invalid_users_rejected(self, username):
        """无效用户、大小写错误、非字符串类型均应被拒绝"""
        assert authenticate(username) is False

    def test_new_roles_not_implicitly_accepted(self):
        """VALID_USERS 之外的新角色必须被拒绝，不能因实现缺陷而放行"""
        assert authenticate("superadmin") is False
        assert authenticate("dev") is False


# ============================================================================
# check_permission
# ============================================================================

class TestCheckPermission:
    """资源访问权限校验"""

    # ── admin 通配符 ──────────────────────────────────────────────────

    def test_admin_has_wildcard_to_all_resources(self):
        """admin 对任意资源均有访问权（通配符 '*'）"""
        for resource in ["read", "write", "delete", "admin", "*", "anything"]:
            assert check_permission("admin", resource) is True

    # ── developer 双权限 ──────────────────────────────────────────────

    def test_developer_has_read_and_write(self):
        """developer 拥有 read 与 write 权限"""
        assert check_permission("developer", "read") is True
        assert check_permission("developer", "write") is True

    def test_developer_cannot_delete(self):
        """developer 不应拥有 delete 等其他权限"""
        assert check_permission("developer", "delete") is False
        assert check_permission("developer", "admin") is False

    # ── viewer 只读 ──────────────────────────────────────────────────

    def test_viewer_read_only(self):
        """viewer 仅拥有 read 权限"""
        assert check_permission("viewer", "read") is True
        assert check_permission("viewer", "write") is False
        assert check_permission("viewer", "delete") is False

    # ── 未知用户 ────────────────────────────────────────────────────

    def test_unknown_user_rejected(self):
        """未知用户（包括空串与新角色）在任何资源上均被拒绝"""
        for user in ["", "guest", "root", "superadmin"]:
            assert check_permission(user, "read") is False
            assert check_permission(user, "write") is False
            assert check_permission(user, "admin") is False

    # ── 边界资源名 ──────────────────────────────────────────────────

    def test_nonexistent_resource_for_known_user(self):
        """已知用户访问不存在的资源应被视为越权"""
        assert check_permission("developer", "execute") is False
        assert check_permission("viewer", "list") is False

    def test_empty_resource_name(self):
        """空字符串资源名不得匹配任何权限"""
        assert check_permission("admin", "") is True  # 通配符仍放行
        assert check_permission("developer", "") is False
        assert check_permission("viewer", "") is False

    def test_none_resource_does_not_crash(self):
        """None 作为资源名时函数不得抛异常"""
        try:
            result = check_permission("developer", None)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"check_permission 不应抛异常: {exc}")
        # None 与任何已登记权限字符串不相等，不能放行
        assert result is False


# ============================================================================
# 认证与权限协同（集成视角）
# ============================================================================

class TestAuthAndPermissionIntegration:
    """authenticate + check_permission 的组合行为"""

    def test_unauthenticated_user_cannot_escalate(self):
        """未通过认证的用户即便在权限映射中存在，也不应被信任
        （当前实现未将 authenticate 与 check_permission 串联，
         此测试固化 check_permission 的独立行为，避免未来重构时
         意外给予未认证用户管理员权限。）"""
        # 空字符串用户不在 permissions 映射中
        assert check_permission("", "read") is False

    def test_copy_of_permissions_does_not_leak_state(self):
        """调用不应修改内部权限字典（通过深拷贝模拟并发场景）"""
        snapshot = copy.deepcopy(VALID_USERS)
        for user in ["admin", "developer", "viewer"]:
            check_permission(user, "read")
        assert snapshot == VALID_USERS
