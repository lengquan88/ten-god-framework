"""Comprehensive tests for tengod.config_manager."""

from __future__ import annotations

import os
import time
from unittest.mock import patch

import pytest

import tengod.config_manager as cm
from tengod.config_schema import _PYDANTIC_V2, TengodConfig


# =============================================================================
# _env_override tests
# =============================================================================


class TestEnvOverride:
    """Tests for the internal _env_override function."""

    def test_no_env_vars_set_returns_unchanged(self, clean_env):
        """When no TENGOD_* env vars are set, config dict is unchanged."""
        config = {"name": "test", "server": {"host": "0.0.0.0", "port": 8000}}
        result = cm._env_override(config)
        assert result["name"] == "test"
        assert result["server"]["host"] == "0.0.0.0"
        assert result["server"]["port"] == 8000

    def test_tengod_name_override(self, clean_env):
        """TENGOD_NAME overrides name field."""
        os.environ["TENGOD_NAME"] = "my-custom-name"
        config = {"name": "default"}
        result = cm._env_override(config)
        assert result["name"] == "my-custom-name"

    def test_tengod_host_override(self, clean_env):
        """TENGOD_HOST overrides server.host."""
        os.environ["TENGOD_HOST"] = "192.168.1.1"
        config = {"server": {"host": "0.0.0.0"}}
        result = cm._env_override(config)
        assert result["server"]["host"] == "192.168.1.1"

    def test_tengod_port_override_int(self, clean_env):
        """TENGOD_PORT is converted to int."""
        os.environ["TENGOD_PORT"] = "9999"
        config = {"server": {"port": 8000}}
        result = cm._env_override(config)
        assert result["server"]["port"] == 9999
        assert isinstance(result["server"]["port"], int)

    def test_tengod_port_invalid_value_skipped(self, clean_env):
        """Invalid TENGOD_PORT value is silently skipped."""
        os.environ["TENGOD_PORT"] = "not-a-number"
        config = {"server": {"port": 8000}}
        result = cm._env_override(config)
        assert result["server"]["port"] == 8000

    def test_tengod_workers_override(self, clean_env):
        """TENGOD_WORKERS overrides server.workers."""
        os.environ["TENGOD_WORKERS"] = "4"
        config = {"server": {"workers": 1}}
        result = cm._env_override(config)
        assert result["server"]["workers"] == 4

    def test_tengod_cors_override(self, clean_env):
        """TENGOD_CORS splits comma-separated string into list."""
        os.environ["TENGOD_CORS"] = "http://a.com,http://b.com,http://c.com"
        config = {"server": {"cors_origins": ["*"]}}
        result = cm._env_override(config)
        assert result["server"]["cors_origins"] == [
            "http://a.com",
            "http://b.com",
            "http://c.com",
        ]

    def test_tengod_cors_single_value(self, clean_env):
        """TENGOD_CORS with single value."""
        os.environ["TENGOD_CORS"] = "http://localhost:3000"
        config = {"server": {"cors_origins": ["*"]}}
        result = cm._env_override(config)
        assert result["server"]["cors_origins"] == ["http://localhost:3000"]

    def test_tengod_log_level_override(self, clean_env):
        """TENGOD_LOG_LEVEL overrides monitoring.log_level."""
        os.environ["TENGOD_LOG_LEVEL"] = "DEBUG"
        config = {"monitoring": {"log_level": "INFO"}}
        result = cm._env_override(config)
        assert result["monitoring"]["log_level"] == "DEBUG"

    def test_tengod_log_format_override(self, clean_env):
        """TENGOD_LOG_FORMAT overrides monitoring.log_format."""
        os.environ["TENGOD_LOG_FORMAT"] = "text"
        config = {"monitoring": {"log_format": "json"}}
        result = cm._env_override(config)
        assert result["monitoring"]["log_format"] == "text"

    def test_tengod_db_url_override(self, clean_env):
        """TENGOD_DB_URL overrides database.url."""
        os.environ["TENGOD_DB_URL"] = "postgresql://localhost/test"
        config = {"database": {"url": ""}}
        result = cm._env_override(config)
        assert result["database"]["url"] == "postgresql://localhost/test"

    def test_tengod_llm_provider_override(self, clean_env):
        """TENGOD_LLM_PROVIDER overrides llm.provider."""
        os.environ["TENGOD_LLM_PROVIDER"] = "anthropic"
        config = {"llm": {"provider": "openai"}}
        result = cm._env_override(config)
        assert result["llm"]["provider"] == "anthropic"

    def test_tengod_llm_api_key_override(self, clean_env):
        """TENGOD_LLM_API_KEY overrides llm.api_key."""
        os.environ["TENGOD_LLM_API_KEY"] = "sk-secret-key"
        config = {"llm": {"api_key": ""}}
        result = cm._env_override(config)
        assert result["llm"]["api_key"] == "sk-secret-key"

    def test_tengod_llm_model_override(self, clean_env):
        """TENGOD_LLM_MODEL overrides llm.model."""
        os.environ["TENGOD_LLM_MODEL"] = "gpt-4-turbo"
        config = {"llm": {"model": "gpt-3.5-turbo"}}
        result = cm._env_override(config)
        assert result["llm"]["model"] == "gpt-4-turbo"

    def test_tengod_llm_base_override(self, clean_env):
        """TENGOD_LLM_BASE overrides llm.api_base."""
        os.environ["TENGOD_LLM_BASE"] = "https://custom.api.com"
        config = {"llm": {"api_base": ""}}
        result = cm._env_override(config)
        assert result["llm"]["api_base"] == "https://custom.api.com"

    def test_tengod_jwt_secret_override(self, clean_env):
        """TENGOD_JWT_SECRET overrides security.jwt_secret."""
        os.environ["TENGOD_JWT_SECRET"] = "super-secret-jwt"
        config = {"security": {"jwt_secret": ""}}
        result = cm._env_override(config)
        assert result["security"]["jwt_secret"] == "super-secret-jwt"

    def test_tengod_rate_limit_override(self, clean_env):
        """TENGOD_RATE_LIMIT overrides security.rate_limit_capacity."""
        os.environ["TENGOD_RATE_LIMIT"] = "500"
        config = {"security": {"rate_limit_capacity": 100}}
        result = cm._env_override(config)
        assert result["security"]["rate_limit_capacity"] == 500

    def test_tengod_rate_limit_invalid_skipped(self, clean_env):
        """Invalid TENGOD_RATE_LIMIT value is silently skipped."""
        os.environ["TENGOD_RATE_LIMIT"] = "abc"
        config = {"security": {"rate_limit_capacity": 100}}
        result = cm._env_override(config)
        assert result["security"]["rate_limit_capacity"] == 100

    def test_tengod_prometheus_enabled_true(self, clean_env):
        """TENGOD_PROMETHEUS=true enables prometheus."""
        os.environ["TENGOD_PROMETHEUS"] = "true"
        config = {"monitoring": {"prometheus_enabled": False}}
        result = cm._env_override(config)
        assert result["monitoring"]["prometheus_enabled"] is True

    def test_tengod_prometheus_enabled_false(self, clean_env):
        """TENGOD_PROMETHEUS=false disables prometheus."""
        os.environ["TENGOD_PROMETHEUS"] = "false"
        config = {"monitoring": {"prometheus_enabled": True}}
        result = cm._env_override(config)
        assert result["monitoring"]["prometheus_enabled"] is False

    def test_tengod_prometheus_case_insensitive(self, clean_env):
        """TENGOD_PROMETHEUS is case-insensitive."""
        os.environ["TENGOD_PROMETHEUS"] = "TRUE"
        config = {"monitoring": {"prometheus_enabled": False}}
        result = cm._env_override(config)
        assert result["monitoring"]["prometheus_enabled"] is True

    def test_creates_nested_section_if_missing(self, clean_env):
        """Env var creates parent dict if it doesn't exist."""
        os.environ["TENGOD_HOST"] = "10.0.0.1"
        config = {"name": "test"}
        result = cm._env_override(config)
        assert result["server"]["host"] == "10.0.0.1"

    def test_multiple_env_vars_applied_together(self, clean_env):
        """Multiple env vars are all applied."""
        os.environ["TENGOD_NAME"] = "multi-test"
        os.environ["TENGOD_PORT"] = "7777"
        os.environ["TENGOD_LOG_LEVEL"] = "ERROR"
        config = {
            "name": "default",
            "server": {"port": 8000},
            "monitoring": {"log_level": "INFO"},
        }
        result = cm._env_override(config)
        assert result["name"] == "multi-test"
        assert result["server"]["port"] == 7777
        assert result["monitoring"]["log_level"] == "ERROR"

    def test_with_pydantic_model_input(self, clean_env):
        """_env_override handles Pydantic model objects via _to_dict."""
        os.environ["TENGOD_NAME"] = "from-env"
        cfg = TengodConfig(name="original")
        if _PYDANTIC_V2:
            config_dict = cfg.model_dump()
        else:
            config_dict = cfg.__dict__
        result = cm._env_override(config_dict)
        assert result["name"] == "from-env"

    def test_to_dict_handles_nested_pydantic_model(self, clean_env):
        """_env_override _to_dict handles dict values that are pydantic models."""
        from tengod.config_schema import ServerConfig

        os.environ["TENGOD_HOST"] = "10.0.0.99"
        # Pass a dict whose value is a pydantic model instance
        config = {"server": ServerConfig(host="0.0.0.0", port=8000)}
        result = cm._env_override(config)
        assert result["server"]["host"] == "10.0.0.99"

    def test_to_dict_handles_object_with_dict(self, clean_env):
        """_env_override _to_dict handles objects with __dict__ attribute."""

        class CustomObj:
            def __init__(self):
                self.host = "1.2.3.4"
                self.port = 9999
                self._private = "hidden"

        os.environ["TENGOD_HOST"] = "override-host"
        config = {"server": CustomObj()}
        result = cm._env_override(config)
        assert result["server"]["host"] == "override-host"
        assert "_private" not in result["server"]


