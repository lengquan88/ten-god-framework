#!/usr/bin/env python3
"""
plugin_manager.py — 十神插件系统 v2.0.0
支持动态加载/卸载/生命周期管理的插件框架。
"""

import importlib
import importlib.util
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

__all__ = ["PluginManager", "PluginSpec", "PluginState", "PluginHook"]
__version__ = "2.0.0"


@dataclass
class PluginSpec:
    """插件规格"""

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = ""  # 如 "my_plugin:main"
    file_path: str = ""


class PluginState:
    """插件状态枚举"""

    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    FAILED = "failed"
    DISABLED = "disabled"


class PluginHook:
    """插件钩子定义"""

    ON_LOAD = "on_load"
    ON_UNLOAD = "on_unload"
    ON_ACTIVATE = "on_activate"
    ON_DEACTIVATE = "on_deactivate"
    ON_ERROR = "on_error"
    PRE_GENERATE = "pre_generate"  # 食神生成前
    POST_GENERATE = "post_generate"  # 食神生成后
    PRE_SEARCH = "pre_search"  # 正财搜索前
    POST_SEARCH = "post_search"  # 正财搜索后
    PRE_EVALUATE = "pre_evaluate"  # 七杀评估前
    POST_EVALUATE = "post_evaluate"  # 七杀评估后


class Plugin:
    """插件实例"""

    def __init__(self, spec: PluginSpec):
        self.spec = spec
        self.state = PluginState.UNLOADED
        self.module: Optional[Any] = None
        self.instance: Optional[Any] = None
        self._hooks: Dict[str, List[Callable]] = {}
        self.loaded_at: Optional[float] = None
        self.error: Optional[str] = None

    def call_hook(self, hook_name: str, *args, **kwargs) -> Any:
        if hook_name in self._hooks:
            for handler in self._hooks[hook_name]:
                try:
                    result = handler(*args, **kwargs)
                    if result is not None:
                        return result
                except Exception as e:
                    self.spec.dependencies  # silence
                    print(f"[Plugin {self.spec.name}] hook {hook_name} error: {e}")
        return None


