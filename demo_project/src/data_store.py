#!/usr/bin/env python3
"""data_store.py — 数据存储 (正财·知识固化)"""

from typing import Dict, List

_records: List[Dict] = []


def save_record(record: Dict) -> None:
    """保存记录"""
    _records.append(record)


def query_records(filters: Dict = None) -> List[Dict]:
    """查询记录"""
    if not filters:
        return list(_records)
    return [r for r in _records if all(r.get(k) == v for k, v in filters.items())]


def count_records() -> int:
    """统计记录数"""
    return len(_records)
