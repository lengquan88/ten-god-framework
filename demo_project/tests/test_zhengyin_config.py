"""
test_zhengyin_config.py — ConfigManager 模块全面测试
覆盖：ConfigSource, Config, ConfigManager, ConfigWatcher
目标覆盖率：85%+
"""

import io
import json
import os
import tempfile
import threading
import time
from unittest import mock

import pytest

from tengod.正印_滋养守护.config_manager import (
    Config,
    ConfigManager,
    ConfigSource,
    ConfigWatcher,
)


# ============================================================================
# ConfigSource 枚举测试
# ============================================================================

class TestConfigSource:
    """ConfigSource 枚举值测试"""

    def test_enum_values(self):
        assert ConfigSource.ENV.value == "env"
        assert ConfigSource.FILE.value == "file"
        assert ConfigSource.DEFAULT.value == "default"
        assert ConfigSource.OVERRIDE.value == "override"

    def test_enum_members(self):
        members = list(ConfigSource)
        assert len(members) == 4
        assert ConfigSource.ENV in members
        assert ConfigSource.FILE in members
        assert ConfigSource.DEFAULT in members
        assert ConfigSource.OVERRIDE in members


# ============================================================================
# Config 数据类测试
# ============================================================================

class TestConfig:
    """Config 数据类测试"""

    def test_create_with_all_fields(self):
        c = Config(key="test_key", value="test_value", source=ConfigSource.ENV, description="测试描述")
        assert c.key == "test_key"
        assert c.value == "test_value"
        assert c.source == ConfigSource.ENV
        assert c.description == "测试描述"

    def test_create_with_defaults(self):
        c = Config(key="k", value="v")
        assert c.key == "k"
        assert c.value == "v"
        assert c.source == ConfigSource.DEFAULT
        assert c.description == ""

    def test_create_with_int_value(self):
        c = Config(key="count", value=42)
        assert c.value == 42

    def test_create_with_list_value(self):
        c = Config(key="items", value=[1, 2, 3])
        assert c.value == [1, 2, 3]

    def test_create_with_dict_value(self):
        c = Config(key="nested", value={"a": 1})
        assert c.value == {"a": 1}

    def test_equality(self):
        c1 = Config(key="k", value="v")
        c2 = Config(key="k", value="v")
        assert c1 == c2


# ============================================================================
# ConfigManager 测试
# ============================================================================

class TestConfigManagerInit:
    """ConfigManager __init__ 测试"""

    def test_default_env_prefix(self):
        cm = ConfigManager()
        assert cm._env_prefix == "TENGOD_"

    def test_custom_env_prefix(self):
        cm = ConfigManager(env_prefix="MYAPP_")
        assert cm._env_prefix == "MYAPP_"

    def test_empty_env_prefix(self):
        cm = ConfigManager(env_prefix="")
        assert cm._env_prefix == ""

    def test_initial_state_empty(self):
        cm = ConfigManager()
        assert cm._configs == {}
        assert cm._defaults == {}


class TestSetDefault:
    """set_default() 测试"""

    def test_set_default_simple(self):
        cm = ConfigManager()
        cm.set_default("key1", "value1")
        assert cm._defaults["key1"] == "value1"
        assert cm.has("key1")
        assert cm.get("key1") == "value1"

    def test_set_default_with_description(self):
        cm = ConfigManager()
        cm.set_default("key2", 42, description="答案")
        info = cm.get_info("key2")
        assert info.description == "答案"
        assert info.source == ConfigSource.DEFAULT

    def test_set_default_overwrite_defaults_dict(self):
        cm = ConfigManager()
        cm.set_default("k", "v1")
        cm.set_default("k", "v2")
        assert cm._defaults["k"] == "v2"

    def test_set_default_does_not_overwrite_existing_env_config(self):
        """已存在的 config（非 default）不会因 set_default 而被覆盖"""
        cm = ConfigManager()
        cm.set("k", "env_value", source="env")
        cm.set_default("k", "default_value")
        assert cm.get("k") == "env_value"

    def test_set_default_multiple_keys(self):
        cm = ConfigManager()
        cm.set_default("a", 1)
        cm.set_default("b", 2)
        cm.set_default("c", 3)
        assert cm.list_all() == {"a": 1, "b": 2, "c": 3}


