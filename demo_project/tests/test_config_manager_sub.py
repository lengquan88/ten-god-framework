"""
test_config_manager_sub.py — tengod.正印_滋养守护.config_manager 全面补充测试
覆盖：ConfigSource, Config, ConfigManager, ConfigWatcher
目标覆盖率：100%
"""

from __future__ import annotations

import io
import json
import os
import threading
from unittest.mock import MagicMock, mock_open, patch

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

    def test_all_enum_values(self):
        """所有枚举值"""
        assert ConfigSource.ENV.value == "env"
        assert ConfigSource.FILE.value == "file"
        assert ConfigSource.DEFAULT.value == "default"
        assert ConfigSource.OVERRIDE.value == "override"

    def test_all_enum_members_present(self):
        """所有成员存在"""
        members = list(ConfigSource)
        assert len(members) == 4
        names = {m.name for m in members}
        assert names == {"ENV", "FILE", "DEFAULT", "OVERRIDE"}


# ============================================================================
# Config 数据类测试
# ============================================================================


class TestConfig:
    """Config 数据类测试"""

    def test_create_with_all_fields(self):
        """创建时传入所有字段"""
        c = Config(
            key="test_key",
            value="test_value",
            source=ConfigSource.ENV,
            description="test description",
        )
        assert c.key == "test_key"
        assert c.value == "test_value"
        assert c.source == ConfigSource.ENV
        assert c.description == "test description"

    def test_default_source_is_default(self):
        """默认 source 是 DEFAULT"""
        c = Config(key="k", value="v")
        assert c.source == ConfigSource.DEFAULT

    def test_default_description_is_empty(self):
        """默认 description 是空字符串"""
        c = Config(key="k", value="v")
        assert c.description == ""


# ============================================================================
# ConfigManager __init__ 测试
# ============================================================================


class TestConfigManagerInit:
    """ConfigManager __init__ 测试"""

    def test_default_env_prefix_is_tengod(self):
        """默认 env_prefix 是 TENGOD_"""
        cm = ConfigManager()
        assert cm._env_prefix == "TENGOD_"

    def test_custom_env_prefix(self):
        """自定义 env_prefix"""
        cm = ConfigManager(env_prefix="MYAPP_")
        assert cm._env_prefix == "MYAPP_"

    def test_initial_state_is_empty(self):
        """初始化状态为空"""
        cm = ConfigManager()
        assert cm._configs == {}
        assert cm._defaults == {}


# ============================================================================
# set_default() 测试
# ============================================================================


class TestSetDefault:
    """set_default() 测试"""

    def test_set_default_value(self):
        """设置默认值"""
        cm = ConfigManager()
        cm.set_default("key1", "value1")
        assert cm._defaults["key1"] == "value1"

    def test_get_returns_default(self):
        """get() 返回默认值"""
        cm = ConfigManager()
        cm.set_default("key1", "value1")
        assert cm.get("key1") == "value1"

    def test_default_not_overwritten_if_already_set(self):
        """已存在的配置不会被 set_default 覆盖"""
        cm = ConfigManager()
        cm.set("key", "set_value")
        cm.set_default("key", "default_value")
        assert cm.get("key") == "set_value"

    def test_set_default_with_description(self):
        """set_default 带 description"""
        cm = ConfigManager()
        cm.set_default("key2", 42, description="answer")
        info = cm.get_info("key2")
        assert info.description == "answer"
        assert info.source == ConfigSource.DEFAULT

    def test_multiple_set_default_calls(self):
        """多次 set_default 调用"""
        cm = ConfigManager()
        cm.set_default("k", "v1")
        cm.set_default("k", "v2")
        assert cm._defaults["k"] == "v2"
        # 但 config 中的值不更新（因为 key 已存在）
        assert cm.get("k") == "v1"


# ============================================================================
# set() 测试
# ============================================================================