# =============================================================================
# load_config tests
# =============================================================================


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_from_yaml_file(self, temp_yaml_config, clean_env):
        """Load config from a valid YAML file."""
        cfg = cm.load_config(temp_yaml_config)
        assert cfg.name == "test-tengod"
        assert cfg.server.host == "127.0.0.1"
        assert cfg.server.port == 9090
        assert cfg.server.mode == "simple"
        assert cfg.server.workers == 2
        assert cfg.database.backend == "sqlite"
        assert cfg.database.url == "test.db"
        assert cfg.llm.provider == "openai"
        assert cfg.llm.model == "gpt-4"
        assert cfg.security.jwt_secret == "test-secret-key"
        assert cfg.monitoring.log_level == "DEBUG"

    def test_load_from_minimal_yaml(self, minimal_yaml_config, clean_env):
        """Load config from minimal YAML with defaults for missing fields."""
        cfg = cm.load_config(minimal_yaml_config)
        assert cfg.name == "minimal"
        # Defaults should be filled in
        assert cfg.server.port == 8000
        assert cfg.server.host == "0.0.0.0"

    def test_load_missing_file_uses_defaults(self, clean_env):
        """When config file doesn't exist, defaults are used."""
        cfg = cm.load_config("/nonexistent/path/config.yaml")
        assert cfg.name == "tengod"
        assert cfg.server.port == 8000
        assert cfg.server.host == "0.0.0.0"
        assert cfg.llm.provider == "openai"
        assert cfg.llm.model == "gpt-3.5-turbo"

    def test_load_with_env_override(self, temp_yaml_config, clean_env):
        """Env vars override YAML values."""
        os.environ["TENGOD_NAME"] = "env-override-name"
        os.environ["TENGOD_PORT"] = "5555"
        cfg = cm.load_config(temp_yaml_config)
        assert cfg.name == "env-override-name"
        assert cfg.server.port == 5555

    def test_load_without_env_override(self, temp_yaml_config, clean_env):
        """With auto_env=False, env vars are ignored."""
        os.environ["TENGOD_NAME"] = "should-not-appear"
        cfg = cm.load_config(temp_yaml_config, auto_env=False)
        assert cfg.name == "test-tengod"

    def test_load_with_hot_reload_enabled(self, temp_yaml_config, clean_env):
        """Hot reload flag is stored."""
        cfg = cm.load_config(temp_yaml_config, hot_reload=True)
        assert cfg is not None
        assert cm._CONFIG_HOT_RELOAD is True

    def test_load_uses_tengod_config_file_env(self, temp_yaml_config, clean_env):
        """Uses TENGOD_CONFIG_FILE env var when config_path is None."""
        os.environ["TENGOD_CONFIG_FILE"] = temp_yaml_config
        cfg = cm.load_config()
        assert cfg.name == "test-tengod"

    def test_load_uses_tengod_config_fallback(self, clean_env):
        """Uses TENGOD_CONFIG env var as fallback."""
        # No TENGOD_CONFIG_FILE set, TENGOD_CONFIG points to non-existent
        # so it falls through to defaults
        os.environ["TENGOD_CONFIG"] = "some_config.yaml"
        cfg = cm.load_config()
        # File doesn't exist, so defaults
        assert cfg.name == "tengod"

    def test_load_invalid_yaml_raises(self, invalid_yaml_file, clean_env):
        """Loading invalid YAML raises an error."""
        import yaml

        with pytest.raises((yaml.YAMLError, yaml.scanner.ScannerError)):
            cm.load_config(invalid_yaml_file)

    def test_load_returns_tengodconfig_instance(self, temp_yaml_config, clean_env):
        """load_config returns TengodConfig instance."""
        cfg = cm.load_config(temp_yaml_config)
        assert isinstance(cfg, TengodConfig)

    def test_load_sets_global_state(self, temp_yaml_config, clean_env):
        """load_config sets global state variables."""
        cm.load_config(temp_yaml_config)
        assert cm._CONFIG_INSTANCE is not None
        assert cm._CONFIG_PATH == temp_yaml_config
        assert cm._CONFIG_MTIME > 0

    def test_load_missing_file_sets_mtime_zero(self, clean_env):
        """Missing config file sets mtime to 0."""
        cm.load_config("/nonexistent/config.yaml")
        assert cm._CONFIG_MTIME == 0