class TestLoadFromEnv:
    """load_from_env() 测试"""

    def test_env_var_exists(self, monkeypatch):
        monkeypatch.setenv("TENGOD_TEST_KEY", "hello")
        cm = ConfigManager()
        result = cm.load_from_env("test_key")
        assert result is True
        assert cm.get("test_key") == "hello"

    def test_env_var_not_exists(self):
        cm = ConfigManager()
        result = cm.load_from_env("NONEXISTENT_KEY_XYZ")
        assert result is False

    def test_env_var_custom_prefix(self, monkeypatch):
        monkeypatch.setenv("MYAPP_DB_HOST", "localhost")
        cm = ConfigManager(env_prefix="MYAPP_")
        result = cm.load_from_env("db_host")
        assert result is True
        assert cm.get("db_host") == "localhost"

    def test_env_var_boolean_true(self, monkeypatch):
        monkeypatch.setenv("TENGOD_BOOL_FLAG", "true")
        cm = ConfigManager()
        cm.load_from_env("bool_flag")
        assert cm.get("bool_flag") is True

    def test_env_var_boolean_false(self, monkeypatch):
        monkeypatch.setenv("TENGOD_BOOL_FLAG", "false")
        cm = ConfigManager()
        cm.load_from_env("bool_flag")
        assert cm.get("bool_flag") is False

    def test_env_var_integer(self, monkeypatch):
        monkeypatch.setenv("TENGOD_PORT", "8080")
        cm = ConfigManager()
        cm.load_from_env("port")
        assert cm.get("port") == 8080
        assert isinstance(cm.get("port"), int)

    def test_env_var_float(self, monkeypatch):
        monkeypatch.setenv("TENGOD_RATE", "3.14")
        cm = ConfigManager()
        cm.load_from_env("rate")
        assert cm.get("rate") == 3.14
        assert isinstance(cm.get("rate"), float)

    def test_env_var_json_list(self, monkeypatch):
        monkeypatch.setenv("TENGOD_HOSTS", '["a","b","c"]')
        cm = ConfigManager()
        cm.load_from_env("hosts")
        assert cm.get("hosts") == ["a", "b", "c"]

    def test_env_var_json_dict(self, monkeypatch):
        monkeypatch.setenv("TENGOD_SETTINGS", '{"x": 1, "y": 2}')
        cm = ConfigManager()
        cm.load_from_env("settings")
        assert cm.get("settings") == {"x": 1, "y": 2}

    def test_env_var_source_is_env(self, monkeypatch):
        monkeypatch.setenv("TENGOD_SRC_KEY", "val")
        cm = ConfigManager()
        cm.load_from_env("src_key")
        info = cm.get_info("src_key")
        assert info.source == ConfigSource.ENV

    def test_env_var_key_uppercase_transform(self, monkeypatch):
        monkeypatch.setenv("TENGOD_MIXED_CASE", "yes")
        cm = ConfigManager()
        cm.load_from_env("Mixed_Case")
        assert cm.get("Mixed_Case") == "yes"


class TestSet:
    """set() 测试"""

    def test_set_without_source_uses_override(self):
        cm = ConfigManager()
        cm.set("key", "value")
        info = cm.get_info("key")
        assert info.source == ConfigSource.OVERRIDE

    def test_set_with_source_uses_file(self):
        cm = ConfigManager()
        cm.set("key", "value", source="/path/to/file.json")
        info = cm.get_info("key")
        assert info.source == ConfigSource.FILE

    def test_set_overwrites_existing(self):
        cm = ConfigManager()
        cm.set("key", "old")
        cm.set("key", "new")
        assert cm.get("key") == "new"

    def test_set_with_none_source(self):
        cm = ConfigManager()
        cm.set("key", "value", source=None)
        info = cm.get_info("key")
        assert info.source == ConfigSource.OVERRIDE

    def test_set_with_empty_string_source(self):
        cm = ConfigManager()
        cm.set("key", "value", source="")
        info = cm.get_info("key")
        assert info.source == ConfigSource.OVERRIDE