class TestSet:
    """set() 测试"""

    def test_set_value(self):
        """设置值"""
        cm = ConfigManager()
        cm.set("key", "value")
        assert cm.get("key") == "value"

    def test_value_source_is_override(self):
        """不带 source 时 source 为 OVERRIDE"""
        cm = ConfigManager()
        cm.set("key", "value")
        info = cm.get_info("key")
        assert info.source == ConfigSource.OVERRIDE

    def test_set_with_source_parameter(self):
        """带 source 参数时 source 为 FILE"""
        cm = ConfigManager()
        cm.set("key", "value", source="/path/to/file.json")
        info = cm.get_info("key")
        assert info.source == ConfigSource.FILE

    def test_set_with_none_source(self):
        """source=None 时 source 为 OVERRIDE"""
        cm = ConfigManager()
        cm.set("key", "value", source=None)
        info = cm.get_info("key")
        assert info.source == ConfigSource.OVERRIDE

    def test_set_with_empty_string_source(self):
        """source="" 时 source 为 OVERRIDE"""
        cm = ConfigManager()
        cm.set("key", "value", source="")
        info = cm.get_info("key")
        assert info.source == ConfigSource.OVERRIDE

    def test_set_overrides_default(self):
        """set() 覆盖默认值"""
        cm = ConfigManager()
        cm.set_default("k", "default_val")
        cm.set("k", "override_val")
        assert cm.get("k") == "override_val"

    def test_set_after_set_default(self):
        """set() 在 set_default() 之后调用"""
        cm = ConfigManager()
        cm.set_default("k", "default_val")
        cm.set("k", "new_val")
        info = cm.get_info("k")
        assert info.value == "new_val"
        assert info.source == ConfigSource.OVERRIDE


# ============================================================================
# get() 测试
# ============================================================================


class TestGet:
    """get() 测试"""

    def test_get_existing_value(self):
        """获取已存在的值"""
        cm = ConfigManager()
        cm.set("key", "value")
        assert cm.get("key") == "value"

    def test_get_non_existent_returns_default(self):
        """获取不存在的 key 返回默认值"""
        cm = ConfigManager()
        assert cm.get("nope", "default") == "default"

    def test_get_non_existent_returns_none(self):
        """获取不存在的 key 返回 None"""
        cm = ConfigManager()
        assert cm.get("nope") is None


# ============================================================================
# has() 测试
# ============================================================================


class TestHas:
    """has() 测试"""

    def test_has_true_for_existing_key(self):
        """已存在的 key 返回 True"""
        cm = ConfigManager()
        cm.set("key", "value")
        assert cm.has("key") is True

    def test_has_false_for_non_existing_key(self):
        """不存在的 key 返回 False"""
        cm = ConfigManager()
        assert cm.has("nope") is False


# ============================================================================
# get_info() 测试
# ============================================================================


class TestGetInfo:
    """get_info() 测试"""

    def test_get_info_returns_config_object(self):
        """返回 Config 对象"""
        cm = ConfigManager()
        cm.set("key", "value")
        info = cm.get_info("key")
        assert isinstance(info, Config)
        assert info.key == "key"
        assert info.value == "value"

    def test_get_info_returns_none_for_non_existing(self):
        """不存在的 key 返回 None"""
        cm = ConfigManager()
        assert cm.get_info("nope") is None


# ============================================================================
# list_all() 测试
# ============================================================================


class TestListAll:
    """list_all() 测试"""

    def test_list_all_returns_dict_of_all_configs(self):
        """返回所有配置的字典"""
        cm = ConfigManager()
        cm.set("a", 1)
        cm.set_default("b", 2)
        result = cm.list_all()
        assert result == {"a": 1, "b": 2}

    def test_list_all_empty_initially(self):
        """初始为空"""
        cm = ConfigManager()
        assert cm.list_all() == {}


# ============================================================================
# list_with_source() 测试
# ============================================================================


class TestListWithSource:
    """list_with_source() 测试"""

    def test_list_with_source_returns_dict_with_source_info(self):
        """返回带来源信息的字典"""
        cm = ConfigManager()
        cm.set_default("a", 1, description="item a")
        cm.set("b", 2, source="/tmp/f.json")
        result = cm.list_with_source()
        assert "a" in result
        assert result["a"]["value"] == 1
        assert result["a"]["source"] == "default"
        assert result["a"]["description"] == "item a"
        assert "b" in result
        assert result["b"]["value"] == 2
        assert result["b"]["source"] == "file"

    def test_list_with_source_includes_description(self):
        """包含 description 字段"""
        cm = ConfigManager()
        cm.set_default("key", "val", description="desc text")
        result = cm.list_with_source()
        assert result["key"]["description"] == "desc text"


# ============================================================================
# load_from_env() 测试
# ============================================================================


