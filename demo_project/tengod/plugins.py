"""
tengod.plugins —— Stage 23: Plugin Marketplace / 插件子系统

提供：
- PluginMetadata         插件元数据
- PluginRegistry         插件注册/查询/激活
- PluginSandbox          安全执行环境（in-process 或 subprocess 隔离）
- PluginHookManager      钩子触发与批处理
- Built-in Plugins       内置插件集合
"""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
import time
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime
from multiprocessing import Process, Queue
from queue import Empty
from typing import Any, Callable, Dict, List, Optional, Union

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

VALID_HOOKS: frozenset = frozenset([
    "bazi:pre_calc",
    "bazi:post_calc",
    "report:pre_gen",
    "report:post_gen",
    "search:post_query",
    "ui:custom_component",
    "analysis:post_trajectory",
])

VALID_PERMISSIONS: frozenset = frozenset([
    "read:records",
    "write:records",
    "read:cases",
    "write:cases",
    "cache:read",
    "cache:write",
    "network:outbound",
    "config:read",
    "metrics:write",
    "ui:render",
])

# 沙盒允许的模块导入白名单
SANDBOX_IMPORT_WHITELIST: frozenset = frozenset([
    "json", "math", "re", "datetime", "time",
    "collections", "copy", "itertools", "random",
    "statistics", "string", "typing", "enum",
    "dataclasses", "functools", "operator",
    "hashlib", "base64", "uuid", "csv",
    "bisect", "heapq", "pprint",
])

DEFAULT_TIMEOUT_SECONDS: float = 5.0
DEFAULT_MAX_MEMORY_MB: int = 256

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(-[A-Za-z0-9]+(\.[A-Za-z0-9]+)*)?$")
_PLUGIN_ID_RE = re.compile(r"^[a-z][a-z0-9_\-]*(\.[a-z][a-z0-9_\-]*)+$")


# ---------------------------------------------------------------------------
# 子进程执行：模块级函数（用于 multiprocessing pickle）
# ---------------------------------------------------------------------------


def _sandbox_child_main(code: str, data: Any, ctx: Dict[str, Any],
                        queue: "Queue[Dict[str, Any]]",
                        allowed_modules: List[str],
                        max_memory_mb: int) -> None:
    try:
        import resource  # type: ignore
        try:
            resource.setrlimit(resource.RLIMIT_AS,
                               (max_memory_mb * 1024 * 1024,
                                max_memory_mb * 1024 * 1024))
        except (ValueError, OSError):
            pass
    except Exception:
        pass

    import builtins as _builtins_mod
    wanted_names = [
        "abs", "all", "any", "ascii", "bin", "bool", "bytes",
        "callable", "chr", "complex", "dict", "dir", "divmod",
        "enumerate", "filter", "float", "format", "frozenset",
        "getattr", "hasattr", "hash", "hex", "id", "int",
        "isinstance", "issubclass", "iter", "len", "list",
        "map", "max", "min", "next", "oct", "ord", "pow",
        "print", "range", "repr", "reversed", "round", "set",
        "slice", "sorted", "str", "sum", "tuple", "type",
        "zip", "True", "False", "None",
    ]
    _safe_builtins: Dict[str, Any] = {}
    for name in wanted_names:
        if hasattr(_builtins_mod, name):
            _safe_builtins[name] = getattr(_builtins_mod, name)
    _allowed = set(allowed_modules)

    def _safe_import(name: str, *args: Any, **kwargs: Any) -> Any:
        root = name.split(".")[0]
        if root not in _allowed:
            raise ImportError(f"import of '{name}' not allowed in sandbox")
        return __import__(name, *args, **kwargs)

    _safe_builtins["__import__"] = _safe_import

    local_ns: Dict[str, Any] = {"__builtins__": _safe_builtins}
    _start = time.perf_counter()
    try:
        exec(code, local_ns)
        main_fn = local_ns.get("main")
        if not callable(main_fn):
            queue.put({
                "result": None,
                "success": False,
                "error": "No callable 'main' in plugin code",
                "elapsed_ms": int((time.perf_counter() - _start) * 1000),
            })
            return
        res = main_fn(data, ctx)
        queue.put({
            "result": res,
            "success": True,
            "error": None,
            "elapsed_ms": int((time.perf_counter() - _start) * 1000),
        })
    except Exception as e:
        queue.put({
            "result": None,
            "success": False,
            "error": f"{type(e).__name__}: {e}",
            "elapsed_ms": 0,
        })


