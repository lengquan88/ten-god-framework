#!/usr/bin/env python3
"""
auth.py — 用户认证与权限管理 v1.0.0

阶段十三：用户系统与权限

功能：
  1. 密码哈希（PBKDF2-HMAC-SHA256，无需外部依赖）
  2. JWT 令牌签发与验证（access_token + refresh_token）
  3. 角色权限模型（admin/user/guest）
  4. API 配额管理（按用户日限）
  5. 认证依赖注入（FastAPI Depends）
"""

from __future__ import annotations
import os
import hmac
import hashlib
import base64
import json
import time
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


# ============================================================================
# 配置
# ============================================================================

# JWT 密钥（从环境变量读取，默认值仅用于开发）
JWT_SECRET = os.environ.get("TENGOD_JWT_SECRET", "tengod_dev_secret_change_in_production_2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24       # access token 有效期 24 小时
REFRESH_TOKEN_EXPIRE_DAYS = 7                # refresh token 有效期 7 天

# 角色权限定义
ROLE_PERMISSIONS = {
    "admin": {
        "name": "管理员",
        "permissions": ["*"],  # 所有权限
        "quota_daily": 10000,
    },
    "user": {
        "name": "普通用户",
        "permissions": [
            "bazi:calc", "bazi:full", "bazi:report",
            "ziwei:calc", "liuyao:shake", "qimen:calc",
            "name:analyze", "marriage:analyze",
            "knowledge:search", "knowledge:wuxing",
            "chat:send", "chat:report",
            "ai:interpret", "ai:interpret:stream",
            "case:read", "case:write", "case:delete",
            "records:read", "records:write", "records:delete",
            "webhook:read", "webhook:write",
            "plugin:read",
            "data:read", "data:write", "data:admin",  # v2.12: 数据管理权限
        ],
        "quota_daily": 100,
    },
    "guest": {
        "name": "访客",
        "permissions": ["bazi:calc", "knowledge:search", "case:read", "plugin:read"],
        "quota_daily": 10,
    },
}


# ============================================================================
# 密码哈希（PBKDF2-HMAC-SHA256）
# ============================================================================

class PasswordHasher:
    """密码哈希器（使用 PBKDF2-HMAC-SHA256，兼容 Python 标准库）"""

    ITERATIONS = 100000
    SALT_LENGTH = 16
    KEY_LENGTH = 32

    @classmethod
    def hash(cls, password: str) -> str:
        """哈希密码"""
        salt = secrets.token_bytes(cls.SALT_LENGTH)
        key = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt,
            cls.ITERATIONS, cls.KEY_LENGTH
        )
        # 格式: pbkdf2_sha256$iterations$salt_base64$key_base64
        return f"pbkdf2_sha256${cls.ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(key).decode()}"

    @classmethod
    def verify(cls, password: str, hashed: str) -> bool:
        """验证密码"""
        try:
            parts = hashed.split("$")
            if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
                return False
            iterations = int(parts[1])
            salt = base64.b64decode(parts[2])
            stored_key = base64.b64decode(parts[3])
            key = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt,
                iterations, len(stored_key)
            )
            return hmac.compare_digest(key, stored_key)
        except Exception:
            return False


# ============================================================================
# JWT 令牌
# ============================================================================

