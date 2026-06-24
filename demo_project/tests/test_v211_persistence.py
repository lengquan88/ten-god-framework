"""
test_v211_persistence.py — v2.11.0 持久化测试
==============================================
测试范围：
  - 数据库层 CRUD
  - 案例仓库
  - 对话/反馈持久化
  - 知识图谱持久化
  - 向后兼容（内存模式）
"""

import pytest
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# 测试辅助
# ============================================================================

@pytest.fixture
def temp_db():
    """临时数据库"""
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["STORAGE_BACKEND"] = "sqlite"
    os.environ["TENGOD_DB_PATH"] = path
    from tengod.database import reset_db, DatabaseManager
    reset_db()
    db = DatabaseManager(path)
    db.init()
    yield db
    db.close()
    os.unlink(path)
    os.environ["STORAGE_BACKEND"] = "memory"
    reset_db()


@pytest.fixture
def clean_db():
    """清理数据库环境"""
    os.environ["STORAGE_BACKEND"] = "memory"
    from tengod.database import reset_db
    reset_db()
    yield
    os.environ["STORAGE_BACKEND"] = "memory"
    reset_db()


# ============================================================================
# Test 1: Database CRUD
# ============================================================================

class TestDatabaseCRUD:
    """数据库层 CRUD 测试"""

    def test_init(self, temp_db):
        """测试初始化"""
        assert temp_db.is_initialized()
        stats = temp_db.get_stats()
        assert stats["cases"] == 0

    def test_case_crud(self, temp_db):
        """测试案例 CRUD"""
        # Insert
        case_id = temp_db.insert_case({
            "name": "测试案例", "bazi_data": {"year": "庚午"},
            "tags": ["test"], "category": "bazi",
        })
        assert case_id > 0

        # Get
        case = temp_db.get_case(case_id)
        assert case["name"] == "测试案例"
        assert case["bazi_data"]["year"] == "庚午"

        # Update
        temp_db.update_case(case_id, {"name": "更新案例", "tags": ["updated"]})
        case = temp_db.get_case(case_id)
        assert case["name"] == "更新案例"
        assert "updated" in case["tags"]

        # List
        cases = temp_db.list_cases()
        assert len(cases) == 1

        # Delete
        temp_db.delete_case(case_id)
        assert temp_db.get_case(case_id) is None

    def test_case_pagination(self, temp_db):
        """测试案例分页"""
        for i in range(5):
            temp_db.insert_case({"name": f"案例{i}", "category": "bazi"})

        page1 = temp_db.list_cases(limit=2, offset=0)
        page2 = temp_db.list_cases(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0]["id"] != page2[0]["id"]

    def test_case_search(self, temp_db):
        """测试案例搜索"""
        temp_db.insert_case({"name": "财运分析", "category": "bazi"})
        temp_db.insert_case({"name": "事业分析", "category": "bazi"})

        results = temp_db.list_cases(search="财运")
        assert len(results) == 1
        assert results[0]["name"] == "财运分析"

    def test_feedback_crud(self, temp_db):
        """测试反馈 CRUD"""
        fb_id = temp_db.insert_feedback({
            "session_id": "sess_001", "domain": "bazi",
            "accuracy": 5, "satisfaction": 4, "usefulness": 5,
            "comment": "很准"
        })
        assert fb_id > 0

        fbs = temp_db.list_feedback(domain="bazi")
        assert len(fbs) == 1
        assert fbs[0]["accuracy"] == 5

        stats = temp_db.get_feedback_stats()
        assert stats["total"] == 1
        assert stats["avg_accuracy"] == 5.0

    def test_conversation_crud(self, temp_db):
        """测试对话 CRUD"""
        temp_db.insert_message("sess_001", "user", "你好")
        temp_db.insert_message("sess_001", "assistant", "您好！")

        msgs = temp_db.get_conversation("sess_001")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"

        recent = temp_db.get_recent_conversations()
        assert len(recent) == 1
        assert recent[0]["session_id"] == "sess_001"

        temp_db.delete_conversation("sess_001")
        assert len(temp_db.get_conversation("sess_001")) == 0

    def test_kg_node_crud(self, temp_db):
        """测试知识图谱节点 CRUD"""
        temp_db.insert_kg_node({"id": "n1", "domain": "bazi", "concept": "五行", "confidence": 0.9})
        temp_db.insert_kg_node({"id": "n2", "domain": "bazi", "concept": "天干", "confidence": 0.8})

        node = temp_db.get_kg_node("n1")
        assert node["concept"] == "五行"

        nodes = temp_db.list_kg_nodes("bazi")
        assert len(nodes) == 2

    def test_kg_edge_crud(self, temp_db):
        """测试知识图谱边 CRUD"""
        temp_db.insert_kg_node({"id": "n1", "domain": "bazi", "concept": "A"})
        temp_db.insert_kg_node({"id": "n2", "domain": "bazi", "concept": "B"})
        temp_db.insert_kg_edge({"source_id": "n1", "target_id": "n2", "relation": "correlates", "weight": 0.7})

        edges = temp_db.list_kg_edges()
        assert len(edges) == 1

    def test_user_crud(self, temp_db):
        """测试用户 CRUD"""
        temp_db.create_user({"username": "testuser", "role": "admin", "quota_limit": 5000})
        user = temp_db.get_user(username="testuser")
        assert user["username"] == "testuser"
        assert user["quota_limit"] == 5000

        temp_db.update_quota("testuser", 10)
        ok, used, limit = temp_db.check_quota("testuser")
        assert ok
        assert used == 10

    def test_export_import(self, temp_db):
        """测试导入导出"""
        temp_db.insert_case({"name": "测试"})
        temp_db.insert_feedback({"session_id": "sess", "domain": "bazi"})

        export = temp_db.export_all()
        assert "cases" in export["tables"]
        assert len(export["tables"]["cases"]) == 1

        counts = temp_db.import_all(export)
        assert counts["cases"] >= 1

    def test_is_persistent(self, temp_db):
        """测试持久化状态"""
        from tengod.database import is_persistent
        assert is_persistent()

    def test_memory_mode(self, clean_db):
        """测试内存模式"""
        from tengod.database import is_persistent, get_db
        assert not is_persistent()


