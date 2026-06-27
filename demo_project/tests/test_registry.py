#!/usr/bin/env python3
"""
test_registry.py — 组件注册中心全面测试
覆盖 tengod.比肩_架构协同.registry 模块的所有公共 API。
"""

import threading
import pytest
from unittest.mock import patch, MagicMock

from tengod.比肩_架构协同.registry import (
    ComponentRegistry,
    ComponentState,
    LifecycleManager,
    component,
    get_registry,
)


# ══════════════════════════════════════════════════════════════════════════════
# ComponentState 枚举测试
# ══════════════════════════════════════════════════════════════════════════════

class TestComponentState:
    """ComponentState 枚举值测试"""

    def test_all_enum_values(self):
        """验证所有枚举值"""
        assert ComponentState.UNINITIALIZED.value == "uninitialized"
        assert ComponentState.INITIALIZING.value == "initializing"
        assert ComponentState.READY.value == "ready"
        assert ComponentState.DEGRADED.value == "degraded"
        assert ComponentState.STOPPED.value == "stopped"
        assert ComponentState.FAILED.value == "failed"

    def test_enum_membership(self):
        """验证枚举成员数量"""
        members = list(ComponentState)
        assert len(members) == 6

    def test_enum_str(self):
        """验证 str(enum) 输出"""
        assert str(ComponentState.READY) == "ComponentState.READY"


# ══════════════════════════════════════════════════════════════════════════════
# LifecycleManager 测试
# ══════════════════════════════════════════════════════════════════════════════