class TestLoadFromEnv:
    """load_from_env() 测试"""

    def test_returns_true_when_env_var_exists(self):
        """环境变量存在时返回 True"""
        with patch.dict(os.environ, {"TENGOD_KEY": "value"}):
            cm = ConfigManager()
            result = cm.load_from_env("key")
            assert result is True

    def test_returns_false_when_env_var_not_exists(self):
        """环境变量不存在时返回 False"""
        with patch.dict(os.environ, {}, clear=True):
            cm = ConfigManager()
            result = cm.load_from_env("NONEXISTENT_KEY")
            assert result is False

    def test_auto_cast_boolean_true(self):
        """_auto_cast 布尔值 true"""
        with patch.dict(os.environ, {"TENGOD_FLAG": "true"}):
            cm = ConfigManager()
            cm.load_from_env("flag")
            assert cm.get("flag") is True

    def test_auto_cast_boolean_false(self):
        """_auto_cast 布尔值 false"""
        with patch.dict(os.environ, {"TENGOD_FLAG": "false"}):
            cm = ConfigManager()
            cm.load_from_env("flag")
            assert cm.get("flag") is False

    def test_auto_cast_integer(self):
        """_auto_cast 整数值"""
        with patch.dict(os.environ, {"TENGOD_PORT": "8080"}):
            cm = ConfigManager()
            cm.load_from_env("port")
            assert cm.get("port") == 8080
            assert isinstance(cm.get("port"), int)

    def test_auto_cast_float(self):
        """_auto_cast 浮点值"""
        with patch.dict(os.environ, {"TENGOD_RATE": "3.14"}):
            cm = ConfigManager()
            cm.load_from_env("rate")
            assert cm.get("rate") == 3.14
            assert isinstance(cm.get("rate"), float)

    def test_auto_cast_json_list(self):
        """_auto_cast JSON 数组"""
        with patch.dict(os.environ, {"TENGOD_HOSTS": '["a","b","c"]'}):
            cm = ConfigManager()
            cm.load_from_env("hosts")
            assert cm.get("hosts") == ["a", "b", "c"]

    def test_auto_cast_json_dict(self):
        """_auto_cast JSON 对象"""
        with patch.dict(os.environ, {"TENGOD_SETTINGS": '{"x":1,"y":2}'}):
            cm = ConfigManager()
            cm.load_from_env("settings")
            assert cm.get("settings") == {"x": 1, "y": 2}

    def test_auto_cast_plain_string(self):
        """_auto_cast 普通字符串"""
        with patch.dict(os.environ, {"TENGOD_NAME": "hello world"}):
            cm = ConfigManager()
            cm.load_from_env("name")
            assert cm.get("name") == "hello world"

    def test_env_source_is_set(self):
        """环境变量来源为 ENV"""
        with patch.dict(os.environ, {"TENGOD_KEY": "val"}):
            cm = ConfigManager()
            cm.load_from_env("key")
            info = cm.get_info("key")
            assert info.source == ConfigSource.ENV

    def test_env_overrides_default(self):
        """load_from_env() 在 set_default() 之后，环境变量覆盖默认值"""
        with patch.dict(os.environ, {"TENGOD_KEY": "env_val"}):
            cm = ConfigManager()
            cm.set_default("key", "default_val")
            cm.load_from_env("key")
            assert cm.get("key") == "env_val"


# ============================================================================
# _auto_cast() 测试
# ============================================================================


class TestAutoCast:
    """_auto_cast() 静态方法测试"""

    def test_true_lowercase(self):
        assert ConfigManager._auto_cast("true") is True

    def test_true_uppercase(self):
        assert ConfigManager._auto_cast("TRUE") is True

    def test_true_mixedcase(self):
        assert ConfigManager._auto_cast("True") is True

    def test_false_lowercase(self):
        assert ConfigManager._auto_cast("false") is False

    def test_false_uppercase(self):
        assert ConfigManager._auto_cast("FALSE") is False

    def test_false_mixedcase(self):
        assert ConfigManager._auto_cast("False") is False

    def test_integer_123(self):
        assert ConfigManager._auto_cast("123") == 123
        assert isinstance(ConfigManager._auto_cast("123"), int)

    def test_negative_integer(self):
        assert ConfigManager._auto_cast("-456") == -456

    def test_float_3_14(self):
        assert ConfigManager._auto_cast("3.14") == 3.14
        assert isinstance(ConfigManager._auto_cast("3.14"), float)

    def test_negative_float(self):
        assert ConfigManager._auto_cast("-2.5") == -2.5

    def test_json_array(self):
        assert ConfigManager._auto_cast("[1,2,3]") == [1, 2, 3]

    def test_json_object(self):
        assert ConfigManager._auto_cast('{"a":1}') == {"a": 1}

    def test_plain_string(self):
        assert ConfigManager._auto_cast("plain") == "plain"

    def test_invalid_json_falls_back_to_string(self):
        result = ConfigManager._auto_cast("[invalid")
        assert result == "[invalid"

    def test_zero(self):
        assert ConfigManager._auto_cast("0") == 0

    def test_empty_string(self):
        assert ConfigManager._auto_cast("") == ""


