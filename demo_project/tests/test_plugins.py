#!/usr/bin/env python3
"""
plugins.py 测试套件
====================
覆盖: PluginMetadata, PluginRegistry, PluginSandbox, PluginHookManager
"""

import pytest

from tengod.plugins import (
    PluginMetadata,
    PluginRegistry,
    PluginSandbox,
    PluginHookManager,
    PermissionDeniedError,
    VALID_HOOKS,
    VALID_PERMISSIONS,
)


# ═══════════════════════════════════════════════════════════
# PluginMetadata 测试
# ═══════════════════════════════════════════════════════════

class TestPluginMetadata:

    def test_creation(self):
        md = PluginMetadata(
            id="my.plugin",
            name="My Plugin",
            version="1.0.0",
            author="Test",
            description="Test plugin",
            entry_point="test.module:main"
        )
        assert md.id == "my.plugin"
        assert md.name == "My Plugin"
        assert md.version == "1.0.0"
        assert md.is_active is True
        assert md.is_builtin is False

    def test_to_dict(self):
        md = PluginMetadata(
            id="test.plugin",
            name="Test",
            version="1.0.0",
            author="Author",
            description="Desc",
            entry_point="mod:fn",
            hooks=["bazi:post_calc"],
            permissions=["read:records"],
        )
        d = md.to_dict()
        assert d["id"] == "test.plugin"
        assert d["name"] == "Test"
        assert d["hooks"] == ["bazi:post_calc"]
        assert d["permissions"] == ["read:records"]
        assert "_runtime_fn" not in d

    def test_to_json(self):
        md = PluginMetadata(
            id="test.plugin",
            name="Test",
            version="1.0.0",
            author="Author",
            description="Desc",
            entry_point="mod:fn",
        )
        json_str = md.to_json()
        assert "test.plugin" in json_str
        assert "Test" in json_str


# ═══════════════════════════════════════════════════════════
# PluginRegistry 测试
# ═══════════════════════════════════════════════════════════

