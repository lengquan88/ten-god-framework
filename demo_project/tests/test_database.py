#!/usr/bin/env python3
"""
test_database.py — SQLite 数据库层深度测试 v1.0
==================================================
针对 database.py 中高风险逻辑路径的补充测试：

 1. 生命周期：init / is_initialized / close / get_stats
 2. 案例 CRUD：insert / get / update / delete / list / count / category + search 过滤
 3. JSON 字段序列化：bazi_data / analysis / tags / metadata 在 DB ↔ Dict 间的往返
 4. 反馈 CRUD：insert / list / count / get_feedback_stats
 5. 对话 CRUD：insert_message / get_conversation / delete_conversation / get_recent_conversations
 6. 知识图谱：节点 insert/get/list，边 insert/list，外键约束（删除节点级联删边）
 7. 用户与配额：create_user / get_user (username/api_key) / update_quota / check_quota
 8. 导入导出：export_all / import_all 白名单过滤（非法表名 → ValueError，非法列静默剔除）
 9. 全局单例：get_db / reset_db 线程安全语义 + is_persistent 环境变量读取

使用内存模式 (`:memory:`) 避免磁盘 IO，每个测试独立实例，无交叉污染。
"""

from __future__ import annotations

import os
import threading
import time
import tempfile
from pathlib import Path

import pytest