class TestLifecycleManager:
    """LifecycleManager 全覆盖测试"""

    # ── 初始化和注册 ────────────────────────────────────────────────────

    def test_init(self):
        """测试 __init__ 初始化"""
        lm = LifecycleManager()
        assert lm._states == {}
        assert lm._hooks == {}
        assert isinstance(lm._lock, type(threading.Lock()))

    def test_register(self):
        """测试 register()：注册组件并设置初始状态"""
        lm = LifecycleManager()
        lm.register("comp_a")
        assert lm.get_state("comp_a") == ComponentState.UNINITIALIZED
        assert "comp_a" in lm._hooks
        assert lm._hooks["comp_a"]["on_start"] == []
        assert lm._hooks["comp_a"]["on_stop"] == []
        assert lm._hooks["comp_a"]["on_fail"] == []

    def test_register_multiple(self):
        """测试注册多个组件"""
        lm = LifecycleManager()
        lm.register("a")
        lm.register("b")
        lm.register("c")
        assert len(lm._states) == 3

    def test_register_duplicate(self):
        """测试重复注册：覆盖之前的状态"""
        lm = LifecycleManager()
        lm.register("svc")
        lm.set_state("svc", ComponentState.READY)
        assert lm.get_state("svc") == ComponentState.READY
        lm.register("svc")  # 重新注册，重置为 UNINITIALIZED
        assert lm.get_state("svc") == ComponentState.UNINITIALIZED

    # ── get_state ───────────────────────────────────────────────────────

    def test_get_state_existing(self):
        """测试 get_state() 获取已注册组件状态"""
        lm = LifecycleManager()
        lm.register("svc")
        lm.set_state("svc", ComponentState.READY)
        assert lm.get_state("svc") == ComponentState.READY

    def test_get_state_nonexistent(self):
        """测试 get_state() 对未注册组件返回默认值"""
        lm = LifecycleManager()
        assert lm.get_state("nonexistent") == ComponentState.UNINITIALIZED

    # ── set_state 触发钩子 ──────────────────────────────────────────────

    def test_set_state_triggers_on_start(self):
        """测试 set_state(READY) 触发 on_start 钩子"""
        lm = LifecycleManager()
        lm.register("svc")
        calls = []
        lm.on_start("svc", lambda n: calls.append(("start", n)))
        lm.set_state("svc", ComponentState.READY)
        assert calls == [("start", "svc")]

    def test_set_state_no_duplicate_on_start(self):
        """测试 READY→READY 不重复触发 on_start"""
        lm = LifecycleManager()
        lm.register("svc")
        calls = []
        lm.on_start("svc", lambda n: calls.append("start"))
        lm.set_state("svc", ComponentState.READY)
        lm.set_state("svc", ComponentState.READY)  # 不应再次触发
        assert calls == ["start"]

    def test_set_state_triggers_on_stop(self):
        """测试 set_state(STOPPED) 触发 on_stop 钩子"""
        lm = LifecycleManager()
        lm.register("svc")
        calls = []
        lm.on_stop("svc", lambda n: calls.append(("stop", n)))
        lm.set_state("svc", ComponentState.STOPPED)
        assert calls == [("stop", "svc")]

    def test_set_state_triggers_on_fail(self):
        """测试 set_state(FAILED) 触发 on_fail 钩子"""
        lm = LifecycleManager()
        lm.register("svc")
        calls = []
        lm.on_fail("svc", lambda n: calls.append(("fail", n)))
        lm.set_state("svc", ComponentState.FAILED)
        assert calls == [("fail", "svc")]

    def test_set_state_hook_exception_suppressed(self):
        """测试钩子中抛出异常被静默吞掉"""
        lm = LifecycleManager()
        lm.register("svc")
        lm.on_start("svc", lambda n: 1 / 0)
        lm.on_stop("svc", lambda n: 1 / 0)
        lm.on_fail("svc", lambda n: 1 / 0)
        # 不应该抛出异常
        lm.set_state("svc", ComponentState.READY)
        lm.set_state("svc", ComponentState.STOPPED)
        lm.set_state("svc", ComponentState.FAILED)
        assert lm.get_state("svc") == ComponentState.FAILED

    def test_set_state_degraded_no_hooks(self):
        """测试 DEGRADED 状态不触发任何钩子"""
        lm = LifecycleManager()
        lm.register("svc")
        calls = []
        lm.on_start("svc", lambda n: calls.append("start"))
        lm.on_stop("svc", lambda n: calls.append("stop"))
        lm.on_fail("svc", lambda n: calls.append("fail"))
        lm.set_state("svc", ComponentState.DEGRADED)
        assert calls == []

    def test_set_state_initializing_no_hooks(self):
        """测试 INITIALIZING 状态不触发任何钩子"""
        lm = LifecycleManager()
        lm.register("svc")
        calls = []
        lm.on_start("svc", lambda n: calls.append("start"))
        lm.on_stop("svc", lambda n: calls.append("stop"))
        lm.set_state("svc", ComponentState.INITIALIZING)
        assert calls == []

    def test_set_state_uninitialized_no_hooks(self):
        """测试 UNINITIALIZED 状态不触发任何钩子"""
        lm = LifecycleManager()
        lm.register("svc")
        calls = []
        lm.on_start("svc", lambda n: calls.append("start"))
        lm.on_stop("svc", lambda n: calls.append("stop"))
        lm.set_state("svc", ComponentState.UNINITIALIZED)
        assert calls == []

    def test_set_state_unknown_component_no_hooks(self):
        """测试对未注册组件 set_state 不会触发钩子"""
        lm = LifecycleManager()
        calls = []
        lm.set_state("unknown", ComponentState.READY)
        lm.set_state("unknown", ComponentState.STOPPED)
        lm.set_state("unknown", ComponentState.FAILED)
        assert calls == []  # 没有钩子注册，也不会崩溃

    def test_set_state_from_ready_to_stop(self):
        """测试 READY→STOPPED 不触发 on_start，但触发 on_stop"""
        lm = LifecycleManager()
        lm.register("svc")
        start_calls = []
        stop_calls = []
        lm.on_start("svc", lambda n: start_calls.append(n))
        lm.on_stop("svc", lambda n: stop_calls.append(n))
        lm.set_state("svc", ComponentState.READY)
        assert start_calls == ["svc"]
        lm.set_state("svc", ComponentState.STOPPED)
        assert stop_calls == ["svc"]
        assert len(start_calls) == 1  # 没有重复触发

    def test_set_state_multiple_hooks(self):
        """测试多个钩子依次触发"""
        lm = LifecycleManager()
        lm.register("svc")
        calls = []
        lm.on_start("svc", lambda n: calls.append("h1"))
        lm.on_start("svc", lambda n: calls.append("h2"))
        lm.set_state("svc", ComponentState.READY)
        assert calls == ["h1", "h2"]

    # ── on_start / on_stop / on_fail 方法 ───────────────────────────────

    def test_on_start_auto_creates_entry(self):
        """测试 on_start() 对未注册组件自动创建 hooks 条目"""
        lm = LifecycleManager()
        lm.on_start("new_svc", lambda n: None)
        assert len(lm._hooks["new_svc"]["on_start"]) == 1

    def test_on_stop_auto_creates_entry(self):
        """测试 on_stop() 对未注册组件自动创建 hooks 条目"""
        lm = LifecycleManager()
        lm.on_stop("new_svc", lambda n: None)
        assert len(lm._hooks["new_svc"]["on_stop"]) == 1

    def test_on_fail_auto_creates_entry(self):
        """测试 on_fail() 对未注册组件自动创建 hooks 条目"""
        lm = LifecycleManager()
        lm.on_fail("new_svc", lambda n: None)
        assert len(lm._hooks["new_svc"]["on_fail"]) == 1

    def test_on_start_multiple_hooks(self):
        """测试多次 on_start() 追加多个钩子"""
        lm = LifecycleManager()
        lm.register("svc")
        lm.on_start("svc", lambda n: None)
        lm.on_start("svc", lambda n: None)
        assert len(lm._hooks["svc"]["on_start"]) == 2

    # ── list_states ─────────────────────────────────────────────────────

    def test_list_states(self):
        """测试 list_states() 返回所有组件状态"""
        lm = LifecycleManager()
        lm.register("a")
        lm.register("b")
        lm.set_state("a", ComponentState.READY)
        states = lm.list_states()
        assert states == {"a": "ready", "b": "uninitialized"}

    def test_list_states_empty(self):
        """测试空 LifecycleManager 的 list_states()"""
        lm = LifecycleManager()
        assert lm.list_states() == {}

    # ── summary ─────────────────────────────────────────────────────────

    def test_summary(self):
        """测试 summary() 统计信息"""
        lm = LifecycleManager()
        lm.register("a")
        lm.register("b")
        lm.register("c")
        lm.set_state("a", ComponentState.READY)
        lm.set_state("b", ComponentState.READY)
        s = lm.summary()
        assert s["total"] == 3
        assert s["by_state"]["ready"] == 2
        assert s["by_state"]["uninitialized"] == 1

    def test_summary_empty(self):
        """测试空 LifecycleManager 的 summary()"""
        lm = LifecycleManager()
        s = lm.summary()
        assert s["total"] == 0
        for state in ComponentState:
            assert s["by_state"][state.value] == 0

    def test_summary_all_states(self):
        """测试 summary() 覆盖所有状态类型"""
        lm = LifecycleManager()
        state_map = {
            "a": ComponentState.UNINITIALIZED,
            "b": ComponentState.INITIALIZING,
            "c": ComponentState.READY,
            "d": ComponentState.DEGRADED,
            "e": ComponentState.STOPPED,
            "f": ComponentState.FAILED,
        }
        for name, state in state_map.items():
            lm.register(name)
            lm.set_state(name, state)
        s = lm.summary()
        assert s["total"] == 6
        for state in ComponentState:
            assert s["by_state"][state.value] == 1