# =============================================================================
# get_config tests
# =============================================================================


class TestGetConfig:
    """Tests for get_config function."""

    def test_first_call_auto_loads(self, clean_env):
        """First call to get_config auto-loads with defaults."""
        cfg = cm.get_config()
        assert isinstance(cfg, TengodConfig)
        assert cfg.name == "tengod"

    def test_subsequent_calls_return_cached(self, temp_yaml_config, clean_env):
        """Subsequent calls return the cached instance."""
        cfg1 = cm.load_config(temp_yaml_config)
        cfg2 = cm.get_config()
        assert cfg2 is cfg1

    def test_returns_none_when_no_instance(self, clean_env):
        """When _CONFIG_INSTANCE is None, get_config calls load_config."""
        cm._CONFIG_INSTANCE = None
        cfg = cm.get_config()
        assert cfg is not None
        assert isinstance(cfg, TengodConfig)

    def test_hot_reload_detects_changed_file(self, temp_yaml_config, clean_env):
        """Hot reload loads new config when file mtime changes."""
        cfg1 = cm.load_config(temp_yaml_config, hot_reload=True)

        # Touch the file to update mtime
        time.sleep(0.01)
        Path = __import__("pathlib").Path
        Path(temp_yaml_config).touch()

        with patch("tengod.config_manager.load_config") as mock_load:
            mock_load.return_value = cfg1
            cm.get_config()
            mock_load.assert_called_once()

    def test_hot_reload_no_change_no_reload(self, temp_yaml_config, clean_env):
        """Hot reload does not reload when file hasn't changed."""
        cm.load_config(temp_yaml_config, hot_reload=True)
        cfg1 = cm.get_config()

        with patch("tengod.config_manager.load_config") as mock_load:
            cfg2 = cm.get_config()
            mock_load.assert_not_called()
            assert cfg2 is cfg1