class TestGet:
    """get() 测试"""

    def test_get_existing_key(self):
        cm = ConfigManager()
        cm.set("key", "value")
        assert cm.get("key") == "value"

    def test_get_non_existing_key(self):
        cm = ConfigManager()
        assert cm.get("nope") is None

    def test_get_with_default(self):
        cm = ConfigManager()
        assert cm.get("nope", "fallback") == "fallback"

    def test_get_with_default_none(self):
        cm = ConfigManager()
        assert cm.get("nope", None) is None


class TestHas:
    """has() 测试"""

    def test_has_existing_key(self):
        cm = ConfigManager()
        cm.set("key", "value")
        assert cm.has("key") is True

    def test_has_non_existing_key(self):
        cm = ConfigManager()
        assert cm.has("nope") is False

    def test_has_after_set_default(self):
        cm = ConfigManager()
        cm.set_default("dk", "dv")
        assert cm.has("dk") is True


class TestGetInfo:
    """get_info() 测试"""

    def test_get_info_existing(self):
        cm = ConfigManager()
        cm.set("key", "value", source="/tmp/test.json")
        info = cm.get_info("key")
        assert isinstance(info, Config)
        assert info.key == "key"
        assert info.value == "value"

    def test_get_info_non_existing(self):
        cm = ConfigManager()
        assert cm.get_info("nope") is None

    def test_get_info_default_config(self):
        cm = ConfigManager()
        cm.set_default("dk", "dv", description="desc")
        info = cm.get_info("dk")
        assert info.source == ConfigSource.DEFAULT
        assert info.description == "desc"


class TestListAll:
    """list_all() 测试"""

    def test_list_all_empty(self):
        cm = ConfigManager()
        assert cm.list_all() == {}

    def test_list_all_returns_dict_of_values(self):
        cm = ConfigManager()
        cm.set("a", 1)
        cm.set("b", 2)
        cm.set_default("c", 3)
        assert cm.list_all() == {"a": 1, "b": 2, "c": 3}

    def test_list_all_values_not_config_objects(self):
        cm = ConfigManager()
        cm.set("k", "v")
        result = cm.list_all()
        assert not isinstance(result["k"], Config)


class TestListWithSource:
    """list_with_source() 测试"""

    def test_list_with_source_empty(self):
        cm = ConfigManager()
        assert cm.list_with_source() == {}

    def test_list_with_source_structure(self):
        cm = ConfigManager()
        cm.set_default("a", 1, description="第一项")
        cm.set("b", 2, source="/tmp/f.json")
        result = cm.list_with_source()
        assert "a" in result
        assert result["a"]["value"] == 1
        assert result["a"]["source"] == "default"
        assert result["a"]["description"] == "第一项"
        assert "b" in result
        assert result["b"]["value"] == 2
        assert result["b"]["source"] == "file"


