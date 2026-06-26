"""测试 偏印_桥接通变/adapter.py — 协议适配器模块"""

import json
import pytest
from abc import ABC

from tengod.偏印_桥接通变.adapter import (
    ProtocolConverter,
    Adapter,
    DictToJsonConverter,
    CamelToSnakeConverter,
    BridgeRegistry,
)


# ═══════════════════════════════════════════════════════════════
# 1. ProtocolConverter 抽象基类
# ═══════════════════════════════════════════════════════════════

class TestProtocolConverter:
    """抽象基类不可直接实例化"""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            ProtocolConverter()  # type: ignore[abstract]

    def test_is_abstract_base_class(self):
        assert issubclass(ProtocolConverter, ABC)

    def test_subclass_must_implement_abstract_methods(self):
        """未实现所有抽象方法的子类不可实例化"""

        class Incomplete(ProtocolConverter):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_concrete_subclass_instantiable(self):
        class Complete(ProtocolConverter):
            def from_source(self, data):
                return data

            def to_source(self, data):
                return data

        obj = Complete()
        assert isinstance(obj, ProtocolConverter)


# ═══════════════════════════════════════════════════════════════
# 2. Adapter
# ═══════════════════════════════════════════════════════════════

class _FakeConverter(ProtocolConverter):
    """测试用转换器"""

    def __init__(self):
        self.from_calls = []
        self.to_calls = []

    def from_source(self, data):
        self.from_calls.append(data)
        return f"from_{data}"

    def to_source(self, data):
        self.to_calls.append(data)
        return f"to_{data}"


class _FailingConverter(ProtocolConverter):
    """总是抛出异常的转换器"""

    def from_source(self, data):
        raise RuntimeError("from_source 失败")

    def to_source(self, data):
        raise RuntimeError("to_source 失败")


class TestAdapter:
    """Adapter 核心测试"""

    # ── 构造与属性 ──

    def test_init_with_name_and_converter(self):
        c = _FakeConverter()
        a = Adapter("test_adapter", c)
        assert a.name == "test_adapter"
        assert a._converter is c

    def test_name_property(self):
        a = Adapter("my_adapter", _FakeConverter())
        assert a.name == "my_adapter"
        assert isinstance(a.name, str)

    # ── convert direction="from" ──

    def test_convert_from_direction_calls_from_source(self):
        c = _FakeConverter()
        a = Adapter("a", c)
        result = a.convert({"key": "value"}, direction="from")
        assert result == "from_{'key': 'value'}"
        assert c.from_calls == [{"key": "value"}]
        assert c.to_calls == []

    def test_convert_from_is_default_direction(self):
        c = _FakeConverter()
        a = Adapter("a", c)
        result = a.convert("hello")
        assert result == "from_hello"
        assert c.from_calls == ["hello"]

    # ── convert direction="to" ──

    def test_convert_to_direction_calls_to_source(self):
        c = _FakeConverter()
        a = Adapter("a", c)
        result = a.convert("data", direction="to")
        assert result == "to_data"
        assert c.to_calls == ["data"]
        assert c.from_calls == []

    # ── invalid direction ──

    def test_convert_invalid_direction_raises_valueerror(self):
        a = Adapter("a", _FakeConverter())
        with pytest.raises(ValueError, match="Unknown direction"):
            a.convert("data", direction="invalid")

    # ── converter 抛出异常 ──

    def test_convert_when_converter_raises_error_count_incremented(self):
        a = Adapter("a", _FailingConverter())
        with pytest.raises(RuntimeError, match="from_source 失败"):
            a.convert("data", direction="from")
        stats = a.stats()
        assert stats["errors"] == 1
        assert stats["calls"] == 1

    def test_convert_when_converter_raises_exception_re_raised(self):
        a = Adapter("a", _FailingConverter())
        with pytest.raises(RuntimeError, match="to_source 失败"):
            a.convert("data", direction="to")
        stats = a.stats()
        assert stats["errors"] == 1

    # ── stats ──

    def test_stats_after_successful_operations(self):
        a = Adapter("a", _FakeConverter())
        a.convert("x", direction="from")
        a.convert("y", direction="to")
        a.convert("z", direction="from")
        stats = a.stats()
        assert stats["calls"] == 3
        assert stats["errors"] == 0

    def test_stats_after_mixed_operations(self):
        a = Adapter("a", _FakeConverter())
        a.convert("ok1", direction="from")
        a.convert("ok2", direction="to")

        # 临时替换为失败的 converter 来模拟错误
        failing = _FailingConverter()
        a._converter = failing
        try:
            a.convert("fail1", direction="from")
        except RuntimeError:
            pass

        stats = a.stats()
        assert stats["calls"] == 3
        assert stats["errors"] == 1

    def test_stats_initial_state(self):
        a = Adapter("a", _FakeConverter())
        stats = a.stats()
        assert stats == {"calls": 0, "errors": 0}