# =============================================================================
# reload_config tests
# =============================================================================


class TestReloadConfig:
    """Tests for reload_config function."""

    def test_reload_loads_fresh_config(self, temp_yaml_config, clean_env):
        """reload_config forces a fresh load."""
        cm.load_config(temp_yaml_config)
        cfg = cm.reload_config()
        assert isinstance(cfg, TengodConfig)
        assert cfg.name == "test-tengod"

    def test_reload_when_never_loaded(self, clean_env):
        """reload_config works even if never loaded before."""
        cfg = cm.reload_config()
        assert isinstance(cfg, TengodConfig)
        assert cfg.name == "tengod"


# =============================================================================
# get_config_dict tests
# =============================================================================


class TestGetConfigDict:
    """Tests for get_config_dict function."""

    def test_returns_dict(self, temp_yaml_config, clean_env):
        """get_config_dict returns a plain dict."""
        cm.load_config(temp_yaml_config)
        d = cm.get_config_dict()
        assert isinstance(d, dict)
        assert d["name"] == "test-tengod"
        assert "server" in d

    def test_auto_loads_if_not_loaded(self, clean_env):
        """get_config_dict auto-loads if no config loaded."""
        d = cm.get_config_dict()
        assert isinstance(d, dict)
        assert d["name"] == "tengod"


# =============================================================================
# get_server_config tests
# =============================================================================


