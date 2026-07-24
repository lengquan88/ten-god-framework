#!/usr/bin/env python3
"""
data_store.py 测试套件
========================
覆盖: User, BaziRecord, ReportCache, LegacyCase, DataStore CRUD
"""

import os
import tempfile

import pytest

from tengod.data_store import DataStore, User, BaziRecord


class TestDataStore:

    @pytest.fixture
    def datastore(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        store = DataStore(db_path=db_path)
        yield store
        os.unlink(db_path)

    # ── 用户管理 ──────────────────────────────────────────────────────────

    def test_get_or_create_user(self, datastore):
        user = datastore.get_or_create_user("testuser")
        assert user.username == "testuser"
        assert user.display_name == "testuser"

        user2 = datastore.get_or_create_user("testuser", display_name="Test User")
        assert user2.id == user.id
        assert user2.display_name == "testuser"

        user3 = datastore.get_or_create_user("newuser", display_name="New User")
        assert user3.username == "newuser"
        assert user3.display_name == "New User"

    def test_get_user(self, datastore):
        user = datastore.get_or_create_user("gettest")
        fetched = datastore.get_user(user.id)
        assert fetched is not None
        assert fetched.username == "gettest"

        not_found = datastore.get_user(99999)
        assert not_found is None

    def test_list_users(self, datastore):
        datastore.get_or_create_user("user1")
        datastore.get_or_create_user("user2")
        users = datastore.list_users(limit=10)
        assert len(users) >= 2

    # ── 八字记录 CRUD ────────────────────────────────────────────────────

    def test_save_bazi_record(self, datastore):
        record_id = datastore.save_bazi_record(
            year=1990, month=6, day=15, hour=10, minute=30,
            gender="male", longitude=116.4, latitude=39.9,
            label="测试记录",
        )
        assert record_id > 0

    def test_get_bazi_record(self, datastore):
        record_id = datastore.save_bazi_record(
            year=1990, month=6, day=15, hour=10, minute=30,
            gender="female",
        )
        record = datastore.get_bazi_record(record_id)
        assert record is not None
        assert record.year == 1990
        assert record.month == 6
        assert record.day == 15
        assert record.gender == "female"

        not_found = datastore.get_bazi_record(99999)
        assert not_found is None

    def test_list_bazi_records(self, datastore):
        datastore.save_bazi_record(1990, 6, 15, 10, label="record1")
        datastore.save_bazi_record(1991, 7, 20, 12, label="record2")
        records = datastore.list_bazi_records(limit=5)
        assert len(records) >= 2

    def test_list_bazi_records_pagination(self, datastore):
        for i in range(10):
            datastore.save_bazi_record(1990 + i, 6, 15, 10)
        records = datastore.list_bazi_records(limit=3, offset=2)
        assert len(records) == 3

    def test_search_bazi_records(self, datastore):
        datastore.save_bazi_record(1990, 6, 15, 10, gender="male", day_master="甲")
        datastore.save_bazi_record(1990, 6, 20, 12, gender="female", day_master="乙")
        datastore.save_bazi_record(1991, 6, 15, 10, gender="male", day_master="甲")

        results = datastore.search_bazi_records(year=1990)
        assert len(results) == 2

        results = datastore.search_bazi_records(gender="male")
        assert len(results) >= 2

        results = datastore.search_bazi_records(day_master="甲")
        assert len(results) >= 2

    def test_update_bazi_record(self, datastore):
        record_id = datastore.save_bazi_record(
            year=1990, month=6, day=15, hour=10, label="original"
        )
        success = datastore.update_bazi_record(record_id, label="updated")
        assert success is True

        record = datastore.get_bazi_record(record_id)
        assert record.label == "updated"

        not_found = datastore.update_bazi_record(99999, label="nope")
        assert not_found is False

    def test_delete_bazi_record(self, datastore):
        record_id = datastore.save_bazi_record(1990, 6, 15, 10)
        success = datastore.delete_bazi_record(record_id)
        assert success is True

        record = datastore.get_bazi_record(record_id)
        assert record is None

        not_found = datastore.delete_bazi_record(99999)
        assert not_found is False

    def test_count_bazi_records(self, datastore):
        initial = datastore.count_bazi_records()
        datastore.save_bazi_record(1990, 6, 15, 10)
        datastore.save_bazi_record(1991, 7, 20, 12)
        assert datastore.count_bazi_records() == initial + 2

    def test_save_bazi_record_with_json_data(self, datastore):
        record_id = datastore.save_bazi_record(
            year=1990, month=6, day=15, hour=10,
            day_master="甲",
            pillars={"year": "甲子", "month": "庚午"},
            analysis={"wuxing": {"木": 2, "火": 1}},
            tags="tag1,tag2",
            notes="测试备注",
        )
        record = datastore.get_bazi_record(record_id)
        assert record is not None
        assert record.day_master == "甲"
        assert record.tags == "tag1,tag2"
        assert record.notes == "测试备注"

        record_dict = record.to_dict()
        assert record_dict["pillars"] == {"year": "甲子", "month": "庚午"}
        assert record_dict["analysis"] == {"wuxing": {"木": 2, "火": 1}}

    # ── 报告缓存 ──────────────────────────────────────────────────────────

    def test_cache_report(self, datastore):
        record_id = datastore.save_bazi_record(1990, 6, 15, 10)
        cache_id = datastore.cache_report(record_id, "text", "报告内容")
        assert cache_id > 0

    def test_cache_report_deduplication(self, datastore):
        record_id = datastore.save_bazi_record(1990, 6, 15, 10)
        cache_id1 = datastore.cache_report(record_id, "text", "相同内容")
        cache_id2 = datastore.cache_report(record_id, "text", "相同内容")
        assert cache_id1 == cache_id2

    def test_get_cached_report(self, datastore):
        record_id = datastore.save_bazi_record(1990, 6, 15, 10)
        datastore.cache_report(record_id, "text", "我的报告")
        content = datastore.get_cached_report(record_id, "text")
        assert content == "我的报告"

        not_found = datastore.get_cached_report(99999, "text")
        assert not_found is None

    def test_clear_report_cache(self, datastore):
        record_id = datastore.save_bazi_record(1990, 6, 15, 10)
        datastore.cache_report(record_id, "text", "报告1")
        datastore.cache_report(record_id, "json", "报告2")

        count = datastore.clear_report_cache(record_id)
        assert count >= 2

        content = datastore.get_cached_report(record_id, "text")
        assert content is None

    # ── BaziRecord.to_dict ────────────────────────────────────────────────

    def test_bazi_record_to_dict(self, datastore):
        record_id = datastore.save_bazi_record(
            year=1990, month=6, day=15, hour=10,
            label="测试",
            pillars={"year": "甲子"},
            analysis={"test": "data"},
        )
        record = datastore.get_bazi_record(record_id)
        record_dict = record.to_dict()
        assert isinstance(record_dict, dict)
        assert record_dict["id"] == record_id
        assert record_dict["year"] == 1990
        assert record_dict["label"] == "测试"
        assert record_dict["pillars"] == {"year": "甲子"}
        assert record_dict["analysis"] == {"test": "data"}
