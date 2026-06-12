#!/usr/bin/env python3
"""
guard.py — 守护器
劫财主理攻防，提供统一的权限校验与安全边界。
"""

import time
import uuid
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from functools import wraps


class Permission(Enum):
    """权限"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class SecurityContext:
    """安全上下文"""
    user_id: str
    roles: Set[str] = field(default_factory=set)
    permissions: Set[Permission] = field(default_factory=set)
    ip_address: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def has_permission(self, perm: Permission) -> bool:
        """检查是否拥有某权限"""
        if Permission.ADMIN in self.permissions:
            return True
        return perm in self.permissions

    def has_role(self, role: str) -> bool:
        """检查是否拥有某角色"""
        return role in self.roles


class Guard:
    """守护器 — 攻防之盾

    统一的权限校验、限流、审计。
    """

    def __init__(self):
        self._users: Dict[str, SecurityContext] = {}
        self._role_permissions: Dict[str, Set[Permission]] = {}
        self._rate_limits: Dict[str, List[float]] = {}
        self._audit_log: List[Dict[str, Any]] = []

    def register_role(self, role: str, permissions: Set[Permission]) -> None:
        """注册角色及其权限"""
        self._role_permissions[role] = permissions

    def create_context(
        self,
        user_id: str,
        roles: Optional[List[str]] = None,
        direct_permissions: Optional[List[Permission]] = None,
        ip: Optional[str] = None,
    ) -> SecurityContext:
        """创建安全上下文"""
        role_set = set(roles or [])
        perm_set = set(direct_permissions or [])

        for role in role_set:
            perm_set.update(self._role_permissions.get(role, set()))

        ctx = SecurityContext(
            user_id=user_id,
            roles=role_set,
            permissions=perm_set,
            ip_address=ip,
        )
        self._users[user_id] = ctx
        return ctx

    def check(self, ctx: SecurityContext, required: Permission) -> bool:
        """检查权限"""
        ok = ctx.has_permission(required)
        self._audit(ctx.user_id, "check", required.value, ok)
        return ok

    def enforce(self, required: Permission):
        """装饰器：强制权限检查"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                ctx = kwargs.get("ctx") or (args[0] if args else None)
                if not isinstance(ctx, SecurityContext):
                    raise PermissionError("SecurityContext required")
                if not self.check(ctx, required):
                    raise PermissionError(
                        f"Permission denied: {required.value} for {ctx.user_id}"
                    )
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def rate_limit(
        self,
        user_id: str,
        max_requests: int = 60,
        window_seconds: float = 60.0,
    ) -> bool:
        """限流检查"""
        now = time.time()
        timestamps = self._rate_limits.get(user_id, [])
        # 清理窗口外的记录
        timestamps = [t for t in timestamps if now - t < window_seconds]
        if len(timestamps) >= max_requests:
            self._rate_limits[user_id] = timestamps
            return False
        timestamps.append(now)
        self._rate_limits[user_id] = timestamps
        return True

    def _audit(self, user_id: str, action: str, resource: str, granted: bool) -> None:
        """审计日志"""
        self._audit_log.append({
            "timestamp": time.time(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "granted": granted,
        })

    def get_audit_log(self, user_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取审计日志"""
        logs = self._audit_log
        if user_id:
            logs = [l for l in logs if l["user_id"] == user_id]
        return logs[-limit:]