# ══════════════════════════════════════════════════════════════════════════════
# ComponentRegistry 单例测试
# ══════════════════════════════════════════════════════════════════════════════

class TestComponentRegistrySingleton:
    """ComponentRegistry 单例行为测试"""

    def test_singleton_same_instance(self):
        """测试多次实例化返回同一个对象"""
        r1 = ComponentRegistry()
        r2 = ComponentRegistry()
        assert r1 is r2

    def test_clear_between_tests_isolation(self):
        """测试 clear() 确保测试隔离"""
        r = ComponentRegistry()
        r.clear()
        r.register("x", 1)
        assert r.has("x")
        r.clear()
        assert not r.has("x")


# ══════════════════════════════════════════════════════════════════════════════
# ComponentRegistry 注册测试
# ══════════════════════════════════════════════════════════════════════════════

class TestComponentRegistryRegister:
    """ComponentRegistry.register() 测试"""

    def test_register_direct(self):
        """测试直接注册组件"""
        r = ComponentRegistry()
        r.clear()
        obj = {"key": "value"}
        result = r.register("my_comp", obj)
        assert result is obj
        assert r.has("my_comp")
        assert r.get("my_comp") is obj

    def test_register_decorator(self):
        """测试装饰器模式注册"""
        r = ComponentRegistry()
        r.clear()

        @r.register("deco_class")
        class MyClass:
            pass

        assert r.has("deco_class")
        assert r.get("deco_class") is MyClass

    def test_register_decorator_with_aliases(self):
        """测试装饰器注册带别名"""
        r = ComponentRegistry()
        r.clear()

        @r.register("deco_comp", aliases=["dc", "dcomp"])
        class DecoComp:
            pass

        assert r.has("deco_comp")
        assert r.has("dc")
        assert r.has("dcomp")
        assert r.get("dc") is DecoComp

    def test_register_direct_with_aliases(self):
        """测试直接注册带别名"""
        r = ComponentRegistry()
        r.clear()
        obj = object()
        r.register("direct_comp", obj, aliases=["dir", "dc2"])
        assert r.has("direct_comp")
        assert r.has("dir")
        assert r.has("dc2")
        assert r.get("dir") is obj

    def test_register_direct_no_aliases(self):
        """测试直接注册不带别名"""
        r = ComponentRegistry()
        r.clear()
        r.register("no_alias", 42)
        assert r.has("no_alias")
        assert r.get("no_alias") == 42

    def test_register_overwrite(self):
        """测试重复注册覆盖旧值"""
        r = ComponentRegistry()
        r.clear()
        r.register("comp", "old")
        r.register("comp", "new")
        assert r.get("comp") == "new"

    def test_register_none_component_rejected(self):
        """测试 register(component=None) 进入装饰器模式，而非注册 None"""
        r = ComponentRegistry()
        r.clear()
        # 当 component=None 时，register 进入装饰器模式，返回装饰器
        decorator = r.register("none_comp", None)
        assert callable(decorator)
        # 未实际注册
        assert not r.has("none_comp")
        # 调用装饰器完成注册
        obj = object()
        result = decorator(obj)
        assert result is obj
        assert r.has("none_comp")
        assert r.get("none_comp") is obj

    def test_register_empty_string_name(self):
        """测试空字符串名称注册"""
        r = ComponentRegistry()
        r.clear()
        r.register("", "empty_name")
        assert r.has("")
        assert r.get("") == "empty_name"

    def test_register_empty_aliases_list(self):
        """测试空别名列表注册"""
        r = ComponentRegistry()
        r.clear()
        r.register("comp", object(), aliases=[])
        assert r.has("comp")
        assert r.list_all() == ["comp"]