# ═══════════════════════════════════════════════════════════════
# 3. DictToJsonConverter
# ═══════════════════════════════════════════════════════════════

class TestDictToJsonConverter:
    """DictToJsonConverter 测试"""

    # ── from_source ──

    def test_from_source_valid_json_string(self):
        c = DictToJsonConverter()
        result = c.from_source('{"name": "test", "value": 42}')
        assert result == {"name": "test", "value": 42}

    def test_from_source_non_string_input_returns_dict(self):
        c = DictToJsonConverter()
        result = c.from_source({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}

    def test_from_source_list_of_tuples(self):
        c = DictToJsonConverter()
        result = c.from_source([("key", "val")])
        assert result == {"key": "val"}

    def test_from_source_invalid_json_string_raises(self):
        c = DictToJsonConverter()
        with pytest.raises(ValueError):
            c.from_source("not valid json")

    # ── to_source ──

    def test_to_source_dict_to_json_string(self):
        c = DictToJsonConverter()
        result = c.to_source({"name": "test"})
        parsed = json.loads(result)
        assert parsed == {"name": "test"}

    def test_to_source_empty_dict(self):
        c = DictToJsonConverter()
        result = c.to_source({})
        parsed = json.loads(result)
        assert parsed == {}

    def test_to_source_with_nested_dict(self):
        c = DictToJsonConverter()
        data = {"outer": {"inner": {"deep": True}}}
        result = c.to_source(data)
        parsed = json.loads(result)
        assert parsed == data

    def test_to_source_with_unicode_chinese(self):
        c = DictToJsonConverter()
        data = {"名称": "中华文明", "描述": "永生体"}
        result = c.to_source(data)
        assert "名称" in result
        assert "中华文明" in result
        parsed = json.loads(result)
        assert parsed == data

    def test_to_source_with_lists(self):
        c = DictToJsonConverter()
        data = {"items": [1, 2, 3], "nested": [{"a": 1}, {"b": 2}]}
        result = c.to_source(data)
        parsed = json.loads(result)
        assert parsed == data

    # ── 类继承 ──

    def test_is_protocol_converter_subclass(self):
        assert isinstance(DictToJsonConverter(), ProtocolConverter)


# ═══════════════════════════════════════════════════════════════
# 4. CamelToSnakeConverter
# ═══════════════════════════════════════════════════════════════

class TestCamelToSnakeConverter:
    """CamelToSnakeConverter 测试"""

    # ── from_source (camelCase → snake_case) ──

    def test_from_source_simple_camel_case(self):
        c = CamelToSnakeConverter()
        result = c.from_source({"camelCase": 1})
        assert result == {"camel_case": 1}

    def test_from_source_multiple_camel_case_keys(self):
        c = CamelToSnakeConverter()
        result = c.from_source({"helloWorld": 1, "fooBar": 2})
        assert result == {"hello_world": 1, "foo_bar": 2}

    def test_from_source_with_acronyms(self):
        c = CamelToSnakeConverter()
        result = c.from_source({"XMLParser": 1})
        assert result == {"xml_parser": 1}

    def test_from_source_already_snake_case(self):
        c = CamelToSnakeConverter()
        result = c.from_source({"already_snake": 1})
        assert result == {"already_snake": 1}

    def test_from_source_single_word_keys(self):
        c = CamelToSnakeConverter()
        result = c.from_source({"simple": 1, "hello": 2})
        assert result == {"simple": 1, "hello": 2}

    def test_from_source_empty_dict(self):
        c = CamelToSnakeConverter()
        result = c.from_source({})
        assert result == {}

    def test_from_source_mixed_keys(self):
        c = CamelToSnakeConverter()
        result = c.from_source({"simple": 1, "camelCase": 2, "already_snake": 3})
        assert result == {"simple": 1, "camel_case": 2, "already_snake": 3}

    # ── to_source (snake_case → camelCase) ──

    def test_to_source_snake_case(self):
        c = CamelToSnakeConverter()
        result = c.to_source({"snake_case": 1})
        assert result == {"snakeCase": 1}

    def test_to_source_single_word(self):
        c = CamelToSnakeConverter()
        result = c.to_source({"simple": 1})
        assert result == {"simple": 1}

    def test_to_source_multiple_underscores(self):
        c = CamelToSnakeConverter()
        result = c.to_source({"hello_world_test": 1})
        assert result == {"helloWorldTest": 1}

    def test_to_source_empty_dict(self):
        c = CamelToSnakeConverter()
        result = c.to_source({})
        assert result == {}

    # ── _to_snake 静态方法 ──

    def test_to_snake_simple(self):
        assert CamelToSnakeConverter._to_snake("camelCase") == "camel_case"

    def test_to_snake_multiple_caps(self):
        assert CamelToSnakeConverter._to_snake("helloWorldTest") == "hello_world_test"

    def test_to_snake_acronym(self):
        assert CamelToSnakeConverter._to_snake("XMLParser") == "xml_parser"

    def test_to_snake_already_snake(self):
        assert CamelToSnakeConverter._to_snake("already_snake") == "already_snake"

    def test_to_snake_single_word(self):
        assert CamelToSnakeConverter._to_snake("simple") == "simple"

    def test_to_snake_empty_string(self):
        assert CamelToSnakeConverter._to_snake("") == ""

    def test_to_snake_all_uppercase(self):
        assert CamelToSnakeConverter._to_snake("ABC") == "abc"

    def test_to_snake_numbers_in_key(self):
        assert CamelToSnakeConverter._to_snake("num42Key") == "num42_key"

    def test_to_snake_leading_uppercase(self):
        assert CamelToSnakeConverter._to_snake("HelloWorld") == "hello_world"

    # ── _to_camel 静态方法 ──

    def test_to_camel_simple(self):
        assert CamelToSnakeConverter._to_camel("snake_case") == "snakeCase"

    def test_to_camel_multiple_underscores(self):
        assert CamelToSnakeConverter._to_camel("hello_world_test") == "helloWorldTest"

    def test_to_camel_single_word(self):
        assert CamelToSnakeConverter._to_camel("simple") == "simple"

    def test_to_camel_empty_string(self):
        assert CamelToSnakeConverter._to_camel("") == ""

    def test_to_camel_triple_underscore(self):
        assert CamelToSnakeConverter._to_camel("a_b_c") == "aBC"

    def test_to_camel_xml_parser(self):
        assert CamelToSnakeConverter._to_camel("xml_parser") == "xmlParser"

    def test_to_camel_already_camel(self):
        # "alreadyCamel" has no underscore, so stays same
        assert CamelToSnakeConverter._to_camel("alreadyCamel") == "alreadyCamel"

    # ── 类继承 ──

    def test_is_protocol_converter_subclass(self):
        assert isinstance(CamelToSnakeConverter(), ProtocolConverter)


# ═══════════════════════════════════════════════════════════════
# 5. BridgeRegistry
# ═══════════════════════════════════════════════════════════════

class TestBridgeRegistry:
    """BridgeRegistry 测试"""

    # ── 适配器注册与获取 ──

    def test_register_and_get_adapter(self):
        reg = BridgeRegistry()
        adapter = Adapter("my_adapter", _FakeConverter())
        reg.register_adapter(adapter)
        assert reg.get_adapter("my_adapter") is adapter

    def test_get_adapter_non_existing_returns_none(self):
        reg = BridgeRegistry()
        assert reg.get_adapter("nonexistent") is None

    # ── 转换器注册与获取 ──

    def test_register_and_get_converter(self):
        reg = BridgeRegistry()
        converter = DictToJsonConverter()
        reg.register_converter("json_converter", converter)
        assert reg.get_converter("json_converter") is converter

    def test_get_converter_non_existing_returns_none(self):
        reg = BridgeRegistry()
        assert reg.get_converter("nonexistent") is None

    # ── list_adapters ──

    def test_list_adapters_after_registration(self):
        reg = BridgeRegistry()
        reg.register_adapter(Adapter("a1", _FakeConverter()))
        reg.register_adapter(Adapter("a2", _FakeConverter()))
        assert sorted(reg.list_adapters()) == ["a1", "a2"]

    def test_list_adapters_empty(self):
        reg = BridgeRegistry()
        assert reg.list_adapters() == []

    # ── list_converters ──

    def test_list_converters_after_registration(self):
        reg = BridgeRegistry()
        reg.register_converter("c1", DictToJsonConverter())
        reg.register_converter("c2", CamelToSnakeConverter())
        assert sorted(reg.list_converters()) == ["c1", "c2"]

    def test_list_converters_empty(self):
        reg = BridgeRegistry()
        assert reg.list_converters() == []


# ═══════════════════════════════════════════════════════════════
# 6. 边界与集成测试
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """边界情况与集成测试"""

    def test_adapter_with_custom_protocol_converter(self):
        """自定义 ProtocolConverter 子类与 Adapter 集成"""

        class CustomConverter(ProtocolConverter):
            def from_source(self, data):
                return data.upper() if isinstance(data, str) else data

            def to_source(self, data):
                return data.lower() if isinstance(data, str) else data

        adapter = Adapter("custom", CustomConverter())
        assert adapter.convert("Hello", direction="from") == "HELLO"
        assert adapter.convert("WORLD", direction="to") == "world"
        assert adapter.stats() == {"calls": 2, "errors": 0}

    def test_multiple_adapters_in_registry(self):
        reg = BridgeRegistry()
        reg.register_adapter(Adapter("json", DictToJsonConverter()))
        reg.register_adapter(Adapter("camel", CamelToSnakeConverter()))

        json_adapter = reg.get_adapter("json")
        result = json_adapter.convert({"a": 1}, direction="to")
        assert isinstance(result, str)
        assert "a" in result

        camel_adapter = reg.get_adapter("camel")
        result = camel_adapter.convert({"helloWorld": 1}, direction="from")
        assert result == {"hello_world": 1}

    def test_dict_to_json_with_special_values(self):
        c = DictToJsonConverter()
        data = {"bool": True, "none": None, "int": 42, "float": 3.14}
        result = c.to_source(data)
        parsed = json.loads(result)
        assert parsed == data

    def test_camel_to_snake_with_numbers_in_keys(self):
        c = CamelToSnakeConverter()
        assert c._to_snake("version2Api") == "version2_api"
        assert c._to_snake("apiV2") == "api_v2"

    def test_camel_to_snake_roundtrip(self):
        """camelCase → snake_case → camelCase 往返"""
        original = {"helloWorldTest": 42, "simple": 1, "xmlParser": 2}
        c = CamelToSnakeConverter()
        snake = c.from_source(original)
        camel = c.to_source(snake)
        assert camel == original

    def test_adapter_convert_chain(self):
        """通过 Adapter 链式转换"""
        a = Adapter("camel", CamelToSnakeConverter())
        # from: camelCase → snake_case
        result = a.convert({"helloWorld": 1}, direction="from")
        assert result == {"hello_world": 1}
        # to: snake_case → camelCase
        result2 = a.convert({"hello_world": 1}, direction="to")
        assert result2 == {"helloWorld": 1}

    def test_adapter_name_immutable_via_property(self):
        """name 属性不可直接设置"""
        a = Adapter("original", _FakeConverter())
        with pytest.raises(AttributeError):
            a.name = "new_name"

    def test_camel_to_snake_preserves_values(self):
        """转换时值保持不变"""
        c = CamelToSnakeConverter()
        data = {"myKey": [1, 2, 3], "otherKey": {"nested": True}}
        result = c.from_source(data)
        assert result["my_key"] == [1, 2, 3]
        assert result["other_key"] == {"nested": True}

    def test_invalid_direction_increments_call_count(self):
        """无效方向也应增加 call_count"""
        a = Adapter("a", _FakeConverter())
        try:
            a.convert("data", direction="invalid")
        except ValueError:
            pass
        stats = a.stats()
        assert stats["calls"] == 1
        assert stats["errors"] == 1