class TestAutoCast:
    """_auto_cast() 测试"""

    def test_true_lowercase(self):
        assert ConfigManager._auto_cast("true") is True

    def test_true_uppercase(self):
        assert ConfigManager._auto_cast("TRUE") is True

    def test_true_mixed(self):
        assert ConfigManager._auto_cast("True") is True

    def test_false_lowercase(self):
        assert ConfigManager._auto_cast("false") is False

    def test_false_uppercase(self):
        assert ConfigManager._auto_cast("FALSE") is False

    def test_integer(self):
        assert ConfigManager._auto_cast("123") == 123
        assert isinstance(ConfigManager._auto_cast("123"), int)

    def test_negative_integer(self):
        assert ConfigManager._auto_cast("-456") == -456

    def test_float(self):
        assert ConfigManager._auto_cast("3.14") == 3.14
        assert isinstance(ConfigManager._auto_cast("3.14"), float)

    def test_json_list(self):
        assert ConfigManager._auto_cast('["a","b"]') == ["a", "b"]

    def test_json_dict(self):
        assert ConfigManager._auto_cast('{"x":1}') == {"x": 1}

    def test_json_invalid_falls_back_to_string(self):
        result = ConfigManager._auto_cast("[invalid json")
        assert result == "[invalid json"

    def test_plain_string(self):
        assert ConfigManager._auto_cast("hello world") == "hello world"

    def test_zero(self):
        assert ConfigManager._auto_cast("0") == 0

    def test_empty_string(self):
        assert ConfigManager._auto_cast("") == ""


class TestValidateSchema:
    """validate_schema() 测试"""

    def test_valid_data(self):
        cm = ConfigManager()
        schema = {"name": {"type": str, "required": True}, "count": {"type": int, "required": False}}
        data = {"name": "test", "count": 5}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is True
        assert errors == []

    def test_valid_data_no_optional(self):
        cm = ConfigManager()
        schema = {"name": {"type": str, "required": True}}
        data = {"name": "test"}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is True

    def test_missing_required_without_default(self):
        cm = ConfigManager()
        schema = {"name": {"type": str, "required": True}}
        data = {}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is False
        assert len(errors) == 1
        assert "缺少必需字段" in errors[0]

    def test_missing_required_with_default_fallback(self):
        cm = ConfigManager()
        schema = {"name": {"type": str, "required": True, "default": "fallback"}}
        data = {}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is True
        assert data["name"] == "fallback"

    def test_type_mismatch(self):
        cm = ConfigManager()
        schema = {"count": {"type": int, "required": True}}
        data = {"count": "not_a_number"}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is False
        assert len(errors) == 1
        assert "字段类型错误" in errors[0]

    def test_multiple_errors(self):
        cm = ConfigManager()
        schema = {
            "name": {"type": str, "required": True},
            "count": {"type": int, "required": True},
        }
        data = {}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is False
        assert len(errors) == 2

    def test_empty_schema(self):
        cm = ConfigManager()
        passed, errors = cm.validate_schema({}, {})
        assert passed is True
        assert errors == []

    def test_no_type_specified(self):
        cm = ConfigManager()
        schema = {"key": {"required": True}}
        data = {"key": "anything"}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is True


class TestWatchFile:
    """watch_file() 测试"""

    def test_watch_file_returns_config_watcher(self, tmp_path):
        f = tmp_path / "test.json"
        f.write_text("{}")
        cm = ConfigManager()
        watcher = cm.watch_file(str(f))
        assert isinstance(watcher, ConfigWatcher)
        assert watcher._file_path == str(f)


