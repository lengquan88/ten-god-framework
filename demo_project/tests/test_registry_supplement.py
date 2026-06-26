#!/usr/bin/env python3
"""
test_registry_supplement.py — 注册中心补充测试，提升覆盖率至 70%+
"""

import pytest

from tengod.比肩_架构协同.registry import (
    ComponentRegistry,
    ComponentState,
    LifecycleManager,
    component,
    get_registry,
)


# ── LifecycleManager 测试 ──────────────────────────────────────────────

class TestLifecycleManager:
    """LifecycleManager 全覆盖测试"""

    def test_register_and_get_state(self):
        """覆盖 register() 和 get_state()"""
        lm = LifecycleManager()
        lm.register("comp_a")
        assert lm.get_state("comp_a") == ComponentState.UNINITIALIZED
        # 未注册的组件返回默认值
        assert lm.get_state("nonexistent") == ComponentState.UNINITIALIZED

    def test_set_state_triggers_on_start_hook(self):
        """覆盖 set_state 触发 on_start 钩子 (lines 47-52)"""
        lm = LifecycleManager()
        lm.register("svc")
        calls = []

        lm.on_start("svc", lambda n: calls.append(("start", n)))
        lm.set_state("svc", ComponentState.READY)

        assert calls == [("start", "svc")]
        assert lm.get_state("svc") == ComponentState.READY

    def test_set_state_triggers_on_stop_hook(self):
        """覆盖 set_state 触发 on_stop 钩子 (lines 53-58)"""
        lm = LifecycleManager()
        lm.register("svc")
        calls = []

        lm.on_stop("svc", lambda n: calls.append(("stop", n)))
        lm.set_state("svc", ComponentState.STOPPED)

        assert calls == [("stop", "svc")]
        assert lm.get_state("svc") == ComponentState.STOPPED

    def test_set_state_triggers_on_fail_hook(self):
        """覆盖 set_state 触发 on_fail 钩子 (lines 53-58)"""
        lm = LifecycleManager()
        lm.register("svc")
        calls = []

        lm.on_fail("svc", lambda n: calls.append(("fail", n)))
        lm.set_state("svc", ComponentState.FAILED)

        assert calls == [("fail", "svc")]
        assert lm.get_state("svc") == ComponentState.FAILED

    def test_set_state_hook_exception_suppressed(self):
        """覆盖 set_state 中钩子异常被静默吞掉 (lines 49-52, 57-60)"""
        lm = LifecycleManager()
        lm.register("svc")
        lm.on_start("svc", lambda n: 1 / 0)  # 故意抛出异常
        lm.on_stop("svc", lambda n: 1 / 0)
        lm.on_fail("svc", lambda n: 1 / 0)

        # 不应该抛出异常
        lm.set_state("svc", ComponentState.READY)
        lm.set_state("svc", ComponentState.STOPPED)
        lm.set_state("svc", ComponentState.FAILED)

        assert lm.get_state("svc") == ComponentState.FAILED

    def test_set_state_no_duplicate_start_hook(self):
        """set_state 从 READY→READY 不重复触发 on_start"""
        lm = LifecycleManager()
        lm.register("svc")
        calls = []

        lm.on_start("svc", lambda n: calls.append("start"))
        lm.set_state("svc", ComponentState.READY)
        lm.set_state("svc", ComponentState.READY)  # 不应再次触发

        assert calls == ["start"]

    def test_on_start_on_stop_on_fail_methods(self):
        """覆盖 on_start/on_stop/on_fail 方法 (lines 66-67, 70-71, 74-75)"""
        lm = LifecycleManager()
        # 未注册的组件也可以添加钩子（setdefault 自动创建）
        lm.on_start("new_svc", lambda n: None)
        lm.on_stop("new_svc", lambda n: None)
        lm.on_fail("new_svc", lambda n: None)

        assert len(lm._hooks["new_svc"]["on_start"]) == 1
        assert len(lm._hooks["new_svc"]["on_stop"]) == 1
        assert len(lm._hooks["new_svc"]["on_fail"]) == 1

    def test_list_states(self):
        """覆盖 list_states() (line 78)"""
        lm = LifecycleManager()
        lm.register("a")
        lm.register("b")
        lm.set_state("a", ComponentState.READY)

        states = lm.list_states()
        assert states == {"a": "ready", "b": "uninitialized"}

    def test_summary(self):
        """覆盖 summary() (lines 80-84)"""
        lm = LifecycleManager()
        lm.register("a")
        lm.register("b")
        lm.set_state("a", ComponentState.READY)

        s = lm.summary()
        assert s["total"] == 2
        assert s["by_state"]["ready"] == 1
        assert s["by_state"]["uninitialized"] == 1


# ── ComponentRegistry 补充测试 ─────────────────────────────────────────

