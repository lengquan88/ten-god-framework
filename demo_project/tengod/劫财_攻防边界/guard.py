#!/usr/bin/env python3
"""
guard.py — 守护器
劫财主理攻防，提供统一的权限校验与安全边界。
版本: 1.3.0
"""

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


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
    token_exp: Optional[float] = None

    def has_permission(self, perm: Permission) -> bool:
        """检查是否拥有某权限"""
        if Permission.ADMIN in self.permissions:
            return True
        return perm in self.permissions

    def has_role(self, role: str) -> bool:
        """检查是否拥有某角色"""
        return role in self.roles

    def is_expired(self) -> bool:
        """检查 token 是否过期"""
        if self.token_exp is None:
            return False
        return time.time() > self.token_exp

    @classmethod
    def from_token(
        cls, token: str, guard: "Guard", secret: str = "default-secret"
    ) -> Optional["SecurityContext"]:
        """从 JWT Token 构造安全上下文"""
        payload = guard.verify_token(token, secret)
        if payload is None:
            return None

        user_id = payload.get("user_id", "")
        roles = set(payload.get("roles", []))
        exp = payload.get("exp", 0)

        # 构建权限集合
        perm_set: Set[Permission] = set()
        for role in roles:
            perm_set.update(guard._role_permissions.get(role, set()))

        ctx = cls(
            user_id=user_id,
            roles=roles,
            permissions=perm_set,
            token_exp=exp,
        )
        guard._users[user_id] = ctx
        return ctx


