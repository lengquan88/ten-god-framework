#!/usr/bin/env python3
"""
test_registry_sub.py — 注册中心全面测试，目标 100% 覆盖率。
"""

import typing

import pytest

from tengod.比肩_架构协同.registry import (
    ComponentRegistry,
    ComponentState,
    LifecycleManager,
    component,
    get_registry,
)


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_registry():
    """每次测试前重置全局单例状态。"""
    reg = get_registry()
    reg.clear()
    reg._lifecycle = None
    yield


@pytest.fixture
def lm():
    """新建 LifecycleManager 实例。"""
    return LifecycleManager()


# ══════════════════════════════════════════════════════════════════════════════
# ComponentState — 枚举值
# ══════════════════════════════════════════════════════════════════════════════

class TestComponentState:
    """ComponentState 枚举测试。"""

    def test_all_enum_values(self):
        """所有枚举值存在。"""
        members = list(ComponentState)
        assert len(members) == 6
        names = {m.name for m in members}
        assert names == {
            "UNINITIALIZED", "INITIALIZING", "READY",
            "DEGRADED", "STOPPED", "FAILED",
        }

    def test_value_strings_match(self):
        """每个枚举值的 .value 字符串正确。"""
        assert ComponentState.UNINITIALIZED.value == "uninitialized"
        assert ComponentState.INITIALIZING.value == "initializing"
        assert ComponentState.READY.value == "ready"
        assert ComponentState.DEGRADED.value == "degraded"
        assert ComponentState.STOPPED.value == "stopped"
        assert ComponentState.FAILED.value == "failed"

    def test_enum_equality(self):
        """枚举相等性比较。"""
        assert ComponentState.READY == ComponentState.READY
        assert ComponentState.READY != ComponentState.FAILED
        assert ComponentState.READY is ComponentState.READY


# ══════════════════════════════════════════════════════════════════════════════
# LifecycleManager
# ══════════════════════════════════════════════════════════════════════════════