class JWTManager:
    """JWT 令牌管理器"""

    @staticmethod
    def _b64encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64decode(data: str) -> bytes:
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)

    @classmethod
    def _sign(cls, message: str) -> str:
        return hmac.new(
            JWT_SECRET.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    @classmethod
    def create_token(cls, user_id: int, username: str, role: str,
                     token_type: str = "access",
                     expires_in: Optional[int] = None) -> str:
        """创建 JWT 令牌"""
        now = datetime.now(timezone.utc)
        if expires_in is None:
            if token_type == "access":
                expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60
            else:
                expires_in = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600

        payload = {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "type": token_type,
            "iat": int(now.timestamp()),
            "exp": int(now.timestamp()) + expires_in,
        }

        header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
        header_b64 = cls._b64encode(json.dumps(header, separators=(",", ":")).encode())
        payload_b64 = cls._b64encode(json.dumps(payload, separators=(",", ":")).encode())
        signing_input = f"{header_b64}.{payload_b64}"
        signature = cls._sign(signing_input)

        return f"{signing_input}.{signature}"

    @classmethod
    def verify_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """验证 JWT 令牌，返回 payload 或 None"""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, signature = parts
            signing_input = f"{header_b64}.{payload_b64}"

            # 验证签名
            expected_sig = cls._sign(signing_input)
            if not hmac.compare_digest(signature, expected_sig):
                return None

            # 解码 payload
            payload = json.loads(cls._b64decode(payload_b64))

            # 检查过期时间
            if payload.get("exp", 0) < int(time.time()):
                return None

            return payload
        except Exception:
            return None

    @classmethod
    def create_access_token(cls, user_id: int, username: str, role: str) -> str:
        return cls.create_token(user_id, username, role, "access")

    @classmethod
    def create_refresh_token(cls, user_id: int, username: str, role: str) -> str:
        return cls.create_token(user_id, username, role, "refresh")


# ============================================================================
# 当前用户上下文
# ============================================================================

@dataclass
class CurrentUser:
    """当前认证用户"""
    id: int
    username: str
    role: str
    permissions: list
    is_authenticated: bool = True

    def has_permission(self, perm: str) -> bool:
        """检查是否拥有某权限"""
        if "*" in self.permissions:
            return True
        return perm in self.permissions

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


# ============================================================================
# 认证依赖
# ============================================================================

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> CurrentUser:
    """
    FastAPI 依赖：从 Bearer token 获取当前用户
    用法: @app.get("/api/xxx", dependencies=[Depends(get_current_user)])
    """
    if credentials is None or credentials.scheme != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = JWTManager.verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌类型错误",
        )

    role = payload.get("role", "guest")
    perms = ROLE_PERMISSIONS.get(role, {}).get("permissions", [])

    return CurrentUser(
        id=int(payload["sub"]),
        username=payload["username"],
        role=role,
        permissions=perms,
    )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> CurrentUser:
    """可选认证：未登录返回 guest 用户"""
    if credentials is None or credentials.scheme != "Bearer":
        return CurrentUser(
            id=0, username="guest", role="guest",
            permissions=ROLE_PERMISSIONS["guest"]["permissions"],
        )

    payload = JWTManager.verify_token(credentials.credentials)
    if payload is None:
        return CurrentUser(
            id=0, username="guest", role="guest",
            permissions=ROLE_PERMISSIONS["guest"]["permissions"],
        )

    role = payload.get("role", "guest")
    perms = ROLE_PERMISSIONS.get(role, {}).get("permissions", [])

    return CurrentUser(
        id=int(payload["sub"]),
        username=payload["username"],
        role=role,
        permissions=perms,
    )


def require_permission(perm: str):
    """
    权限检查依赖工厂
    用法: @app.post("/api/xxx", dependencies=[Depends(require_permission("bazi:calc"))])
    """
    async def check_perm(user: CurrentUser = None):
        if user is None:
            # 尝试从 request 获取
            raise HTTPException(status_code=401, detail="未认证")
        if not user.has_permission(perm):
            raise HTTPException(
                status_code=403,
                detail=f"权限不足，需要: {perm}",
            )
        return user
    return check_perm


def require_role(*roles: str):
    """
    角色检查依赖工厂
    用法: @app.get("/api/admin/xxx", dependencies=[Depends(require_role("admin"))])
    """
    async def check_role(user: CurrentUser = None):
        if user is None:
            raise HTTPException(status_code=401, detail="未认证")
        if user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"角色不足，需要: {', '.join(roles)}",
            )
        return user
    return check_role


# ============================================================================
# API 配额管理
# ============================================================================

class QuotaManager:
    """API 配额管理器（内存版，生产环境可用 Redis）"""

    _usage: Dict[str, Dict[str, int]] = {}  # {user_id: {date: count}}

    @classmethod
    def _today(cls) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    @classmethod
    def check(cls, user_id: int, quota: int) -> Tuple[bool, int, int]:
        """
        检查配额
        返回: (是否允许, 已用次数, 剩余次数)
        """
        today = cls._today()
        key = str(user_id)

        if key not in cls._usage:
            cls._usage[key] = {}

        # 清理旧日期
        cls._usage[key] = {d: c for d, c in cls._usage[key].items() if d >= today}

        used = cls._usage[key].get(today, 0)
        remaining = max(0, quota - used)

        if used >= quota:
            return False, used, 0
        return True, used, remaining

    @classmethod
    def consume(cls, user_id: int):
        """消耗一次配额"""
        today = cls._today()
        key = str(user_id)
        if key not in cls._usage:
            cls._usage[key] = {}
        cls._usage[key][today] = cls._usage[key].get(today, 0) + 1

    @classmethod
    def get_usage(cls, user_id: int) -> Dict[str, int]:
        """获取用户使用情况"""
        return cls._usage.get(str(user_id), {})

    @classmethod
    def reset(cls, user_id: int):
        """重置用户配额"""
        cls._usage.pop(str(user_id), None)


# ============================================================================
# 认证中间件（从 Authorization header 提取用户）
# ============================================================================