class TestLoadFromFile:
    """load_from_file() 测试"""

    # ── JSON ──────────────────────────────────────────────────

    def test_json_file(self, tmp_path):
        f = tmp_path / "config.json"
        f.write_text('{"key1": "val1", "key2": 42}')
        cm = ConfigManager()
        result = cm.load_from_file(str(f))
        assert result == {"key1": "val1", "key2": 42}
        assert cm.get("key1") == "val1"
        assert cm.get("key2") == 42

    # ── YAML (simple, via fallback parser) ────────────────────

    def test_yaml_file_simple(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text("key1: val1\nkey2: 42\n")
        cm = ConfigManager()
        result = cm.load_from_file(str(f))
        # yaml 库已安装时 safe_load 会将 "42" 转为 int
        assert result["key1"] == "val1"
        assert result["key2"] == 42
        assert cm.get("key1") == "val1"

    def test_yaml_file_with_comments_and_blanks(self, tmp_path):
        f = tmp_path / "config.yml"
        f.write_text("# comment\n\nkey_a: hello\n  \nkey_b: world\n")
        cm = ConfigManager()
        result = cm.load_from_file(str(f))
        assert result["key_a"] == "hello"
        assert result["key_b"] == "world"

    def test_yaml_file_with_quotes(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text('name: "quoted_value"\nflag: \'single_quoted\'\n')
        cm = ConfigManager()
        result = cm.load_from_file(str(f))
        assert result["name"] == "quoted_value"
        assert result["flag"] == "single_quoted"

    def test_yaml_file_bool_key(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text("enabled:\n")
        cm = ConfigManager()
        result = cm.load_from_file(str(f))
        # yaml.safe_load 将空值解析为 None
        assert result["enabled"] is None

    # ── INI ───────────────────────────────────────────────────

    def test_ini_file(self, tmp_path):
        f = tmp_path / "config.ini"
        f.write_text("[section1]\nkey1 = val1\nkey2 = 42\n\n[section2]\nkey_a = hello\n")
        cm = ConfigManager()
        result = cm.load_from_file(str(f))
        assert "section1" in result
        assert result["section1"]["key1"] == "val1"
        assert result["section1"]["key2"] == "42"
        assert result["section2"]["key_a"] == "hello"

    # ── TOML ──────────────────────────────────────────────────

    def test_toml_file(self, tmp_path):
        f = tmp_path / "config.toml"
        f.write_text('key1 = "val1"\nkey2 = 42\nflag = true\n')
        cm = ConfigManager()
        result = cm.load_from_file(str(f))
        assert result["key1"] == "val1"
        assert result["key2"] == 42
        assert result["flag"] is True

    def test_toml_file_with_comments_and_sections(self, tmp_path):
        f = tmp_path / "config.toml"
        f.write_text("# comment\nkey_a = \"hello\"\n\n[section]\n\nkey_b = \"world\"\n")
        cm = ConfigManager()
        result = cm.load_from_file(str(f))
        assert result["key_a"] == "hello"
        # _parse_toml 跳过 section header 行但继续解析后续的 key-value

    # ── 错误处理 ──────────────────────────────────────────────

    def test_non_existent_file_raises(self):
        cm = ConfigManager()
        with pytest.raises(FileNotFoundError, match="配置文件不存在"):
            cm.load_from_file("/nonexistent/path/config.json")

    def test_unsupported_extension_raises(self, tmp_path):
        f = tmp_path / "config.txt"
        f.write_text("data")
        cm = ConfigManager()
        with pytest.raises(ValueError, match="不支持的配置文件格式"):
            cm.load_from_file(str(f))

    def test_unknown_extension_raises(self, tmp_path):
        f = tmp_path / "config.xml"
        f.write_text("<root/>")
        cm = ConfigManager()
        with pytest.raises(ValueError, match="不支持的配置文件格式"):
            cm.load_from_file(str(f))

    def test_yaml_fallback_when_import_error(self, tmp_path):
        """当 yaml 库不可用时，回退到 _parse_simple_yaml"""
        f = tmp_path / "config.yaml"
        f.write_text("key1: val1\nkey2: 42\n")
        cm = ConfigManager()
        # 模拟 yaml 导入失败
        with mock.patch.dict("sys.modules", {"yaml": None}):
            result = cm.load_from_file(str(f))
        assert result == {"key1": "val1", "key2": "42"}


class TestParseSimpleYaml:
    """_parse_simple_yaml() 测试"""

    def test_basic_key_value(self):
        cm = ConfigManager()
        f = io.StringIO("key1: val1\nkey2: val2\n")
        result = cm._parse_simple_yaml(f)
        assert result == {"key1": "val1", "key2": "val2"}

    def test_skip_comments(self):
        cm = ConfigManager()
        f = io.StringIO("# comment\nkey: value\n")
        result = cm._parse_simple_yaml(f)
        assert result == {"key": "value"}

    def test_skip_empty_lines(self):
        cm = ConfigManager()
        f = io.StringIO("\n\nkey: value\n\n")
        result = cm._parse_simple_yaml(f)
        assert result == {"key": "value"}

    def test_bool_key(self):
        cm = ConfigManager()
        f = io.StringIO("enabled:\n")
        result = cm._parse_simple_yaml(f)
        assert result == {"enabled": True}

    def test_strip_quotes(self):
        cm = ConfigManager()
        f = io.StringIO('name: "double"\nflag: \'single\'\n')
        result = cm._parse_simple_yaml(f)
        assert result["name"] == "double"
        assert result["flag"] == "single"

    def test_empty_file(self):
        cm = ConfigManager()
        f = io.StringIO("")
        result = cm._parse_simple_yaml(f)
        assert result == {}


class TestParseToml:
    """_parse_toml() 测试"""

    def test_basic_key_value(self):
        cm = ConfigManager()
        result = cm._parse_toml('key1 = "val1"\nkey2 = "val2"\n')
        assert result == {"key1": "val1", "key2": "val2"}

    def test_skip_comments(self):
        cm = ConfigManager()
        result = cm._parse_toml("# comment\nkey = \"value\"\n")
        assert result == {"key": "value"}

    def test_skip_sections(self):
        cm = ConfigManager()
        # _parse_toml 跳过 [section] 行但继续解析后续 key-value
        result = cm._parse_toml("[section]\nkey = \"value\"\n")
        assert result == {"key": "value"}

    def test_skip_empty_lines(self):
        cm = ConfigManager()
        result = cm._parse_toml("\n\nkey = \"value\"\n\n")
        assert result == {"key": "value"}

    def test_boolean_true(self):
        cm = ConfigManager()
        result = cm._parse_toml("flag = true\n")
        assert result["flag"] is True

    def test_boolean_false(self):
        cm = ConfigManager()
        result = cm._parse_toml("flag = false\n")
        assert result["flag"] is False

    def test_integer(self):
        cm = ConfigManager()
        result = cm._parse_toml("port = 8080\n")
        assert result["port"] == 8080
        assert isinstance(result["port"], int)

    def test_empty_content(self):
        cm = ConfigManager()
        result = cm._parse_toml("")
        assert result == {}

    def test_strip_quotes(self):
        cm = ConfigManager()
        result = cm._parse_toml('name = "hello"\n')
        assert result["name"] == "hello"


# ============================================================================
# ConfigWatcher 测试
# ============================================================================

class TestConfigWatcherInit:
    """ConfigWatcher __init__ 测试"""

    def test_init_with_file_path(self, tmp_path):
        f = tmp_path / "watch.json"
        f.write_text("{}")
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(f))
        assert w._file_path == str(f)
        assert w._config is cm
        assert w._interval == 2.0
        assert w._running is False
        assert w._thread is None
        assert w._on_change_callbacks == []

    def test_init_with_custom_interval(self, tmp_path):
        f = tmp_path / "watch.json"
        f.write_text("{}")
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(f), interval=0.5)
        assert w._interval == 0.5

    def test_init_with_non_existent_file(self, tmp_path):
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(tmp_path / "nonexistent.json"))
        assert w._mtime == 0


