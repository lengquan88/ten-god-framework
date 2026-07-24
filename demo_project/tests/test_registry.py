"""Tests for registry.py — 组件注册中心"""

import sys
import pytest

# Ensure the source module is importable
sys.path.insert(0, "/workspace/demo_project")

from tengod.比肩_架构协同.registry import (
    ComponentRegistry,
    ComponentState,
    LifecycleManager,
    component,
    get_registry,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fresh_registry():
    """Create a fresh registry singleton by clearing any existing state."""
    reg = ComponentRegistry()
    reg.clear()
    # Also clear the lifecycle singleton reference
    reg._lifecycle = None
    return reg


@pytest.fixture
def fresh_lifecycle():
    """Create a fresh LifecycleManager."""
    return LifecycleManager()


# ---------------------------------------------------------------------------
# ComponentState
# ---------------------------------------------------------------------------

class TestComponentState:
    """Tests for the ComponentState enum."""

    def test_all_values_present(self):
        """Verify all six lifecycle states exist."""
        assert ComponentState.UNINITIALIZED.value == "uninitialized"
        assert ComponentState.INITIALIZING.value == "initializing"
        assert ComponentState.READY.value == "ready"
        assert ComponentState.DEGRADED.value == "degraded"
        assert ComponentState.STOPPED.value == "stopped"
        assert ComponentState.FAILED.value == "failed"

    def test_is_enum(self):
        """Verify ComponentState is an Enum subclass."""
        assert issubclass(ComponentState, type(ComponentState.READY))

    def test_equality(self):
        """Verify enum equality works."""
        assert ComponentState.READY == ComponentState.READY
        assert ComponentState.READY != ComponentState.FAILED

    def test_str_value(self):
        """Verify string values match expected."""
        assert str(ComponentState.READY.value) == "ready"


# ---------------------------------------------------------------------------
# LifecycleManager
# ---------------------------------------------------------------------------

class TestLifecycleManager:
    """Tests for the LifecycleManager class."""

    def test_register_initial_state(self, fresh_lifecycle):
        """Registering a component sets state to UNINITIALIZED."""
        fresh_lifecycle.register("db")
        assert fresh_lifecycle.get_state("db") == ComponentState.UNINITIALIZED

    def test_register_multiple(self, fresh_lifecycle):
        """Register multiple components."""
        fresh_lifecycle.register("db")
        fresh_lifecycle.register("cache")
        assert fresh_lifecycle.get_state("db") == ComponentState.UNINITIALIZED
        assert fresh_lifecycle.get_state("cache") == ComponentState.UNINITIALIZED

    def test_get_state_unknown(self, fresh_lifecycle):
        """Unknown component returns UNINITIALIZED."""
        assert fresh_lifecycle.get_state("nonexistent") == ComponentState.UNINITIALIZED

    def test_set_and_get_state(self, fresh_lifecycle):
        """Set and get a component state."""
        fresh_lifecycle.register("db")
        fresh_lifecycle.set_state("db", ComponentState.READY)
        assert fresh_lifecycle.get_state("db") == ComponentState.READY

    def test_set_state_unknown_component(self, fresh_lifecycle):
        """Setting state for an unknown component still works."""
        fresh_lifecycle.set_state("ghost", ComponentState.READY)
        assert fresh_lifecycle.get_state("ghost") == ComponentState.READY

    def test_set_state_all_transitions(self, fresh_lifecycle):
        """Test all valid state transitions."""
        fresh_lifecycle.register("svc")
        for state in ComponentState:
            fresh_lifecycle.set_state("svc", state)
            assert fresh_lifecycle.get_state("svc") == state

    def test_on_start_hook_is_triggered(self, fresh_lifecycle):
        """on_start hook fires when state becomes READY."""
        called = []
        fresh_lifecycle.register("svc")
        fresh_lifecycle.on_start("svc", lambda n: called.append(n))
        fresh_lifecycle.set_state("svc", ComponentState.READY)
        assert called == ["svc"]

    def test_on_start_hook_not_triggered_on_other_state(self, fresh_lifecycle):
        """on_start hook does NOT fire on non-READY states."""
        called = []
        fresh_lifecycle.register("svc")
        fresh_lifecycle.on_start("svc", lambda n: called.append(n))
        fresh_lifecycle.set_state("svc", ComponentState.INITIALIZING)
        assert called == []

    def test_on_start_not_triggered_when_already_ready(self, fresh_lifecycle):
        """on_start hook does NOT re-fire if already READY."""
        called = []
        fresh_lifecycle.register("svc")
        fresh_lifecycle.on_start("svc", lambda n: called.append(n))
        fresh_lifecycle.set_state("svc", ComponentState.READY)
        called.clear()
        fresh_lifecycle.set_state("svc", ComponentState.READY)
        assert called == []

    def test_on_stop_hook_is_triggered(self, fresh_lifecycle):
        """on_stop hook fires when state becomes STOPPED."""
        called = []
        fresh_lifecycle.register("svc")
        fresh_lifecycle.on_stop("svc", lambda n: called.append(n))
        fresh_lifecycle.set_state("svc", ComponentState.STOPPED)
        assert called == ["svc"]

    def test_on_fail_hook_is_triggered(self, fresh_lifecycle):
        """on_fail hook fires when state becomes FAILED."""
        called = []
        fresh_lifecycle.register("svc")
        fresh_lifecycle.on_fail("svc", lambda n: called.append(n))
        fresh_lifecycle.set_state("svc", ComponentState.FAILED)
        assert called == ["svc"]

    def test_on_stop_not_triggered_for_fail(self, fresh_lifecycle):
        """on_stop does NOT fire when state is FAILED."""
        called_stop = []
        called_fail = []
        fresh_lifecycle.register("svc")
        fresh_lifecycle.on_stop("svc", lambda n: called_stop.append(n))
        fresh_lifecycle.on_fail("svc", lambda n: called_fail.append(n))
        fresh_lifecycle.set_state("svc", ComponentState.FAILED)
        assert called_stop == []
        assert called_fail == ["svc"]

    def test_hook_exception_silenced_on_start(self, fresh_lifecycle):
        """Exceptions in on_start hooks are silently caught."""
        def bad_hook(name):
            raise RuntimeError("boom")

        fresh_lifecycle.register("svc")
        fresh_lifecycle.on_start("svc", bad_hook)
        # Should not raise
        fresh_lifecycle.set_state("svc", ComponentState.READY)
        assert fresh_lifecycle.get_state("svc") == ComponentState.READY

    def test_hook_exception_silenced_on_stop(self, fresh_lifecycle):
        """Exceptions in on_stop hooks are silently caught."""
        def bad_hook(name):
            raise RuntimeError("boom")

        fresh_lifecycle.register("svc")
        fresh_lifecycle.on_stop("svc", bad_hook)
        fresh_lifecycle.set_state("svc", ComponentState.STOPPED)
        assert fresh_lifecycle.get_state("svc") == ComponentState.STOPPED

    def test_hook_exception_silenced_on_fail(self, fresh_lifecycle):
        """Exceptions in on_fail hooks are silently caught."""
        def bad_hook(name):
            raise RuntimeError("boom")

        fresh_lifecycle.register("svc")
        fresh_lifecycle.on_fail("svc", bad_hook)
        fresh_lifecycle.set_state("svc", ComponentState.FAILED)
        assert fresh_lifecycle.get_state("svc") == ComponentState.FAILED

    def test_multiple_hooks(self, fresh_lifecycle):
        """Multiple hooks of the same type are all called."""
        called = []
        fresh_lifecycle.register("svc")
        fresh_lifecycle.on_start("svc", lambda n: called.append(1))
        fresh_lifecycle.on_start("svc", lambda n: called.append(2))
        fresh_lifecycle.set_state("svc", ComponentState.READY)
        assert called == [1, 2]

    def test_hook_registered_before_register(self, fresh_lifecycle):
        """Hook registered before lifecycle.register is overwritten (register resets hooks)."""
        called = []
        fresh_lifecycle.on_start("svc", lambda n: called.append(n))
        # register() overwrites _hooks[name] with an empty dict, so the hook is lost
        fresh_lifecycle.register("svc")
        fresh_lifecycle.set_state("svc", ComponentState.READY)
        assert called == []

    def test_list_states(self, fresh_lifecycle):
        """list_states returns dict of name -> state string value."""
        fresh_lifecycle.register("a")
        fresh_lifecycle.register("b")
        fresh_lifecycle.set_state("a", ComponentState.READY)
        states = fresh_lifecycle.list_states()
        assert states == {"a": "ready", "b": "uninitialized"}

    def test_list_states_empty(self, fresh_lifecycle):
        """list_states on empty manager returns empty dict."""
        assert fresh_lifecycle.list_states() == {}

    def test_summary(self, fresh_lifecycle):
        """summary returns correct counts."""
        fresh_lifecycle.register("a")
        fresh_lifecycle.register("b")
        fresh_lifecycle.register("c")
        fresh_lifecycle.set_state("a", ComponentState.READY)
        s = fresh_lifecycle.summary()
        assert s["total"] == 3
        assert s["by_state"]["uninitialized"] == 2
        assert s["by_state"]["ready"] == 1

    def test_summary_empty(self, fresh_lifecycle):
        """summary on empty manager."""
        s = fresh_lifecycle.summary()
        assert s["total"] == 0
        assert sum(s["by_state"].values()) == 0

    def test_register_duplicate(self, fresh_lifecycle):
        """Re-registering the same name resets state."""
        fresh_lifecycle.register("svc")
        fresh_lifecycle.set_state("svc", ComponentState.READY)
        fresh_lifecycle.register("svc")  # re-register
        assert fresh_lifecycle.get_state("svc") == ComponentState.UNINITIALIZED


# ---------------------------------------------------------------------------
# ComponentRegistry
# ---------------------------------------------------------------------------

class TestComponentRegistry:
    """Tests for the ComponentRegistry singleton."""

    def test_singleton(self, fresh_registry):
        """ComponentRegistry is a singleton."""
        a = ComponentRegistry()
        b = ComponentRegistry()
        assert a is b

    def test_register_direct(self, fresh_registry):
        """Register a component by direct call."""
        obj = object()
        result = fresh_registry.register("my_obj", obj)
        assert result is obj
        assert fresh_registry.get("my_obj") is obj

    def test_register_decorator(self, fresh_registry):
        """Register a component via decorator pattern."""
        @fresh_registry.register("my_func")
        def my_func():
            return 42

        assert fresh_registry.get("my_func") is my_func
        assert fresh_registry.get("my_func")() == 42

    def test_register_decorator_returns_callable(self, fresh_registry):
        """Decorator returns the original callable."""
        @fresh_registry.register("my_class")
        class MyClass:
            pass

        assert MyClass.__name__ == "MyClass"

    def test_register_with_aliases(self, fresh_registry):
        """Register with aliases."""
        obj = object()
        fresh_registry.register("db", obj, aliases=["database", "datastore"])
        assert fresh_registry.get("db") is obj
        assert fresh_registry.get("database") is obj
        assert fresh_registry.get("datastore") is obj

    def test_register_decorator_with_aliases(self, fresh_registry):
        """Decorator with aliases."""
        @fresh_registry.register("calc", aliases=["calculator"])
        def calc():
            return 100

        assert fresh_registry.get("calc") is calc
        assert fresh_registry.get("calculator") is calc

    def test_register_duplicate_overwrites(self, fresh_registry):
        """Registering the same name twice overwrites."""
        a = object()
        b = object()
        fresh_registry.register("x", a)
        fresh_registry.register("x", b)
        assert fresh_registry.get("x") is b

    def test_get_missing_raises_keyerror(self, fresh_registry):
        """Getting a missing component raises KeyError."""
        with pytest.raises(KeyError, match="Component not found"):
            fresh_registry.get("nonexistent")

    def test_get_missing_alias_raises_keyerror(self, fresh_registry):
        """Getting a missing alias raises KeyError."""
        with pytest.raises(KeyError, match="Component not found"):
            fresh_registry.get("nonexistent_alias")

    def test_has_true(self, fresh_registry):
        """has returns True for registered component."""
        fresh_registry.register("svc", object())
        assert fresh_registry.has("svc") is True

    def test_has_false(self, fresh_registry):
        """has returns False for missing component."""
        assert fresh_registry.has("missing") is False

    def test_has_via_alias(self, fresh_registry):
        """has returns True for alias."""
        fresh_registry.register("svc", object(), aliases=["s"])
        assert fresh_registry.has("s") is True

    def test_list_all_empty(self, fresh_registry):
        """list_all on empty registry returns empty list."""
        assert fresh_registry.list_all() == []

    def test_list_all_sorted(self, fresh_registry):
        """list_all returns sorted component names."""
        fresh_registry.register("c", object())
        fresh_registry.register("a", object())
        fresh_registry.register("b", object())
        assert fresh_registry.list_all() == ["a", "b", "c"]

    def test_list_all_excludes_aliases(self, fresh_registry):
        """list_all returns only primary names, not aliases."""
        fresh_registry.register("db", object(), aliases=["database"])
        assert fresh_registry.list_all() == ["db"]

    def test_resolve_deps(self, fresh_registry):
        """resolve_deps resolves type-annotated parameters."""
        class Database:
            pass

        class Cache:
            pass

        db = Database()
        cache = Cache()
        fresh_registry.register("Database", db)
        fresh_registry.register("Cache", cache)

        def service(db: Database, cache: Cache):
            pass

        resolved = fresh_registry.resolve_deps(service)
        assert resolved == {"db": db, "cache": cache}

    def test_resolve_deps_partial(self, fresh_registry):
        """resolve_deps only resolves registered types."""
        class Database:
            pass

        db = Database()
        fresh_registry.register("Database", db)

        def service(db: Database, unknown: int):
            pass

        resolved = fresh_registry.resolve_deps(service)
        assert resolved == {"db": db}

    def test_resolve_deps_no_annotations(self, fresh_registry):
        """resolve_deps with no annotations returns empty dict."""
        def service(a, b):
            pass

        resolved = fresh_registry.resolve_deps(service)
        assert resolved == {}

    def test_resolve_deps_empty_registry(self, fresh_registry):
        """resolve_deps with empty registry returns empty dict."""
        class Database:
            pass

        def service(db: Database):
            pass

        resolved = fresh_registry.resolve_deps(service)
        assert resolved == {}

    def test_clear(self, fresh_registry):
        """clear removes all components and aliases."""
        fresh_registry.register("a", object(), aliases=["aa"])
        fresh_registry.clear()
        assert fresh_registry.list_all() == []
        assert fresh_registry.has("a") is False
        assert fresh_registry.has("aa") is False

    def test_get_lifecycle(self, fresh_registry):
        """get_lifecycle returns a LifecycleManager."""
        lm = fresh_registry.get_lifecycle()
        assert isinstance(lm, LifecycleManager)

    def test_get_lifecycle_same_instance(self, fresh_registry):
        """get_lifecycle returns the same instance each time."""
        lm1 = fresh_registry.get_lifecycle()
        lm2 = fresh_registry.get_lifecycle()
        assert lm1 is lm2

    def test_register_with_lifecycle(self, fresh_registry):
        """register_with_lifecycle registers and sets READY."""
        obj = object()
        fresh_registry.get_lifecycle()  # ensure lifecycle exists
        result = fresh_registry.register_with_lifecycle("svc", obj)
        assert result is obj
        assert fresh_registry.get("svc") is obj
        lm = fresh_registry.get_lifecycle()
        assert lm.get_state("svc") == ComponentState.READY

    def test_register_with_lifecycle_hooks(self, fresh_registry):
        """register_with_lifecycle with on_start/on_stop hooks.

        Note: set_state runs before hooks are registered in register_with_lifecycle,
        so on_start does NOT fire during the initial registration. The hooks are
        registered for future state transitions.
        """
        started = []
        stopped = []

        fresh_registry.get_lifecycle()
        fresh_registry.register_with_lifecycle(
            "svc", object(),
            on_start=lambda n: started.append(n),
            on_stop=lambda n: stopped.append(n),
        )

        # on_start does NOT fire here because set_state is called before on_start is registered
        assert started == []

        # Manually trigger stop → on_stop hook fires
        lm = fresh_registry.get_lifecycle()
        lm.set_state("svc", ComponentState.STOPPED)
        assert stopped == ["svc"]

        # Reset to READY → on_start hook fires now
        lm.set_state("svc", ComponentState.READY)
        assert started == ["svc"]

    def test_register_with_lifecycle_no_lifecycle(self, fresh_registry):
        """register_with_lifecycle when lifecycle is None still works."""
        fresh_registry._lifecycle = None
        obj = object()
        result = fresh_registry.register_with_lifecycle("svc", obj)
        assert result is obj

    def test_register_returns_component_direct_call(self, fresh_registry):
        """Direct register returns the component."""
        obj = object()
        assert fresh_registry.register("x", obj) is obj


# ---------------------------------------------------------------------------
# get_registry
# ---------------------------------------------------------------------------

class TestGetRegistry:
    """Tests for the get_registry function."""

    def test_returns_component_registry(self):
        assert isinstance(get_registry(), ComponentRegistry)

    def test_same_instance(self, fresh_registry):
        a = get_registry()
        b = get_registry()
        assert a is b


# ---------------------------------------------------------------------------
# component decorator
# ---------------------------------------------------------------------------

class TestComponentDecorator:
    """Tests for the component() decorator."""

    def test_decorator_registers(self, fresh_registry):
        """component decorator registers the function."""
        @component("my_service")
        def my_service():
            return "hello"

        reg = get_registry()
        assert reg.get("my_service") is my_service
        assert my_service() == "hello"

    def test_decorator_with_aliases(self, fresh_registry):
        """component decorator with aliases."""
        @component("svc", aliases=["service", "s"])
        class Service:
            pass

        reg = get_registry()
        assert reg.get("svc") is Service
        assert reg.get("service") is Service
        assert reg.get("s") is Service

    def test_decorator_returns_original(self, fresh_registry):
        """Decorator returns the original callable."""
        @component("x")
        class X:
            pass

        assert X.__name__ == "X"


# ---------------------------------------------------------------------------
# Edge cases / integration
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge case and integration tests."""

    def test_empty_registry_operations(self, fresh_registry):
        """Various operations on empty registry."""
        assert fresh_registry.list_all() == []
        assert fresh_registry.has("anything") is False
        with pytest.raises(KeyError):
            fresh_registry.get("anything")

    def test_duplicate_registration_overwrites(self, fresh_registry):
        """Duplicate registration overwrites previous."""
        a = object()
        b = object()
        fresh_registry.register("dup", a)
        fresh_registry.register("dup", b)
        assert fresh_registry.get("dup") is b

    def test_missing_plugin_raises(self, fresh_registry):
        """Accessing missing plugin raises KeyError."""
        with pytest.raises(KeyError):
            fresh_registry.get("missing_plugin")

    def test_alias_chain(self, fresh_registry):
        """Alias correctly resolves to the original component."""
        obj = object()
        fresh_registry.register("original", obj, aliases=["a1", "a2", "a3"])
        for name in ["original", "a1", "a2", "a3"]:
            assert fresh_registry.get(name) is obj
            assert fresh_registry.has(name) is True

    def test_lifecycle_integration(self, fresh_registry):
        """Full lifecycle integration: register -> start -> stop."""
        lm = fresh_registry.get_lifecycle()
        fresh_registry.register("db", "database_object")
        lm.register("db")
        lm.set_state("db", ComponentState.INITIALIZING)
        assert lm.get_state("db") == ComponentState.INITIALIZING
        lm.set_state("db", ComponentState.READY)
        assert lm.get_state("db") == ComponentState.READY
        lm.set_state("db", ComponentState.STOPPED)
        assert lm.get_state("db") == ComponentState.STOPPED

    def test_resolve_deps_with_aliases(self, fresh_registry):
        """resolve_deps resolves using aliases."""
        class DB:
            pass

        db = DB()
        fresh_registry.register("Database", db, aliases=["DB"])
        # The type annotation's __name__ is "DB", which should match the alias

        def service(db: DB):
            pass

        resolved = fresh_registry.resolve_deps(service)
        assert resolved == {"db": db}

    def test_clear_and_reuse(self, fresh_registry):
        """After clear, registry can be reused."""
        fresh_registry.register("a", 1)
        fresh_registry.clear()
        fresh_registry.register("a", 2)
        assert fresh_registry.get("a") == 2

    def test_register_many_components(self, fresh_registry):
        """Register many components and verify all."""
        for i in range(50):
            fresh_registry.register(f"comp_{i}", i)
        assert len(fresh_registry.list_all()) == 50
        assert fresh_registry.get("comp_0") == 0
        assert fresh_registry.get("comp_49") == 49

    def test_lifecycle_full_cycle(self, fresh_lifecycle):
        """Full lifecycle cycle: UNINITIALIZED -> INITIALIZING -> READY -> STOPPED."""
        started = []
        stopped = []

        fresh_lifecycle.register("worker")
        fresh_lifecycle.on_start("worker", lambda n: started.append(n))
        fresh_lifecycle.on_stop("worker", lambda n: stopped.append(n))

        fresh_lifecycle.set_state("worker", ComponentState.INITIALIZING)
        assert started == []
        fresh_lifecycle.set_state("worker", ComponentState.READY)
        assert started == ["worker"]
        fresh_lifecycle.set_state("worker", ComponentState.STOPPED)
        assert stopped == ["worker"]

    def test_degraded_state(self, fresh_lifecycle):
        """DEGRADED state does not trigger on_start or on_stop."""
        started = []
        stopped = []
        fresh_lifecycle.register("svc")
        fresh_lifecycle.on_start("svc", lambda n: started.append(n))
        fresh_lifecycle.on_stop("svc", lambda n: stopped.append(n))
        fresh_lifecycle.set_state("svc", ComponentState.DEGRADED)
        assert started == []
        assert stopped == []

    def test_component_decorator_preserves_metadata(self, fresh_registry):
        """The component decorator preserves the original function."""
        @component("greeter")
        def greet(name: str) -> str:
            """Say hello."""
            return f"Hello, {name}"

        assert greet.__name__ == "greet"
        assert greet.__doc__ == "Say hello."
        assert greet("World") == "Hello, World"