# ============================================================================
# load_from_file() 测试
# ============================================================================


class TestLoadFromFile:
    """load_from_file() 测试"""

    # ── JSON 文件 ──

    def test_json_file_load(self):
        """加载 JSON 文件"""
        m = mock_open(read_data='{"key1": "val1", "key2": 42}')
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", m):
                cm = ConfigManager()
                result = cm.load_from_file("config.json")
                assert result == {"key1": "val1", "key2": 42}
                assert cm.get("key1") == "val1"
                assert cm.get("key2") == 42

    # ── YAML 文件（有 yaml 库） ──

    def test_yaml_file_load_with_yaml_import(self, tmp_path):
        """加载 YAML 文件（yaml 库可用时）"""
        f = tmp_path / "config.yaml"
        f.write_text("key1: val1\nkey2: 42\n")
        cm = ConfigManager()
        result = cm.load_from_file(str(f))
        assert result["key1"] == "val1"
        # yaml.safe_load 会将 "42" 转为 int（取决于 yaml 库是否安装）
        # 无 yaml 库时回退到简单解析，值为字符串 "42"
        assert result["key2"] in (42, "42")

    # ── YAML 文件（无 yaml 库，回退到简单解析） ──

    def test_yaml_file_load_without_yaml_fallback(self):
        """加载 YAML 文件（无 yaml 库时回退到简单解析）"""
        m = mock_open(read_data="key1: val1\nkey2: 42\n")
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", m):
                with patch.dict("sys.modules", {"yaml": None}):
                    cm = ConfigManager()
                    result = cm.load_from_file("config.yaml")
                    assert result == {"key1": "val1", "key2": "42"}

    # ── TOML 文件 ──

    def test_toml_file_load(self):
        """加载 TOML 文件"""
        m = mock_open(read_data='key1 = "val1"\nkey2 = 42\nflag = true\n')
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", m):
                cm = ConfigManager()
                result = cm.load_from_file("config.toml")
                assert result["key1"] == "val1"
                assert result["key2"] == 42
                assert result["flag"] is True

    # ── INI 文件 ──

    def test_ini_file_load(self, tmp_path):
        """加载 INI 文件"""
        f = tmp_path / "config.ini"
        f.write_text("[section1]\nkey1 = val1\nkey2 = 42\n\n[section2]\nkey_a = hello\n")
        cm = ConfigManager()
        result = cm.load_from_file(str(f))
        assert "section1" in result
        assert result["section1"]["key1"] == "val1"
        assert result["section1"]["key2"] == "42"
        assert result["section2"]["key_a"] == "hello"

    # ── 错误处理 ──

    def test_non_existent_file_raises_file_not_found(self):
        """不存在的文件抛出 FileNotFoundError"""
        with patch("os.path.exists", return_value=False):
            cm = ConfigManager()
            with pytest.raises(FileNotFoundError, match="配置文件不存在"):
                cm.load_from_file("/nonexistent/config.json")

    def test_unsupported_extension_raises_value_error(self):
        """不支持的后缀抛出 ValueError"""
        m = mock_open(read_data="data")
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", m):
                cm = ConfigManager()
                with pytest.raises(ValueError, match="不支持的配置文件格式"):
                    cm.load_from_file("config.txt")

    def test_non_dict_data_does_not_break(self):
        """非 dict 数据不会导致 break"""
        m = mock_open(read_data="[1, 2, 3]")
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", m):
                cm = ConfigManager()
                result = cm.load_from_file("config.json")
                # JSON 返回 list，isinstance(data, dict) 为 False，不设置任何 config
                assert result == [1, 2, 3]
                assert cm.list_all() == {}

    # ── 带 source 信息 ──

    def test_load_from_file_sets_file_source(self, tmp_path):
        """load_from_file 设置 source 为 FILE"""
        f = tmp_path / "config.json"
        f.write_text('{"key": "file_val"}')
        cm = ConfigManager()
        cm.load_from_file(str(f))
        info = cm.get_info("key")
        assert info.source == ConfigSource.FILE
        assert info.value == "file_val"