# ══════════════════════════════════════════════════════════════════════════════
# ComponentRegistry 查询测试
# ══════════════════════════════════════════════════════════════════════════════

class TestComponentRegistryQuery:
    """ComponentRegistry.get() / has() / list_all() 测试"""

    def test_get_existing(self):
        """测试获取已注册组件"""
        r = ComponentRegistry()
        r.clear()
        obj = object()
        r.register("comp", obj)
        assert r.get("comp") is obj

    def test_get_via_alias(self):
        """测试通过别名获取组件"""
        r = ComponentRegistry()
        r.clear()
        obj = object()
        r.register("comp", obj, aliases=["alias1", "alias2"])
        assert r.get("alias1") is obj
        assert r.get("alias2") is obj

    def test_get_raises_keyerror(self):
        """测试获取不存在的组件抛出 KeyError"""
        r = ComponentRegistry()
        r.clear()
        with pytest.raises(KeyError, match="Component not found"):
            r.get("nonexistent")

    def test_get_raises_keyerror_for_invalid_alias(self):
        """测试通过不存在的别名获取抛出 KeyError"""
        r = ComponentRegistry()
        r.clear()
        with pytest.raises(KeyError, match="Component not found"):
            r.get("invalid_alias")

    def test_has_existing(self):
        """测试 has() 检查已注册组件"""
        r = ComponentRegistry()
        r.clear()
        r.register("comp", 1)
        assert r.has("comp") is True

    def test_has_nonexistent(self):
        """测试 has() 检查不存在的组件"""
        r = ComponentRegistry()
        r.clear()
        assert r.has("nonexistent") is False

    def test_has_via_alias(self):
        """测试 has() 通过别名检查"""
        r = ComponentRegistry()
        r.clear()
        r.register("comp", 1, aliases=["a1"])
        assert r.has("a1") is True

    def test_has_invalid_alias(self):
        """测试 has() 无效别名返回 False"""
        r = ComponentRegistry()
        r.clear()
        assert r.has("invalid") is False

    def test_list_all_sorted(self):
        """测试 list_all() 返回排序后的列表"""
        r = ComponentRegistry()
        r.clear()
        r.register("c", 1)
        r.register("a", 2)
        r.register("b", 3)
        assert r.list_all() == ["a", "b", "c"]

    def test_list_all_empty(self):
        """测试空注册表的 list_all()"""
        r = ComponentRegistry()
        r.clear()
        assert r.list_all() == []

    def test_list_all_excludes_aliases(self):
        """测试 list_all() 不包含别名"""
        r = ComponentRegistry()
        r.clear()
        r.register("comp", 1, aliases=["a1", "a2"])
        assert r.list_all() == ["comp"]