class PluginManager:
    """插件管理器"""

    def __init__(self, plugin_dir: Optional[str] = None):
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, List[Callable]] = {}  # 全局钩子
        self._lock = threading.RLock()
        self._search_paths: List[str] = []
        if plugin_dir:
            self.add_search_path(plugin_dir)
        # 默认搜索路径
        default = os.path.join(os.path.dirname(__file__), "plugins")
        if os.path.isdir(default):
            self.add_search_path(default)

    def add_search_path(self, path: str) -> None:
        """添加插件搜索路径"""
        if os.path.isdir(path) and path not in self._search_paths:
            self._search_paths.append(path)

    def discover(self) -> List[PluginSpec]:
        """自动发现插件（扫描 search_paths 下所有 python 文件）"""
        discovered: List[PluginSpec] = []
        for search_path in self._search_paths:
            if not os.path.isdir(search_path):
                continue
            for fname in os.listdir(search_path):
                if fname.endswith(".py") and not fname.startswith("_"):
                    fpath = os.path.join(search_path, fname)
                    try:
                        spec = self._parse_plugin_file(fpath)
                        if spec:
                            discovered.append(spec)
                    except Exception:
                        pass
        return discovered

    def _parse_plugin_file(self, fpath: str) -> Optional[PluginSpec]:
        """从 Python 文件解析插件规格（检查 PLUGIN_SPEC 变量）"""
        try:
            spec = importlib.util.spec_from_file_location("plugin", fpath)
            if not spec or not spec.loader:
                return None
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            # 查找 PLUGIN_SPEC
            if hasattr(mod, "PLUGIN_SPEC"):
                s = mod.PLUGIN_SPEC
                return PluginSpec(
                    name=s.get("name", os.path.basename(fpath)[:-3]),
                    version=s.get("version", "1.0.0"),
                    description=s.get("description", ""),
                    author=s.get("author", ""),
                    dependencies=s.get("dependencies", []),
                    entry_point=s.get("entry_point", ""),
                    file_path=fpath,
                )
            return None
        except Exception:
            return None

    def register_plugin(self, spec: PluginSpec) -> Plugin:
        """注册插件（但不加载）"""
        with self._lock:
            if spec.name in self._plugins:
                raise ValueError(f"插件 {spec.name} 已注册")
            plugin = Plugin(spec)
            self._plugins[spec.name] = plugin
            return plugin

    def load_plugin(self, name: str) -> Plugin:
        """加载插件"""
        with self._lock:
            plugin = self._plugins.get(name)
            if not plugin:
                raise KeyError(f"插件 {name} 未注册")
            if plugin.state in (PluginState.LOADED, PluginState.ACTIVE):
                return plugin

            plugin.state = PluginState.LOADING
            try:
                # 动态导入
                if plugin.spec.file_path:
                    spec = importlib.util.spec_from_file_location(
                        f"plugin_{name}", plugin.spec.file_path
                    )
                    if not spec or not spec.loader:
                        raise ImportError("无法加载文件")
                    plugin.module = importlib.util.module_from_spec(spec)
                    sys.modules[f"plugin_{name}"] = plugin.module
                    spec.loader.exec_module(plugin.module)

                # 实例化入口
                if plugin.spec.entry_point and plugin.module:
                    parts = plugin.spec.entry_point.split(":")
                    if len(parts) == 2:
                        obj = getattr(plugin.module, parts[0], None)
                        if callable(obj):
                            plugin.instance = obj()

                # 注册钩子
                if plugin.module:
                    for hook_name in dir(plugin.module):
                        if hook_name.startswith("hook_"):
                            handler = getattr(plugin.module, hook_name)
                            if callable(handler):
                                plugin._hooks[hook_name.replace("hook_", "")] = (
                                    plugin._hooks.get(
                                        hook_name.replace("hook_", ""), []
                                    )
                                )
                                plugin._hooks[hook_name.replace("hook_", "")].append(
                                    handler
                                )

                plugin.state = PluginState.LOADED
                plugin.loaded_at = time.time()
                plugin.call_hook(PluginHook.ON_LOAD)
                return plugin
            except Exception as e:
                plugin.state = PluginState.FAILED
                plugin.error = str(e)
                plugin.call_hook(PluginHook.ON_ERROR, e)
                raise

    def activate_plugin(self, name: str) -> Plugin:
        """激活插件（加载并启用）"""
        plugin = self.load_plugin(name)
        if plugin.state == PluginState.LOADED:
            plugin.state = PluginState.ACTIVE
            plugin.call_hook(PluginHook.ON_ACTIVATE)
        return plugin

    def deactivate_plugin(self, name: str) -> None:
        """停用插件"""
        with self._lock:
            plugin = self._plugins.get(name)
            if plugin and plugin.state == PluginState.ACTIVE:
                plugin.state = PluginState.LOADED
                plugin.call_hook(PluginHook.ON_DEACTIVATE)

    def uninstall_plugin(self, name: str) -> bool:
        """卸载插件"""
        with self._lock:
            plugin = self._plugins.pop(name, None)
            if plugin:
                if plugin.state == PluginState.ACTIVE:
                    self.deactivate_plugin(name)
                plugin.state = PluginState.UNLOADED
                plugin.call_hook(PluginHook.ON_UNLOAD)
                return True
            return False

    def call_global_hook(self, hook_name: str, *args, **kwargs) -> Any:
        """触发全局钩子"""
        results = []
        with self._lock:
            for plugin in self._plugins.values():
                if plugin.state == PluginState.ACTIVE:
                    r = plugin.call_hook(hook_name, *args, **kwargs)
                    if r is not None:
                        results.append(r)
            for handler in self._hooks.get(hook_name, []):
                try:
                    r = handler(*args, **kwargs)
                    if r is not None:
                        results.append(r)
                except Exception as e:
                    print(f"[PluginManager] global hook {hook_name} error: {e}")
        return results

    def get_plugin(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)

    def list_plugins(self, state: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出插件（可选按状态过滤）"""
        with self._lock:
            plugins = list(self._plugins.values())
            if state:
                plugins = [p for p in plugins if p.state == state]
            return [
                {
                    "name": p.spec.name,
                    "version": p.spec.version,
                    "description": p.spec.description,
                    "author": p.spec.author,
                    "state": p.state,
                    "loaded_at": p.loaded_at,
                    "error": p.error,
                }
                for p in plugins
            ]

    def stats(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        for p in self._plugins.values():
            counts[p.state] = counts.get(p.state, 0) + 1
        return {
            "total": len(self._plugins),
            "by_state": counts,
            "search_paths": self._search_paths,
        }


# -------- 示例插件 --------
def _create_sample_plugin() -> None:
    """创建一个示例插件到 plugins/ 目录"""
    sample_dir = os.path.join(os.path.dirname(__file__), "plugins")
    os.makedirs(sample_dir, exist_ok=True)
    sample = os.path.join(sample_dir, "tengod_sample_plugin.py")
    if not os.path.exists(sample):
        with open(sample, "w", encoding="utf-8") as f:
            f.write('''
"""十神示例插件 - 中华文明知识增强"""

PLUGIN_SPEC = {
    "name": "zhwenshi-knowledge",
    "version": "1.0.0",
    "description": "中华文明知识增强插件",
    "author": "tengod",
    "dependencies": [],
    "entry_point": "",
}

def hook_on_load():
    print("[zhwenshi-knowledge] 插件已加载")

def hook_on_activate():
    print("[zhwenshi-knowledge] 插件已激活")
''')


if __name__ == "__main__":
    pm = PluginManager()
    pm.add_search_path(".")
    specs = pm.discover()
    print(f"发现插件: {[s.name for s in specs]}")
    for s in specs:
        p = pm.register_plugin(s)
        pm.activate_plugin(s.name)
    print(f"已激活插件: {[p['name'] for p in pm.list_plugins(PluginState.ACTIVE)]}")
    print(pm.stats())
