#!/usr/bin/env python3
"""
比肩_架构协同 — 核心编排/入口点
比肩主理协同，承担系统的核心编排与组件注册职责。
"""

from .registry import ComponentRegistry, ComponentState, LifecycleManager, component, get_registry

__all__ = ["ComponentRegistry", "ComponentState", "LifecycleManager", "component", "get_registry"]
__version__ = "1.4.0"
