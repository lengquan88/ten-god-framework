#!/usr/bin/env python3
"""
test_case_repository.py — 案例仓库测试

覆盖 CaseRepository 所有公共方法、SEED_CASES 常量、get_repository/reset_repository 函数。
使用 unittest.mock.patch 完整模拟数据库层，不依赖真实 SQLite。
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from tengod.case_repository import (
    CaseRepository,
    SEED_CASES,
    get_repository,
    reset_repository,
)


# ══════════════════════════════════════════════════════════════
# 辅助工具
# ══════════════════════════════════════════════════════════════

def make_mock_db():
    """创建一个模拟 DatabaseManager 用于注入"""
    db = MagicMock()
    db._db_path = "/tmp/mock_tengod.db"
    return db


def make_case_row(case_id=1, name="测试案例", category="bazi", tags=None, bazi_data=None, analysis=None):
    """快速构造一个类似 db._row_to_case 返回的字典"""
    return {
        "id": case_id,
        "name": name,
        "bazi_data": bazi_data if bazi_data is not None else {"day_master": "辛金", "gender": "male"},
        "analysis": analysis if analysis is not None else {"geju": "财旺身弱", "yongshen": "土金"},
        "tags": tags or ["八字", "财运"],
        "category": category,
        "metadata": {"source": "test"},
        "created_at": 1700000000.0,
        "updated_at": 1700000000.0,
    }


# ══════════════════════════════════════════════════════════════
# SEED_CASES 常量
# ══════════════════════════════════════════════════════════════

class TestSeedCases:
    """SEED_CASES 常量测试"""

    def test_seed_cases_count(self):
        """种子数据应有 5 条记录"""
        assert len(SEED_CASES) == 5

    def test_seed_cases_structure(self):
        """每条种子数据都包含必要字段"""
        for case in SEED_CASES:
            assert "name" in case
            assert "bazi_data" in case
            assert "analysis" in case
            assert "tags" in case
            assert "category" in case
            assert "metadata" in case
            assert isinstance(case["tags"], list)
            assert isinstance(case["bazi_data"], dict)
            assert isinstance(case["analysis"], dict)

    def test_seed_cases_have_day_master(self):
        """每条种子案例的 bazi_data 都包含 day_master"""
        for case in SEED_CASES:
            assert "day_master" in case["bazi_data"]

    def test_seed_cases_all_bazi_category(self):
        """所有种子案例的分类都是 bazi"""
        for case in SEED_CASES:
            assert case["category"] == "bazi"


# ══════════════════════════════════════════════════════════════
# CaseRepository.__init__ / seed
# ══════════════════════════════════════════════════════════════

class TestCaseRepositoryInit:
    """初始化与播种测试"""

    def test_init_default(self):
        """新建仓库 _seeded 应为 False"""
        repo = CaseRepository()
        assert repo._seeded is False

    def test_seed_not_persistent_returns_5(self):
        """非持久化模式下 seed() 返回 5（种子数量），但不用数据库"""
        repo = CaseRepository()
        with patch("tengod.case_repository.is_persistent", return_value=False):
            result = repo.seed()
            assert result == 5
            assert repo._seeded is True

    def test_seed_already_seeded_returns_0(self):
        """已播种的仓库再次 seed 返回 0"""
        repo = CaseRepository()
        with patch("tengod.case_repository.is_persistent", return_value=False):
            repo.seed()
            result = repo.seed()
            assert result == 0

    def test_seed_persistent_with_existing_cases_returns_0(self):
        """持久化模式下，数据库已有案例时不播种"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.count_cases.return_value = 3
        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.seed()
            assert result == 0
            assert repo._seeded is True
            mock_db.insert_case.assert_not_called()

    def test_seed_persistent_empty_db(self):
        """持久化模式下，空数据库播种全部 5 条"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.count_cases.return_value = 0
        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.seed()
            assert result == 5
            assert repo._seeded is True
            assert mock_db.insert_case.call_count == 5


# ══════════════════════════════════════════════════════════════
# CaseRepository.add_case
# ══════════════════════════════════════════════════════════════

class TestAddCase:
    """add_case 测试"""

    def test_add_case_persistent(self):
        """持久化模式下 add_case 调用 db.insert_case 和 db.get_case"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        expected_case = make_case_row(case_id=42)
        mock_db.insert_case.return_value = 42
        mock_db.get_case.return_value = expected_case

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            case_data = {"name": "新案例", "category": "bazi"}
            result = repo.add_case(case_data)
            assert result == expected_case
            mock_db.insert_case.assert_called_once_with(case_data)
            mock_db.get_case.assert_called_once_with(42)

    def test_add_case_memory_mode(self):
        """内存模式下 add_case 生成时间戳 ID 并返回副本"""
        repo = CaseRepository()
        with patch("tengod.case_repository.is_persistent", return_value=False):
            case_data = {"name": "内存案例", "category": "test"}
            result = repo.add_case(case_data)
            assert "id" in result
            assert isinstance(result["id"], int)
            assert result["name"] == "内存案例"
            # 确认是 dict 副本（不是同一个对象）
            assert result is not case_data

    def test_add_case_empty_dict(self):
        """添加空字典案例"""
        repo = CaseRepository()
        with patch("tengod.case_repository.is_persistent", return_value=False):
            result = repo.add_case({})
            assert "id" in result
            assert isinstance(result["id"], int)