class TestLifecycleManager:
    """LifecycleManager 测试。"""

    # ── register ──────────────────────────────────────────────────────────

    def test_register_sets_state_to_uninitialized(self, lm):
        """register() 将组件状态设为 UNINITIALIZED。"""
        lm.register("comp_a")
        assert lm.get_state("comp_a") == ComponentState.UNINITIALIZED

    def test_register_creates_hooks(self, lm):
        """register() 为组件创建钩子列表。"""
        lm.register("comp_a")
        assert "comp_a" in lm._hooks
        assert lm._hooks["comp_a"]["on_start"] == []
        assert lm._hooks["comp_a"]["on_stop"] == []
        assert lm._hooks["comp_a"]["on_fail"] == []

    # ── set_state ─────────────────────────────────────────────────────────

    def test_set_state_changes_state(self, lm):
        """set_state() 改变组件状态。"""
        lm.register("svc")
        lm.set_state("svc", ComponentState.READY)
        assert lm.get_state("svc") == ComponentState.READY

    def test_set_state_triggers_on_start_when_ready(self, lm):
        """set_state() 在状态变为 READY 时触发 on_start 钩子。"""
        lm.register("svc")
        calls = []
        lm.on_start("svc", lambda n: calls.append(("start", n)))
        lm.set_state("svc", ComponentState.READY)
        assert calls == [("start", "svc")]

    def test_set_state_triggers_on_stop_when_stopped(self, lm):
        """set_state() 在状态变为 STOPPED 时触发 on_stop 钩子。"""
        lm.register("svc")
        calls = []
        lm.on_stop("svc", lambda n: calls.append(("stop", n)))
        lm.set_state("svc", ComponentState.STOPPED)
        assert calls == [("stop", "svc")]

    def test_set_state_triggers_on_fail_when_failed(self, lm):
        """set_state() 在状态变为 FAILED 时触发 on_fail 钩子。"""
        lm.register("svc")
        calls = []
        lm.on_fail("svc", lambda n: calls.append(("fail", n)))
        lm.set_state("svc", ComponentState.FAILED)
        assert calls == [("fail", "svc")]

    def test_set_state_hook_exception_is_caught(self, lm):
        """set_state() 钩子中抛出异常不会导致崩溃。"""
        lm.register("svc")
        lm.on_start("svc", lambda n: 1 / 0)
        lm.on_stop("svc", lambda n: 1 / 0)
        lm.on_fail("svc", lambda n: 1 / 0)

        # 不应抛出异常
        lm.set_state("svc", ComponentState.READY)
        lm.set_state("svc", ComponentState.STOPPED)
        lm.set_state("svc", ComponentState.FAILED)
        assert lm.get_state("svc") == ComponentState.FAILED

    def test_set_state_on_start_hook_called_with_name(self, lm):
        """on_start 钩子被调用时传入组件名称。"""
        lm.register("my_service")
        received_name = []

        def hook(name):
            received_name.append(name)

        lm.on_start("my_service", hook)
        lm.set_state("my_service", ComponentState.READY)
        assert received_name == ["my_service"]

    def test_set_state_to_same_ready_does_not_trigger_hooks(self, lm):
        """set_state() 从 READY→READY 不触发钩子。"""
        lm.register("svc")
        calls = []
        lm.on_start("svc", lambda n: calls.append("start"))
        lm.set_state("svc", ComponentState.READY)
        assert calls == ["start"]
        lm.set_state("svc", ComponentState.READY)
        assert calls == ["start"]  # 不重复触发

    def test_set_state_to_same_stopped_triggers_hooks_again(self, lm):
        """set_state() STOPPED→STOPPED 会再次触发 on_stop 钩子。"""
        lm.register("svc")
        calls = []
        lm.on_stop("svc", lambda n: calls.append("stop"))
        lm.set_state("svc", ComponentState.STOPPED)
        lm.set_state("svc", ComponentState.STOPPED)
        assert calls == ["stop", "stop"]

    def test_set_state_to_same_failed_triggers_hooks_again(self, lm):
        """set_state() FAILED→FAILED 会再次触发 on_fail 钩子。"""
        lm.register("svc")
        calls = []
        lm.on_fail("svc", lambda n: calls.append("fail"))
        lm.set_state("svc", ComponentState.FAILED)
        lm.set_state("svc", ComponentState.FAILED)
        assert calls == ["fail", "fail"]

    def test_set_state_initializing_does_not_trigger_hooks(self, lm):
        """INITIALIZING/DEGRADED 状态不触发任何钩子。"""
        lm.register("svc")
        start_calls = []
        stop_calls = []
        fail_calls = []
        lm.on_start("svc", lambda n: start_calls.append(n))
        lm.on_stop("svc", lambda n: stop_calls.append(n))
        lm.on_fail("svc", lambda n: fail_calls.append(n))

        lm.set_state("svc", ComponentState.INITIALIZING)
        lm.set_state("svc", ComponentState.DEGRADED)

        assert start_calls == []
        assert stop_calls == []
        assert fail_calls == []

    # ── get_state ─────────────────────────────────────────────────────────

    def test_get_state_returns_current_state(self, lm):
        """get_state() 返回当前状态。"""
        lm.register("svc")
        lm.set_state("svc", ComponentState.READY)
        assert lm.get_state("svc") == ComponentState.READY

    def test_get_state_nonexistent_returns_uninitialized(self, lm):
        """get_state() 对不存在的组件返回 UNINITIALIZED。"""
        assert lm.get_state("nonexistent") == ComponentState.UNINITIALIZED

    # ── on_start / on_stop / on_fail ──────────────────────────────────────

    def test_on_start_registers_hook(self, lm):
        """on_start() 注册钩子。"""
        lm.on_start("svc", lambda n: None)
        assert len(lm._hooks["svc"]["on_start"]) == 1

    def test_on_stop_registers_hook(self, lm):
        """on_stop() 注册钩子。"""
        lm.on_stop("svc", lambda n: None)
        assert len(lm._hooks["svc"]["on_stop"]) == 1

    def test_on_fail_registers_hook(self, lm):
        """on_fail() 注册钩子。"""
        lm.on_fail("svc", lambda n: None)
        assert len(lm._hooks["svc"]["on_fail"]) == 1

    def test_hooks_for_nonexistent_component(self, lm):
        """可以为未注册的组件添加钩子。"""
        lm.on_start("ghost", lambda n: None)
        lm.on_stop("ghost", lambda n: None)
        lm.on_fail("ghost", lambda n: None)
        assert len(lm._hooks["ghost"]["on_start"]) == 1
        assert len(lm._hooks["ghost"]["on_stop"]) == 1
        assert len(lm._hooks["ghost"]["on_fail"]) == 1

    # ── list_states ───────────────────────────────────────────────────────

    def test_list_states_returns_dict_of_state_values(self, lm):
        """list_states() 返回 name→state_value 字典。"""
        lm.register("a")
        lm.register("b")
        lm.set_state("a", ComponentState.READY)
        assert lm.list_states() == {"a": "ready", "b": "uninitialized"}

    def test_list_states_empty(self, lm):
        """空管理器 list_states() 返回空字典。"""
        assert lm.list_states() == {}

    # ── summary ───────────────────────────────────────────────────────────

    def test_summary_returns_total_and_by_state(self, lm):
        """summary() 返回 total 和 by_state 计数。"""
        lm.register("a")
        lm.register("b")
        lm.set_state("a", ComponentState.READY)

        s = lm.summary()
        assert s["total"] == 2
        assert s["by_state"]["ready"] == 1
        assert s["by_state"]["uninitialized"] == 1
        assert s["by_state"]["stopped"] == 0

    def test_summary_with_multiple_states(self, lm):
        """summary() 多种状态正确计数。"""
        lm.register("a")
        lm.register("b")
        lm.register("c")
        lm.register("d")
        lm.set_state("a", ComponentState.READY)
        lm.set_state("b", ComponentState.STOPPED)
        lm.set_state("c", ComponentState.FAILED)
        lm.set_state("d", ComponentState.DEGRADED)

        s = lm.summary()
        assert s["total"] == 4
        assert s["by_state"]["ready"] == 1
        assert s["by_state"]["stopped"] == 1
        assert s["by_state"]["failed"] == 1
        assert s["by_state"]["degraded"] == 1
        assert s["by_state"]["uninitialized"] == 0

    def test_summary_empty(self, lm):
        """空管理器 summary() 返回 total=0。"""
        s = lm.summary()
        assert s["total"] == 0
        assert sum(s["by_state"].values()) == 0


