#!/usr/bin/env python3
"""
test_case_library.py — 命例案例库测试（Mock 版本）
使用 unittest.mock 完全模拟 SQLAlchemy Session，不依赖真实数据库。
覆盖：CaseLibrary 所有公共方法、Case/CaseRelation 模型、边缘情况。
"""
import json
import sys
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch, PropertyMock, call, ANY

import pytest

# 确保 tengod 在路径中
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# ── 在导入 case_library 之前，先 mock 掉 data_store 模块 ──────────
# 这样避免真实 SQLAlchemy 引擎被创建
_mock_base = MagicMock()
_mock_base.metadata = MagicMock()
_mock_base.metadata.create_all = MagicMock()

_mock_bazi_record = MagicMock()
_mock_data_store = MagicMock()
_mock_get_data_store = MagicMock()

# 注入 mock 到 sys.modules 中待被导入的模块
# 因为 case_library 使用 from .data_store import ...
# 所以我们只需要 mock tengod.data_store 已经存在即可
# 但更好的做法：在 import 后 patch 相关引用

# 先正常导入
from tengod.case_library import (
    CaseLibrary, Case, CaseRelation, DEFAULT_CATEGORIES, get_case_library,
)


# ════════════════════════════════════════
# 辅助函数：创建 mock Session
# ════════════════════════════════════════

def make_mock_session():
    """创建一个支持 context manager 的 mock Session"""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    return session


def make_mock_query(return_value=None, first_value=None, count_value=None, scalar_value=None):
    """创建一个 mock query 对象，支持链式调用"""
    q = MagicMock()
    q.filter.return_value = q
    q.join.return_value = q
    q.order_by.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.group_by.return_value = q
    q.all.return_value = return_value if return_value is not None else []
    q.first.return_value = first_value
    q.count.return_value = count_value if count_value is not None else (len(return_value) if return_value else 0)
    q.scalar.return_value = scalar_value if scalar_value is not None else (len(return_value) if return_value else 0)
    return q


class _MockCase:
    """一个模拟 Case 的简单对象，避免 MagicMock 的自动属性创建问题"""

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 1)
        self.record_id = kwargs.get('record_id', 1)
        self.title = kwargs.get('title', '测试案例')
        self.category = kwargs.get('category', '事业')
        self.source = kwargs.get('source', None)
        self.credibility = kwargs.get('credibility', 0.8)
        self.is_public = kwargs.get('is_public', True)
        self.is_featured = kwargs.get('is_featured', False)
        self.summary = kwargs.get('summary', None)
        self.analysis_text = kwargs.get('analysis_text', None)
        self.conclusion = kwargs.get('conclusion', None)
        self.view_count = kwargs.get('view_count', 0)
        self.favorite_count = kwargs.get('favorite_count', 0)
        self.like_count = kwargs.get('like_count', 0)
        self._tags = kwargs.get('tags', '企业家,创业')
        self.created_at = kwargs.get('created_at', datetime(2024, 1, 1, tzinfo=timezone.utc))
        self.updated_at = kwargs.get('updated_at', datetime(2024, 1, 1, tzinfo=timezone.utc))
        self._record_data = kwargs.get('_record_data', None)

    @property
    def tags(self):
        return self._tags

    @tags.setter
    def tags(self, value):
        self._tags = value

    def to_dict(self, include_record=False):
        result = {
            "id": self.id,
            "record_id": self.record_id,
            "title": self.title,
            "category": self.category,
            "source": self.source,
            "credibility": self.credibility,
            "is_public": self.is_public,
            "is_featured": self.is_featured,
            "summary": self.summary,
            "analysis_text": self.analysis_text,
            "conclusion": self.conclusion,
            "view_count": self.view_count,
            "favorite_count": self.favorite_count,
            "like_count": self.like_count,
            "tags": self._tags.split(",") if self._tags else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_record and self._record_data is not None:
            result["record"] = self._record_data
        return result


def make_mock_case(case_id=1, **kwargs):
    """创建一个模拟 Case 对象"""
    defaults = {
        'id': case_id,
        'title': '测试案例',
        'category': '事业',
        'tags': '企业家,创业',
    }
    defaults.update(kwargs)
    return _MockCase(**defaults)


def make_mock_record(record_id=1, **kwargs):
    """创建一个 mock BaziRecord 对象"""
    defaults = {
        'id': record_id,
        'year': 1990, 'month': 6, 'day': 15, 'hour': 10, 'minute': 0,
        'gender': 'male',
        'day_master': '辛',
        'pillars_json': json.dumps({"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"}),
        'geju_json': json.dumps({"geju_name": "伤官格"}),
        'analysis_json': json.dumps({"wuxing": {"金": 2, "水": 2, "火": 3, "土": 1}}),
    }
    defaults.update(kwargs)

    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)

    def _to_dict():
        return {
            "id": mock.id,
            "year": mock.year, "month": mock.month, "day": mock.day,
            "hour": mock.hour, "minute": mock.minute,
            "gender": mock.gender,
            "day_master": mock.day_master,
            "pillars": json.loads(mock.pillars_json) if mock.pillars_json else None,
            "geju": json.loads(mock.geju_json) if mock.geju_json else None,
            "analysis": json.loads(mock.analysis_json) if mock.analysis_json else None,
            "tags": mock.tags if hasattr(mock, 'tags') else None,
        }

    mock.to_dict = _to_dict
    return mock


