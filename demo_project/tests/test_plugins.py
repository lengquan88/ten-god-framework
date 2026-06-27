"""tengod.plugins 完整测试集 —— 目标 90%+ 覆盖率。"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from tengod.plugins import (
    BUILTIN_PLUGINS,
    DEFAULT_MAX_MEMORY_MB,
    DEFAULT_TIMEOUT_SECONDS,
    PermissionDeniedError,
    PluginHookManager,
    PluginMetadata,
    PluginRegistry,
    PluginSandbox,
    SANDBOX_IMPORT_WHITELIST,
    VALID_HOOKS,
    VALID_PERMISSIONS,
    _PluginManager,
    _PLUGIN_ID_RE,
    _VERSION_RE,
    _builtin_lucky_element_suggestor_fn,
    _builtin_report_formatter_fn,
    _builtin_topic_tagger_fn,
    _reset_plugin_manager,
    create_plugin_metadata,
    get_plugin_manager,
    validate_plugin_json,
)


# ===========================================================================
# 工具函数
# ===========================================================================


def _make_plugin_metadata(
    pid: str,
    hooks: List[str],
    permissions: List[str] | None = None,
    runtime_sleep: float = 0.0,
    runtime_value: Any = None,
    runtime_raise: BaseException | None = None,
    is_builtin: bool = False,
    is_active: bool = True,
) -> PluginMetadata:
    def _fn(payload: Dict[str, Any], context: Dict[str, Any]) -> Any:
        if runtime_sleep > 0:
            time.sleep(runtime_sleep)
        if runtime_raise is not None:
            raise runtime_raise
        if runtime_value is not None:
            return runtime_value
        return {
            "pid": pid,
            "hook": payload.get("hook"),
            "input": payload.get("input"),
            "context_keys": sorted(context.keys()),
        }

    md = create_plugin_metadata(
        id=pid,
        name=f"测试插件-{pid}",
        version="1.2.3",
        author="pytest",
        description="测试用插件",
        entry_point=f"tests.test_plugins:{pid}",
        hooks=hooks,
        permissions=permissions or ["read:records"],
        is_active=is_active,
        is_builtin=is_builtin,
        runtime_fn=_fn,
    )
    return md


# ===========================================================================
# TestPluginMetadata
# ===========================================================================


class TestPluginMetadata:
    def test_init_with_required_fields(self):
        md = PluginMetadata(
            id="com.example.test",
            name="测试插件",
            version="1.0.0",
            author="author",
            description="描述",
            entry_point="mod:fn",
        )
        assert md.id == "com.example.test"
        assert md.name == "测试插件"
        assert md.version == "1.0.0"
        assert md.author == "author"
        assert md.description == "描述"
        assert md.entry_point == "mod:fn"

    def test_init_with_all_fields(self):
        md = PluginMetadata(
            id="com.example.full",
            name="全字段插件",
            version="2.0.0-beta",
            author="author",
            description="完整描述",
            entry_point="mod:fn",
            hooks=["bazi:post_calc", "report:post_gen"],
            permissions=["read:records", "cache:read"],
            dependencies=["pkg1", "pkg2"],
            is_active=False,
            is_builtin=True,
        )
        assert md.id == "com.example.full"
        assert md.hooks == ["bazi:post_calc", "report:post_gen"]
        assert md.permissions == ["read:records", "cache:read"]
        assert md.dependencies == ["pkg1", "pkg2"]
        assert md.is_active is False
        assert md.is_builtin is True

    def test_default_is_active_true(self):
        md = PluginMetadata(
            id="com.example.def",
            name="默认",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="m:f",
        )
        assert md.is_active is True

    def test_default_is_builtin_false(self):
        md = PluginMetadata(
            id="com.example.def2",
            name="默认",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="m:f",
        )
        assert md.is_builtin is False

    def test_to_dict_returns_dict_with_isoformat_created_at(self):
        md = PluginMetadata(
            id="com.example.td",
            name="dict测试",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="m:f",
        )
        d = md.to_dict()
        assert isinstance(d, dict)
        assert d["id"] == "com.example.td"
        assert isinstance(d["created_at"], str)
        # 验证 isoformat
        datetime.fromisoformat(d["created_at"])

    def test_to_dict_no_runtime_fn(self):
        md = PluginMetadata(
            id="com.example.norf",
            name="无runtime",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="m:f",
        )
        md._runtime_fn = lambda x: x
        d = md.to_dict()
        assert "_runtime_fn" not in d

    def test_to_json_returns_valid_json_string(self):
        md = PluginMetadata(
            id="com.example.json",
            name="JSON测试",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="m:f",
        )
        json_str = md.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["id"] == "com.example.json"
        assert parsed["name"] == "JSON测试"
        assert "_runtime_fn" not in parsed


# ===========================================================================
# TestPluginRegistry
# ===========================================================================


class TestPluginRegistry:
    def setup_method(self):
        self.registry = PluginRegistry()

    def test_register_valid_metadata(self):
        md = _make_plugin_metadata("com.example.reg", ["report:post_gen"])
        assert self.registry.register(md) is True

    def test_register_duplicate_returns_false(self):
        md1 = _make_plugin_metadata("com.example.dup", ["report:post_gen"])
        md2 = _make_plugin_metadata("com.example.dup", ["report:post_gen"])
        assert self.registry.register(md1) is True
        assert self.registry.register(md2) is False

    def test_register_invalid_metadata_returns_false(self):
        md = PluginMetadata(
            id="INVALID",
            name="",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="m:f",
            hooks=["bazi:pre_calc"],
        )
        assert self.registry.register(md) is False

    def test_unregister_existing(self):
        md = _make_plugin_metadata("com.example.unreg", ["report:post_gen"])
        self.registry.register(md)
        assert self.registry.unregister("com.example.unreg") is True
        assert self.registry.get("com.example.unreg") is None

    def test_unregister_nonexistent_returns_false(self):
        assert self.registry.unregister("com.example.nope") is False

    def test_unregister_builtin_returns_false(self):
        md = _make_plugin_metadata(
            "com.example.builtin", ["report:post_gen"], is_builtin=True
        )
        self.registry.register(md)
        assert self.registry.unregister("com.example.builtin") is False

    def test_get_existing(self):
        md = _make_plugin_metadata("com.example.get", ["report:post_gen"])
        self.registry.register(md)
        retrieved = self.registry.get("com.example.get")
        assert retrieved is not None
        assert retrieved.id == "com.example.get"

    def test_get_nonexistent(self):
        assert self.registry.get("com.example.none") is None

    def test_list_all_empty(self):
        items = self.registry.list_all()
        assert items == []

    def test_list_all_with_active_only(self):
        a = _make_plugin_metadata("com.example.aa", ["report:post_gen"], is_active=True)
        b = _make_plugin_metadata("com.example.bb", ["report:post_gen"], is_active=False)
        c = _make_plugin_metadata("com.example.cc", ["report:post_gen"], is_active=True)
        self.registry.register(a)
        self.registry.register(b)
        self.registry.register(c)
        active = self.registry.list_all(active_only=True)
        ids = {p["id"] for p in active}
        assert ids == {"com.example.aa", "com.example.cc"}

    def test_list_all_with_hook_filter(self):
        a = _make_plugin_metadata("com.example.ha", ["report:post_gen"])
        b = _make_plugin_metadata("com.example.hb", ["bazi:post_calc"])
        c = _make_plugin_metadata("com.example.hc", ["report:post_gen", "bazi:post_calc"])
        self.registry.register(a)
        self.registry.register(b)
        self.registry.register(c)
        filtered = self.registry.list_all(hook_filter="report:post_gen")
        ids = {p["id"] for p in filtered}
        assert ids == {"com.example.ha", "com.example.hc"}

    def test_activate(self):
        md = _make_plugin_metadata("com.example.act", ["report:post_gen"], is_active=False)
        self.registry.register(md)
        assert self.registry.activate("com.example.act") is True
        assert self.registry.get("com.example.act").is_active is True

    def test_activate_nonexistent(self):
        assert self.registry.activate("com.example.nobody") is False

    def test_deactivate(self):
        md = _make_plugin_metadata("com.example.deact", ["report:post_gen"], is_active=True)
        self.registry.register(md)
        assert self.registry.deactivate("com.example.deact") is True
        assert self.registry.get("com.example.deact").is_active is False

    def test_deactivate_nonexistent(self):
        assert self.registry.deactivate("com.example.nobody") is False

    def test_get_by_hook_filters_by_active_and_hook(self):
        a = _make_plugin_metadata("com.example.gh1", ["bazi:post_calc"], is_active=True)
        b = _make_plugin_metadata("com.example.gh2", ["bazi:post_calc"], is_active=False)
        c = _make_plugin_metadata("com.example.gh3", ["report:post_gen"], is_active=True)
        self.registry.register(a)
        self.registry.register(b)
        self.registry.register(c)
        matched = self.registry.get_by_hook("bazi:post_calc")
        ids = {p.id for p in matched}
        assert ids == {"com.example.gh1"}

    def test_validate_metadata_valid_id_format(self):
        md = PluginMetadata(
            id="com.example.ok",
            name="OK",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="m:f",
            hooks=["bazi:pre_calc"],
        )
        assert self.registry.validate_metadata(md) is True

    def test_validate_metadata_invalid_id_format(self):
        # uppercase
        md = PluginMetadata(
            id="INVALID",
            name="Bad",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="m:f",
            hooks=["bazi:pre_calc"],
        )
        assert self.registry.validate_metadata(md) is False
        # no dot
        md2 = PluginMetadata(
            id="nodot",
            name="Bad",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="m:f",
            hooks=["bazi:pre_calc"],
        )
        assert self.registry.validate_metadata(md2) is False

    def test_validate_metadata_invalid_version_format(self):
        for bad_ver in ["1", "v1.0.0", "1.0.0.0", "abc"]:
            md = PluginMetadata(
                id="com.example.ver",
                name="n",
                version=bad_ver,
                author="a",
                description="d",
                entry_point="m:f",
                hooks=["bazi:pre_calc"],
            )
            assert self.registry.validate_metadata(md) is False, f"version {bad_ver} should fail"

    def test_validate_metadata_invalid_hooks(self):
        md = PluginMetadata(
            id="com.example.badhook",
            name="n",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="m:f",
            hooks=["nonexistent:hook"],
        )
        assert self.registry.validate_metadata(md) is False

    def test_validate_metadata_invalid_permissions(self):
        md = PluginMetadata(
            id="com.example.badperm",
            name="n",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="m:f",
            hooks=["bazi:pre_calc"],
            permissions=["admin:everything"],
        )
        assert self.registry.validate_metadata(md) is False

    def test_validate_metadata_invalid_dependencies_not_list(self):
        md = PluginMetadata(
            id="com.example.baddep",
            name="n",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="m:f",
            hooks=["bazi:pre_calc"],
            dependencies="not_a_list",  # type: ignore
        )
        assert self.registry.validate_metadata(md) is False

    def test_validate_metadata_empty_required_fields(self):
        r = self.registry
        # empty name
        md = PluginMetadata(
            id="com.example.empt",
            name="",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="m:f",
            hooks=["bazi:pre_calc"],
        )
        assert r.validate_metadata(md) is False
        # empty entry_point
        md2 = PluginMetadata(
            id="com.example.empt2",
            name="n",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="",
            hooks=["bazi:pre_calc"],
        )
        assert r.validate_metadata(md2) is False
        # empty description
        md3 = PluginMetadata(
            id="com.example.empt3",
            name="n",
            version="1.0.0",
            author="a",
            description="",
            entry_point="m:f",
            hooks=["bazi:pre_calc"],
        )
        assert r.validate_metadata(md3) is False
        # empty author
        md4 = PluginMetadata(
            id="com.example.empt4",
            name="n",
            version="1.0.0",
            author="",
            description="d",
            entry_point="m:f",
            hooks=["bazi:pre_calc"],
        )
        assert r.validate_metadata(md4) is False

    def test_import_plugin_from_dict_valid(self):
        d = {
            "id": "com.example.imp",
            "name": "导入插件",
            "version": "1.0.0",
            "author": "a",
            "description": "d",
            "entry_point": "m:f",
            "hooks": ["bazi:post_calc"],
            "permissions": ["read:records"],
        }
        md = self.registry.import_plugin_from_dict(d)
        assert md is not None
        assert md.id == "com.example.imp"
        assert "com.example.imp" in self.registry

    def test_import_plugin_from_dict_invalid(self):
        d = {"id": "BAD", "name": "", "version": "bad", "author": "", "description": "", "entry_point": ""}
        assert self.registry.import_plugin_from_dict(d) is None

    def test_import_plugin_from_dict_none(self):
        assert self.registry.import_plugin_from_dict(None) is None

    def test_import_plugin_from_dict_datetime_created_at(self):
        now = datetime.now(timezone.utc)
        d = {
            "id": "com.example.dt",
            "name": "DateTime",
            "version": "1.0.0",
            "author": "a",
            "description": "d",
            "entry_point": "m:f",
            "hooks": ["bazi:post_calc"],
            "created_at": now,
        }
        md = self.registry.import_plugin_from_dict(d)
        assert md is not None
        assert md.created_at == now

    def test_import_plugin_from_dict_string_created_at(self):
        d = {
            "id": "com.example.strdt",
            "name": "StringDateTime",
            "version": "1.0.0",
            "author": "a",
            "description": "d",
            "entry_point": "m:f",
            "hooks": ["bazi:post_calc"],
            "created_at": "2024-01-15T10:30:00+00:00",
        }
        md = self.registry.import_plugin_from_dict(d)
        assert md is not None
        assert md.created_at.year == 2024
        assert md.created_at.month == 1
        assert md.created_at.day == 15

    def test_import_plugin_from_dict_empty_created_at(self):
        d = {
            "id": "com.example.emptydt",
            "name": "EmptyDT",
            "version": "1.0.0",
            "author": "a",
            "description": "d",
            "entry_point": "m:f",
            "hooks": ["bazi:post_calc"],
        }
        md = self.registry.import_plugin_from_dict(d)
        assert md is not None
        assert isinstance(md.created_at, datetime)

    def test_import_plugin_from_dict_is_active_is_builtin(self):
        d = {
            "id": "com.example.flags",
            "name": "Flags",
            "version": "1.0.0",
            "author": "a",
            "description": "d",
            "entry_point": "m:f",
            "hooks": ["bazi:post_calc"],
            "is_active": False,
            "is_builtin": True,
        }
        md = self.registry.import_plugin_from_dict(d)
        assert md is not None
        assert md.is_active is False
        assert md.is_builtin is True

    def test_len(self):
        assert len(self.registry) == 0
        md = _make_plugin_metadata("com.example.len", ["report:post_gen"])
        self.registry.register(md)
        assert len(self.registry) == 1

    def test_contains(self):
        md = _make_plugin_metadata("com.example.contain", ["report:post_gen"])
        self.registry.register(md)
        assert "com.example.contain" in self.registry
        assert "com.example.nope" not in self.registry


# ===========================================================================
# TestPluginSandbox
# ===========================================================================


class TestPluginSandbox:
    def setup_method(self):
        self.registry = PluginRegistry()
        self.sandbox = PluginSandbox(self.registry, timeout=2.0)

    def test_verify_permissions_success(self):
        md = _make_plugin_metadata(
            "com.example.perm", ["report:post_gen"],
            permissions=["read:records", "cache:read"],
        )
        self.registry.register(md)
        # 不应抛出异常
        self.sandbox.verify_permissions("com.example.perm", ["read:records"])

    def test_verify_permissions_missing_raises_permission_denied(self):
        md = _make_plugin_metadata(
            "com.example.perm2", ["report:post_gen"],
            permissions=["read:records"],
        )
        self.registry.register(md)
        with pytest.raises(PermissionDeniedError, match="missing permissions"):
            self.sandbox.verify_permissions("com.example.perm2", ["network:outbound"])

    def test_verify_permissions_nonexistent_raises_permission_denied(self):
        with pytest.raises(PermissionDeniedError, match="not registered"):
            self.sandbox.verify_permissions("com.example.nobody", ["read:records"])

    def test_load_entry_point_valid(self):
        # 使用标准库中存在的函数
        fn = self.sandbox._load_entry_point("json:dumps")
        assert callable(fn)

    def test_load_entry_point_no_colon_returns_none(self):
        assert self.sandbox._load_entry_point("no_colon") is None

    def test_load_entry_point_nonexistent_module_returns_none(self):
        assert self.sandbox._load_entry_point("nonexistent.module:func") is None

    def test_load_entry_point_nonexistent_function_returns_none(self):
        assert self.sandbox._load_entry_point("json:nonexistent_func") is None

    def test_run_in_process_success(self):
        def test_fn(payload, ctx):
            return {"result": 42}

        result = self.sandbox.run_in_process(test_fn, {"x": 1})
        assert result["success"] is True
        assert result["result"] == {"result": 42}
        assert isinstance(result["elapsed_ms"], int)

    def test_run_in_process_with_exception(self):
        def test_fn(payload, ctx):
            raise ValueError("test error")

        result = self.sandbox.run_in_process(test_fn, {})
        assert result["success"] is False
        assert result["result"] is None
        assert "ValueError" in result["error"]
        assert "test error" in result["error"]

    def test_run_in_process_with_none_context(self):
        def test_fn(payload, ctx):
            return {"has_context": isinstance(ctx, dict)}

        result = self.sandbox.run_in_process(test_fn, {}, context=None)
        assert result["success"] is True
        assert result["result"]["has_context"] is True

    def test_run_with_builtin_plugin(self):
        md = _make_plugin_metadata(
            "com.example.bi", ["report:post_gen"],
            runtime_value={"builtin": True}, is_builtin=True,
        )
        self.registry.register(md)
        result = self.sandbox.run("com.example.bi", "report:post_gen", {})
        assert result["success"] is True
        assert result["result"] == {"builtin": True}
        assert result["plugin_id"] == "com.example.bi"
        assert result["hook"] == "report:post_gen"

    def test_run_with_user_plugin_and_runtime_fn(self):
        md = _make_plugin_metadata(
            "com.example.usr", ["report:post_gen"],
            runtime_value={"user": True},
        )
        self.registry.register(md)
        result = self.sandbox.run("com.example.usr", "report:post_gen", {})
        assert result["success"] is True
        assert result["result"] == {"user": True}

    def test_run_with_entry_point_loading(self):
        def dummy_entry(payload: Any, context: Any) -> Any:
            return {"loaded": True, "hook": payload.get("hook")}

        md = PluginMetadata(
            id="com.example.epl",
            name="EntryPoint",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="some.module:dummy_entry",
            hooks=["bazi:pre_calc"],
            permissions=["read:records"],
        )
        self.registry.register(md)
        with patch.object(self.sandbox, "_load_entry_point", return_value=dummy_entry):
            result = self.sandbox.run("com.example.epl", "bazi:pre_calc", {"key": "val"})
        assert result["success"] is True
        assert result["result"] == {"loaded": True, "hook": "bazi:pre_calc"}

    def test_run_with_code_entry_point(self):
        # 使用 code:// 入口
        md = PluginMetadata(
            id="com.example.code",
            name="CodePlugin",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="code://\ndef main(data, ctx):\n    return {'ok': True}\n",
            hooks=["bazi:pre_calc"],
            permissions=["read:records"],
        )
        self.registry.register(md)
        # 需要 mock Process 避免实际创建子进程
        with patch("tengod.plugins.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.is_alive.return_value = False
            mock_process.return_value = mock_proc

            # 需要在 Queue 中放入结果
            with patch("tengod.plugins.Queue") as mock_queue:
                mock_q = MagicMock()
                mock_q.get_nowait.return_value = {
                    "result": {"ok": True},
                    "success": True,
                    "error": None,
                    "elapsed_ms": 10,
                }
                mock_queue.return_value = mock_q

                result = self.sandbox.run("com.example.code", "bazi:pre_calc", {})
                assert result["success"] is True
                assert result["result"] == {"ok": True}

    def test_run_with_nonexistent_plugin(self):
        result = self.sandbox.run("com.example.nobody", "report:post_gen", {})
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_run_isolated_mocked(self):
        # Mock Process 避免实际创建子进程
        with patch("tengod.plugins.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.is_alive.return_value = False
            mock_process.return_value = mock_proc

            with patch("tengod.plugins.Queue") as mock_queue:
                mock_q = MagicMock()
                mock_q.get_nowait.return_value = {
                    "result": {"isolated": True},
                    "success": True,
                    "error": None,
                    "elapsed_ms": 5,
                }
                mock_queue.return_value = mock_q

                result = self.sandbox.run_isolated(
                    "def main(data, ctx):\n    return {'isolated': True}\n",
                    {"x": 1},
                )
                assert result["success"] is True
                assert result["result"] == {"isolated": True}

    def test_run_isolated_timeout(self):
        with patch("tengod.plugins.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.is_alive.return_value = True  # 进程仍在运行 → 超时
            mock_process.return_value = mock_proc

            self.sandbox.timeout = 0.1
            result = self.sandbox.run_isolated("", {})
            assert result["success"] is False
            assert result["timed_out"] is True

    def test_run_isolated_empty_queue(self):
        with patch("tengod.plugins.Process") as mock_process:
            mock_proc = MagicMock()
            mock_proc.is_alive.return_value = False
            mock_process.return_value = mock_proc

            with patch("tengod.plugins.Queue") as mock_queue:
                from queue import Empty

                mock_q = MagicMock()
                mock_q.get_nowait.side_effect = Empty()
                mock_queue.return_value = mock_q

                result = self.sandbox.run_isolated("", {})
                assert result["success"] is False
                assert result["error"] == "no result"

    def test_run_without_runtime_and_entry_point_returns_error(self):
        # 注册一个没有 runtime_fn 且 entry_point 不存在的插件
        md = PluginMetadata(
            id="com.example.noexec",
            name="NoExec",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="nonexistent.module:func",
            hooks=["bazi:pre_calc"],
            permissions=["read:records"],
        )
        self.registry.register(md)
        result = self.sandbox.run("com.example.noexec", "bazi:pre_calc", {})
        assert result["success"] is False
        assert "no executable entry_point" in result["error"]


# ===========================================================================
# TestPluginHookManager
# ===========================================================================


class TestPluginHookManager:
    def setup_method(self):
        self.registry = PluginRegistry()
        self.sandbox = PluginSandbox(self.registry, timeout=2.0)
        self.hm = PluginHookManager(self.registry, self.sandbox)

    def test_trigger_hook_with_matching_plugins(self):
        md = _make_plugin_metadata(
            "com.example.th1", ["report:post_gen"],
            runtime_value={"x": 1},
        )
        self.registry.register(md)
        results = self.hm.trigger_hook("report:post_gen", {"in": 1})
        assert len(results) == 1
        assert results[0]["plugin_id"] == "com.example.th1"
        assert results[0]["success"] is True
        assert results[0]["data"] == {"x": 1}

    def test_trigger_hook_with_no_plugins(self):
        results = self.hm.trigger_hook("report:post_gen", {})
        assert results == []

    def test_trigger_hook_single_success(self):
        md = _make_plugin_metadata(
            "com.example.ths", ["report:post_gen"],
            runtime_value={"single": True},
        )
        self.registry.register(md)
        result = self.hm.trigger_hook_single("com.example.ths", "report:post_gen", {})
        assert result["plugin_id"] == "com.example.ths"
        assert result["success"] is True
        assert result["data"] == {"single": True}

    def test_trigger_hook_single_plugin_not_found(self):
        result = self.hm.trigger_hook_single("com.example.nobody", "report:post_gen", {})
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_trigger_hook_single_inactive_plugin(self):
        md = _make_plugin_metadata(
            "com.example.inactive", ["report:post_gen"],
            runtime_value={"should_not_run": True}, is_active=False,
        )
        self.registry.register(md)
        result = self.hm.trigger_hook_single("com.example.inactive", "report:post_gen", {})
        assert result["success"] is False
        assert "not found or inactive" in result["error"]

    def test_batch_trigger_with_multiple_plugins(self):
        for i in range(3):
            md = _make_plugin_metadata(
                f"com.example.bt{i}", ["report:post_gen"],
                runtime_value={"i": i},
            )
            self.registry.register(md)
        pids = [f"com.example.bt{i}" for i in range(3)]
        results = self.hm.batch_trigger(pids, "report:post_gen", {})
        assert len(results) == 3
        result_ids = {r["plugin_id"] for r in results}
        assert result_ids == set(pids)

    def test_batch_trigger_with_inactive_plugins(self):
        a = _make_plugin_metadata(
            "com.example.bt_active", ["report:post_gen"],
            runtime_value={"active": True}, is_active=True,
        )
        b = _make_plugin_metadata(
            "com.example.bt_inactive", ["report:post_gen"],
            runtime_value={"should_not": True}, is_active=False,
        )
        self.registry.register(a)
        self.registry.register(b)
        results = self.hm.batch_trigger(
            ["com.example.bt_active", "com.example.bt_inactive"],
            "report:post_gen", {},
        )
        # 两个都应该返回，但 inactive 的 success=False
        assert len(results) == 2
        results_by_id = {r["plugin_id"]: r for r in results}
        assert results_by_id["com.example.bt_active"]["success"] is True
        assert results_by_id["com.example.bt_inactive"]["success"] is False


# ===========================================================================
# TestBuiltinFunctions
# ===========================================================================


class TestBuiltinReportFormatter:
    def test_with_report_containing_wuxing(self):
        payload = {"input": {"report": "此报告包含五行分析内容"}}
        result = _builtin_report_formatter_fn(payload, {})
        assert result["enhanced"] is True
        assert "已对五行部分进行高亮分析" in result["extra_sections"]

    def test_with_report_containing_dayun(self):
        payload = {"input": {"report": "此报告包含大运走势分析"}}
        result = _builtin_report_formatter_fn(payload, {})
        assert result["enhanced"] is True
        assert "已附加大运关键年份索引" in result["extra_sections"]

    def test_with_empty_report(self):
        payload = {"input": {"report": ""}}
        result = _builtin_report_formatter_fn(payload, {})
        assert result["enhanced"] is True
        assert result["extra_sections"] == []

    def test_with_no_report(self):
        payload = {"input": {}}
        result = _builtin_report_formatter_fn(payload, {})
        assert result["enhanced"] is True
        assert result["extra_sections"] == []

    def test_with_non_dict_payload(self):
        result = _builtin_report_formatter_fn("not a dict", {})
        assert result["enhanced"] is True
        assert result["extra_sections"] == []


class TestBuiltinTopicTagger:
    def test_with_pillars_containing_wuxing(self):
        payload = {"input": {"pillars": ["金", "木", "水", "火", "土"]}}
        result = _builtin_topic_tagger_fn(payload, {})
        assert "金属性" in result["topics"]
        assert "木属性" in result["topics"]
        assert "水属性" in result["topics"]
        assert "火属性" in result["topics"]
        assert "土属性" in result["topics"]
        assert result["count"] == 5

    def test_with_day_master(self):
        payload = {"input": {"day_master": "甲木"}}
        result = _builtin_topic_tagger_fn(payload, {})
        assert "日主-甲木" in result["topics"]
        assert result["count"] == 1

    def test_with_empty_input(self):
        payload = {"input": {}}
        result = _builtin_topic_tagger_fn(payload, {})
        assert result["topics"] == []
        assert result["count"] == 0

    def test_with_non_dict_payload(self):
        result = _builtin_topic_tagger_fn("not a dict", {})
        assert result["topics"] == []
        assert result["count"] == 0

    def test_with_partial_pillars(self):
        payload = {"input": {"pillars": ["金", "金", "木"]}}
        result = _builtin_topic_tagger_fn(payload, {})
        # 去重后：金属性、木属性
        assert result["topics"] == ["金属性", "木属性"]
        assert result["count"] == 2


class TestBuiltinLuckyElementSuggestor:
    def test_with_year_int(self):
        payload = {"input": {"year": 2024}}
        result = _builtin_lucky_element_suggestor_fn(payload, {})
        assert result["plugin"] == "builtin_lucky_element_suggestor"
        assert "primary_element" in result
        assert "secondary_element" in result
        assert "unfavorable" in result
        assert result["year"] == 2024
        # 2024 % 5 = 4 → 土
        expected = ["金", "木", "水", "火", "土"]
        assert result["primary_element"] == expected[2024 % 5]

    def test_with_year_string(self):
        payload = {"input": {"year": "2023"}}
        result = _builtin_lucky_element_suggestor_fn(payload, {})
        expected = ["金", "木", "水", "火", "土"]
        assert result["primary_element"] == expected[2023 % 5]

    def test_with_trajectory(self):
        payload = {"input": {"trajectory": [1, 2, 3]}}
        result = _builtin_lucky_element_suggestor_fn(payload, {})
        # elements = ["金", "木", "水", "火", "土"]
        # len([1,2,3]) = 3, idx = 3 % 5 = 3 → elements[3] = 火
        # secondary = elements[(3+2)%5] = elements[0] = 金
        # unfavorable = elements[(3+1)%5] = elements[4] = 土
        assert result["primary_element"] == "火"
        assert result["secondary_element"] == "金"
        assert result["unfavorable"] == "土"

    def test_with_no_input(self):
        payload = {"input": {}}
        result = _builtin_lucky_element_suggestor_fn(payload, {})
        # idx = 0 → 金
        assert result["primary_element"] == "金"
        assert result["secondary_element"] == "水"
        assert result["unfavorable"] == "木"
        assert result["year"] is None

    def test_with_non_dict_payload(self):
        result = _builtin_lucky_element_suggestor_fn("not a dict", {})
        assert result["primary_element"] == "金"

    def test_with_year_non_digit_string(self):
        payload = {"input": {"year": "abc"}}
        result = _builtin_lucky_element_suggestor_fn(payload, {})
        # idx = 0 → 金
        assert result["primary_element"] == "金"

    def test_with_empty_trajectory(self):
        payload = {"input": {"trajectory": []}}
        result = _builtin_lucky_element_suggestor_fn(payload, {})
        # idx = 0 → 金
        assert result["primary_element"] == "金"


# ===========================================================================
# TestHelpers
# ===========================================================================


class TestCreatePluginMetadata:
    def test_with_all_params(self):
        md = create_plugin_metadata(
            id="com.example.all",
            name="全参数",
            version="2.0.0",
            author="author",
            description="desc",
            entry_point="mod:fn",
            hooks=["bazi:post_calc"],
            permissions=["read:records", "cache:read"],
            dependencies=["pkg1"],
            is_active=False,
            is_builtin=True,
            runtime_fn=lambda x, y: x,
        )
        assert md.id == "com.example.all"
        assert md.name == "全参数"
        assert md.version == "2.0.0"
        assert md.author == "author"
        assert md.description == "desc"
        assert md.entry_point == "mod:fn"
        assert md.hooks == ["bazi:post_calc"]
        assert md.permissions == ["read:records", "cache:read"]
        assert md.dependencies == ["pkg1"]
        assert md.is_active is False
        assert md.is_builtin is True
        assert md._runtime_fn is not None

    def test_with_defaults(self):
        md = create_plugin_metadata(
            id="com.example.def",
            name="默认",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="m:f",
        )
        assert md.hooks == []
        assert md.permissions == []
        assert md.dependencies == []
        assert md.is_active is True
        assert md.is_builtin is False
        assert md._runtime_fn is None


class TestValidatePluginJson:
    def test_with_valid_json(self):
        payload = {
            "id": "com.example.json",
            "name": "JSON插件",
            "version": "1.0.0",
            "author": "tester",
            "description": "测试",
            "entry_point": "mod:fn",
            "hooks": ["bazi:post_calc"],
            "permissions": ["read:records"],
        }
        assert validate_plugin_json(json.dumps(payload)) is True

    def test_with_invalid_json(self):
        assert validate_plugin_json("not json at all") is False

    def test_with_missing_fields(self):
        payload = {"id": "BAD", "name": "", "version": "1.0", "author": "", "description": "", "entry_point": ""}
        assert validate_plugin_json(json.dumps(payload)) is False


class TestGetPluginManager:
    def setup_method(self):
        _reset_plugin_manager()

    def test_returns_singleton(self):
        pm1 = get_plugin_manager()
        pm2 = get_plugin_manager()
        assert pm1 is pm2

    def test_registers_3_builtins(self):
        pm = get_plugin_manager()
        assert len(pm.registry) == 3
        assert "tengod.builtin.report_formatter" in pm.registry
        assert "tengod.builtin.topic_tagger" in pm.registry
        assert "tengod.builtin.lucky_element_suggestor" in pm.registry


class TestResetPluginManager:
    def setup_method(self):
        _reset_plugin_manager()

    def test_clears_singleton(self):
        pm1 = get_plugin_manager()
        assert pm1 is not None
        _reset_plugin_manager()
        pm2 = get_plugin_manager()
        # 重置后获取新实例
        assert pm2 is not None
        # 新实例也是 _PluginManager 类型
        assert isinstance(pm2, _PluginManager)


# ===========================================================================
# TestConstants
# ===========================================================================


class TestValidHooks:
    def test_contains_expected_hooks(self):
        expected = [
            "bazi:pre_calc",
            "bazi:post_calc",
            "report:pre_gen",
            "report:post_gen",
            "search:post_query",
            "ui:custom_component",
            "analysis:post_trajectory",
        ]
        for hook in expected:
            assert hook in VALID_HOOKS


class TestValidPermissions:
    def test_contains_expected_permissions(self):
        expected = [
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
        ]
        for perm in expected:
            assert perm in VALID_PERMISSIONS


class TestSandboxImportWhitelist:
    def test_contains_expected_modules(self):
        expected = [
            "json", "math", "re", "datetime", "time",
            "collections", "copy", "itertools", "random",
            "statistics", "string", "typing", "enum",
            "dataclasses", "functools", "operator",
            "hashlib", "base64", "uuid", "csv",
            "bisect", "heapq", "pprint",
        ]
        for mod in expected:
            assert mod in SANDBOX_IMPORT_WHITELIST


class TestDefaultTimeout:
    def test_default_timeout_seconds(self):
        assert DEFAULT_TIMEOUT_SECONDS == 5.0


class TestDefaultMaxMemory:
    def test_default_max_memory_mb(self):
        assert DEFAULT_MAX_MEMORY_MB == 256


class TestVersionRegex:
    def test_matches_valid_versions(self):
        valid = ["1.0.0", "0.1.0", "1.2.3-beta", "2.0.0-rc.1", "10.20.30-alpha.2"]
        for v in valid:
            assert _VERSION_RE.match(v), f"version {v} should match"

    def test_rejects_invalid_versions(self):
        invalid = ["1", "1.0", "v1.0.0", "1.0.0.0", "abc", "1.0.0 ", " 1.0.0"]
        for v in invalid:
            assert not _VERSION_RE.match(v), f"version {v} should not match"


class TestPluginIdRegex:
    def test_matches_valid_ids(self):
        valid = [
            "com.example.test",
            "tengod.builtin.report_formatter",
            "a.b",
            "my-plugin.test_plugin",
            "org.example.plugin-name",
        ]
        for pid in valid:
            assert _PLUGIN_ID_RE.match(pid), f"id {pid} should match"

    def test_rejects_invalid_ids(self):
        invalid = [
            "INVALID",
            "no_dot",
            "UpperCase.example",
            "com.",
            ".com",
            "-leading.com",
            "com..example",
        ]
        for pid in invalid:
            assert not _PLUGIN_ID_RE.match(pid), f"id {pid} should not match"


# ===========================================================================
# TestBuiltinPlugins
# ===========================================================================


class TestBuiltinPlugins:
    def setup_method(self):
        _reset_plugin_manager()

    def test_builtin_plugins_dict_has_3_entries(self):
        assert len(BUILTIN_PLUGINS) == 3

    def test_builtin_report_formatter_fn_is_callable(self):
        assert callable(_builtin_report_formatter_fn)

    def test_builtin_topic_tagger_fn_is_callable(self):
        assert callable(_builtin_topic_tagger_fn)

    def test_builtin_lucky_element_suggestor_fn_is_callable(self):
        assert callable(_builtin_lucky_element_suggestor_fn)

    def test_builtin_plugins_are_active(self):
        pm = get_plugin_manager()
        for pid in BUILTIN_PLUGINS:
            md = pm.registry.get(pid)
            assert md is not None, f"{pid} should exist"
            assert md.is_active is True, f"{pid} should be active"

    def test_builtin_plugins_cannot_be_unregistered(self):
        pm = get_plugin_manager()
        for pid in BUILTIN_PLUGINS:
            assert pm.unregister(pid) is False, f"{pid} should not be unregistered"


# ===========================================================================
# TestPluginManager
# ===========================================================================


class TestPluginManager:
    def setup_method(self):
        _reset_plugin_manager()

    def test_register_delegates_to_registry(self):
        pm = get_plugin_manager()
        md = _make_plugin_metadata("com.example.pm1", ["report:post_gen"])
        assert pm.register(md) is True
        assert "com.example.pm1" in pm.registry

    def test_unregister_delegates_to_registry(self):
        pm = get_plugin_manager()
        md = _make_plugin_metadata("com.example.pm2", ["report:post_gen"])
        pm.register(md)
        assert pm.unregister("com.example.pm2") is True
        assert "com.example.pm2" not in pm.registry

    def test_trigger_delegates_to_hook_manager(self):
        pm = get_plugin_manager()
        md = _make_plugin_metadata(
            "com.example.pm3", ["report:post_gen"],
            runtime_value={"triggered": True},
        )
        pm.register(md)
        results = pm.trigger("report:post_gen", {})
        assert len(results) >= 1
        ours = [r for r in results if r["plugin_id"] == "com.example.pm3"]
        assert len(ours) == 1
        assert ours[0]["success"] is True


# ===========================================================================
# TestImportPluginFromDictEdgeCases
# ===========================================================================


class TestImportPluginFromDictEdgeCases:
    def setup_method(self):
        self.registry = PluginRegistry()

    def test_duplicate_import_returns_none(self):
        d = {
            "id": "com.example.dupimp",
            "name": "Dup",
            "version": "1.0.0",
            "author": "a",
            "description": "d",
            "entry_point": "m:f",
            "hooks": ["bazi:post_calc"],
        }
        first = self.registry.import_plugin_from_dict(d)
        assert first is not None
        second = self.registry.import_plugin_from_dict(d)
        assert second is None

    def test_invalid_created_at_string_falls_back(self):
        d = {
            "id": "com.example.baddt",
            "name": "BadDT",
            "version": "1.0.0",
            "author": "a",
            "description": "d",
            "entry_point": "m:f",
            "hooks": ["bazi:post_calc"],
            "created_at": "not-a-datetime",
        }
        md = self.registry.import_plugin_from_dict(d)
        assert md is not None
        assert isinstance(md.created_at, datetime)

    def test_created_at_other_type_falls_back(self):
        d = {
            "id": "com.example.otherdt",
            "name": "OtherDT",
            "version": "1.0.0",
            "author": "a",
            "description": "d",
            "entry_point": "m:f",
            "hooks": ["bazi:post_calc"],
            "created_at": 12345,
        }
        md = self.registry.import_plugin_from_dict(d)
        assert md is not None
        assert isinstance(md.created_at, datetime)

    def test_none_hooks_permissions(self):
        d = {
            "id": "com.example.nonehooks",
            "name": "NoneHooks",
            "version": "1.0.0",
            "author": "a",
            "description": "d",
            "entry_point": "m:f",
            "hooks": None,
            "permissions": None,
            "dependencies": None,
        }
        md = self.registry.import_plugin_from_dict(d)
        assert md is not None
        assert md.hooks == []
        assert md.permissions == []
        assert md.dependencies == []


# ===========================================================================
# TestSandboxEdgeCases
# ===========================================================================


class TestSandboxEdgeCases:
    def setup_method(self):
        self.registry = PluginRegistry()
        self.sandbox = PluginSandbox(self.registry)

    def test_run_without_entry_point_and_no_runtime_fn(self):
        md = PluginMetadata(
            id="com.example.noentry",
            name="NoEntry",
            version="1.0.0",
            author="a",
            description="d",
            entry_point="no_module:no_func",
            hooks=["bazi:pre_calc"],
            permissions=["read:records"],
        )
        self.registry.register(md)
        result = self.sandbox.run("com.example.noentry", "bazi:pre_calc", {})
        assert result["success"] is False
        assert "no executable entry_point" in result["error"]

    def test_run_in_process_with_context(self):
        def test_fn(payload, ctx):
            return {"ctx_key": ctx.get("my_key")}

        result = self.sandbox.run_in_process(test_fn, {}, context={"my_key": "my_value"})
        assert result["success"] is True
        assert result["result"]["ctx_key"] == "my_value"

    def test_trigger_hook_with_plugin_that_raises(self):
        md = _make_plugin_metadata(
            "com.example.raise", ["report:post_gen"],
            runtime_raise=RuntimeError("something went wrong"),
        )
        self.registry.register(md)
        results = self.sandbox.registry.get_by_hook("report:post_gen")
        assert len(results) == 1
        result = self.sandbox.run("com.example.raise", "report:post_gen", {})
        assert result["success"] is False
        assert "RuntimeError" in result["error"]

    def test_run_isolated_terminate_then_kill(self):
        """测试 run_isolated 中 terminate 后进程仍存活，触发 kill 路径"""
        with patch("tengod.plugins.Process") as mock_process:
            mock_proc = MagicMock()
            # 第一次 is_alive 返回 True（terminate 后仍存活），kill 后不再检查
            mock_proc.is_alive.side_effect = [True, True]
            mock_process.return_value = mock_proc

            self.sandbox.timeout = 0.1
            result = self.sandbox.run_isolated("", {})
            assert result["success"] is False
            assert result["timed_out"] is True
            # 验证 kill 被调用
            mock_proc.kill.assert_called()

    def test_load_entry_point_with_module_error(self):
        """测试模块加载报错返回 None"""
        with patch("tengod.plugins.importlib.import_module", side_effect=ImportError("no module")):
            result = self.sandbox._load_entry_point("some.module:func")
            assert result is None


# ===========================================================================
# TestValidatePluginJsonEdgeCases
# ===========================================================================


class TestValidatePluginJsonEdgeCases:
    def test_with_non_dict_json(self):
        assert validate_plugin_json("[]") is False
        assert validate_plugin_json("42") is False
        assert validate_plugin_json('"string"') is False

    def test_with_valid_but_missing_required_field(self):
        # entry_point 为空字符串会被 reject
        payload = {
            "id": "com.example.missing",
            "name": "Missing",
            "version": "1.0.0",
            "author": "a",
            "description": "d",
            "entry_point": "",
            "hooks": ["bazi:post_calc"],
        }
        assert validate_plugin_json(json.dumps(payload)) is False

    def test_with_none_values_in_json(self):
        # JSON null → Python None → str(None) = "None" (非空字符串，会通过字段检查但可能被其他校验拦截)
        payload = {
            "id": "com.example.none",
            "name": "NoneTest",
            "version": "1.0.0",
            "author": "a",
            "description": "d",
            "entry_point": None,
            "hooks": ["bazi:post_calc"],
        }
        # str(None) = "None" 不为空，所以 entry_point 非空，验证会通过
        assert validate_plugin_json(json.dumps(payload)) is True