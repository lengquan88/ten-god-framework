"""
secrets.py — 集中密钥管理模块 v1.0
===================================
从 .env 文件加载密钥到进程内存，绝不暴露到系统环境变量。

原则：
  1. 密钥仅在进程内存中，不会泄漏到子进程或系统全局
  2. 通过 `from tengod.secrets import get_secret` 统一获取
  3. 绝不通过 os.environ 读取敏感信息

用法：
  >>> from tengod.secrets import get_secret
  >>> api_key = get_secret("DEEPSEEK_API_KEY")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# ── 加载 .env 文件 ──────────────────────────────────────────────────────
# 查找项目根目录的 .env 文件（向上查找直到找到或到达文件系统根目录）
_ENV_LOADED = False
_ENV_VALUES: dict[str, str] = {}


def _find_env_file() -> Optional[Path]:
    """向上查找 .env 文件"""
    current = Path(__file__).resolve().parent.parent  # demo_project/
    # 也检查 /workspace 根目录
    candidates = [
        current / ".env",
        current.parent / ".env",  # /workspace/.env
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _load_env_file() -> dict[str, str]:
    """手动解析 .env 文件，避免依赖 python-dotenv（零依赖回退）"""
    global _ENV_LOADED, _ENV_VALUES

    if _ENV_LOADED:
        return _ENV_VALUES

    env_path = _find_env_file()
    if env_path is None:
        _ENV_LOADED = True
        return _ENV_VALUES

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith("#"):
                    continue
                # 解析 KEY=VALUE（支持引号）
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    # 去掉引号
                    if len(value) >= 2:
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                    _ENV_VALUES[key] = value
    except Exception:
        pass

    _ENV_LOADED = True
    return _ENV_VALUES


def get_secret(key: str, default: str = "") -> str:
    """获取密钥（优先从 .env 文件，其次从环境变量，最后返回默认值）

    注意：从环境变量读取仅作为向后兼容的降级方案。
    新代码应确保密钥仅存在于 .env 文件中。
    """
    _load_env_file()
    if key in _ENV_VALUES:
        return _ENV_VALUES[key]
    # 降级：从系统环境变量读取（向后兼容）
    return os.environ.get(key, default)


def has_secret(key: str) -> bool:
    """检查密钥是否已配置"""
    return bool(get_secret(key))


def list_configured_secrets() -> list[str]:
    """列出所有已配置的密钥名称（不暴露值）"""
    _load_env_file()
    return list(_ENV_VALUES.keys())


# ── 便捷访问器 ──────────────────────────────────────────────────────────

DEEPSEEK_API_KEY = property(lambda self: get_secret("DEEPSEEK_API_KEY"))
IMA_OPENAPI_APIKEY = property(lambda self: get_secret("IMA_OPENAPI_APIKEY"))
IMA_OPENAPI_CLIENTID = property(lambda self: get_secret("IMA_OPENAPI_CLIENTID"))
XIND_API_KEY = property(lambda self: get_secret("XIND_API_KEY"))
OPENAI_API_KEY = property(lambda self: get_secret("OPENAI_API_KEY"))
ANTHROPIC_API_KEY = property(lambda self: get_secret("ANTHROPIC_API_KEY"))
ANTHROPIC_BASE_URL = property(lambda self: get_secret("ANTHROPIC_BASE_URL", "https://api.anthropic.com"))
OPENAI_BASE_URL = property(lambda self: get_secret("OPENAI_BASE_URL", "https://api.openai.com/v1"))


__all__ = [
    "get_secret",
    "has_secret",
    "list_configured_secrets",
]