class TestPluginRegistry:

    @pytest.fixture
    def registry(self):
        return PluginRegistry()

    def test_register_valid(self, registry):
        md = PluginMetadata(
            id="valid.plugin",
            name="Valid",
            version="1.0.0",
            author="Test",
            description="Valid plugin",
            entry_point="test:main"
        )
        assert registry.register(md) is True
        assert "valid.plugin" in registry

    def test_register_invalid_id(self, registry):
        md = PluginMetadata(
            id="INVALID_PLUGIN",
            name="Invalid",
            version="1.0.0",
            author="Test",
            description="Invalid",
            entry_point="test:main"
        )
        assert registry.register(md) is False

    def test_register_duplicate(self, registry):
        md1 = PluginMetadata(
            id="dup.plugin",
            name="Dup1",
            version="1.0.0",
            author="Test",
            description="Dup",
            entry_point="test:main"
        )
        md2 = PluginMetadata(
            id="dup.plugin",
            name="Dup2",
            version="2.0.0",
            author="Test",
            description="Dup",
            entry_point="test:main"
        )
        assert registry.register(md1) is True
        assert registry.register(md2) is False

    def test_unregister(self, registry):
        md = PluginMetadata(
            id="test.unreg",
            name="Unreg",
            version="1.0.0",
            author="Test",
            description="Test",
            entry_point="test:main"
        )
        registry.register(md)
        assert registry.unregister("test.unreg") is True
        assert "test.unreg" not in registry

    def test_unregister_builtin(self, registry):
        md = PluginMetadata(
            id="builtin.test",
            name="Builtin",
            version="1.0.0",
            author="Test",
            description="Builtin",
            entry_point="test:main",
            is_builtin=True
        )
        registry.register(md)
        assert registry.unregister("builtin.test") is False

    def test_get(self, registry):
        md = PluginMetadata(
            id="get.test",
            name="Get",
            version="1.0.0",
            author="Test",
            description="Test",
            entry_point="test:main"
        )
        registry.register(md)
        result = registry.get("get.test")
        assert result is not None
        assert result.name == "Get"

    def test_list_all(self, registry):
        md1 = PluginMetadata(
            id="list.a",
            name="A",
            version="1.0.0",
            author="Test",
            description="A",
            entry_point="test:main",
            is_active=True
        )
        md2 = PluginMetadata(
            id="list.b",
            name="B",
            version="1.0.0",
            author="Test",
            description="B",
            entry_point="test:main",
            is_active=False
        )
        registry.register(md1)
        registry.register(md2)
        all_plugins = registry.list_all()
        assert len(all_plugins) == 2
        active_only = registry.list_all(active_only=True)
        assert len(active_only) == 1

    def test_activate_deactivate(self, registry):
        md = PluginMetadata(
            id="act.test",
            name="Act",
            version="1.0.0",
            author="Test",
            description="Test",
            entry_point="test:main",
            is_active=True
        )
        registry.register(md)
        assert registry.deactivate("act.test") is True
        p = registry.get("act.test")
        assert p.is_active is False
        assert registry.activate("act.test") is True
        p = registry.get("act.test")
        assert p.is_active is True

    def test_get_by_hook(self, registry):
        md1 = PluginMetadata(
            id="hook.a",
            name="A",
            version="1.0.0",
            author="Test",
            description="A",
            entry_point="test:main",
            hooks=["bazi:post_calc"],
            is_active=True
        )
        md2 = PluginMetadata(
            id="hook.b",
            name="B",
            version="1.0.0",
            author="Test",
            description="B",
            entry_point="test:main",
            hooks=["report:post_gen"],
            is_active=True
        )
        md3 = PluginMetadata(
            id="hook.c",
            name="C",
            version="1.0.0",
            author="Test",
            description="C",
            entry_point="test:main",
            hooks=["bazi:post_calc"],
            is_active=False
        )
        registry.register(md1)
        registry.register(md2)
        registry.register(md3)
        results = registry.get_by_hook("bazi:post_calc")
        assert len(results) == 1
        assert results[0].id == "hook.a"

    def test_validate_metadata(self, registry):
        valid = PluginMetadata(
            id="valid.test",
            name="Valid",
            version="1.0.0",
            author="Test",
            description="Valid",
            entry_point="test:main",
            hooks=["bazi:post_calc"],
            permissions=["read:records"],
        )
        assert registry.validate_metadata(valid) is True

        invalid_id = PluginMetadata(
            id="INVALID",
            name="Invalid",
            version="1.0.0",
            author="Test",
            description="Invalid",
            entry_point="test:main"
        )
        assert registry.validate_metadata(invalid_id) is False

        invalid_version = PluginMetadata(
            id="valid.test",
            name="Invalid",
            version="invalid",
            author="Test",
            description="Invalid",
            entry_point="test:main"
        )
        assert registry.validate_metadata(invalid_version) is False

        invalid_hook = PluginMetadata(
            id="valid.test",
            name="Invalid",
            version="1.0.0",
            author="Test",
            description="Invalid",
            entry_point="test:main",
            hooks=["invalid:hook"]
        )
        assert registry.validate_metadata(invalid_hook) is False

    def test_import_plugin_from_dict(self, registry):
        plugin_dict = {
            "id": "imported.test",
            "name": "Imported",
            "version": "1.0.0",
            "author": "Test",
            "description": "Imported",
            "entry_point": "test:main",
            "hooks": ["bazi:post_calc"],
            "permissions": ["read:records"],
        }
        md = registry.import_plugin_from_dict(plugin_dict)
        assert md is not None
        assert md.id == "imported.test"
        assert "imported.test" in registry


# ═══════════════════════════════════════════════════════════
# PluginSandbox 测试
# ═══════════════════════════════════════════════════════════