async def auth_middleware(request: Request, call_next):
    """
    认证中间件：解析 JWT 并将用户信息附加到 request.state
    不强制认证，只解析；具体权限检查在端点层完成
    """
    auth_header = request.headers.get("Authorization", "")
    request.state.current_user = None

    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = JWTManager.verify_token(token)
        if payload and payload.get("type") == "access":
            role = payload.get("role", "guest")
            perms = ROLE_PERMISSIONS.get(role, {}).get("permissions", [])
            request.state.current_user = CurrentUser(
                id=int(payload["sub"]),
                username=payload["username"],
                role=role,
                permissions=perms,
            )

    response = await call_next(request)
    return response


def authorize(request: Request, perm: str, consume_quota: bool = True) -> CurrentUser:
    """
    端点内权限检查 + 配额消耗（支持未登录 guest）

    用法:
        user = authorize(request, "bazi:calc")

    行为:
      - 未登录 → 视为 guest，检查 guest 是否拥有该权限
      - 已登录 → 检查用户权限
      - 权限不足 → 抛 401（未登录）或 403（已登录但权限不够）
      - 配额耗尽 → 抛 429
      - 通过 → 返回 CurrentUser 并消耗一次配额
    """
    user = getattr(request.state, "current_user", None)
    if user is None or not user.is_authenticated:
        user = CurrentUser(
            id=0, username="guest", role="guest",
            permissions=ROLE_PERMISSIONS["guest"]["permissions"],
            is_authenticated=False,
        )

    if not user.has_permission(perm):
        if user.is_authenticated:
            raise HTTPException(
                status_code=403,
                detail=f"权限不足，需要: {perm}",
            )
        else:
            raise HTTPException(
                status_code=401,
                detail=f"请登录后使用此功能（需要权限: {perm}）",
            )

    if consume_quota:
        quota = ROLE_PERMISSIONS.get(user.role, {}).get("quota_daily", 10)
        allowed, used, _ = QuotaManager.check(user.id, quota)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"今日配额已用尽（{used}/{quota}），请明日再试或升级账号",
            )
        QuotaManager.consume(user.id)

    return user


# ============================================================================
# 便捷函数
# ============================================================================

def create_token_pair(user_id: int, username: str, role: str) -> Dict[str, Any]:
    """创建 access + refresh token 对"""
    return {
        "access_token": JWTManager.create_access_token(user_id, username, role),
        "refresh_token": JWTManager.create_refresh_token(user_id, username, role),
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# ============================================================================
# v2.12: 数据库用户集成
# ============================================================================

def sync_user_to_db(username: str, password: str, role: str = "user") -> Dict[str, Any]:
    """同步用户到数据库

    持久化用户到数据库 tables。
    """
    from tengod.database import is_persistent, get_db

    user_id = hash(username) % 100000  # 简单 ID 生成

    # 持久化
    if is_persistent():
        db = get_db()
        existing = db.get_user(username=username)
        if not existing:
            api_key = _generate_api_key()
            db.create_user({
                "username": username,
                "api_key": api_key,
                "role": role,
                "quota_limit": ROLE_PERMISSIONS.get(role, {}).get("quota_daily", 100),
            })

    return {"user_id": user_id, "username": username, "role": role}


def load_users_from_db() -> int:
    """从数据库加载用户到内存"""
    from tengod.database import is_persistent
    if not is_persistent():
        return 0

    # 由于用户数据存储在内存中，这里做种子用户初始化
    # 检查是否已有用户
    count = 0
    import os
    admin_pass = os.environ.get("ADMIN_PASSWORD", "admin123")
    sync_user_to_db("admin", admin_pass, "admin")
    count += 1

    return count


def _generate_api_key(length: int = 32) -> str:
    """生成 API Key"""
    import secrets
    import hashlib
    raw = secrets.token_bytes(length)
    return hashlib.sha256(raw).hexdigest()[:length]


def check_db_quota(username: str) -> Tuple[bool, int, int]:
    """检查数据库配额"""
    from tengod.database import is_persistent, get_db
    if not is_persistent():
        return True, 0, 0
    return get_db().check_quota(username)


def update_db_quota(username: str, delta: int = 1) -> bool:
    """更新数据库配额"""
    from tengod.database import is_persistent, get_db
    if not is_persistent():
        return True
    return get_db().update_quota(username, delta)


__all__ = [
    "PasswordHasher", "JWTManager", "CurrentUser",
    "get_current_user", "get_current_user_optional",
    "require_permission", "require_role",
    "QuotaManager", "auth_middleware", "authorize",
    "create_token_pair", "ROLE_PERMISSIONS",
    "ACCESS_TOKEN_EXPIRE_MINUTES", "REFRESH_TOKEN_EXPIRE_DAYS",
    "sync_user_to_db", "load_users_from_db",  # v2.12
    "check_db_quota", "update_db_quota",  # v2.12
]