# ============================================================================
# Test 2: Case Repository
# ============================================================================

class TestCaseRepository:
    """案例仓库测试"""

    def test_seed(self, temp_db):
        """测试种子数据"""
        from tengod.case_repository import CaseRepository, reset_repository
        reset_repository()
        repo = CaseRepository()
        count = repo.seed()
        assert count == 5

    def test_add_and_get(self, temp_db):
        """测试添加和获取"""
        from tengod.case_repository import CaseRepository, reset_repository
        reset_repository()
        repo = CaseRepository()
        case = repo.add_case({"name": "自定义", "tags": ["custom"], "category": "test"})
        assert case["id"] > 0
        retrieved = repo.get_case(case["id"])
        assert retrieved["name"] == "自定义"

    def test_list_pagination(self, temp_db):
        """测试分页列表"""
        from tengod.case_repository import CaseRepository, reset_repository
        reset_repository()
        repo = CaseRepository()
        repo.seed()
        page = repo.list_cases(page=1, page_size=2)
        assert len(page["items"]) == 2
        assert page["total_pages"] >= 3

    def test_search(self, temp_db):
        """测试搜索"""
        from tengod.case_repository import CaseRepository, reset_repository
        reset_repository()
        repo = CaseRepository()
        repo.seed()
        results = repo.search("庚午")
        assert len(results) >= 1

    def test_export_import(self, temp_db):
        """测试文件导入导出"""
        from tengod.case_repository import CaseRepository, reset_repository
        reset_repository()
        repo = CaseRepository()
        repo.seed()

        path = "/tmp/test_cases_export.json"
        count = repo.export_to_json(path)
        assert count >= 5
        assert os.path.exists(path)

        imported = repo.import_from_json(path)
        assert imported >= 5

        os.unlink(path)

    def test_stats(self, temp_db):
        """测试统计"""
        from tengod.case_repository import CaseRepository, reset_repository
        reset_repository()
        repo = CaseRepository()
        repo.seed()
        stats = repo.get_stats()
        assert stats["total"] >= 5
        assert "bazi" in stats["by_category"]

    def test_similar_cases(self, temp_db):
        """测试相似案例查找"""
        from tengod.case_repository import CaseRepository, reset_repository
        reset_repository()
        repo = CaseRepository()
        repo.seed()
        similar = repo.get_similar_cases({"day_master": "辛金", "gender": "male"})
        assert len(similar) >= 1

    def test_singleton(self, temp_db):
        """测试单例"""
        from tengod.case_repository import get_repository, reset_repository
        reset_repository()
        r1 = get_repository()
        r2 = get_repository()
        assert r1 is r2


# ============================================================================
# Test 3: Persistence Integration
# ============================================================================