# ============================================================================
# _parse_simple_yaml() 测试
# ============================================================================


class TestParseSimpleYaml:
    """_parse_simple_yaml() 测试"""

    def test_basic_key_value(self):
        """基本的 key: value"""
        cm = ConfigManager()
        f = io.StringIO("key1: val1\nkey2: val2\n")
        result = cm._parse_simple_yaml(f)
        assert result == {"key1": "val1", "key2": "val2"}

    def test_comment_lines_skipped(self):
        """注释行跳过"""
        cm = ConfigManager()
        f = io.StringIO("# comment\nkey: value\n")
        result = cm._parse_simple_yaml(f)
        assert result == {"key": "value"}

    def test_empty_lines_skipped(self):
        """空行跳过"""
        cm = ConfigManager()
        f = io.StringIO("\n\nkey: value\n\n")
        result = cm._parse_simple_yaml(f)
        assert result == {"key": "value"}

    def test_lines_ending_with_colon_boolean(self):
        """以 : 结尾的行为布尔值 True"""
        cm = ConfigManager()
        f = io.StringIO("enabled:\n")
        result = cm._parse_simple_yaml(f)
        assert result == {"enabled": True}

    def test_strip_quotes(self):
        """去除引号"""
        cm = ConfigManager()
        f = io.StringIO('name: "double"\nflag: \'single\'\n')
        result = cm._parse_simple_yaml(f)
        assert result["name"] == "double"
        assert result["flag"] == "single"

    def test_empty_file(self):
        """空文件"""
        cm = ConfigManager()
        f = io.StringIO("")
        result = cm._parse_simple_yaml(f)
        assert result == {}

    def test_lines_without_colon_ignored(self):
        """没有冒号的行被忽略"""
        cm = ConfigManager()
        f = io.StringIO("plain text\nkey: val\n")
        result = cm._parse_simple_yaml(f)
        assert result == {"key": "val"}


# ============================================================================
# _parse_toml() 测试
# ============================================================================


class TestParseToml:
    """_parse_toml() 测试"""

    def test_basic_key_value(self):
        """基本 key = value"""
        cm = ConfigManager()
        result = cm._parse_toml('key1 = "val1"\nkey2 = "val2"\n')
        assert result == {"key1": "val1", "key2": "val2"}

    def test_integer_values(self):
        """整数值"""
        cm = ConfigManager()
        result = cm._parse_toml("port = 8080\n")
        assert result["port"] == 8080
        assert isinstance(result["port"], int)

    def test_boolean_true(self):
        """布尔值 true"""
        cm = ConfigManager()
        result = cm._parse_toml("flag = true\n")
        assert result["flag"] is True

    def test_boolean_false(self):
        """布尔值 false"""
        cm = ConfigManager()
        result = cm._parse_toml("flag = false\n")
        assert result["flag"] is False

    def test_comments_skipped(self):
        """注释行跳过"""
        cm = ConfigManager()
        result = cm._parse_toml('# comment\nkey = "value"\n')
        assert result == {"key": "value"}

    def test_sections_skipped(self):
        """section 行跳过"""
        cm = ConfigManager()
        result = cm._parse_toml("[section]\nkey = \"value\"\n")
        assert result == {"key": "value"}

    def test_empty_lines_skipped(self):
        """空行跳过"""
        cm = ConfigManager()
        result = cm._parse_toml("\n\nkey = \"value\"\n\n")
        assert result == {"key": "value"}

    def test_strip_quotes(self):
        """去除引号"""
        cm = ConfigManager()
        result = cm._parse_toml('name = "hello"\n')
        assert result["name"] == "hello"

    def test_empty_content(self):
        """空内容"""
        cm = ConfigManager()
        result = cm._parse_toml("")
        assert result == {}


# ============================================================================
# validate_schema() 测试
# ============================================================================


