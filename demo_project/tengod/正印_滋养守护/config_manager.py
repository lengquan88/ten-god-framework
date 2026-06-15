#!/usr/bin/env python3
"""
config_manager.py — 配置管理器
正印主理滋养，提供统一的配置加载与环境管理。
版本：1.5.0
"""

import os
import json
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
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

    def load_from_file(self, file_path: str) -> Dict[str, Any]:
        """从文件加载配置，支持 JSON/YAML/TOML"""
        import os
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"配置文件不存在：{file_path}")
        ext = os.path.splitext(file_path)[1].lower()
        with open(file_path, "r", encoding="utf-8") as f:
            if ext in (".yaml", ".yml"):
                try:
                    import yaml
                    data = yaml.safe_load(f)
                except ImportError:
                    # 纯 Python YAML 解析（简化版：仅支持 key: value）
                    data = self._parse_simple_yaml(f)
            elif ext == ".toml":
                data = self._parse_toml(f.read())
            elif ext == ".json":
                import json
                data = json.load(f)
            elif ext == ".ini":
                data = self._parse_ini(f)
            else:
                raise ValueError(f"不支持的配置文件格式：{ext}")
        if isinstance(data, dict):
            for k, v in data.items():
                self.set(k, v, source=file_path)
        return data

    def _parse_simple_yaml(self, f) -> Dict[str, Any]:
        """纯 Python 简单 YAML 解析（仅支持 key: value）"""
        result = {}
        for line in f:
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue
            if ": " in line:
                k, v = line.split(": ", 1)
                result[k.strip()] = v.strip().strip('"').strip("'")
            elif line.endswith(":"):
                result[line[:-1].strip()] = True
        return result

    def _parse_toml(self, content: str) -> Dict[str, Any]:
        """纯 Python TOML 解析（简化版：仅支持 key = value）"""
        result = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("["):
                continue
            if " = " in line:
                k, v = line.split(" = ", 1)
                v = v.strip().strip('"').strip("'")
                if v.lower() == "true":
                    v = True
                elif v.lower() == "false":
                    v = False
                elif v.isdigit():
                    v = int(v)
                result[k.strip()] = v
        return result

    def _parse_ini(self, f) -> Dict[str, Any]:
        """纯 Python INI 解析"""
        import configparser
        cp = configparser.ConfigParser()
        cp.read_file(f)
        return {s: dict(cp.items(s)) for s in cp.sections()}

    def watch_file(self, file_path: str, interval: float = 2.0) -> "ConfigWatcher":
        """监听配置文件变化，自动热加载（返回 watcher，需手动启动线程）"""
        return ConfigWatcher(self, file_path, interval)

    def validate_schema(self, data: Dict[str, Any],
                       schema: Dict[str, Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Schema 验证。
        schema 形如：{"key": {"type": str, "required": True, "default": None}}
        返回 (passed, errors)
        """
        errors = []
        for key, spec in schema.items():
            if spec.get("required", False) and key not in data:
                if "default" in spec:
                    data[key] = spec["default"]
                else:
                    errors.append(f"缺少必需字段：{key}")
            if key in data:
                expected_type = spec.get("type")
                if expected_type and not isinstance(data[key], expected_type):
                    errors.append(
                        f"字段类型错误 {key}: expected {expected_type.__name__}, "
                        f"got {type(data[key]).__name__}"
                    )
        return len(errors) == 0, errors

    def set(self, key: str, value: Any, source: Any = None) -> None:
        """直接设置（最高优先级）"""
        src = ConfigSource.FILE if source else ConfigSource.OVERRIDE
        self._configs[key] = Config(
            key=key,
            value=value,
            source=src,
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


__all__ = ["ConfigManager", "ConfigWatcher", "ConfigSource", "Config"]


class ConfigWatcher:
    """配置文件热加载监视器"""

    def __init__(self, config: "ConfigManager", file_path: str, interval: float = 2.0):
        import threading, time
        self._config = config
        self._file_path = file_path
        self._interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0

    def start(self) -> None:
        import threading
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self) -> None:
        import time, os
        while self._running:
            time.sleep(self._interval)
            if not os.path.exists(self._file_path):
                continue
            mtime = os.path.getmtime(self._file_path)
            if mtime != self._mtime:
                self._mtime = mtime
                try:
                    self._config.load_from_file(self._file_path)
                    print(f"[ConfigWatcher] 配置已热加载：{self._file_path}")
                except Exception as e:
                    print(f"[ConfigWatcher] 热加载失败：{e}")