class TestConfigWatcherOnChange:
    """on_change() 测试"""

    def test_register_callback(self, tmp_path):
        f = tmp_path / "w.json"
        f.write_text("{}")
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(f))

        calls = []

        def cb(data):
            calls.append(data)

        w.on_change(cb)
        assert len(w._on_change_callbacks) == 1
        assert w._on_change_callbacks[0] is cb

    def test_register_multiple_callbacks(self, tmp_path):
        f = tmp_path / "w.json"
        f.write_text("{}")
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(f))

        w.on_change(lambda d: None)
        w.on_change(lambda d: None)
        assert len(w._on_change_callbacks) == 2


class TestConfigWatcherStartStop:
    """start() / stop() 测试"""

    def test_start_creates_thread(self, tmp_path):
        f = tmp_path / "w.json"
        f.write_text("{}")
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(f), interval=0.1)
        w.start()
        assert w._running is True
        assert w._thread is not None
        assert isinstance(w._thread, threading.Thread)
        w.stop()

    def test_stop_stops_thread(self, tmp_path):
        f = tmp_path / "w.json"
        f.write_text("{}")
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(f), interval=0.1)
        w.start()
        w.stop()
        assert w._running is False

    def test_stop_without_start_does_not_raise(self, tmp_path):
        f = tmp_path / "w.json"
        f.write_text("{}")
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(f))
        w.stop()
        assert w._running is False

    def test_double_start_does_not_raise(self, tmp_path):
        """start twice should be OK"""
        f = tmp_path / "w.json"
        f.write_text("{}")
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(f), interval=0.1)
        w.start()
        w.start()
        w.stop()