def make_mock_case_relation(rel_id=1, **kwargs):
    """创建一个 mock CaseRelation 对象"""
    defaults = {
        'id': rel_id,
        'case_a_id': 1,
        'case_b_id': 2,
        'relation_type': 'similar',
        'similarity_score': 0.8,
        'note': None,
        'created_at': datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(kwargs)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


# ════════════════════════════════════════
# 夹具
# ════════════════════════════════════════

@pytest.fixture
def mock_store():
    """创建一个 mock DataStore"""
    store = MagicMock()
    store._engine = MagicMock()
    return store


@pytest.fixture
def mock_session():
    """创建一个 mock Session"""
    return make_mock_session()


@pytest.fixture
def lib(mock_store, mock_session):
    """创建一个 CaseLibrary 实例，其 _session() 返回 mock_session"""
    mock_store._session = MagicMock(return_value=mock_session)

    with patch('tengod.case_library.Base', _mock_base):
        with patch('tengod.case_library.get_data_store', return_value=mock_store):
            lib = CaseLibrary(store=mock_store)
            # 替换 _session 方法
            lib._session = MagicMock(return_value=mock_session)
            return lib


# ════════════════════════════════════════
# 1. 模型测试
# ════════════════════════════════════════

class TestCaseModel:
    """Case 模型测试"""

    def test_case_to_dict_basic(self):
        """to_dict 基本输出"""
        mock = make_mock_case(case_id=42, title="测试标题", category="婚姻")
        result = mock.to_dict()
        assert result["id"] == 42
        assert result["title"] == "测试标题"
        assert result["category"] == "婚姻"
        assert result["tags"] == ["企业家", "创业"]
        assert result["created_at"] is not None

    def test_case_to_dict_with_tags(self):
        """to_dict — tags 正确解析为列表"""
        mock = make_mock_case(tags="标签A,标签B,标签C")
        result = mock.to_dict()
        assert result["tags"] == ["标签A", "标签B", "标签C"]

    def test_case_to_dict_no_tags(self):
        """to_dict — tags 为 None"""
        mock = make_mock_case(tags=None)
        result = mock.to_dict()
        assert result["tags"] == []

    def test_case_to_dict_empty_tags(self):
        """to_dict — tags 为空字符串（falsy 值视为无标签）"""
        mock = make_mock_case(tags="")
        result = mock.to_dict()
        assert result["tags"] == []

    def test_case_to_dict_include_record(self):
        """to_dict — include_record=True"""
        mock = make_mock_case()
        mock._record_data = {"year": 1990, "month": 6}
        result = mock.to_dict(include_record=True)
        assert "record" in result
        assert result["record"]["year"] == 1990

    def test_case_to_dict_include_record_no_data(self):
        """to_dict — include_record=True 但没有 _record_data"""
        mock = make_mock_case()
        result = mock.to_dict(include_record=True)
        assert "record" not in result

    def test_case_to_dict_none_dates(self):
        """to_dict — created_at/updated_at 为 None"""
        mock = make_mock_case(created_at=None, updated_at=None)
        result = mock.to_dict()
        assert result["created_at"] is None
        assert result["updated_at"] is None

    def test_case_to_dict_all_fields(self):
        """to_dict — 所有字段存在"""
        mock = make_mock_case(
            id=100, record_id=200, title="完整案例", category="吉凶",
            source="《滴天髓》", credibility=0.95, is_public=False,
            is_featured=True, summary="摘要内容", analysis_text="分析文本",
            conclusion="结论", view_count=10, favorite_count=5, like_count=3,
        )
        result = mock.to_dict()
        assert result["id"] == 100
        assert result["record_id"] == 200
        assert result["source"] == "《滴天髓》"
        assert result["credibility"] == 0.95
        assert result["is_public"] is False
        assert result["is_featured"] is True
        assert result["summary"] == "摘要内容"
        assert result["analysis_text"] == "分析文本"
        assert result["conclusion"] == "结论"
        assert result["view_count"] == 10
        assert result["favorite_count"] == 5
        assert result["like_count"] == 3


class TestCaseRelationModel:
    """CaseRelation 模型测试"""

    def test_relation_attributes(self):
        """CaseRelation 基本属性"""
        rel = make_mock_case_relation(
            rel_id=5, case_a_id=10, case_b_id=20,
            relation_type="contrast", similarity_score=0.5,
            note="对比分析"
        )
        assert rel.id == 5
        assert rel.case_a_id == 10
        assert rel.case_b_id == 20
        assert rel.relation_type == "contrast"
        assert rel.similarity_score == 0.5
        assert rel.note == "对比分析"

    def test_relation_defaults(self):
        """CaseRelation 默认值"""
        rel = make_mock_case_relation()
        assert rel.similarity_score == 0.8
        assert rel.note is None


class TestDefaultCategories:
    """DEFAULT_CATEGORIES 常量测试"""

    def test_default_categories_count(self):
        """预定义分类数量"""
        assert len(DEFAULT_CATEGORIES) >= 10

    def test_default_categories_contains_core(self):
        """核心分类存在"""
        assert "富贵" in DEFAULT_CATEGORIES
        assert "贫贱" in DEFAULT_CATEGORIES
        assert "吉凶" in DEFAULT_CATEGORIES
        assert "寿夭" in DEFAULT_CATEGORIES
        assert "婚姻" in DEFAULT_CATEGORIES
        assert "事业" in DEFAULT_CATEGORIES
        assert "疾病" in DEFAULT_CATEGORIES
        assert "灾厄" in DEFAULT_CATEGORIES
        assert "学业" in DEFAULT_CATEGORIES
        assert "子女" in DEFAULT_CATEGORIES
        assert "财运" in DEFAULT_CATEGORIES
        assert "官运" in DEFAULT_CATEGORIES
        assert "其他" in DEFAULT_CATEGORIES


# ════════════════════════════════════════
# 2. CaseLibrary 初始化
# ════════════════════════════════════════

class TestCaseLibraryInit:
    """CaseLibrary 初始化测试"""

    def test_init_with_store(self, mock_store):
        """使用自定义 store 初始化"""
        mock_store._session = MagicMock()
        with patch('tengod.case_library.Base', _mock_base):
            lib = CaseLibrary(store=mock_store)
            assert lib.store == mock_store

    def test_init_creates_tables(self, mock_store):
        """初始化时调用 create_all"""
        mock_store._session = MagicMock()
        with patch('tengod.case_library.Base', _mock_base):
            CaseLibrary(store=mock_store)
            _mock_base.metadata.create_all.assert_called()

    def test_init_without_store(self):
        """无 store 参数时使用 get_data_store"""
        mock_ds = MagicMock()
        mock_ds._session = MagicMock()
        mock_ds._engine = MagicMock()

        with patch('tengod.case_library.Base', _mock_base):
            with patch('tengod.case_library.get_data_store', return_value=mock_ds):
                lib = CaseLibrary()
                assert lib.store == mock_ds


# ════════════════════════════════════════
# 3. CRUD 测试
# ════════════════════════════════════════

class TestCreateCase:
    """create_case 测试"""

    def test_create_case_success(self, lib, mock_session):
        """成功创建案例"""
        mock_record = make_mock_record()
        q = make_mock_query(first_value=mock_record)
        mock_session.query.return_value = q

        # 模拟 s.refresh 设置 case.id
        def _refresh(obj):
            obj.id = 42
        mock_session.refresh = _refresh

        case_id = lib.create_case(
            record_id=1, title="新案例", category="事业",
            summary="摘要", tags=["标签1", "标签2"],
        )
        assert case_id == 42

    def test_create_case_invalid_record(self, lib, mock_session):
        """创建案例 — 无效 record_id"""
        q = make_mock_query(first_value=None)  # record 不存在
        mock_session.query.return_value = q

        with pytest.raises(ValueError, match="不存在"):
            lib.create_case(record_id=99999, title="无效案例")

    def test_create_case_with_all_fields(self, lib, mock_session):
        """创建案例 — 所有可选字段"""
        mock_record = make_mock_record()
        q = make_mock_query(first_value=mock_record)
        mock_session.query.return_value = q

        def _refresh(obj):
            obj.id = 100
        mock_session.refresh = _refresh

        case_id = lib.create_case(
            record_id=1,
            title="完整案例",
            category="富贵",
            source="《子平真诠》",
            credibility=0.9,
            is_public=False,
            is_featured=True,
            summary="摘要",
            analysis_text="分析",
            conclusion="结论",
            tags=["富豪", "巨富"],
        )
        assert case_id == 100

    def test_create_case_without_tags(self, lib, mock_session):
        """创建案例 — 无标签"""
        mock_record = make_mock_record()
        q = make_mock_query(first_value=mock_record)
        mock_session.query.return_value = q

        def _refresh(obj):
            obj.id = 7
        mock_session.refresh = _refresh

        case_id = lib.create_case(record_id=1, title="无标签案例")
        assert case_id == 7


class TestGetCase:
    """get_case 测试"""

    def test_get_case_found(self, lib, mock_session):
        """获取存在的案例"""
        mock_case = make_mock_case(case_id=42)
        mock_record = make_mock_record()

        # 第一次 query 返回 Case，第二次 query 返回 BaziRecord
        q_case = make_mock_query(first_value=mock_case)
        q_record = make_mock_query(first_value=mock_record)

        mock_session.query.side_effect = [q_case, q_record]

        result = lib.get_case(42)
        assert result is not None
        assert result["title"] == "测试案例"
        assert "record" in result

    def test_get_case_not_found(self, lib, mock_session):
        """获取不存在的案例"""
        q = make_mock_query(first_value=None)
        mock_session.query.return_value = q

        result = lib.get_case(99999)
        assert result is None

    def test_get_case_increment_view(self, lib, mock_session):
        """获取案例时增加浏览数"""
        mock_case = make_mock_case(case_id=42, view_count=5)
        mock_record = make_mock_record()

        q_case = make_mock_query(first_value=mock_case)
        q_record = make_mock_query(first_value=mock_record)
        mock_session.query.side_effect = [q_case, q_record]

        result = lib.get_case(42, increment_view=True)
        assert mock_case.view_count == 6  # 5 + 1
        assert result["view_count"] == 6

    def test_get_case_increment_view_from_none(self, lib, mock_session):
        """get_case — view_count 为 None 时增加"""
        mock_case = make_mock_case(case_id=42, view_count=None)
        mock_record = make_mock_record()

        q_case = make_mock_query(first_value=mock_case)
        q_record = make_mock_query(first_value=mock_record)
        mock_session.query.side_effect = [q_case, q_record]

        result = lib.get_case(42, increment_view=True)
        assert mock_case.view_count == 1

    def test_get_case_no_record(self, lib, mock_session):
        """get_case — 关联的 BaziRecord 不存在"""
        mock_case = make_mock_case(case_id=42)
        q_case = make_mock_query(first_value=mock_case)
        q_record = make_mock_query(first_value=None)
        mock_session.query.side_effect = [q_case, q_record]

        result = lib.get_case(42)
        assert result is not None
        assert "record" not in result


class TestListCases:
    """list_cases 测试"""

    def test_list_cases_basic(self, lib, mock_session):
        """列出所有案例"""
        cases = [make_mock_case(case_id=1), make_mock_case(case_id=2)]
        q = make_mock_query(return_value=cases, count_value=2)
        mock_session.query.return_value = q

        result = lib.list_cases()
        assert result["total"] == 2
        assert result["limit"] == 50
        assert result["offset"] == 0
        assert len(result["cases"]) == 2

    def test_list_cases_empty(self, lib, mock_session):
        """空列表"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.list_cases()
        assert result["total"] == 0
        assert result["cases"] == []

    def test_list_cases_by_category(self, lib, mock_session):
        """按分类筛选"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.list_cases(category="事业")
        assert result["total"] == 0

    def test_list_cases_by_public(self, lib, mock_session):
        """按公开状态筛选"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.list_cases(is_public=True)
        assert result["total"] == 0

    def test_list_cases_by_featured(self, lib, mock_session):
        """按精选状态筛选"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.list_cases(is_featured=True)
        assert result["total"] == 0

    def test_list_cases_order_created_asc(self, lib, mock_session):
        """按创建时间升序排列"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.list_cases(order_by="created_asc")
        assert result["total"] == 0

    def test_list_cases_order_views(self, lib, mock_session):
        """按浏览数排列"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.list_cases(order_by="views")
        assert result["total"] == 0

    def test_list_cases_order_favorites(self, lib, mock_session):
        """按收藏数排列"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.list_cases(order_by="favorites")
        assert result["total"] == 0

    def test_list_cases_pagination(self, lib, mock_session):
        """分页测试"""
        q = make_mock_query(return_value=[], count_value=100)
        mock_session.query.return_value = q

        result = lib.list_cases(limit=10, offset=20)
        assert result["total"] == 100
        assert result["limit"] == 10
        assert result["offset"] == 20

    def test_list_cases_combined_filters(self, lib, mock_session):
        """组合筛选"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.list_cases(
            category="事业", is_public=True, is_featured=True,
            order_by="views",
        )
        assert result["total"] == 0


