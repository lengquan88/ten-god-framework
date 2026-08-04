"""Tests for tengod.enterprise_config — EnterpriseConfigManager.

Coverage focus:
  * Singleton lifecycle + global reset
  * Priority chain: defaults < YAML < env < runtime
  * Nested env-var path handling (including bool/int/float converters)
  * Pydantic v2 model validation + degraded fallback behavior
  * Runtime overrides with audit logging and change listener dispatch
  * Consistency validation + health check edge cases
  * Deep merge + nested-set helpers
"""

from __future__ import annotations

import os
import tempfile
import time
from typing import Any, Dict
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_enterprise_config():
    """Ensure the enterprise config singleton is reset between tests."""
    import tengod.enterprise_config as ec

    ec.reset_enterprise_config()
    # Clear any lingering env var pollution
    to_restore = {}
    for key in list(os.environ.keys()):
        if key.startswith("TENGOD_"):
            to_restore[key] = os.environ.pop(key)
    yield
    for key, val in to_restore.items():
        os.environ[key] = val
    ec.reset_enterprise_config()


@pytest.fixture
def yalc_path() -> str:
    """Create a YAML config file on disk."""
    content = """
name: yamled-instance
version: 2.31.0
environment: staging
hot_reload: true
audit_enabled: true
audit_retention: 50
cognitive:
  tbce:
    drift_warning_threshold: 0.4
    drift_critical_threshold: 0.6
    drift_check_interval: 120
  twelve_gods:
    enabled: true
    strict_mode: true
    majority_threshold: 0.6
    chaos_sea_threshold: 0.3
  seven_theories:
    thresholds:
      ontology: 0.8
      practice: 0.7
      chaos_sea: 0.4
  self_correction:
    max_steps: 5
    step_timeout: 10.0
  imaging:
    stage_timeout: 30.0
    quality_threshold: 0.8
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        path = f.name
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def yalc_no_audit_path() -> str:
    """YAML config that has audit disabled."""
    content = """
name: yamled-no-audit
audit_enabled: false
audit_retention: 50
cognitive:
  tbce:
    drift_check_interval: 120
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        path = f.name
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Singleton lifecycle
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_same_instance(self):
        from tengod.enterprise_config import EnterpriseConfigManager

        a = EnterpriseConfigManager()
        b = EnterpriseConfigManager()
        assert a is b

    def test_direct_instantiation_after_reset(self):
        import tengod.enterprise_config as ec

        ec.EnterpriseConfigManager._instance = None
        a = ec.EnterpriseConfigManager()
        b = ec.EnterpriseConfigManager()
        assert a is b

    def test_global_accessor(self):
        import tengod.enterprise_config as ec

        a = ec.get_enterprise_config()
        b = ec.get_enterprise_config()
        assert a is b

    def test_reset_clears_singleton(self):
        import tengod.enterprise_config as ec

        a = ec.get_enterprise_config()
        ec.reset_enterprise_config()
        b = ec.get_enterprise_config()
        assert a is not b


# ---------------------------------------------------------------------------
# ConfigChangeRecord / ConfigSource
# ---------------------------------------------------------------------------


class TestChangeRecord:
    def test_to_dict_truncates_long_values(self):
        from tengod.enterprise_config import ConfigChangeRecord, ConfigSource

        long = "x" * 500
        rec = ConfigChangeRecord(
            key="k", old_value=long, new_value=long, source=ConfigSource.RUNTIME
        )
        d = rec.to_dict()
        assert len(d["old_value"]) == 200
        assert len(d["new_value"]) == 200
        assert d["source"] == "runtime"
        assert d["key"] == "k"


# ---------------------------------------------------------------------------
# Priority chain
# ---------------------------------------------------------------------------