class TestConfigWatcherLoop:
    """_loop() 测试"""

    def test_loop_detects_change_and_reloads(self, tmp_path):
        f = tmp_path / "loop.json"
        f.write_text('{"key": "old"}')
        cm = ConfigManager()
        # 先加载一次，让 ConfigManager 有初始数据
        cm.load_from_file(str(f))

        callbacks_fired = []
        w = ConfigWatcher(cm, str(f), interval=0.05)
        w.on_change(lambda data: callbacks_fired.append(data))

        original_mtime = os.path.getmtime(str(f))

        # 修改文件
        f.write_text('{"key": "new"}')

        w._running = True

        # 让 time.sleep 在第一次调用后停止循环
        def stop_loop(*args, **kwargs):
            w._running = False

        with mock.patch("time.sleep", side_effect=stop_loop):
            with mock.patch("os.path.getmtime", return_value=original_mtime + 1):
                w._loop()

        assert len(callbacks_fired) == 1
        assert callbacks_fired[0]["old"] == {"key": "old"}
        assert callbacks_fired[0]["new"]["key"] == "new"
        assert callbacks_fired[0]["file"] == str(f)

    def test_loop_skips_when_not_running(self, tmp_path):
        f = tmp_path / "loop2.json"
        f.write_text('{"key": "v"}')
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(f), interval=0.05)
        w._running = False
        # 不应该进入循环体
        w._loop()  # 直接返回

    def test_loop_skips_nonexistent_file(self, tmp_path):
        non_existent = tmp_path / "does_not_exist.json"
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(non_existent), interval=0.05)
        w._running = True

        def stop_loop(*args, **kwargs):
            w._running = False

        with mock.patch("time.sleep", side_effect=stop_loop):
            # 文件不存在时不应崩溃
            w._loop()

    def test_loop_callback_error_handled(self, tmp_path, capsys):
        f = tmp_path / "loop3.json"
        f.write_text('{"key": "old"}')
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(f), interval=0.05)

        def bad_callback(data):
            raise RuntimeError("callback error")

        w.on_change(bad_callback)

        original_mtime = os.path.getmtime(str(f))

        # 修改文件
        f.write_text('{"key": "new"}')

        w._running = True

        def stop_loop(*args, **kwargs):
            w._running = False

        with mock.patch("time.sleep", side_effect=stop_loop):
            with mock.patch("os.path.getmtime", return_value=original_mtime + 1):
                w._loop()

        captured = capsys.readouterr()
        assert "回调错误" in captured.out

    def test_loop_reload_failure_handled(self, tmp_path, capsys):
        """_loop 中 load_from_file 失败时不应崩溃"""
        f = tmp_path / "loop4.json"
        f.write_text('{"key": "old"}')
        cm = ConfigManager()
        cm.load_from_file(str(f))

        w = ConfigWatcher(cm, str(f), interval=0.05)
        original_mtime = os.path.getmtime(str(f))

        # 修改文件为无效 JSON
        f.write_text("not valid json")

        w._running = True

        def stop_loop(*args, **kwargs):
            w._running = False

        with mock.patch("time.sleep", side_effect=stop_loop):
            with mock.patch("os.path.getmtime", return_value=original_mtime + 1):
                w._loop()

        captured = capsys.readouterr()
        assert "热加载失败" in captured.out


