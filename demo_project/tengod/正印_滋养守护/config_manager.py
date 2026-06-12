#!/usr/bin/env python3
"""
config_manager.py — 配置管理器
正印主理滋养，提供统一的配置加载与环境管理。
"""

import os
import json
from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


class ConfigSource(Enum):
    """配置来源"""
    ENV = "env"
    FILE = "file"
    DEFAULT = "default"
    OVERRIDE = "override"


@dataclass
class Config:
    """配置项"""
    key: str
    value: Any
    source: ConfigSource = ConfigSource.DEFAULT
    description: str = ""


class ConfigManager:
    """配置管理器 — 滋养之源

    统一管理多来源配置，支持默认值、环境变量、文件覆盖。
    """

    def __init__(self, env_prefix: str = "TENGOD_"):
        self._configs: Dict[str, Config] = {}
        self._env_prefix = env_prefix
        self._defaults: Dict[str, Any] = {}

    def set_default(self, key: str, value: Any, description: str = "") -> None:
        """设置默认值"""
        self._defaults[key] = value
        if key not in self._configs:
            self._configs[key] = Config(
                key=key,
                value=value,
                source=ConfigSource.DEFAULT,
                description=description,
            )

    def load_from_env(self, key: str) -> bool:
        """从环境变量加载"""
        env_key = f"{self._env_prefix}{key.upper()}"
        if env_key in os.environ:
            value = os.environ[env_key]
            # 尝试类型转换
            value = self._auto_cast(value)
            self._configs[key] = Config(
                key=key,
                value=value,
                source=ConfigSource.ENV,
            )
            return True
        return False

    def load_from_file(self, file_path: str) -> int:
        """从 JSON 文件加载"""
        if not os.path.exists(file_path):
            return 0
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            count = 0
            for key, value in data.items():
                self._configs[key] = Config(
                    key=key,
                    value=value,
                    source=ConfigSource.FILE,
                )
                count += 1
            return count
        except (json.JSONDecodeError, IOError):
            return 0

    def set(self, key: str, value: Any) -> None:
        """直接设置（最高优先级）"""
        self._configs[key] = Config(
            key=key,
            value=value,
            source=ConfigSource.OVERRIDE,
        )

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置"""
        if key in self._configs:
            return self._configs[key].value
        return default

    def has(self, key: str) -> bool:
        """检查配置是否存在"""
        return key in self._configs

    def get_info(self, key: str) -> Optional[Config]:
        """获取配置详情"""
        return self._configs.get(key)

    def list_all(self) -> Dict[str, Any]:
        """列出所有配置"""
        return {k: c.value for k, c in self._configs.items()}

    def list_with_source(self) -> Dict[str, Dict[str, Any]]:
        """列出所有配置及其来源"""
        return {
            k: {
                "value": c.value,
                "source": c.source.value,
                "description": c.description,
            }
            for k, c in self._configs.items()
        }

    @staticmethod
    def _auto_cast(value: str) -> Any:
        """自动类型转换"""
        # 布尔
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        # 数字
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        # JSON
        if value.startswith(("[", "{")):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return value
