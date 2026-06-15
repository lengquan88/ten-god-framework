#!/usr/bin/env python3
"""
偏印_桥接通变 — 桥接适配/协议转换
偏印主理桥接，承担系统的协议转换与外部适配职责。
"""

from .adapter import (
    Adapter,
    BridgeRegistry,
    CamelToSnakeConverter,
    DictToJsonConverter,
    ProtocolConverter,
)

__all__ = [
    "Adapter",
    "ProtocolConverter",
    "BridgeRegistry",
    "DictToJsonConverter",
    "CamelToSnakeConverter",
]
__version__ = "1.0.0"
