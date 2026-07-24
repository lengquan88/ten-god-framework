#!/usr/bin/env python3
"""
case_comparator.py 测试套件
============================
覆盖: SimilarCase, ComparisonResult, CaseComparator, quick_compare
"""

import pytest

from tengod.case_comparator import (
    CaseComparator,
    ComparisonResult,
    SimilarCase,
    quick_compare,
)


# ═══════════════════════════════════════════════════════════
# SimilarCase 测试
# ═══════════════════════════════════════════════════════════

class TestSimilarCase:

    def test_creation(self):
        case = SimilarCase(
            case_id="case_001",
            similarity=0.85,
            bazi_summary="日主戊土",
            outcome="事业有成",
            tags=["身旺", "喜金水"],
            verified=True,
        )
        assert case.case_id == "case_001"
        assert case.similarity == 0.85
        assert case.bazi_summary == "日主戊土"
        assert case.verified is True

    def test_to_dict(self):
        case = SimilarCase(
            case_id="case_001",
            similarity=0.75,
            bazi_summary="test",
            tags=["tag1"],
            verified=False,
        )
        d = case.to_dict()
        assert d["case_id"] == "case_001"
        assert d["similarity"] == 0.75
        assert d["verified"] is False


# ═══════════════════════════════════════════════════════════
# ComparisonResult 测试
# ═══════════════════════════════════════════════════════════

class TestComparisonResult:

    def test_creation(self):
        cases = [SimilarCase(case_id="case_1", similarity=0.8)]
        result = ComparisonResult(
            source_case={"test": "data"},
            similar_cases=cases,
            similarity_stats={"count": 1},
            common_patterns=["pattern1"],
            differences=["diff1"],
            comparison_report="report text",
        )
        assert result.source_case == {"test": "data"}
        assert len(result.similar_cases) == 1
        assert result.comparison_report == "report text"

    def test_to_dict(self):
        cases = [SimilarCase(case_id="case_1", similarity=0.8)]
        result = ComparisonResult(
            source_case={"test": "data"},
            similar_cases=cases,
            similarity_stats={"count": 1},
            common_patterns=["pattern1"],
            differences=["diff1"],
            comparison_report="report text",
        )
        d = result.to_dict()
        assert d["source_case"] == {"test": "data"}
        assert len(d["similar_cases"]) == 1
        assert d["similar_cases"][0]["case_id"] == "case_1"


# ═══════════════════════════════════════════════════════════
# CaseComparator 测试
# ═══════════════════════════════════════════════════════════

class TestCaseComparator:

    @pytest.fixture
    def comparator(self):
        return CaseComparator(use_vector=False)

    def test_init_with_vector_fallback(self):
        cc = CaseComparator(use_vector=True)
        assert cc._use_vector is False

    def test_build_bazi_vector(self, comparator):
        bazi_data = {
            "pillars": {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚申"},
            "analysis": {"wuxing": {"木": 2, "火": 1, "土": 3, "金": 2, "水": 0}},
        }
        vector = comparator._build_bazi_vector(bazi_data)
        assert isinstance(vector, list)
        assert len(vector) > 0

    def test_cosine_similarity(self, comparator):
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert comparator._cosine_similarity(a, b) == 1.0

        c = [1.0, 0.0, 0.0]
        d = [0.0, 1.0, 0.0]
        assert comparator._cosine_similarity(c, d) == 0.0

    def test_find_similar(self, comparator):
        bazi_data = {
            "pillars": {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚申"},
            "analysis": {"wuxing": {"木": 2, "火": 1, "土": 3, "金": 2, "水": 0}},
        }
        similar = comparator.find_similar(bazi_data, top_k=3)
        assert isinstance(similar, list)
        assert len(similar) <= 3
        for case in similar:
            assert isinstance(case, SimilarCase)
            assert case.similarity >= 0.3

    def test_find_similar_empty_data(self, comparator):
        similar = comparator.find_similar({}, top_k=3)
        assert isinstance(similar, list)

    def test_find_similar_with_min_similarity(self, comparator):
        bazi_data = {
            "pillars": {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚申"},
            "analysis": {"wuxing": {"木": 2, "火": 1, "土": 3, "金": 2, "水": 0}},
        }
        similar = comparator.find_similar(bazi_data, top_k=5, min_similarity=0.8)
        for case in similar:
            assert case.similarity >= 0.8

    def test_generate_comparison_report(self, comparator):
        bazi_data = {
            "pillars": {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚申"},
            "analysis": {"wuxing": {"木": 2, "火": 1, "土": 3, "金": 2, "水": 0}},
        }
        similar = [
            SimilarCase(case_id="case_1", similarity=0.85, bazi_summary="日主戊土", verified=True),
            SimilarCase(case_id="case_2", similarity=0.70, bazi_summary="日主己土", verified=False),
        ]
        result = comparator.generate_comparison_report(bazi_data, similar)
        assert isinstance(result, ComparisonResult)
        assert isinstance(result.comparison_report, str)
        assert "源命盘" in result.comparison_report
        assert "案例对比分析报告" in result.comparison_report

    def test_generate_comparison_report_empty_cases(self, comparator):
        bazi_data = {"pillars": {"year": "甲子"}}
        result = comparator.generate_comparison_report(bazi_data, [])
        assert isinstance(result, ComparisonResult)
        assert result.similarity_stats["count"] == 0

    def test_extract_common_patterns(self, comparator):
        source = {
            "pillars": {"day": "戊辰"},
            "analysis": {"wuxing": {"土": 5, "金": 1}},
        }
        similar = [
            SimilarCase(case_id="case_1", similarity=0.8, bazi_summary="日主戊土"),
            SimilarCase(case_id="case_2", similarity=0.7, bazi_summary="日主戊土"),
            SimilarCase(case_id="case_3", similarity=0.6, bazi_summary="日主庚金"),
        ]
        patterns = comparator._extract_common_patterns(source, similar)
        assert isinstance(patterns, list)

    def test_analyze_differences(self, comparator):
        similar = [
            SimilarCase(case_id="case_1", similarity=0.85, outcome="好"),
            SimilarCase(case_id="case_2", similarity=0.35, outcome="差"),
        ]
        diffs = comparator._analyze_differences({}, similar)
        assert isinstance(diffs, list)
        assert len(diffs) > 0


# ═══════════════════════════════════════════════════════════
# quick_compare 测试
# ═══════════════════════════════════════════════════════════

class TestQuickCompare:

    def test_quick_compare(self):
        bazi_data = {
            "pillars": {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚申"},
            "analysis": {"wuxing": {"木": 2, "火": 1, "土": 3, "金": 2, "水": 0}},
        }
        result = quick_compare(bazi_data, top_k=3)
        assert isinstance(result, ComparisonResult)
        assert isinstance(result.comparison_report, str)
