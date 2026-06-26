#!/usr/bin/env python3
"""
test_case_library.py — 命例案例库测试
覆盖：CaseLibrary 类方法、API 端点、导入导出、相似推荐
"""
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.pop("TENGOD_API_KEY", None)
os.environ["TENGOD_LLM_BACKEND"] = "mock"

from fastapi.testclient import TestClient
from tengod.api_server import app
from tengod.auth import QuotaManager, JWTManager
from tengod.data_store import DataStore
from tengod.case_library import CaseLibrary, Case, CaseRelation, DEFAULT_CATEGORIES


def unwrap(r):
    """解包内在小孩门禁包裹的响应 {output, confidence, uncertainty} → output"""
    data = r.json()
    if isinstance(data, dict) and "output" in data and "confidence" in data:
        return data["output"]
    return data


# ════════════════════════════════════════
# 测试夹具
# ════════════════════════════════════════

@pytest.fixture
def temp_store():
    """临时数据库 DataStore"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        store = DataStore(db_path=db_path)
        yield store
    finally:
        store.close()
        os.unlink(db_path)


@pytest.fixture
def lib(temp_store):
    """CaseLibrary 实例"""
    return CaseLibrary(temp_store)


@pytest.fixture
def sample_record(temp_store):
    """创建示例八字记录"""
    user = temp_store.get_or_create_user("test_user")
    return temp_store.save_bazi_record(
        year=1990, month=6, day=15, hour=10,
        gender="male", user_id=user.id, day_master="辛",
        pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
        analysis={"wuxing": {"金": 2, "水": 2, "火": 3, "土": 1}},
        geju={"geju_name": "伤官格"},
    )


@pytest.fixture
def sample_case(lib, sample_record):
    """创建示例案例"""
    return lib.create_case(
        record_id=sample_record,
        title="某企业家命例",
        category="事业",
        summary="辛金日主，伤官格，适合创业",
        tags=["企业家", "创业"],
    )


@pytest.fixture
def client_and_headers():
    """TestClient 和认证 headers"""
    client = TestClient(app)
    token = JWTManager.create_access_token(1, "testuser", "user")
    return client, {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_state():
    """每个测试前清空配额和限流状态"""
    QuotaManager._usage.clear()
    from tengod.api_server import _request_counts
    _request_counts.clear()
    # 重置 case library 单例，避免测试间状态泄漏
    import tengod.case_library as cl
    cl._library = None
    yield
    QuotaManager._usage.clear()
    _request_counts.clear()
    cl._library = None


# ════════════════════════════════════════
# 1. CaseLibrary 基础 CRUD 测试
# ════════════════════════════════════════

class TestCaseLibraryCRUD:
    """CaseLibrary CRUD 测试"""

    def test_create_case(self, lib, sample_record):
        """创建案例"""
        case_id = lib.create_case(
            record_id=sample_record,
            title="测试案例",
            category="事业",
        )
        assert case_id > 0

    def test_create_case_invalid_record(self, lib):
        """创建案例 - 无效记录ID"""
        with pytest.raises(ValueError):
            lib.create_case(record_id=99999, title="无效案例")

    def test_get_case(self, lib, sample_case):
        """获取案例"""
        case = lib.get_case(sample_case)
        assert case is not None
        assert case["title"] == "某企业家命例"
        assert case["category"] == "事业"
        assert "record" in case

    def test_get_case_not_found(self, lib):
        """获取不存在的案例"""
        assert lib.get_case(99999) is None

    def test_get_case_increment_view(self, lib, sample_case):
        """获取案例时增加浏览数"""
        lib.get_case(sample_case, increment_view=True)
        lib.get_case(sample_case, increment_view=True)
        case = lib.get_case(sample_case)
        assert case["view_count"] >= 2

    def test_list_cases(self, lib, sample_case):
        """列出案例"""
        result = lib.list_cases()
        assert result["total"] >= 1
        assert len(result["cases"]) >= 1

    def test_list_cases_by_category(self, lib, sample_case):
        """按分类筛选案例"""
        result = lib.list_cases(category="事业")
        assert result["total"] >= 1
        result = lib.list_cases(category="不存在")
        assert result["total"] == 0

    def test_update_case(self, lib, sample_case):
        """更新案例"""
        success = lib.update_case(sample_case, title="更新后的标题", summary="新摘要")
        assert success
        case = lib.get_case(sample_case)
        assert case["title"] == "更新后的标题"
        assert case["summary"] == "新摘要"

    def test_update_case_tags(self, lib, sample_case):
        """更新案例标签"""
        success = lib.update_case(sample_case, tags=["新标签1", "新标签2"])
        assert success
        case = lib.get_case(sample_case)
        assert "新标签1" in case["tags"]
        assert "新标签2" in case["tags"]

    def test_delete_case(self, lib, sample_case):
        """删除案例"""
        success = lib.delete_case(sample_case)
        assert success
        assert lib.get_case(sample_case) is None

    def test_delete_case_not_found(self, lib):
        """删除不存在的案例"""
        assert lib.delete_case(99999) is False


# ════════════════════════════════════════
# 2. 搜索测试
# ════════════════════════════════════════

class TestCaseSearch:
    """案例搜索测试"""

    def test_search_by_keyword(self, lib, sample_case):
        """关键词搜索"""
        result = lib.search_cases(keyword="企业家")
        assert result["total"] >= 1

    def test_search_by_category(self, lib, sample_case):
        """分类搜索"""
        result = lib.search_cases(category="事业")
        assert result["total"] >= 1

    def test_search_by_tag(self, lib, sample_case):
        """标签搜索"""
        result = lib.search_cases(tag="创业")
        assert result["total"] >= 1

    def test_search_by_day_master(self, lib, sample_case):
        """日主搜索"""
        result = lib.search_cases(day_master="辛")
        assert result["total"] >= 1

    def test_search_by_geju(self, lib, sample_case):
        """格局搜索"""
        result = lib.search_cases(geju="伤官格")
        assert result["total"] >= 1

    def test_search_no_result(self, lib):
        """无结果搜索"""
        result = lib.search_cases(keyword="不存在的关键词")
        assert result["total"] == 0

    def test_search_combined(self, lib, sample_case):
        """组合条件搜索"""
        result = lib.search_cases(category="事业", day_master="辛")
        assert result["total"] >= 1


# ════════════════════════════════════════
# 3. 分类与标签测试
# ════════════════════════════════════════

class TestCategoriesAndTags:
    """分类与标签测试"""

    def test_list_categories(self, lib, sample_case):
        """列出分类"""
        cats = lib.list_categories()
        assert len(cats) >= 1
        assert any(c["name"] == "事业" for c in cats)

    def test_list_tags(self, lib, sample_case):
        """列出标签"""
        tags = lib.list_tags()
        assert len(tags) >= 2
        tag_names = [t["name"] for t in tags]
        assert "企业家" in tag_names
        assert "创业" in tag_names

    def test_default_categories(self):
        """预定义分类"""
        assert "富贵" in DEFAULT_CATEGORIES
        assert "事业" in DEFAULT_CATEGORIES
        assert "婚姻" in DEFAULT_CATEGORIES
        assert len(DEFAULT_CATEGORIES) >= 10


# ════════════════════════════════════════
# 4. 互动功能测试
# ════════════════════════════════════════

class TestCaseInteractions:
    """案例互动功能测试"""

    def test_increment_view(self, lib, sample_case):
        """增加浏览数"""
        lib.increment_view(sample_case)
        lib.increment_view(sample_case)
        case = lib.get_case(sample_case)
        assert case["view_count"] >= 2

    def test_toggle_favorite(self, lib, sample_case):
        """收藏"""
        count = lib.toggle_favorite(sample_case)
        assert count >= 1

    def test_toggle_like(self, lib, sample_case):
        """点赞"""
        count = lib.toggle_like(sample_case)
        assert count >= 1


# ════════════════════════════════════════
# 5. 案例关联测试
# ════════════════════════════════════════

class TestCaseRelations:
    """案例关联测试"""

    def test_link_cases(self, lib, temp_store, sample_case):
        """建立案例关联"""
        # 创建第二个案例
        record2 = temp_store.save_bazi_record(
            year=1985, month=3, day=20, hour=14,
            gender="female", day_master="甲",
            pillars={"year": "乙丑", "month": "己卯", "day": "甲午", "hour": "辛未"},
            analysis={"wuxing": {"木": 2, "火": 1, "土": 2, "金": 1}},
            geju={"geju_name": "建禄格"},
        )
        case2 = lib.create_case(record_id=record2, title="对比案例")

        rel_id = lib.link_cases(sample_case, case2, "contrast", 0.5, "对比分析")
        assert rel_id > 0

    def test_link_self_error(self, lib, sample_case):
        """不能关联自己"""
        with pytest.raises(ValueError):
            lib.link_cases(sample_case, sample_case)

    def test_get_relations(self, lib, temp_store, sample_case):
        """获取案例关联"""
        record2 = temp_store.save_bazi_record(
            year=1985, month=3, day=20, hour=14,
            gender="female", day_master="甲",
        )
        case2 = lib.create_case(record_id=record2, title="关联案例")
        lib.link_cases(sample_case, case2, "similar", 0.8)

        rels = lib.get_relations(sample_case)
        assert len(rels) >= 1
        assert rels[0]["other_case_id"] == case2


# ════════════════════════════════════════
# 6. 相似案例推荐测试
# ════════════════════════════════════════

class TestSimilarCases:
    """相似案例推荐测试"""

    def test_find_similar_same_dm(self, lib, temp_store, sample_case):
        """同日主相似案例"""
        # 创建同日主案例
        record2 = temp_store.save_bazi_record(
            year=1988, month=8, day=8, hour=8,
            gender="male", day_master="辛",
            pillars={"year": "戊辰", "month": "庚申", "day": "辛卯", "hour": "壬辰"},
            analysis={"wuxing": {"金": 2, "水": 1, "土": 2, "木": 1}},
            geju={"geju_name": "建禄格"},
        )
        lib.create_case(record_id=record2, title="同日主案例")

        similar = lib.find_similar_cases(sample_case)
        assert len(similar) >= 1
        assert any(s["day_master"] == "辛" for s in similar)

    def test_find_similar_same_geju(self, lib, temp_store, sample_case):
        """同格局相似案例"""
        record2 = temp_store.save_bazi_record(
            year=1985, month=5, day=5, hour=5,
            gender="female", day_master="丙",
            pillars={"year": "乙丑", "month": "辛巳", "day": "丙午", "hour": "辛卯"},
            analysis={"wuxing": {"火": 2, "金": 2, "木": 1, "土": 1}},
            geju={"geju_name": "伤官格"},
        )
        lib.create_case(record_id=record2, title="同格局案例")

        similar = lib.find_similar_cases(sample_case)
        assert len(similar) >= 1

    def test_find_similar_not_found(self, lib):
        """不存在的案例"""
        similar = lib.find_similar_cases(99999)
        assert similar == []


# ════════════════════════════════════════
# 7. 导入导出测试
# ════════════════════════════════════════

class TestImportExport:
    """导入导出测试"""

    def test_export_json(self, lib, sample_case):
        """JSON 导出"""
        content = lib.export_cases(format="json")
        data = json.loads(content)
        assert "cases" in data
        assert len(data["cases"]) >= 1
        assert data["cases"][0]["title"] == "某企业家命例"

    def test_export_csv(self, lib, sample_case):
        """CSV 导出"""
        content = lib.export_cases(format="csv")
        lines = content.strip().split("\n")
        assert len(lines) >= 2  # header + at least 1 row
        assert "title" in lines[0]
        assert "某企业家命例" in lines[1]

    def test_import_json(self, lib, temp_store, sample_case):
        """JSON 导入"""
        # 先导出
        exported = lib.export_cases(format="json")
        # 创建新记录供导入使用
        record2 = temp_store.save_bazi_record(
            year=1985, month=3, day=20, hour=14,
            gender="female", day_master="甲",
        )
        # 修改导出数据，指向新记录
        data = json.loads(exported)
        data["cases"][0]["record"] = {
            "year": 1985, "month": 3, "day": 20, "hour": 14,
        }
        data["cases"][0]["title"] = "导入的案例"

        result = lib.import_cases(json.dumps(data), format="json")
        assert result["imported"] >= 1


# ════════════════════════════════════════
# 8. 统计测试
# ════════════════════════════════════════

class TestCaseStats:
    """案例库统计测试"""

    def test_stats(self, lib, sample_case):
        """统计信息"""
        stats = lib.stats()
        assert stats["total_cases"] >= 1
        assert stats["public_cases"] >= 1
        assert "categories" in stats
        assert "top_tags" in stats


# ════════════════════════════════════════
# 9. API 端点测试
# ════════════════════════════════════════

class TestCaseAPI:
    """案例库 API 端点测试"""

    def test_create_case_unauthorized(self, client_and_headers):
        """未认证不能创建案例"""
        client, _ = client_and_headers
        r = client.post("/api/cases", json={
            "record_id": 1, "title": "测试",
        })
        assert r.status_code in (401, 403)

    def test_create_case_authorized(self, client_and_headers, sample_record, temp_store):
        """认证用户创建案例"""
        client, headers = client_and_headers
        # 重置 case library 单例以使用临时测试数据库
        import tengod.case_library as cl
        from tengod.case_library import CaseLibrary
        cl._library = CaseLibrary(temp_store)

        r = client.post("/api/cases", json={
            "record_id": sample_record,
            "title": "API测试案例",
            "category": "事业",
            "tags": ["测试"],
        }, headers=headers)
        assert r.status_code == 200
        assert unwrap(r)["created"] is True

    def test_list_cases_api(self, client_and_headers):
        """列出案例 API"""
        client, headers = client_and_headers
        r = client.get("/api/cases", headers=headers)
        assert r.status_code == 200
        assert "total" in unwrap(r)

    def test_search_cases_api(self, client_and_headers):
        """搜索案例 API"""
        client, headers = client_and_headers
        r = client.post("/api/cases/search", json={
            "category": "事业",
        }, headers=headers)
        assert r.status_code == 200

    def test_categories_api(self, client_and_headers):
        """分类列表 API"""
        client, headers = client_and_headers
        r = client.get("/api/cases/categories/list", headers=headers)
        assert r.status_code == 200
        assert "categories" in unwrap(r)

    def test_tags_api(self, client_and_headers):
        """标签列表 API"""
        client, headers = client_and_headers
        r = client.get("/api/cases/tags/list", headers=headers)
        assert r.status_code == 200
        assert "tags" in unwrap(r)

    def test_stats_api(self, client_and_headers):
        """统计 API"""
        client, headers = client_and_headers
        r = client.get("/api/cases/stats/summary", headers=headers)
        assert r.status_code == 200

    def test_export_api(self, client_and_headers):
        """导出 API"""
        client, headers = client_and_headers
        r = client.get("/api/cases/export/all", params={"format": "json"}, headers=headers)
        assert r.status_code == 200

    def test_guest_can_read(self, client_and_headers):
        """游客可读案例（case:read 权限）"""
        client, _ = client_and_headers
        # 无 token 访问（guest）
        r = client.get("/api/cases")
        assert r.status_code == 200

    def test_guest_cannot_write(self, client_and_headers):
        """游客不能创建案例"""
        client, _ = client_and_headers
        r = client.post("/api/cases", json={
            "record_id": 1, "title": "游客尝试",
        })
        assert r.status_code in (401, 403)