class TestValidateSchema:
    """validate_schema() 测试"""

    def test_all_required_fields_present_passes(self):
        """所有必需字段存在时通过"""
        cm = ConfigManager()
        schema = {"name": {"type": str, "required": True}}
        data = {"name": "test"}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is True
        assert errors == []

    def test_missing_required_with_default_auto_fills(self):
        """缺少必需字段但有默认值时自动填充"""
        cm = ConfigManager()
        schema = {"name": {"type": str, "required": True, "default": "fallback"}}
        data = {}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is True
        assert data["name"] == "fallback"

    def test_missing_required_without_default_error(self):
        """缺少必需字段且无默认值时返回错误"""
        cm = ConfigManager()
        schema = {"name": {"type": str, "required": True}}
        data = {}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is False
        assert len(errors) == 1
        assert "缺少必需字段" in errors[0]

    def test_wrong_type_error(self):
        """类型错误时返回错误"""
        cm = ConfigManager()
        schema = {"count": {"type": int, "required": True}}
        data = {"count": "not_an_int"}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is False
        assert len(errors) == 1
        assert "字段类型错误" in errors[0]

    def test_empty_schema_passes(self):
        """空 schema 通过"""
        cm = ConfigManager()
        passed, errors = cm.validate_schema({}, {})
        assert passed is True
        assert errors == []

    def test_optional_fields_pass(self):
        """可选字段通过"""
        cm = ConfigManager()
        schema = {
            "name": {"type": str, "required": True},
            "age": {"type": int, "required": False},
        }
        data = {"name": "test"}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is True

    def test_multiple_errors_collected(self):
        """多个错误被收集"""
        cm = ConfigManager()
        schema = {
            "name": {"type": str, "required": True},
            "count": {"type": int, "required": True},
        }
        data = {}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is False
        assert len(errors) == 2

    def test_no_type_specified_passes(self):
        """没有指定 type 时通过"""
        cm = ConfigManager()
        schema = {"key": {"required": True}}
        data = {"key": "anything"}
        passed, errors = cm.validate_schema(data, schema)
        assert passed is True


# ============================================================================
# watch_file() 测试
# ============================================================================


class TestWatchFile:
    """watch_file() 测试"""

    def test_watch_file_returns_config_watcher(self, tmp_path):
        """返回 ConfigWatcher 实例"""
        f = tmp_path / "test.json"
        f.write_text("{}")
        cm = ConfigManager()
        watcher = cm.watch_file(str(f))
        assert isinstance(watcher, ConfigWatcher)
        assert watcher._file_path == str(f)

    def test_watch_file_default_interval(self, tmp_path):
        """默认 interval 为 2.0"""
        f = tmp_path / "test.json"
        f.write_text("{}")
        cm = ConfigManager()
        watcher = cm.watch_file(str(f))
        assert watcher._interval == 2.0


# ============================================================================
# ConfigWatcher 测试
# ============================================================================


class TestConfigWatcherInit:
    """ConfigWatcher __init__ 测试"""

    def test_init_with_file_path(self, tmp_path):
        """初始化时传入 file_path"""
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
        """初始化时传入自定义 interval"""
        f = tmp_path / "watch.json"
        f.write_text("{}")
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(f), interval=0.5)
        assert w._interval == 0.5

    def test_init_with_non_existent_file(self, tmp_path):
        """初始化时文件不存在，mtime 为 0"""
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(tmp_path / "nonexistent.json"))
        assert w._mtime == 0


class TestConfigWatcherOnChange:
    """on_change() 测试"""

    def test_on_change_registers_callback(self, tmp_path):
        """注册回调函数"""
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

    def test_on_change_multiple_callbacks(self, tmp_path):
        """注册多个回调"""
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
        """start() 创建线程"""
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
        """stop() 停止线程"""
        f = tmp_path / "w.json"
        f.write_text("{}")
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(f), interval=0.1)
        w.start()
        w.stop()
        assert w._running is False

    def test_stop_without_start_does_not_raise(self, tmp_path):
        """未 start 时 stop 不抛异常"""
        f = tmp_path / "w.json"
        f.write_text("{}")
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(f))
        w.stop()
        assert w._running is False