class TestGetServerConfig:
    """Tests for get_server_config function."""

    def test_returns_server_dict(self, temp_yaml_config, clean_env):
        """get_server_config returns server config as dict."""
        cm.load_config(temp_yaml_config)
        s = cm.get_server_config()
        assert isinstance(s, dict)
        assert s["host"] == "127.0.0.1"
        assert s["port"] == 9090
        assert s["mode"] == "simple"
        assert s["workers"] == 2
        assert "cors_origins" in s

    def test_auto_loads_if_not_loaded(self, clean_env):
        """get_server_config auto-loads if no config loaded."""
        s = cm.get_server_config()
        assert isinstance(s, dict)
        assert "host" in s
        assert "port" in s


# =============================================================================
# get_llm_config tests
# =============================================================================


class TestGetLLMConfig:
    """Tests for get_llm_config function."""

    def test_returns_llm_dict_with_masked_key(self, temp_yaml_config, clean_env):
        """get_llm_config masks API key longer than 8 chars."""
        cm.load_config(temp_yaml_config)
        llm = cm.get_llm_config()
        assert isinstance(llm, dict)
        assert llm["provider"] == "openai"
        assert llm["model"] == "gpt-4"
        # sk-test-key-1234567890 → sk-****7890
        assert llm["api_key"] == "sk-t****7890"
        assert "****" in llm["api_key"]

    def test_short_api_key_not_masked(self, temp_yaml_config, clean_env):
        """API key of 8 chars or less is not masked."""
        # Use env override to set a short key
        os.environ["TENGOD_LLM_API_KEY"] = "short"
        cm.load_config(temp_yaml_config)
        llm = cm.get_llm_config()
        assert llm["api_key"] == "short"

    def test_empty_api_key_not_masked(self, temp_yaml_config, clean_env):
        """Empty API key is not masked."""
        os.environ["TENGOD_LLM_API_KEY"] = ""
        cm.load_config(temp_yaml_config)
        llm = cm.get_llm_config()
        assert llm["api_key"] == ""

    def test_auto_loads_if_not_loaded(self, clean_env):
        """get_llm_config auto-loads if no config loaded."""
        llm = cm.get_llm_config()
        assert isinstance(llm, dict)
        assert "provider" in llm
        assert "model" in llm

    def test_exact_8_char_key_not_masked(self, temp_yaml_config, clean_env):
        """API key exactly 8 chars is not masked (len > 8 check)."""
        os.environ["TENGOD_LLM_API_KEY"] = "12345678"
        cm.load_config(temp_yaml_config)
        llm = cm.get_llm_config()
        assert llm["api_key"] == "12345678"


# =============================================================================
# init_config tests
# =============================================================================


class TestInitConfig:
    """Tests for init_config function."""

    def test_init_returns_config(self, temp_yaml_config, clean_env):
        """init_config returns TengodConfig instance."""
        cfg = cm.init_config(temp_yaml_config)
        assert isinstance(cfg, TengodConfig)
        assert cfg.name == "test-tengod"

    def test_init_with_hot_reload(self, temp_yaml_config, clean_env):
        """init_config with hot_reload flag."""
        cfg = cm.init_config(temp_yaml_config, hot_reload=True)
        assert cfg is not None
        assert cm._CONFIG_HOT_RELOAD is True

    def test_init_defaults(self, clean_env):
        """init_config with no args uses defaults."""
        cfg = cm.init_config()
        assert isinstance(cfg, TengodConfig)
        assert cfg.name == "tengod"


# =============================================================================
# Edge case and integration tests
# =============================================================================