class Guard:
    """守护器 — 攻防之盾

    统一的权限校验、限流、审计。
    版本: 1.3.0
    """

    VERSION = "1.3.0"

    def __init__(self, audit_log_path: str = "audit.log"):
        self._users: Dict[str, SecurityContext] = {}
        self._role_permissions: Dict[str, Set[Permission]] = {}
        self._rate_limits: Dict[str, List[float]] = {}
        self._audit_log: List[Dict[str, Any]] = []
        self._audit_log_path = audit_log_path
        self._audit_buffer: List[Dict[str, Any]] = []
        self._audit_buffer_lock = threading.Lock()
        self._token_bucket_lock = threading.Lock()
        self._token_buckets: Dict[str, Dict[str, Any]] = {}
        self._init_audit_db()

    def _init_audit_db(self) -> None:
        """初始化审计数据库"""
        if self._audit_log_path.endswith(".log"):
            # 文本日志模式
            return
        # SQLite 模式
        conn = sqlite3.connect(self._audit_log_path, isolation_level=None)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                user_id TEXT,
                action TEXT,
                resource TEXT,
                granted INTEGER
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp)"
        )
        conn.close()

    # ========== JWT Token 实现 ==========

    def _base64url_encode(self, data: bytes) -> str:
        """Base64url 编码"""
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    def _base64url_decode(self, data: str) -> bytes:
        """Base64url 解码"""
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)

    def generate_token(
        self,
        user_id: str,
        roles: List[str],
        secret: str = "default-secret",
        expires_in: int = 86400,
    ) -> str:
        """生成 JWT Token

        Args:
            user_id: 用户 ID
            roles: 用户角色列表
            secret: 密钥
            expires_in: 有效期（秒），默认 86400

        Returns:
            JWT token 字符串
        """
        now = time.time()
        exp = now + expires_in

        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = self._base64url_encode(
            json.dumps(header, separators=(",", ":")).encode()
        )
        payload = {
            "user_id": user_id,
            "roles": roles,
            "exp": exp,
            "iat": now,
            "jti": str(uuid.uuid4()),
        }
        payload_b64 = self._base64url_encode(
            json.dumps(payload, separators=(",", ":")).encode()
        )

        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
        signature_b64 = self._base64url_encode(signature)

        return f"{message}.{signature_b64}"

    def verify_token(
        self, token: str, secret: str = "default-secret"
    ) -> Optional[Dict]:
        """验证 JWT Token

        Args:
            token: JWT token 字符串
            secret: 密钥

        Returns:
            payload dict 或 None（验证失败）
        """
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, signature_b64 = parts

            # 验证签名
            message = f"{header_b64}.{payload_b64}"
            expected_sig = hmac.new(
                secret.encode(), message.encode(), hashlib.sha256
            ).digest()
            expected_sig_b64 = self._base64url_encode(expected_sig)

            if not hmac.compare_digest(signature_b64, expected_sig_b64):
                return None

            # 解析 payload
            payload_data = self._base64url_decode(payload_b64)
            payload = json.loads(payload_data)

            # 检查过期
            if "exp" in payload and time.time() > payload["exp"]:
                return None

            return payload

        except (ValueError, json.JSONDecodeError, KeyError):
            return None

    # ========== 令牌桶限流 ==========

    def rate_limit_token_bucket(
        self, user_id: str, capacity: int = 60, refill_rate: float = 1.0
    ) -> Tuple[bool, Dict]:
        """令牌桶限流

        Args:
            user_id: 用户 ID
            capacity: 令牌桶容量（最大突发）
            refill_rate: 每秒补充令牌数

        Returns:
            (allowed, info): 是否允许请求，以及限流信息
        """
        with self._token_bucket_lock:
            now = time.time()
            bucket = self._token_buckets.get(user_id)

            if bucket is None:
                # 初始化桶
                bucket = {
                    "tokens": float(capacity),
                    "last_refill": now,
                    "capacity": capacity,
                    "refill_rate": refill_rate,
                }
                self._token_buckets[user_id] = bucket

            # 补充令牌
            elapsed = now - bucket["last_refill"]
            bucket["tokens"] = min(
                bucket["capacity"], bucket["tokens"] + elapsed * bucket["refill_rate"]
            )
            bucket["last_refill"] = now

            # 尝试消费令牌
            if bucket["tokens"] >= 1.0:
                bucket["tokens"] -= 1.0
                allowed = True
            else:
                allowed = False

            # 计算恢复时间
            if allowed:
                reset_in = 0.0
            else:
                reset_in = (1.0 - bucket["tokens"]) / bucket["refill_rate"]

            return (
                allowed,
                {
                    "remaining": int(bucket["tokens"]),
                    "capacity": bucket["capacity"],
                    "reset_in": reset_in,
                    "allowed": allowed,
                },
            )

    # ========== 守卫模式 ==========

    def enter_gate(self, user_id: str, permission: Permission) -> bool:
        """守卫模式：原子性检查权限 + 扣减令牌桶

        Args:
            user_id: 用户 ID
            permission: 所需权限

        Returns:
            是否允许通过
        """
        ctx = self._users.get(user_id)
        if ctx is None:
            return False

        if not ctx.has_permission(permission):
            self._audit(user_id, "gate_denied", permission.value, False)
            return False

        # 原子性扣减令牌桶
        allowed, info = self.rate_limit_token_bucket(user_id)
        if not allowed:
            self._audit(user_id, "gate_rate_limited", permission.value, False)
            return False

        self._audit(user_id, "gate_passed", permission.value, True)
        return True

    # ========== 审计日志持久化 ==========

    def _audit(self, user_id: str, action: str, resource: str, granted: bool) -> None:
        """审计日志"""
        entry = {
            "timestamp": time.time(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "granted": granted,
        }

        # 写入内存
        self._audit_log.append(entry)

        # 缓冲批量写入
        with self._audit_buffer_lock:
            self._audit_buffer.append(entry)
            if len(self._audit_buffer) >= 10:
                self._audit_log_persist()

    def _audit_log_persist(self, limit: int = 1000) -> None:
        """将审计日志追加写入文件"""
        if not self._audit_buffer:
            return

        with self._audit_buffer_lock:
            entries = self._audit_buffer[:limit]
            self._audit_buffer = self._audit_buffer[limit:]

        if self._audit_log_path.endswith(".log"):
            # 文本日志模式
            try:
                with open(self._audit_log_path, "a", encoding="utf-8") as f:
                    for entry in entries:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except IOError:
                pass
        else:
            # SQLite 模式
            try:
                conn = sqlite3.connect(self._audit_log_path, isolation_level=None)
                conn.executemany(
                    "INSERT INTO audit_log (timestamp, user_id, action, resource, granted) VALUES (?, ?, ?, ?, ?)",
                    [
                        (
                            e["timestamp"],
                            e["user_id"],
                            e["action"],
                            e["resource"],
                            1 if e["granted"] else 0,
                        )
                        for e in entries
                    ],
                )
                conn.close()
            except sqlite3.Error:
                pass

    def get_audit_log(
        self, user_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取审计日志

        优先从文件读取，合并内存日志
        """
        # 刷新缓冲
        self._audit_log_persist()

        all_logs: List[Dict[str, Any]] = []

        if self._audit_log_path.endswith(".log"):
            # 文本日志
            try:
                if os.path.exists(self._audit_log_path):
                    with open(self._audit_log_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    all_logs.append(json.loads(line))
                                except json.JSONDecodeError:
                                    pass
            except IOError:
                pass
        else:
            # SQLite
            try:
                conn = sqlite3.connect(self._audit_log_path, isolation_level=None)
                cursor = conn.execute(
                    "SELECT timestamp, user_id, action, resource, granted FROM audit_log ORDER BY timestamp DESC LIMIT ?",
                    (limit * 10,),
                )
                for row in cursor:
                    all_logs.append(
                        {
                            "timestamp": row[0],
                            "user_id": row[1],
                            "action": row[2],
                            "resource": row[3],
                            "granted": bool(row[4]),
                        }
                    )
                conn.close()
            except sqlite3.Error:
                pass

        # 合并内存日志
        all_logs.extend(self._audit_log)

        # 过滤
        if user_id:
            all_logs = [l for l in all_logs if l["user_id"] == user_id]

        # 按时间排序并限制
        all_logs.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_logs[:limit]

    # ========== 原有接口保持不变 ==========

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
        """限流检查（原有滑动窗口实现）"""
        now = time.time()
        timestamps = self._rate_limits.get(user_id, [])
        timestamps = [t for t in timestamps if now - t < window_seconds]
        if len(timestamps) >= max_requests:
            self._rate_limits[user_id] = timestamps
            return False
        timestamps.append(now)
        self._rate_limits[user_id] = timestamps
        return True