# ══════════════════════════════════════════════════════════════════════════════
# ComponentRegistry resolve_deps 测试
# ══════════════════════════════════════════════════════════════════════════════

class TestComponentRegistryResolveDeps:
    """ComponentRegistry.resolve_deps() 测试"""

    def test_resolve_deps_basic(self):
        """测试基本类型注解依赖解析"""
        r = ComponentRegistry()
        r.clear()

        class HttpClient:
            pass

        class Database:
            pass

        r.register("HttpClient", HttpClient())
        r.register("Database", Database())

        def my_func(http_client: HttpClient, db: Database, plain):
            pass

        resolved = r.resolve_deps(my_func)
        assert "http_client" in resolved
        assert "db" in resolved
        assert "plain" not in resolved
        assert isinstance(resolved["http_client"], HttpClient)
        assert isinstance(resolved["db"], Database)

    def test_resolve_deps_no_annotations(self):
        """测试无类型注解的函数"""
        r = ComponentRegistry()
        r.clear()

        def no_annotations(a, b):
            pass

        resolved = r.resolve_deps(no_annotations)
        assert resolved == {}

    def test_resolve_deps_all_annotations_missing(self):
        """测试所有类型注解无对应组件"""
        r = ComponentRegistry()
        r.clear()

        class NotRegistered:
            pass

        def my_func(x: NotRegistered):
            pass

        resolved = r.resolve_deps(my_func)
        assert resolved == {}

    def test_resolve_deps_mixed(self):
        """测试部分注解可解析、部分不可解析"""
        r = ComponentRegistry()
        r.clear()

        class Known:
            pass

        class Unknown:
            pass

        r.register("Known", Known())

        def my_func(k: Known, u: Unknown):
            pass

        resolved = r.resolve_deps(my_func)
        assert "k" in resolved
        assert "u" not in resolved
        assert isinstance(resolved["k"], Known)

    def test_resolve_deps_annotation_without_name(self):
        """测试类型注解没有 __name__ 属性（如字符串注解）"""
        r = ComponentRegistry()
        r.clear()

        def my_func(x: "SomeType"):
            pass

        # "SomeType" 没有注册，所以不会解析
        resolved = r.resolve_deps(my_func)
        assert resolved == {}

    def test_resolve_deps_default_values(self):
        """测试带默认值的参数"""
        r = ComponentRegistry()
        r.clear()

        class Service:
            pass

        r.register("Service", Service())

        def my_func(svc: Service = None):
            pass

        resolved = r.resolve_deps(my_func)
        assert "svc" in resolved


