"""
test_enterprise_config.py — 企业级配置管理器测试 v1.0
========================================================
测试覆盖（完全新增的核心模块，之前无任何测试）：
1. ConfigPriority / ConfigSource 枚举
2. ConfigChangeRecord 审计记录
3. EnterpriseConfigManager 单例模式
4. 配置优先级链：默认值 → 环境变量 → 运行时覆盖
5. get() 点号路径访问
6. set_runtime() 运行时覆盖 + 审计日志 + 变更监听
7. 热重载 / 强制 reload
8. 环境变量覆盖（TENGOD_*）
9. Pydantic v2 验证降级路径（environment 枚举）
10. 审计摘要与日志截断
11. _deep_merge / _set_nested / _trim_audit_log 内部工具
"""

import math
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tengod.enterprise_config import (
    ConfigPriority, ConfigSource, ConfigChangeRecord,
    EnterpriseConfigManager,
    EnterpriseConfig, TBCEConfig, TwelveGodsGateConfig,
    SevenTheoriesConfig, SelfCorrectionConfig, ImagingConfig,
    CognitiveConfig,
    _PYDANTIC_V2,
)


# ── Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_enterprise_singleton():
    """重置 EnterpriseConfigManager 单例，避免测试间状态污染。"""
    EnterpriseConfigManager._instance = None
    with EnterpriseConfigManager._lock:
        EnterpriseConfigManager._instance = None
    yield
    EnterpriseConfigManager._instance = None
    with EnterpriseConfigManager._lock:
        EnterpriseConfigManager._instance = None


@pytest.fixture
def clean_env():
    """清理 TENGOD_* 环境变量，避免真实环境干扰。"""
    saved = {}
    for k in list(os.environ.keys()):
        if k.startswith("TENGOD_"):
            saved[k] = os.environ.pop(k)
    yield
    for k, v in saved.items():
        os.environ[k] = v


@pytest.fixture
def mgr():
    """获取一个干净的 EnterpriseConfigManager 实例（不加载任何外部文件）。

    注意：降级路径 (_PYDANTIC_V2=False) 的 CognitiveConfig 构造函数内部会
      self.tbce = TBCEConfig(**kwargs.get("tbce", {}))
    所以传 TBCEConfig() 对象给 CognitiveConfig(tbce=...) 会导致 "** must be a mapping" 错误。
    最简单的做法：不传 cognitive，用默认 factory 构造，然后直接改 name/environment。
    """
    m = EnterpriseConfigManager()
    # 不传 cognitive 子参数——用各自的默认构造器
    m._config = EnterpriseConfig(
        name="test-instance",
        version="2.31.0",
        environment="testing",
    )
    # 再强制覆盖（EnterpriseConfig 默认值里 name 是 tengod-enterprise，这里确保是 test-instance）
    m._config.name = "test-instance"
    m._config.environment = "testing"
    m._runtime_overrides = {}
    m._audit_log = []
    m._change_listeners = []
    m._source_registry = {}
    m._validation_errors = []
    return m


# ========================================================================
# 1. 枚举值
# ========================================================================

class TestEnums:
    def test_config_priority_order(self):
        """优先级顺序必须严格递增，确保链正确。"""
        assert ConfigPriority.DEFAULT.value < ConfigPriority.YAML_FILE.value
        assert ConfigPriority.YAML_FILE.value < ConfigPriority.ENV_VARIABLE.value
        assert ConfigPriority.ENV_VARIABLE.value < ConfigPriority.RUNTIME.value

    def test_config_source_values(self):
        assert ConfigSource.DEFAULT.value == "default"
        assert ConfigSource.YAML.value == "yaml"
        assert ConfigSource.ENV.value == "env"
        assert ConfigSource.RUNTIME.value == "runtime"


# ========================================================================
# 2. ConfigChangeRecord 审计记录
# ========================================================================

class TestConfigChangeRecord:
    def test_to_dict_basic(self):
        r = ConfigChangeRecord(
            key="x.y",
            old_value=1,
            new_value=2,
            source=ConfigSource.RUNTIME,
            reason="test",
        )
        d = r.to_dict()
        assert d["key"] == "x.y"
        assert d["old_value"] == "1"
        assert d["new_value"] == "2"
        assert d["source"] == "runtime"
        assert d["reason"] == "test"
        assert isinstance(d["timestamp"], float)

    def test_to_dict_truncates_long_values(self):
        """超过 200 字符的 old/new 值必须被截断，防止审计日志膨胀。"""
        long_old = "A" * 300
        long_new = "B" * 300
        r = ConfigChangeRecord(
            key="big",
            old_value=long_old,
            new_value=long_new,
            source=ConfigSource.RUNTIME,
        )
        d = r.to_dict()
        assert len(d["old_value"]) == 200
        assert len(d["new_value"]) == 200