# ══════════════════════════════════════════════════════════════
# CaseRepository.get_case
# ══════════════════════════════════════════════════════════════

class TestGetCase:
    """get_case 测试"""

    def test_get_case_persistent_found(self):
        """持久化模式下找到案例"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        expected = make_case_row(case_id=1, name="找到的案例")
        mock_db.get_case.return_value = expected

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.get_case(1)
            assert result == expected
            mock_db.get_case.assert_called_once_with(1)

    def test_get_case_persistent_not_found(self):
        """持久化模式下未找到案例返回 None"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.get_case.return_value = None

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.get_case(999)
            assert result is None

    def test_get_case_memory_mode(self):
        """内存模式下 get_case 始终返回 None"""
        repo = CaseRepository()
        with patch("tengod.case_repository.is_persistent", return_value=False):
            result = repo.get_case(1)
            assert result is None

    def test_get_case_invalid_id_zero(self):
        """ID 为 0 时查询"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.get_case.return_value = None
        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.get_case(0)
            assert result is None

    def test_get_case_negative_id(self):
        """负数 ID 查询"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.get_case.return_value = None
        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.get_case(-1)
            assert result is None


# ══════════════════════════════════════════════════════════════
# CaseRepository.update_case
# ══════════════════════════════════════════════════════════════

class TestUpdateCase:
    """update_case 测试"""

    def test_update_case_persistent_success(self):
        """持久化模式下更新成功返回 True"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.update_case.return_value = True

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.update_case(1, {"name": "更新名称"})
            assert result is True
            mock_db.update_case.assert_called_once_with(1, {"name": "更新名称"})

    def test_update_case_persistent_not_found(self):
        """持久化模式下更新不存在的案例返回 False"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.update_case.return_value = False

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.update_case(999, {"name": "不存在"})
            assert result is False

    def test_update_case_memory_mode(self):
        """内存模式下 update_case 返回 False"""
        repo = CaseRepository()
        with patch("tengod.case_repository.is_persistent", return_value=False):
            result = repo.update_case(1, {"name": "x"})
            assert result is False


# ══════════════════════════════════════════════════════════════
# CaseRepository.delete_case
# ══════════════════════════════════════════════════════════════

class TestDeleteCase:
    """delete_case 测试"""

    def test_delete_case_persistent_success(self):
        """持久化模式下删除成功返回 True"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.delete_case.return_value = True

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.delete_case(1)
            assert result is True
            mock_db.delete_case.assert_called_once_with(1)

    def test_delete_case_persistent_not_found(self):
        """持久化模式下删除不存在案例返回 False"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.delete_case.return_value = False

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.delete_case(999)
            assert result is False

    def test_delete_case_memory_mode(self):
        """内存模式下 delete_case 返回 False"""
        repo = CaseRepository()
        with patch("tengod.case_repository.is_persistent", return_value=False):
            result = repo.delete_case(1)
            assert result is False


# ══════════════════════════════════════════════════════════════
# CaseRepository.list_cases
# ══════════════════════════════════════════════════════════════