class TestEdgeCases:
    """Edge case and integration tests."""

    def test_load_config_thread_safety_lock(self, temp_yaml_config, clean_env):
        """Verify lock is acquired during load_config."""
        cfg = cm.load_config(temp_yaml_config)
        assert cfg is not None

    def test_reload_preserves_hot_reload_flag(self, temp_yaml_config, clean_env):
        """reload_config preserves the hot_reload setting."""
        cm.load_config(temp_yaml_config, hot_reload=True)
        assert cm._CONFIG_HOT_RELOAD is True
        cm.reload_config()
        assert cm._CONFIG_HOT_RELOAD is True

    def test_multiple_loads_update_instance(self, temp_yaml_config, minimal_yaml_config, clean_env):
        """Multiple load_config calls update the global instance."""
        cfg1 = cm.load_config(temp_yaml_config)
        assert cfg1.name == "test-tengod"

        cfg2 = cm.load_config(minimal_yaml_config)
        assert cfg2.name == "minimal"
        assert cm._CONFIG_INSTANCE is cfg2

    def test_env_override_with_empty_config(self, clean_env):
        """Env override on empty config dict."""
        os.environ["TENGOD_NAME"] = "from-env"
        config = {}
        result = cm._env_override(config)
        assert result["name"] == "from-env"

    def test_all_env_vars_simultaneously(self, clean_env):
        """All 14 environment variables set at once."""
        os.environ["TENGOD_NAME"] = "full-test"
        os.environ["TENGOD_HOST"] = "10.0.0.1"
        os.environ["TENGOD_PORT"] = "8080"
        os.environ["TENGOD_WORKERS"] = "8"
        os.environ["TENGOD_CORS"] = "http://a.com,http://b.com"
        os.environ["TENGOD_LOG_LEVEL"] = "WARNING"
        os.environ["TENGOD_LOG_FORMAT"] = "text"
        os.environ["TENGOD_DB_URL"] = "postgresql://db/test"
        os.environ["TENGOD_LLM_PROVIDER"] = "anthropic"
        os.environ["TENGOD_LLM_API_KEY"] = "sk-ant-key"
        os.environ["TENGOD_LLM_MODEL"] = "claude-3"
        os.environ["TENGOD_LLM_BASE"] = "https://api.anthropic.com"
        os.environ["TENGOD_JWT_SECRET"] = "jwt-secret-123"
        os.environ["TENGOD_RATE_LIMIT"] = "300"
        os.environ["TENGOD_PROMETHEUS"] = "true"

        config = {
            "name": "default",
            "server": {"host": "0.0.0.0", "port": 8000, "workers": 1, "cors_origins": ["*"]},
            "database": {"url": ""},
            "llm": {"provider": "openai", "api_key": "", "model": "", "api_base": ""},
            "security": {"jwt_secret": "", "rate_limit_capacity": 100},
            "monitoring": {"log_level": "INFO", "log_format": "json", "prometheus_enabled": False},
        }
        result = cm._env_override(config)

        assert result["name"] == "full-test"
        assert result["server"]["host"] == "10.0.0.1"
        assert result["server"]["port"] == 8080
        assert result["server"]["workers"] == 8
        assert result["server"]["cors_origins"] == ["http://a.com", "http://b.com"]
        assert result["monitoring"]["log_level"] == "WARNING"
        assert result["monitoring"]["log_format"] == "text"
        assert result["monitoring"]["prometheus_enabled"] is True
        assert result["database"]["url"] == "postgresql://db/test"
        assert result["llm"]["provider"] == "anthropic"
        assert result["llm"]["api_key"] == "sk-ant-key"
        assert result["llm"]["model"] == "claude-3"
        assert result["llm"]["api_base"] == "https://api.anthropic.com"
        assert result["security"]["jwt_secret"] == "jwt-secret-123"
        assert result["security"]["rate_limit_capacity"] == 300

    def test_empty_config_path_uses_default(self, clean_env):
        """Empty string config_path falls through to defaults."""
        # Ensure no env vars interfere
        os.environ.pop("TENGOD_CONFIG_FILE", None)
        os.environ.pop("TENGOD_CONFIG", None)
        cfg = cm.load_config("")
        assert cfg.name == "tengod"

    def test_load_config_with_env_override_and_no_file(self, clean_env):
        """load_config with no file but env overrides."""
        os.environ["TENGOD_NAME"] = "env-only"
        os.environ["TENGOD_PORT"] = "3000"
        os.environ.pop("TENGOD_CONFIG_FILE", None)
        os.environ.pop("TENGOD_CONFIG", None)
        cfg = cm.load_config("/nonexistent/path.yaml")
        assert cfg.name == "env-only"
        assert cfg.server.port == 3000

    def test_generate_example_yaml_imported(self):
        """generate_example_yaml is importable from config_manager."""
        from tengod.config_manager import generate_example_yaml

        result = generate_example_yaml()
        assert isinstance(result, str)
        assert "十神架构" in result
        assert "tengod-prod" in result

    def test_config_manager_all_exports(self):
        """Verify __all__ contains all public functions."""
        assert "load_config" in cm.__all__
        assert "get_config" in cm.__all__
        assert "reload_config" in cm.__all__
        assert "get_config_dict" in cm.__all__
        assert "get_server_config" in cm.__all__
        assert "get_llm_config" in cm.__all__
        assert "init_config" in cm.__all__
        assert "generate_example_yaml" in cm.__all__