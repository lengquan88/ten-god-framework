"""
test_v212_data_api.py — v2.12.0 数据管理 API 测试
==================================================
测试范围：
  - 案例管理 API 接口逻辑
  - 数据管理 API 接口逻辑
  - 部署配置文件验证
  - 用户集成
  - 向后兼容性
"""

import pytest
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


# ============================================================================
# Test 1: Case Repository API Logic
# ============================================================================

class TestCaseRepositoryAPI:
    """案例仓库 API 逻辑测试"""

    def test_seed_and_list(self, temp_db):
        """测试种子数据+列表"""
        from tengod.case_repository import get_repository, reset_repository
        reset_repository()
        repo = get_repository()
        repo.seed()
        result = repo.list_cases(page=1, page_size=20)
        assert result["total"] >= 5
        assert len(result["items"]) >= 5
        assert result["page"] == 1

    def test_search_cases(self, temp_db):
        """测试搜索"""
        from tengod.case_repository import get_repository, reset_repository
        reset_repository()
        repo = get_repository()
        repo.seed()
        results = repo.search("庚午")
        assert len(results) >= 1

    def test_add_case(self, temp_db):
        """测试添加案例"""
        from tengod.case_repository import get_repository, reset_repository
        reset_repository()
        repo = get_repository()
        case = repo.add_case({"name": "API测试", "bazi_data": {"day_master": "甲木"}, "tags": ["api"], "category": "test"})
        assert case["id"] > 0
        assert case["name"] == "API测试"

    def test_full_crud_cycle(self, temp_db):
        """测试完整 CRUD"""
        from tengod.case_repository import get_repository, reset_repository
        reset_repository()
        repo = get_repository()
        # Create
        case = repo.add_case({"name": "CRUD测试", "category": "test"})
        case_id = case["id"]
        # Read
        assert repo.get_case(case_id)["name"] == "CRUD测试"
        # Update
        repo.update_case(case_id, {"name": "CRUD更新"})
        assert repo.get_case(case_id)["name"] == "CRUD更新"
        # Delete
        repo.delete_case(case_id)
        assert repo.get_case(case_id) is None

    def test_export_import(self, temp_db):
        """测试导出导入"""
        from tengod.case_repository import get_repository, reset_repository
        reset_repository()
        repo = get_repository()
        repo.seed()
        path = "/tmp/test_api_export.json"
        count = repo.export_to_json(path)
        assert count >= 5
        assert os.path.exists(path)
        imported = repo.import_from_json(path)
        assert imported >= 5
        os.unlink(path)

    def test_bulk_import(self, temp_db):
        """测试批量导入"""
        from tengod.case_repository import get_repository, reset_repository
        reset_repository()
        repo = get_repository()
        cases = [
            {"name": "批量1", "category": "test"},
            {"name": "批量2", "category": "test"},
            {"name": "批量3", "category": "test"},
        ]
        count = repo.bulk_import(cases)
        assert count == 3

    def test_similar_cases(self, temp_db):
        """测试相似案例"""
        from tengod.case_repository import get_repository, reset_repository
        reset_repository()
        repo = get_repository()
        repo.seed()
        similar = repo.get_similar_cases({"day_master": "辛金"})
        assert len(similar) >= 1

    def test_get_stats(self, temp_db):
        """测试统计"""
        from tengod.case_repository import get_repository, reset_repository
        reset_repository()
        repo = get_repository()
        repo.seed()
        stats = repo.get_stats()
        assert stats["total"] >= 5
        assert "bazi" in stats["by_category"]


# ============================================================================
# Test 2: Database Management API Logic
# ============================================================================

class TestDatabaseManagementAPI:
    """数据库管理 API 逻辑测试"""

    def test_db_stats(self, temp_db):
        """测试数据库统计"""
        from tengod.database import get_db
        stats = get_db().get_stats()
        assert "cases" in stats
        assert "feedback" in stats
        assert "conversations" in stats

    def test_feedback_stats(self, temp_db):
        """测试反馈统计"""
        from tengod.database import get_db
        get_db().insert_feedback({"session_id": "stat_test", "domain": "bazi", "accuracy": 5, "satisfaction": 4, "usefulness": 5})
        stats = get_db().get_feedback_stats()
        assert stats["total"] >= 1
        assert stats["avg_accuracy"] >= 4.0

    def test_conversation_list(self, temp_db):
        """测试会话列表"""
        from tengod.database import get_db
        get_db().insert_message("conv_api", "user", "测试")
        get_db().insert_message("conv_api", "assistant", "回复")
        recent = get_db().get_recent_conversations(limit=5)
        assert len(recent) >= 1

    def test_full_export_import(self, temp_db):
        """测试全量导出导入"""
        from tengod.database import get_db
        db = get_db()
        db.insert_case({"name": "导出测试"})
        export = db.export_all()
        assert "cases" in export["tables"]
        counts = db.import_all(export)
        assert counts["cases"] >= 1