class TestListCases:
    """list_cases 测试"""

    def test_list_cases_memory_mode(self):
        """内存模式下返回空结果"""
        repo = CaseRepository()
        with patch("tengod.case_repository.is_persistent", return_value=False):
            result = repo.list_cases()
            assert result["items"] == []
            assert result["total"] == 0
            assert result["page"] == 1
            assert result["page_size"] == 20
            assert result["total_pages"] == 0

    def test_list_cases_default_pagination(self):
        """默认分页参数"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = [make_case_row(1), make_case_row(2)]
        mock_db.count_cases.return_value = 2

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.list_cases()
            assert len(result["items"]) == 2
            assert result["total"] == 2
            assert result["page"] == 1
            assert result["page_size"] == 20
            assert result["total_pages"] == 1
            mock_db.list_cases.assert_called_once_with(
                limit=20, offset=0, category="", search=""
            )

    def test_list_cases_custom_page(self):
        """自定义页码和每页数量"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = [make_case_row(3)]
        mock_db.count_cases.return_value = 25

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.list_cases(page=3, page_size=10)
            assert result["page"] == 3
            assert result["page_size"] == 10
            assert result["total_pages"] == 3  # ceil(25/10)
            mock_db.list_cases.assert_called_once_with(
                limit=10, offset=20, category="", search=""
            )

    def test_list_cases_filter_category(self):
        """按分类过滤"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = [make_case_row(1, category="ziwei")]
        mock_db.count_cases.return_value = 1

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.list_cases(category="ziwei")
            assert len(result["items"]) == 1
            mock_db.list_cases.assert_called_once_with(
                limit=20, offset=0, category="ziwei", search=""
            )
            mock_db.count_cases.assert_called_once_with(category="ziwei", search="")

    def test_list_cases_filter_search(self):
        """按搜索关键词过滤"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = []
        mock_db.count_cases.return_value = 0

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.list_cases(search="财运")
            assert result["items"] == []
            mock_db.list_cases.assert_called_once_with(
                limit=20, offset=0, category="", search="财运"
            )

    def test_list_cases_filter_tag(self):
        """按标签过滤（内存中过滤）"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        items = [
            make_case_row(1, tags=["八字", "财运"]),
            make_case_row(2, tags=["八字", "事业"]),
            make_case_row(3, tags=["紫微", "财运"]),
        ]
        mock_db.list_cases.return_value = items
        mock_db.count_cases.return_value = 3

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.list_cases(tag="财运")
            assert len(result["items"]) == 2
            for item in result["items"]:
                assert "财运" in item["tags"]

    def test_list_cases_empty_result(self):
        """空结果的分页信息"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = []
        mock_db.count_cases.return_value = 0

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.list_cases(page=5, page_size=20)
            assert result["items"] == []
            assert result["total"] == 0
            assert result["total_pages"] == 1  # max(1, ...)

    def test_list_cases_total_pages_calculation(self):
        """total_pages 计算正确：ceil(total / page_size)"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = []
        mock_db.count_cases.return_value = 55

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.list_cases(page=1, page_size=20)
            assert result["total_pages"] == 3  # ceil(55/20)

    def test_list_cases_tag_filter_with_no_tags_field(self):
        """标签过滤时案例没有 tags 字段"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        items = [
            make_case_row(1, tags=None),
            make_case_row(2, tags=["财运"]),
        ]
        # 模拟没有 tags 字段的情况
        items[0] = {"id": 1, "name": "无标签", "category": "bazi"}
        mock_db.list_cases.return_value = items
        mock_db.count_cases.return_value = 2

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.list_cases(tag="财运")
            assert len(result["items"]) == 1


# ══════════════════════════════════════════════════════════════
# CaseRepository.search
# ══════════════════════════════════════════════════════════════

