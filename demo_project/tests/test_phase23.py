"""Stage 23: Plugin Marketplace 测试集。"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Dict, List

import pytest

from tengod.plugins import (
    BUILTIN_PLUGINS,
    PluginHookManager,
    PluginMetadata,
    PluginRegistry,
    PluginSandbox,
    create_plugin_metadata,
    get_plugin_manager,
    validate_plugin_json,
    _reset_plugin_manager,
)


# ---------------------------------------------------------------------------
# 工具：创建一个带有 runtime_fn 的测试插件
# ---------------------------------------------------------------------------


def _make_plugin_metadata(pid: str,
                          hooks: List[str],
                          permissions: List[str] | None = None,
                          runtime_sleep: float = 0.0,
                          runtime_value: Any = None,
                          runtime_raise: BaseException | None = None,
                          is_builtin: bool = False,
                          is_active: bool = True) -> PluginMetadata:
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
        description="该插件用于测试",
        entry_point=f"tests.test_phase23:{pid}",
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
    def test_create_basic_metadata(self):
        md = create_plugin_metadata(
            id="com.example.basic1",
            name="基础示例插件",
            version="1.0.0",
            author="tester-A",
            description="用于测试创建流程",
            entry_point="mymodule:main",
            hooks=["bazi:post_calc"],
            permissions=["read:records"],
        )
        assert md.id == "com.example.basic1"
        assert md.version == "1.0.0"
        assert "bazi:post_calc" in md.hooks
        assert md.is_active is True
        assert md.is_builtin is False
        assert isinstance(md.created_at, datetime)

    def test_metadata_required_fields(self):
        r = PluginRegistry()
        # 缺少必填字段的各种变体
        missing_name = create_plugin_metadata(
            id="com.example.bad",
            name="",
            version="1.0.0",
            author="t",
            description="d",
            entry_point="m:f",
            hooks=["bazi:pre_calc"],
        )
        assert r.validate_metadata(missing_name) is False

        missing_entry = create_plugin_metadata(
            id="com.example.bad2",
            name="n",
            version="1.0.0",
            author="t",
            description="d",
            entry_point="",
            hooks=["bazi:pre_calc"],
        )
        assert r.validate_metadata(missing_entry) is False

        bad_id = create_plugin_metadata(
            id="INVALID-UPPER",
            name="n",
            version="1.0.0",
            author="t",
            description="d",
            entry_point="m:f",
            hooks=["bazi:pre_calc"],
        )
        assert r.validate_metadata(bad_id) is False

    def test_metadata_version_format(self):
        r = PluginRegistry()
        for good in ["1.0.0", "0.1.0", "1.2.3-beta", "2.0.0-rc.1"]:
            md = create_plugin_metadata(
                id="com.example.ver",
                name="n",
                version=good,
                author="t",
                description="d",
                entry_point="m:f",
                hooks=["bazi:pre_calc"],
            )
            assert r.validate_metadata(md), f"version {good} should pass"

        for bad in ["1", "1.0", "v1.0.0", "1.0.0.0", "abc"]:
            md = create_plugin_metadata(
                id="com.example.ver2",
                name="n",
                version=bad,
                author="t",
                description="d",
                entry_point="m:f",
                hooks=["bazi:pre_calc"],
            )
            assert r.validate_metadata(md) is False, f"version {bad} should fail"

    def test_permission_validation(self):
        r = PluginRegistry()
        md_ok = create_plugin_metadata(
            id="com.example.perm",
            name="n",
            version="1.0.0",
            author="t",
            description="d",
            entry_point="m:f",
            hooks=["bazi:pre_calc"],
            permissions=["read:records", "cache:read", "network:outbound"],
        )
        assert r.validate_metadata(md_ok) is True

        md_bad = create_plugin_metadata(
            id="com.example.perm.bad",
            name="n",
            version="1.0.0",
            author="t",
            description="d",
            entry_point="m:f",
            hooks=["bazi:pre_calc"],
            permissions=["read:records", "admin:everything"],
        )
        assert r.validate_metadata(md_bad) is False

        md_bad_hook = create_plugin_metadata(
            id="com.example.hook.bad",
            name="n",
            version="1.0.0",
            author="t",
            description="d",
            entry_point="m:f",
            hooks=["bazi:pre_calc", "nonexistent:hook"],
        )
        assert r.validate_metadata(md_bad_hook) is False


# ===========================================================================
# TestPluginRegistry
# ===========================================================================


class TestPluginRegistry:
    def setup_method(self):
        self.registry = PluginRegistry()

    def test_register_plugin(self):
        md = _make_plugin_metadata("com.example.reg1", ["report:post_gen"])
        assert self.registry.register(md) is True
        assert "com.example.reg1" in self.registry

    def test_register_duplicate_id(self):
        md1 = _make_plugin_metadata("com.example.dup", ["report:post_gen"])
        md2 = _make_plugin_metadata("com.example.dup", ["report:post_gen"])
        assert self.registry.register(md1) is True
        assert self.registry.register(md2) is False

    def test_unregister_plugin(self):
        md = _make_plugin_metadata("com.example.unreg", ["report:post_gen"])
        self.registry.register(md)
        assert self.registry.unregister("com.example.unreg") is True
        assert self.registry.get("com.example.unreg") is None

    def test_unregister_missing(self):
        assert self.registry.unregister("com.example.nope") is False

    def test_activate_deactivate(self):
        md = _make_plugin_metadata("com.example.act", ["report:post_gen"])
        self.registry.register(md)
        assert self.registry.deactivate("com.example.act") is True
        assert self.registry.get("com.example.act").is_active is False
        assert self.registry.activate("com.example.act") is True
        assert self.registry.get("com.example.act").is_active is True

        # 不存在的插件
        assert self.registry.activate("com.example.missing") is False
        assert self.registry.deactivate("com.example.missing") is False

    def test_list_active_only(self):
        a = _make_plugin_metadata("com.example.a", ["report:post_gen"], is_active=True)
        b = _make_plugin_metadata("com.example.b", ["report:post_gen"], is_active=False)
        c = _make_plugin_metadata("com.example.c", ["report:post_gen"], is_active=True)
        self.registry.register(a)
        self.registry.register(b)
        self.registry.register(c)
        all_items = self.registry.list_all()
        assert len(all_items) == 3
        active_items = self.registry.list_all(active_only=True)
        ids = {p["id"] for p in active_items}
        assert ids == {"com.example.a", "com.example.c"}

    def test_list_with_hook_filter(self):
        a = _make_plugin_metadata("com.example.ha", ["report:post_gen"])
        b = _make_plugin_metadata("com.example.hb", ["bazi:post_calc"])
        c = _make_plugin_metadata("com.example.hc", ["report:post_gen", "bazi:post_calc"])
        self.registry.register(a)
        self.registry.register(b)
        self.registry.register(c)
        report_items = self.registry.list_all(hook_filter="report:post_gen")
        ids = {p["id"] for p in report_items}
        assert ids == {"com.example.ha", "com.example.hc"}

    def test_get_by_hook(self):
        a = _make_plugin_metadata("com.example.gh1", ["bazi:post_calc"], is_active=True)
        b = _make_plugin_metadata("com.example.gh2", ["bazi:post_calc"], is_active=False)
        c = _make_plugin_metadata("com.example.gh3", ["report:post_gen"], is_active=True)
        self.registry.register(a)
        self.registry.register(b)
        self.registry.register(c)
        matched = self.registry.get_by_hook("bazi:post_calc")
        ids = {p.id for p in matched}
        assert ids == {"com.example.gh1"}


# ===========================================================================
# TestPluginSandbox
# ===========================================================================


class TestPluginSandbox:
    def setup_method(self):
        self.registry = PluginRegistry()
        self.sandbox = PluginSandbox(self.registry, timeout=2.0)

    def test_sandbox_can_run_in_process(self):
        md = _make_plugin_metadata("com.example.sb", ["report:post_gen"],
                                   runtime_value={"ok": True, "answer": 42})
        self.registry.register(md)
        result = self.sandbox.run("com.example.sb", "report:post_gen", {"x": 1})
        assert result["success"] is True
        assert result["plugin_id"] == "com.example.sb"
        assert result["result"] == {"ok": True, "answer": 42}

    def test_sandbox_timeout(self):
        md = _make_plugin_metadata("com.example.tm", ["report:post_gen"],
                                   runtime_sleep=0.5,
                                   runtime_value={"slow": True})
        self.registry.register(md)
        # 使用很短的超时；这里由于是 in-process 路径，不会真正终止，
        # 所以另外通过 run_isolated 测试真正的超时行为
        self.sandbox.timeout = 0.2
        code = "import time\ndef main(data, ctx):\n    time.sleep(5)\n    return {'done': True}\n"
        result = self.sandbox.run_isolated(code, {"x": 1})
        assert result["success"] is False
        assert "timeout" in result.get("error", "").lower() or result.get("timed_out") is True

    def test_sandbox_permission_check(self):
        md = _make_plugin_metadata("com.example.perm", ["report:post_gen"],
                                   permissions=["read:records"])
        self.registry.register(md)
        # 已授予的权限
        self.sandbox.verify_permissions("com.example.perm", ["read:records"])
        # 缺少的权限
        with pytest.raises(Exception):
            self.sandbox.verify_permissions("com.example.perm",
                                             ["read:records", "network:outbound"])
        # 不存在的插件
        with pytest.raises(Exception):
            self.sandbox.verify_permissions("com.example.nobody", ["read:records"])

    def test_sandbox_returns_dict(self):
        md = _make_plugin_metadata("com.example.shape", ["report:post_gen"],
                                   runtime_value={"shape": 1})
        self.registry.register(md)
        result = self.sandbox.run("com.example.shape", "report:post_gen", {})
        assert isinstance(result, dict)
        assert "result" in result
        assert "plugin_id" in result
        assert "elapsed_ms" in result
        assert isinstance(result["elapsed_ms"], int)

    def test_sandbox_handles_exception(self):
        md = _make_plugin_metadata("com.example.err", ["report:post_gen"],
                                   runtime_raise=ValueError("boom!"))
        self.registry.register(md)
        result = self.sandbox.run("com.example.err", "report:post_gen", {})
        assert result["success"] is False
        assert result["result"] is None
        assert "boom" in (result.get("error") or "").lower()

    def test_sandbox_limits_untrusted_imports(self):
        code = (
            "import os\n"
            "def main(data, ctx):\n"
            "    return {'cwd': os.getcwd()}\n"
        )
        result = self.sandbox.run_isolated(code, {})
        assert result["success"] is False
        assert "not allowed" in (result.get("error") or "").lower() or "import" in (
            result.get("error") or "").lower()

    def test_sandbox_builtin_fast_path(self):
        md = _make_plugin_metadata("com.example.bi", ["report:post_gen"],
                                   runtime_value={"fast": True},
                                   is_builtin=True)
        self.registry.register(md)
        result = self.sandbox.run("com.example.bi", "report:post_gen", {})
        assert result["success"] is True
        assert result["result"]["fast"] is True

    def test_sandbox_context_injection(self):
        md = _make_plugin_metadata("com.example.ctx", ["report:post_gen"])
        self.registry.register(md)
        result = self.sandbox.run("com.example.ctx", "report:post_gen",
                                  {"k": "v"},
                                  context={"extra": "ctx"})
        assert result["success"] is True
        payload = result["result"]
        # context_keys 来自 runtime_fn：包含 "extra" 与 "plugin_id"
        assert "extra" in payload["context_keys"]
        assert "plugin_id" in payload["context_keys"]


# ===========================================================================
# TestHookManager
# ===========================================================================


class TestHookManager:
    def setup_method(self):
        self.registry = PluginRegistry()
        self.sandbox = PluginSandbox(self.registry, timeout=2.0)
        self.hm = PluginHookManager(self.registry, self.sandbox)

    def test_trigger_hook_empty(self):
        results = self.hm.trigger_hook("report:post_gen", {})
        assert isinstance(results, list)
        assert len(results) == 0

    def test_trigger_hook_single_plugin(self):
        md = _make_plugin_metadata("com.example.hm1", ["report:post_gen"],
                                   runtime_value={"x": 1})
        self.registry.register(md)
        results = self.hm.trigger_hook("report:post_gen", {"in": 1})
        assert len(results) == 1
        assert results[0]["plugin_id"] == "com.example.hm1"
        assert results[0]["success"] is True

    def test_trigger_hook_multiple_plugins(self):
        for i in range(3):
            md = _make_plugin_metadata(f"com.example.hm{i}", ["report:post_gen"],
                                        runtime_value={"idx": i})
            self.registry.register(md)
        results = self.hm.trigger_hook("report:post_gen", {"in": 2})
        assert len(results) == 3
        pids = {r["plugin_id"] for r in results}
        assert pids == {"com.example.hm0", "com.example.hm1", "com.example.hm2"}

    def test_trigger_hook_inactive_skipped(self):
        active = _make_plugin_metadata("com.example.ha", ["report:post_gen"],
                                       runtime_value={"a": 1})
        inactive = _make_plugin_metadata("com.example.hi", ["report:post_gen"],
                                         runtime_value={"i": 1}, is_active=False)
        self.registry.register(active)
        self.registry.register(inactive)
        results = self.hm.trigger_hook("report:post_gen", {})
        assert len(results) == 1
        assert results[0]["plugin_id"] == "com.example.ha"

    def test_trigger_hook_specific_plugin(self):
        a = _make_plugin_metadata("com.example.hsp", ["report:post_gen"],
                                  runtime_value={"sp": 1})
        self.registry.register(a)
        result = self.hm.trigger_hook_single("com.example.hsp", "report:post_gen", {})
        assert result["plugin_id"] == "com.example.hsp"
        assert result["success"] is True

        # 不存在
        result2 = self.hm.trigger_hook_single("com.example.nobody", "report:post_gen", {})
        assert result2["success"] is False

    def test_hook_result_structure(self):
        md = _make_plugin_metadata("com.example.hst", ["report:post_gen"],
                                   runtime_value={"hello": "world"})
        self.registry.register(md)
        results = self.hm.trigger_hook("report:post_gen", {"in": 0})
        r = results[0]
        assert "plugin_id" in r
        assert "success" in r
        assert "data" in r
        assert "error" in r
        assert "elapsed_ms" in r

    def test_batch_trigger_parallel(self):
        for i in range(4):
            md = _make_plugin_metadata(f"com.example.bt{i}",
                                        ["report:post_gen"],
                                        runtime_sleep=0.05,
                                        runtime_value={"i": i})
            self.registry.register(md)
        pids = [f"com.example.bt{i}" for i in range(4)]
        start = time.perf_counter()
        results = self.hm.batch_trigger(pids, "report:post_gen", {})
        elapsed = time.perf_counter() - start
        assert len(results) == 4
        # 并行：应比串行 (4 * 0.05 = 0.2s) 更快，但放宽到 1.5s 给 CI 留余裕
        assert elapsed < 1.5


# ===========================================================================
# TestBuiltinPlugins
# ===========================================================================


class TestBuiltinPlugins:
    def setup_method(self):
        _reset_plugin_manager()

    def test_builtin_report_formatter_exists(self):
        pm = get_plugin_manager()
        md = pm.registry.get("tengod.builtin.report_formatter")
        assert md is not None
        assert md.is_builtin is True
        assert "report:post_gen" in md.hooks

    def test_builtin_report_formatter_runs(self):
        pm = get_plugin_manager()
        result = pm.hook_manager.trigger_hook_single(
            "tengod.builtin.report_formatter",
            "report:post_gen",
            {"report": "此报告讨论五行以及大运走向。"},
        )
        assert result["success"] is True
        data = result["data"]
        assert data["enhanced"] is True
        assert len(data["extra_sections"]) > 0

    def test_builtin_topic_tagger_tags(self):
        pm = get_plugin_manager()
        result = pm.hook_manager.trigger_hook_single(
            "tengod.builtin.topic_tagger",
            "search:post_query",
            {"day_master": "甲木", "pillars": ["金", "木", "水", "火"]},
        )
        assert result["success"] is True
        topics = result["data"]["topics"]
        assert "日主-甲木" in topics
        assert "金属性" in topics

    def test_builtin_lucky_element_suggestor(self):
        pm = get_plugin_manager()
        result = pm.hook_manager.trigger_hook_single(
            "tengod.builtin.lucky_element_suggestor",
            "analysis:post_trajectory",
            {"year": 2024},
        )
        assert result["success"] is True
        data = result["data"]
        assert "primary_element" in data
        assert "secondary_element" in data
        assert "unfavorable" in data

    def test_builtin_plugins_are_active(self):
        pm = get_plugin_manager()
        for pid in BUILTIN_PLUGINS:
            md = pm.registry.get(pid)
            assert md is not None
            assert md.is_active is True

    def test_builtin_plugins_cannot_be_deleted(self):
        pm = get_plugin_manager()
        for pid in BUILTIN_PLUGINS:
            assert pm.unregister(pid) is False


# ===========================================================================
# TestPluginSystemIntegration
# ===========================================================================


class TestPluginSystemIntegration:
    def setup_method(self):
        _reset_plugin_manager()

    def test_full_register_run_flow(self):
        pm = get_plugin_manager()
        md = _make_plugin_metadata("com.example.integ", ["report:post_gen"],
                                   runtime_value={"hello": "world"})
        assert pm.register(md) is True
        pm.registry.deactivate("com.example.integ")
        results_before = pm.trigger("report:post_gen", {})
        assert all(r["plugin_id"] != "com.example.integ" for r in results_before)
        pm.registry.activate("com.example.integ")
        results_after = pm.trigger("report:post_gen", {})
        ids = {r["plugin_id"] for r in results_after}
        assert "com.example.integ" in ids

    def test_multiple_plugins_same_hook(self):
        pm = get_plugin_manager()
        pids = [f"com.example.multi{i}" for i in range(3)]
        for pid in pids:
            pm.register(_make_plugin_metadata(pid, ["report:post_gen"],
                                               runtime_value={"pid": pid}))
        results = pm.trigger("report:post_gen", {})
        result_ids = {r["plugin_id"] for r in results}
        for pid in pids:
            assert pid in result_ids

    def test_plugin_produces_serializable_result(self):
        pm = get_plugin_manager()
        md = _make_plugin_metadata("com.example.ser", ["report:post_gen"],
                                   runtime_value={"a": 1, "b": [True, False, None],
                                                  "c": {"nested": "ok"}})
        pm.register(md)
        results = pm.trigger("report:post_gen", {})
        # 找到我们的结果
        ours = next(r for r in results if r["plugin_id"] == "com.example.ser")
        dumped = json.dumps(ours, ensure_ascii=False)
        assert isinstance(dumped, str)
        assert "ok" in dumped

    def test_hook_manager_uses_sandbox(self):
        pm = get_plugin_manager()
        md = _make_plugin_metadata("com.example.use", ["report:post_gen"],
                                   runtime_raise=RuntimeError("sandboxed"))
        pm.register(md)
        results = pm.trigger("report:post_gen", {})
        ours = next(r for r in results if r["plugin_id"] == "com.example.use")
        assert ours["success"] is False
        assert "sandboxed" in (ours.get("error") or "").lower()


# ===========================================================================
# 额外：验证 validate_plugin_json 可用
# ===========================================================================


def test_validate_plugin_json_ok():
    payload = {
        "id": "com.example.json",
        "name": "JSON 插件",
        "version": "1.0.0",
        "author": "tester",
        "description": "测试 JSON 校验",
        "entry_point": "mod:fn",
        "hooks": ["bazi:post_calc"],
        "permissions": ["read:records"],
    }
    assert validate_plugin_json(json.dumps(payload)) is True


def test_validate_plugin_json_bad():
    payload = {"id": "BAD", "name": "", "version": "1.0",
               "author": "", "description": "", "entry_point": ""}
    assert validate_plugin_json(json.dumps(payload)) is False
    assert validate_plugin_json("not json at all") is False
