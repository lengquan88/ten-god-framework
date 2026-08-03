"""
test_enterprise_config.py — 企业级配置管理器测试
=================================================
覆盖 tengod/enterprise_config.py 的配置加载、验证与覆盖逻辑。

高风险路径：
  1. 线程安全单例——双检锁模式
  2. 环境变量解析与类型转换（bool/int/float/嵌套路径）
  3. _deep_merge 深度合并——嵌套字典递归合并
  4. health_check 健康度自检——多规则验证
  5. _validate_consistency 跨配置一致性校验
  6. set_runtime 运行时覆盖与审计日志
  7. get 点号路径访问
  8. reset_enterprise_config 单例重置
"""

from __future__ import annotations

import os
import threading

import pytest

from tengod.enterprise_config import (
    EnterpriseConfigManager,
    ConfigSource,
    ConfigChangeRecord,
    get_enterprise_config,
    reset_enterprise_config,
)


@pytest.fixture(autouse=True)
def clean_config_singleton():
    """每个测试前重置单例和全局状态，确保隔离"""
    reset_enterprise_config()
    # 同时清理可能影响测试的 TENGOD_* 环境变量
    saved_env = {}
    for key in list(os.environ.keys()):
        if key.startswith("TENGOD_"):
            saved_env[key] = os.environ.pop(key)
    yield
    # 恢复环境变量
    for key, val in saved_env.items():
        os.environ[key] = val
    reset_enterprise_config()


# ============================================================================
# 1. 单例模式测试
# ============================================================================

class TestSingleton:
    """线程安全单例——双检锁模式"""

    def test_singleton_returns_same_instance(self):
        """多次获取应返回同一实例"""
        mgr1 = EnterpriseConfigManager()
        mgr2 = EnterpriseConfigManager()
        assert mgr1 is mgr2

    def test_get_enterprise_config_singleton(self):
        """全局函数返回单例"""
        mgr = get_enterprise_config()
        assert isinstance(mgr, EnterpriseConfigManager)
        assert get_enterprise_config() is mgr

    def test_reset_creates_new_instance(self):
        """reset 后应创建新实例"""
        mgr1 = get_enterprise_config()
        reset_enterprise_config()
        mgr2 = get_enterprise_config()
        assert mgr1 is not mgr2

    def test_singleton_thread_safety(self):
        """多线程并发获取单例应安全"""
        reset_enterprise_config()
        instances = []

        def get_instance():
            instances.append(EnterpriseConfigManager())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有线程应获得同一实例
        assert all(inst is instances[0] for inst in instances)


# ============================================================================
# 2. 配置加载测试
# ============================================================================