class TestSearch:
    """search 测试"""

    def test_search_persistent(self):
        """持久化模式下搜索"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        expected = [make_case_row(1, name="财运案例"), make_case_row(2, name="财运分析")]
        mock_db.list_cases.return_value = expected

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.search("财运")
            assert len(result) == 2
            mock_db.list_cases.assert_called_once_with(limit=20, search="财运")

    def test_search_persistent_custom_limit(self):
        """搜索时自定义 limit"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = [make_case_row(1)]

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.search("test", limit=5)
            assert len(result) == 1
            mock_db.list_cases.assert_called_once_with(limit=5, search="test")

    def test_search_memory_mode(self):
        """内存模式下搜索返回空列表"""
        repo = CaseRepository()
        with patch("tengod.case_repository.is_persistent", return_value=False):
            result = repo.search("anything")
            assert result == []

    def test_search_empty_query(self):
        """空查询字符串"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = [make_case_row(1), make_case_row(2)]

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.search("")
            assert len(result) == 2

    def test_search_no_results(self):
        """搜索无结果"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = []

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.search("不存在的关键词")
            assert result == []


# ══════════════════════════════════════════════════════════════
# CaseRepository.count
# ══════════════════════════════════════════════════════════════

class TestCount:
    """count 测试"""

    def test_count_persistent(self):
        """持久化模式下统计案例总数"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.count_cases.return_value = 42

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.count()
            assert result == 42
            mock_db.count_cases.assert_called_once_with(category="")

    def test_count_persistent_with_category(self):
        """按分类统计"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.count_cases.return_value = 10

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.count(category="bazi")
            assert result == 10
            mock_db.count_cases.assert_called_once_with(category="bazi")

    def test_count_memory_mode(self):
        """内存模式下 count 返回 0"""
        repo = CaseRepository()
        with patch("tengod.case_repository.is_persistent", return_value=False):
            result = repo.count()
            assert result == 0


# ══════════════════════════════════════════════════════════════
# CaseRepository.export_to_json
# ══════════════════════════════════════════════════════════════

