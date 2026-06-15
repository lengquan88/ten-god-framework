"""test_config_schema.py — Pydantic v2 配置 Schema 测试"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tengod"))

import pytest
from config_schema import (
    validate_and_load,
    generate_example_yaml,
    TengodConfig,
    ServerConfig,
    DatabaseConfig,
    LLMConfig,
    SecurityConfig,
    SchedulerConfig,
    ConsensusConfig,
    KnowledgeConfig,
    MonitoringConfig,
    LogLevel,
    DBBackend,
    ServerMode,
    _PYDANTIC_V2,
)


class TestLogLevel:
    def test_debug(self):
        assert LogLevel.DEBUG == "DEBUG"

    def test_info(self):
        assert LogLevel.INFO == "INFO"

    def test_warning(self):
        assert LogLevel.WARNING == "WARNING"

    def test_error(self):
        assert LogLevel.ERROR == "ERROR"


class TestDBBackend:
    def test_memory(self):
        assert DBBackend.MEMORY == "memory"

    def test_sqlite(self):
        assert DBBackend.SQLITE == "sqlite"

    def test_postgresql(self):
        assert DBBackend.POSTGRESQL == "postgresql"

    def test_json(self):
        assert DBBackend.JSON == "json"


class TestServerMode:
    def test_fastapi(self):
        assert ServerMode.FASTAPI == "fastapi"

    def test_simple(self):
        assert ServerMode.SIMPLE == "simple"

    def test_auto(self):
        assert ServerMode.AUTO == "auto"


class TestServerConfig:
    def test_defaults(self):
        cfg = ServerConfig()
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 8000
        assert cfg.mode == "auto"
        assert cfg.workers == 1
        assert cfg.cors_origins == ["*"]

    def test_custom(self):
        cfg = ServerConfig(host="127.0.0.1", port=9000, mode="simple", workers=4)
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 9000
        assert cfg.mode == "simple"
        assert cfg.workers == 4


class TestDatabaseConfig:
    def test_defaults(self):
        cfg = DatabaseConfig()
        assert cfg.backend == "memory"
        assert cfg.url == ""
        assert cfg.pool_size == 5
        assert cfg.wal_mode is True
        assert cfg.echo_sql is False

    def test_custom(self):
        cfg = DatabaseConfig(backend="sqlite", url="test.db", pool_size=10)
        assert cfg.backend == "sqlite"
        assert cfg.url == "test.db"
        assert cfg.pool_size == 10


class TestLLMConfig:
    def test_defaults(self):
        cfg = LLMConfig()
        assert cfg.provider == "openai"
        assert cfg.api_key == ""
        assert cfg.model == "gpt-3.5-turbo"
        assert cfg.temperature == 0.7
        assert cfg.max_tokens == 2048
        assert cfg.timeout == 60.0
        assert cfg.max_retries == 3
        assert cfg.retry_backoff == 2.0

    def test_custom(self):
        cfg = LLMConfig(provider="claude", model="claude-3-opus", temperature=0.3, max_tokens=4096)
        assert cfg.provider == "claude"
        assert cfg.model == "claude-3-opus"
        assert cfg.temperature == 0.3
        assert cfg.max_tokens == 4096


class TestSecurityConfig:
    def test_defaults(self):
        cfg = SecurityConfig()
        assert cfg.jwt_secret == ""
        assert cfg.jwt_algorithm == "HS256"
        assert cfg.jwt_expire_minutes == 60
        assert cfg.rate_limit_capacity == 100
        assert cfg.rate_limit_refill_rate == 10.0
        assert cfg.audit_enabled is True
        assert cfg.audit_backend == "sqlite"

    def test_custom(self):
        cfg = SecurityConfig(jwt_secret="my-secret", jwt_expire_minutes=120, rate_limit_capacity=200)
        assert cfg.jwt_secret == "my-secret"
        assert cfg.jwt_expire_minutes == 120
        assert cfg.rate_limit_capacity == 200


class TestSchedulerConfig:
    def test_defaults(self):
        cfg = SchedulerConfig()
        assert cfg.max_workers == 4
        assert cfg.timeout == 30
        assert cfg.queue_size == 100
        assert cfg.cache_enabled is True
        assert cfg.cache_size == 1000

    def test_custom(self):
        cfg = SchedulerConfig(max_workers=8, timeout=60, queue_size=200)
        assert cfg.max_workers == 8
        assert cfg.timeout == 60
        assert cfg.queue_size == 200


class TestConsensusConfig:
    def test_defaults(self):
        cfg = ConsensusConfig()
        assert cfg.enabled is False
        assert cfg.node_id == ""
        assert cfg.peer_addresses == []
        assert cfg.election_timeout_min == 5.0
        assert cfg.election_timeout_max == 10.0
        assert cfg.heartbeat_interval == 2.0

    def test_custom(self):
        cfg = ConsensusConfig(enabled=True, node_id="node-1", peer_addresses=["peer:8001"])
        assert cfg.enabled is True
        assert cfg.node_id == "node-1"
        assert cfg.peer_addresses == ["peer:8001"]


class TestKnowledgeConfig:
    def test_defaults(self):
        cfg = KnowledgeConfig()
        assert cfg.backend == "memory"
        assert cfg.vector_enabled is False
        assert cfg.vector_backend == "auto"
        assert cfg.max_node_size == 10000
        assert cfg.index_path == ""

    def test_custom(self):
        cfg = KnowledgeConfig(backend="sqlite", vector_enabled=True, vector_backend="faiss")
        assert cfg.backend == "sqlite"
        assert cfg.vector_enabled is True
        assert cfg.vector_backend == "faiss"


class TestMonitoringConfig:
    def test_defaults(self):
        cfg = MonitoringConfig()
        assert cfg.prometheus_enabled is True
        assert cfg.log_level == "INFO"
        assert cfg.log_format == "json"
        assert cfg.health_check_interval == 30

    def test_custom(self):
        cfg = MonitoringConfig(log_level="DEBUG", log_format="text", health_check_interval=60)
        assert cfg.log_level == "DEBUG"
        assert cfg.log_format == "text"
        assert cfg.health_check_interval == 60


class TestTengodConfig:
    def test_defaults(self):
        cfg = TengodConfig()
        assert cfg.name == "tengod"
        assert isinstance(cfg.server, ServerConfig)
        assert isinstance(cfg.database, DatabaseConfig)
        assert isinstance(cfg.llm, LLMConfig)
        assert isinstance(cfg.security, SecurityConfig)
        assert isinstance(cfg.scheduler, SchedulerConfig)
        assert isinstance(cfg.consensus, ConsensusConfig)
        assert isinstance(cfg.knowledge, KnowledgeConfig)
        assert isinstance(cfg.monitoring, MonitoringConfig)

    def test_custom_name(self):
        cfg = TengodConfig(name="my-tengod")
        assert cfg.name == "my-tengod"

    def test_nested_config(self):
        cfg = TengodConfig(
            name="prod",
            server={"host": "0.0.0.0", "port": 8888},
            database={"backend": "sqlite", "url": "prod.db"},
        )
        assert cfg.name == "prod"
        assert cfg.server.host == "0.0.0.0"
        assert cfg.server.port == 8888
        assert cfg.database.backend == "sqlite"
        assert cfg.database.url == "prod.db"


class TestValidateAndLoad:
    def test_basic(self):
        result = validate_and_load({"name": "test"})
        assert "name" in str(result)

    def test_full_config(self):
        result = validate_and_load({
            "name": "full-test",
            "server": {"host": "0.0.0.0", "port": 8000},
            "database": {"backend": "memory", "wal_mode": True},
            "llm": {"provider": "openai", "model": "gpt-3.5-turbo"},
            "security": {"jwt_secret": "test-secret"},
        })
        if _PYDANTIC_V2:
            assert result["name"] == "full-test"
        else:
            assert result["name"] == "full-test"


class TestGenerateExampleYaml:
    def test_generates_yaml(self):
        yaml_str = generate_example_yaml()
        assert "tengod-prod" in yaml_str
        assert "server:" in yaml_str
        assert "database:" in yaml_str
        assert "llm:" in yaml_str
        assert isinstance(yaml_str, str)
        assert len(yaml_str) > 100