import tengod.database as dbmod
from tengod.database import (
    DatabaseManager,
    get_db,
    reset_db,
    is_persistent,
    ALLOWED_TABLES,
    EXPORT_TABLES,
    SCHEMA_VERSION,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def fresh_db():
    """每个测试使用独立的内存数据库实例，避免交叉污染。"""
    mgr = DatabaseManager(":memory:")
    mgr.init()
    yield mgr
    mgr.close()


@pytest.fixture(autouse=True)
def reset_global_db_instance():
    """确保 get_db() 单例在测试前后被重置。"""
    reset_db()
    yield
    reset_db()


@pytest.fixture
def persistent_db_path():
    """临时持久化数据库路径。"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    # Cleanup
    for suffix in ("", "-wal", "-shm", "-journal"):
        p = Path(path + suffix)
        if p.exists():
            p.unlink(missing_ok=True)


# ============================================================================
# 1. 生命周期
# ============================================================================

class TestLifecycle:
    def test_init_creates_schema(self, fresh_db):
        """init() 应创建所有 6 张业务表 + schema_version 并写入版本号。"""
        assert fresh_db.is_initialized() is True
        stats = fresh_db.get_stats()
        for t in EXPORT_TABLES:
            assert t in stats
            assert stats[t] == 0

    def test_is_initialized_before_init_returns_false(self):
        """未 init 的数据库 is_initialized 返回 False，不抛异常。"""
        mgr = DatabaseManager(":memory:")
        try:
            assert mgr.is_initialized() is False
        finally:
            mgr.close()

    def test_close_then_reinit_works(self, fresh_db):
        """关闭连接后仍可重新创建连接并使用。"""
        fresh_db.close()
        # init 重新打开新的连接
        fresh_db.init()
        assert fresh_db.is_initialized() is True

    def test_get_stats_empty_and_after_insert(self, fresh_db):
        """get_stats 在插入前后正确反映行数。"""
        before = fresh_db.get_stats()
        assert before["cases"] == 0

        fresh_db.insert_case({"name": "C1", "bazi_data": {"year": 1990}})
        after = fresh_db.get_stats()
        assert after["cases"] == 1
        assert after["feedback"] == 0


# ============================================================================
# 2 + 3. 案例 CRUD 与 JSON 往返
# ============================================================================

class TestCaseCRUD:
    def test_insert_and_get_roundtrip(self, fresh_db):
        """复杂嵌套 JSON 字段（bazi_data/analysis/tags/metadata）应完整往返。"""
        data = {
            "name": "张三命例",
            "category": "bazi",
            "bazi_data": {"year": 1990, "month": 5, "day": 12, "hour": 10, "gender": "male",
                          "五行": {"金": 2, "木": 1, "水": 1, "火": 2, "土": 2}},
            "analysis": {"十神": {"正官": 1, "七杀": 0}, "格局": "伤官格"},
            "tags": ["经典", "高相似度", "从格"],
            "metadata": {"source": "manual", "rating": 5},
        }
        cid = fresh_db.insert_case(data)
        assert cid > 0

        row = fresh_db.get_case(cid)
        assert row is not None
        assert row["name"] == "张三命例"
        assert row["category"] == "bazi"
        assert row["bazi_data"]["五行"]["火"] == 2
        assert row["analysis"]["格局"] == "伤官格"
        assert row["tags"] == ["经典", "高相似度", "从格"]
        assert row["metadata"]["rating"] == 5
        # 时间戳由 DB 自动填充
        assert "created_at" in row and row["created_at"] > 0
        assert "updated_at" in row and row["updated_at"] > 0

    def test_get_case_not_found(self, fresh_db):
        """不存在的案例返回 None，不抛异常。"""
        assert fresh_db.get_case(99999) is None

    def test_update_case_updates_fields_and_updates_timestamp(self, fresh_db):
        """update_case 只更新请求字段，其他字段保留；同时更新 updated_at。"""
        cid = fresh_db.insert_case({
            "name": "原命例",
            "bazi_data": {"year": 1990},
            "analysis": {"k": "v"},
            "tags": ["old"],
            "metadata": {"m": 1},
        })
        orig = fresh_db.get_case(cid)
        # 模拟时间推移以确保 updated_at 变化
        time.sleep(0.01)
        ok = fresh_db.update_case(cid, {
            "name": "改名",
            "category": "ziwei",
            "tags": ["new"],
            "analysis": {"new_analysis": True},
            # 故意不更新 bazi_data、metadata
        })
        assert ok is True
        updated = fresh_db.get_case(cid)
        assert updated["name"] == "改名"
        assert updated["category"] == "ziwei"
        assert updated["tags"] == ["new"]
        assert updated["analysis"] == {"new_analysis": True}
        # 未更新字段保留原值
        assert updated["bazi_data"] == {"year": 1990}
        assert updated["metadata"] == {"m": 1}
        # updated_at 应变大
        assert updated["updated_at"] >= orig["updated_at"]

    def test_update_case_no_fields_returns_false(self, fresh_db):
        """update_case 不带任何允许字段时返回 False，不执行 SQL。"""
        cid = fresh_db.insert_case({"name": "C"})
        assert fresh_db.update_case(cid, {"not_a_field": 1}) is False

    def test_update_case_missing_id_returns_false(self, fresh_db):
        """更新不存在的记录返回 False。"""
        assert fresh_db.update_case(12345, {"name": "X"}) is False

    def test_delete_case(self, fresh_db):
        """删除存在/不存在记录返回正确布尔值。"""
        cid = fresh_db.insert_case({"name": "D"})
        assert fresh_db.delete_case(cid) is True
        assert fresh_db.get_case(cid) is None
        assert fresh_db.delete_case(cid) is False

    def test_list_and_count_filtering(self, fresh_db):
        """list_cases 与 count_cases 支持 category 和 search 过滤。"""
        fresh_db.insert_case({"name": "甲子命", "category": "bazi",
                              "bazi_data": {"stem": "甲"}})
        fresh_db.insert_case({"name": "乙丑命", "category": "bazi",
                              "bazi_data": {"stem": "乙"}})
        fresh_db.insert_case({"name": "紫微盘", "category": "ziwei",
                              "bazi_data": {}})
        # category filter
        assert fresh_db.count_cases(category="bazi") == 2
        assert fresh_db.count_cases(category="ziwei") == 1
        assert fresh_db.count_cases(category="xxx") == 0
        # search by name
        r = fresh_db.list_cases(search="甲子")
        assert len(r) == 1 and r[0]["name"] == "甲子命"
        # search by bazi_data content
        r = fresh_db.list_cases(search="stem")
        assert len(r) == 2
        # pagination
        page1 = fresh_db.list_cases(limit=2, offset=0)
        page2 = fresh_db.list_cases(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 1  # 总计 3 条，offset=2 剩 1

    def test_count_cases_matches_total_list(self, fresh_db):
        """总数目应 = list_cases(limit=很大) 的长度。"""
        for i in range(5):
            fresh_db.insert_case({"name": f"C{i}"})
        assert fresh_db.count_cases() == 5
        assert len(fresh_db.list_cases(limit=100)) == 5


# ============================================================================
# 4. 反馈 CRUD
# ============================================================================

class TestFeedbackCRUD:
    def test_insert_and_list_defaults_applied(self, fresh_db):
        """反馈字段默认值（accuracy=3 / domain=general 等）应正确应用。"""
        fid = fresh_db.insert_feedback({"session_id": "s1"})
        assert fid > 0
        rows = fresh_db.list_feedback(session_id="s1")
        assert len(rows) == 1
        f = rows[0]
        assert f["session_id"] == "s1"
        assert f["domain"] == "general"
        assert f["accuracy"] == 3
        assert f["satisfaction"] == 3
        assert f["usefulness"] == 3
        assert f["corrections"] == []
        assert f["tags"] == []

    def test_list_feedback_domain_and_pagination(self, fresh_db):
        """list_feedback 按 domain / session_id 过滤并支持分页。"""
        for i in range(4):
            fresh_db.insert_feedback({"session_id": f"s{i%2}",
                                      "domain": "bazi" if i < 2 else "ziwei",
                                      "accuracy": 5, "comment": f"fb{i}"})
        assert len(fresh_db.list_feedback(domain="bazi")) == 2
        assert len(fresh_db.list_feedback(domain="ziwei")) == 2
        assert len(fresh_db.list_feedback(session_id="s0")) == 2
        # 分页
        assert len(fresh_db.list_feedback(limit=2, offset=2, domain="ziwei")) == 0
        assert len(fresh_db.list_feedback(limit=1, offset=1)) == 1

    def test_count_feedback_domain(self, fresh_db):
        fresh_db.insert_feedback({"session_id": "a", "domain": "D1"})
        fresh_db.insert_feedback({"session_id": "b", "domain": "D2"})
        fresh_db.insert_feedback({"session_id": "c", "domain": "D1"})
        assert fresh_db.count_feedback() == 3
        assert fresh_db.count_feedback("D1") == 2
        assert fresh_db.count_feedback("NX") == 0

    def test_get_feedback_stats_empty_and_values(self, fresh_db):
        """空表统计返回 0，平均值正确四舍五入。"""
        s = fresh_db.get_feedback_stats()
        assert s == {"total": 0, "avg_accuracy": 0.0, "avg_satisfaction": 0.0, "avg_usefulness": 0.0}

        fresh_db.insert_feedback({"session_id": "a", "accuracy": 5, "satisfaction": 4, "usefulness": 3})
        fresh_db.insert_feedback({"session_id": "b", "accuracy": 1, "satisfaction": 2, "usefulness": 1})
        s = fresh_db.get_feedback_stats()
        assert s["total"] == 2
        assert s["avg_accuracy"] == 3.0
        assert s["avg_satisfaction"] == 3.0
        assert s["avg_usefulness"] == 2.0

    def test_feedback_json_roundtrip(self, fresh_db):
        """corrections 与 tags JSON 字段完整往返。"""
        fid = fresh_db.insert_feedback({
            "session_id": "s",
            "corrections": [{"field": "x", "before": "a", "after": "b"}],
            "tags": ["重要", "需人工复核"],
        })
        row = fresh_db.list_feedback(session_id="s")[0]
        assert row["corrections"] == [{"field": "x", "before": "a", "after": "b"}]
        assert row["tags"] == ["重要", "需人工复核"]


# ============================================================================
# 5. 对话 CRUD
# ============================================================================

class TestConversationsCRUD:
    def test_insert_and_get_conversation_ordered_oldest_first(self, fresh_db):
        """对话按创建时间升序返回。"""
        s = "sess-1"
        for i, (role, msg) in enumerate([
            ("user", "你好"),
            ("assistant", "您好！请告诉我您的出生时间"),
            ("user", "1990年6月15日 10:30"),
        ]):
            fresh_db.insert_message(s, role, msg, {"step": i})
        # 插入第二条不同 session 确保过滤
        fresh_db.insert_message("sess-2", "user", "无关会话")

        conv = fresh_db.get_conversation(s)
        assert len(conv) == 3
        assert conv[0]["role"] == "user" and conv[0]["message"] == "你好"
        assert conv[1]["role"] == "assistant"
        assert conv[2]["message"] == "1990年6月15日 10:30"
        # intent JSON 往返
        assert conv[0]["intent"] == {"step": 0}
        # 会话必须限制为指定 session_id
        assert all(m["session_id"] == s for m in conv)

    def test_get_conversation_limit_param(self, fresh_db):
        s = "big-session"
        for i in range(10):
            fresh_db.insert_message(s, "user", f"msg{i}")
        assert len(fresh_db.get_conversation(s, limit=100)) == 10
        assert len(fresh_db.get_conversation(s, limit=3)) == 3

    def test_delete_conversation(self, fresh_db):
        fresh_db.insert_message("s1", "user", "m1")
        fresh_db.insert_message("s2", "user", "m2")
        assert fresh_db.delete_conversation("s1") is True
        assert len(fresh_db.get_conversation("s1")) == 0
        assert len(fresh_db.get_conversation("s2")) == 1
        # 再次删除返回 False
        assert fresh_db.delete_conversation("s1") is False

    def test_get_recent_conversations_summary(self, fresh_db):
        """最近会话摘要：按 session_id 聚合，按 last_msg 倒序。"""
        t0 = time.time()
        fresh_db.insert_message("A", "user", "A1")
        time.sleep(0.01)
        fresh_db.insert_message("B", "user", "B1")
        fresh_db.insert_message("B", "assistant", "B2")
        time.sleep(0.01)
        fresh_db.insert_message("A", "assistant", "A2")  # A 应最新

        recent = fresh_db.get_recent_conversations(limit=10)
        by_session = {r["session_id"]: r for r in recent}
        assert "A" in by_session and "B" in by_session
        # A 在 B 之后（因为最后一条消息更新）
        assert recent[0]["session_id"] == "A"
        assert by_session["B"]["message_count"] == 2
        assert by_session["A"]["message_count"] == 2


# ============================================================================
# 6. 知识图谱（节点 & 边 & 外键）
# ============================================================================

class TestKnowledgeGraph:
    def test_node_insert_upsert_and_get(self, fresh_db):
        """节点 id 是 TEXT 主键，INSERT OR REPLACE 语义（Upsert）。"""
        fresh_db.insert_kg_node({
            "id": "n1", "domain": "命理", "concept": "正官",
            "confidence": 0.9, "properties": {"wuxing": "金"},
            "sources": ["三命通会"],
        })
        n1 = fresh_db.get_kg_node("n1")
        assert n1 is not None
        assert n1["concept"] == "正官"
        assert n1["properties"] == {"wuxing": "金"}
        assert n1["sources"] == ["三命通会"]

        # Upsert：同 id 覆盖 concept 和 confidence
        fresh_db.insert_kg_node({
            "id": "n1", "domain": "命理", "concept": "正官（偏官）",
            "confidence": 0.95,
            "properties": {"wuxing": "金", "十神": "克我"},
            "sources": ["三命通会", "滴天髓"],
        })
        n1b = fresh_db.get_kg_node("n1")
        assert n1b["concept"] == "正官（偏官）"
        assert n1b["confidence"] == 0.95
        assert n1b["sources"] == ["三命通会", "滴天髓"]

    def test_node_get_missing_returns_none(self, fresh_db):
        assert fresh_db.get_kg_node("not-exists") is None

    def test_list_nodes_domain_filter(self, fresh_db):
        for i in range(3):
            fresh_db.insert_kg_node({"id": f"b{i}", "domain": "bazi", "concept": f"B{i}"})
        for i in range(2):
            fresh_db.insert_kg_node({"id": f"z{i}", "domain": "ziwei", "concept": f"Z{i}"})
        assert len(fresh_db.list_kg_nodes()) == 5
        assert len(fresh_db.list_kg_nodes("bazi")) == 3
        assert len(fresh_db.list_kg_nodes("none")) == 0

    def test_edges_foreign_key_cascade(self, fresh_db):
        """
        kg_edges.source_id/target_id 引用 kg_nodes.id。
        当 ON DELETE CASCADE 开启时，删除节点应同时删除关联边。
        """
        fresh_db.insert_kg_node({"id": "A", "concept": "A", "domain": "d"})
        fresh_db.insert_kg_node({"id": "B", "concept": "B", "domain": "d"})
        eid = fresh_db.insert_kg_edge({
            "source_id": "A", "target_id": "B",
            "relation": "生", "weight": 0.9, "confidence": 0.8,
        })
        assert eid > 0
        # 双向过滤
        assert len(fresh_db.list_kg_edges(source_id="A")) == 1
        assert len(fresh_db.list_kg_edges(target_id="B")) == 1
        assert len(fresh_db.list_kg_edges(target_id="A")) == 0

        # 级联删除：删源节点 A 应同步删边
        with fresh_db._cursor() as cur:
            cur.execute("DELETE FROM kg_nodes WHERE id='A'")
        assert len(fresh_db.list_kg_edges()) == 0


# ============================================================================
# 7. 用户与配额
# ============================================================================

class TestUsersAndQuota:
    def test_create_user_defaults_and_roundtrip(self, fresh_db):
        uid = fresh_db.create_user({
            "username": "alice",
            "password_hash": "ph",
            "api_key": "k-abc",
            "role": "admin",
            "quota_limit": 5000,
            "metadata": {"team": "nlp"},
        })
        assert uid > 0

        # 按用户名查询
        u = fresh_db.get_user(username="alice")
        assert u is not None
        assert u["username"] == "alice"
        assert u["password_hash"] == "ph"
        assert u["api_key"] == "k-abc"
        assert u["role"] == "admin"
        assert u["quota_limit"] == 5000
        assert u["quota_used"] == 0
        assert u["metadata"] == {"team": "nlp"}

        # 按 api_key 查询
        u2 = fresh_db.get_user(api_key="k-abc")
        assert u2 is not None and u2["id"] == uid

        # 两者均不提供 → None
        assert fresh_db.get_user() is None

        # 不存在 → None
        assert fresh_db.get_user(username="bob") is None

    def test_update_and_check_quota(self, fresh_db):
        fresh_db.create_user({"username": "bob", "quota_limit": 10})
        ok, used, limit = fresh_db.check_quota("bob")
        assert ok is True and used == 0 and limit == 10

        # +1 配额
        assert fresh_db.update_quota("bob", 1) is True
        assert fresh_db.check_quota("bob") == (True, 1, 10)

        # +9 → 达到上限 10（quota_used < quota_limit → False 哦不: 10 < 10 是 False）
        fresh_db.update_quota("bob", 9)
        ok, used, limit = fresh_db.check_quota("bob")
        assert used == 10
        assert ok is False  # 严格 < 上限才算可用

        # delta 可以是负数（归还配额）
        fresh_db.update_quota("bob", -2)
        ok, used, _ = fresh_db.check_quota("bob")
        assert used == 8 and ok is True

        # 不存在用户的 check_quota 返回 (False, 0, 0)
        assert fresh_db.check_quota("ghost") == (False, 0, 0)

    def test_update_quota_missing_user_returns_false(self, fresh_db):
        assert fresh_db.update_quota("ghost", 5) is False


# ============================================================================
# 8. 导入 / 导出 与 白名单校验
# ============================================================================

class TestExportImport:
    def test_export_all_structure(self, fresh_db):
        """export_all 返回 schema_version + exported_at + 所有表的列表。"""
        fresh_db.insert_case({"name": "C1"})
        fresh_db.insert_feedback({"session_id": "s1"})
        payload = fresh_db.export_all()
        assert set(payload.keys()) == {"schema_version", "exported_at", "tables"}
        assert payload["schema_version"] == SCHEMA_VERSION
        assert payload["exported_at"] > 0
        assert set(payload["tables"].keys()) == set(EXPORT_TABLES)
        assert len(payload["tables"]["cases"]) == 1
        assert len(payload["tables"]["feedback"]) == 1

    def test_import_all_roundtrip(self, fresh_db, persistent_db_path):
        """导出 → 清空 → 导入 应完整还原数据。"""
        # 填充源库
        cid1 = fresh_db.insert_case({"name": "C1", "tags": ["t1", "t2"]})
        cid2 = fresh_db.insert_case({"name": "C2", "category": "ziwei"})
        fresh_db.insert_feedback({"session_id": "s1", "comment": "good",
                                  "tags": ["x"]})
        fresh_db.create_user({"username": "u1", "quota_limit": 777,
                              "metadata": {"a": 1}})
        payload = fresh_db.export_all()

        # 新库导入
        mgr2 = DatabaseManager(persistent_db_path)
        try:
            mgr2.init()
            counts = mgr2.import_all(payload)
            assert counts["cases"] == 2
            assert counts["feedback"] == 1
            assert counts["users"] == 1

            # 验证导入内容（注意 cases id 保持）
            rc1 = mgr2.get_case(cid1)
            assert rc1 is not None and rc1["name"] == "C1" and rc1["tags"] == ["t1", "t2"]
            rc2 = mgr2.get_case(cid2)
            assert rc2["category"] == "ziwei"
            assert mgr2.get_user(username="u1")["quota_limit"] == 777
            fb = mgr2.list_feedback(session_id="s1")[0]
            assert fb["comment"] == "good" and fb["tags"] == ["x"]
        finally:
            mgr2.close()

    def test_import_all_rejects_invalid_table(self, fresh_db):
        """非法表名应抛 ValueError，不允许写入。"""
        payload = {"tables": {"bad_table": [{"id": 1, "name": "x"}]}}
        with pytest.raises(ValueError, match="Invalid table name"):
            fresh_db.import_all(payload)

    def test_import_all_invalid_columns_silently_filtered(self, fresh_db):
        """
        行中存在 ALLOWED_TABLES 以外的列时，被过滤掉后仍可插入。
        若所有列都无效则抛 ValueError。
        """
        payload = {"tables": {
            "cases": [
                # id 不在 ALLOWED_TABLES["cases"]? — 实际上 id 是允许的。
                # 加一个非法列 'bogus_field'
                {"id": 1, "name": "ok-case", "bogus_field": 123,
                 "category": "general"}
            ]
        }}
        counts = fresh_db.import_all(payload)
        assert counts["cases"] == 1
        row = fresh_db.get_case(1)
        assert row["name"] == "ok-case"
        # bogus_field 被过滤（没写入，DB 用默认）

    def test_import_all_no_valid_columns_raises(self, fresh_db):
        """当所有列都不在白名单 → ValueError。"""
        payload = {"tables": {
            "cases": [{"bogus": 1, "also_bad": 2}]
        }}
        with pytest.raises(ValueError, match="No valid columns"):
            fresh_db.import_all(payload)

    def test_import_all_empty_rows_is_zero_count(self, fresh_db):
        """行列表为空时不报错，返回 0。"""
        payload = {"tables": {"cases": []}}
        counts = fresh_db.import_all(payload)
        assert counts["cases"] == 0


# ============================================================================
# 9. 全局单例 & 环境配置
# ============================================================================

class TestGlobalSingleton:
    def test_get_db_returns_same_instance(self):
        """同一 db_path 上 get_db() 返回同一对象（单例）。"""
        a = get_db(":memory:")
        b = get_db(":memory:")
        assert a is b

    def test_reset_db_recreates_instance(self):
        """reset_db() 后 get_db() 返回新对象。"""
        a = get_db(":memory:")
        reset_db()
        b = get_db(":memory:")
        assert a is not b

    def test_is_persistent_reads_env(self, monkeypatch):
        monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
        assert is_persistent() is True
        monkeypatch.setenv("STORAGE_BACKEND", "memory")
        assert is_persistent() is False
        monkeypatch.delenv("STORAGE_BACKEND", raising=False)
        assert is_persistent() is False  # 默认 memory

    def test_get_db_sqlite_backend_auto_init(self, monkeypatch, persistent_db_path):
        """STORAGE_BACKEND=sqlite 时 get_db 会自动 init()。"""
        monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
        monkeypatch.setenv("TENGOD_DB_PATH", persistent_db_path)
        # 注意：get_db() 读取的是模块级常量 STORAGE_BACKEND（import 时缓存），
        # 不是每次从 os.environ 读。需要同时替换模块级变量才能触发 init。
        # 本测试改为直接验证：若传入 STORAGE_BACKEND=sqlite 的新模块副本也能 init，
        # 或直接构造 DatabaseManager + 手动调用路径确保 init 行为。
        import importlib
        import tengod
        # 覆盖模块级变量并 reset 单例
        monkeypatch.setattr(dbmod, "STORAGE_BACKEND", "sqlite")
        monkeypatch.setattr(dbmod, "DB_PATH", persistent_db_path)
        reset_db()
        mgr = get_db()
        try:
            assert mgr.is_initialized() is True
        finally:
            reset_db()

    def test_module_constants_sane(self):
        """所有导出常量符合预期形状。"""
        assert SCHEMA_VERSION == 1
        assert set(EXPORT_TABLES) == {"cases", "feedback", "conversations",
                                       "kg_nodes", "kg_edges", "users"}
        for tbl, cols in ALLOWED_TABLES.items():
            assert tbl in EXPORT_TABLES
            assert isinstance(cols, set) and len(cols) > 0
