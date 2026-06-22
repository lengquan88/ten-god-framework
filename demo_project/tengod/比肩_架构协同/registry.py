#!/usr/bin/env python3
"""
registry.py — 组件注册中心
比肩主理协同，提供系统级组件的统一注册与管理。
"""

import inspect
import threading
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ComponentState(Enum):
    """组件生命周期状态"""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    STOPPED = "stopped"
    FAILED = "failed"


class LifecycleManager:
    """组件生命周期管理器"""

    def __init__(self):
        self._states: Dict[str, ComponentState] = {}
        self._hooks: Dict[
            str, Dict[str, List[Callable]]
        ] = {}  # name -> {on_start: [], on_stop: [], on_fail: []}
        self._lock = threading.Lock()

    def register(self, name: str) -> None:
        """注册组件生命周期"""
        with self._lock:
            self._states[name] = ComponentState.UNINITIALIZED
            self._hooks[name] = {"on_start": [], "on_stop": [], "on_fail": []}

    def set_state(self, name: str, state: ComponentState) -> None:
        """设置组件状态"""
        with self._lock:
            old = self._states.get(name, ComponentState.UNINITIALIZED)
            self._states[name] = state
            # 触发钩子
            hooks = self._hooks.get(name, {})
            if state == ComponentState.READY and old != ComponentState.READY:
                for h in hooks.get("on_start", []):
                    try:
                        h(name)
                    except Exception:
                        pass
            elif state in (ComponentState.STOPPED, ComponentState.FAILED):
                for h in hooks.get(
                    "on_stop" if state == ComponentState.STOPPED else "on_fail", []
                ):
                    try:
                        h(name)
                    except Exception:
                        pass

    def get_state(self, name: str) -> ComponentState:
        return self._states.get(name, ComponentState.UNINITIALIZED)

    def on_start(self, name: str, hook: Callable) -> None:
        self._hooks.setdefault(name, {"on_start": [], "on_stop": [], "on_fail": []})
        self._hooks[name]["on_start"].append(hook)

    def on_stop(self, name: str, hook: Callable) -> None:
        self._hooks.setdefault(name, {"on_start": [], "on_stop": [], "on_fail": []})
        self._hooks[name]["on_stop"].append(hook)

    def on_fail(self, name: str, hook: Callable) -> None:
        self._hooks.setdefault(name, {"on_start": [], "on_stop": [], "on_fail": []})
        self._hooks[name]["on_fail"].append(hook)

    def list_states(self) -> Dict[str, str]:
        return {n: s.value for n, s in self._states.items()}

    def summary(self) -> Dict[str, Any]:
        counts = {s.value: 0 for s in ComponentState}
        for s in self._states.values():
            counts[s.value] += 1
        return {"total": len(self._states), "by_state": counts}


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
            cls._instance._lifecycle: Optional[LifecycleManager] = None
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

    def get_lifecycle(self) -> LifecycleManager:
        """获取生命周期管理器"""
        if self._lifecycle is None:
            self._lifecycle = LifecycleManager()
        return self._lifecycle

    def register_with_lifecycle(
        self,
        name: str,
        component: Any,
        *,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
    ) -> bool:
        """注册组件并设置生命周期钩子"""
        ok = self.register(name, component)
        if ok and self._lifecycle:
            self._lifecycle.register(name)
            self._lifecycle.set_state(name, ComponentState.READY)
            if on_start:
                self._lifecycle.on_start(name, on_start)
            if on_stop:
                self._lifecycle.on_stop(name, on_stop)
        return ok


def get_registry() -> ComponentRegistry:
    """获取全局注册中心单例"""
    return ComponentRegistry()


def component(name: str, aliases: Optional[List[str]] = None):
    """组件注册装饰器"""
    return get_registry().register(name, aliases=aliases)


__all__ = [
    "ComponentRegistry",
    "ComponentState",
    "LifecycleManager",
    "component",
    "get_registry",
]
__version__ = "1.4.0"