# ============================================================================
# Test 3: Deployment Configuration
# ============================================================================

class TestDeploymentConfig:
    """部署配置验证"""

    def test_docker_compose_exists(self):
        """测试 docker-compose.yml 存在"""
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docker-compose.yml")
        assert os.path.exists(path)

    def test_docker_compose_valid(self):
        """测试 docker-compose.yml 格式有效"""
        import yaml
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docker-compose.yml")
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "services" in data
        assert "api" in data["services"]
        assert "nginx" in data["services"]

    def test_nginx_conf_exists(self):
        """测试 nginx.conf 存在"""
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nginx.conf")
        assert os.path.exists(path)

    def test_nginx_conf_has_upstream(self):
        """测试 nginx.conf 包含上游配置"""
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nginx.conf")
        with open(path) as f:
            content = f.read()
        assert "upstream tengod_api" in content
        assert "proxy_pass" in content

    def test_env_example_exists(self):
        """测试 .env.example 存在"""
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.example")
        assert os.path.exists(path)

    def test_env_example_keys(self):
        """测试 .env.example 包含关键配置"""
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.example")
        with open(path) as f:
            content = f.read()
        assert "STORAGE_BACKEND" in content
        assert "TENGOD_DB_PATH" in content
        assert "LOG_LEVEL" in content

    def test_healthcheck_script_exists(self):
        """测试健康检查脚本存在"""
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts/healthcheck.sh")
        assert os.path.exists(path)


# ============================================================================
# Test 4: User Integration
# ============================================================================

class TestUserIntegration:
    """用户集成测试"""

    def test_sync_user_to_db(self, temp_db):
        """测试用户同步到数据库"""
        from tengod.auth import sync_user_to_db
        result = sync_user_to_db("testuser", "testpass", "user")
        assert result["username"] == "testuser"
        assert result["role"] == "user"

        from tengod.database import get_db
        user = get_db().get_user(username="testuser")
        assert user is not None
        assert user["role"] == "user"

    def test_check_db_quota(self, temp_db):
        """测试数据库配额检查"""
        from tengod.auth import sync_user_to_db, check_db_quota, update_db_quota
        sync_user_to_db("quota_user", "pass", "user")
        ok, used, limit = check_db_quota("quota_user")
        assert ok
        assert used == 0
        update_db_quota("quota_user", 5)
        ok, used, limit = check_db_quota("quota_user")
        assert used == 5

    def test_load_users_from_db(self, temp_db):
        """测试从数据库加载用户"""
        from tengod.auth import load_users_from_db
        count = load_users_from_db()
        assert count >= 1

    def test_guest_role_exists(self):
        """测试 guest 角色"""
        from tengod.auth import ROLE_PERMISSIONS
        assert "guest" in ROLE_PERMISSIONS
        assert "bazi:calc" in ROLE_PERMISSIONS["guest"]["permissions"]

    def test_data_permissions_added(self):
        """测试 v2.12 数据权限"""
        from tengod.auth import ROLE_PERMISSIONS
        user_perms = ROLE_PERMISSIONS["user"]["permissions"]
        assert "data:read" in user_perms
        assert "data:write" in user_perms


# ============================================================================
# Test 5: Backward Compatibility
# ============================================================================

class TestBackwardCompatibility:
    """向后兼容性测试"""

    def test_database_imports(self):
        """测试数据库模块导入"""
        from tengod.database import (
            DatabaseManager, get_db, reset_db, is_persistent,
            STORAGE_BACKEND, DB_PATH,
        )
        assert DatabaseManager is not None

    def test_case_repository_imports(self):
        """测试案例仓库导入"""
        from tengod.case_repository import (
            CaseRepository, get_repository, reset_repository, SEED_CASES,
        )
        assert len(SEED_CASES) == 5

    def test_auth_imports(self):
        """测试认证模块导入"""
        from tengod.auth import (
            sync_user_to_db, load_users_from_db,
            check_db_quota, update_db_quota,
        )
        assert callable(sync_user_to_db)

    def test_existing_api_unchanged(self):
        """测试现有 API 不变"""
        from tengod.ai_interpreter import interpret_bazi, build_bazi_context
        from tengod.agent_orchestrator import quick_orchestrate
        from tengod.knowledge_evolution import quick_feedback
        assert callable(interpret_bazi)
        assert callable(build_bazi_context)
        assert callable(quick_orchestrate)
        assert callable(quick_feedback)

    def test_memory_mode_still_works(self):
        """测试内存模式正常工作"""
        os.environ["STORAGE_BACKEND"] = "memory"
        from tengod.database import reset_db, is_persistent
        reset_db()
        assert not is_persistent()

        from tengod.case_repository import get_repository, reset_repository
        reset_repository()
        repo = get_repository()
        result = repo.list_cases()
        assert result["total"] == 0