class TestConfigLoad:
    """load() 配置加载与默认值"""

    def test_load_with_defaults(self):
        """无配置文件时加载默认值"""
        mgr = EnterpriseConfigManager()
        cfg = mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        assert cfg.name == "tengod-enterprise"
        assert cfg.environment == "production"
        assert cfg.cognitive.twelve_gods.enabled is True

    def test_load_environment_from_env(self):
        """环境变量覆盖默认值"""
        os.environ["TENGOD_ENV"] = "testing"
        mgr = EnterpriseConfigManager()
        cfg = mgr.load(config_path="/nonexistent/path.yaml", auto_env=True)
        assert cfg.environment == "testing"

    def test_load_hot_reload_from_env(self):
        """环境变量 bool 类型转换"""
        os.environ["TENGOD_HOT_RELOAD"] = "false"
        mgr = EnterpriseConfigManager()
        cfg = mgr.load(config_path="/nonexistent/path.yaml", auto_env=True)
        assert cfg.hot_reload is False

    def test_load_hot_reload_true_string(self):
        """'true' 字符串正确转换为 True"""
        os.environ["TENGOD_HOT_RELOAD"] = "true"
        mgr = EnterpriseConfigManager()
        cfg = mgr.load(config_path="/nonexistent/path.yaml", auto_env=True)
        assert cfg.hot_reload is True

    def test_load_interval_from_env(self):
        """环境变量 int 类型转换"""
        os.environ["TENGOD_HOT_RELOAD_INTERVAL"] = "15"
        mgr = EnterpriseConfigManager()
        cfg = mgr.load(config_path="/nonexistent/path.yaml", auto_env=True)
        assert cfg.hot_reload_interval == 15

    def test_load_invalid_env_value_skipped(self):
        """无效环境变量值应被跳过，不崩溃"""
        os.environ["TENGOD_HOT_RELOAD_INTERVAL"] = "not_a_number"
        mgr = EnterpriseConfigManager()
        cfg = mgr.load(config_path="/nonexistent/path.yaml", auto_env=True)
        # 应回退到默认值
        assert cfg.hot_reload_interval == 5

    def test_load_nested_env_override(self):
        """嵌套路径环境变量覆盖"""
        os.environ["TENGOD_TWELVE_GODS_ENABLED"] = "false"
        os.environ["TENGOD_MAJORITY_THRESHOLD"] = "0.75"
        mgr = EnterpriseConfigManager()
        cfg = mgr.load(config_path="/nonexistent/path.yaml", auto_env=True)
        assert cfg.cognitive.twelve_gods.enabled is False
        assert cfg.cognitive.twelve_gods.majority_threshold == 0.75


# ============================================================================
# 3. 深度合并测试
# ============================================================================

class TestDeepMerge:
    """_deep_merge() 嵌套字典递归合并"""

    def test_merge_disjoint_keys(self):
        """不重叠的键直接合并"""
        mgr = EnterpriseConfigManager()
        result = mgr._deep_merge({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_merge_override_scalar(self):
        """标量值被覆盖"""
        mgr = EnterpriseConfigManager()
        result = mgr._deep_merge({"a": 1}, {"a": 2})
        assert result == {"a": 2}

    def test_merge_nested_dicts(self):
        """嵌套字典递归合并"""
        mgr = EnterpriseConfigManager()
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 20, "z": 30}}
        result = mgr._deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 20, "z": 30}, "b": 3}

    def test_merge_does_not_mutate_base(self):
        """合并不应修改原始 base 字典"""
        mgr = EnterpriseConfigManager()
        base = {"a": {"x": 1}}
        mgr._deep_merge(base, {"a": {"y": 2}})
        assert base == {"a": {"x": 1}}

    def test_merge_dict_replaces_non_dict(self):
        """当 base 值非 dict 但 override 是 dict 时，override 替换"""
        mgr = EnterpriseConfigManager()
        result = mgr._deep_merge({"a": 1}, {"a": {"nested": True}})
        assert result == {"a": {"nested": True}}


# ============================================================================
# 4. 健康度自检测试
# ============================================================================

class TestHealthCheck:
    """health_check() 配置健康度自检"""

    def test_healthy_config(self):
        """默认配置应健康"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        result = mgr.health_check()
        assert result["status"] in ("healthy", "warning")

    def test_drift_threshold_inversion_detected(self):
        """TBCE 漂移警告阈值 >= 严重阈值应报 issue"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        # 运行时覆盖：让 warning >= critical
        mgr.set_runtime("cognitive.tbce.drift_warning_threshold", 0.6)
        mgr.set_runtime("cognitive.tbce.drift_critical_threshold", 0.5)
        result = mgr.health_check()
        assert result["status"] == "unhealthy"
        assert any("漂移" in issue for issue in result["issues"])


# ============================================================================
# 5. 运行时覆盖与审计测试
# ============================================================================