# ========================================================================
# 3. EnterpriseConfigManager 单例模式
# ========================================================================

class TestSingleton:
    def test_singleton_returns_same_instance(self):
        a = EnterpriseConfigManager()
        b = EnterpriseConfigManager()
        assert a is b

    def test_init_only_runs_once(self):
        """_initialized 标志确保 __init__ 只执行一次。"""
        a = EnterpriseConfigManager()
        a._test_flag = "exists"
        b = EnterpriseConfigManager()
        assert hasattr(b, "_test_flag")
        assert b._test_flag == "exists"

    def test_thread_safety_smoke(self):
        """多线程同时实例化，仍然返回同一实例（冒烟级验证锁生效）。"""
        results = []
        def worker():
            results.append(EnterpriseConfigManager())
        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        first = results[0]
        for r in results[1:]:
            assert r is first


# ========================================================================
# 4. 默认配置 + 优先级链
# ========================================================================

class TestDefaultsAndPriority:
    def test_defaults_produces_valid_config(self, clean_env):
        """无 YAML、无 env 时，load() 能产出合法默认配置。"""
        m = EnterpriseConfigManager()
        cfg = m.load(auto_env=False, hot_reload=False)
        assert cfg.environment == "production"
        assert cfg.name == "tengod-enterprise"
        assert cfg.cognitive.twelve_gods.enabled is True
        assert cfg.cognitive.tbce.default_coordinates == [0.5]*6
        assert cfg.audit_enabled is True

    def test_env_overrides_default(self, clean_env):
        """环境变量优先级高于默认值。"""
        os.environ["TENGOD_ENV"] = "staging"
        os.environ["TENGOD_HOT_RELOAD"] = "false"
        os.environ["TENGOD_AUDIT_RETENTION"] = "500"
        m = EnterpriseConfigManager()
        cfg = m.load(auto_env=True, hot_reload=False)
        assert cfg.environment == "staging"
        assert cfg.hot_reload is False
        assert cfg.audit_retention == 500

    def test_env_bool_lowercase_true(self, clean_env):
        """TENGOD_TWELVE_GODS_ENABLED=false 必须正确解析为 False。"""
        os.environ["TENGOD_TWELVE_GODS_ENABLED"] = "false"
        os.environ["TENGOD_VETO_ENABLED"] = "false"
        m = EnterpriseConfigManager()
        cfg = m.load(auto_env=True, hot_reload=False)
        assert cfg.cognitive.twelve_gods.enabled is False
        assert cfg.cognitive.twelve_gods.veto_enabled is False

    def test_env_numeric_parsing(self, clean_env):
        os.environ["TENGOD_MAJORITY_THRESHOLD"] = "0.75"
        os.environ["TENGOD_DRIFT_WARNING"] = "0.25"
        os.environ["TENGOD_DRIFT_INTERVAL"] = "120"
        m = EnterpriseConfigManager()
        cfg = m.load(auto_env=True, hot_reload=False)
        assert cfg.cognitive.twelve_gods.majority_threshold == pytest.approx(0.75)
        assert cfg.cognitive.tbce.drift_warning_threshold == pytest.approx(0.25)
        assert cfg.cognitive.tbce.drift_check_interval == 120

    def test_env_invalid_skipped_silently(self, clean_env):
        """无法转换的 env 变量应被跳过而非抛异常。"""
        os.environ["TENGOD_MAJORITY_THRESHOLD"] = "not-a-number"
        os.environ["TENGOD_AUDIT_RETENTION"] = "also-not-a-number"
        m = EnterpriseConfigManager()
        cfg = m.load(auto_env=True, hot_reload=False)
        # 默认值仍然生效
        assert cfg.cognitive.twelve_gods.majority_threshold == pytest.approx(0.5)
        assert cfg.audit_retention == 1000


# ========================================================================
# 5. get() 点号路径访问
# ========================================================================

class TestGet:
    def test_get_top_level(self, mgr):
        assert mgr.get("name") == "test-instance"

    def test_get_nested(self, mgr):
        assert mgr.get("cognitive.twelve_gods.enabled") is True
        assert mgr.get("cognitive.tbce.drift_warning_threshold") == pytest.approx(0.3)
        assert mgr.get("cognitive.seven_theories.thresholds.ontology") == pytest.approx(0.7)

    def test_get_missing_key_returns_default(self, mgr):
        assert mgr.get("does.not.exist", 42) == 42
        assert mgr.get("also.missing") is None

    def test_get_auto_init_config(self, clean_env):
        """在 _config 为 None 时，get() 必须自动调用 load()。"""
        m = EnterpriseConfigManager()
        name = m.get("name")
        assert name is not None
        assert m._config is not None


