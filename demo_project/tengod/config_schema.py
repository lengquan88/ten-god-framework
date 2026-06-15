#!/usr/bin/env python3
"""
config_schema.py — Pydantic v2 配置 Schema 严格校验 v2.0.1
==============================================================
用 Pydantic v2 定义所有配置项的严格类型、范围和约束。
运行时自动校验 + 自动填充默认值 + 友好的错误提示。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal

try:
    from pydantic import BaseModel, Field, field_validator, model_validator

    _PYDANTIC_V2 = True
except ImportError:
    _PYDANTIC_V2 = False

    # 纯 Python 降级实现
    class BaseModel:
        def __init_subclass__(cls, **kwargs: Any) -> None:
            pass


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class DBBackend(str, Enum):
    MEMORY = "memory"
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    JSON = "json"


class ServerMode(str, Enum):
    FASTAPI = "fastapi"
    SIMPLE = "simple"
    AUTO = "auto"


if _PYDANTIC_V2:

    class ServerConfig(BaseModel):
        """HTTP 服务器配置"""

        host: str = Field(default="0.0.0.0", description="绑定地址")
        port: int = Field(default=8000, ge=1024, le=65535, description="绑定端口")
        mode: ServerMode = Field(default=ServerMode.AUTO, description="服务器模式")
        workers: int = Field(default=1, ge=1, le=16, description="Worker数量")
        cors_origins: List[str] = Field(default=["*"], description="CORS 允许源")

    class DatabaseConfig(BaseModel):
        """数据库配置"""

        backend: DBBackend = Field(default=DBBackend.MEMORY, description="数据库后端")
        url: str = Field(default="", description="数据库连接URL")
        pool_size: int = Field(default=5, ge=1, le=50, description="连接池大小")
        wal_mode: bool = Field(default=True, description="SQLite WAL模式")
        echo_sql: bool = Field(default=False, description="打印SQL日志")

    class LLMConfig(BaseModel):
        """LLM 配置"""

        provider: str = Field(default="openai", description="LLM提供商")
        api_key: str = Field(default="", description="API密钥")
        api_base: str = Field(default="", description="API基础URL")
        model: str = Field(default="gpt-3.5-turbo", description="模型名称")
        temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度")
        max_tokens: int = Field(
            default=2048, ge=1, le=128000, description="最大输出token"
        )
        timeout: float = Field(
            default=60.0, ge=5.0, le=600.0, description="请求超时(秒)"
        )
        max_retries: int = Field(default=3, ge=0, le=10, description="最大重试次数")
        retry_backoff: float = Field(
            default=2.0, ge=0.5, le=10.0, description="重试退避系数"
        )

    class SecurityConfig(BaseModel):
        """安全配置"""

        jwt_secret: str = Field(default="", description="JWT签名密钥")
        jwt_algorithm: str = Field(default="HS256", description="JWT算法")
        jwt_expire_minutes: int = Field(
            default=60, ge=1, le=1440, description="JWT过期(分钟)"
        )
        rate_limit_capacity: int = Field(
            default=100, ge=1, le=10000, description="令牌桶容量"
        )
        rate_limit_refill_rate: float = Field(
            default=10.0, ge=0.1, le=100.0, description="令牌桶填充速率"
        )
        audit_enabled: bool = Field(default=True, description="审计日志")
        audit_backend: str = Field(default="sqlite", description="审计存储后端")

    class SchedulerConfig(BaseModel):
        """任务调度配置"""

        max_workers: int = Field(default=4, ge=1, le=64, description="最大Worker数")
        timeout: int = Field(default=30, ge=1, le=3600, description="任务超时(秒)")
        queue_size: int = Field(default=100, ge=1, le=10000, description="队列大小")
        cache_enabled: bool = Field(default=True, description="启用缓存")
        cache_size: int = Field(
            default=1000, ge=10, le=100000, description="缓存条目数"
        )

    class ConsensusConfig(BaseModel):
        """共识配置"""

        enabled: bool = Field(default=False, description="启用共识")
        node_id: str = Field(default="", description="节点ID")
        peer_addresses: List[str] = Field(default=[], description="对等节点地址")
        election_timeout_min: float = Field(
            default=5.0, ge=1.0, le=60.0, description="选举超时下限"
        )
        election_timeout_max: float = Field(
            default=10.0, ge=2.0, le=120.0, description="选举超时上限"
        )
        heartbeat_interval: float = Field(
            default=2.0, ge=0.5, le=30.0, description="心跳间隔"
        )

    class KnowledgeConfig(BaseModel):
        """知识库配置"""

        backend: DBBackend = Field(default=DBBackend.MEMORY, description="存储后端")
        vector_enabled: bool = Field(default=False, description="启用向量搜索")
        vector_backend: Literal["faiss", "chromadb", "auto"] = Field(
            default="auto", description="向量后端"
        )
        max_node_size: int = Field(
            default=10000, ge=100, le=1000000, description="最大节点数"
        )
        index_path: str = Field(default="", description="FAISS索引路径")

    class MonitoringConfig(BaseModel):
        """监控配置"""

        prometheus_enabled: bool = Field(default=True, description="启用Prometheus指标")
        log_level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")
        log_format: Literal["json", "text"] = Field(
            default="json", description="日志格式"
        )
        health_check_interval: int = Field(
            default=30, ge=10, le=300, description="健康检查间隔(秒)"
        )

    class TengodConfig(BaseModel):
        """十神架构顶层配置 v2.0.1"""

        name: str = Field(default="tengod", description="实例名称")
        server: ServerConfig = Field(default_factory=ServerConfig)
        database: DatabaseConfig = Field(default_factory=DatabaseConfig)
        llm: LLMConfig = Field(default_factory=LLMConfig)
        security: SecurityConfig = Field(default_factory=SecurityConfig)
        scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
        consensus: ConsensusConfig = Field(default_factory=ConsensusConfig)
        knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
        monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

        @field_validator("name")
        @classmethod
        def validate_name(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("实例名称不能为空")
            if not v.replace("_", "").replace("-", "").isalnum():
                raise ValueError("实例名称只能包含字母、数字、_、-")
            return v

else:
    # 无 Pydantic 降级：提供相同的类结构（不做校验）
    class ServerConfig:
        host = "0.0.0.0"
        port = 8000
        mode = "auto"
        workers = 1
        cors_origins = ["*"]

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class DatabaseConfig:
        backend = "memory"
        url = ""
        pool_size = 5
        wal_mode = True
        echo_sql = False

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class LLMConfig:
        provider = "openai"
        api_key = ""
        api_base = ""
        model = "gpt-3.5-turbo"
        temperature = 0.7
        max_tokens = 2048
        timeout = 60.0
        max_retries = 3
        retry_backoff = 2.0

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class SecurityConfig:
        jwt_secret = ""
        jwt_algorithm = "HS256"
        jwt_expire_minutes = 60
        rate_limit_capacity = 100
        rate_limit_refill_rate = 10.0
        audit_enabled = True
        audit_backend = "sqlite"

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class SchedulerConfig:
        max_workers = 4
        timeout = 30
        queue_size = 100
        cache_enabled = True
        cache_size = 1000

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class ConsensusConfig:
        enabled = False
        node_id = ""
        peer_addresses = []
        election_timeout_min = 5.0
        election_timeout_max = 10.0
        heartbeat_interval = 2.0

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class KnowledgeConfig:
        backend = "memory"
        vector_enabled = False
        vector_backend = "auto"
        max_node_size = 10000
        index_path = ""

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class MonitoringConfig:
        prometheus_enabled = True
        log_level = "INFO"
        log_format = "json"
        health_check_interval = 30

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    def _coerce_config(cls, value):
        """将值转换为配置类实例，支持 dict 和已实例化对象"""
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(**value)
        return cls()

    class TengodConfig:
        def __init__(self, **kwargs):
            self.name = kwargs.get("name", "tengod")
            self.server = _coerce_config(ServerConfig, kwargs.get("server", {}))
            self.database = _coerce_config(DatabaseConfig, kwargs.get("database", {}))
            self.llm = _coerce_config(LLMConfig, kwargs.get("llm", {}))
            self.security = _coerce_config(SecurityConfig, kwargs.get("security", {}))
            self.scheduler = _coerce_config(SchedulerConfig, kwargs.get("scheduler", {}))
            self.consensus = _coerce_config(ConsensusConfig, kwargs.get("consensus", {}))
            self.knowledge = _coerce_config(KnowledgeConfig, kwargs.get("knowledge", {}))
            self.monitoring = _coerce_config(MonitoringConfig, kwargs.get("monitoring", {}))


def validate_and_load(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """验证并加载配置，返回验证后的字典。

    优先使用 Pydantic v2 严格校验，不可用时返回原字典。
    错误时抛出 ValueError 包含详细校验失败信息。
    """
    if _PYDANTIC_V2:
        cfg = TengodConfig(**config_dict)
        return cfg.model_dump()
    else:
        cfg = TengodConfig(**config_dict)
        return cfg.__dict__


def load_from_yaml(file_path: str) -> Dict[str, Any]:
    """从 YAML 文件加载并校验配置"""
    import yaml

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return validate_and_load(data)


def generate_example_yaml() -> str:
    """生成示例 YAML 配置"""
    cfg = TengodConfig(
        name="tengod-prod",
        server=ServerConfig(port=8000, mode="auto"),
        database=DatabaseConfig(backend="sqlite", url="tengod.db", wal_mode=True),
        llm=LLMConfig(model="gpt-4", max_tokens=4096),
        security=SecurityConfig(jwt_secret="your-secret-key-change-me"),
        monitoring=MonitoringConfig(log_format="json"),
    )
    if _PYDANTIC_V2:
        d = cfg.model_dump()
    else:
        d = cfg.__dict__

    def _to_yaml(obj: Any, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{prefix}{k}:")
                    lines.append(_to_yaml(v, indent + 1))
                elif isinstance(v, str):
                    lines.append(f'{prefix}{k}: "{v}"')
                else:
                    lines.append(f"{prefix}{k}: {v}")
        elif isinstance(obj, list):
            for item in obj:
                lines.append(f"{prefix}- {item}")
        return "\n".join(lines)

    return "# 十神架构 v2.0.1 配置\n" + _to_yaml(d)


__all__ = [
    "TengodConfig",
    "ServerConfig",
    "DatabaseConfig",
    "LLMConfig",
    "SecurityConfig",
    "SchedulerConfig",
    "ConsensusConfig",
    "KnowledgeConfig",
    "MonitoringConfig",
    "validate_and_load",
    "load_from_yaml",
    "generate_example_yaml",
    "_PYDANTIC_V2",
]
__version__ = "2.0.1"
