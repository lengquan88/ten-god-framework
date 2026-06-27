"""
test_config_manager.py — 统一配置管理器全面测试
=================================================
覆盖：load_config, get_config, reload_config, get_config_dict,
      get_server_config, get_llm_config, init_config, _env_override
目标覆盖率：85%+
"""

import os
import tempfile
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

import tengod.config_manager as cm
from tengod.config_schema import TengodConfig, ServerConfig, LLMConfig, _PYDANTIC_V2


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_global_state():
    """每个测试前重置 config_manager 的全局状态"""
    cm._CONFIG_INSTANCE = None
    cm._CONFIG_PATH = None
    cm._CONFIG_MTIME = 0
    cm._CONFIG_HOT_RELOAD = False
    cm._CONFIG_HOT_RELOAD_INTERVAL = 5
    yield


def _make_valid_config_dict(name="tengod"):
    """构造一个有效的配置字典"""
    return {
        "name": name,
        "server": {"host": "0.0.0.0", "port": 8000, "mode": "auto", "workers": 1, "cors_origins": ["*"]},
        "database": {"backend": "memory", "url": "", "pool_size": 5, "wal_mode": True, "echo_sql": False},
        "llm": {"provider": "openai", "api_key": "", "api_base": "", "model": "gpt-3.5-turbo",
                "temperature": 0.7, "max_tokens": 2048, "timeout": 60.0, "max_retries": 3, "retry_backoff": 2.0},
        "security": {"jwt_secret": "", "jwt_algorithm": "HS256", "jwt_expire_minutes": 60,
                     "rate_limit_capacity": 100, "rate_limit_refill_rate": 10.0,
                     "audit_enabled": True, "audit_backend": "sqlite"},
        "scheduler": {"max_workers": 4, "timeout": 30, "queue_size": 100, "cache_enabled": True, "cache_size": 1000},
        "consensus": {"enabled": False, "node_id": "", "peer_addresses": [],
                      "election_timeout_min": 5.0, "election_timeout_max": 10.0, "heartbeat_interval": 2.0},
        "knowledge": {"backend": "memory", "vector_enabled": False, "vector_backend": "auto",
                      "max_node_size": 10000, "index_path": ""},
        "monitoring": {"prometheus_enabled": True, "log_level": "INFO", "log_format": "json",
                       "health_check_interval": 30},
    }


# ============================================================================
# _env_override 测试
# ============================================================================


