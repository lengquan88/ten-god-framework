#!/usr/bin/env python3
"""
test_phase22.py —— 阶段 22 数据库升级全面测试

覆盖：
  1. DataStore 核心 CRUD（User / BaziRecord / ReportCache / Case）
  2. PostgreSQL 连接池配置
  3. ChineseEmbedder + 内存索引
  4. CacheManager（内存缓存 / 装饰器 / 限流 / Session）
  5. MigrationManager（SQLite → SQLite 自测迁移）
  6. stats() 统计
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import uuid
from typing import Any, Dict, List, Optional

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tengod.data_store import DataStore
from tengod.vector_store_pg import ChineseEmbedder
from tengod.cache_manager import MemoryCacheManager, get_cache_manager
from tengod.db_migration import MigrationManager


def _temp_db(suffix: str = ".db") -> str:
    return os.path.join(tempfile.gettempdir(), f"tengod_p22_{uuid.uuid4().hex}{suffix}")


def _make_store(db_path: Optional[str] = None) -> DataStore:
    if db_path is None:
        db_path = _temp_db()
    return DataStore(db_path=db_path)


# ----------------------------------------------------------------------------
# TestDataStoreCore —— 基本 CRUD 与新 Case 模型
# ----------------------------------------------------------------------------

class TestDataStoreCore:
    """DataStore 核心 CRUD 测试。"""

    def setup_method(self, method):
        self.db_path = _temp_db()
        self.db = DataStore(db_path=self.db_path)

    def teardown_method(self, method):
        try:
            self.db.close()
        except Exception:
            pass
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_save_and_get_case(self):
        cid = self.db.save_case(
            title="身弱伤官格 · 事业命例",
            summary="命主日主辛金偏弱，月令伤官透出",
            analysis_text="用神取印比帮身",
            category="事业",
            is_public=True,
            is_featured=True,
            day_master="辛",
            tags="伤官,用印",
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            geju={"name": "伤官格"},
            yongshen={"main": "印比"},
        )
        assert cid > 0
        case = self.db.get_case(cid)
        assert case is not None
        assert case.id == cid
        assert case.title == "身弱伤官格 · 事业命例"
        assert case.category == "事业"
        assert bool(case.is_public) is True
        assert bool(case.is_featured) is True
        assert case.day_master == "辛"
        assert case.tags == "伤官,用印"
        d = case.to_dict()
        assert d["pillars"]["year"] == "庚午"
        assert "geju" in d
        assert case.fts_vector and "伤官" in case.fts_vector

    def test_list_cases(self):
        for i in range(3):
            cat = "情感" if i % 2 == 0 else "事业"
            feat = (i == 0)
            self.db.save_case(title=f"命例 {i}", category=cat, is_featured=feat)
        assert len(self.db.list_cases()) == 3
        assert len(self.db.list_cases(category="情感")) == 2
        assert len(self.db.list_cases(category="事业")) == 1
        assert len(self.db.list_cases(is_featured=True)) == 1
        assert len(self.db.list_cases(is_public=False)) == 0

    def test_update_case(self):
        cid = self.db.save_case(title="原始标题", category="事业", summary="初始摘要")
        ok = self.db.update_case(cid, title="更新后的标题", summary="新摘要")
        assert ok is True
        case = self.db.get_case(cid)
        assert case.title == "更新后的标题"
        assert case.summary == "新摘要"
        assert "更新" in case.fts_vector
        assert self.db.update_case(999999, title="no") is False

    def test_delete_case(self):
        cid = self.db.save_case(title="将被删除")
        assert self.db.get_case(cid) is not None
        assert self.db.delete_case(cid) is True
        assert self.db.get_case(cid) is None
        assert self.db.delete_case(cid) is False

    def test_search_cases(self):
        self.db.save_case(title="伤官格命例", summary="伤官见官", analysis_text="事业不顺", category="事业")
        self.db.save_case(title="正官格命例", summary="正官透出", analysis_text="官星得位", category="事业")
        self.db.save_case(title="情感案例", category="情感")

        r = self.db.search_cases("伤官")
        assert len(r) >= 1
        assert any("伤官" in (x.title or "") or "伤官" in (x.summary or "") for x in r)

        r2 = self.db.search_cases("命例", category="情感")
        for x in r2:
            assert x.category == "情感"

    def test_count_cases(self):
        for i in range(4):
            self.db.save_case(title=f"c{i}", category="事业", is_public=(i % 2 == 0))
        for i in range(3):
            self.db.save_case(title=f"em{i}", category="情感")
        assert self.db.count_cases() == 7
        assert self.db.count_cases(category="事业") == 4
        assert self.db.count_cases(category="情感") == 3
        # is_public=True 且 category="事业" 的记录数
        assert self.db.count_cases(category="事业", is_public=True) == 2

    def test_fulltext_search(self):
        self.db.save_case(title="伤官格", summary="伤官透干", analysis_text="身弱用印比")
        self.db.save_case(title="七杀格", summary="杀旺")
        self.db.save_case(title="正印格")
        assert self.db.fulltext_search("") == []
        r = self.db.fulltext_search("伤官")
        assert len(r) >= 1
        for case in r:
            text = " ".join(filter(None, [case.title, case.summary, case.analysis_text, case.fts_vector]))
            assert "伤官" in text

    def test_get_case_stats(self):
        for c, n in [("事业", 2), ("情感", 3), ("健康", 1)]:
            for i in range(n):
                self.db.save_case(title=f"{c}_{i}", category=c, is_featured=(i == 0 and c == "事业"))
        stats = self.db.get_case_stats()
        assert stats["total_cases"] == 6
        assert stats["featured_cases"] == 1
        assert stats["per_category"]["事业"] == 2
        assert stats["per_category"]["情感"] == 3

    def test_case_with_none_fields(self):
        cid = self.db.save_case(title="仅标题")
        case = self.db.get_case(cid)
        assert case.summary is None
        assert case.analysis_text is None
        assert case.category is None
        assert case.day_master is None
        assert case.pillars_json is None

    def test_case_with_empty_string_title(self):
        cid = self.db.save_case(title="")
        assert cid > 0

    def test_user_unchanged(self):
        u = self.db.get_or_create_user(f"p22_user_{uuid.uuid4().hex[:8]}", "演示用户")
        assert u is not None
        assert u.id > 0

    def test_bazirecord_save_and_list(self):
        rid = self.db.save_bazi_record(
            year=1990, month=6, day=15, hour=10, minute=0, gender="male",
            day_master="辛",
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
        )
        rec = self.db.get_bazi_record(rid)
        assert rec is not None
        assert rec.day_master == "辛"
        records = self.db.list_bazi_records(limit=10)
        assert len(records) >= 1


# ----------------------------------------------------------------------------
# TestPostgresConnection —— 连接池参数
# ----------------------------------------------------------------------------

class TestPostgresConnection:
    """PostgreSQL URL 会正确应用 pool_size / max_overflow。"""

    def test_postgres_pool_config_applied(self):
        """验证 DataStore 对 PostgreSQL 连接池参数正确设置。"""
        # 1) 通过检查源码确认参数字符串存在
        ds_path = os.path.join(
            os.path.dirname(__file__), "..", "tengod", "data_store.py"
        )
        source = open(ds_path, encoding="utf-8").read()
        assert 'pool_size=20' in source
        assert 'max_overflow=30' in source
        assert 'pool_timeout=30' in source
        assert 'pool_recycle=1800' in source
        assert 'pool_pre_ping=True' in source
        assert 'future=True' in source

        # 2) 猴子补丁 tengod.data_store 内对 create_engine 的引用
        #    以捕获实际传参并阻止真实数据库访问
        import tengod.data_store as _ds
        original = _ds.create_engine
        captured: Dict[str, Any] = {}

        def _fake(url, **kw):
            captured["url"] = url
            captured.update(kw)
            raise RuntimeError("stop-here")

        try:
            _ds.create_engine = _fake
            try:
                DataStore(db_url="postgresql://fake:fake@localhost/tengod_test")
            except RuntimeError as e:
                assert "stop-here" in str(e)
        finally:
            _ds.create_engine = original

        assert "postgres" in str(captured.get("url", ""))
        assert captured.get("pool_size") == 20
        assert captured.get("max_overflow") == 30
        assert captured.get("pool_timeout") == 30
        assert captured.get("pool_recycle") == 1800
        assert captured.get("pool_pre_ping") is True
        assert captured.get("future") is True

    def test_sqlite_fallback(self):
        db_path = _temp_db()
        store = DataStore(db_path)
        assert store.db_path == db_path
        assert store.db_url is None
        assert store._engine is not None
        cid = store.save_case(title="sqlite-test")
        assert cid > 0
        store.close()
        if os.path.exists(db_path):
            os.remove(db_path)


# ----------------------------------------------------------------------------
# TestVectorStorePG —— ChineseEmbedder
# ----------------------------------------------------------------------------

class TestVectorStorePG:
    """ChineseEmbedder 文本/八字/案例向量生成验证。"""

    def setup_method(self, method):
        self.embedder = ChineseEmbedder()

    def test_embed_text_dimension(self):
        vec = self.embedder.embed_text("身弱伤官格，用神取印比")
        assert isinstance(vec, list)
        assert len(vec) == 256
        assert all(isinstance(v, (int, float)) for v in vec)

    def test_embed_text_normalization(self):
        import math
        vec = self.embedder.embed_text("八字命理学")
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 1e-5 or norm == 0.0

    def test_embed_bazi(self):
        bazi = {
            "day_master": "辛",
            "pillars": {"year": "庚午", "month": "壬午"},
            "analysis": "身弱伤官",
            "geju": {"name": "伤官格"},
            "yongshen": {"wuxing": "土金"},
        }
        vec = self.embedder.embed_bazi(bazi)
        assert len(vec) == 256

    def test_embed_case(self):
        vec = self.embedder.embed_case(
            "伤官格命例",
            "辛金日主身弱",
            "用印比帮身",
            "事业",
        )
        assert len(vec) == 256

    def test_similar_text_higher_than_different(self):
        base = self.embedder.embed_text("伤官格 身弱 用印")
        similar = self.embedder.embed_text("伤官格 身弱 用印 事业")
        different = self.embedder.embed_text("正官格 身强 用财 情感")
        sim_same = sum(x * y for x, y in zip(base, similar))
        sim_diff = sum(x * y for x, y in zip(base, different))
        assert sim_same > sim_diff

    def test_empty_text(self):
        vec = self.embedder.embed_text("")
        assert len(vec) == 256
        assert all(v == 0.0 for v in vec)

    def test_in_memory_index_topk(self):
        from tengod.vector_store_pg import _InMemoryIndex as InMemoryIndex
        idx = InMemoryIndex()
        texts = [
            ("伤官格 身弱用印", {"label": "命例A"}),
            ("正官格 身强用财", {"label": "命例B"}),
            ("七杀格 制杀为权", {"label": "命例C"}),
            ("伤官格 身旺", {"label": "命例D"}),
        ]
        for i, (t, meta) in enumerate(texts):
            vec = self.embedder.embed_text(t)
            idx.add(i + 1, vec, meta)
        assert idx.size == 4
        query = self.embedder.embed_text("伤官格 身弱")
        results = idx.search(query, top_k=2)
        assert len(results) == 2
        top_labels = {r.get("label") for r in results}
        assert "命例A" in top_labels or "命例D" in top_labels


# ----------------------------------------------------------------------------
# TestCacheManager —— MemoryCacheManager
# ----------------------------------------------------------------------------

class TestCacheManager:
    """MemoryCacheManager 完整功能验证。"""

    def setup_method(self, method):
        self.cm = MemoryCacheManager()

    def test_get_set_delete(self):
        assert self.cm.set("k1", {"a": 1, "msg": "中文"})
        assert self.cm.get("k1") == {"a": 1, "msg": "中文"}
        self.cm.delete("k1")
        assert self.cm.get("k1") is None
        assert self.cm.get("not_exist") is None

    def test_ttl_expire(self):
        self.cm.set("short", {"x": 1}, ttl=1)
        assert self.cm.get("short") == {"x": 1}
        time.sleep(1.1)
        assert self.cm.get("short") is None

    def test_delete_pattern(self):
        self.cm.set("user_1", {"n": 1})
        self.cm.set("user_2", {"n": 2})
        self.cm.set("other", {"n": 3})
        removed = self.cm.delete_pattern("user_*")
        assert removed == 2
        assert self.cm.get("user_1") is None
        assert self.cm.get("other") is not None

    def test_cached_decorator(self):
        call_count = {"n": 0}

        @self.cm.cached("expensive", ttl=3600)
        def expensive(x: int) -> Dict[str, Any]:
            call_count["n"] += 1
            return {"x": x, "square": x * x}

        r1 = expensive(5)
        r2 = expensive(5)
        r3 = expensive(3)
        assert r1 == r2 == {"x": 5, "square": 25}
        assert r3 == {"x": 3, "square": 9}
        assert call_count["n"] == 2

    def test_rate_limit_sliding_window(self):
        uid = f"user_{uuid.uuid4().hex[:8]}"
        endpoint = "/api/test"
        limit, window = 3, 10
        results = [self.cm.rate_limit(uid, endpoint, limit, window) for _ in range(5)]
        assert results[:3] == [True, True, True]
        assert results[3] is False
        assert results[4] is False
        remaining = self.cm.get_rate_limit_remaining(uid, endpoint, limit, window)
        assert remaining == 0

    def test_session_caching(self):
        sid = f"session-{uuid.uuid4().hex}"
        data = {"user_id": 123, "name": "测试用户"}
        assert self.cm.cache_session(sid, data, ttl=3600)
        loaded = self.cm.get_session(sid)
        assert loaded == data
        self.cm.delete_session(sid)
        assert self.cm.get_session(sid) is None

    def test_health_check_memory(self):
        assert self.cm.health_check() is True

    def test_factory_function(self):
        cm = get_cache_manager()
        assert cm is not None
        key = f"factory_test_{uuid.uuid4().hex}"
        cm.set(key, {"ok": True})
        assert cm.get(key) == {"ok": True}


# ----------------------------------------------------------------------------
# TestMigrationTool —— 迁移管理器
# ----------------------------------------------------------------------------

class TestMigrationTool:
    """MigrationManager 基本功能验证。"""

    def test_instantiation(self):
        src = _temp_db("_src.db")
        dst = _temp_db("_dst.db")
        mm = MigrationManager(sqlite_path=src, postgres_url=f"sqlite:///{dst}")
        assert mm is not None
        try:
            mm.close()
        except Exception:
            pass
        for p in (src, dst):
            if os.path.exists(p):
                os.remove(p)

    def test_parse_datetime(self):
        from datetime import datetime as _dt
        src = _temp_db("_src2.db")
        dst = _temp_db("_dst2.db")
        mm = MigrationManager(sqlite_path=src, postgres_url=f"sqlite:///{dst}")
        cases = [
            "2024-01-15T10:30:00",
            "2024-01-15 10:30:00",
            "2024-01-15",
        ]
        for s in cases:
            result = mm._parse_datetime(s)
            assert result is not None, f"格式未解析: {s}"
            assert isinstance(result, _dt)
        assert mm._parse_datetime(None) is None
        assert mm._parse_datetime("") is None
        assert mm._parse_datetime("not a date") is None
        mm.close()
        for p in (src, dst):
            if os.path.exists(p):
                os.remove(p)

    def test_self_migration_sqlite_to_sqlite(self):
        src_db = _temp_db("_src.db")
        dst_db = _temp_db("_dst.db")
        src_store = DataStore(db_path=src_db)
        src_store.save_case(title="事业命例 A", category="事业", summary="测试摘要")
        src_store.save_case(title="情感命例 B", category="情感")
        src_store.save_bazi_record(
            year=1990, month=6, day=15, hour=10, gender="male", day_master="辛",
        )
        src_store.close()

        mm = MigrationManager(sqlite_path=src_db, postgres_url=f"sqlite:///{dst_db}")
        try:
            report = mm.run_all()
            assert report is not None
        finally:
            mm.close()

        dst_store = DataStore(db_path=dst_db)
        try:
            cases = dst_store.list_cases()
            assert isinstance(cases, list)
            records = dst_store.list_bazi_records()
            assert isinstance(records, list)
        finally:
            dst_store.close()
        for p in (src_db, dst_db):
            if os.path.exists(p):
                os.remove(p)

    def test_column_coercion(self):
        src = _temp_db("_src3.db")
        dst = _temp_db("_dst3.db")
        mm = MigrationManager(sqlite_path=src, postgres_url=f"sqlite:///{dst}")
        from tengod.data_store import LegacyCase as _Case
        assert mm._coerce_value(None, "category", _Case) is None
        assert mm._coerce_value("事业", "category", _Case) == "事业"
        result = mm._coerce_value(1, "is_public", _Case)
        assert result is not None
        json_text = '{"year": "庚午"}'
        result = mm._coerce_value(json_text, "pillars_json", _Case)
        assert result is not None
        mm.close()
        for p in (src, dst):
            if os.path.exists(p):
                os.remove(p)


# ----------------------------------------------------------------------------
# TestDataStats —— stats()
# ----------------------------------------------------------------------------

class TestDataStats:
    """stats() 统计信息验证。"""

    def setup_method(self, method):
        self.db_path = _temp_db()
        self.db = DataStore(db_path=self.db_path)

    def teardown_method(self, method):
        try:
            self.db.close()
        except Exception:
            pass
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_stats_structure(self):
        uname = f"p22_stats_{uuid.uuid4().hex[:8]}"
        u = self.db.get_or_create_user(uname, "统计测试")
        self.db.save_bazi_record(
            year=1990, month=6, day=15, hour=10, gender="male",
            day_master="辛", user_id=u.id,
        )
        self.db.save_bazi_record(
            year=1985, month=3, day=20, hour=8, gender="female",
            day_master="甲", user_id=u.id,
        )
        self.db.save_case(title="命例 A", category="事业", day_master="辛")
        self.db.save_case(title="命例 B", category="情感", day_master="甲")
        self.db.cache_report(1, "text", "报告内容")
        stats = self.db.stats()
        for k in ("total_users", "total_records", "total_cached_reports", "total_cases", "top_day_masters"):
            assert k in stats, f"缺少统计键: {k}"
        assert stats["total_users"] >= 1
        assert stats["total_records"] >= 2
        assert stats["total_cases"] == 2
        assert stats["total_cached_reports"] >= 1
        assert isinstance(stats["top_day_masters"], list)

    def test_stats_empty(self):
        stats = self.db.stats()
        assert stats["total_users"] == 0
        assert stats["total_records"] == 0
        assert stats["total_cases"] == 0