# ══════════════════════════════════════════════════════════════════════════════
# ComponentRegistry clear 测试
# ══════════════════════════════════════════════════════════════════════════════

class TestComponentRegistryClear:
    """ComponentRegistry.clear() 测试"""

    def test_clear_removes_all_components(self):
        """测试 clear() 移除所有组件"""
        r = ComponentRegistry()
        r.clear()
        r.register("a", 1)
        r.register("b", 2)
        r.clear()
        assert r.list_all() == []
        assert not r.has("a")
        assert not r.has("b")

    def test_clear_removes_aliases(self):
        """测试 clear() 同时移除别名"""
        r = ComponentRegistry()
        r.clear()
        r.register("comp", 1, aliases=["a1", "a2"])
        r.clear()
        assert not r.has("a1")
        assert not r.has("a2")
        with pytest.raises(KeyError):
            r.get("a1")

    def test_clear_idempotent(self):
        """测试 clear() 幂等性"""
        r = ComponentRegistry()
        r.clear()
        r.clear()  # 第二次调用不应出错
        assert r.list_all() == []


# ══════════════════════════════════════════════════════════════════════════════
# ComponentRegistry 生命周期集成测试
# ══════════════════════════════════════════════════════════════════════════════

class TestComponentRegistryLifecycle:
    """ComponentRegistry.get_lifecycle() / register_with_lifecycle() 测试"""

    def test_get_lifecycle_lazy_init(self):
        """测试 get_lifecycle() 懒初始化"""
        r = ComponentRegistry()
        r.clear()
        r._lifecycle = None
        lc = r.get_lifecycle()
        assert isinstance(lc, LifecycleManager)

    def test_get_lifecycle_singleton(self):
        """测试 get_lifecycle() 返回同一个实例"""
        r = ComponentRegistry()
        r.clear()
        r._lifecycle = None
        lc1 = r.get_lifecycle()
        lc2 = r.get_lifecycle()
        assert lc1 is lc2

    def test_register_with_lifecycle_basic(self):
        """测试 register_with_lifecycle() 基本用法"""
        r = ComponentRegistry()
        r.clear()
        r._lifecycle = None
        lc = r.get_lifecycle()

        start_calls = []
        stop_calls = []

        result = r.register_with_lifecycle(
            "lifecycle_comp",
            {"data": 42},
            on_start=lambda n: start_calls.append(n),
            on_stop=lambda n: stop_calls.append(n),
        )

        assert result is not None
        assert lc.get_state("lifecycle_comp") == ComponentState.READY
        assert len(lc._hooks["lifecycle_comp"]["on_start"]) == 1
        assert len(lc._hooks["lifecycle_comp"]["on_stop"]) == 1

    def test_register_with_lifecycle_no_hooks(self):
        """测试 register_with_lifecycle() 无钩子"""
        r = ComponentRegistry()
        r.clear()
        r._lifecycle = None
        r.get_lifecycle()

        result = r.register_with_lifecycle("no_hooks", 42)
        assert result == 42
        assert r.get("no_hooks") == 42
        assert r.get_lifecycle().get_state("no_hooks") == ComponentState.READY

    def test_register_with_lifecycle_returns_component(self):
        """测试 register_with_lifecycle() 返回注册的组件"""
        r = ComponentRegistry()
        r.clear()
        r._lifecycle = None
        r.get_lifecycle()

        obj = object()
        result = r.register_with_lifecycle("ret_comp", obj)
        assert result is obj

    def test_register_with_lifecycle_when_lifecycle_none(self):
        """测试 _lifecycle 为 None 时 register_with_lifecycle 不触发生命周期"""
        r = ComponentRegistry()
        r.clear()
        r._lifecycle = None  # 不调用 get_lifecycle()

        result = r.register_with_lifecycle(
            "nolc_comp",
            "value",
            on_start=lambda n: None,
            on_stop=lambda n: None,
        )
        # 仍应成功注册组件
        assert result == "value"
        assert r.has("nolc_comp")
        # 但 lifecycle 没有初始化
        assert r._lifecycle is None