class TestPriorityChain:
    def test_defaults_loaded_without_files(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        cfg = mgr.load(config_path="/definitely/does/not/exist.yaml", auto_env=False)
        assert cfg.name == "tengod-enterprise"
        assert cfg.environment == "production"
        assert cfg.hot_reload is True

    def test_yaml_overrides_defaults(self, yalc_path):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        cfg = mgr.load(config_path=yalc_path, auto_env=False)
        assert cfg.name == "yamled-instance"
        assert cfg.environment == "staging"
        assert cfg.hot_reload is True
        assert cfg.audit_retention == 50

    def test_env_overrides_yaml(self, yalc_path):
        import tengod.enterprise_config as ec

        os.environ["TENGOD_ENV"] = "testing"
        os.environ["TENGOD_HOT_RELOAD"] = "true"
        os.environ["TENGOD_AUDIT_RETENTION"] = "200"

        mgr = ec.EnterpriseConfigManager()
        cfg = mgr.load(config_path=yalc_path)
        assert cfg.environment == "testing"
        assert cfg.hot_reload is True
        assert cfg.audit_retention == 200

    def test_env_bool_and_int_converters(self, yalc_path):
        import tengod.enterprise_config as ec

        os.environ["TENGOD_TWELVE_GODS_ENABLED"] = "false"
        os.environ["TENGOD_TWELVE_GODS_STRICT"] = "yes"  # anything != "true" -> False
        os.environ["TENGOD_MAJORITY_THRESHOLD"] = "0.75"
        os.environ["TENGOD_DRIFT_INTERVAL"] = "300"

        mgr = ec.EnterpriseConfigManager()
        cfg = mgr.load(config_path=yalc_path)
        # Note:  bool converter uses .lower() == "true"  -> "yes" -> False
        assert cfg.cognitive.twelve_gods.enabled is False
        assert cfg.cognitive.twelve_gods.strict_mode is False
        assert cfg.cognitive.twelve_gods.majority_threshold == 0.75
        assert cfg.cognitive.tbce.drift_check_interval == 300

    def test_invalid_int_env_silently_skipped(self, yalc_path):
        import tengod.enterprise_config as ec

        os.environ["TENGOD_AUDIT_RETENTION"] = "not-an-int"
        mgr = ec.EnterpriseConfigManager()
        cfg = mgr.load(config_path=yalc_path)
        # YAML value should be preserved
        assert cfg.audit_retention == 50

    def test_invalid_float_env_silently_skipped(self, yalc_path):
        import tengod.enterprise_config as ec

        os.environ["TENGOD_MAJORITY_THRESHOLD"] = "bad"
        mgr = ec.EnterpriseConfigManager()
        cfg = mgr.load(config_path=yalc_path)
        # YAML-provided 0.6 should still be in effect
        assert cfg.cognitive.twelve_gods.majority_threshold == 0.6

    def test_runtime_override_has_highest_priority(self, yalc_path):
        import tengod.enterprise_config as ec

        os.environ["TENGOD_ENV"] = "testing"
        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path=yalc_path)
        mgr.set_runtime("environment", "production", reason="fix")
        assert mgr.get("environment") == "production"

    def test_set_nested_creates_intermediate_keys(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        d: Dict[str, Any] = {}
        mgr._set_nested(d, ("a", "b", "c"), 42)
        assert d == {"a": {"b": {"c": 42}}}


# ---------------------------------------------------------------------------
# Deep merge
# ---------------------------------------------------------------------------


class TestDeepMerge:
    def test_scalar_override(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        assert mgr._deep_merge({"a": 1}, {"a": 2}) == {"a": 2}

    def test_nested_merge(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        over = {"a": {"y": 9}, "c": 4}
        assert mgr._deep_merge(base, over) == {"a": {"x": 1, "y": 9}, "b": 3, "c": 4}

    def test_override_replaces_list(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        base = {"a": [1, 2]}
        over = {"a": [3]}
        assert mgr._deep_merge(base, over) == {"a": [3]}


# ---------------------------------------------------------------------------
# Config accessors
# ---------------------------------------------------------------------------


class TestConfigAccess:
    def test_get_dotpath(self, yalc_path):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path=yalc_path)
        assert mgr.get("cognitive.twelve_gods.enabled") is True
        assert mgr.get("cognitive.tbce.drift_check_interval") == 120

    def test_get_missing_returns_default(self, yalc_path):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path=yalc_path)
        assert mgr.get("does.not.exist") is None
        assert mgr.get("does.not.exist", "fallback") == "fallback"

    def test_get_before_load_auto_loads(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        # Should not raise
        assert mgr.get("environment") == "production"

    def test_to_dict_round_trip(self, yalc_path):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path=yalc_path)
        d = mgr.to_dict()
        assert d["name"] == "yamled-instance"
        assert d["cognitive"]["tbce"]["drift_check_interval"] == 120


# ---------------------------------------------------------------------------
# Audit logging + change listeners
# ---------------------------------------------------------------------------


class TestAuditAndListeners:
    def test_runtime_override_logs_audit(self, yalc_path):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path=yalc_path)
        before = mgr.get_audit_log()
        mgr.set_runtime("hot_reload", True, reason="enable hot reload")
        after = mgr.get_audit_log()
        assert len(after) == len(before) + 1
        record = after[-1]
        assert record["key"] == "hot_reload"
        assert record["source"] == "runtime"
        assert record["reason"] == "enable hot reload"

    def test_trim_audit_log(self, yalc_path):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path=yalc_path)
        # audit_retention is 50 in the YAML
        for i in range(60):
            mgr.set_runtime(f"cognitive.tbce.drift_check_interval", i, reason=str(i))
        # Should have been trimmed down to retention size
        assert len(mgr._audit_log) <= 50

    def test_audit_disabled_does_not_log(self, yalc_no_audit_path):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path=yalc_no_audit_path)  # audit_enabled = false
        mgr.set_runtime("hot_reload", True, reason="sneaky")
        # No audit entries because audit_enabled is false
        assert len(mgr._audit_log) == 0

    def test_change_listener_invoked(self, yalc_path):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path=yalc_path)

        events = []
        def cb(key, old, new):
            events.append((key, old, new))

        mgr.on_change(cb)
        mgr.set_runtime("hot_reload", True, reason="x")
        assert events
        assert events[0][0] == "hot_reload"

    def test_remove_listener_prevents_further_callbacks(self, yalc_path):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path=yalc_path)

        events = []
        def cb(k, o, n):
            events.append(k)

        mgr.on_change(cb)
        mgr.remove_listener(cb)
        mgr.set_runtime("hot_reload", True, reason="x")
        assert events == []

    def test_broken_listener_isolation(self, yalc_path):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path=yalc_path)

        def bad(k, o, n):
            raise RuntimeError("boom")

        called = []
        def good(k, o, n):
            called.append(k)

        mgr.on_change(bad)
        mgr.on_change(good)
        # Should NOT raise
        mgr.set_runtime("hot_reload", True, reason="x")
        assert called == ["hot_reload"]

    def test_get_audit_summary(self, yalc_path):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path=yalc_path)
        mgr.set_runtime("hot_reload", True, reason="a")
        mgr.set_runtime("hot_reload", False, reason="b")
        summary = mgr.get_audit_summary()
        assert summary["total_changes"] == 2
        assert summary["by_source"].get("runtime") == 2
        assert summary["latest"] is not None