# ══════════════════════════════════════════════════════════════════════════════
# ComponentRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestComponentRegistry:
    """ComponentRegistry 单例测试。"""

    # ── Singleton ─────────────────────────────────────────────────────────

    def test_singleton_pattern(self):
        """ComponentRegistry 是单例。"""
        a = ComponentRegistry()
        b = ComponentRegistry()
        assert a is b

    def test_singleton_same_instance_via_get_registry(self):
        """get_registry() 返回同一个 ComponentRegistry 实例。"""
        a = ComponentRegistry()
        b = get_registry()
        assert a is b

    def test_get_registry_returns_singleton(self):
        """get_registry() 返回 ComponentRegistry 实例。"""
        reg = get_registry()
        assert isinstance(reg, ComponentRegistry)

    # ── register ──────────────────────────────────────────────────────────

    def test_register_with_component(self):
        """register() 直接注册组件。"""
        reg = get_registry()
        obj = object()
        result = reg.register("my_obj", obj)
        assert result is obj
        assert reg.get("my_obj") is obj

    def test_register_as_decorator(self):
        """register() 作为装饰器使用。"""
        reg = get_registry()

        @reg.register("my_func")
        def my_func():
            return 42

        assert reg.get("my_func") is my_func
        assert reg.get("my_func")() == 42

    def test_register_with_aliases(self):
        """register() 直接注册时设置别名。"""
        reg = get_registry()
        obj = object()
        reg.register("db", obj, aliases=["database", "datastore"])
        assert reg.get("db") is obj
        assert reg.get("database") is obj
        assert reg.get("datastore") is obj

    def test_register_decorator_with_aliases(self):
        """register() 装饰器模式下设置别名。"""
        reg = get_registry()

        @reg.register("calc", aliases=["calculator", "c"])
        def calc():
            return 100

        assert reg.get("calc") is calc
        assert reg.get("calculator") is calc
        assert reg.get("c") is calc

    def test_register_decorator_returns_original(self):
        """装饰器返回原始可调用对象。"""
        reg = get_registry()

        @reg.register("my_cls")
        class MyCls:
            pass

        assert MyCls.__name__ == "MyCls"

    # ── get ───────────────────────────────────────────────────────────────

    def test_get_returns_component(self):
        """get() 返回已注册的组件。"""
        reg = get_registry()
        obj = object()
        reg.register("x", obj)
        assert reg.get("x") is obj

    def test_get_via_alias(self):
        """get() 通过别名获取组件。"""
        reg = get_registry()
        obj = object()
        reg.register("original", obj, aliases=["alias"])
        assert reg.get("alias") is obj

    def test_get_nonexistent_raises_keyerror(self):
        """get() 对不存在的组件抛出 KeyError。"""
        reg = get_registry()
        with pytest.raises(KeyError, match="Component not found"):
            reg.get("nonexistent")

    def test_get_nonexistent_alias_raises_keyerror(self):
        """get() 对不存在的别名抛出 KeyError。"""
        reg = get_registry()
        with pytest.raises(KeyError, match="Component not found"):
            reg.get("no_such_alias")

    # ── has ───────────────────────────────────────────────────────────────

    def test_has_returns_true(self):
        """has() 对已注册组件返回 True。"""
        reg = get_registry()
        reg.register("svc", object())
        assert reg.has("svc") is True

    def test_has_returns_true_via_alias(self):
        """has() 通过别名返回 True。"""
        reg = get_registry()
        reg.register("svc", object(), aliases=["s"])
        assert reg.has("s") is True

    def test_has_returns_false(self):
        """has() 对未注册组件返回 False。"""
        reg = get_registry()
        assert reg.has("missing") is False

    # ── list_all ──────────────────────────────────────────────────────────

    def test_list_all_returns_sorted_names(self):
        """list_all() 返回排序后的组件名列表。"""
        reg = get_registry()
        reg.register("c", 1)
        reg.register("a", 2)
        reg.register("b", 3)
        assert reg.list_all() == ["a", "b", "c"]

    def test_list_all_empty(self):
        """空注册表 list_all() 返回 []。"""
        reg = get_registry()
        assert reg.list_all() == []

    def test_list_all_excludes_aliases(self):
        """list_all() 不含别名。"""
        reg = get_registry()
        reg.register("db", object(), aliases=["database"])
        assert reg.list_all() == ["db"]

    # ── resolve_deps ──────────────────────────────────────────────────────

    def test_resolve_deps_with_type_annotations(self):
        """resolve_deps() 基于类型注解解析依赖。"""
        reg = get_registry()

        class Database:
            pass

        class Cache:
            pass

        db = Database()
        cache = Cache()
        reg.register("Database", db)
        reg.register("Cache", cache)

        def service(db: Database, cache: Cache):
            pass

        resolved = reg.resolve_deps(service)
        assert resolved == {"db": db, "cache": cache}

    def test_resolve_deps_with_no_annotations(self):
        """resolve_deps() 无类型注解时返回空字典。"""
        reg = get_registry()

        def service(a, b):
            pass

        resolved = reg.resolve_deps(service)
        assert resolved == {}

    def test_resolve_deps_with_no_matching_types(self):
        """resolve_deps() 函数参数类型未注册时返回空字典。"""
        reg = get_registry()

        class UnknownService:
            pass

        def service(svc: UnknownService):
            pass

        resolved = reg.resolve_deps(service)
        assert resolved == {}

    def test_resolve_deps_with_annotation_no_name_attr(self):
        """resolve_deps() 处理没有 __name__ 属性的类型注解（如 typing.List[int]）。"""
        reg = get_registry()

        def service(items: typing.List[int]):
            pass

        resolved = reg.resolve_deps(service)
        assert resolved == {}

    def test_resolve_deps_partial_match(self):
        """resolve_deps() 只解析已注册的类型。"""
        reg = get_registry()

        class Database:
            pass

        db = Database()
        reg.register("Database", db)

        def service(db: Database, unknown: int, plain):
            pass

        resolved = reg.resolve_deps(service)
        assert resolved == {"db": db}
        assert "unknown" not in resolved
        assert "plain" not in resolved

    # ── clear ─────────────────────────────────────────────────────────────

    def test_clear_removes_all(self):
        """clear() 移除所有组件和别名。"""
        reg = get_registry()
        reg.register("a", object(), aliases=["aa"])
        reg.register("b", object())
        reg.clear()
        assert reg.list_all() == []
        assert reg.has("a") is False
        assert reg.has("aa") is False
        assert reg.has("b") is False

    # ── get_lifecycle ─────────────────────────────────────────────────────

    def test_get_lifecycle_returns_lifecycle_manager(self):
        """get_lifecycle() 返回 LifecycleManager 实例。"""
        reg = get_registry()
        lc = reg.get_lifecycle()
        assert isinstance(lc, LifecycleManager)

    def test_get_lifecycle_returns_same_instance(self):
        """get_lifecycle() 多次调用返回同一实例。"""
        reg = get_registry()
        lc1 = reg.get_lifecycle()
        lc2 = reg.get_lifecycle()
        assert lc1 is lc2

    # ── register_with_lifecycle ───────────────────────────────────────────

    def test_register_with_lifecycle_basic(self):
        """register_with_lifecycle() 注册组件并设为 READY。"""
        reg = get_registry()
        reg.get_lifecycle()  # 确保 lifecycle 存在
        obj = object()
        result = reg.register_with_lifecycle("svc", obj)
        assert result is obj
        assert reg.get("svc") is obj
        lc = reg.get_lifecycle()
        assert lc.get_state("svc") == ComponentState.READY

    def test_register_with_lifecycle_with_on_start(self):
        """register_with_lifecycle() 注册 on_start 钩子。"""
        reg = get_registry()
        reg.get_lifecycle()
        started = []

        result = reg.register_with_lifecycle(
            "svc", object(), on_start=lambda n: started.append(n)
        )
        assert result is not None
        lc = reg.get_lifecycle()
        assert lc.get_state("svc") == ComponentState.READY
        assert len(lc._hooks["svc"]["on_start"]) == 1

    def test_register_with_lifecycle_with_on_stop(self):
        """register_with_lifecycle() 注册 on_stop 钩子。"""
        reg = get_registry()
        reg.get_lifecycle()
        stopped = []

        result = reg.register_with_lifecycle(
            "svc", object(), on_stop=lambda n: stopped.append(n)
        )
        assert result is not None
        lc = reg.get_lifecycle()
        assert len(lc._hooks["svc"]["on_stop"]) == 1

    def test_register_with_lifecycle_without_lifecycle_manager(self):
        """register_with_lifecycle() 未初始化 lifecycle 时仍可注册组件。"""
        reg = get_registry()
        reg._lifecycle = None
        obj = object()
        result = reg.register_with_lifecycle("svc", obj)
        assert result is obj
        assert reg.get("svc") is obj

    def test_register_with_lifecycle_no_hooks(self):
        """register_with_lifecycle() 无钩子时正常注册。"""
        reg = get_registry()
        reg.get_lifecycle()
        result = reg.register_with_lifecycle("no_hooks", 42)
        assert result == 42
        assert reg.get("no_hooks") == 42
        assert reg.get_lifecycle().get_state("no_hooks") == ComponentState.READY