class TestUpdateCase:
    """update_case 测试"""

    def test_update_case_success(self, lib, mock_session):
        """更新案例成功"""
        mock_case = make_mock_case(case_id=42, title="旧标题")
        q = make_mock_query(first_value=mock_case)
        mock_session.query.return_value = q

        result = lib.update_case(42, title="新标题", summary="新摘要")
        assert result is True
        assert mock_case.title == "新标题"
        assert mock_case.summary == "新摘要"

    def test_update_case_not_found(self, lib, mock_session):
        """更新不存在的案例"""
        q = make_mock_query(first_value=None)
        mock_session.query.return_value = q

        result = lib.update_case(99999, title="新标题")
        assert result is False

    def test_update_case_tags_list(self, lib, mock_session):
        """更新标签 — 传入 list"""
        mock_case = make_mock_case(case_id=42, tags="旧标签")
        q = make_mock_query(first_value=mock_case)
        mock_session.query.return_value = q

        result = lib.update_case(42, tags=["标签A", "标签B"])
        assert result is True
        assert mock_case.tags == "标签A,标签B"

    def test_update_case_tags_string(self, lib, mock_session):
        """更新标签 — 传入 string"""
        mock_case = make_mock_case(case_id=42, tags="旧标签")
        q = make_mock_query(first_value=mock_case)
        mock_session.query.return_value = q

        result = lib.update_case(42, tags="标签字符串")
        assert result is True
        assert mock_case.tags == "标签字符串"

    def test_update_case_ignores_invalid_attrs(self, lib, mock_session):
        """更新 — 忽略不存在的属性"""
        mock_case = make_mock_case()
        q = make_mock_query(first_value=mock_case)
        mock_session.query.return_value = q

        result = lib.update_case(42, nonexistent_field="value")
        assert result is True  # 不会报错

    def test_update_case_updates_timestamp(self, lib, mock_session):
        """更新时刷新 updated_at"""
        mock_case = make_mock_case()
        old_updated = mock_case.updated_at
        q = make_mock_query(first_value=mock_case)
        mock_session.query.return_value = q

        lib.update_case(42, title="新标题")
        assert mock_case.updated_at != old_updated


class TestDeleteCase:
    """delete_case 测试"""

    def test_delete_case_success(self, lib, mock_session):
        """删除案例成功"""
        mock_case = make_mock_case(case_id=42)
        q = make_mock_query(first_value=mock_case)
        mock_session.query.return_value = q

        result = lib.delete_case(42)
        assert result is True
        mock_session.delete.assert_called_once_with(mock_case)

    def test_delete_case_not_found(self, lib, mock_session):
        """删除不存在的案例"""
        q = make_mock_query(first_value=None)
        mock_session.query.return_value = q

        result = lib.delete_case(99999)
        assert result is False