# ============================================================================
# 边界情况与综合测试
# ============================================================================

class TestEdgeCases:
    """边界情况测试"""

    def test_empty_env_prefix_load_from_env(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY", "val")
        cm = ConfigManager(env_prefix="")
        assert cm.load_from_env("TEST_KEY") is True
        assert cm.get("TEST_KEY") == "val"

    def test_special_characters_in_keys(self):
        cm = ConfigManager()
        cm.set("key-with-dashes", "v1")
        cm.set("key.with.dots", "v2")
        cm.set("key_with_underscores", "v3")
        cm.set("中文键", "v4")
        assert cm.get("key-with-dashes") == "v1"
        assert cm.get("key.with.dots") == "v2"
        assert cm.get("key_with_underscores") == "v3"
        assert cm.get("中文键") == "v4"

    def test_empty_config_manager(self):
        cm = ConfigManager()
        assert cm.list_all() == {}
        assert cm.list_with_source() == {}
        assert cm.get("anything") is None
        assert cm.has("anything") is False
        assert cm.get_info("anything") is None

    def test_overwrite_default_with_set(self):
        cm = ConfigManager()
        cm.set_default("k", "default_val")
        cm.set("k", "override_val")
        assert cm.get("k") == "override_val"
        info = cm.get_info("k")
        assert info.source == ConfigSource.OVERRIDE

    def test_env_overrides_default(self, monkeypatch):
        monkeypatch.setenv("TENGOD_KEY", "env_val")
        cm = ConfigManager()
        cm.set_default("key", "default_val")
        cm.load_from_env("key")
        assert cm.get("key") == "env_val"

    def test_load_from_env_non_string_key_handling(self, monkeypatch):
        """确保 key 名被正确大写处理"""
        monkeypatch.setenv("TENGOD_LOWERCASE", "hello")
        cm = ConfigManager()
        cm.load_from_env("lowercase")
        assert cm.get("lowercase") == "hello"

    def test_auto_cast_boolean_priority_over_numeric(self):
        """_auto_cast 中 "true"/"false" 应优先于数字解析"""
        # 这些字符串不是数字，但确保逻辑正确
        assert ConfigManager._auto_cast("true") is True
        assert ConfigManager._auto_cast("false") is False

    def test_auto_cast_negative_float(self):
        assert ConfigManager._auto_cast("-2.5") == -2.5

    def test_parse_simple_yaml_leading_trailing_spaces(self):
        cm = ConfigManager()
        f = io.StringIO("  key  :   value  \n")
        result = cm._parse_simple_yaml(f)
        assert result == {"key": "value"}

    def test_load_from_file_with_source_in_info(self, tmp_path):
        f = tmp_path / "src_test.json"
        f.write_text('{"key": "file_val"}')
        cm = ConfigManager()
        cm.load_from_file(str(f))
        info = cm.get_info("key")
        assert info.source == ConfigSource.FILE
        # 注意：source 存的是 file_path 字符串但被转为 ConfigSource.FILE
        # 因为 set() 在 source 非空时使用 ConfigSource.FILE
        assert info.value == "file_val"

    def test_validate_schema_mixed_required_and_optional(self):
        cm = ConfigManager()
        schema = {
            "name": {"type": str, "required": True},
            "age": {"type": int, "required": False},
            "email": {"type": str, "required": True, "default": "no-reply@example.com"},
        }
        data = {"name": "张三", "age": 30}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is True
        assert data["email"] == "no-reply@example.com"

    def test_validate_schema_required_with_default_and_no_data(self):
        cm = ConfigManager()
        schema = {"key": {"type": str, "required": True, "default": "fb"}}
        data = {}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is True
        assert data["key"] == "fb"