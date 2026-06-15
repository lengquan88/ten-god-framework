#!/usr/bin/env python3
"""auth_service.py — 认证服务 (劫财·攻防边界)"""

VALID_USERS = {"admin", "developer", "viewer"}


def authenticate(username: str) -> bool:
    """验证用户身份"""
    return username in VALID_USERS


def check_permission(username: str, resource: str) -> bool:
    """检查资源访问权限"""
    permissions = {
        "admin": ["*"],
        "developer": ["read", "write"],
        "viewer": ["read"],
    }
    allowed = permissions.get(username, [])
    return "*" in allowed or resource in allowed
