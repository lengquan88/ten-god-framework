"""
test_src_auth_service.py — 认证服务安全测试
=============================================
覆盖 src/auth_service.py 的认证与权限校验逻辑。

高风险路径：
  1. authenticate — 有效/无效/空用户名边界
  2. check_permission — admin 通配符权限、角色分级访问控制
  3. 未知用户拒绝访问（安全默认值）
  4. 权限边界：恰好拥有/恰好缺失
"""

from __future__ import annotations

import os
import sys

import pytest

# src/ 目录无 __init__.py，需手动加入 sys.path
_src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
_src_dir = os.path.abspath(_src_dir)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import auth_service


# ============================================================================
# 1. authenticate 认证测试
# ============================================================================

class TestAuthenticate:
    """authenticate() 用户身份验证"""

    def test_valid_users_accepted(self):
        """所有预定义用户应认证成功"""
        for user in ("admin", "developer", "viewer"):
            assert auth_service.authenticate(user) is True

    def test_invalid_user_rejected(self):
        """未知用户应认证失败"""
        assert auth_service.authenticate("hacker") is False

    def test_empty_string_rejected(self):
        """空字符串应认证失败"""
        assert auth_service.authenticate("") is False

    def test_case_sensitive(self):
        """用户名大小写敏感——'Admin' 不等于 'admin'"""
        assert auth_service.authenticate("Admin") is False
        assert auth_service.authenticate("ADMIN") is False

    def test_none_username_rejected(self):
        """None 用户名应触发安全失败（不在 VALID_USERS 中）"""
        assert auth_service.authenticate(None) is False


# ============================================================================
# 2. check_permission 权限校验测试
# ============================================================================

class TestCheckPermission:
    """check_permission() 资源访问权限校验"""

    def test_admin_wildcard_access(self):
        """admin 拥有 '*' 通配符，可访问任意资源"""
        assert auth_service.check_permission("admin", "read") is True
        assert auth_service.check_permission("admin", "write") is True
        assert auth_service.check_permission("admin", "delete") is True
        assert auth_service.check_permission("admin", "anything") is True

    def test_developer_read_write(self):
        """developer 拥有 read 和 write 权限"""
        assert auth_service.check_permission("developer", "read") is True
        assert auth_service.check_permission("developer", "write") is True

    def test_developer_no_delete(self):
        """developer 无 delete 权限"""
        assert auth_service.check_permission("developer", "delete") is False

    def test_viewer_read_only(self):
        """viewer 仅有 read 权限"""
        assert auth_service.check_permission("viewer", "read") is True

    def test_viewer_no_write(self):
        """viewer 无 write 权限"""
        assert auth_service.check_permission("viewer", "write") is False

    def test_unknown_user_denied(self):
        """未知用户对所有资源都应被拒绝"""
        assert auth_service.check_permission("unknown", "read") is False
        assert auth_service.check_permission("unknown", "write") is False

    def test_permission_boundary_exact_match(self):
        """权限边界：恰好拥有该权限应通过"""
        assert auth_service.check_permission("developer", "read") is True
        assert auth_service.check_permission("developer", "write") is True

    def test_permission_boundary_just_outside(self):
        """权限边界：恰好缺失该权限应拒绝"""
        # viewer 的权限集中没有 'write'
        assert "write" not in ["read"]
        assert auth_service.check_permission("viewer", "write") is False


# ============================================================================
# 3. 安全默认值测试
# ============================================================================

class TestSecurityDefaults:
    """安全默认值：拒绝优先"""

    def test_none_user_no_permission(self):
        """None 用户应无任何权限"""
        assert auth_service.check_permission(None, "read") is False

    def test_none_resource_denied(self):
        """None 资源对非 admin 用户应拒绝"""
        # admin 的 '*' 在 allowed 中，None 不在 allowed 中 → False
        # 但 admin 的 '*' 检查会先通过
        assert auth_service.check_permission("admin", None) is True
        # 非 admin 用户：None 不在权限列表中
        assert auth_service.check_permission("viewer", None) is False

    def test_valid_users_set_immutable_safety(self):
        """VALID_USERS 集合内容验证——确保测试覆盖的用户集完整"""
        assert auth_service.VALID_USERS == {"admin", "developer", "viewer"}