class TestConfigWatcherLoop:
    """_loop() 测试"""

    def test_loop_no_file_change(self, tmp_path):
        """_loop() 文件未变化时不触发重载"""
        f = tmp_path / "loop.json"
        f.write_text('{"key": "old"}')
        cm = ConfigManager()
        cm.load_from_file(str(f))

        w = ConfigWatcher(cm, str(f), interval=0.05)
        w._running = True

        callbacks_fired = []
        w.on_change(lambda data: callbacks_fired.append(data))

        def stop_loop(*args, **kwargs):
            w._running = False

        # 不修改 mtime 和文件内容，不触发重载
        with patch("time.sleep", side_effect=stop_loop):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=w._mtime):
                    w._loop()

        assert len(callbacks_fired) == 0

    def test_loop_file_change_triggers_reload(self, tmp_path):
        """_loop() 文件变化时触发重载"""
        f = tmp_path / "loop2.json"
        f.write_text('{"key": "old"}')
        cm = ConfigManager()
        cm.load_from_file(str(f))

        original_mtime = os.path.getmtime(str(f))

        callbacks_fired = []
        w = ConfigWatcher(cm, str(f), interval=0.05)
        w.on_change(lambda data: callbacks_fired.append(data))

        w._running = True

        # 修改文件
        f.write_text('{"key": "new"}')

        def stop_loop(*args, **kwargs):
            w._running = False

        with patch("time.sleep", side_effect=stop_loop):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=original_mtime + 1):
                    w._loop()

        assert len(callbacks_fired) == 1
        assert callbacks_fired[0]["old"] == {"key": "old"}
        assert callbacks_fired[0]["new"]["key"] == "new"
        assert callbacks_fired[0]["file"] == str(f)

    def test_loop_file_not_existing(self, tmp_path):
        """_loop() 文件不存在时跳过"""
        non_existent = tmp_path / "does_not_exist.json"
        cm = ConfigManager()
        w = ConfigWatcher(cm, str(non_existent), interval=0.05)
        w._running = True

        def stop_loop(*args, **kwargs):
            w._running = False

        with patch("time.sleep", side_effect=stop_loop):
            with patch("os.path.exists", return_value=False):
                w._loop()

        # 不崩溃即通过

    def test_loop_load_error_handled(self, tmp_path, capsys):
        """_loop() 加载错误被捕获"""
        f = tmp_path / "loop3.json"
        f.write_text('{"key": "old"}')
        cm = ConfigManager()
        cm.load_from_file(str(f))

        original_mtime = os.path.getmtime(str(f))

        w = ConfigWatcher(cm, str(f), interval=0.05)
        w._running = True

        # 修改文件为无效 JSON
        f.write_text("not valid json")

        def stop_loop(*args, **kwargs):
            w._running = False

        with patch("time.sleep", side_effect=stop_loop):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=original_mtime + 1):
                    w._loop()

        captured = capsys.readouterr()
        assert "热加载失败" in captured.out

    def test_loop_callback_triggers_on_change(self, tmp_path):
        """_loop() 变化时触发 on_change 回调"""
        f = tmp_path / "loop4.json"
        f.write_text('{"key": "old"}')
        cm = ConfigManager()
        cm.load_from_file(str(f))

        original_mtime = os.path.getmtime(str(f))

        callbacks_fired = []
        w = ConfigWatcher(cm, str(f), interval=0.05)
        w.on_change(lambda data: callbacks_fired.append(data))

        w._running = True

        f.write_text('{"key": "new"}')

        def stop_loop(*args, **kwargs):
            w._running = False

        with patch("time.sleep", side_effect=stop_loop):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=original_mtime + 1):
                    w._loop()

        assert len(callbacks_fired) == 1
        assert "old" in callbacks_fired[0]
        assert "new" in callbacks_fired[0]
        assert "file" in callbacks_fired[0]

    def test_loop_callback_exception_does_not_crash(self, tmp_path, capsys):
        """_loop() 回调异常不崩溃"""
        f = tmp_path / "loop5.json"
        f.write_text('{"key": "old"}')
        cm = ConfigManager()
        cm.load_from_file(str(f))

        original_mtime = os.path.getmtime(str(f))

        w = ConfigWatcher(cm, str(f), interval=0.05)

        def bad_callback(data):
            raise RuntimeError("callback error")

        w.on_change(bad_callback)

        w._running = True

        f.write_text('{"key": "new"}')

        def stop_loop(*args, **kwargs):
            w._running = False

        with patch("time.sleep", side_effect=stop_loop):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getmtime", return_value=original_mtime + 1):
                    w._loop()

        captured = capsys.readouterr()
        assert "回调错误" in captured.out


# ============================================================================
# 边界情况与综合测试
# ============================================================================