# ══════════════════════════════════════════════════════════════════════════════
# Global helpers
# ══════════════════════════════════════════════════════════════════════════════

class TestGlobalHelpers:
    """get_registry() 和 component() 全局助手测试。"""

    def test_get_registry_returns_singleton(self):
        """get_registry() 返回单例。"""
        a = get_registry()
        b = get_registry()
        assert a is b
        assert isinstance(a, ComponentRegistry)

    def test_component_decorator_registers_component(self):
        """component() 装饰器注册组件。"""
        @component("my_service")
        def my_service():
            return "hello"

        reg = get_registry()
        assert reg.get("my_service") is my_service
        assert my_service() == "hello"

    def test_component_decorator_with_aliases(self):
        """component() 装饰器支持别名。"""
        @component("svc", aliases=["service", "s"])
        class Service:
            pass

        reg = get_registry()
        assert reg.get("svc") is Service
        assert reg.get("service") is Service
        assert reg.get("s") is Service

    def test_component_decorator_returns_original(self):
        """component() 装饰器返回原始可调用对象。"""
        @component("x")
        class X:
            pass

        assert X.__name__ == "X"


# ══════════════════════════════════════════════════════════════════════════════
# Edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """边界情况测试。"""

    def test_resolve_deps_no_matching_types(self):
        """resolve_deps() 函数参数类型未注册时返回空。"""
        reg = get_registry()

        class UnknownService:
            pass

        def service(svc: UnknownService):
            pass

        resolved = reg.resolve_deps(service)
        assert resolved == {}

    def test_register_with_lifecycle_without_lifecycle(self):
        """register_with_lifecycle() 无 lifecycle 时仍返回组件。"""
        reg = get_registry()
        reg._lifecycle = None
        obj = object()
        result = reg.register_with_lifecycle("svc", obj)
        assert result is obj

    def test_set_state_to_same_state_does_not_trigger_on_start(self):
        """set_state() READY→READY 不触发 on_start。"""
        lm = LifecycleManager()
        lm.register("svc")
        calls = []
        lm.on_start("svc", lambda n: calls.append("start"))
        lm.set_state("svc", ComponentState.READY)
        lm.set_state("svc", ComponentState.READY)
        assert calls == ["start"]

    def test_hooks_for_nonexistent_component(self):
        """为未注册的组件添加钩子。"""
        lm = LifecycleManager()
        lm.on_start("ghost", lambda n: None)
        lm.on_stop("ghost", lambda n: None)
        lm.on_fail("ghost", lambda n: None)
        assert len(lm._hooks["ghost"]["on_start"]) == 1
        assert len(lm._hooks["ghost"]["on_stop"]) == 1
        assert len(lm._hooks["ghost"]["on_fail"]) == 1

    def test_register_duplicate_overwrites(self):
        """重复注册同名组件覆盖旧值。"""
        reg = get_registry()
        a = object()
        b = object()
        reg.register("dup", a)
        reg.register("dup", b)
        assert reg.get("dup") is b

    def test_clear_and_reuse(self):
        """clear() 后注册表可复用。"""
        reg = get_registry()
        reg.register("a", 1)
        reg.clear()
        reg.register("a", 2)
        assert reg.get("a") == 2

    def test_many_components(self):
        """注册大量组件。"""
        reg = get_registry()
        for i in range(50):
            reg.register(f"comp_{i}", i)
        assert len(reg.list_all()) == 50
        assert reg.get("comp_0") == 0
        assert reg.get("comp_49") == 49

    def test_full_lifecycle_flow(self):
        """完整生命周期：UNINITIALIZED→INITIALIZING→READY→DEGRADED→STOPPED。"""
        lm = LifecycleManager()
        events = []

        def record(evt):
            return lambda name: events.append(f"{evt}:{name}")

        lm.register("app")
        lm.on_start("app", record("start"))
        lm.on_stop("app", record("stop"))
        lm.on_fail("app", record("fail"))

        lm.set_state("app", ComponentState.INITIALIZING)
        lm.set_state("app", ComponentState.READY)
        lm.set_state("app", ComponentState.DEGRADED)
        lm.set_state("app", ComponentState.STOPPED)

        assert events == ["start:app", "stop:app"]
        assert lm.get_state("app") == ComponentState.STOPPED