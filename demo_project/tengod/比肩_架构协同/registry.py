#!/usr/bin/env python3
"""
registry.py — 组件注册中心
比肩主理协同，提供系统级组件的统一注册与管理。
"""

import inspect
from typing import Any, Callable, Dict, List, Optional, Type


class ComponentRegistry:
    """组件注册中心 — 协同之基

    管理所有可被系统识别的组件，支持类型注册、依赖解析。
    """

    _instance: Optional["ComponentRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._components = {}
            cls._instance._aliases = {}
        return cls._instance

    def register(
        self,
        name: str,
        component: Any = None,
        *,
        aliases: Optional[List[str]] = None,
    ) -> Any:
        """注册组件（装饰器或直接调用）"""
        if component is None:
            # 装饰器模式
            def decorator(func_or_class: Any) -> Any:
                self._components[name] = func_or_class
                if aliases:
                    for alias in aliases:
                        self._aliases[alias] = name
                return func_or_class
            return decorator
        # 直接注册
        self._components[name] = component
        if aliases:
            for alias in aliases:
                self._aliases[alias] = name
        return component

    def get(self, name: str) -> Any:
        """获取组件"""
        actual_name = self._aliases.get(name, name)
        if actual_name not in self._components:
            raise KeyError(f"Component not found: {name}")
        return self._components[actual_name]

    def has(self, name: str) -> bool:
        """检查组件是否存在"""
        actual_name = self._aliases.get(name, name)
        return actual_name in self._components

    def list_all(self) -> List[str]:
        """列出所有组件名"""
        return sorted(self._components.keys())

    def resolve_deps(self, func: Callable) -> Dict[str, Any]:
        """基于类型注解解析依赖"""
        sig = inspect.signature(func)
        resolved = {}
        for param_name, param in sig.parameters.items():
            if param.annotation is inspect.Parameter.empty:
                continue
            type_name = getattr(param.annotation, "__name__", str(param.annotation))
            if self.has(type_name):
                resolved[param_name] = self.get(type_name)
        return resolved

    def clear(self) -> None:
        """清空注册表（谨慎使用）"""
        self._components.clear()
        self._aliases.clear()


def get_registry() -> ComponentRegistry:
    """获取全局注册中心单例"""
    return ComponentRegistry()


def component(name: str, aliases: Optional[List[str]] = None):
    """组件注册装饰器"""
    return get_registry().register(name, aliases=aliases)