# ══════════════════════════════════════════════════════════════════════════════
# 模块级函数测试
# ══════════════════════════════════════════════════════════════════════════════

class TestModuleFunctions:
    """get_registry() / component() 模块级函数测试"""

    def test_get_registry_returns_singleton(self):
        """测试 get_registry() 返回 ComponentRegistry 单例"""
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2
        assert isinstance(r1, ComponentRegistry)

    def test_component_decorator(self):
        """测试 component() 装饰器"""
        r = ComponentRegistry()
        r.clear()

        @component("mod_comp", aliases=["mc"])
        class ModComp:
            pass

        assert r.has("mod_comp")
        assert r.has("mc")
        assert r.get("mc") is ModComp

    def test_component_decorator_no_aliases(self):
        """测试 component() 装饰器不带别名"""
        r = ComponentRegistry()
        r.clear()

        @component("simple_comp")
        def simple_func():
            pass

        assert r.has("simple_comp")
        assert r.get("simple_comp") is simple_func

    def test_get_registry_is_component_registry(self):
        """测试 get_registry() 返回的确实是 ComponentRegistry"""
        r = get_registry()
        assert isinstance(r, ComponentRegistry)


# ══════════════════════════════════════════════════════════════════════════════
# 集成测试
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """集成测试：LifecycleManager + ComponentRegistry 协同"""

    def test_full_lifecycle_flow(self):
        """完整生命周期流程：注册→启动→降级→停止"""
        r = ComponentRegistry()
        r.clear()
        r._lifecycle = None
        lc = r.get_lifecycle()

        events = []

        def record(event):
            return lambda name: events.append(f"{event}:{name}")

        lc.register("app")
        lc.on_start("app", record("start"))
        lc.on_stop("app", record("stop"))
        lc.on_fail("app", record("fail"))

        lc.set_state("app", ComponentState.INITIALIZING)
        lc.set_state("app", ComponentState.READY)
        lc.set_state("app", ComponentState.DEGRADED)
        lc.set_state("app", ComponentState.STOPPED)

        assert events == ["start:app", "stop:app"]
        assert lc.get_state("app") == ComponentState.STOPPED

    def test_registry_with_lifecycle_end_to_end(self):
        """端到端：先注册组件到注册中心，再注册到生命周期管理器"""
        r = ComponentRegistry()
        r.clear()
        r._lifecycle = None
        lc = r.get_lifecycle()

        r.register("app", {"name": "MyApp"})
        lc.register("app")
        lc.set_state("app", ComponentState.READY)

        assert lc.get_state("app") == ComponentState.READY
        assert r.get("app") == {"name": "MyApp"}

    def test_register_with_lifecycle_and_trigger(self):
        """注册带生命周期的组件并触发钩子"""
        r = ComponentRegistry()
        r.clear()
        r._lifecycle = None
        lc = r.get_lifecycle()

        events = []

        r.register_with_lifecycle(
            "svc",
            "service_value",
            on_start=lambda n: events.append(f"started:{n}"),
            on_stop=lambda n: events.append(f"stopped:{n}"),
        )

        # 已在 register_with_lifecycle 中设置 READY
        # 再切到 STOPPED 触发 on_stop
        lc.set_state("svc", ComponentState.STOPPED)
        assert events == ["stopped:svc"]

    def test_multiple_components_lifecycle(self):
        """多个组件的生命周期管理"""
        r = ComponentRegistry()
        r.clear()
        r._lifecycle = None
        lc = r.get_lifecycle()

        for i in range(1, 6):
            r.register_with_lifecycle(f"comp_{i}", i)

        assert len(lc._states) == 5
        s = lc.summary()
        assert s["total"] == 5
        assert s["by_state"]["ready"] == 5