class TestComponentRegistrySupplement:
    """ComponentRegistry 未覆盖方法补充测试"""

    def test_register_decorator_with_aliases(self):
        """覆盖装饰器注册时设置别名 (lines 116-117)"""
        registry = ComponentRegistry()
        registry.clear()

        @registry.register("deco_comp", aliases=["dc", "dcomp"])
        class DecoComp:
            pass

        assert registry.has("deco_comp")
        assert registry.has("dc")
        assert registry.has("dcomp")
        assert registry.get("dc") is DecoComp

    def test_register_direct_with_aliases(self):
        """覆盖直接注册组件并设置别名 (lines 122-126)"""
        registry = ComponentRegistry()
        registry.clear()

        obj = {"key": "value"}
        registry.register("direct_comp", obj, aliases=["dir", "dcomp2"])

        assert registry.has("direct_comp")
        assert registry.has("dir")
        assert registry.get("dir") is obj

    def test_get_raises_keyerror(self):
        """覆盖 get() 对不存在的组件抛出 KeyError (line 132)"""
        registry = ComponentRegistry()
        registry.clear()

        with pytest.raises(KeyError, match="Component not found"):
            registry.get("nonexistent_component")

    def test_list_all(self):
        """覆盖 list_all() (line 142)"""
        registry = ComponentRegistry()
        registry.clear()

        registry.register("c", 1)
        registry.register("a", 2)
        registry.register("b", 3)

        assert registry.list_all() == ["a", "b", "c"]

    def test_resolve_deps(self):
        """覆盖 resolve_deps() 基于类型注解解析依赖 (lines 146-154)"""
        registry = ComponentRegistry()
        registry.clear()

        # 注册一个名字与类型名匹配的组件
        class HttpClient:
            pass

        class Database:
            pass

        registry.register("HttpClient", HttpClient())
        registry.register("Database", Database())

        def my_func(http_client: HttpClient, db: Database, plain):
            pass

        resolved = registry.resolve_deps(my_func)
        assert "http_client" in resolved
        assert "db" in resolved
        assert "plain" not in resolved
        assert isinstance(resolved["http_client"], HttpClient)
        assert isinstance(resolved["db"], Database)

    def test_resolve_deps_no_annotations(self):
        """覆盖 resolve_deps() 无类型注解的情况"""
        registry = ComponentRegistry()
        registry.clear()

        def no_annotations(a, b):
            pass

        resolved = registry.resolve_deps(no_annotations)
        assert resolved == {}

    def test_clear(self):
        """覆盖 clear() (lines 158-159)"""
        registry = ComponentRegistry()
        registry.clear()

        registry.register("x", 1)
        registry.register("y", 2, aliases=["yy"])
        assert registry.has("x")
        assert registry.has("yy")

        registry.clear()
        assert not registry.has("x")
        assert not registry.has("yy")
        assert registry.list_all() == []

    def test_get_lifecycle(self):
        """覆盖 get_lifecycle() 懒初始化 (lines 163-165)"""
        registry = ComponentRegistry()
        registry.clear()
        # 重置 lifecycle 为 None
        registry._lifecycle = None

        lc = registry.get_lifecycle()
        assert isinstance(lc, LifecycleManager)
        # 第二次调用返回同一个实例
        lc2 = registry.get_lifecycle()
        assert lc is lc2

    def test_register_with_lifecycle(self):
        """覆盖 register_with_lifecycle() (lines 176-184)"""
        registry = ComponentRegistry()
        registry.clear()
        registry._lifecycle = None
        lc = registry.get_lifecycle()  # 初始化 lifecycle

        start_calls = []
        stop_calls = []

        def on_start(name):
            start_calls.append(name)

        def on_stop(name):
            stop_calls.append(name)

        result = registry.register_with_lifecycle(
            "lifecycle_comp",
            object(),
            on_start=on_start,
            on_stop=on_stop,
        )

        assert result is not None
        # set_state(READY) 在 on_start 注册之前调用，钩子不会在此触发
        # 但组件已注册到 lifecycle 并设置为 READY 状态
        assert lc.get_state("lifecycle_comp") == ComponentState.READY
        # 钩子已添加到 lifecycle manager
        assert len(lc._hooks["lifecycle_comp"]["on_start"]) == 1
        assert len(lc._hooks["lifecycle_comp"]["on_stop"]) == 1

    def test_register_with_lifecycle_no_hooks(self):
        """覆盖 register_with_lifecycle() 无钩子的情况"""
        registry = ComponentRegistry()
        registry.clear()
        registry._lifecycle = None
        registry.get_lifecycle()  # 初始化 lifecycle

        result = registry.register_with_lifecycle("no_hooks", 42)
        assert result == 42
        assert registry.get("no_hooks") == 42
        assert registry.get_lifecycle().get_state("no_hooks") == ComponentState.READY

    def test_component_decorator(self):
        """覆盖 component() 模块级装饰器函数"""
        registry = ComponentRegistry()
        registry.clear()

        @component("mod_comp", aliases=["mc"])
        class ModComp:
            pass

        assert registry.has("mod_comp")
        assert registry.has("mc")
        assert registry.get("mc") is ModComp


# ── ComponentState 枚举测试 ────────────────────────────────────────────

class TestComponentState:
    """ComponentState 枚举值测试"""

    def test_enum_values(self):
        assert ComponentState.UNINITIALIZED.value == "uninitialized"
        assert ComponentState.INITIALIZING.value == "initializing"
        assert ComponentState.READY.value == "ready"
        assert ComponentState.DEGRADED.value == "degraded"
        assert ComponentState.STOPPED.value == "stopped"
        assert ComponentState.FAILED.value == "failed"


# ── 集成测试 ───────────────────────────────────────────────────────────

class TestIntegration:
    """集成测试：LifecycleManager + ComponentRegistry 协同"""

    def test_full_lifecycle_flow(self):
        """完整生命周期流程：注册→启动→降级→停止"""
        registry = ComponentRegistry()
        registry.clear()
        registry._lifecycle = None
        lc = registry.get_lifecycle()

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