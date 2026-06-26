"""
config_manager.py — 统一配置管理器 v2.8
=======================================
优先级：环境变量 > YAML 文件 > 默认值
支持：热重载、配置校验、敏感信息保护
"""

from __future__ import annotations

import os
import threading
from typing import Any, Dict, Optional

from .config_schema import (
    TengodConfig, validate_and_load, load_from_yaml,
    generate_example_yaml, _PYDANTIC_V2,
)

_CONFIG_FILE_ENV = "TENGOD_CONFIG_FILE"
_CONFIG_LOCK = threading.Lock()
_CONFIG_INSTANCE: Optional[TengodConfig] = None
_CONFIG_PATH: Optional[str] = None
_CONFIG_MTIME: float = 0
_CONFIG_HOT_RELOAD: bool = False
_CONFIG_HOT_RELOAD_INTERVAL: int = 5


def _env_override(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """环境变量覆盖配置"""
    # 确保是普通 dict（递归处理嵌套 Pydantic model）
    def _to_dict(obj):
        if isinstance(obj, dict):
            return {k: _to_dict(v) for k, v in obj.items()}
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        if hasattr(obj, '__dict__') and not isinstance(obj, (str, int, float, bool, list, tuple)):
            return {k: _to_dict(v) for k, v in obj.__dict__.items()
                    if not k.startswith('_')}
        return obj

    config_dict = _to_dict(config_dict)

    env_map = {
        "TENGOD_NAME": ("name", str),
        "TENGOD_HOST": ("server", "host", str),
        "TENGOD_PORT": ("server", "port", int),
        "TENGOD_WORKERS": ("server", "workers", int),
        "TENGOD_CORS": ("server", "cors_origins", lambda x: [s.strip() for s in x.split(",")]),
        "TENGOD_LOG_LEVEL": ("monitoring", "log_level", str),
        "TENGOD_LOG_FORMAT": ("monitoring", "log_format", str),
        "TENGOD_DB_URL": ("database", "url", str),
        "TENGOD_LLM_PROVIDER": ("llm", "provider", str),
        "TENGOD_LLM_API_KEY": ("llm", "api_key", str),
        "TENGOD_LLM_MODEL": ("llm", "model", str),
        "TENGOD_LLM_BASE": ("llm", "api_base", str),
        "TENGOD_JWT_SECRET": ("security", "jwt_secret", str),
        "TENGOD_RATE_LIMIT": ("security", "rate_limit_capacity", int),
        "TENGOD_PROMETHEUS": ("monitoring", "prometheus_enabled", lambda x: x.lower() == "true"),
    }

    for env_var, path in env_map.items():
        val = os.environ.get(env_var)
        if val is None:
            continue

        converter = path[-1] if callable(path[-1]) else None
        keys = path[:-1] if converter else path

        try:
            if converter:
                val = converter(val)
            elif isinstance(path[-1], type):
                val = path[-1](val)
        except (ValueError, TypeError):
            continue

        if len(keys) == 1:
            config_dict[keys[0]] = val
        elif len(keys) == 2:
            if keys[0] not in config_dict:
                config_dict[keys[0]] = {}
            config_dict[keys[0]][keys[1]] = val

    return config_dict


def load_config(
    config_path: Optional[str] = None,
    auto_env: bool = True,
    hot_reload: bool = False,
) -> TengodConfig:
    """加载统一配置

    Args:
        config_path: YAML 配置文件路径，None 则检查环境变量 TENGOD_CONFIG_FILE
        auto_env: 是否自动从环境变量覆盖
        hot_reload: 是否启用热重载

    Returns:
        TengodConfig 实例
    """
    global _CONFIG_INSTANCE, _CONFIG_PATH, _CONFIG_MTIME, _CONFIG_HOT_RELOAD

    with _CONFIG_LOCK:
        _CONFIG_HOT_RELOAD = hot_reload

        # 确定配置文件路径
        if config_path is None:
            config_path = os.environ.get(_CONFIG_FILE_ENV, "")
        if not config_path:
            config_path = os.environ.get("TENGOD_CONFIG", "tengod_config.yaml")

        _CONFIG_PATH = config_path

        # 加载配置
        if os.path.exists(config_path):
            config_dict = load_from_yaml(config_path)
            _CONFIG_MTIME = os.path.getmtime(config_path)
        else:
            config_dict = validate_and_load({"name": "tengod"})
            _CONFIG_MTIME = 0

        # 环境变量覆盖
        if auto_env:
            config_dict = _env_override(config_dict)

        _CONFIG_INSTANCE = TengodConfig(**config_dict) if _PYDANTIC_V2 else TengodConfig(**config_dict)

    return _CONFIG_INSTANCE


def get_config() -> TengodConfig:
    """获取当前配置实例（首次调用自动加载）"""
    global _CONFIG_INSTANCE

    if _CONFIG_INSTANCE is None:
        return load_config()

    # 热重载检查
    if _CONFIG_HOT_RELOAD and _CONFIG_PATH and os.path.exists(_CONFIG_PATH):
        mtime = os.path.getmtime(_CONFIG_PATH)
        if mtime > _CONFIG_MTIME:
            return load_config(_CONFIG_PATH, hot_reload=True)

    return _CONFIG_INSTANCE


def reload_config() -> TengodConfig:
    """强制重新加载配置"""
    return load_config(_CONFIG_PATH, hot_reload=_CONFIG_HOT_RELOAD)


def get_config_dict() -> Dict[str, Any]:
    """获取配置字典（适合序列化）"""
    cfg = get_config()
    if _PYDANTIC_V2:
        return cfg.model_dump()
    return cfg.__dict__


def get_server_config() -> Dict[str, Any]:
    """获取服务器配置"""
    cfg = get_config()
    s = cfg.server
    if _PYDANTIC_V2:
        return s.model_dump()
    return {"host": s.host, "port": s.port, "mode": s.mode, "workers": s.workers, "cors_origins": s.cors_origins}


def get_llm_config() -> Dict[str, Any]:
    """获取 LLM 配置（敏感信息已脱敏）"""
    cfg = get_config()
    llm = cfg.llm
    if _PYDANTIC_V2:
        d = llm.model_dump()
    else:
        d = {"provider": llm.provider, "api_key": llm.api_key, "api_base": llm.api_base,
             "model": llm.model, "temperature": llm.temperature, "max_tokens": llm.max_tokens,
             "timeout": llm.timeout, "max_retries": llm.max_retries, "retry_backoff": llm.retry_backoff}
    # 脱敏
    if d.get("api_key") and len(d["api_key"]) > 8:
        d["api_key"] = d["api_key"][:4] + "****" + d["api_key"][-4:]
    return d


def init_config(config_path: Optional[str] = None, hot_reload: bool = False) -> TengodConfig:
    """初始化配置（应用启动时调用）"""
    cfg = load_config(config_path, hot_reload=hot_reload)
    return cfg


__all__ = [
    "load_config",
    "get_config",
    "reload_config",
    "get_config_dict",
    "get_server_config",
    "get_llm_config",
    "init_config",
    "generate_example_yaml",
]