# ══════════════════════════════════════════════════════════════════════════════
# 边界情况与健壮性测试
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """边界情况与健壮性测试"""

    def test_get_state_after_set_state_to_none(self):
        """测试 set_state 到 UNINITIALIZED 后 get_state 正确"""
        lm = LifecycleManager()
        lm.register("svc")
        lm.set_state("svc", ComponentState.READY)
        lm.set_state("svc", ComponentState.UNINITIALIZED)
        assert lm.get_state("svc") == ComponentState.UNINITIALIZED

    def test_register_with_lifecycle_after_clear(self):
        """测试 clear() 后 register_with_lifecycle 仍然正常工作"""
        r = ComponentRegistry()
        r.clear()
        r._lifecycle = None
        r.get_lifecycle()

        r.register_with_lifecycle("comp", 1)
        r.clear()
        # 组件已清空，但 lifecycle 未被清空（clear 不触发生命周期）
        assert not r.has("comp")
        # lifecycle 状态保持不变（clear 不涉及 lifecycle）
        assert r.get_lifecycle().get_state("comp") == ComponentState.READY

    def test_aliases_overwrite(self):
        """测试别名覆盖：新注册覆盖旧别名"""
        r = ComponentRegistry()
        r.clear()
        r.register("comp1", "old", aliases=["shared"])
        r.register("comp2", "new", aliases=["shared"])
        assert r.get("shared") == "new"

    def test_alias_to_alias_chain(self):
        """测试别名链：别名指向另一个别名"""
        r = ComponentRegistry()
        r.clear()
        r.register("comp", "value", aliases=["a1", "a2"])
        # _aliases: {"a1": "comp", "a2": "comp"}
        # get("a1") -> actual_name = "comp" -> _components["comp"]
        assert r.get("a1") == "value"
        assert r.get("a2") == "value"

    def test_register_with_lifecycle_aliases(self):
        """测试 register_with_lifecycle 不支持别名参数"""
        r = ComponentRegistry()
        r.clear()
        r._lifecycle = None
        r.get_lifecycle()

        # register_with_lifecycle 没有 aliases 参数
        result = r.register_with_lifecycle("comp", "data")
        assert result == "data"
        assert r.has("comp")

    def test_module_version(self):
        """测试模块版本号"""
        from tengod.比肩_架构协同 import registry as reg_module
        assert hasattr(reg_module, "__version__")
        assert reg_module.__version__ == "1.4.0"

    def test_module_all(self):
        """测试 __all__ 导出列表"""
        from tengod.比肩_架构协同 import registry as reg_module
        expected = [
            "ComponentRegistry",
            "ComponentState",
            "LifecycleManager",
            "component",
            "get_registry",
        ]
        assert reg_module.__all__ == expected