class TestExportToJson:
    """export_to_json 测试"""

    def test_export_to_json(self):
        """导出案例到 JSON 文件"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        items = [make_case_row(1), make_case_row(2)]
        mock_db.list_cases.return_value = items
        mock_db.count_cases.return_value = 2

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            with patch("tengod.case_repository.is_persistent", return_value=True), \
                 patch("tengod.case_repository.get_db", return_value=mock_db):
                count = repo.export_to_json(tmp_path)
                assert count == 2

            # 验证文件内容
            with open(tmp_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["version"] == "2.11.0"
            assert "exported_at" in data
            assert data["count"] == 2
            assert len(data["cases"]) == 2
        finally:
            os.unlink(tmp_path)

    def test_export_to_json_empty(self):
        """导出空案例库"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = []
        mock_db.count_cases.return_value = 0

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            with patch("tengod.case_repository.is_persistent", return_value=True), \
                 patch("tengod.case_repository.get_db", return_value=mock_db):
                count = repo.export_to_json(tmp_path)
                assert count == 0

            with open(tmp_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["count"] == 0
            assert data["cases"] == []
        finally:
            os.unlink(tmp_path)


# ══════════════════════════════════════════════════════════════
# CaseRepository.import_from_json
# ══════════════════════════════════════════════════════════════

class TestImportFromJson:
    """import_from_json 测试"""

    def test_import_from_json(self):
        """从 JSON 文件导入案例"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.insert_case.return_value = 1
        mock_db.get_case.return_value = make_case_row(1)

        import_data = {
            "version": "2.11.0",
            "cases": [
                {
                    "name": "导入案例1",
                    "bazi_data": {"day_master": "甲木"},
                    "analysis": {"geju": "建禄格"},
                    "tags": ["八字"],
                    "category": "bazi",
                    "metadata": {"source": "import"},
                },
                {
                    "name": "导入案例2",
                    "bazi_data": {},
                    "analysis": {},
                    "tags": [],
                    "category": "general",
                    "metadata": {},
                },
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(import_data, f, ensure_ascii=False)
            tmp_path = f.name

        try:
            with patch("tengod.case_repository.is_persistent", return_value=True), \
                 patch("tengod.case_repository.get_db", return_value=mock_db):
                count = repo.import_from_json(tmp_path)
                assert count == 2
                assert mock_db.insert_case.call_count == 2
        finally:
            os.unlink(tmp_path)

    def test_import_from_json_file_not_exists(self):
        """导入不存在的文件返回 0"""
        repo = CaseRepository()
        count = repo.import_from_json("/tmp/nonexistent_file_xyz.json")
        assert count == 0

    def test_import_from_json_missing_fields(self):
        """导入缺少字段的案例，使用默认值填充"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.insert_case.return_value = 1
        mock_db.get_case.return_value = make_case_row(1)

        import_data = {
            "cases": [
                {"name": "只有名称"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(import_data, f, ensure_ascii=False)
            tmp_path = f.name

        try:
            with patch("tengod.case_repository.is_persistent", return_value=True), \
                 patch("tengod.case_repository.get_db", return_value=mock_db):
                count = repo.import_from_json(tmp_path)
                assert count == 1
                # 验证传入 add_case 的数据被清理过
                call_args = mock_db.insert_case.call_args[0][0]
                assert call_args["name"] == "只有名称"
                assert call_args["bazi_data"] == {}
                assert call_args["analysis"] == {}
                assert call_args["tags"] == []
                assert call_args["category"] == "general"
                assert call_args["metadata"] == {}
        finally:
            os.unlink(tmp_path)

    def test_import_from_json_memory_mode(self):
        """内存模式下导入"""
        repo = CaseRepository()
        import_data = {"cases": [{"name": "mem import"}]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(import_data, f, ensure_ascii=False)
            tmp_path = f.name

        try:
            with patch("tengod.case_repository.is_persistent", return_value=False):
                count = repo.import_from_json(tmp_path)
                # 内存模式下 add_case 仍然能工作
                assert count == 1
        finally:
            os.unlink(tmp_path)

    def test_import_from_json_no_cases_key(self):
        """JSON 中没有 cases 键"""
        repo = CaseRepository()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"other": "data"}, f, ensure_ascii=False)
            tmp_path = f.name

        try:
            with patch("tengod.case_repository.is_persistent", return_value=False):
                count = repo.import_from_json(tmp_path)
                assert count == 0
        finally:
            os.unlink(tmp_path)


# ══════════════════════════════════════════════════════════════
# CaseRepository.bulk_import
# ══════════════════════════════════════════════════════════════

class TestBulkImport:
    """bulk_import 测试"""

    def test_bulk_import(self):
        """批量导入多个案例"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.insert_case.side_effect = [1, 2, 3]
        mock_db.get_case.side_effect = [
            make_case_row(1), make_case_row(2), make_case_row(3),
        ]

        cases = [
            {"name": "批量1", "category": "bazi"},
            {"name": "批量2", "category": "ziwei"},
            {"name": "批量3", "category": "bazi"},
        ]

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            count = repo.bulk_import(cases)
            assert count == 3
            assert mock_db.insert_case.call_count == 3

    def test_bulk_import_empty(self):
        """批量导入空列表"""
        repo = CaseRepository()
        count = repo.bulk_import([])
        assert count == 0

    def test_bulk_import_memory_mode(self):
        """内存模式下批量导入"""
        repo = CaseRepository()
        cases = [{"name": "m1"}, {"name": "m2"}]
        with patch("tengod.case_repository.is_persistent", return_value=False):
            count = repo.bulk_import(cases)
            assert count == 2


# ══════════════════════════════════════════════════════════════
# CaseRepository.get_stats
# ══════════════════════════════════════════════════════════════

class TestGetStats:
    """get_stats 测试"""

    def test_get_stats_memory_mode(self):
        """内存模式下返回默认统计"""
        repo = CaseRepository()
        with patch("tengod.case_repository.is_persistent", return_value=False):
            stats = repo.get_stats()
            assert stats["total"] == 0
            assert stats["by_category"] == {}
            assert stats["by_tag"] == {}
            assert stats["source"] == "memory"

    def test_get_stats_persistent(self):
        """持久化模式下返回完整统计"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.count_cases.return_value = 3
        mock_db.list_cases.return_value = [
            make_case_row(1, category="bazi", tags=["八字", "财运"]),
            make_case_row(2, category="bazi", tags=["八字", "事业"]),
            make_case_row(3, category="ziwei", tags=["紫微"]),
        ]
        mock_db._db_path = "/tmp/test.db"

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            stats = repo.get_stats()
            assert stats["total"] == 3
            assert stats["source"] == "sqlite"
            assert stats["db_path"] == "/tmp/test.db"
            assert stats["by_category"] == {"bazi": 2, "ziwei": 1}
            assert stats["by_tag"] == {"八字": 2, "财运": 1, "事业": 1, "紫微": 1}

    def test_get_stats_persistent_empty(self):
        """持久化模式下空数据库统计"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.count_cases.return_value = 0
        mock_db.list_cases.return_value = []
        mock_db._db_path = "/tmp/empty.db"

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            stats = repo.get_stats()
            assert stats["total"] == 0
            assert stats["by_category"] == {}
            assert stats["by_tag"] == {}

    def test_get_stats_case_without_tags(self):
        """案例没有 tags 字段时不影响统计"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.count_cases.return_value = 1
        mock_db.list_cases.return_value = [
            {"id": 1, "name": "无标签", "category": "bazi"},
        ]
        mock_db._db_path = "/tmp/test.db"

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            stats = repo.get_stats()
            assert stats["total"] == 1
            assert stats["by_category"] == {"bazi": 1}
            assert stats["by_tag"] == {}


# ══════════════════════════════════════════════════════════════
# CaseRepository.get_similar_cases
# ══════════════════════════════════════════════════════════════

class TestGetSimilarCases:
    """get_similar_cases 测试"""

    def test_get_similar_cases_memory_mode(self):
        """内存模式下返回空列表"""
        repo = CaseRepository()
        with patch("tengod.case_repository.is_persistent", return_value=False):
            result = repo.get_similar_cases({"day_master": "辛金"})
            assert result == []

    def test_get_similar_cases_by_day_master(self):
        """按 day_master 匹配相似案例"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = [
            make_case_row(1, bazi_data={"day_master": "辛金", "gender": "male"},
                          tags=["八字", "财运"]),
            make_case_row(2, bazi_data={"day_master": "戊土", "gender": "female"},
                          tags=["八字", "食神"]),
            make_case_row(3, bazi_data={"day_master": "辛金", "gender": "female"},
                          tags=["八字", "事业"]),
        ]

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.get_similar_cases({"day_master": "辛金", "gender": "male"})
            assert len(result) > 0
            # 同 day_master + 同 gender 应排在最前
            top_score = result[0]["score"]
            assert result[0]["case"]["bazi_data"]["day_master"] == "辛金"

    def test_get_similar_cases_by_geju_keyword(self):
        """按 geju 关键词匹配标签"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = [
            make_case_row(1, bazi_data={"day_master": "甲木", "gender": "male"},
                          tags=["财旺", "身弱"]),
            make_case_row(2, bazi_data={"day_master": "乙木", "gender": "male"},
                          tags=["食神", "生财"]),
        ]

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.get_similar_cases(
                {"day_master": "甲木", "geju": "财旺身弱"}
            )
            assert len(result) > 0
            # 案例1 有 day_master 匹配 + "财旺" tag 匹配
            top_case = result[0]["case"]
            assert top_case["id"] == 1

    def test_get_similar_cases_custom_limit(self):
        """自定义返回数量限制"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        cases = [
            make_case_row(i, bazi_data={"day_master": "辛金", "gender": "male"},
                          tags=["八字"])
            for i in range(1, 11)
        ]
        mock_db.list_cases.return_value = cases

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.get_similar_cases(
                {"day_master": "辛金", "gender": "male"}, limit=3
            )
            assert len(result) == 3

    def test_get_similar_cases_no_match(self):
        """没有匹配的相似案例"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = [
            make_case_row(1, bazi_data={"day_master": "戊土", "gender": "female"},
                          tags=["八字"]),
        ]

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.get_similar_cases(
                {"day_master": "庚金", "gender": "male"}
            )
            assert result == []

    def test_get_similar_cases_empty_bazi_data(self):
        """空的 bazi_data 查询"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = [
            make_case_row(1),
        ]

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.get_similar_cases({})
            assert result == []  # 没有关键词匹配，score 全为 0

    def test_get_similar_cases_score_descending(self):
        """结果按 score 降序排列"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = [
            make_case_row(1, bazi_data={"day_master": "辛金", "gender": "female"},
                          tags=["财运"]),
            make_case_row(2, bazi_data={"day_master": "辛金", "gender": "male"},
                          tags=["财运"]),
            make_case_row(3, bazi_data={"day_master": "戊土", "gender": "male"},
                          tags=["财运"]),
        ]

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.get_similar_cases({"day_master": "辛金", "gender": "male"})
            scores = [r["score"] for r in result]
            assert scores == sorted(scores, reverse=True)

    def test_get_similar_cases_case_without_bazi_data(self):
        """案例没有 bazi_data 字段时，gender 均为 None 也会匹配（score=1）"""
        repo = CaseRepository()
        mock_db = make_mock_db()
        mock_db.list_cases.return_value = [
            {"id": 1, "name": "无八字", "category": "bazi", "tags": ["八字"]},
        ]

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            result = repo.get_similar_cases({"day_master": "辛金"})
            # 没有 bazi_data 字段 → day_master 不匹配，但 gender 同为 None，score=1
            assert len(result) == 1
            assert result[0]["score"] == 1
            assert result[0]["case"]["id"] == 1


