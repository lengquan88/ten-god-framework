#!/usr/bin/env python3
"""
adapter.py — 协议适配器
偏印主理桥接，提供统一的协议转换与外部系统对接。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ProtocolConverter(ABC):
    """协议转换器抽象基类"""

    @abstractmethod
    def from_source(self, data: Any) -> Any:
        """从源格式转换"""
        pass

    @abstractmethod
    def to_source(self, data: Any) -> Any:
        """转换到源格式"""
        pass


class Adapter:
    """适配器 — 桥接之桥

    将一种协议/格式转换为另一种。
    """

    def __init__(self, name: str, converter: ProtocolConverter):
        self._name = name
        self._converter = converter
        self._call_count = 0
        self._error_count = 0

    def convert(self, data: Any, direction: str = "from") -> Any:
        """执行转换"""
        self._call_count += 1
        try:
            if direction == "from":
                return self._converter.from_source(data)
            elif direction == "to":
                return self._converter.to_source(data)
            else:
                raise ValueError(f"Unknown direction: {direction}")
        except Exception:
            self._error_count += 1
            raise

    @property
    def name(self) -> str:
        return self._name

    def stats(self) -> Dict[str, int]:
        return {
            "calls": self._call_count,
            "errors": self._error_count,
        }


class DictToJsonConverter(ProtocolConverter):
    """字典 ↔ JSON 字符串转换器"""

    def from_source(self, data: str) -> Dict[str, Any]:
        import json

        return json.loads(data) if isinstance(data, str) else dict(data)

    def to_source(self, data: Dict[str, Any]) -> str:
        import json

        return json.dumps(data, ensure_ascii=False, indent=2)


class CamelToSnakeConverter(ProtocolConverter):
    """驼峰 ↔ 蛇形命名转换器"""

    def from_source(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {self._to_snake(k): v for k, v in data.items()}

    def to_source(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {self._to_camel(k): v for k, v in data.items()}

    @staticmethod
    def _to_snake(name: str) -> str:
        import re

        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    @staticmethod
    def _to_camel(name: str) -> str:
        parts = name.split("_")
        return parts[0] + "".join(p.title() for p in parts[1:])


class BridgeRegistry:
    """桥接注册中心

    统一管理所有适配器与转换器。
    """

    def __init__(self):
        self._adapters: Dict[str, Adapter] = {}
        self._converters: Dict[str, ProtocolConverter] = {}

    def register_adapter(self, adapter: Adapter) -> None:
        """注册适配器"""
        self._adapters[adapter.name] = adapter

    def register_converter(self, name: str, converter: ProtocolConverter) -> None:
        """注册转换器"""
        self._converters[name] = converter

    def get_adapter(self, name: str) -> Optional[Adapter]:
        """获取适配器"""
        return self._adapters.get(name)

    def get_converter(self, name: str) -> Optional[ProtocolConverter]:
        """获取转换器"""
        return self._converters.get(name)

    def list_adapters(self) -> List[str]:
        return list(self._adapters.keys())

    def list_converters(self) -> List[str]:
        return list(self._converters.keys())