class TestEnvOverride:
    """测试 _env_override 函数"""

    def test_no_env_vars_set(self):
        """没有环境变量时原样返回配置"""
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {}, clear=True):
            result = cm._env_override(config)
        assert result["name"] == "tengod"

    def test_tengod_name(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_NAME": "my-tengod"}, clear=True):
            result = cm._env_override(config)
        assert result["name"] == "my-tengod"

    def test_tengod_host(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_HOST": "127.0.0.1"}, clear=True):
            result = cm._env_override(config)
        assert result["server"]["host"] == "127.0.0.1"

    def test_tengod_port(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_PORT": "9090"}, clear=True):
            result = cm._env_override(config)
        assert result["server"]["port"] == 9090

    def test_tengod_port_invalid(self):
        """无效端口号应被忽略"""
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_PORT": "abc"}, clear=True):
            result = cm._env_override(config)
        assert result["server"]["port"] == 8000  # 保持默认值

    def test_tengod_workers(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_WORKERS": "8"}, clear=True):
            result = cm._env_override(config)
        assert result["server"]["workers"] == 8

    def test_tengod_cors(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_CORS": "a.com,b.com"}, clear=True):
            result = cm._env_override(config)
        assert result["server"]["cors_origins"] == ["a.com", "b.com"]

    def test_tengod_cors_single(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_CORS": "only.com"}, clear=True):
            result = cm._env_override(config)
        assert result["server"]["cors_origins"] == ["only.com"]

    def test_tengod_log_level(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_LOG_LEVEL": "DEBUG"}, clear=True):
            result = cm._env_override(config)
        assert result["monitoring"]["log_level"] == "DEBUG"

    def test_tengod_log_format(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_LOG_FORMAT": "text"}, clear=True):
            result = cm._env_override(config)
        assert result["monitoring"]["log_format"] == "text"

    def test_tengod_db_url(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_DB_URL": "postgresql://localhost/db"}, clear=True):
            result = cm._env_override(config)
        assert result["database"]["url"] == "postgresql://localhost/db"

    def test_tengod_llm_provider(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_LLM_PROVIDER": "claude"}, clear=True):
            result = cm._env_override(config)
        assert result["llm"]["provider"] == "claude"

    def test_tengod_llm_api_key(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_LLM_API_KEY": "sk-12345678"}, clear=True):
            result = cm._env_override(config)
        assert result["llm"]["api_key"] == "sk-12345678"

    def test_tengod_llm_model(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_LLM_MODEL": "gpt-4"}, clear=True):
            result = cm._env_override(config)
        assert result["llm"]["model"] == "gpt-4"

    def test_tengod_llm_base(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_LLM_BASE": "https://api.example.com"}, clear=True):
            result = cm._env_override(config)
        assert result["llm"]["api_base"] == "https://api.example.com"

    def test_tengod_jwt_secret(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_JWT_SECRET": "super-secret"}, clear=True):
            result = cm._env_override(config)
        assert result["security"]["jwt_secret"] == "super-secret"

    def test_tengod_rate_limit(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_RATE_LIMIT": "200"}, clear=True):
            result = cm._env_override(config)
        assert result["security"]["rate_limit_capacity"] == 200

    def test_tengod_rate_limit_invalid(self):
        """无效的速率限制值应被忽略"""
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_RATE_LIMIT": "not-a-number"}, clear=True):
            result = cm._env_override(config)
        assert result["security"]["rate_limit_capacity"] == 100

    def test_tengod_prometheus_enabled_true(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_PROMETHEUS": "true"}, clear=True):
            result = cm._env_override(config)
        assert result["monitoring"]["prometheus_enabled"] is True

    def test_tengod_prometheus_enabled_false(self):
        config = _make_valid_config_dict()
        with patch.dict(os.environ, {"TENGOD_PROMETHEUS": "false"}, clear=True):
            result = cm._env_override(config)
        assert result["monitoring"]["prometheus_enabled"] is False

    def test_all_env_vars_together(self):
        """多个环境变量同时设置"""
        config = _make_valid_config_dict()
        env = {
            "TENGOD_NAME": "prod",
            "TENGOD_HOST": "10.0.0.1",
            "TENGOD_PORT": "8080",
            "TENGOD_WORKERS": "4",
            "TENGOD_LOG_LEVEL": "ERROR",
            "TENGOD_DB_URL": "sqlite:///prod.db",
            "TENGOD_LLM_PROVIDER": "deepseek",
            "TENGOD_LLM_API_KEY": "sk-key",
            "TENGOD_LLM_MODEL": "deepseek-v3",
            "TENGOD_JWT_SECRET": "jwt-key",
            "TENGOD_RATE_LIMIT": "500",
            "TENGOD_PROMETHEUS": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            result = cm._env_override(config)
        assert result["name"] == "prod"
        assert result["server"]["host"] == "10.0.0.1"
        assert result["server"]["port"] == 8080
        assert result["server"]["workers"] == 4
        assert result["monitoring"]["log_level"] == "ERROR"
        assert result["database"]["url"] == "sqlite:///prod.db"
        assert result["llm"]["provider"] == "deepseek"
        assert result["llm"]["api_key"] == "sk-key"
        assert result["llm"]["model"] == "deepseek-v3"
        assert result["security"]["jwt_secret"] == "jwt-key"
        assert result["security"]["rate_limit_capacity"] == 500
        assert result["monitoring"]["prometheus_enabled"] is False

    def test_nested_dict_not_created_for_unused_keys(self):
        """当 server 不存在时，env 覆盖应创建 server 字典"""
        config = {"name": "test"}
        with patch.dict(os.environ, {"TENGOD_HOST": "1.2.3.4"}, clear=True):
            result = cm._env_override(config)
        assert result["server"]["host"] == "1.2.3.4"

    def test_pydantic_model_input(self):
        """输入是 Pydantic model 时应能正确处理"""
        with patch.dict(os.environ, {"TENGOD_NAME": "pydantic-name"}, clear=True):
            if _PYDANTIC_V2:
                cfg = TengodConfig(name="original")
                result = cm._env_override(cfg)
                assert result["name"] == "pydantic-name"
            else:
                # non-pydantic path: TengodConfig.__dict__ is used
                cfg = TengodConfig(name="original")
                result = cm._env_override(cfg)
                assert result["name"] == "pydantic-name"


# ============================================================================
# load_config 测试
# ============================================================================


class TestLoadConfig:
    """测试 load_config 函数"""

    def test_load_from_yaml_file(self, tmp_path):
        """从 YAML 文件加载配置"""
        yaml_content = "name: test-yaml\n"
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content)

        with patch.dict(os.environ, {}, clear=True):
            cfg = cm.load_config(str(yaml_file), auto_env=False)

        assert cfg.name == "test-yaml"
        assert cm._CONFIG_PATH == str(yaml_file)
        assert cm._CONFIG_MTIME > 0

    def test_load_from_file_with_env_override(self, tmp_path):
        """从文件加载并用环境变量覆盖"""
        yaml_content = "name: file-name\n"
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content)

        with patch.dict(os.environ, {"TENGOD_NAME": "env-name"}, clear=True):
            cfg = cm.load_config(str(yaml_file), auto_env=True)

        assert cfg.name == "env-name"

    def test_load_from_file_without_env_override(self, tmp_path):
        """从文件加载但不覆盖环境变量"""
        yaml_content = "name: file-name\n"
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content)

        with patch.dict(os.environ, {"TENGOD_NAME": "env-name"}, clear=True):
            cfg = cm.load_config(str(yaml_file), auto_env=False)

        assert cfg.name == "file-name"

    def test_load_defaults_when_no_config_path(self):
        """没有配置文件路径时使用默认值"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                cfg = cm.load_config(auto_env=False)

        assert cfg.name == "tengod"
        assert cfg.server.host == "0.0.0.0"
        assert cfg.server.port == 8000
        assert cm._CONFIG_MTIME == 0

    def test_load_from_env_var_config_file(self):
        """通过环境变量 TENGOD_CONFIG_FILE 指定配置路径"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write("name: from-env-config-file\n")
            tmp_path = f.name

        try:
            with patch.dict(os.environ, {"TENGOD_CONFIG_FILE": tmp_path}, clear=True):
                cfg = cm.load_config(auto_env=False)
            assert cfg.name == "from-env-config-file"
        finally:
            os.unlink(tmp_path)

    def test_load_from_env_var_config(self):
        """通过环境变量 TENGOD_CONFIG 指定配置路径"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write("name: from-tengod-config\n")
            tmp_path = f.name

        try:
            with patch.dict(os.environ, {"TENGOD_CONFIG": tmp_path}, clear=True):
                with patch("os.path.exists", return_value=True):
                    with patch("tengod.config_manager.load_from_yaml", return_value=_make_valid_config_dict("from-tengod-config")):
                        cfg = cm.load_config(auto_env=False)
            assert cfg.name == "from-tengod-config"
        finally:
            os.unlink(tmp_path)

    def test_load_with_hot_reload_enabled(self, tmp_path):
        """启用热重载标志"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("name: hot-reload-test\n")

        with patch.dict(os.environ, {}, clear=True):
            cfg = cm.load_config(str(yaml_file), hot_reload=True, auto_env=False)

        assert cfg.name == "hot-reload-test"
        assert cm._CONFIG_HOT_RELOAD is True

    def test_load_with_hot_reload_disabled(self, tmp_path):
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("name: no-hot-reload\n")

        with patch.dict(os.environ, {}, clear=True):
            cfg = cm.load_config(str(yaml_file), hot_reload=False, auto_env=False)

        assert cm._CONFIG_HOT_RELOAD is False

    def test_load_config_path_explicit(self, tmp_path):
        """显式指定 config_path 参数"""
        yaml_file = tmp_path / "my_config.yaml"
        yaml_file.write_text("name: explicit-path\n")

        with patch.dict(os.environ, {}, clear=True):
            cfg = cm.load_config(str(yaml_file), auto_env=False)

        assert cfg.name == "explicit-path"
        assert cm._CONFIG_PATH == str(yaml_file)

    def test_load_config_path_none_and_no_env(self):
        """config_path=None 且无环境变量时使用默认文件名"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("default-name")):
                    cfg = cm.load_config(auto_env=False)

        assert cfg.name == "default-name"

    def test_load_config_path_none_but_tengod_config_file_set(self):
        """config_path=None 但 TENGOD_CONFIG_FILE 有值"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write("name: env-file\n")
            tmp_path = f.name

        try:
            with patch.dict(os.environ, {"TENGOD_CONFIG_FILE": tmp_path}, clear=True):
                cfg = cm.load_config(auto_env=False)
            assert cfg.name == "env-file"
        finally:
            os.unlink(tmp_path)

    def test_load_config_path_empty_string(self):
        """config_path 为空字符串时使用默认"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("default-empty")):
                    cfg = cm.load_config("", auto_env=False)

        assert cfg.name == "default-empty"


# ============================================================================
# get_config 测试
# ============================================================================


class TestGetConfig:
    """测试 get_config 函数"""

    def test_auto_loads_when_instance_is_none(self):
        """首次调用时自动加载配置"""
        cm._CONFIG_INSTANCE = None

        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("auto-loaded")):
                    cfg = cm.get_config()

        assert cfg.name == "auto-loaded"

    def test_returns_existing_instance(self):
        """已有实例时直接返回"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("first")):
                    cfg1 = cm.load_config(auto_env=False)

        cfg2 = cm.get_config()
        assert cfg2 is cfg1

    def test_hot_reload_when_mtime_changed(self, tmp_path):
        """热重载：当文件 mtime 变化时重新加载"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("name: version-1\n")

        with patch.dict(os.environ, {}, clear=True):
            cfg1 = cm.load_config(str(yaml_file), hot_reload=True, auto_env=False)

        assert cfg1.name == "version-1"

        # 修改文件
        yaml_file.write_text("name: version-2\n")

        # 返回新配置
        with patch.dict(os.environ, {}, clear=True):
            cfg2 = cm.get_config()

        assert cfg2.name == "version-2"

    def test_no_hot_reload_when_disabled(self, tmp_path):
        """热重载关闭时不检查 mtime"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("name: version-1\n")

        with patch.dict(os.environ, {}, clear=True):
            cfg1 = cm.load_config(str(yaml_file), hot_reload=False, auto_env=False)

        # 修改文件
        yaml_file.write_text("name: version-2\n")

        cfg2 = cm.get_config()
        assert cfg2 is cfg1

    def test_no_hot_reload_when_file_removed(self, tmp_path):
        """热重载开启但文件已删除时返回旧配置"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("name: version-1\n")

        with patch.dict(os.environ, {}, clear=True):
            cfg1 = cm.load_config(str(yaml_file), hot_reload=True, auto_env=False)

        # 删除文件
        os.unlink(yaml_file)

        cfg2 = cm.get_config()
        assert cfg2 is cfg1

    def test_no_hot_reload_when_mtime_not_changed(self, tmp_path):
        """mtime 未变化时不重新加载"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("name: stable\n")

        with patch.dict(os.environ, {}, clear=True):
            cfg1 = cm.load_config(str(yaml_file), hot_reload=True, auto_env=False)

        # 不修改文件，直接调用 get_config
        cfg2 = cm.get_config()
        assert cfg2 is cfg1

    def test_get_config_after_manual_load(self, tmp_path):
        """手动 load_config 后再调用 get_config"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("name: manual\n")

        with patch.dict(os.environ, {}, clear=True):
            cfg1 = cm.load_config(str(yaml_file), auto_env=False)

        cfg2 = cm.get_config()
        assert cfg2 is cfg1


# ============================================================================
# reload_config 测试
# ============================================================================


class TestReloadConfig:
    """测试 reload_config 函数"""

    def test_reload_from_file(self, tmp_path):
        """强制从文件重新加载"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("name: original\n")

        with patch.dict(os.environ, {}, clear=True):
            cfg1 = cm.load_config(str(yaml_file), auto_env=False)
        assert cfg1.name == "original"

        yaml_file.write_text("name: updated\n")

        with patch.dict(os.environ, {}, clear=True):
            cfg2 = cm.reload_config()
        assert cfg2.name == "updated"

    def test_reload_preserves_hot_reload_flag(self, tmp_path):
        """reload 保持 hot_reload 标志"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("name: hot\n")

        with patch.dict(os.environ, {}, clear=True):
            cm.load_config(str(yaml_file), hot_reload=True, auto_env=False)

        yaml_file.write_text("name: hot-updated\n")

        with patch.dict(os.environ, {}, clear=True):
            cm.reload_config()

        assert cm._CONFIG_HOT_RELOAD is True

    def test_reload_when_no_config_loaded(self):
        """从未加载配置时调用 reload"""
        cm._CONFIG_PATH = None
        cm._CONFIG_HOT_RELOAD = False

        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("reload-default")):
                    cfg = cm.reload_config()

        assert cfg.name == "reload-default"


# ============================================================================
# get_config_dict 测试
# ============================================================================


class TestGetConfigDict:
    """测试 get_config_dict 函数"""

    def test_returns_dict(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("dict-test")):
                    result = cm.get_config_dict()

        assert isinstance(result, dict)
        assert result["name"] == "dict-test"

    def test_contains_all_sections(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("all-sections")):
                    result = cm.get_config_dict()

        for key in ["name", "server", "database", "llm", "security", "scheduler", "consensus", "knowledge", "monitoring"]:
            assert key in result, f"Missing key: {key}"

    def test_with_pydantic_v2(self):
        """通过 _PYDANTIC_V2=True 路径获取字典"""
        if _PYDANTIC_V2:
            with patch.dict(os.environ, {}, clear=True):
                with patch("os.path.exists", return_value=False):
                    with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("pydantic-dict")):
                        result = cm.get_config_dict()

            assert isinstance(result, dict)
            assert result["name"] == "pydantic-dict"


# ============================================================================
# get_server_config 测试
# ============================================================================


class TestGetServerConfig:
    """测试 get_server_config 函数"""

    def test_returns_dict(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("server-test")):
                    result = cm.get_server_config()

        assert isinstance(result, dict)
        assert result["host"] == "0.0.0.0"
        assert result["port"] == 8000
        assert result["mode"] == "auto"
        assert result["workers"] == 1
        assert result["cors_origins"] == ["*"]

    def test_custom_server_config(self, tmp_path):
        yaml_content = """\
name: custom-server
server:
  host: 192.168.1.1
  port: 9000
  mode: simple
  workers: 8
  cors_origins:
    - https://example.com
"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content)

        with patch.dict(os.environ, {}, clear=True):
            cm.load_config(str(yaml_file), auto_env=False)

        result = cm.get_server_config()
        assert result["host"] == "192.168.1.1"
        assert result["port"] == 9000
        assert result["mode"] == "simple"
        assert result["workers"] == 8
        assert result["cors_origins"] == ["https://example.com"]


# ============================================================================
# get_llm_config 测试
# ============================================================================


class TestGetLLMConfig:
    """测试 get_llm_config 函数"""

    def test_returns_dict(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("llm-test")):
                    result = cm.get_llm_config()

        assert isinstance(result, dict)
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-3.5-turbo"
        assert result["temperature"] == 0.7
        assert result["max_tokens"] == 2048

    def test_masks_long_api_key(self):
        """长 API key 应被脱敏"""
        config = _make_valid_config_dict("llm-mask")
        config["llm"]["api_key"] = "sk-1234567890abcdef"

        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=config):
                    result = cm.get_llm_config()

        assert result["api_key"] == "sk-1****cdef"  # 前4 + **** + 后4

    def test_does_not_mask_short_api_key(self):
        """短 API key 不应脱敏"""
        config = _make_valid_config_dict("llm-short")
        config["llm"]["api_key"] = "short"

        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=config):
                    result = cm.get_llm_config()

        assert result["api_key"] == "short"

    def test_does_not_mask_empty_api_key(self):
        """空 API key 不应脱敏"""
        config = _make_valid_config_dict("llm-empty")
        config["llm"]["api_key"] = ""

        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=config):
                    result = cm.get_llm_config()

        assert result["api_key"] == ""

    def test_masks_exactly_8_char_api_key(self):
        """8 字符 API key 不应脱敏（len > 8 才脱敏）"""
        config = _make_valid_config_dict("llm-8")
        config["llm"]["api_key"] = "12345678"

        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=config):
                    result = cm.get_llm_config()

        assert result["api_key"] == "12345678"

    def test_custom_llm_config(self, tmp_path):
        yaml_content = """\
name: llm-test
llm:
  provider: claude
  api_key: sk-ant-api03-very-long-key-example
  model: claude-3-opus
  temperature: 0.3
  max_tokens: 4096
  timeout: 120.0
  max_retries: 5
  retry_backoff: 3.0
"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content)

        with patch.dict(os.environ, {}, clear=True):
            cm.load_config(str(yaml_file), auto_env=False)

        result = cm.get_llm_config()
        assert result["provider"] == "claude"
        assert result["model"] == "claude-3-opus"
        assert result["temperature"] == 0.3
        assert result["max_tokens"] == 4096
        assert "****" in result["api_key"]


# ============================================================================
# init_config 测试
# ============================================================================


class TestInitConfig:
    """测试 init_config 函数"""

    def test_init_config_calls_load_config(self, tmp_path):
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("name: init-test\n")

        with patch.dict(os.environ, {}, clear=True):
            cfg = cm.init_config(str(yaml_file), hot_reload=False)

        assert cfg.name == "init-test"

    def test_init_config_with_hot_reload(self, tmp_path):
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("name: init-hot\n")

        with patch.dict(os.environ, {}, clear=True):
            cfg = cm.init_config(str(yaml_file), hot_reload=True)

        assert cfg.name == "init-hot"
        assert cm._CONFIG_HOT_RELOAD is True

    def test_init_config_without_path(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("init-default")):
                    cfg = cm.init_config()

        assert cfg.name == "init-default"


# ============================================================================
# 线程安全测试
# ============================================================================


class TestThreadSafety:
    """测试线程锁机制"""

    def test_load_config_uses_lock(self):
        """load_config 使用 _CONFIG_LOCK"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("lock-test")):
                    cfg = cm.load_config(auto_env=False)

        assert cfg.name == "lock-test"
        # 验证锁存在且可获取
        assert cm._CONFIG_LOCK.acquire(blocking=False)
        cm._CONFIG_LOCK.release()


# ============================================================================
# 边界情况测试
# ============================================================================


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_config_dict(self):
        """空配置字典"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value={"name": "tengod"}):
                    cfg = cm.load_config(auto_env=False)

        assert cfg.name == "tengod"

    def test_get_config_after_reset(self):
        """reset 全局状态后 get_config 应重新加载"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("first-load")):
                    cfg1 = cm.load_config(auto_env=False)
        assert cfg1.name == "first-load"

        cm._CONFIG_INSTANCE = None

        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("second-load")):
                    cfg2 = cm.get_config()
        assert cfg2.name == "second-load"

    def test_multiple_load_config_calls(self, tmp_path):
        """多次调用 load_config"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("name: multi-1\n")

        with patch.dict(os.environ, {}, clear=True):
            cm.load_config(str(yaml_file), auto_env=False)

        yaml_file.write_text("name: multi-2\n")

        with patch.dict(os.environ, {}, clear=True):
            cfg = cm.load_config(str(yaml_file), auto_env=False)

        assert cfg.name == "multi-2"

    def test_llm_config_key_not_present(self):
        """api_key 不在字典中"""
        config = _make_valid_config_dict("llm-no-key")
        del config["llm"]["api_key"]

        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=config):
                    result = cm.get_llm_config()

        assert "api_key" in result
        assert result["api_key"] == ""

    def test_server_config_with_cors_origins_list(self, tmp_path):
        yaml_content = """\
name: cors-test
server:
  cors_origins:
    - http://a.com
    - http://b.com
"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content)

        with patch.dict(os.environ, {}, clear=True):
            cm.load_config(str(yaml_file), auto_env=False)

        result = cm.get_server_config()
        assert "http://a.com" in result["cors_origins"]
        assert "http://b.com" in result["cors_origins"]

    def test_reload_config_after_file_deleted(self, tmp_path):
        """文件被删除后 reload_config 使用默认值"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("name: will-be-deleted\n")

        with patch.dict(os.environ, {}, clear=True):
            cm.load_config(str(yaml_file), auto_env=False)

        os.unlink(yaml_file)

        with patch.dict(os.environ, {}, clear=True):
            with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("default-after-delete")):
                cfg = cm.reload_config()

        assert cfg.name == "default-after-delete"

    def test_env_override_with_existing_pydantic_model(self):
        """_env_override 输入为 Pydantic model 实例"""
        if _PYDANTIC_V2:
            cfg = TengodConfig(name="model-name")
            with patch.dict(os.environ, {"TENGOD_HOST": "10.0.0.1"}, clear=True):
                result = cm._env_override(cfg)

            assert result["server"]["host"] == "10.0.0.1"

    def test_env_override_with_plain_object(self):
        """_env_override 输入为有 __dict__ 的普通对象"""
        class FakeConfig:
            def __init__(self):
                self.name = "fake"
                self.server = FakeServer()
                self._private = "should-be-ignored"

        class FakeServer:
            def __init__(self):
                self.host = "0.0.0.0"

        fake = FakeConfig()
        with patch.dict(os.environ, {"TENGOD_HOST": "1.1.1.1"}, clear=True):
            result = cm._env_override(fake)

        assert result["server"]["host"] == "1.1.1.1"
        assert "_private" not in result


# ============================================================================
# __all__ 导出测试
# ============================================================================


class TestExports:
    """测试模块导出"""

    def test_all_public_functions_exported(self):
        expected = [
            "load_config",
            "get_config",
            "reload_config",
            "get_config_dict",
            "get_server_config",
            "get_llm_config",
            "init_config",
            "generate_example_yaml",
        ]
        for name in expected:
            assert name in cm.__all__, f"Missing {name} in __all__"

    def test_generate_example_yaml_re_exported(self):
        """generate_example_yaml 从 config_schema 重新导出"""
        from tengod.config_manager import generate_example_yaml
        yaml_str = generate_example_yaml()
        assert "tengod-prod" in yaml_str
        assert isinstance(yaml_str, str)


# ============================================================================
# 非 Pydantic 降级路径测试
# ============================================================================


class TestNonPydanticPath:
    """测试 _PYDANTIC_V2=False 的降级路径"""

    def test_get_config_dict_non_pydantic(self):
        """get_config_dict 在非 Pydantic 路径下使用 __dict__"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("non-pydantic")):
                    with patch("tengod.config_manager._PYDANTIC_V2", False):
                        result = cm.get_config_dict()

        assert isinstance(result, dict)
        assert result["name"] == "non-pydantic"

    def test_get_server_config_non_pydantic(self):
        """get_server_config 在非 Pydantic 路径下"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("non-pydantic-server")):
                    with patch("tengod.config_manager._PYDANTIC_V2", False):
                        result = cm.get_server_config()

        assert isinstance(result, dict)
        assert "host" in result
        assert "port" in result

    def test_get_llm_config_non_pydantic(self):
        """get_llm_config 在非 Pydantic 路径下"""
        config = _make_valid_config_dict("non-pydantic-llm")
        config["llm"]["api_key"] = "sk-1234567890abcdef"

        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=config):
                    with patch("tengod.config_manager._PYDANTIC_V2", False):
                        result = cm.get_llm_config()

        assert isinstance(result, dict)
        assert "provider" in result
        assert "****" in result["api_key"]

    def test_load_config_non_pydantic(self):
        """load_config 在非 Pydantic 路径下"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch("tengod.config_manager.validate_and_load", return_value=_make_valid_config_dict("non-pydantic-load")):
                    with patch("tengod.config_manager._PYDANTIC_V2", False):
                        cfg = cm.load_config(auto_env=False)

        assert cfg.name == "non-pydantic-load"