# ══════════════════════════════════════════════════════════════
# 模块级函数: get_repository / reset_repository
# ══════════════════════════════════════════════════════════════

class TestModuleFunctions:
    """模块级函数测试"""

    def test_get_repository_returns_singleton(self):
        """get_repository 返回单例"""
        reset_repository()
        repo1 = get_repository()
        repo2 = get_repository()
        assert repo1 is repo2

    def test_get_repository_auto_seeds(self):
        """get_repository 自动播种"""
        reset_repository()
        with patch("tengod.case_repository.is_persistent", return_value=False):
            repo = get_repository()
            assert repo._seeded is True

    def test_reset_repository(self):
        """reset_repository 清除单例"""
        reset_repository()
        repo1 = get_repository()
        reset_repository()
        repo2 = get_repository()
        assert repo1 is not repo2

    def test_get_repository_persistent_mode(self):
        """持久化模式下 get_repository 自动播种"""
        reset_repository()
        mock_db = make_mock_db()
        mock_db.count_cases.return_value = 0
        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):
            repo = get_repository()
            assert repo._seeded is True
            mock_db.insert_case.call_count == 5


# ══════════════════════════════════════════════════════════════
# 集成场景测试
# ══════════════════════════════════════════════════════════════

class TestIntegrationScenarios:
    """CRUD 集成场景测试"""

    def test_full_crud_cycle(self):
        """完整的增删改查流程"""
        repo = CaseRepository()
        mock_db = make_mock_db()

        # 模拟一个可变的状态
        storage = {}

        def mock_insert(case):
            case_id = len(storage) + 1
            storage[case_id] = {**case, "id": case_id}
            return case_id

        def mock_get(case_id):
            return storage.get(case_id)

        def mock_update(case_id, data):
            if case_id not in storage:
                return False
            storage[case_id].update(data)
            return True

        def mock_delete(case_id):
            if case_id in storage:
                del storage[case_id]
                return True
            return False

        def mock_list(limit=20, offset=0, category="", search=""):
            items = list(storage.values())
            if category:
                items = [c for c in items if c.get("category") == category]
            return items[offset:offset + limit]

        def mock_count(category="", search=""):
            items = list(storage.values())
            if category:
                items = [c for c in items if c.get("category") == category]
            return len(items)

        mock_db.insert_case.side_effect = mock_insert
        mock_db.get_case.side_effect = mock_get
        mock_db.update_case.side_effect = mock_update
        mock_db.delete_case.side_effect = mock_delete
        mock_db.list_cases.side_effect = mock_list
        mock_db.count_cases.side_effect = mock_count

        with patch("tengod.case_repository.is_persistent", return_value=True), \
             patch("tengod.case_repository.get_db", return_value=mock_db):

            # Add
            case1 = repo.add_case({"name": "集成测试1", "category": "bazi"})
            case2 = repo.add_case({"name": "集成测试2", "category": "ziwei"})
            assert case1["id"] == 1
            assert case2["id"] == 2

            # Get
            assert repo.get_case(1) is not None
            assert repo.get_case(999) is None

            # Update
            assert repo.update_case(1, {"name": "更新后"}) is True
            assert repo.get_case(1)["name"] == "更新后"

            # Count
            assert repo.count() == 2
            assert repo.count(category="bazi") == 1

            # List
            result = repo.list_cases()
            assert len(result["items"]) == 2

            # Delete
            assert repo.delete_case(1) is True
            assert repo.get_case(1) is None
            assert repo.count() == 1

            # Delete non-existent
            assert repo.delete_case(999) is False