# ========================================================================
# 6. set_runtime() — 运行时覆盖、审计日志、变更监听
# ========================================================================

class TestSetRuntime:
    def test_set_runtime_updates_value(self, mgr):
        mgr.set_runtime("cognitive.twelve_gods.strict_mode", True, reason="test enable strict")
        assert mgr.get("cognitive.twelve_gods.strict_mode") is True

    def test_set_runtime_writes_audit_log(self, mgr):
        mgr.set_runtime("audit_retention", 777, reason="retention tweak")
        log = mgr.get_audit_log(limit=10)
        assert len(log) >= 1
        latest = log[-1]
        assert latest["key"] == "audit_retention"
        assert latest["new_value"] == "777"
        assert latest["source"] == "runtime"
        assert latest["reason"] == "retention tweak"

    def test_set_runtime_fires_listener(self, mgr):
        events = []
        def cb(key, old, new):
            events.append((key, old, new))
        mgr.on_change(cb)
        mgr.set_runtime("hot_reload_interval", 12, reason="listener test")
        assert len(events) == 1
        assert events[0][0] == "hot_reload_interval"
        assert events[0][2] == 12

    def test_remove_listener_stops_events(self, mgr):
        events = []
        def cb(key, old, new):
            events.append(1)
        mgr.on_change(cb)
        mgr.remove_listener(cb)
        mgr.set_runtime("hot_reload_interval", 3, reason="no listener")
        assert events == []

    def test_listener_exception_is_swallowed(self, mgr):
        """监听器抛异常不能影响主流程。"""
        def bad_cb(*a):
            raise RuntimeError("boom")
        mgr.on_change(bad_cb)
        # 不抛异常即可
        mgr.set_runtime("hot_reload_interval", 9)
        assert mgr.get("hot_reload_interval") == 9

    def test_audit_retention_is_truncated(self, mgr):
        """_trim_audit_log 保证审计日志不超过 audit_retention 条。

        注意：set_runtime 内部会调用 load() 重建 _config，所以手动 mgr._config.audit_retention=5 设置会被覆盖。
        正确做法：先 set_runtime("audit_retention", 5) 写入 _runtime_overrides，
        这样每次 load/reload 都把 audit_retention=5 应用到 _config。
        """
        # set_runtime 写进 runtime_overrides → 后续每次 reload 都会应用
        mgr.set_runtime("audit_retention", 5, reason="low retention")
        # 确认 load 后确实是 5
        assert mgr._config.audit_retention == 5
        # 再写 20 条 change
        for i in range(20):
            mgr.set_runtime("hot_reload_interval", i, reason=f"set-{i}")
        # 最终应 <= 5
        assert len(mgr._audit_log) <= 5

    def test_get_audit_summary(self, mgr):
        mgr.set_runtime("hot_reload_interval", 1, reason="a")
        mgr.set_runtime("audit_retention", 200, reason="b")
        summary = mgr.get_audit_summary()
        assert summary["total_changes"] == 2
        assert summary["by_source"].get("runtime") == 2
        assert summary["latest"]["key"] == "audit_retention"

    def test_get_audit_summary_empty(self):
        m = EnterpriseConfigManager()
        m._audit_log = []
        s = m.get_audit_summary()
        assert s["total_changes"] == 0
        assert s["latest"] is None


# ========================================================================
# 7. 热重载 / reload
# ========================================================================

class TestHotReload:
    def test_force_reload_reloads_config(self, clean_env):
        m = EnterpriseConfigManager()
        cfg1 = m.load(auto_env=False, hot_reload=False)
        # 通过 runtime 覆盖改一下，然后 reload 会重新按优先级链构建
        m.set_runtime("name", "overridden", reason="temp")
        assert m.get("name") == "overridden"
        cfg2 = m.reload()
        # reload 也会应用 runtime_overrides，所以名字仍应为 overridden
        assert cfg2.name == "overridden"

    def test_get_config_after_set_runtime_preserves_runtime_value(self, clean_env):
        """yaml 模块不可用时，mtime 机制没有 YAML 文件可监控，但
        set_runtime + get_config 组合必须保证 runtime 值保留。
        """
        m = EnterpriseConfigManager()
        # 不传 config_path，也不加载 YAML
        m.load(config_path="__no_such_file__.yaml", auto_env=False, hot_reload=True)
        # 先 set_runtime 覆盖 name
        m.set_runtime("name", "first-version", reason="set v1")
        assert m.get("name") == "first-version"
        # 改 runtime_overrides 为另一值（模拟 set_runtime）
        m.set_runtime("name", "second-version", reason="set v2")
        # 再次 get_config 必须保留最新 runtime 值
        cfg = m.get_config()
        assert cfg.name == "second-version"