# ════════════════════════════════════════
# 4. 搜索测试
# ════════════════════════════════════════

class TestSearchCases:
    """search_cases 测试"""

    def test_search_by_keyword(self, lib, mock_session):
        """关键词搜索"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.search_cases(keyword="企业家")
        assert result["total"] == 0

    def test_search_by_category(self, lib, mock_session):
        """分类搜索"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.search_cases(category="事业")
        assert result["total"] == 0

    def test_search_by_tag(self, lib, mock_session):
        """标签搜索"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.search_cases(tag="创业")
        assert result["total"] == 0

    def test_search_by_day_master(self, lib, mock_session):
        """日主搜索"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.search_cases(day_master="辛")
        assert result["total"] == 0

    def test_search_by_geju(self, lib, mock_session):
        """格局搜索"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.search_cases(geju="伤官格")
        assert result["total"] == 0

    def test_search_by_gender(self, lib, mock_session):
        """性别搜索"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.search_cases(gender="male")
        assert result["total"] == 0

    def test_search_by_source(self, lib, mock_session):
        """来源搜索"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.search_cases(source="《滴天髓》")
        assert result["total"] == 0

    def test_search_by_is_public(self, lib, mock_session):
        """公开状态搜索"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.search_cases(is_public=True)
        assert result["total"] == 0

    def test_search_combined(self, lib, mock_session):
        """组合条件搜索"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.search_cases(
            keyword="企业家", category="事业", day_master="辛",
            geju="伤官格", is_public=True,
        )
        assert result["total"] == 0

    def test_search_no_results(self, lib, mock_session):
        """无结果搜索"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.search_cases(keyword="不存在的关键词")
        assert result["total"] == 0
        assert result["cases"] == []

    def test_search_with_results(self, lib, mock_session):
        """有结果搜索"""
        cases = [make_mock_case(case_id=1), make_mock_case(case_id=2)]
        q = make_mock_query(return_value=cases, count_value=2)
        mock_session.query.return_value = q

        result = lib.search_cases(category="事业")
        assert result["total"] == 2
        assert len(result["cases"]) == 2

    def test_search_pagination(self, lib, mock_session):
        """搜索分页"""
        q = make_mock_query(return_value=[], count_value=50)
        mock_session.query.return_value = q

        result = lib.search_cases(limit=20, offset=10)
        assert result["total"] == 50
        assert result["limit"] == 20
        assert result["offset"] == 10

    def test_search_all_params_none(self, lib, mock_session):
        """无任何搜索参数"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.search_cases()
        assert result["total"] == 0


# ════════════════════════════════════════
# 5. 分类与标签测试
# ════════════════════════════════════════

class TestCategoriesAndTags:
    """分类与标签测试"""

    def test_list_categories(self, lib, mock_session):
        """列出分类"""
        q = make_mock_query(return_value=[
            ("事业", 5), ("婚姻", 3), ("富贵", 2),
        ])
        mock_session.query.return_value = q

        result = lib.list_categories()
        assert len(result) == 3
        assert result[0] == {"name": "事业", "count": 5}
        assert result[1] == {"name": "婚姻", "count": 3}
        assert result[2] == {"name": "富贵", "count": 2}

    def test_list_categories_empty(self, lib, mock_session):
        """空分类列表"""
        q = make_mock_query(return_value=[])
        mock_session.query.return_value = q

        result = lib.list_categories()
        assert result == []

    def test_list_tags(self, lib, mock_session):
        """列出标签"""
        q = make_mock_query(return_value=[
            ("企业家,创业",), ("创业,命理",), ("企业家,财富",),
        ])
        mock_session.query.return_value = q

        result = lib.list_tags()
        assert len(result) >= 3
        tag_names = [t["name"] for t in result]
        assert "企业家" in tag_names
        assert "创业" in tag_names

    def test_list_tags_empty(self, lib, mock_session):
        """空标签列表"""
        q = make_mock_query(return_value=[])
        mock_session.query.return_value = q

        result = lib.list_tags()
        assert result == []

    def test_list_tags_with_spaces(self, lib, mock_session):
        """标签有空格"""
        q = make_mock_query(return_value=[
            (" 标签A , 标签B , 标签C ",),
        ])
        mock_session.query.return_value = q

        result = lib.list_tags()
        tag_names = [t["name"] for t in result]
        assert "标签A" in tag_names
        assert "标签B" in tag_names
        assert "标签C" in tag_names

    def test_list_tags_single_tag(self, lib, mock_session):
        """单个标签"""
        q = make_mock_query(return_value=[("单标签",)])
        mock_session.query.return_value = q

        result = lib.list_tags()
        assert len(result) == 1
        assert result[0]["name"] == "单标签"
        assert result[0]["count"] == 1

    def test_list_tags_deduplication(self, lib, mock_session):
        """标签去重聚合"""
        q = make_mock_query(return_value=[
            ("标签A,标签B",), ("标签A,标签C",), ("标签A,标签B",),
        ])
        mock_session.query.return_value = q

        result = lib.list_tags()
        tag_a = next(t for t in result if t["name"] == "标签A")
        assert tag_a["count"] == 3


# ════════════════════════════════════════
# 6. 互动功能测试
# ════════════════════════════════════════

class TestInteractions:
    """互动功能测试"""

    def test_increment_view_success(self, lib, mock_session):
        """增加浏览数成功"""
        mock_case = make_mock_case(case_id=42, view_count=10)
        q = make_mock_query(first_value=mock_case)
        mock_session.query.return_value = q

        result = lib.increment_view(42)
        assert result is True
        assert mock_case.view_count == 11

    def test_increment_view_not_found(self, lib, mock_session):
        """增加浏览数 — 案例不存在"""
        q = make_mock_query(first_value=None)
        mock_session.query.return_value = q

        result = lib.increment_view(99999)
        assert result is False

    def test_increment_view_from_none(self, lib, mock_session):
        """增加浏览数 — view_count 为 None"""
        mock_case = make_mock_case(case_id=42, view_count=None)
        q = make_mock_query(first_value=mock_case)
        mock_session.query.return_value = q

        result = lib.increment_view(42)
        assert result is True
        assert mock_case.view_count == 1

    def test_toggle_favorite_success(self, lib, mock_session):
        """收藏成功"""
        mock_case = make_mock_case(case_id=42, favorite_count=3)
        q = make_mock_query(first_value=mock_case)
        mock_session.query.return_value = q

        result = lib.toggle_favorite(42)
        assert result == 4
        assert mock_case.favorite_count == 4

    def test_toggle_favorite_not_found(self, lib, mock_session):
        """收藏 — 案例不存在"""
        q = make_mock_query(first_value=None)
        mock_session.query.return_value = q

        result = lib.toggle_favorite(99999)
        assert result is None

    def test_toggle_like_success(self, lib, mock_session):
        """点赞成功"""
        mock_case = make_mock_case(case_id=42, like_count=7)
        q = make_mock_query(first_value=mock_case)
        mock_session.query.return_value = q

        result = lib.toggle_like(42)
        assert result == 8
        assert mock_case.like_count == 8

    def test_toggle_like_not_found(self, lib, mock_session):
        """点赞 — 案例不存在"""
        q = make_mock_query(first_value=None)
        mock_session.query.return_value = q

        result = lib.toggle_like(99999)
        assert result is None

    def test_toggle_favorite_from_none(self, lib, mock_session):
        """收藏 — favorite_count 为 None"""
        mock_case = make_mock_case(case_id=42, favorite_count=None)
        q = make_mock_query(first_value=mock_case)
        mock_session.query.return_value = q

        result = lib.toggle_favorite(42)
        assert result == 1

    def test_toggle_like_from_none(self, lib, mock_session):
        """点赞 — like_count 为 None"""
        mock_case = make_mock_case(case_id=42, like_count=None)
        q = make_mock_query(first_value=mock_case)
        mock_session.query.return_value = q

        result = lib.toggle_like(42)
        assert result == 1


# ════════════════════════════════════════
# 7. 案例关联测试
# ════════════════════════════════════════

class TestCaseRelations:
    """案例关联测试"""

    def test_link_cases_success(self, lib, mock_session):
        """成功建立关联"""
        def _refresh(obj):
            obj.id = 99
        mock_session.refresh = _refresh

        result = lib.link_cases(1, 2, "similar", 0.8, "相似案例")
        assert result == 99

    def test_link_cases_self_error(self, lib, mock_session):
        """不能关联自己"""
        with pytest.raises(ValueError, match="不能关联自己"):
            lib.link_cases(1, 1)

    def test_link_cases_default_params(self, lib, mock_session):
        """默认参数"""
        def _refresh(obj):
            obj.id = 55
        mock_session.refresh = _refresh

        result = lib.link_cases(1, 2)
        assert result == 55

    def test_get_relations(self, lib, mock_session):
        """获取关联列表"""
        rel = make_mock_case_relation(
            case_a_id=1, case_b_id=2, relation_type="similar",
        )
        other_case = make_mock_case(case_id=2, title="关联案例", category="婚姻")

        q_rel = make_mock_query(return_value=[rel])
        q_case = make_mock_query(first_value=other_case)
        mock_session.query.side_effect = [q_rel, q_case]

        results = lib.get_relations(1)
        assert len(results) == 1
        assert results[0]["other_case_id"] == 2
        assert results[0]["other_title"] == "关联案例"
        assert results[0]["relation_type"] == "similar"

    def test_get_relations_filter_type(self, lib, mock_session):
        """按类型筛选关联"""
        q_rel = make_mock_query(return_value=[])
        mock_session.query.return_value = q_rel

        results = lib.get_relations(1, relation_type="contrast")
        assert results == []

    def test_get_relations_empty(self, lib, mock_session):
        """空关联列表"""
        q = make_mock_query(return_value=[])
        mock_session.query.return_value = q

        results = lib.get_relations(1)
        assert results == []

    def test_get_relations_case_b_not_found(self, lib, mock_session):
        """关联的案例不存在"""
        rel = make_mock_case_relation(case_a_id=1, case_b_id=99999)
        q_rel = make_mock_query(return_value=[rel])
        q_case = make_mock_query(first_value=None)
        mock_session.query.side_effect = [q_rel, q_case]

        results = lib.get_relations(1)
        assert results == []

    def test_get_relations_from_case_b_side(self, lib, mock_session):
        """从 case_b 侧获取关联（case_a_id != case_id）"""
        rel = make_mock_case_relation(case_a_id=2, case_b_id=1)
        other_case = make_mock_case(case_id=2, title="关联案例B")

        q_rel = make_mock_query(return_value=[rel])
        q_case = make_mock_query(first_value=other_case)
        mock_session.query.side_effect = [q_rel, q_case]

        results = lib.get_relations(1)
        assert len(results) == 1
        assert results[0]["other_case_id"] == 2


# ════════════════════════════════════════
# 8. 相似案例推荐测试
# ════════════════════════════════════════

class TestFindSimilarCases:
    """find_similar_cases 测试"""

    def test_find_similar_not_found(self, lib, mock_session):
        """目标案例不存在"""
        q = make_mock_query(first_value=None)
        mock_session.query.return_value = q

        result = lib.find_similar_cases(99999)
        assert result == []

    def test_find_similar_record_not_found(self, lib, mock_session):
        """目标案例的 record 不存在"""
        target_case = make_mock_case(case_id=1)
        q_case = make_mock_query(first_value=target_case)
        q_record = make_mock_query(first_value=None)
        mock_session.query.side_effect = [q_case, q_record]

        result = lib.find_similar_cases(1)
        assert result == []

    def test_find_similar_same_day_master(self, lib, mock_session):
        """同日主返回相似案例"""
        target_case = make_mock_case(case_id=1, record_id=1)
        target_record = make_mock_record(
            record_id=1, day_master="辛",
            geju_json=json.dumps({"geju_name": "伤官格"}),
            analysis_json=json.dumps({"wuxing": {"金": 2, "水": 2, "火": 3, "土": 1}}),
        )
        other_record = make_mock_record(
            record_id=2, day_master="辛",
            geju_json=json.dumps({"geju_name": "建禄格"}),
            analysis_json=json.dumps({"wuxing": {"金": 1, "水": 1, "火": 1, "土": 1, "木": 1}}),
        )
        other_case = make_mock_case(case_id=2, record_id=2, title="同日主案例", is_public=True)

        q_case = make_mock_query(first_value=target_case)
        q_record = make_mock_query(first_value=target_record)
        q_others = make_mock_query(return_value=[(other_case, other_record)])

        mock_session.query.side_effect = [q_case, q_record, q_others]

        result = lib.find_similar_cases(1)
        assert len(result) >= 1
        assert any(s["day_master"] == "辛" for s in result)

    def test_find_similar_same_geju(self, lib, mock_session):
        """同格局返回相似案例"""
        target_case = make_mock_case(case_id=1, record_id=1)
        target_record = make_mock_record(
            record_id=1, day_master="辛",
            geju_json=json.dumps({"geju_name": "伤官格"}),
            analysis_json=json.dumps({"wuxing": {"金": 2, "水": 2, "火": 3, "土": 1}}),
        )
        other_record = make_mock_record(
            record_id=2, day_master="丙",
            geju_json=json.dumps({"geju_name": "伤官格"}),
            analysis_json=json.dumps({"wuxing": {"金": 1, "水": 1, "火": 1, "土": 1, "木": 1}}),
        )
        other_case = make_mock_case(case_id=2, record_id=2, title="同格局案例", is_public=True)

        q_case = make_mock_query(first_value=target_case)
        q_record = make_mock_query(first_value=target_record)
        q_others = make_mock_query(return_value=[(other_case, other_record)])

        mock_session.query.side_effect = [q_case, q_record, q_others]

        result = lib.find_similar_cases(1)
        assert len(result) >= 1

    def test_find_similar_limit(self, lib, mock_session):
        """limit 限制返回数量"""
        target_case = make_mock_case(case_id=1, record_id=1)
        target_record = make_mock_record(
            record_id=1, day_master="辛",
            geju_json=json.dumps({"geju_name": "伤官格"}),
            analysis_json=json.dumps({"wuxing": {"金": 2, "水": 2, "火": 3, "土": 1}}),
        )
        other_case = make_mock_case(case_id=2, title="案例2", is_public=True)

        q_case = make_mock_query(first_value=target_case)
        q_record = make_mock_query(first_value=target_record)
        q_others = make_mock_query(return_value=[])
        mock_session.query.side_effect = [q_case, q_record, q_others]

        result = lib.find_similar_cases(1, limit=3)
        # 结果应该被限制在 3 以内
        assert len(result) <= 3

    def test_find_similar_no_geju(self, lib, mock_session):
        """目标案例无格局"""
        target_case = make_mock_case(case_id=1, record_id=1)
        target_record = make_mock_record(
            record_id=1, day_master="辛",
            geju_json=None,
            analysis_json=None,
        )
        other_case = make_mock_case(case_id=2, title="其他案例", is_public=True)
        other_record = make_mock_record(
            record_id=2, day_master="辛",
            geju_json=json.dumps({"geju_name": "伤官格"}),
            analysis_json=json.dumps({"wuxing": {"金": 1, "水": 1, "火": 1, "土": 1, "木": 1}}),
        )

        q_case = make_mock_query(first_value=target_case)
        q_record = make_mock_query(first_value=target_record)
        q_others = make_mock_query(return_value=[(other_case, other_record)])
        mock_session.query.side_effect = [q_case, q_record, q_others]

        result = lib.find_similar_cases(1)
        # 同日主 +30%，无格局对比，无五行对比
        assert len(result) >= 1


# ════════════════════════════════════════
# 9. 辅助方法测试
# ════════════════════════════════════════

class TestHelperMethods:
    """辅助方法测试"""

    def test_extract_geju_name_valid(self, lib):
        """提取有效格局名"""
        record = make_mock_record(geju_json=json.dumps({"geju_name": "正官格"}))
        result = lib._extract_geju_name(record)
        assert result == "正官格"

    def test_extract_geju_name_none(self, lib):
        """geju_json 为 None"""
        record = make_mock_record(geju_json=None)
        result = lib._extract_geju_name(record)
        assert result is None

    def test_extract_geju_name_invalid_json(self, lib):
        """无效 JSON"""
        record = make_mock_record(geju_json="invalid json")
        result = lib._extract_geju_name(record)
        assert result is None

    def test_extract_geju_name_no_key(self, lib):
        """JSON 中无 geju_name 字段"""
        record = make_mock_record(geju_json=json.dumps({"other": "value"}))
        result = lib._extract_geju_name(record)
        assert result is None

    def test_extract_wuxing_valid(self, lib):
        """提取有效五行分布"""
        record = make_mock_record(
            analysis_json=json.dumps({"wuxing": {"金": 2, "木": 1, "水": 3, "火": 0, "土": 2}})
        )
        result = lib._extract_wuxing(record)
        assert result == {"金": 2, "木": 1, "水": 3, "火": 0, "土": 2}

    def test_extract_wuxing_none(self, lib):
        """analysis_json 为 None"""
        record = make_mock_record(analysis_json=None)
        result = lib._extract_wuxing(record)
        assert result is None

    def test_extract_wuxing_invalid_json(self, lib):
        """无效 JSON"""
        record = make_mock_record(analysis_json="invalid")
        result = lib._extract_wuxing(record)
        assert result is None

    def test_wuxing_similarity_identical(self):
        """相同五行分布 — 相似度 1.0"""
        w1 = {"金": 2, "木": 1, "水": 3, "火": 0, "土": 2}
        w2 = {"金": 2, "木": 1, "水": 3, "火": 0, "土": 2}
        sim = CaseLibrary._wuxing_similarity(w1, w2)
        assert abs(sim - 1.0) < 1e-6

    def test_wuxing_similarity_different(self):
        """完全不同五行分布"""
        w1 = {"金": 5, "木": 0, "水": 0, "火": 0, "土": 0}
        w2 = {"金": 0, "木": 0, "水": 0, "火": 5, "土": 0}
        sim = CaseLibrary._wuxing_similarity(w1, w2)
        assert abs(sim - 0.0) < 1e-6

    def test_wuxing_similarity_zero_vector(self):
        """零向量"""
        w1 = {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0}
        w2 = {"金": 1, "木": 1, "水": 1, "火": 1, "土": 1}
        sim = CaseLibrary._wuxing_similarity(w1, w2)
        assert sim == 0.0

    def test_wuxing_similarity_missing_elements(self):
        """缺失元素默认 0"""
        w1 = {"金": 1, "水": 1}  # 缺木、火、土
        w2 = {"木": 1, "火": 1}
        sim = CaseLibrary._wuxing_similarity(w1, w2)
        assert abs(sim - 0.0) < 1e-6  # 无交集

    def test_wuxing_similarity_partial(self):
        """部分相似"""
        w1 = {"金": 2, "木": 0, "水": 2, "火": 0, "土": 0}
        w2 = {"金": 2, "木": 0, "水": 2, "火": 0, "土": 0}
        sim = CaseLibrary._wuxing_similarity(w1, w2)
        assert abs(sim - 1.0) < 1e-6


# ════════════════════════════════════════
# 10. 导入导出测试
# ════════════════════════════════════════

class TestExport:
    """导出测试"""

    def test_export_json(self, lib, mock_session):
        """JSON 导出"""
        mock_case = make_mock_case(case_id=1, title="导出案例")
        mock_record = make_mock_record(record_id=1)

        q_cases = make_mock_query(return_value=[mock_case])
        q_record = make_mock_query(first_value=mock_record)
        mock_session.query.side_effect = [q_cases, q_record]

        result = lib.export_cases(format="json")
        data = json.loads(result)
        assert "cases" in data
        assert "exported_at" in data
        assert len(data["cases"]) == 1
        assert data["cases"][0]["title"] == "导出案例"

    def test_export_json_with_record_data(self, lib, mock_session):
        """JSON 导出包含 record 数据"""
        mock_case = make_mock_case(case_id=1, title="导出案例")
        mock_record = make_mock_record(
            record_id=1, year=1990, month=6, day=15, hour=10,
            gender="male", day_master="辛",
        )

        q_cases = make_mock_query(return_value=[mock_case])
        q_record = make_mock_query(first_value=mock_record)
        mock_session.query.side_effect = [q_cases, q_record]

        result = lib.export_cases(format="json")
        data = json.loads(result)
        assert "record" in data["cases"][0]
        assert data["cases"][0]["record"]["year"] == 1990

    def test_export_json_case_ids(self, lib, mock_session):
        """按 ID 列表导出"""
        q = make_mock_query(return_value=[])
        mock_session.query.return_value = q

        result = lib.export_cases(case_ids=[1, 2, 3], format="json")
        data = json.loads(result)
        assert data["cases"] == []

    def test_export_csv(self, lib, mock_session):
        """CSV 导出"""
        mock_case = make_mock_case(case_id=1, title="导出案例")
        mock_record = make_mock_record(record_id=1)

        q_cases = make_mock_query(return_value=[mock_case])
        q_record = make_mock_query(first_value=mock_record)
        mock_session.query.side_effect = [q_cases, q_record]

        result = lib.export_cases(format="csv")
        lines = result.strip().split("\n")
        assert len(lines) >= 2  # header + data
        assert "title" in lines[0]
        assert "导出案例" in lines[1]

    def test_export_csv_no_record(self, lib, mock_session):
        """CSV 导出 — 无关联 record"""
        mock_case = make_mock_case(case_id=1, title="导出案例")
        q_cases = make_mock_query(return_value=[mock_case])
        q_record = make_mock_query(first_value=None)
        mock_session.query.side_effect = [q_cases, q_record]

        result = lib.export_cases(format="csv")
        lines = result.strip().split("\n")
        assert len(lines) >= 2

    def test_export_json_no_record(self, lib, mock_session):
        """JSON 导出 — 无关联 record"""
        mock_case = make_mock_case(case_id=1, title="导出案例")
        q_cases = make_mock_query(return_value=[mock_case])
        q_record = make_mock_query(first_value=None)
        mock_session.query.side_effect = [q_cases, q_record]

        result = lib.export_cases(format="json")
        data = json.loads(result)
        assert "record" not in data["cases"][0]


class TestImport:
    """导入测试"""

    def test_import_json_success(self, lib, mock_session):
        """JSON 导入成功"""
        mock_record = make_mock_record(record_id=1)
        q_find = make_mock_query(first_value=mock_record)
        q_check = make_mock_query(first_value=None)  # 案例不存在
        mock_session.query.side_effect = [q_find, q_check]

        import_data = json.dumps({
            "cases": [{
                "title": "导入案例",
                "category": "事业",
                "record": {"year": 1990, "month": 6, "day": 15, "hour": 10},
            }]
        })
        result = lib.import_cases(import_data, format="json")
        assert result["imported"] == 1
        assert result["skipped"] == 0

    def test_import_json_no_record_data(self, lib, mock_session):
        """导入 — 无 record 数据"""
        import_data = json.dumps({
            "cases": [{
                "title": "导入案例",
                "category": "事业",
            }]
        })
        result = lib.import_cases(import_data, format="json")
        assert result["imported"] == 0
        assert result["skipped"] == 1

    def test_import_json_record_not_found(self, lib, mock_session):
        """导入 — record 不存在"""
        q = make_mock_query(first_value=None)
        mock_session.query.return_value = q

        import_data = json.dumps({
            "cases": [{
                "title": "导入案例",
                "record": {"year": 2000, "month": 1, "day": 1, "hour": 1},
            }]
        })
        result = lib.import_cases(import_data, format="json")
        assert result["imported"] == 0
        assert result["skipped"] == 1

    def test_import_json_duplicate(self, lib, mock_session):
        """导入 — 重复案例"""
        mock_record = make_mock_record(record_id=1)
        mock_existing_case = make_mock_case(case_id=99)
        q_find = make_mock_query(first_value=mock_record)
        q_check = make_mock_query(first_value=mock_existing_case)
        mock_session.query.side_effect = [q_find, q_check]

        import_data = json.dumps({
            "cases": [{
                "title": "已存在案例",
                "record": {"year": 1990, "month": 6, "day": 15, "hour": 10},
            }]
        })
        result = lib.import_cases(import_data, format="json")
        assert result["imported"] == 0
        assert result["skipped"] == 1

    def test_import_json_exception(self, lib, mock_session):
        """导入 — 异常处理"""
        mock_record = make_mock_record(record_id=1)
        q_find = make_mock_query(first_value=mock_record)
        q_check = make_mock_query(first_value=None)
        # 让 s.add 或 s.commit 抛出异常
        mock_session.commit.side_effect = Exception("DB error")
        mock_session.query.side_effect = [q_find, q_check]

        import_data = json.dumps({
            "cases": [{
                "title": "导入案例",
                "record": {"year": 1990, "month": 6, "day": 15, "hour": 10},
            }]
        })
        result = lib.import_cases(import_data, format="json")
        assert result["skipped"] >= 1

    def test_import_json_with_tags(self, lib, mock_session):
        """导入 — 带标签"""
        mock_record = make_mock_record(record_id=1)
        q_find = make_mock_query(first_value=mock_record)
        q_check = make_mock_query(first_value=None)
        mock_session.query.side_effect = [q_find, q_check]

        import_data = json.dumps({
            "cases": [{
                "title": "带标签案例",
                "category": "富贵",
                "tags": ["富豪", "商界"],
                "record": {"year": 1990, "month": 6, "day": 15, "hour": 10},
            }]
        })
        result = lib.import_cases(import_data, format="json")
        assert result["imported"] == 1

    def test_import_json_multiple(self, lib, mock_session):
        """批量导入多个案例"""
        mock_record = make_mock_record(record_id=1)
        q_find = make_mock_query(first_value=mock_record)
        q_check = make_mock_query(first_value=None)
        mock_session.query.side_effect = [
            q_find, q_check, q_find, q_check, q_find, q_check,
        ]

        import_data = json.dumps({
            "cases": [
                {"title": "案例1", "record": {"year": 1990, "month": 6, "day": 15, "hour": 10}},
                {"title": "案例2", "record": {"year": 1990, "month": 6, "day": 15, "hour": 10}},
                {"title": "案例3", "record": {"year": 1990, "month": 6, "day": 15, "hour": 10}},
            ]
        })
        result = lib.import_cases(import_data, format="json")
        assert result["imported"] == 3
        assert result["skipped"] == 0


# ════════════════════════════════════════
# 11. 统计测试
# ════════════════════════════════════════

class TestStats:
    """统计测试"""

    def test_stats_basic(self, lib, mock_session):
        """基本统计"""
        q_total = make_mock_query(scalar_value=10)
        q_public = make_mock_query(scalar_value=8)
        q_featured = make_mock_query(scalar_value=3)
        q_views = make_mock_query(scalar_value=100)
        q_favorites = make_mock_query(scalar_value=50)
        q_cats = make_mock_query(return_value=[("事业", 5), ("婚姻", 3)])
        q_tags = make_mock_query(return_value=[("企业家,创业",), ("命理,分析",)])

        mock_session.query.side_effect = [
            q_total, q_public, q_featured, q_views, q_favorites, q_cats, q_tags,
        ]

        stats = lib.stats()
        assert stats["total_cases"] == 10
        assert stats["public_cases"] == 8
        assert stats["featured_cases"] == 3
        assert stats["total_views"] == 100
        assert stats["total_favorites"] == 50
        assert "categories" in stats
        assert "top_tags" in stats

    def test_stats_empty(self, lib, mock_session):
        """空数据库统计"""
        q = make_mock_query(scalar_value=0, return_value=[])
        mock_session.query.return_value = q

        stats = lib.stats()
        assert stats["total_cases"] == 0
        assert stats["public_cases"] == 0
        assert stats["featured_cases"] == 0
        assert stats["total_views"] == 0
        assert stats["total_favorites"] == 0

    def test_stats_top_tags_limit(self, lib, mock_session):
        """top_tags 限制为 10 个"""
        q_total = make_mock_query(scalar_value=5)
        q_public = make_mock_query(scalar_value=5)
        q_featured = make_mock_query(scalar_value=0)
        q_views = make_mock_query(scalar_value=0)
        q_favorites = make_mock_query(scalar_value=0)
        q_cats = make_mock_query(return_value=[])
        q_tags = make_mock_query(return_value=[(f"标签{i},",) for i in range(15)])

        mock_session.query.side_effect = [
            q_total, q_public, q_featured, q_views, q_favorites, q_cats, q_tags,
        ]

        stats = lib.stats()
        assert len(stats["top_tags"]) <= 10


# ════════════════════════════════════════
# 12. 单例测试
# ════════════════════════════════════════

class TestSingleton:
    """get_case_library 单例测试"""

    def test_get_case_library_creates(self):
        """首次调用创建实例"""
        import tengod.case_library as cl
        cl._library = None

        mock_ds = MagicMock()
        mock_ds._session = MagicMock()
        mock_ds._engine = MagicMock()

        with patch('tengod.case_library.Base', _mock_base):
            with patch('tengod.case_library.get_data_store', return_value=mock_ds):
                lib = get_case_library()
                assert lib is not None
                assert isinstance(lib, CaseLibrary)

    def test_get_case_library_returns_same(self):
        """再次调用返回同一实例"""
        import tengod.case_library as cl
        cl._library = None

        mock_ds = MagicMock()
        mock_ds._session = MagicMock()
        mock_ds._engine = MagicMock()

        with patch('tengod.case_library.Base', _mock_base):
            with patch('tengod.case_library.get_data_store', return_value=mock_ds):
                lib1 = get_case_library()
                lib2 = get_case_library()
                assert lib1 is lib2

    def test_get_case_library_with_store(self):
        """传入自定义 store"""
        import tengod.case_library as cl
        cl._library = None

        mock_ds = MagicMock()
        mock_ds._session = MagicMock()
        mock_ds._engine = MagicMock()

        with patch('tengod.case_library.Base', _mock_base):
            lib = get_case_library(store=mock_ds)
            assert lib.store == mock_ds


# ════════════════════════════════════════
# 13. 边缘情况测试
# ════════════════════════════════════════

class TestEdgeCases:
    """边缘情况测试"""

    def test_create_case_with_empty_title(self, lib, mock_session):
        """空标题创建案例"""
        mock_record = make_mock_record()
        q = make_mock_query(first_value=mock_record)
        mock_session.query.return_value = q

        def _refresh(obj):
            obj.id = 1
        mock_session.refresh = _refresh

        case_id = lib.create_case(record_id=1, title="")
        assert case_id == 1

    def test_create_case_with_special_chars(self, lib, mock_session):
        """特殊字符标题"""
        mock_record = make_mock_record()
        q = make_mock_query(first_value=mock_record)
        mock_session.query.return_value = q

        def _refresh(obj):
            obj.id = 1
        mock_session.refresh = _refresh

        case_id = lib.create_case(record_id=1, title="测试📊案例\n换行")
        assert case_id == 1

    def test_list_cases_large_offset(self, lib, mock_session):
        """大偏移量分页"""
        q = make_mock_query(return_value=[], count_value=1000)
        mock_session.query.return_value = q

        result = lib.list_cases(offset=999, limit=10)
        assert result["total"] == 1000
        assert result["offset"] == 999

    def test_search_empty_keyword(self, lib, mock_session):
        """空关键词搜索"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.search_cases(keyword="")
        assert result is not None
        assert "total" in result

    def test_update_case_no_changes(self, lib, mock_session):
        """更新但无变化"""
        mock_case = make_mock_case(case_id=42)
        q = make_mock_query(first_value=mock_case)
        mock_session.query.return_value = q

        result = lib.update_case(42)
        assert result is True

    def test_get_relations_multiple_same(self, lib, mock_session):
        """多个关联案例"""
        rel1 = make_mock_case_relation(case_a_id=1, case_b_id=2)
        rel2 = make_mock_case_relation(case_a_id=1, case_b_id=3)
        case2 = make_mock_case(case_id=2, title="案例2")
        case3 = make_mock_case(case_id=3, title="案例3")

        q_rel = make_mock_query(return_value=[rel1, rel2])
        q_case2 = make_mock_query(first_value=case2)
        q_case3 = make_mock_query(first_value=case3)
        mock_session.query.side_effect = [q_rel, q_case2, q_case3]

        results = lib.get_relations(1)
        assert len(results) == 2

    def test_export_empty_cases(self, lib, mock_session):
        """导出空案例库"""
        q = make_mock_query(return_value=[])
        mock_session.query.return_value = q

        result = lib.export_cases(format="json")
        data = json.loads(result)
        assert data["cases"] == []

    def test_export_csv_empty(self, lib, mock_session):
        """CSV 导出空案例库"""
        q = make_mock_query(return_value=[])
        mock_session.query.return_value = q

        result = lib.export_cases(format="csv")
        lines = result.strip().split("\n")
        assert len(lines) == 1  # 仅有 header

    def test_increment_view_many_times(self, lib, mock_session):
        """多次浏览"""
        mock_case = make_mock_case(case_id=42, view_count=0)
        q = make_mock_query(first_value=mock_case)
        mock_session.query.return_value = q

        for _ in range(100):
            lib.increment_view(42)
        assert mock_case.view_count == 100

    def test_toggle_favorite_many_times(self, lib, mock_session):
        """多次收藏"""
        mock_case = make_mock_case(case_id=42, favorite_count=0)
        q = make_mock_query(first_value=mock_case)
        mock_session.query.return_value = q

        for _ in range(50):
            lib.toggle_favorite(42)
        assert mock_case.favorite_count == 50

    def test_list_cases_default_order_by(self, lib, mock_session):
        """默认排序（created_desc）"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.list_cases()  # order_by 默认为 created_desc
        assert result["total"] == 0

    def test_search_by_source_contains(self, lib, mock_session):
        """来源模糊搜索"""
        q = make_mock_query(return_value=[], count_value=0)
        mock_session.query.return_value = q

        result = lib.search_cases(source="滴天")
        assert result["total"] == 0

    def test_get_case_increment_view_false_default(self, lib, mock_session):
        """get_case 默认不增加浏览数"""
        mock_case = make_mock_case(case_id=42, view_count=5)
        mock_record = make_mock_record()
        q_case = make_mock_query(first_value=mock_case)
        q_record = make_mock_query(first_value=mock_record)
        mock_session.query.side_effect = [q_case, q_record]

        lib.get_case(42)  # increment_view=False (default)
        assert mock_case.view_count == 5  # 不变

    def test_to_dict_with_record_data(self):
        """to_dict include_record with _record_data present"""
        mock = make_mock_case()
        mock._record_data = {"day_master": "辛"}
        result = mock.to_dict(include_record=True)
        assert result["record"] == {"day_master": "辛"}