# ---------------------------------------------------------------------------
# Source tracking
# ---------------------------------------------------------------------------


class TestSourceTracking:
    def test_source_registry_populated_by_layer(self, yalc_path):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path=yalc_path, auto_env=False)
        # Only leaf keys are tracked by _record_source.
        # "name" and "hot_reload" are top-level leaves
        assert mgr.get_source("name").value == "yaml"
        assert mgr.get_source("hot_reload").value == "yaml"
        assert mgr.get_source("audit_retention").value == "yaml"

    def test_missing_key_defaults_to_DEFAULT(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        assert mgr.get_source("never.set").value == "default"


# ---------------------------------------------------------------------------
# Consistency validation
# ---------------------------------------------------------------------------


class TestConsistencyValidation:
    def test_no_validation_errors_in_valid_config(self, yalc_path):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        # Use an existing file path so hot_reload check does not fire
        mgr.load(config_path=yalc_path, auto_env=False)
        # Defaults chaos_sea (0.5 in yalc) and seven_theories min (0.7) -> no error
        assert mgr.get_validation_errors() == []

    def test_chaos_sea_gt_all_seven_theories_triggers_error(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path="/no/such/file.yaml", auto_env=False)
        mgr.set_runtime("cognitive.twelve_gods.chaos_sea_threshold", 0.9, reason="x")
        errs = mgr.get_validation_errors()
        assert any("混沌海阈值应低于所有七论阈值" in e for e in errs)

    def test_hot_reload_enabled_with_missing_file_warns(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        # Defaults have hot_reload=True and a non-existent path
        mgr.load(config_path="/definitely/not/here.yaml", auto_env=False)
        errs = mgr.get_validation_errors()
        assert any("热重载已启用但配置文件不存在" in e for e in errs)

    def test_reload_without_config_path_is_safe(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path="/definitely/not/here.yaml", auto_env=False)
        # clear path
        mgr._config_path = None
        # Should not raise
        new_cfg = mgr.reload()
        assert new_cfg is not None


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    def test_healthy_default_config(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path="/no/such/file.yaml", auto_env=False)
        hc = mgr.health_check()
        # Defaults are reasonable -> status should not be "unhealthy"
        assert hc["status"] in ("healthy", "warning")
        assert "config_hash" in hc
        assert "timestamp" in hc

    def test_low_majority_threshold_generates_warning(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path="/no/such/file.yaml", auto_env=False)
        mgr.set_runtime("cognitive.twelve_gods.majority_threshold", 0.1, reason="x")
        hc = mgr.health_check()
        assert any("多数阈值过低" in w for w in hc["warnings"])

    def test_high_majority_threshold_generates_warning(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path="/no/such/file.yaml", auto_env=False)
        mgr.set_runtime("cognitive.twelve_gods.majority_threshold", 0.95, reason="x")
        hc = mgr.health_check()
        assert any("多数阈值过高" in w for w in hc["warnings"])

    def test_max_boost_high_generates_warning(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path="/no/such/file.yaml", auto_env=False)
        mgr.set_runtime("cognitive.twelve_gods.max_boost", 0.45, reason="x")
        hc = mgr.health_check()
        assert any("五行加成上限过高" in w for w in hc["warnings"])

    def test_veto_disabled_warning(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path="/no/such/file.yaml", auto_env=False)
        mgr.set_runtime("cognitive.twelve_gods.veto_enabled", False, reason="x")
        hc = mgr.health_check()
        assert any("太极否决权已禁用" in w for w in hc["warnings"])

    def test_tbce_drift_threshold_order_issue(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path="/no/such/file.yaml", auto_env=False)
        # warning >= critical -> issue
        mgr.set_runtime("cognitive.tbce.drift_warning_threshold", 0.7, reason="x")
        mgr.set_runtime("cognitive.tbce.drift_critical_threshold", 0.4, reason="x")
        hc = mgr.health_check()
        assert any("TBCE漂移警告阈值应小于严重阈值" in i for i in hc["issues"])
        assert hc["status"] == "unhealthy"

    def test_self_correction_step_timeout_too_short(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path="/no/such/file.yaml", auto_env=False)
        mgr.set_runtime("cognitive.self_correction.step_timeout", 1.0, reason="x")
        hc = mgr.health_check()
        assert any("自修正每步超时过短" in i for i in hc["issues"])

    def test_self_correction_few_steps_warning(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path="/no/such/file.yaml", auto_env=False)
        mgr.set_runtime("cognitive.self_correction.max_steps", 1, reason="x")
        hc = mgr.health_check()
        assert any("自修正步数过少" in w for w in hc["warnings"])

    def test_seven_theories_threshold_out_of_range(self):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path="/no/such/file.yaml", auto_env=False)
        mgr.set_runtime("cognitive.seven_theories.thresholds.ontology", 0.1, reason="x")
        mgr.set_runtime("cognitive.seven_theories.thresholds.future", 0.99, reason="x")
        hc = mgr.health_check()
        texts = hc["warnings"] + hc["issues"]
        assert any("ontology" in w and "过低" in w for w in texts)
        assert any("future" in w and "过高" in w for w in texts)


# ---------------------------------------------------------------------------
# Hot reload
# ---------------------------------------------------------------------------


class TestHotReload:
    def test_get_config_reloads_when_file_changes(self, yalc_path):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        cfg1 = mgr.load(config_path=yalc_path)
        assert cfg1.name == "yamled-instance"

        # Touch the file with a new value and ensure mtime is newer than
        # the one recorded at load time.
        with open(yalc_path, "a", encoding="utf-8") as f:
            f.write("\nname: updated-instance\n")
        # Force mtime into the future so the hot-reload check is deterministic
        future = time.time() + 5
        os.utime(yalc_path, (future, future))

        cfg2 = mgr.get_config()
        assert cfg2.name == "updated-instance"


# ---------------------------------------------------------------------------
# Pydantic v2 validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_invalid_environment_raises(self):
        import tengod.enterprise_config as ec

        if not ec._PYDANTIC_V2:
            pytest.skip("Pydantic v2 not installed — validation is skipped")

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path="/no/such/file.yaml", auto_env=False)
        with pytest.raises(Exception):
            mgr.set_runtime("environment", "invalid-env", reason="x")


# ---------------------------------------------------------------------------
# Global hook-up of set_runtime behavior after load
# ---------------------------------------------------------------------------


class TestSetRuntimeBehavior:
    def test_set_runtime_after_load_refreshes_config(self, yalc_path):
        import tengod.enterprise_config as ec

        mgr = ec.EnterpriseConfigManager()
        mgr.load(config_path=yalc_path)
        mgr.set_runtime("cognitive.twelve_gods.enabled", False, reason="disable")
        # After set_runtime + reload, value should be read back
        assert mgr.get("cognitive.twelve_gods.enabled") is False