class TestEdgeCases:
    """边界情况与综合测试"""

    def test_multiple_set_default_calls(self):
        """多次 set_default() 调用"""
        cm = ConfigManager()
        cm.set_default("k", "v1")
        cm.set_default("k", "v2")
        # _defaults 字典被更新
        assert cm._defaults["k"] == "v2"
        # 但 configs 中的值不变（因为 key 已存在）
        assert cm.get("k") == "v1"

    def test_set_overrides_default(self):
        """set() 覆盖默认值"""
        cm = ConfigManager()
        cm.set_default("k", "default_val")
        cm.set("k", "override_val")
        assert cm.get("k") == "override_val"
        info = cm.get_info("k")
        assert info.source == ConfigSource.OVERRIDE

    def test_set_after_set_default(self):
        """set() 在 set_default() 之后的优先级"""
        cm = ConfigManager()
        cm.set_default("k", "default_val")
        cm.set("k", "new_val")
        assert cm.get("k") == "new_val"

    def test_load_from_env_after_set_default_env_overrides(self):
        """load_from_env() 在 set_default() 之后，环境变量覆盖"""
        with patch.dict(os.environ, {"TENGOD_KEY": "env_val"}):
            cm = ConfigManager()
            cm.set_default("key", "default_val")
            cm.load_from_env("key")
            assert cm.get("key") == "env_val"

    def test_load_from_file_with_mixed_content(self, tmp_path):
        """load_from_file() 混合内容"""
        f = tmp_path / "mixed.json"
        f.write_text('{"str_key": "hello", "int_key": 42, "bool_key": true, "null_key": null}')
        cm = ConfigManager()
        result = cm.load_from_file(str(f))
        assert result["str_key"] == "hello"
        assert result["int_key"] == 42
        assert result["bool_key"] is True
        assert result["null_key"] is None
        assert cm.get("str_key") == "hello"
        assert cm.get("int_key") == 42
        assert cm.get("bool_key") is True
        assert cm.get("null_key") is None

    def test_empty_config_manager_operations(self):
        """空 ConfigManager 的各种操作"""
        cm = ConfigManager()
        assert cm.list_all() == {}
        assert cm.list_with_source() == {}
        assert cm.get("anything") is None
        assert cm.has("anything") is False
        assert cm.get_info("anything") is None

    def test_special_characters_in_keys(self):
        """特殊字符 key"""
        cm = ConfigManager()
        cm.set("key-with-dashes", "v1")
        cm.set("key.with.dots", "v2")
        cm.set("key_with_underscores", "v3")
        cm.set("中文键", "v4")
        assert cm.get("key-with-dashes") == "v1"
        assert cm.get("key.with.dots") == "v2"
        assert cm.get("key_with_underscores") == "v3"
        assert cm.get("中文键") == "v4"

    def test_set_overwrites_existing(self):
        """set() 覆盖已有值"""
        cm = ConfigManager()
        cm.set("key", "old")
        cm.set("key", "new")
        assert cm.get("key") == "new"

    def test_custom_env_prefix_load_from_env(self):
        """自定义 env_prefix 下的 load_from_env"""
        with patch.dict(os.environ, {"MYAPP_HOST": "localhost"}):
            cm = ConfigManager(env_prefix="MYAPP_")
            result = cm.load_from_env("host")
            assert result is True
            assert cm.get("host") == "localhost"

    def test_watch_file_with_custom_interval(self, tmp_path):
        """watch_file() 自定义 interval"""
        f = tmp_path / "test.json"
        f.write_text("{}")
        cm = ConfigManager()
        watcher = cm.watch_file(str(f), interval=1.0)
        assert watcher._interval == 1.0

    def test_parse_simple_yaml_with_leading_trailing_spaces(self):
        """_parse_simple_yaml 处理前后空格"""
        cm = ConfigManager()
        f = io.StringIO("  key  :   value  \n")
        result = cm._parse_simple_yaml(f)
        assert result == {"key": "value"}

    def test_auto_cast_boolean_priority_over_numeric(self):
        """_auto_cast 布尔值优先于数字解析"""
        # "true" / "false" 应先被识别为布尔值
        assert ConfigManager._auto_cast("true") is True
        assert ConfigManager._auto_cast("false") is False

    def test_validate_schema_mixed_required_and_optional(self):
        """validate_schema 混合必需和可选字段"""
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