# ---------------------------------------------------------------------------
# PluginMetadata
# ---------------------------------------------------------------------------


@dataclass
class PluginMetadata:
    id: str
    name: str
    version: str
    author: str
    description: str
    entry_point: str
    hooks: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    is_builtin: bool = False

    # 可选：用户可挂载的运行时函数（in-process 快速路径）
    _runtime_fn: Optional[Callable] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        d.pop("_runtime_fn", None)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# PluginRegistry
# ---------------------------------------------------------------------------


class PluginRegistry:
    """插件注册表：维护插件元数据集合。"""

    def __init__(self) -> None:
        self._plugins: Dict[str, PluginMetadata] = {}
        self._lock = threading.RLock()

    def register(self, metadata: PluginMetadata) -> bool:
        if not self.validate_metadata(metadata):
            return False
        with self._lock:
            if metadata.id in self._plugins:
                return False
            self._plugins[metadata.id] = metadata
            return True

    def unregister(self, plugin_id: str) -> bool:
        with self._lock:
            if plugin_id not in self._plugins:
                return False
            if self._plugins[plugin_id].is_builtin:
                return False
            del self._plugins[plugin_id]
            return True

    def get(self, plugin_id: str) -> Optional[PluginMetadata]:
        return self._plugins.get(plugin_id)

    def list_all(self, active_only: bool = False,
                 hook_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            out: List[Dict[str, Any]] = []
            for p in self._plugins.values():
                if active_only and not p.is_active:
                    continue
                if hook_filter is not None and hook_filter not in p.hooks:
                    continue
                out.append(p.to_dict())
            return out

    def activate(self, plugin_id: str) -> bool:
        p = self._plugins.get(plugin_id)
        if p is None:
            return False
        p.is_active = True
        return True

    def deactivate(self, plugin_id: str) -> bool:
        p = self._plugins.get(plugin_id)
        if p is None:
            return False
        p.is_active = False
        return True

    def get_by_hook(self, hook_name: str) -> List[PluginMetadata]:
        return [
            p for p in self._plugins.values()
            if p.is_active and hook_name in p.hooks
        ]

    def validate_metadata(self, metadata: PluginMetadata) -> bool:
        required = ["id", "name", "version", "author", "description", "entry_point"]
        for f in required:
            v = getattr(metadata, f, None)
            if v is None or (isinstance(v, str) and not v.strip()):
                return False
        if not _PLUGIN_ID_RE.match(metadata.id):
            return False
        if not _VERSION_RE.match(metadata.version):
            return False
        if not isinstance(metadata.hooks, list):
            return False
        if not all(h in VALID_HOOKS for h in metadata.hooks):
            return False
        if not isinstance(metadata.permissions, list):
            return False
        if not all(p in VALID_PERMISSIONS for p in metadata.permissions):
            return False
        if not isinstance(metadata.dependencies, list):
            return False
        return True

    def import_plugin_from_dict(self, d: Dict[str, Any]) -> Optional[PluginMetadata]:
        if not isinstance(d, dict):
            return None
        created_at_raw = d.get("created_at")
        created_at: datetime
        if isinstance(created_at_raw, datetime):
            created_at = created_at_raw
        elif isinstance(created_at_raw, str):
            try:
                created_at = datetime.fromisoformat(created_at_raw)
            except ValueError:
                created_at = datetime.utcnow()
        else:
            created_at = datetime.utcnow()

        md = PluginMetadata(
            id=str(d.get("id", "")),
            name=str(d.get("name", "")),
            version=str(d.get("version", "")),
            author=str(d.get("author", "")),
            description=str(d.get("description", "")),
            entry_point=str(d.get("entry_point", "")),
            hooks=list(d.get("hooks", []) or []),
            permissions=list(d.get("permissions", []) or []),
            dependencies=list(d.get("dependencies", []) or []),
            created_at=created_at,
            is_active=bool(d.get("is_active", True)),
            is_builtin=bool(d.get("is_builtin", False)),
        )
        if self.register(md):
            return md
        return None

    def __len__(self) -> int:
        return len(self._plugins)

    def __contains__(self, plugin_id: str) -> bool:
        return plugin_id in self._plugins


# ---------------------------------------------------------------------------
# PluginSandbox
# ---------------------------------------------------------------------------


class PermissionDeniedError(RuntimeError):
    pass


class PluginSandbox:
    """插件运行时：支持 in-process 快速路径 & 子进程隔离路径。"""

    def __init__(self, registry: PluginRegistry,
                 timeout: float = DEFAULT_TIMEOUT_SECONDS,
                 max_memory_mb: int = DEFAULT_MAX_MEMORY_MB) -> None:
        self.registry = registry
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self._import_whitelist = set(SANDBOX_IMPORT_WHITELIST)

    # -- permissions --------------------------------------------------------

    def verify_permissions(self, plugin_id: str,
                           required_permissions: List[str]) -> None:
        p = self.registry.get(plugin_id)
        if p is None:
            raise PermissionDeniedError(f"plugin {plugin_id} not registered")
        missing = [perm for perm in required_permissions if perm not in p.permissions]
        if missing:
            raise PermissionDeniedError(
                f"plugin {plugin_id} missing permissions: {missing}"
            )

    # -- helpers ------------------------------------------------------------

    def _load_entry_point(self, entry_point: str) -> Optional[Callable]:
        """从 'module.path:funcname' 形式加载函数。"""
        if ":" not in entry_point:
            return None
        module_path, fn_name = entry_point.split(":", 1)
        try:
            module = importlib.import_module(module_path)
            return getattr(module, fn_name, None)
        except Exception:
            return None

    # -- in-process fast path ----------------------------------------------

    def run_in_process(self, plugin_fn: Callable, input_data: Any,
                       context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            if context is None:
                context = {}
            result = plugin_fn(input_data, context)
            elapsed = int((time.perf_counter() - start) * 1000)
            return {
                "result": result,
                "elapsed_ms": elapsed,
                "success": True,
                "error": None,
            }
        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            return {
                "result": None,
                "elapsed_ms": elapsed,
                "success": False,
                "error": f"{type(e).__name__}: {e}",
            }

    # -- subprocess isolated path ------------------------------------------

    def run_isolated(self, plugin_code: str, input_data: Any,
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        以子进程形式运行用户代码：
        - 仅允许导入白名单模块
        - 超时时间由 self.timeout 控制
        - 结果通过 Queue 回传
        """
        if context is None:
            context = {}
        result_queue: Queue = Queue()

        proc = Process(target=_sandbox_child_main,
                       args=(plugin_code, input_data, context, result_queue,
                             list(self._import_whitelist), self.max_memory_mb),
                       daemon=True)
        start = time.perf_counter()
        proc.start()
        proc.join(self.timeout)
        if proc.is_alive():
            proc.terminate()
            proc.join(1.0)
            if proc.is_alive():
                proc.kill()
                proc.join(1.0)
            return {
                "result": None,
                "success": False,
                "error": "timeout",
                "elapsed_ms": int((time.perf_counter() - start) * 1000),
                "timed_out": True,
            }
        try:
            out = result_queue.get_nowait()
        except Empty:
            out = {
                "result": None,
                "success": False,
                "error": "no result",
                "elapsed_ms": int((time.perf_counter() - start) * 1000),
            }
        out.setdefault("elapsed_ms", int((time.perf_counter() - start) * 1000))
        return out

    # -- main entry --------------------------------------------------------

    def run(self, plugin_id: str, hook_name: str, input_data: Any,
            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if context is None:
            context = {}
        p = self.registry.get(plugin_id)
        if p is None:
            return {
                "result": None,
                "success": False,
                "error": f"plugin {plugin_id} not found",
                "plugin_id": plugin_id,
                "hook": hook_name,
                "elapsed_ms": 0,
            }
        start = time.perf_counter()

        # 内置插件：快速路径
        if p.is_builtin and p._runtime_fn is not None:
            res = self.run_in_process(p._runtime_fn,
                                      {"hook": hook_name, "input": input_data},
                                      dict(context, plugin_id=plugin_id))
            res["plugin_id"] = plugin_id
            res["hook"] = hook_name
            return res

        # 用户插件：如挂载了 runtime_fn 也直接 in-process（允许单测注入）
        if p._runtime_fn is not None:
            res = self.run_in_process(p._runtime_fn,
                                      {"hook": hook_name, "input": input_data},
                                      dict(context, plugin_id=plugin_id))
            res["plugin_id"] = plugin_id
            res["hook"] = hook_name
            return res

        # 否则：尝试按 entry_point 加载
        fn = self._load_entry_point(p.entry_point)
        if fn is not None:
            res = self.run_in_process(fn,
                                      {"hook": hook_name, "input": input_data,
                                       "metadata": p.to_dict()},
                                      dict(context, plugin_id=plugin_id))
            res["plugin_id"] = plugin_id
            res["hook"] = hook_name
            return res

        # 最后：若 entry_point 形如 'code://...'，作为代码直接子进程执行
        if p.entry_point.startswith("code://"):
            code = p.entry_point[len("code://"):]
            isolated = self.run_isolated(code,
                                         {"hook": hook_name, "input": input_data,
                                          "metadata": p.to_dict()},
                                         dict(context, plugin_id=plugin_id))
            isolated["plugin_id"] = plugin_id
            isolated["hook"] = hook_name
            return isolated

        return {
            "result": None,
            "success": False,
            "error": f"plugin {plugin_id} has no executable entry_point",
            "plugin_id": plugin_id,
            "hook": hook_name,
            "elapsed_ms": int((time.perf_counter() - start) * 1000),
        }


# ---------------------------------------------------------------------------
# PluginHookManager
# ---------------------------------------------------------------------------


class PluginHookManager:
    """触发 hook，并行批处理。"""

    def __init__(self, registry: PluginRegistry,
                 sandbox: Optional[PluginSandbox] = None,
                 max_workers: int = 4) -> None:
        self.registry = registry
        self.sandbox = sandbox or PluginSandbox(registry)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def trigger_hook(self, hook_name: str, input_data: Any,
                     context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if context is None:
            context = {}
        plugins = self.registry.get_by_hook(hook_name)
        results: List[Dict[str, Any]] = []
        for p in plugins:
            res = self.sandbox.run(p.id, hook_name, input_data, context)
            results.append({
                "plugin_id": p.id,
                "hook": hook_name,
                "success": res.get("success", False),
                "data": res.get("result"),
                "error": res.get("error"),
                "elapsed_ms": res.get("elapsed_ms", 0),
            })
        return results

    def trigger_hook_single(self, plugin_id: str, hook_name: str,
                            input_data: Any,
                            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if context is None:
            context = {}
        p = self.registry.get(plugin_id)
        if p is None or not p.is_active:
            return {
                "plugin_id": plugin_id,
                "hook": hook_name,
                "success": False,
                "data": None,
                "error": "plugin not found or inactive",
                "elapsed_ms": 0,
            }
        res = self.sandbox.run(plugin_id, hook_name, input_data, context)
        return {
            "plugin_id": plugin_id,
            "hook": hook_name,
            "success": res.get("success", False),
            "data": res.get("result"),
            "error": res.get("error"),
            "elapsed_ms": res.get("elapsed_ms", 0),
        }

    def batch_trigger(self, plugin_ids: List[str], hook_name: str,
                      input_data: Any,
                      context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if context is None:
            context = {}

        def _run(pid: str) -> Dict[str, Any]:
            p = self.registry.get(pid)
            if p is None or not p.is_active:
                return {
                    "plugin_id": pid,
                    "hook": hook_name,
                    "success": False,
                    "data": None,
                    "error": "plugin not found or inactive",
                    "elapsed_ms": 0,
                }
            res = self.sandbox.run(pid, hook_name, input_data, context)
            return {
                "plugin_id": pid,
                "hook": hook_name,
                "success": res.get("success", False),
                "data": res.get("result"),
                "error": res.get("error"),
                "elapsed_ms": res.get("elapsed_ms", 0),
            }

        futures = [self._executor.submit(_run, pid) for pid in plugin_ids]
        return [f.result() for f in as_completed(futures)]


# ---------------------------------------------------------------------------
# 内置插件
# ---------------------------------------------------------------------------


def _builtin_report_formatter_fn(payload: Dict[str, Any],
                                 context: Dict[str, Any]) -> Dict[str, Any]:
    inp = payload.get("input", {}) if isinstance(payload, dict) else {}
    report_body = inp.get("report") if isinstance(inp, dict) else None
    extra: List[str] = []
    if isinstance(report_body, str):
        if "五行" in report_body:
            extra.append("已对五行部分进行高亮分析")
        if "大运" in report_body:
            extra.append("已附加大运关键年份索引")
    return {
        "plugin": "builtin_report_formatter",
        "enhanced": True,
        "extra_sections": extra,
        "summary": f"已增强报告，共 {len(extra)} 项补充。",
    }


def _builtin_topic_tagger_fn(payload: Dict[str, Any],
                             context: Dict[str, Any]) -> Dict[str, Any]:
    inp = payload.get("input", {}) if isinstance(payload, dict) else {}
    day_master = inp.get("day_master") if isinstance(inp, dict) else None
    pillars = inp.get("pillars") if isinstance(inp, dict) else None

    topics: List[str] = []
    if isinstance(pillars, (list, tuple)):
        for p in pillars:
            if isinstance(p, str) and "金" in p:
                topics.append("金属性")
            if isinstance(p, str) and "木" in p:
                topics.append("木属性")
            if isinstance(p, str) and "水" in p:
                topics.append("水属性")
            if isinstance(p, str) and "火" in p:
                topics.append("火属性")
            if isinstance(p, str) and "土" in p:
                topics.append("土属性")
    if isinstance(day_master, str):
        topics.append(f"日主-{day_master}")
    # 去重保持顺序
    seen = set()
    unique_topics: List[str] = []
    for t in topics:
        if t not in seen:
            seen.add(t)
            unique_topics.append(t)
    return {
        "plugin": "builtin_topic_tagger",
        "topics": unique_topics,
        "count": len(unique_topics),
    }


def _builtin_lucky_element_suggestor_fn(payload: Dict[str, Any],
                                        context: Dict[str, Any]) -> Dict[str, Any]:
    inp = payload.get("input", {}) if isinstance(payload, dict) else {}
    year = inp.get("year") if isinstance(inp, dict) else None
    trajectory = inp.get("trajectory") if isinstance(inp, dict) else None

    elements = ["金", "木", "水", "火", "土"]
    # 确定性：基于 year 取模
    idx = 0
    if isinstance(year, int):
        idx = year % 5
    elif isinstance(year, str) and year.isdigit():
        idx = int(year) % 5
    elif isinstance(trajectory, (list, tuple)) and len(trajectory) > 0:
        idx = len(trajectory) % 5
    primary = elements[idx]
    secondary = elements[(idx + 2) % 5]
    return {
        "plugin": "builtin_lucky_element_suggestor",
        "primary_element": primary,
        "secondary_element": secondary,
        "unfavorable": elements[(idx + 1) % 5],
        "year": year,
    }


BUILTIN_PLUGINS = {
    "tengod.builtin.report_formatter": {
        "name": "内置报告格式化器",
        "version": "1.0.0",
        "author": "tengod-team",
        "description": "增强输出报告的结构与可读性，附加高亮与索引。",
        "entry_point": "tengod.plugins:_builtin_report_formatter_fn",
        "hooks": ["report:post_gen"],
        "permissions": ["read:records"],
        "fn": _builtin_report_formatter_fn,
    },
    "tengod.builtin.topic_tagger": {
        "name": "内置主题标签器",
        "version": "1.0.0",
        "author": "tengod-team",
        "description": "根据日主与四柱对命例记录打主题/分类标签。",
        "entry_point": "tengod.plugins:_builtin_topic_tagger_fn",
        "hooks": ["search:post_query", "analysis:post_trajectory"],
        "permissions": ["read:records", "cache:read"],
        "fn": _builtin_topic_tagger_fn,
    },
    "tengod.builtin.lucky_element_suggestor": {
        "name": "内置喜忌元素推荐",
        "version": "1.0.0",
        "author": "tengod-team",
        "description": "为每个大运/流年年份推荐有利五行元素与规避元素。",
        "entry_point": "tengod.plugins:_builtin_lucky_element_suggestor_fn",
        "hooks": ["bazi:post_calc", "analysis:post_trajectory"],
        "permissions": ["read:records"],
        "fn": _builtin_lucky_element_suggestor_fn,
    },
}


# ---------------------------------------------------------------------------
# 助手函数 + 单例管理器
# ---------------------------------------------------------------------------


def create_plugin_metadata(id: str, name: str, version: str,
                           author: str, description: str,
                           entry_point: str,
                           hooks: Optional[List[str]] = None,
                           permissions: Optional[List[str]] = None,
                           dependencies: Optional[List[str]] = None,
                           is_active: bool = True,
                           is_builtin: bool = False,
                           runtime_fn: Optional[Callable] = None) -> PluginMetadata:
    md = PluginMetadata(
        id=id,
        name=name,
        version=version,
        author=author,
        description=description,
        entry_point=entry_point,
        hooks=list(hooks or []),
        permissions=list(permissions or []),
        dependencies=list(dependencies or []),
        is_active=is_active,
        is_builtin=is_builtin,
    )
    md._runtime_fn = runtime_fn
    return md


def validate_plugin_json(json_str: str) -> bool:
    try:
        d = json.loads(json_str)
    except json.JSONDecodeError:
        return False
    if not isinstance(d, dict):
        return False
    md = PluginMetadata(
        id=str(d.get("id", "")),
        name=str(d.get("name", "")),
        version=str(d.get("version", "")),
        author=str(d.get("author", "")),
        description=str(d.get("description", "")),
        entry_point=str(d.get("entry_point", "")),
        hooks=list(d.get("hooks", []) or []),
        permissions=list(d.get("permissions", []) or []),
        dependencies=list(d.get("dependencies", []) or []),
    )
    # 临时注册表用于复用 validate_metadata
    tmp = PluginRegistry()
    return tmp.validate_metadata(md)


class _PluginManager:
    """顶层单例管理器：将 Registry / Sandbox / HookManager 组合在一起。"""

    def __init__(self) -> None:
        self.registry = PluginRegistry()
        self.sandbox = PluginSandbox(self.registry)
        self.hook_manager = PluginHookManager(self.registry, self.sandbox)
        self._register_builtins()

    def _register_builtins(self) -> None:
        for pid, info in BUILTIN_PLUGINS.items():
            md = PluginMetadata(
                id=pid,
                name=info["name"],
                version=info["version"],
                author=info["author"],
                description=info["description"],
                entry_point=info["entry_point"],
                hooks=list(info["hooks"]),
                permissions=list(info["permissions"]),
                is_active=True,
                is_builtin=True,
            )
            md._runtime_fn = info["fn"]
            self.registry.register(md)

    def register(self, metadata: PluginMetadata) -> bool:
        return self.registry.register(metadata)

    def unregister(self, plugin_id: str) -> bool:
        return self.registry.unregister(plugin_id)

    def trigger(self, hook_name: str, input_data: Any,
                context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self.hook_manager.trigger_hook(hook_name, input_data, context)


_PLUGIN_MANAGER: Optional[_PluginManager] = None
_PM_LOCK = threading.Lock()


def get_plugin_manager() -> _PluginManager:
    global _PLUGIN_MANAGER
    if _PLUGIN_MANAGER is None:
        with _PM_LOCK:
            if _PLUGIN_MANAGER is None:
                _PLUGIN_MANAGER = _PluginManager()
    return _PLUGIN_MANAGER


def _reset_plugin_manager() -> None:
    """测试工具：重置单例。"""
    global _PLUGIN_MANAGER
    _PLUGIN_MANAGER = None


# ---------------------------------------------------------------------------
# 自测块
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    pm = get_plugin_manager()
    print("已注册插件：")
    for p in pm.registry.list_all():
        print(f"  - {p['id']} ({p['name']} v{p['version']}) "
              f"builtin={p['is_builtin']}, active={p['is_active']}")

    # 测试插件：挂载本地函数
    def test_plugin_fn(payload: Dict[str, Any],
                        context: Dict[str, Any]) -> Dict[str, Any]:
        return {"hello": "from test_plugin", "input": payload.get("input")}

    test_md = create_plugin_metadata(
        id="com.example.self-test-plugin",
        name="自测示例插件",
        version="0.1.0",
        author="test-runner",
        description="用于 CLI 自检的最小插件",
        entry_point="__main__:test_plugin_fn",
        hooks=["report:post_gen"],
        permissions=["read:records"],
        runtime_fn=test_plugin_fn,
    )
    ok = pm.register(test_md)
    print(f"register test plugin -> {ok}")

    results = pm.trigger("report:post_gen",
                         {"report": "示例报告内容 包含 五行 与 大运"})
    print(f"trigger report:post_gen -> {len(results)} 个插件响应")
    for r in results:
        print("  ->", r)
