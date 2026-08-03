"""
test_src_data_store.py — 数据存储全局状态隔离测试
=================================================
覆盖 src/data_store.py 的内存数据存储逻辑。

高风险路径：
  1. 全局可变状态 _records 的隔离——每个测试必须独立
  2. save_record — 追加写入
  3. query_records — 无过滤返回全量、有过滤精确匹配
  4. count_records — 计数准确性
  5. 多字段过滤、不匹配过滤返回空列表
"""

from __future__ import annotations

import os
import sys

import pytest

# src/ 目录无 __init__.py，需手动加入 sys.path
_src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
_src_dir = os.path.abspath(_src_dir)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import data_store


@pytest.fixture(autouse=True)
def reset_records():
    """每个测试前清空全局 _records，确保测试隔离"""
    data_store._records.clear()
    yield
    data_store._records.clear()


# ============================================================================
# 1. save_record 写入测试
# ============================================================================

class TestSaveRecord:
    """save_record() 记录写入"""

    def test_save_single_record(self):
        """保存单条记录后计数应为 1"""
        data_store.save_record({"user": "alice", "action": "login"})
        assert data_store.count_records() == 1

    def test_save_multiple_records(self):
        """保存多条记录后计数应正确"""
        for i in range(5):
            data_store.save_record({"id": i, "user": f"user{i}"})
        assert data_store.count_records() == 5

    def test_save_preserves_record_content(self):
        """保存的记录内容应完整保留"""
        record = {"user": "bob", "action": "write", "status": "ok"}
        data_store.save_record(record)
        results = data_store.query_records()
        assert results[0] == record

    def test_save_empty_dict(self):
        """空字典也应能保存"""
        data_store.save_record({})
        assert data_store.count_records() == 1


# ============================================================================
# 2. query_records 查询测试
# ============================================================================

class TestQueryRecords:
    """query_records() 记录查询"""

    def test_query_no_filters_returns_all(self):
        """无过滤参数时返回全部记录"""
        data_store.save_record({"a": 1})
        data_store.save_record({"b": 2})
        results = data_store.query_records()
        assert len(results) == 2

    def test_query_none_filters_returns_all(self):
        """filters=None 时返回全部记录"""
        data_store.save_record({"a": 1})
        results = data_store.query_records(None)
        assert len(results) == 1

    def test_query_single_field_filter(self):
        """单字段过滤精确匹配"""
        data_store.save_record({"user": "alice", "status": "ok"})
        data_store.save_record({"user": "bob", "status": "ok"})
        data_store.save_record({"user": "alice", "status": "fail"})
        results = data_store.query_records({"user": "alice"})
        assert len(results) == 2
        assert all(r["user"] == "alice" for r in results)

    def test_query_multi_field_filter(self):
        """多字段过滤——所有条件同时满足"""
        data_store.save_record({"user": "alice", "status": "ok", "action": "read"})
        data_store.save_record({"user": "alice", "status": "fail", "action": "read"})
        data_store.save_record({"user": "alice", "status": "ok", "action": "write"})
        results = data_store.query_records({"user": "alice", "status": "ok"})
        assert len(results) == 2
        assert all(r["user"] == "alice" and r["status"] == "ok" for r in results)

    def test_query_no_match_returns_empty(self):
        """过滤无匹配时返回空列表"""
        data_store.save_record({"user": "alice"})
        results = data_store.query_records({"user": "nobody"})
        assert results == []

    def test_query_empty_store_returns_empty(self):
        """空存储查询返回空列表"""
        assert data_store.query_records() == []
        assert data_store.query_records({"any": "thing"}) == []

    def test_query_returns_copy_not_reference(self):
        """query_records 返回的列表应是副本，不影响内部状态"""
        data_store.save_record({"a": 1})
        results = data_store.query_records()
        results.clear()
        # 内部记录不受影响
        assert data_store.count_records() == 1

    def test_query_filter_on_missing_field(self):
        """过滤字段在记录中不存在时该记录不匹配"""
        data_store.save_record({"user": "alice"})
        data_store.save_record({"user": "bob", "role": "admin"})
        results = data_store.query_records({"role": "admin"})
        assert len(results) == 1
        assert results[0]["user"] == "bob"


# ============================================================================
# 3. count_records 计数测试
# ============================================================================

class TestCountRecords:
    """count_records() 记录计数"""

    def test_empty_store_count_zero(self):
        """空存储计数为 0"""
        assert data_store.count_records() == 0

    def test_count_after_saves(self):
        """保存后计数正确"""
        data_store.save_record({"a": 1})
        data_store.save_record({"b": 2})
        assert data_store.count_records() == 2

    def test_count_independent_of_queries(self):
        """查询不影响计数"""
        data_store.save_record({"a": 1})
        data_store.query_records()
        data_store.query_records({"a": 1})
        assert data_store.count_records() == 1
