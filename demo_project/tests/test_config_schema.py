"""test_config_schema.py — Pydantic v2 配置 Schema 测试"""
import importlib
import sys
import os
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tengod"))

import pytest
from config_schema import (
    validate_and_load,
    generate_example_yaml,
    load_from_yaml,
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

    def test_contains_all_sections(self):
        yaml_str = generate_example_yaml()
        expected_sections = [
            "name:", "server:", "database:", "llm:", "security:",
            "scheduler:", "consensus:", "knowledge:", "monitoring:",
        ]
        for section in expected_sections:
            assert section in yaml_str, f"Missing section: {section}"

    def test_with_pydantic_v2(self):
        """Test that generate_example_yaml broadly works with Pydantic."""
        yaml_str = generate_example_yaml()
        assert "gpt-4" in yaml_str or "gpt-3.5-turbo" in yaml_str
        assert "tengod-prod" in yaml_str


# ── Pydantic v2 field validators ────────────────────────────────────


class TestTengodConfigValidateName:
    """Test TengodConfig.validate_name field validator."""

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            TengodConfig(name="   ")

    def test_empty_string_raises2(self):
        with pytest.raises(ValueError):
            TengodConfig(name="")

    def test_special_characters_raises(self):
        with pytest.raises(ValueError):
            TengodConfig(name="bad@name")

    def test_chinese_characters_allowed(self):
        """Chinese characters are alphanumeric in Python, so they pass."""
        cfg = TengodConfig(name="中文名称")
        assert cfg.name == "中文名称"

    def test_valid_name_with_underscore(self):
        cfg = TengodConfig(name="my_tengod")
        assert cfg.name == "my_tengod"

    def test_valid_name_with_hyphen(self):
        cfg = TengodConfig(name="my-tengod")
        assert cfg.name == "my-tengod"

    def test_valid_name_alphanumeric(self):
        cfg = TengodConfig(name="tengod01")
        assert cfg.name == "tengod01"


# ── Pydantic v2 field boundary constraints ──────────────────────────


class TestServerConfigBoundaries:
    """Test ServerConfig ge/le boundary constraints."""

    def test_port_min_boundary(self):
        cfg = ServerConfig(port=1024)
        assert cfg.port == 1024

    def test_port_max_boundary(self):
        cfg = ServerConfig(port=65535)
        assert cfg.port == 65535

    def test_port_below_min_raises(self):
        with pytest.raises(ValueError):
            ServerConfig(port=1023)

    def test_port_above_max_raises(self):
        with pytest.raises(ValueError):
            ServerConfig(port=65536)

    def test_workers_min_boundary(self):
        cfg = ServerConfig(workers=1)
        assert cfg.workers == 1

    def test_workers_max_boundary(self):
        cfg = ServerConfig(workers=16)
        assert cfg.workers == 16

    def test_workers_below_min_raises(self):
        with pytest.raises(ValueError):
            ServerConfig(workers=0)

    def test_workers_above_max_raises(self):
        with pytest.raises(ValueError):
            ServerConfig(workers=17)


class TestLLMConfigBoundaries:
    """Test LLMConfig ge/le boundary constraints."""

    def test_temperature_min_boundary(self):
        cfg = LLMConfig(temperature=0.0)
        assert cfg.temperature == 0.0

    def test_temperature_max_boundary(self):
        cfg = LLMConfig(temperature=2.0)
        assert cfg.temperature == 2.0

    def test_temperature_below_min_raises(self):
        with pytest.raises(ValueError):
            LLMConfig(temperature=-0.1)

    def test_temperature_above_max_raises(self):
        with pytest.raises(ValueError):
            LLMConfig(temperature=2.1)

    def test_max_tokens_min_boundary(self):
        cfg = LLMConfig(max_tokens=1)
        assert cfg.max_tokens == 1

    def test_max_tokens_max_boundary(self):
        cfg = LLMConfig(max_tokens=128000)
        assert cfg.max_tokens == 128000

    def test_max_tokens_below_min_raises(self):
        with pytest.raises(ValueError):
            LLMConfig(max_tokens=0)

    def test_timeout_min_boundary(self):
        cfg = LLMConfig(timeout=5.0)
        assert cfg.timeout == 5.0

    def test_timeout_max_boundary(self):
        cfg = LLMConfig(timeout=600.0)
        assert cfg.timeout == 600.0

    def test_timeout_below_min_raises(self):
        with pytest.raises(ValueError):
            LLMConfig(timeout=4.9)

    def test_max_retries_boundary(self):
        cfg = LLMConfig(max_retries=0)
        assert cfg.max_retries == 0

    def test_max_retries_max_boundary(self):
        cfg = LLMConfig(max_retries=10)
        assert cfg.max_retries == 10

    def test_retry_backoff_min_boundary(self):
        cfg = LLMConfig(retry_backoff=0.5)
        assert cfg.retry_backoff == 0.5

    def test_retry_backoff_max_boundary(self):
        cfg = LLMConfig(retry_backoff=10.0)
        assert cfg.retry_backoff == 10.0


class TestDatabaseConfigBoundaries:
    """Test DatabaseConfig boundary constraints."""

    def test_pool_size_min_boundary(self):
        cfg = DatabaseConfig(pool_size=1)
        assert cfg.pool_size == 1

    def test_pool_size_max_boundary(self):
        cfg = DatabaseConfig(pool_size=50)
        assert cfg.pool_size == 50

    def test_pool_size_below_min_raises(self):
        with pytest.raises(ValueError):
            DatabaseConfig(pool_size=0)


class TestSecurityConfigBoundaries:
    """Test SecurityConfig boundary constraints."""

    def test_jwt_expire_minutes_min(self):
        cfg = SecurityConfig(jwt_expire_minutes=1)
        assert cfg.jwt_expire_minutes == 1

    def test_jwt_expire_minutes_max(self):
        cfg = SecurityConfig(jwt_expire_minutes=1440)
        assert cfg.jwt_expire_minutes == 1440

    def test_rate_limit_capacity_min(self):
        cfg = SecurityConfig(rate_limit_capacity=1)
        assert cfg.rate_limit_capacity == 1

    def test_rate_limit_capacity_max(self):
        cfg = SecurityConfig(rate_limit_capacity=10000)
        assert cfg.rate_limit_capacity == 10000

    def test_rate_limit_refill_rate_min(self):
        cfg = SecurityConfig(rate_limit_refill_rate=0.1)
        assert cfg.rate_limit_refill_rate == 0.1


class TestSchedulerConfigBoundaries:
    """Test SchedulerConfig boundary constraints."""

    def test_max_workers_min(self):
        cfg = SchedulerConfig(max_workers=1)
        assert cfg.max_workers == 1

    def test_max_workers_max(self):
        cfg = SchedulerConfig(max_workers=64)
        assert cfg.max_workers == 64

    def test_timeout_min(self):
        cfg = SchedulerConfig(timeout=1)
        assert cfg.timeout == 1

    def test_timeout_max(self):
        cfg = SchedulerConfig(timeout=3600)
        assert cfg.timeout == 3600

    def test_queue_size_min(self):
        cfg = SchedulerConfig(queue_size=1)
        assert cfg.queue_size == 1

    def test_cache_size_min(self):
        cfg = SchedulerConfig(cache_size=10)
        assert cfg.cache_size == 10


class TestKnowledgeConfigBoundaries:
    """Test KnowledgeConfig boundary constraints."""

    def test_max_node_size_min(self):
        cfg = KnowledgeConfig(max_node_size=100)
        assert cfg.max_node_size == 100

    def test_max_node_size_max(self):
        cfg = KnowledgeConfig(max_node_size=1000000)
        assert cfg.max_node_size == 1000000


class TestMonitoringConfigBoundaries:
    """Test MonitoringConfig boundary constraints."""

    def test_health_check_interval_min(self):
        cfg = MonitoringConfig(health_check_interval=10)
        assert cfg.health_check_interval == 10

    def test_health_check_interval_max(self):
        cfg = MonitoringConfig(health_check_interval=300)
        assert cfg.health_check_interval == 300


# ── Edge case tests ─────────────────────────────────────────────────


class TestValidateAndLoadEdgeCases:
    """Test validate_and_load with edge case inputs."""

    def test_empty_dict(self):
        result = validate_and_load({})
        if _PYDANTIC_V2:
            assert result["name"] == "tengod"
        else:
            assert result["name"] == "tengod"

    def test_invalid_port_raises(self):
        with pytest.raises(ValueError):
            validate_and_load({"server": {"port": 0}})

    def test_invalid_temperature_raises(self):
        with pytest.raises(ValueError):
            validate_and_load({"llm": {"temperature": 3.0}})


# ── load_from_yaml tests ────────────────────────────────────────────


class TestLoadFromYaml:
    """Test load_from_yaml function."""

    def test_minimal_config(self):
        yaml_content = "name: test-minimal\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            tmp_path = f.name
        try:
            result = load_from_yaml(tmp_path)
            assert result["name"] == "test-minimal"
        finally:
            os.unlink(tmp_path)

    def test_full_config(self):
        yaml_content = """\
name: test-full
server:
  host: 127.0.0.1
  port: 9000
  mode: simple
database:
  backend: sqlite
  url: test.db
  pool_size: 10
llm:
  provider: openai
  model: gpt-4
  temperature: 0.5
security:
  jwt_secret: my-secret
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            tmp_path = f.name
        try:
            result = load_from_yaml(tmp_path)
            assert result["name"] == "test-full"
            assert result["server"]["host"] == "127.0.0.1"
            assert result["server"]["port"] == 9000
            assert result["database"]["backend"] == "sqlite"
            assert result["llm"]["model"] == "gpt-4"
        finally:
            os.unlink(tmp_path)

    def test_with_nested_configs(self):
        yaml_content = """\
name: nested-test
server:
  port: 8080
knowledge:
  backend: json
  vector_enabled: true
monitoring:
  log_level: DEBUG
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            tmp_path = f.name
        try:
            result = load_from_yaml(tmp_path)
            assert result["name"] == "nested-test"
            assert result["server"]["port"] == 8080
        finally:
            os.unlink(tmp_path)


# ── Non-Pydantic fallback tests ─────────────────────────────────────


@pytest.fixture
def cs_fallback():
    """Fixture: reload config_schema with pydantic unavailable, restore after."""
    saved = sys.modules.get("pydantic")
    sys.modules["pydantic"] = None
    try:
        for key in list(sys.modules.keys()):
            if "config_schema" in key:
                del sys.modules[key]
        import tengod.config_schema as cs
        importlib.reload(cs)
        yield cs
    finally:
        if saved is not None:
            sys.modules["pydantic"] = saved
        else:
            sys.modules.pop("pydantic", None)
        # Reload config_schema back with pydantic available
        for key in list(sys.modules.keys()):
            if "config_schema" in key:
                del sys.modules[key]
        import tengod.config_schema as cs2
        importlib.reload(cs2)


class TestFallbackServerConfig:
    """Test ServerConfig fallback (non-Pydantic) path."""

    def test_defaults(self, cs_fallback):
        cfg = cs_fallback.ServerConfig()
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 8000
        assert cfg.mode == "auto"
        assert cfg.workers == 1
        assert cfg.cors_origins == ["*"]

    def test_custom_kwargs(self, cs_fallback):
        cfg = cs_fallback.ServerConfig(host="127.0.0.1", port=9000, mode="simple", workers=4)
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 9000
        assert cfg.mode == "simple"
        assert cfg.workers == 4


class TestFallbackDatabaseConfig:
    def test_defaults(self, cs_fallback):
        cfg = cs_fallback.DatabaseConfig()
        assert cfg.backend == "memory"
        assert cfg.url == ""
        assert cfg.pool_size == 5
        assert cfg.wal_mode is True
        assert cfg.echo_sql is False

    def test_custom_kwargs(self, cs_fallback):
        cfg = cs_fallback.DatabaseConfig(backend="sqlite", url="test.db", pool_size=10)
        assert cfg.backend == "sqlite"
        assert cfg.url == "test.db"
        assert cfg.pool_size == 10


class TestFallbackLLMConfig:
    def test_defaults(self, cs_fallback):
        cfg = cs_fallback.LLMConfig()
        assert cfg.provider == "openai"
        assert cfg.model == "gpt-3.5-turbo"
        assert cfg.temperature == 0.7
        assert cfg.max_tokens == 2048

    def test_custom_kwargs(self, cs_fallback):
        cfg = cs_fallback.LLMConfig(provider="claude", model="claude-3", temperature=0.3)
        assert cfg.provider == "claude"
        assert cfg.model == "claude-3"
        assert cfg.temperature == 0.3


class TestFallbackSecurityConfig:
    def test_defaults(self, cs_fallback):
        cfg = cs_fallback.SecurityConfig()
        assert cfg.jwt_secret == ""
        assert cfg.jwt_algorithm == "HS256"
        assert cfg.jwt_expire_minutes == 60
        assert cfg.rate_limit_capacity == 100
        assert cfg.audit_enabled is True

    def test_custom_kwargs(self, cs_fallback):
        cfg = cs_fallback.SecurityConfig(jwt_secret="sec", jwt_expire_minutes=120)
        assert cfg.jwt_secret == "sec"
        assert cfg.jwt_expire_minutes == 120


class TestFallbackSchedulerConfig:
    def test_defaults(self, cs_fallback):
        cfg = cs_fallback.SchedulerConfig()
        assert cfg.max_workers == 4
        assert cfg.timeout == 30
        assert cfg.queue_size == 100
        assert cfg.cache_enabled is True
        assert cfg.cache_size == 1000

    def test_custom_kwargs(self, cs_fallback):
        cfg = cs_fallback.SchedulerConfig(max_workers=8, timeout=60)
        assert cfg.max_workers == 8
        assert cfg.timeout == 60


class TestFallbackConsensusConfig:
    def test_defaults(self, cs_fallback):
        cfg = cs_fallback.ConsensusConfig()
        assert cfg.enabled is False
        assert cfg.node_id == ""
        assert cfg.peer_addresses == []
        assert cfg.election_timeout_min == 5.0
        assert cfg.election_timeout_max == 10.0
        assert cfg.heartbeat_interval == 2.0

    def test_custom_kwargs(self, cs_fallback):
        cfg = cs_fallback.ConsensusConfig(enabled=True, node_id="n1", heartbeat_interval=1.0)
        assert cfg.enabled is True
        assert cfg.node_id == "n1"
        assert cfg.heartbeat_interval == 1.0


class TestFallbackKnowledgeConfig:
    def test_defaults(self, cs_fallback):
        cfg = cs_fallback.KnowledgeConfig()
        assert cfg.backend == "memory"
        assert cfg.vector_enabled is False
        assert cfg.vector_backend == "auto"
        assert cfg.max_node_size == 10000
        assert cfg.index_path == ""

    def test_custom_kwargs(self, cs_fallback):
        cfg = cs_fallback.KnowledgeConfig(backend="sqlite", vector_enabled=True)
        assert cfg.backend == "sqlite"
        assert cfg.vector_enabled is True


class TestFallbackMonitoringConfig:
    def test_defaults(self, cs_fallback):
        cfg = cs_fallback.MonitoringConfig()
        assert cfg.prometheus_enabled is True
        assert cfg.log_level == "INFO"
        assert cfg.log_format == "json"
        assert cfg.health_check_interval == 30

    def test_custom_kwargs(self, cs_fallback):
        cfg = cs_fallback.MonitoringConfig(log_level="DEBUG", log_format="text")
        assert cfg.log_level == "DEBUG"
        assert cfg.log_format == "text"


class TestFallbackCoerceConfig:
    """Test _coerce_config function in fallback path."""

    def test_coerce_dict_returns_instance(self, cs_fallback):
        result = cs_fallback._coerce_config(cs_fallback.ServerConfig, {"host": "10.0.0.1", "port": 3000})
        assert isinstance(result, cs_fallback.ServerConfig)
        assert result.host == "10.0.0.1"
        assert result.port == 3000

    def test_coerce_instance_returns_same(self, cs_fallback):
        sc = cs_fallback.ServerConfig(host="10.0.0.2")
        result = cs_fallback._coerce_config(cs_fallback.ServerConfig, sc)
        assert result is sc

    def test_coerce_none_returns_default(self, cs_fallback):
        result = cs_fallback._coerce_config(cs_fallback.ServerConfig, None)
        assert isinstance(result, cs_fallback.ServerConfig)
        assert result.host == "0.0.0.0"

    def test_coerce_non_dict_returns_default(self, cs_fallback):
        result = cs_fallback._coerce_config(cs_fallback.ServerConfig, "not-a-dict")
        assert isinstance(result, cs_fallback.ServerConfig)
        assert result.host == "0.0.0.0"


class TestFallbackTengodConfig:
    """Test TengodConfig in fallback (non-Pydantic) path."""

    def test_defaults(self, cs_fallback):
        cfg = cs_fallback.TengodConfig()
        assert cfg.name == "tengod"
        assert isinstance(cfg.server, cs_fallback.ServerConfig)
        assert isinstance(cfg.database, cs_fallback.DatabaseConfig)
        assert isinstance(cfg.llm, cs_fallback.LLMConfig)
        assert isinstance(cfg.security, cs_fallback.SecurityConfig)
        assert isinstance(cfg.scheduler, cs_fallback.SchedulerConfig)
        assert isinstance(cfg.consensus, cs_fallback.ConsensusConfig)
        assert isinstance(cfg.knowledge, cs_fallback.KnowledgeConfig)
        assert isinstance(cfg.monitoring, cs_fallback.MonitoringConfig)

    def test_custom_name(self, cs_fallback):
        cfg = cs_fallback.TengodConfig(name="my-fallback")
        assert cfg.name == "my-fallback"

    def test_nested_config_via_dict(self, cs_fallback):
        cfg = cs_fallback.TengodConfig(
            name="prod",
            server={"host": "0.0.0.0", "port": 8888},
            database={"backend": "sqlite", "url": "prod.db"},
        )
        assert cfg.name == "prod"
        assert cfg.server.host == "0.0.0.0"
        assert cfg.server.port == 8888
        assert cfg.database.backend == "sqlite"
        assert cfg.database.url == "prod.db"

    def test_nested_config_via_instance(self, cs_fallback):
        sc = cs_fallback.ServerConfig(host="1.2.3.4", port=9999)
        cfg = cs_fallback.TengodConfig(name="instance-test", server=sc)
        assert cfg.server.host == "1.2.3.4"
        assert cfg.server.port == 9999


class TestFallbackValidateAndLoad:
    """Test validate_and_load in fallback path."""

    def test_basic(self, cs_fallback):
        result = cs_fallback.validate_and_load({"name": "test"})
        assert result["name"] == "test"

    def test_empty_dict(self, cs_fallback):
        result = cs_fallback.validate_and_load({})
        assert result["name"] == "tengod"

    def test_full_config(self, cs_fallback):
        result = cs_fallback.validate_and_load({
            "name": "full-test",
            "server": {"host": "0.0.0.0", "port": 8000},
            "database": {"backend": "memory", "wal_mode": True},
            "llm": {"provider": "openai", "model": "gpt-3.5-turbo"},
            "security": {"jwt_secret": "test-secret"},
        })
        assert result["name"] == "full-test"


class TestFallbackGenerateExampleYaml:
    """Test generate_example_yaml in fallback path."""

    def test_generates_yaml(self, cs_fallback):
        yaml_str = cs_fallback.generate_example_yaml()
        assert "tengod-prod" in yaml_str
        assert "server:" in yaml_str
        assert "database:" in yaml_str
        assert isinstance(yaml_str, str)
        assert len(yaml_str) > 100

    def test_contains_all_sections(self, cs_fallback):
        yaml_str = cs_fallback.generate_example_yaml()
        expected_sections = [
            "name:", "server:", "database:", "llm:", "security:",
            "scheduler:", "consensus:", "knowledge:", "monitoring:",
        ]
        for section in expected_sections:
            assert section in yaml_str, f"Missing section: {section}"


class TestFallbackLoadFromYaml:
    """Test load_from_yaml in fallback path."""

    def test_minimal_config(self, cs_fallback):
        yaml_content = "name: test-fallback-minimal\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(yaml_content)
            tmp_path = f.name
        try:
            result = cs_fallback.load_from_yaml(tmp_path)
            assert result["name"] == "test-fallback-minimal"
        finally:
            os.unlink(tmp_path)


# ── Pydantic v2 validate_and_load with patched _PYDANTIC_V2 ─────────


class TestValidateAndLoadFallbackPath:
    """Test validate_and_load with _PYDANTIC_V2 patched to False at runtime."""

    def test_fallback_path_uses_dict(self):
        """When _PYDANTIC_V2 is False, validate_and_load uses __dict__."""
        import config_schema as cs_mod

        with patch.object(cs_mod, "_PYDANTIC_V2", False):
            result = cs_mod.validate_and_load({"name": "patched-test"})
            assert result["name"] == "patched-test"


class TestGenerateExampleYamlFallbackPath:
    """Test generate_example_yaml with _PYDANTIC_V2 patched to False."""

    def test_fallback_path(self):
        import config_schema as cs_mod

        with patch.object(cs_mod, "_PYDANTIC_V2", False):
            yaml_str = cs_mod.generate_example_yaml()
            assert "tengod-prod" in yaml_str
            assert isinstance(yaml_str, str)


# ── Final Pydantic v2 re-coverage (after fallback module reloads) ────


class TestPydanticReCoverage:
    """Re-run Pydantic-v2 code paths via tengod.config_schema for coverage."""

    def test_validate_and_load_pydantic_path(self):
        """Ensure validate_and_load Pydantic path is covered."""
        import tengod.config_schema as tcs
        result = tcs.validate_and_load({"name": "recover-test"})
        assert result["name"] == "recover-test"

    def test_generate_example_yaml_pydantic_path(self):
        """Ensure generate_example_yaml Pydantic path is covered."""
        import tengod.config_schema as tcs
        yaml_str = tcs.generate_example_yaml()
        assert "tengod-prod" in yaml_str
        assert "gpt-4" in yaml_str

    def test_tengod_config_validate_name(self):
        """Ensure validate_name is covered."""
        import tengod.config_schema as tcs
        cfg = tcs.TengodConfig(name="valid-name")
        assert cfg.name == "valid-name"
        with pytest.raises(ValueError):
            tcs.TengodConfig(name="")

    def test_tengod_config_validate_name_special_chars(self):
        """Ensure validate_name special char branch is covered."""
        import tengod.config_schema as tcs
        with pytest.raises(ValueError):
            tcs.TengodConfig(name="bad@name")