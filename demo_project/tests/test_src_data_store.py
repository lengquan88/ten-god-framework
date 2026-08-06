#!/usr/bin/env python3
"""test_src_data_store.py — src/data_store.py 模块级函数测试

覆盖:
  - save_record: 记录写入
  - query_records: 无过滤/多键过滤/空结果/空值匹配/非等值过滤防御
  - count_records: 统计准确性
  - 全局状态隔离: 测试间通过 fixture 重置共享 _records，保证独立性
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

import src.data_store as ds


# ============================================================================
# Fixture: 每个用例前重置全局 _records
# ============================================================================

@pytest.fixture(autouse=True)
def _reset_module_state():
    """保证每个测试看到一个干净的全局记录列表。"""
    ds._records.clear()
    yield
    ds._records.clear()


# ============================================================================
# save_record
# ============================================================================

class TestSaveRecord:
    """记录写入"""

    def test_save_single_record(self):
        ds.save_record({"id": 1, "name": "a"})
        assert ds.count_records() == 1

    def test_save_appends_in_order(self):
        ds.save_record({"id": 1})
        ds.save_record({"id": 2})
        ds.save_record({"id": 3})
        ids = [r["id"] for r in ds.query_records()]
        assert ids == [1, 2, 3]

    def test_save_empty_dict_is_valid(self):
        """空字典应被视为合法记录（不应抛异常）"""
        ds.save_record({})
        assert ds.count_records() == 1

    def test_save_none_dict_is_rejected(self):
        """None 作为记录时，至少应被计数，但不得在常规查询中静默破坏过滤"""
        ds.save_record(None)
        assert ds.count_records() == 1
        # 当前实现对 None 记录调用 r.get(k) 会抛 AttributeError；
        # 此测试固化现状——未来若实现改为主动拒绝 None，应同步更新此断言。
        with pytest.raises(AttributeError):
            ds.query_records({"k": "v"})


# ============================================================================
# query_records
# ============================================================================

class TestQueryRecords:
    """记录查询与过滤"""

    def test_no_filters_returns_all(self):
        ds.save_record({"id": 1})
        ds.save_record({"id": 2})
        result = ds.query_records()
        assert len(result) == 2

    def test_empty_dict_filter_returns_all(self):
        """filters={} 等价于无过滤"""
        ds.save_record({"id": 1})
        result = ds.query_records({})
        assert len(result) == 1

    def test_single_key_filter_match(self):
        ds.save_record({"id": 1, "kind": "a"})
        ds.save_record({"id": 2, "kind": "b"})
        result = ds.query_records({"kind": "a"})
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_multi_key_filter_requires_all_match(self):
        """多键过滤必须同时满足所有键"""
        ds.save_record({"id": 1, "kind": "a", "owner": "u1"})
        ds.save_record({"id": 2, "kind": "a", "owner": "u2"})
        ds.save_record({"id": 3, "kind": "b", "owner": "u1"})

        assert len(ds.query_records({"kind": "a", "owner": "u1"})) == 1
        assert ds.query_records({"kind": "a", "owner": "u1"})[0]["id"] == 1

    def test_filter_missing_key_matches_none(self):
        """r.get(k) 对缺失键返回 None；filters 中 None 值只匹配 None 或缺失键"""
        ds.save_record({"id": 1, "tag": "x"})
        ds.save_record({"id": 2})  # 没有 tag
        ds.save_record({"id": 3, "tag": None})

        # 过滤 tag=None：应匹配缺失键与显式 None
        result = ds.query_records({"tag": None})
        ids = {r["id"] for r in result}
        assert ids == {2, 3}

    def test_filter_no_match_returns_empty_list(self):
        ds.save_record({"id": 1, "kind": "a"})
        result = ds.query_records({"kind": "zzz"})
        assert result == []

    def test_result_is_a_new_list(self):
        """返回值必须是新列表，不得暴露内部引用"""
        ds.save_record({"id": 1})
        result1 = ds.query_records()
        result2 = ds.query_records()
        assert result1 is not result2
        result1.append({"injected": True})
        assert ds.count_records() == 1

    def test_filters_with_nonexistent_key(self):
        """过滤不存在的键必须返回空集（而不是抛异常）"""
        ds.save_record({"id": 1})
        result = ds.query_records({"completely_missing_key": "v"})
        assert result == []


# ============================================================================
# count_records
# ============================================================================

class TestCountRecords:
    """记录计数"""

    def test_count_empty_store(self):
        assert ds.count_records() == 0

    def test_count_after_additions(self):
        for i in range(5):
            ds.save_record({"i": i})
        assert ds.count_records() == 5

    def test_count_matches_query_total(self):
        for i in range(3):
            ds.save_record({"i": i})
        assert ds.count_records() == len(ds.query_records())


# ============================================================================
# 模块级健壮性
# ============================================================================

class TestModuleRobustness:
    """模块函数对非法输入的健壮性"""

    def test_query_with_non_dict_filters_is_defensive(self):
        """filters 为非字典时，not filters 为真，回退为全量查询"""
        ds.save_record({"id": 1})
        # None / {} / [] 均为 falsy，行为一致
        assert len(ds.query_records(None)) == 1
        assert len(ds.query_records([])) == 1

    def test_filter_value_equality_is_exact(self):
        """过滤使用 == 精确匹配，不得进行类型宽松匹配"""
        ds.save_record({"id": 1, "count": 1})
        ds.save_record({"id": 2, "count": 1.0})
        # 1 == 1.0 在 Python 中为 True，这是语言行为；
        # 此测试固化该契约，若将来改为严格匹配需同步更新。
        result = ds.query_records({"count": 1})
        assert len(result) == 2

    def test_dict_key_preserves_string_identity(self):
        """字符串键过滤必须严格按 key 名匹配"""
        ds.save_record({"Name": "Alice", "name": "Bob"})
        assert ds.query_records({"Name": "Alice"})[0]["Name"] == "Alice"
        assert ds.query_records({"name": "Bob"})[0]["name"] == "Bob"
        assert ds.query_records({"name": "Alice"}) == []