class TestPluginSandbox:

    @pytest.fixture
    def sandbox(self):
        registry = PluginRegistry()
        return PluginSandbox(registry)

    def test_verify_permissions(self, sandbox):
        registry = sandbox.registry
        md = PluginMetadata(
            id="perm.test",
            name="Perm",
            version="1.0.0",
            author="Test",
            description="Perm",
            entry_point="test:main",
            permissions=["read:records", "write:records"]
        )
        registry.register(md)
        sandbox.verify_permissions("perm.test", ["read:records"])

    def test_verify_permissions_missing(self, sandbox):
        registry = sandbox.registry
        md = PluginMetadata(
            id="perm.test",
            name="Perm",
            version="1.0.0",
            author="Test",
            description="Perm",
            entry_point="test:main",
            permissions=["read:records"]
        )
        registry.register(md)
        with pytest.raises(PermissionDeniedError):
            sandbox.verify_permissions("perm.test", ["write:records"])

    def test_run_in_process(self, sandbox):
        def test_fn(data, context):
            return {"result": data["value"] * 2}

        result = sandbox.run_in_process(test_fn, {"value": 42}, {"user": "test"})
        assert result["success"] is True
        assert result["result"] == {"result": 84}

    def test_run_in_process_error(self, sandbox):
        def test_fn(data, context):
            raise RuntimeError("test error")

        result = sandbox.run_in_process(test_fn, {}, {})
        assert result["success"] is False
        assert "test error" in result["error"]

    def test_run_with_runtime_fn(self, sandbox):
        registry = sandbox.registry
        def runtime_fn(data, context):
            return {"hook_result": "success"}

        md = PluginMetadata(
            id="runtime.test",
            name="Runtime",
            version="1.0.0",
            author="Test",
            description="Runtime",
            entry_point="test:main",
            hooks=["bazi:post_calc"]
        )
        md._runtime_fn = runtime_fn
        registry.register(md)

        result = sandbox.run("runtime.test", "bazi:post_calc", {"input": "test"})
        assert result["success"] is True
        assert result["result"] == {"hook_result": "success"}

    def test_run_not_found(self, sandbox):
        result = sandbox.run("nonexistent", "bazi:post_calc", {})
        assert result["success"] is False
        assert "not found" in result["error"]


# ═══════════════════════════════════════════════════════════
# PluginHookManager 测试
# ═══════════════════════════════════════════════════════════

class TestPluginHookManager:

    @pytest.fixture
    def hook_manager(self):
        registry = PluginRegistry()
        return PluginHookManager(registry)

    def test_trigger_hook(self, hook_manager):
        registry = hook_manager.registry

        def hook_fn(data, context):
            return {"processed": True}

        md = PluginMetadata(
            id="hook.trigger",
            name="HookTrigger",
            version="1.0.0",
            author="Test",
            description="HookTrigger",
            entry_point="test:main",
            hooks=["bazi:post_calc"],
            is_active=True
        )
        md._runtime_fn = hook_fn
        registry.register(md)

        results = hook_manager.trigger_hook("bazi:post_calc", {"input": "test"})
        assert len(results) == 1
        assert results[0]["success"] is True

    def test_trigger_hook_no_plugins(self, hook_manager):
        results = hook_manager.trigger_hook("bazi:post_calc", {"input": "test"})
        assert len(results) == 0

    def test_trigger_hook_single(self, hook_manager):
        registry = hook_manager.registry

        def hook_fn(data, context):
            return {"single_result": "ok"}

        md = PluginMetadata(
            id="single.test",
            name="Single",
            version="1.0.0",
            author="Test",
            description="Single",
            entry_point="test:main",
            hooks=["bazi:post_calc"],
            is_active=True
        )
        md._runtime_fn = hook_fn
        registry.register(md)

        result = hook_manager.trigger_hook_single("single.test", "bazi:post_calc", {"input": "test"})
        assert result["success"] is True
        assert result["data"] == {"single_result": "ok"}

    def test_trigger_hook_single_inactive(self, hook_manager):
        registry = hook_manager.registry

        md = PluginMetadata(
            id="inactive.test",
            name="Inactive",
            version="1.0.0",
            author="Test",
            description="Inactive",
            entry_point="test:main",
            hooks=["bazi:post_calc"],
            is_active=False
        )
        registry.register(md)

        result = hook_manager.trigger_hook_single("inactive.test", "bazi:post_calc", {"input": "test"})
        assert result["success"] is False
        assert "inactive" in result["error"]
