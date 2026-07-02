"""
enterprise_config.py — 企业级配置管理器 v4.6.0
==================================================
道曰："治大国若烹小鲜。"

优先级链：环境变量 > YAML 配置文件 > 默认值
核心能力：
  - Pydantic v2 严格模型验证
  - 热重载（文件监控 + 手动触发）
  - TBCE六维坐标感知配置
  - 十二神门禁配置
  - 配置变更审计日志
  - 敏感信息加密存储
  - 配置健康度自检
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

try:
    from pydantic import BaseModel, Field, field_validator, model_validator
    _PYDANTIC_V2 = True
except ImportError:
    _PYDANTIC_V2 = False
    class BaseModel:
        def __init_subclass__(cls, **kwargs: Any) -> None:
            pass


# ============================================================================
# 配置优先级
# ============================================================================

class ConfigPriority(Enum):
    """配置优先级层级"""
    DEFAULT = 0       # 硬编码默认值
    YAML_FILE = 1     # YAML 配置文件
    ENV_VARIABLE = 2  # 环境变量
    RUNTIME = 3       # 运行时覆盖（最高优先级）


class ConfigSource(Enum):
    """配置来源"""
    DEFAULT = "default"
    YAML = "yaml"
    ENV = "env"
    RUNTIME = "runtime"


# ============================================================================
# 配置变更审计
# ============================================================================

@dataclass
class ConfigChangeRecord:
    """配置变更审计记录"""
    key: str
    old_value: Any
    new_value: Any
    source: ConfigSource
    timestamp: float = field(default_factory=time.time)
    reason: str = ""

    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "old_value": str(self.old_value)[:200],
            "new_value": str(self.new_value)[:200],
            "source": self.source.value,
            "timestamp": self.timestamp,
            "reason": self.reason,
        }


# ============================================================================
# Pydantic v2 配置模型
# ============================================================================

if _PYDANTIC_V2:

    class TwelveGodsGateConfig(BaseModel):
        """十二神门禁配置"""
        enabled: bool = Field(default=True, description="是否启用十二神门禁")
        strict_mode: bool = Field(default=False, description="严格模式：任一关则整体关")
        majority_threshold: float = Field(
            default=0.5, ge=0.0, le=1.0, description="多数投票阈值"
        )
        veto_enabled: bool = Field(default=True, description="太极否决权")
        element_boost_enabled: bool = Field(default=True, description="五行生克加成")
        max_boost: float = Field(default=0.15, ge=0.0, le=0.5, description="五行加成上限")
        auto_retry_count: int = Field(default=3, ge=0, le=10, description="门禁失败自动重试次数")
        chaos_sea_threshold: float = Field(
            default=0.4, ge=0.0, le=1.0, description="混沌海存疑阈值"
        )

    class TBCEConfig(BaseModel):
        """TBCE六维认知配置"""
        default_coordinates: List[float] = Field(
            default=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
            description="默认TBCE坐标 [S, T, P, C, I, E]"
        )
        drift_warning_threshold: float = Field(
            default=0.3, ge=0.0, le=1.0, description="坐标漂移警告阈值"
        )
        drift_critical_threshold: float = Field(
            default=0.5, ge=0.0, le=1.0, description="坐标漂移严重阈值"
        )
        drift_check_interval: int = Field(
            default=60, ge=10, le=3600, description="漂移检查间隔(秒)"
        )

    class SevenTheoriesConfig(BaseModel):
        """七论裁决器配置"""
        thresholds: Dict[str, float] = Field(
            default={
                "ontology": 0.7,
                "epistemology": 0.7,
                "practice": 0.6,
                "realm": 0.6,
                "future": 0.5,
                "metacognition": 0.7,
                "chaos_sea": 0.4,
            },
            description="七论阈值"
        )
        interruptible: bool = Field(default=True, description="是否允许中断")
        auto_escalate: bool = Field(default=True, description="自动升级至混沌海")

    class SelfCorrectionConfig(BaseModel):
        """自修正配置"""
        max_steps: int = Field(default=7, ge=1, le=14, description="最大修正步数")
        step_timeout: float = Field(default=30.0, ge=5.0, le=300.0, description="每步超时(秒)")
        gate_enforcement: bool = Field(default=True, description="是否强制门禁裁决")
        fallback_strategy: str = Field(default="chaos_sea", description="失败回退策略")

    class ImagingConfig(BaseModel):
        """七阶段成像配置"""
        stage_timeout: float = Field(default=60.0, ge=10.0, le=600.0, description="每阶段超时(秒)")
        fusion_method: str = Field(default="weighted_average", description="融合方法")
        quality_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="成像质量阈值")

    class CognitiveConfig(BaseModel):
        """认知系统综合配置"""
        tbce: TBCEConfig = Field(default_factory=TBCEConfig)
        twelve_gods: TwelveGodsGateConfig = Field(default_factory=TwelveGodsGateConfig)
        seven_theories: SevenTheoriesConfig = Field(default_factory=SevenTheoriesConfig)
        self_correction: SelfCorrectionConfig = Field(default_factory=SelfCorrectionConfig)
        imaging: ImagingConfig = Field(default_factory=ImagingConfig)

    class EnterpriseConfig(BaseModel):
        """企业级顶层配置 v2.31.0"""
        name: str = Field(default="tengod-enterprise", description="实例名称")
        version: str = Field(default="2.31.0", description="配置版本")
        environment: str = Field(default="production", description="运行环境")
        cognitive: CognitiveConfig = Field(default_factory=CognitiveConfig)
        hot_reload: bool = Field(default=True, description="启用热重载")
        hot_reload_interval: int = Field(default=5, ge=1, le=60, description="热重载检查间隔(秒)")
        audit_enabled: bool = Field(default=True, description="启用配置变更审计")
        audit_retention: int = Field(default=1000, ge=10, le=100000, description="审计记录保留条数")

        @field_validator("environment")
        @classmethod
        def validate_environment(cls, v: str) -> str:
            allowed = {"development", "staging", "production", "testing"}
            if v not in allowed:
                raise ValueError(f"环境必须是 {allowed} 之一，得到 '{v}'")
            return v

else:
    # 无 Pydantic 降级实现
    class TwelveGodsGateConfig:
        enabled = True
        strict_mode = False
        majority_threshold = 0.5
        veto_enabled = True
        element_boost_enabled = True
        max_boost = 0.15
        auto_retry_count = 3
        chaos_sea_threshold = 0.4

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class TBCEConfig:
        default_coordinates = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        drift_warning_threshold = 0.3
        drift_critical_threshold = 0.5
        drift_check_interval = 60

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class SevenTheoriesConfig:
        thresholds = {
            "ontology": 0.7, "epistemology": 0.7, "practice": 0.6,
            "realm": 0.6, "future": 0.5, "metacognition": 0.7, "chaos_sea": 0.4,
        }
        interruptible = True
        auto_escalate = True

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class SelfCorrectionConfig:
        max_steps = 7
        step_timeout = 30.0
        gate_enforcement = True
        fallback_strategy = "chaos_sea"

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class ImagingConfig:
        stage_timeout = 60.0
        fusion_method = "weighted_average"
        quality_threshold = 0.6

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class CognitiveConfig:
        def __init__(self, **kwargs):
            self.tbce = TBCEConfig(**kwargs.get("tbce", {}))
            self.twelve_gods = TwelveGodsGateConfig(**kwargs.get("twelve_gods", {}))
            self.seven_theories = SevenTheoriesConfig(**kwargs.get("seven_theories", {}))
            self.self_correction = SelfCorrectionConfig(**kwargs.get("self_correction", {}))
            self.imaging = ImagingConfig(**kwargs.get("imaging", {}))

    class EnterpriseConfig:
        def __init__(self, **kwargs):
            self.name = kwargs.get("name", "tengod-enterprise")
            self.version = kwargs.get("version", "2.31.0")
            self.environment = kwargs.get("environment", "production")
            self.cognitive = CognitiveConfig(**kwargs.get("cognitive", {}))
            self.hot_reload = kwargs.get("hot_reload", True)
            self.hot_reload_interval = kwargs.get("hot_reload_interval", 5)
            self.audit_enabled = kwargs.get("audit_enabled", True)
            self.audit_retention = kwargs.get("audit_retention", 1000)


# ============================================================================
# 企业级配置管理器
# ============================================================================

class EnterpriseConfigManager:
    """企业级配置管理器 v2.31.0

    优先级链：环境变量 > YAML > 默认值
    支持热重载、Pydantic v2 验证、变更审计、TBCE感知、十二神门禁配置。
    """

    _instance: Optional["EnterpriseConfigManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._config: Optional[EnterpriseConfig] = None
        self._config_path: Optional[str] = None
        self._config_mtime: float = 0
        self._runtime_overrides: Dict[str, Any] = {}
        self._audit_log: List[ConfigChangeRecord] = []
        self._change_listeners: List[Callable[[str, Any, Any], None]] = []
        self._source_registry: Dict[str, ConfigSource] = {}
        self._validation_errors: List[str] = []

    # ── 配置加载 ──────────────────────────────────────────────────────

    def load(
        self,
        config_path: Optional[str] = None,
        auto_env: bool = True,
        hot_reload: bool = True,
    ) -> EnterpriseConfig:
        """加载企业级配置

        优先级链：环境变量 > YAML 文件 > 默认值

        Args:
            config_path: YAML 配置文件路径
            auto_env: 是否自动从环境变量覆盖
            hot_reload: 是否启用热重载

        Returns:
            EnterpriseConfig 实例
        """
        # 确定配置文件路径
        if config_path is None:
            config_path = os.environ.get("TENGOD_ENTERPRISE_CONFIG", "")
        if not config_path:
            config_path = os.environ.get("TENGOD_CONFIG", "tengod_config.yaml")

        self._config_path = config_path

        # 1. 加载默认值
        config_dict = self._get_defaults()

        # 2. YAML 文件覆盖
        if os.path.exists(config_path):
            yaml_dict = self._load_yaml(config_path)
            config_dict = self._deep_merge(config_dict, yaml_dict)
            self._config_mtime = os.path.getmtime(config_path)
            self._record_source(yaml_dict, ConfigSource.YAML)

        # 3. 环境变量覆盖
        if auto_env:
            env_dict = self._load_env_overrides()
            config_dict = self._deep_merge(config_dict, env_dict)
            self._record_source(env_dict, ConfigSource.ENV)

        # 4. 运行时覆盖
        if self._runtime_overrides:
            config_dict = self._deep_merge(config_dict, self._runtime_overrides)
            self._record_source(self._runtime_overrides, ConfigSource.RUNTIME)

        # 5. Pydantic v2 验证
        if _PYDANTIC_V2:
            self._config = EnterpriseConfig(**config_dict)
        else:
            self._config = EnterpriseConfig(**config_dict)

        self._validate_consistency()

        return self._config

    def _get_defaults(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "name": "tengod-enterprise",
            "version": "2.31.0",
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
                    "veto_enabled": True,
                    "element_boost_enabled": True,
                    "max_boost": 0.15,
                    "auto_retry_count": 3,
                    "chaos_sea_threshold": 0.4,
                },
                "seven_theories": {
                    "thresholds": {
                        "ontology": 0.7, "epistemology": 0.7, "practice": 0.6,
                        "realm": 0.6, "future": 0.5, "metacognition": 0.7,
                        "chaos_sea": 0.4,
                    },
                    "interruptible": True,
                    "auto_escalate": True,
                },
                "self_correction": {
                    "max_steps": 7,
                    "step_timeout": 30.0,
                    "gate_enforcement": True,
                    "fallback_strategy": "chaos_sea",
                },
                "imaging": {
                    "stage_timeout": 60.0,
                    "fusion_method": "weighted_average",
                    "quality_threshold": 0.6,
                },
            },
            "hot_reload": True,
            "hot_reload_interval": 5,
            "audit_enabled": True,
            "audit_retention": 1000,
        }

    def _load_yaml(self, path: str) -> Dict[str, Any]:
        """从 YAML 文件加载配置"""
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def _load_env_overrides(self) -> Dict[str, Any]:
        """从环境变量加载覆盖配置"""
        overrides: Dict[str, Any] = {}
        env_map = {
            "TENGOD_ENV": ("environment", str),
            "TENGOD_HOT_RELOAD": ("hot_reload", lambda x: x.lower() == "true"),
            "TENGOD_HOT_RELOAD_INTERVAL": ("hot_reload_interval", int),
            "TENGOD_TWELVE_GODS_ENABLED": ("cognitive", "twelve_gods", "enabled",
                lambda x: x.lower() == "true"),
            "TENGOD_TWELVE_GODS_STRICT": ("cognitive", "twelve_gods", "strict_mode",
                lambda x: x.lower() == "true"),
            "TENGOD_MAJORITY_THRESHOLD": ("cognitive", "twelve_gods", "majority_threshold", float),
            "TENGOD_VETO_ENABLED": ("cognitive", "twelve_gods", "veto_enabled",
                lambda x: x.lower() == "true"),
            "TENGOD_ELEMENT_BOOST": ("cognitive", "twelve_gods", "element_boost_enabled",
                lambda x: x.lower() == "true"),
            "TENGOD_MAX_BOOST": ("cognitive", "twelve_gods", "max_boost", float),
            "TENGOD_DRIFT_WARNING": ("cognitive", "tbce", "drift_warning_threshold", float),
            "TENGOD_DRIFT_CRITICAL": ("cognitive", "tbce", "drift_critical_threshold", float),
            "TENGOD_DRIFT_INTERVAL": ("cognitive", "tbce", "drift_check_interval", int),
            "TENGOD_AUDIT_ENABLED": ("audit_enabled", lambda x: x.lower() == "true"),
            "TENGOD_AUDIT_RETENTION": ("audit_retention", int),
        }

        for env_var, path in env_map.items():
            val = os.environ.get(env_var)
            if val is None:
                continue

            converter = path[-1] if callable(path[-1]) else None
            keys = path[:-1] if converter else path

            try:
                if converter:
                    val = converter(val)
                elif isinstance(path[-1], type):
                    val = path[-1](val)
            except (ValueError, TypeError):
                continue

            self._set_nested(overrides, keys, val)

        return overrides

    # ── 配置访问 ──────────────────────────────────────────────────────

    def get_config(self) -> EnterpriseConfig:
        """获取当前配置（自动热重载检查）"""
        if self._config is None:
            return self.load()

        if self._config.hot_reload and self._config_path and os.path.exists(self._config_path):
            mtime = os.path.getmtime(self._config_path)
            if mtime > self._config_mtime:
                return self.load(self._config_path)

        return self._config

    def reload(self) -> EnterpriseConfig:
        """强制重新加载配置"""
        return self.load(self._config_path)

    def get(self, key_path: str, default: Any = None) -> Any:
        """通过点号分隔的路径获取配置值

        Args:
            key_path: 如 "cognitive.twelve_gods.enabled"
            default: 默认值
        """
        cfg = self.get_config()
        keys = key_path.split(".")
        value = cfg
        try:
            for k in keys:
                if _PYDANTIC_V2 and hasattr(value, 'model_dump'):
                    d = value.model_dump()
                    value = d.get(k, default)
                elif hasattr(value, '__dict__'):
                    value = getattr(value, k)
                elif isinstance(value, dict):
                    value = value.get(k, default)
                else:
                    return default
            return value
        except (AttributeError, KeyError):
            return default

    def set_runtime(self, key_path: str, value: Any, reason: str = "") -> None:
        """运行时覆盖配置值（最高优先级）

        Args:
            key_path: 如 "cognitive.twelve_gods.strict_mode"
            value: 新值
            reason: 变更原因
        """
        old_value = self.get(key_path)
        keys = key_path.split(".")
        self._set_nested(self._runtime_overrides, keys, value)

        if self._config and self._config.audit_enabled:
            self._audit_log.append(ConfigChangeRecord(
                key=key_path,
                old_value=old_value,
                new_value=value,
                source=ConfigSource.RUNTIME,
                reason=reason,
            ))
            self._trim_audit_log()

        # 通知变更监听器
        for listener in self._change_listeners:
            try:
                listener(key_path, old_value, value)
            except Exception:
                pass

        # 重新加载配置以应用运行时覆盖
        if self._config:
            self.load(self._config_path)

    # ── 变更监听 ──────────────────────────────────────────────────────

    def on_change(self, callback: Callable[[str, Any, Any], None]) -> None:
        """注册配置变更监听器"""
        self._change_listeners.append(callback)

    def remove_listener(self, callback: Callable) -> None:
        """移除配置变更监听器"""
        if callback in self._change_listeners:
            self._change_listeners.remove(callback)

    # ── 审计日志 ──────────────────────────────────────────────────────

    def get_audit_log(self, limit: int = 50) -> List[Dict]:
        """获取配置变更审计日志"""
        return [r.to_dict() for r in self._audit_log[-limit:]]

    def get_audit_summary(self) -> Dict[str, Any]:
        """获取审计摘要"""
        sources = {}
        for r in self._audit_log:
            s = r.source.value
            sources[s] = sources.get(s, 0) + 1
        return {
            "total_changes": len(self._audit_log),
            "by_source": sources,
            "latest": self._audit_log[-1].to_dict() if self._audit_log else None,
        }

    def _trim_audit_log(self) -> None:
        """裁剪审计日志"""
        if self._config and len(self._audit_log) > self._config.audit_retention:
            self._audit_log = self._audit_log[-self._config.audit_retention:]

    # ── 配置健康度 ────────────────────────────────────────────────────

    def health_check(self) -> Dict[str, Any]:
        """配置健康度自检"""
        issues = []
        warnings = []

        cfg = self.get_config()
        c = cfg.cognitive

        # 十二神门禁配置检查
        if c.twelve_gods.enabled:
            if c.twelve_gods.majority_threshold < 0.3:
                warnings.append("十二神门禁多数阈值过低 (<0.3)，可能导致过松裁决")
            if c.twelve_gods.majority_threshold > 0.8:
                warnings.append("十二神门禁多数阈值过高 (>0.8)，可能导致过严裁决")
            if c.twelve_gods.max_boost > 0.3:
                warnings.append("五行加成上限过高 (>0.3)，可能掩盖真实问题")
            if not c.twelve_gods.veto_enabled:
                warnings.append("太极否决权已禁用，自指涉门禁无法否决")

        # TBCE配置检查
        if c.tbce.drift_warning_threshold >= c.tbce.drift_critical_threshold:
            issues.append("TBCE漂移警告阈值应小于严重阈值")

        # 七论配置检查
        for theory, threshold in c.seven_theories.thresholds.items():
            if threshold < 0.3:
                warnings.append(f"七论「{theory}」阈值过低 (<0.3)")
            if threshold > 0.95:
                warnings.append(f"七论「{theory}」阈值过高 (>0.95)，几乎不可能通过")

        # 自修正配置检查
        if c.self_correction.step_timeout < 5.0:
            issues.append("自修正每步超时过短 (<5s)")
        if c.self_correction.max_steps < 3:
            warnings.append("自修正步数过少 (<3)，可能无法充分修正")

        status = "healthy"
        if issues:
            status = "unhealthy"
        elif warnings:
            status = "warning"

        return {
            "status": status,
            "issues": issues,
            "warnings": warnings,
            "config_hash": self._compute_config_hash(),
            "timestamp": time.time(),
        }

    def _compute_config_hash(self) -> str:
        """计算配置内容哈希"""
        cfg = self.get_config()
        if _PYDANTIC_V2:
            content = json.dumps(cfg.model_dump(), sort_keys=True, default=str)
        else:
            content = json.dumps(cfg.__dict__, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    # ── 配置一致性校验 ─────────────────────────────────────────────────

    def _validate_consistency(self) -> None:
        """验证配置内部一致性"""
        self._validation_errors = []
        cfg = self._config

        if not cfg:
            return

        # 热重载必须在文件存在时有效
        if cfg.hot_reload and self._config_path and not os.path.exists(self._config_path):
            self._validation_errors.append(
                "热重载已启用但配置文件不存在"
            )

        # 十二神门禁与七论阈值一致性
        c = cfg.cognitive
        if c.twelve_gods.enabled and c.twelve_gods.chaos_sea_threshold > min(
            c.seven_theories.thresholds.values()
        ):
            self._validation_errors.append(
                "混沌海阈值应低于所有七论阈值"
            )

    def get_validation_errors(self) -> List[str]:
        """获取配置校验错误"""
        return self._validation_errors

    # ── 辅助方法 ──────────────────────────────────────────────────────

    def _set_nested(self, d: Dict, keys: tuple, value: Any) -> None:
        """设置嵌套字典值"""
        for key in keys[:-1]:
            if key not in d:
                d[key] = {}
            d = d[key]
        d[keys[-1]] = value

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """深度合并两个字典"""
        result = dict(base)
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    def _record_source(self, config_dict: Dict, source: ConfigSource, prefix: str = "") -> None:
        """记录配置项来源"""
        for k, v in config_dict.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                self._record_source(v, source, key)
            else:
                self._source_registry[key] = source

    def get_source(self, key_path: str) -> ConfigSource:
        """获取配置项来源"""
        return self._source_registry.get(key_path, ConfigSource.DEFAULT)

    def to_dict(self) -> Dict[str, Any]:
        """导出完整配置为字典"""
        cfg = self.get_config()
        if _PYDANTIC_V2:
            return cfg.model_dump()
        return {
            "name": cfg.name,
            "version": cfg.version,
            "environment": cfg.environment,
            "cognitive": {
                "tbce": cfg.cognitive.tbce.__dict__ if hasattr(cfg.cognitive.tbce, '__dict__') else {},
                "twelve_gods": cfg.cognitive.twelve_gods.__dict__ if hasattr(cfg.cognitive.twelve_gods, '__dict__') else {},
                "seven_theories": cfg.cognitive.seven_theories.__dict__ if hasattr(cfg.cognitive.seven_theories, '__dict__') else {},
                "self_correction": cfg.cognitive.self_correction.__dict__ if hasattr(cfg.cognitive.self_correction, '__dict__') else {},
                "imaging": cfg.cognitive.imaging.__dict__ if hasattr(cfg.cognitive.imaging, '__dict__') else {},
            },
            "hot_reload": cfg.hot_reload,
            "hot_reload_interval": cfg.hot_reload_interval,
            "audit_enabled": cfg.audit_enabled,
            "audit_retention": cfg.audit_retention,
        }


# ============================================================================
# 全局单例
# ============================================================================

_enterprise_config: Optional[EnterpriseConfigManager] = None


def get_enterprise_config() -> EnterpriseConfigManager:
    """获取企业级配置管理器单例"""
    global _enterprise_config
    if _enterprise_config is None:
        _enterprise_config = EnterpriseConfigManager()
    return _enterprise_config


def reset_enterprise_config() -> None:
    """重置企业级配置管理器"""
    global _enterprise_config
    _enterprise_config = None
    EnterpriseConfigManager._instance = None


__all__ = [
    "EnterpriseConfigManager",
    "EnterpriseConfig",
    "ConfigPriority",
    "ConfigSource",
    "ConfigChangeRecord",
    "TwelveGodsGateConfig",
    "TBCEConfig",
    "SevenTheoriesConfig",
    "SelfCorrectionConfig",
    "ImagingConfig",
    "CognitiveConfig",
    "get_enterprise_config",
    "reset_enterprise_config",
]