class TestRuntimeOverride:
    """set_runtime() 运行时覆盖与审计日志"""

    def test_runtime_override_applied(self):
        """运行时覆盖应生效"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        mgr.set_runtime("environment", "staging")
        cfg = mgr.get_config()
        assert cfg.environment == "staging"

    def test_runtime_override_audited(self):
        """运行时覆盖应记录审计日志"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        mgr.set_runtime("environment", "staging", reason="deploy")
        log = mgr.get_audit_log()
        assert len(log) >= 1
        latest = log[-1]
        assert latest["key"] == "environment"
        assert latest["new_value"] == "staging"
        assert latest["source"] == "runtime"

    def test_runtime_override_nested_path(self):
        """运行时覆盖嵌套路径"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        mgr.set_runtime("cognitive.twelve_gods.strict_mode", True)
        cfg = mgr.get_config()
        assert cfg.cognitive.twelve_gods.strict_mode is True

    def test_change_listener_called(self):
        """变更监听器应被回调"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        received = []
        mgr.on_change(lambda key, old, new: received.append((key, old, new)))
        mgr.set_runtime("environment", "testing")
        assert len(received) >= 1
        assert received[-1][0] == "environment"
        assert received[-1][2] == "testing"

    def test_change_listener_exception_swallowed(self):
        """监听器异常不应影响覆盖操作"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)

        def bad_listener(key, old, new):
            raise RuntimeError("listener error")

        mgr.on_change(bad_listener)
        # 不应抛出异常
        mgr.set_runtime("environment", "testing")
        assert mgr.get_config().environment == "testing"

    def test_remove_listener(self):
        """移除监听器后不再被回调"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        received = []

        def listener(key, old, new):
            received.append(key)

        mgr.on_change(listener)
        mgr.set_runtime("environment", "testing")
        mgr.remove_listener(listener)
        mgr.set_runtime("environment", "production")
        # 只有第一次覆盖触发了监听器
        assert len(received) == 1


# ============================================================================
# 6. 点号路径访问测试
# ============================================================================

class TestGetByKeyPath:
    """get() 点号分隔路径访问"""

    def test_get_top_level(self):
        """顶层键访问"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        assert mgr.get("name") == "tengod-enterprise"

    def test_get_nested(self):
        """嵌套路径访问"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        assert mgr.get("cognitive.twelve_gods.enabled") is True

    def test_get_deep_nested(self):
        """深层嵌套路径访问"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        val = mgr.get("cognitive.twelve_gods.majority_threshold")
        assert val == 0.5

    def test_get_missing_key_returns_default(self):
        """不存在的键返回默认值"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        assert mgr.get("nonexistent.key", "fallback") == "fallback"

    def test_get_missing_nested_returns_default(self):
        """不存在的嵌套键返回默认值"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        assert mgr.get("cognitive.nonexistent.field", None) is None


# ============================================================================
# 7. 配置来源追踪测试
# ============================================================================

class TestConfigSource:
    """配置来源追踪"""

    def test_default_source_for_unset_key(self):
        """未设置的键来源为 DEFAULT"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        assert mgr.get_source("nonexistent") == ConfigSource.DEFAULT

    def test_env_source_recorded(self):
        """环境变量覆盖的键来源为 ENV"""
        os.environ["TENGOD_ENV"] = "testing"
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=True)
        assert mgr.get_source("environment") == ConfigSource.ENV


# ============================================================================
# 8. 审计摘要测试
# ============================================================================

class TestAuditSummary:
    """get_audit_summary() 审计摘要"""

    def test_empty_audit_summary(self):
        """无变更时摘要为空"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        summary = mgr.get_audit_summary()
        assert summary["total_changes"] == 0
        assert summary["latest"] is None

    def test_summary_after_changes(self):
        """变更后摘要正确"""
        mgr = EnterpriseConfigManager()
        mgr.load(config_path="/nonexistent/path.yaml", auto_env=False)
        mgr.set_runtime("environment", "staging")
        mgr.set_runtime("environment", "production")
        summary = mgr.get_audit_summary()
        assert summary["total_changes"] >= 2
        assert summary["by_source"].get("runtime", 0) >= 2
        assert summary["latest"] is not None