# ========================================================================
# 8. Pydantic 环境验证（或降级路径）
# ========================================================================

class TestEnvironmentValidation:
    def test_invalid_environment_is_refused_via_default_chain(self, clean_env):
        """通过构造 EnterpriseConfig 传递不合法 environment：
        - 有 Pydantic 时抛 ValueError；
        - 无 Pydantic 时降级路径只记录为字符串，不应抛错。
        """
        from tengod.enterprise_config import _PYDANTIC_V2
        if _PYDANTIC_V2:
            with pytest.raises(ValueError):
                EnterpriseConfig(
                    name="x",
                    version="1",
                    environment="invalid-env",
                )
        else:
            # 降级路径：不验证，直接赋值
            cfg = EnterpriseConfig(
                name="x",
                version="1",
                environment="invalid-env",
            )
            assert cfg.environment == "invalid-env"

    def test_valid_environments(self, clean_env):
        for env in ("development", "staging", "production", "testing"):
            cfg = EnterpriseConfig(name="x", version="1", environment=env)
            assert cfg.environment == env


# ========================================================================
# 9. _deep_merge / _set_nested 内部工具（通过行为暴露验证）
# ========================================================================

class TestDeepMerge:
    def test_deep_merge_preserves_unspecified_keys(self, clean_env):
        """YAML 不可用时，直接调用 _deep_merge 内部方法验证：
        base 有完整结构，override 只指定部分字段，未指定字段保留。
        """
        m = EnterpriseConfigManager()
        base = {
            "name": "base-name",
            "environment": "production",
            "cognitive": {
                "tbce": {
                    "default_coordinates": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
                    "drift_warning_threshold": 0.3,
                    "drift_critical_threshold": 0.5,
                    "drift_check_interval": 60,
                },
                "twelve_gods": {
                    "enabled": True,
                    "strict_mode": False,
                    "majority_threshold": 0.5,
                },
            },
        }
        override = {
            "name": "merged-test",
            "environment": "testing",
            "cognitive": {
                "tbce": {
                    "drift_warning_threshold": 0.42,
                },
            },
        }
        merged = m._deep_merge(base, override)
        # 顶层覆盖生效
        assert merged["name"] == "merged-test"
        assert merged["environment"] == "testing"
        # 未被覆盖的默认值保持不变
        assert merged["cognitive"]["twelve_gods"]["enabled"] is True
        assert merged["cognitive"]["twelve_gods"]["strict_mode"] is False
        # 指定的覆盖生效
        assert merged["cognitive"]["tbce"]["drift_warning_threshold"] == pytest.approx(0.42)
        # 默认坐标不变
        assert merged["cognitive"]["tbce"]["default_coordinates"] == [0.5]*6
        # 未在 override 中出现的 tbce.drift_critical_threshold 保留 base 值
        assert merged["cognitive"]["tbce"]["drift_critical_threshold"] == pytest.approx(0.5)


# ========================================================================
# 10. TBCE/十二神/七论 默认配置完整度
# ========================================================================

class TestSubConfigDefaults:
    def test_twelve_gods_defaults(self):
        g = TwelveGodsGateConfig()
        assert g.enabled is True
        assert g.strict_mode is False
        assert g.majority_threshold == pytest.approx(0.5)
        assert g.veto_enabled is True
        assert g.element_boost_enabled is True
        assert g.max_boost == pytest.approx(0.15)
        assert g.auto_retry_count == 3
        assert g.chaos_sea_threshold == pytest.approx(0.4)

    def test_tbce_defaults(self):
        t = TBCEConfig()
        assert t.default_coordinates == [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        assert t.drift_warning_threshold == pytest.approx(0.3)
        assert t.drift_critical_threshold == pytest.approx(0.5)
        assert t.drift_check_interval == 60

    def test_seven_theories_defaults(self):
        s = SevenTheoriesConfig()
        assert s.thresholds["ontology"] == pytest.approx(0.7)
        assert s.thresholds["chaos_sea"] == pytest.approx(0.4)
        assert s.interruptible is True
        assert s.auto_escalate is True

    def test_self_correction_defaults(self):
        s = SelfCorrectionConfig()
        assert s.max_steps == 7
        assert s.step_timeout == pytest.approx(30.0)
        assert s.gate_enforcement is True
        assert s.fallback_strategy == "chaos_sea"

    def test_imaging_defaults(self):
        i = ImagingConfig()
        assert i.stage_timeout == pytest.approx(60.0)
        assert i.fusion_method == "weighted_average"
        assert i.quality_threshold == pytest.approx(0.6)