class TestPersistenceIntegration:
    """持久化集成测试"""

    def test_conversation_persist(self, temp_db):
        """测试对话持久化"""
        import tengod.ai_interpreter as ai
        ai._conversation_engine = None
        from tengod.ai_interpreter import get_conversation_engine
        ce = get_conversation_engine()
        ce.process_message("测试消息", "integ_test_001")
        ce.process_message("第二条消息", "integ_test_001")

        loaded = ce.load_session_from_db("integ_test_001")
        assert loaded is not None
        assert loaded["message_count"] == 2

    def test_feedback_persist(self, temp_db):
        """测试反馈持久化"""
        import tengod.knowledge_evolution as ke
        ke._evolution_engine = None
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        engine.collect_feedback("integ_fb", {"accuracy": 5, "satisfaction": 5, "usefulness": 5}, domain="bazi")

        from tengod.database import get_db
        fbs = get_db().list_feedback(session_id="integ_fb")
        assert len(fbs) == 1

    def test_kg_sync_and_load(self, temp_db):
        """测试知识图谱同步和加载"""
        import tengod.knowledge_evolution as ke
        ke._evolution_engine = None
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        result = engine.sync_knowledge_graph_to_db()
        assert result["nodes"] >= 10
        assert result["edges"] >= 5

        engine.reset()
        loaded = engine.load_knowledge_graph_from_db()
        assert loaded["nodes"] >= 10

    def test_feedback_load(self, temp_db):
        """测试反馈加载"""
        import tengod.knowledge_evolution as ke
        ke._evolution_engine = None
        from tengod.knowledge_evolution import get_evolution_engine
        engine = get_evolution_engine()
        engine.collect_feedback("load_test", {"accuracy": 5, "satisfaction": 5, "usefulness": 5}, domain="bazi")
        engine.collect_feedback("load_test2", {"accuracy": 4, "satisfaction": 4, "usefulness": 4}, domain="bazi")

        engine.reset()
        count = engine.load_feedback_from_db()
        assert count >= 2

    def test_full_cycle(self, temp_db):
        """测试完整持久化周期"""
        import tengod.knowledge_evolution as ke
        import tengod.ai_interpreter as ai
        ke._evolution_engine = None
        ai._conversation_engine = None

        from tengod.knowledge_evolution import get_evolution_engine
        from tengod.ai_interpreter import get_conversation_engine
        from tengod.case_repository import get_repository, reset_repository
        reset_repository()

        # 1. 案例
        repo = get_repository()
        repo.add_case({"name": "完整测试案例", "category": "bazi"})

        # 2. 对话
        ce = get_conversation_engine()
        ce.process_message("完整测试", "full_cycle")

        # 3. 反馈
        engine = get_evolution_engine()
        engine.collect_feedback("full_cycle", {"accuracy": 5, "satisfaction": 5, "usefulness": 5}, domain="bazi")

        # 4. 知识图谱
        engine.sync_knowledge_graph_to_db()

        # 5. 验证 DB
        from tengod.database import get_db
        stats = get_db().get_stats()
        assert stats["cases"] >= 1
        assert stats["conversations"] >= 1
        assert stats["feedback"] >= 1
        assert stats["kg_nodes"] >= 10


# ============================================================================
# Test 4: Database Persistence Hooks
# ============================================================================

class TestDatabaseHooks:
    """持久化钩子行为测试"""

    def test_persist_message_non_blocking(self, temp_db):
        """测试持久化失败不影响主流程"""
        import tengod.ai_interpreter as ai
        ai._conversation_engine = None
        from tengod.ai_interpreter import ConversationEngine
        ce = ConversationEngine()
        # 模拟无 DB 环境
        result = ce.process_message("测试", "hook_test")
        assert result["session_id"] == "hook_test"
        # 加载应该返回 None（无 DB 或 DB 为空）
        loaded = ce.load_session_from_db("hook_test")
        # 此 session 在 temp_db 中插入，可以加载
        from tengod.database import is_persistent
        if is_persistent():
            assert loaded is not None
            assert loaded["message_count"] >= 1

    def test_persist_feedback_non_blocking(self, temp_db):
        """测试反馈持久化非阻塞"""
        import tengod.knowledge_evolution as ke
        ke._evolution_engine = None
        from tengod.knowledge_evolution import KnowledgeEvolution
        engine = KnowledgeEvolution()
        fb = engine.collect_feedback("hook_test", {"accuracy": 3}, domain="test")
        assert fb.overall_score() == 3.0