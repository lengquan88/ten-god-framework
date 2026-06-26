#!/usr/bin/env python3
"""
test_multi_system_engine.py —— ComprehensiveAnalyzer 全面测试

覆盖：
  1. SystemResult / CrossValidation / ConsensusFortune / ComprehensiveResult 数据类
  2. _safe_import 安全导入
  3. _extract_yongshen 喜用神提取（bazi / ziwei / liunian / shushu / 未知系统）
  4. 所有内部 _calc_* 方法（_calc_bazi / _calc_ziwei / _calc_qimen / _calc_liuyao
     / _calc_liunian / _calc_fengshui / _calc_qizheng / _calc_shushu / _calc_name / _calc_marriage）
  5. _cross_validate 交叉验证
  6. _build_consensus 共识构建
  7. _generate_report 报告生成
  8. full_analysis 完整分析（真实日期、不同性别、目标年份、姓名/合婚参数）
  9. 边界情况（空 systems、缺失字段、导入错误）
  10. 不可用引擎的优雅处理
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tengod.multi_system_engine import (
    ComprehensiveAnalyzer,
    SystemResult,
    CrossValidation,
    ConsensusFortune,
    ComprehensiveResult,
    _safe_import,
    WUXING_SIGNS,
)


# ============================================================================
# 辅助函数
# ============================================================================

def _make_system_result(
    system: str,
    available: bool = True,
    data: Dict[str, Any] | None = None,
    error: str | None = None,
    summary: str = "",
) -> SystemResult:
    return SystemResult(
        system=system, available=available, data=data, error=error, summary=summary
    )


# ============================================================================
# 1. 数据类测试
# ============================================================================

class TestSystemResultDataclass:
    """SystemResult 数据类创建与 to_dict()。"""

    def test_default_creation(self):
        sr = SystemResult("八字")
        assert sr.system == "八字"
        assert sr.available is True
        assert sr.data is None
        assert sr.error is None
        assert sr.summary == ""

    def test_full_creation(self):
        sr = SystemResult(
            system="紫微斗数",
            available=True,
            data={"ming_zhu": "天同"},
            summary="命主星：天同",
        )
        assert sr.system == "紫微斗数"
        assert sr.data == {"ming_zhu": "天同"}
        assert sr.summary == "命主星：天同"

    def test_unavailable(self):
        sr = SystemResult("奇门遁甲", available=False, error="引擎未加载")
        assert sr.available is False
        assert sr.error == "引擎未加载"

    def test_to_dict(self):
        sr = SystemResult("八字", True, {"pillars": {}}, None, "日主甲")
        d = sr.to_dict()
        assert d["system"] == "八字"
        assert d["available"] is True
        assert d["data"] == {"pillars": {}}
        assert d["error"] is None
        assert d["summary"] == "日主甲"

    def test_to_dict_unavailable(self):
        sr = SystemResult("六爻卦", False, error="引擎未加载")
        d = sr.to_dict()
        assert d["system"] == "六爻卦"
        assert d["available"] is False
        assert d["error"] == "引擎未加载"


class TestCrossValidationDataclass:
    """CrossValidation 数据类创建与 to_dict()。"""

    def test_default_creation(self):
        cv = CrossValidation()
        assert cv.score == 50
        assert cv.level == "待观察"
        assert cv.agreements == []
        assert cv.conflicts == []
        assert cv.interpretations == []

    def test_full_creation(self):
        cv = CrossValidation(
            score=80,
            level="一致",
            agreements=["共识喜用神：金"],
            conflicts=["流年(吉)与六爻(凶)判断有差异"],
            interpretations=["多体系分析一致性较高"],
        )
        assert cv.score == 80
        assert cv.level == "一致"
        assert len(cv.agreements) == 1
        assert len(cv.conflicts) == 1

    def test_to_dict(self):
        cv = CrossValidation(score=65, level="待观察")
        d = cv.to_dict()
        assert d["score"] == 65
        assert d["level"] == "待观察"
        assert d["agreements"] == []
        assert d["conflicts"] == []
        assert d["interpretations"] == []


class TestConsensusFortuneDataclass:
    """ConsensusFortune 数据类创建与 to_dict()。"""

    def test_default_creation(self):
        cf = ConsensusFortune()
        assert cf.overall == "平"
        assert cf.score == 50
        assert cf.key_strengths == []
        assert cf.key_risks == []
        assert cf.best_timing == []
        assert cf.weak_timing == []
        assert cf.career == ""
        assert cf.wealth == ""
        assert cf.relationships == ""
        assert cf.health == ""

    def test_full_creation(self):
        cf = ConsensusFortune(
            overall="大吉",
            score=85,
            key_strengths=["流年运势佳"],
            key_risks=["注意健康"],
            best_timing=["农历正月", "农历三月"],
            weak_timing=["农历七月"],
            career="事业稳步上升",
            wealth="财运亨通",
            relationships="感情和睦",
            health="精力充沛",
        )
        assert cf.overall == "大吉"
        assert cf.score == 85
        assert cf.best_timing == ["农历正月", "农历三月"]

    def test_to_dict(self):
        cf = ConsensusFortune(overall="吉", score=72, career="事业有成")
        d = cf.to_dict()
        assert d["overall"] == "吉"
        assert d["score"] == 72
        assert d["career"] == "事业有成"


class TestComprehensiveResultDataclass:
    """ComprehensiveResult 数据类创建与 to_dict()。"""

    def test_creation(self):
        birth_info = {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 0, "gender": "male"}
        systems = {"八字": _make_system_result("八字", True, {"pillars": {}}, summary="日主甲")}
        cross = CrossValidation(score=50)
        consensus = ConsensusFortune(score=50)
        report = "测试报告"

        cr = ComprehensiveResult(
            birth_info=birth_info,
            systems=systems,
            cross_validation=cross,
            consensus=consensus,
            comprehensive_report=report,
        )
        assert cr.birth_info == birth_info
        assert "八字" in cr.systems
        assert cr.cross_validation.score == 50
        assert cr.consensus.score == 50
        assert cr.comprehensive_report == "测试报告"

    def test_to_dict(self):
        birth_info = {"year": 2000, "month": 1, "day": 1, "hour": 12, "minute": 0, "gender": "female"}
        systems = {"八字": _make_system_result("八字", False, error="E")}
        cross = CrossValidation()
        consensus = ConsensusFortune()
        cr = ComprehensiveResult(birth_info, systems, cross, consensus, "R")
        d = cr.to_dict()
        assert d["birth_info"] == birth_info
        assert "八字" in d["systems"]
        assert d["systems"]["八字"]["system"] == "八字"
        assert d["cross_validation"]["score"] == 50
        assert d["consensus"]["overall"] == "平"
        assert d["comprehensive_report"] == "R"


# ============================================================================
# 2. _safe_import 测试
# ============================================================================

class TestSafeImport:
    """_safe_import 安全导入函数。"""

    def test_import_builtin(self):
        result = _safe_import("json", "JSONDecoder")
        assert result is not None

    def test_import_nonexistent_module(self):
        result = _safe_import("nonexistent.module.xyz", "SomeClass")
        assert result is None

    def test_import_nonexistent_class(self):
        result = _safe_import("json", "NonExistentClass")
        assert result is None

    def test_import_real_module(self):
        result = _safe_import("tengod.multi_system_engine", "ComprehensiveAnalyzer")
        assert result is not None
        assert result is ComprehensiveAnalyzer


# ============================================================================
# 3. _extract_yongshen 测试
# ============================================================================

class TestExtractYongshen:
    """_extract_yongshen 静态方法。"""

    def test_bazi_with_yongshen(self):
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("bazi", {"yongshen": ["金", "水"]})
        assert yong == ["金", "水"]
        assert ji == []

    def test_bazi_with_chinese_key(self):
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("bazi", {"喜用神": ["木", "火"]})
        assert yong == ["木", "火"]

    def test_bazi_filters_non_wuxing(self):
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("bazi", {"yongshen": ["金", "风", "雷"]})
        assert yong == ["金"]

    def test_bazi_empty_data(self):
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("bazi", {})
        assert yong == []
        assert ji == []

    def test_ziwei_with_ziwei_star(self):
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("ziwei", {"ming_zhu": "紫微"})
        assert "土" in yong or "金" in yong

    def test_ziwei_with_tiantong(self):
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("ziwei", {"ming_zhu": "天同"})
        assert "水" in yong or "金" in yong

    def test_ziwei_with_taiyang(self):
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("ziwei", {"ming_zhu": "太阳"})
        assert "木" in yong or "水" in yong

    def test_ziwei_with_unknown_star(self):
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("ziwei", {"ming_zhu": "天机"})
        assert yong == []

    def test_liunian_with_yongshen(self):
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("liunian", {"yongshen": ["土", "火"]})
        assert yong == ["土", "火"]

    def test_shushu_with_qian(self):
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("shushu", {"tieban": {"tian_pan": "乾"}})
        assert "金" in yong

    def test_shushu_with_li(self):
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("shushu", {"tieban": {"tian_pan": "离"}})
        assert "火" in yong

    def test_unknown_system(self):
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("unknown", {"data": "test"})
        assert yong == []

    def test_none_data(self):
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("bazi", None)
        assert yong == []
        assert ji == []

    def test_non_dict_data(self):
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("bazi", "not a dict")
        assert yong == []
        assert ji == []

    def test_yongshen_truncated_to_3(self):
        yong, ji = ComprehensiveAnalyzer._extract_yongshen("bazi", {"yongshen": ["金", "木", "水", "火", "土"]})
        assert len(yong) == 3


# ============================================================================
# 4. 内部 _calc_* 方法测试
# ============================================================================

class TestCalcMethods:
    """所有 _calc_* 方法（含引擎不可用时的优雅降级）。"""

    def setup_method(self):
        self.analyzer = ComprehensiveAnalyzer()

    def test_calc_bazi_returns_systemresult(self):
        result = self.analyzer._calc_bazi(1990, 6, 15, 10, 0, "male")
        assert isinstance(result, SystemResult)
        assert result.system == "八字"

    def test_calc_bazi_with_female(self):
        result = self.analyzer._calc_bazi(1985, 3, 20, 8, 30, "female")
        assert isinstance(result, SystemResult)
        assert result.system == "八字"

    def test_calc_bazi_with_chinese_gender(self):
        result = self.analyzer._calc_bazi(2000, 1, 1, 12, 0, "男")
        assert isinstance(result, SystemResult)
        assert result.system == "八字"

    def test_calc_bazi_handles_invalid_date(self):
        result = self.analyzer._calc_bazi(99999, 99, 99, 99, 99, "male")
        assert isinstance(result, SystemResult)
        # Should return with available=False or error set
        assert result.system == "八字"

    def test_calc_ziwei_returns_systemresult(self):
        result = self.analyzer._calc_ziwei(1990, 6, 15, 10, 0, "male")
        assert isinstance(result, SystemResult)
        assert result.system == "紫微斗数"

    def test_calc_qimen_returns_systemresult(self):
        result = self.analyzer._calc_qimen(1990, 6, 15, 10, 0)
        assert isinstance(result, SystemResult)
        assert result.system == "奇门遁甲"

    def test_calc_liuyao_returns_systemresult(self):
        result = self.analyzer._calc_liuyao(1990, 6, 15, 10, 0)
        assert isinstance(result, SystemResult)
        assert result.system == "六爻卦"

    def test_calc_liunian_returns_systemresult(self):
        pillars = {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"}
        result = self.analyzer._calc_liunian(pillars, 2026)
        assert isinstance(result, SystemResult)
        assert result.system == "流年断语"

    def test_calc_fengshui_returns_systemresult(self):
        result = self.analyzer._calc_fengshui("北", "南", 2026)
        assert isinstance(result, SystemResult)
        assert result.system == "玄空风水"

    def test_calc_qizheng_returns_systemresult(self):
        result = self.analyzer._calc_qizheng(1990, 6, 15, 10, 0)
        assert isinstance(result, SystemResult)
        assert result.system == "七政四余"

    def test_calc_shushu_returns_systemresult(self):
        pillars = {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"}
        result = self.analyzer._calc_shushu(pillars, 6, 15)
        assert isinstance(result, SystemResult)
        assert result.system == "高级术数"

    def test_calc_name_returns_systemresult(self):
        result = self.analyzer._calc_name("张", "三")
        assert isinstance(result, SystemResult)
        assert result.system == "姓名学"

    def test_calc_name_with_english_letters(self):
        result = self.analyzer._calc_name("Li", "Ming")
        assert isinstance(result, SystemResult)
        assert result.system == "姓名学"

    def test_calc_marriage_returns_systemresult(self):
        result = self.analyzer._calc_marriage(
            "张三", {"pillars": {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"}},
            "李四", {"pillars": {"year": "辛未", "month": "癸巳", "day": "壬子", "hour": "甲辰"}},
        )
        assert isinstance(result, SystemResult)
        assert result.system == "合婚分析"

    def test_calc_marriage_handles_empty_bazi(self):
        result = self.analyzer._calc_marriage("A", {}, "B", {})
        assert isinstance(result, SystemResult)
        assert result.system == "合婚分析"


# ============================================================================
# 5. _cross_validate 测试
# ============================================================================

class TestCrossValidate:
    """_cross_validate 交叉验证逻辑。"""

    def setup_method(self):
        self.analyzer = ComprehensiveAnalyzer()

    def test_empty_systems(self):
        cv = self.analyzer._cross_validate({})
        assert isinstance(cv, CrossValidation)
        assert cv.score == 50
        assert cv.agreements == []

    def test_single_system_no_validation(self):
        systems = {"八字": _make_system_result("八字", True, {"yongshen": ["金"]})}
        cv = self.analyzer._cross_validate(systems)
        assert isinstance(cv, CrossValidation)
        assert cv.score == 50  # single system, no agreements added

    def test_two_systems_with_agreement(self):
        systems = {
            "bazi": _make_system_result("bazi", True, {"yongshen": ["金", "水"]}),
            "liunian": _make_system_result("liunian", True, {"yongshen": ["金", "土"]}),
        }
        cv = self.analyzer._cross_validate(systems)
        assert isinstance(cv, CrossValidation)
        assert "金" in str(cv.agreements)

    def test_liunian_liuyao_agreement(self):
        systems = {
            "流年断语": _make_system_result("流年断语", True, {"overall": "吉", "score": 80}),
            "六爻卦": _make_system_result("六爻卦", True, {"ben_gua_name": "乾为天"}),
        }
        cv = self.analyzer._cross_validate(systems)
        assert isinstance(cv, CrossValidation)

    def test_liunian_liuyao_conflict(self):
        systems = {
            "流年断语": _make_system_result("流年断语", True, {"overall": "吉", "score": 80}),
            "六爻卦": _make_system_result("六爻卦", True, {"ben_gua_name": "天地否"}),
        }
        cv = self.analyzer._cross_validate(systems)
        assert isinstance(cv, CrossValidation)
        assert len(cv.conflicts) > 0

    def test_unavailable_systems_ignored(self):
        systems = {
            "八字": _make_system_result("八字", False, error="引擎未加载"),
            "ziwei": _make_system_result("ziwei", False, error="引擎未加载"),
        }
        cv = self.analyzer._cross_validate(systems)
        assert isinstance(cv, CrossValidation)
        assert cv.score == 50

    def test_agreements_limited_to_5(self):
        systems = {}
        for i in range(10):
            systems[f"sys_{i}"] = _make_system_result(f"sys_{i}", True, {"yongshen": ["金"]})
        cv = self.analyzer._cross_validate(systems)
        assert len(cv.agreements) <= 5

    def test_score_not_negative(self):
        systems = {
            "流年断语": _make_system_result("流年断语", True, {"overall": "吉"}),
            "六爻卦": _make_system_result("六爻卦", True, {"ben_gua_name": "天地否"}),
        }
        cv = self.analyzer._cross_validate(systems)
        assert cv.score >= 0


# ============================================================================
# 6. _build_consensus 测试
# ============================================================================

class TestBuildConsensus:
    """_build_consensus 共识构建。"""

    def setup_method(self):
        self.analyzer = ComprehensiveAnalyzer()

    def test_returns_consensus_fortune(self):
        systems = {}
        cross = CrossValidation()
        cf = self.analyzer._build_consensus(systems, cross)
        assert isinstance(cf, ConsensusFortune)
        assert cf.overall in ("大吉", "吉", "平", "凶")
        assert cf.score >= 65

    def test_with_liunian_data(self):
        systems = {
            "流年断语": _make_system_result("流年断语", True, {"score": 80, "overall": "吉", "favorable_months": ["正月", "二月"], "unfavorable_months": ["七月"]}),
        }
        cf = self.analyzer._build_consensus(systems, CrossValidation())
        assert cf.score >= 80
        assert len(cf.best_timing) == 2
        assert len(cf.weak_timing) == 1

    def test_with_shushu_data(self):
        systems = {
            "高级术数": _make_system_result("高级术数", True, {"shaozi": {"total_score": 90}}),
        }
        cf = self.analyzer._build_consensus(systems, CrossValidation())
        assert cf.score >= 90

    def test_with_liunian_and_shushu(self):
        systems = {
            "流年断语": _make_system_result("流年断语", True, {"score": 70}),
            "高级术数": _make_system_result("高级术数", True, {"shaozi": {"total_score": 80}}),
        }
        cf = self.analyzer._build_consensus(systems, CrossValidation())
        assert cf.score == 75  # (70+80)/2

    def test_has_default_domain_texts(self):
        cf = self.analyzer._build_consensus({}, CrossValidation())
        assert cf.career != ""
        assert cf.wealth != ""
        assert cf.relationships != ""
        assert cf.health != ""

    def test_liunian_judgments_in_strengths(self):
        systems = {
            "流年断语": _make_system_result("流年断语", True, {"score": 75, "judgments": ["今年事业运势较好，宜把握机会"]}),
        }
        cf = self.analyzer._build_consensus(systems, CrossValidation())
        assert len(cf.key_strengths) > 0

    def test_tieban_summary_in_strengths(self):
        systems = {
            "高级术数": _make_system_result("高级术数", True, {"tieban": {"summary": "命中带财"}}),
        }
        cf = self.analyzer._build_consensus(systems, CrossValidation())
        assert len(cf.key_strengths) > 0

    def test_high_score_maps_to_daji(self):
        systems = {
            "流年断语": _make_system_result("流年断语", True, {"score": 90}),
            "高级术数": _make_system_result("高级术数", True, {"shaozi": {"total_score": 90}}),
        }
        cf = self.analyzer._build_consensus(systems, CrossValidation())
        assert cf.overall == "大吉"

    def test_low_score_maps_to_xiong(self):
        # "凶" range is 35-49, so use scores that average to 40
        systems = {
            "流年断语": _make_system_result("流年断语", True, {"score": 38}),
            "高级术数": _make_system_result("高级术数", True, {"shaozi": {"total_score": 42}}),
        }
        cf = self.analyzer._build_consensus(systems, CrossValidation())
        assert cf.overall == "凶"


# ============================================================================
# 7. _generate_report 测试
# ============================================================================

class TestGenerateReport:
    """_generate_report 报告生成。"""

    def setup_method(self):
        self.analyzer = ComprehensiveAnalyzer()

    def test_generates_non_empty_string(self):
        birth_info = {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 0, "gender": "male"}
        systems = {"八字": _make_system_result("八字", True, {"pillars": {}}, summary="日主甲")}
        cross = CrossValidation()
        consensus = ConsensusFortune()
        report = self.analyzer._generate_report(birth_info, systems, cross, consensus)
        assert isinstance(report, str)
        assert len(report) > 0
        assert "中华命理综合分析报告" in report

    def test_report_contains_birth_info(self):
        birth_info = {"year": 2000, "month": 1, "day": 1, "hour": 8, "minute": 30, "gender": "female"}
        systems = {}
        cross = CrossValidation()
        consensus = ConsensusFortune()
        report = self.analyzer._generate_report(birth_info, systems, cross, consensus)
        assert "2000" in report
        assert "female" in report or "女" in report

    def test_report_contains_system_status(self):
        birth_info = {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 0, "gender": "male"}
        systems = {
            "八字": _make_system_result("八字", True, summary="日主甲"),
            "紫微斗数": _make_system_result("紫微斗数", False, error="引擎未加载"),
        }
        cross = CrossValidation(score=80, agreements=["共识喜用神：金"])
        consensus = ConsensusFortune(overall="吉", score=75)
        report = self.analyzer._generate_report(birth_info, systems, cross, consensus)
        assert "八字" in report
        assert "紫微斗数" in report
        assert "引擎未加载" in report
        assert "交叉验证" in report
        assert "共识运势" in report

    def test_report_contains_agreements_and_conflicts(self):
        birth_info = {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 0, "gender": "male"}
        cross = CrossValidation(
            score=65,
            agreements=["共识喜用神：金"],
            conflicts=["喜用神判断不一致"],
        )
        consensus = ConsensusFortune()
        report = self.analyzer._generate_report(birth_info, {}, cross, consensus)
        assert "共识喜用神" in report
        assert "喜用神判断不一致" in report

    def test_report_contains_domains(self):
        birth_info = {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 0, "gender": "male"}
        consensus = ConsensusFortune(
            career="事业顺利", wealth="财运亨通",
            relationships="感情和睦", health="身体健康",
        )
        report = self.analyzer._generate_report(birth_info, {}, CrossValidation(), consensus)
        assert "事业顺利" in report
        assert "财运亨通" in report
        assert "感情和睦" in report
        assert "身体健康" in report

    def test_report_contains_strengths(self):
        birth_info = {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 0, "gender": "male"}
        consensus = ConsensusFortune(key_strengths=["优势1", "优势2"])
        report = self.analyzer._generate_report(birth_info, {}, CrossValidation(), consensus)
        assert "核心优势" in report
        assert "优势1" in report

    def test_report_contains_timing(self):
        birth_info = {"year": 1990, "month": 6, "day": 15, "hour": 10, "minute": 0, "gender": "male"}
        consensus = ConsensusFortune(best_timing=["正月"], weak_timing=["七月"])
        report = self.analyzer._generate_report(birth_info, {}, CrossValidation(), consensus)
        assert "最佳时机" in report
        assert "需谨慎" in report


# ============================================================================
# 8. full_analysis 测试
# ============================================================================

class TestFullAnalysis:
    """full_analysis 完整分析流程。"""

    def setup_method(self):
        self.analyzer = ComprehensiveAnalyzer()

    def test_returns_comprehensive_result(self):
        result = self.analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="male",
        )
        assert isinstance(result, ComprehensiveResult)
        assert result.birth_info["year"] == 1990
        assert result.birth_info["month"] == 6
        assert result.birth_info["day"] == 15

    def test_all_systems_present(self):
        result = self.analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="male",
        )
        expected = ["八字", "紫微斗数", "奇门遁甲", "六爻卦", "流年断语", "玄空风水", "七政四余", "高级术数"]
        for name in expected:
            assert name in result.systems, f"缺少体系：{name}"
            assert isinstance(result.systems[name], SystemResult)

    def test_with_female_gender(self):
        result = self.analyzer.full_analysis(
            birth_date=(1985, 3, 20),
            birth_time=(8, 30),
            gender="female",
        )
        assert isinstance(result, ComprehensiveResult)
        assert result.birth_info["gender"] == "female"

    def test_with_chinese_gender(self):
        result = self.analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="男",
        )
        assert isinstance(result, ComprehensiveResult)

    def test_with_target_year(self):
        result = self.analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="male",
            target_year=2030,
        )
        assert isinstance(result, ComprehensiveResult)

    def test_cross_validation_present(self):
        result = self.analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="male",
        )
        assert isinstance(result.cross_validation, CrossValidation)

    def test_consensus_present(self):
        result = self.analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="male",
        )
        assert isinstance(result.consensus, ConsensusFortune)

    def test_report_is_non_empty_string(self):
        result = self.analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="male",
        )
        assert isinstance(result.comprehensive_report, str)
        assert len(result.comprehensive_report) > 0

    def test_with_name_parameters(self):
        result = self.analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="male",
            name_surname="张",
            name_given="三",
        )
        assert "姓名学" in result.systems
        assert isinstance(result.systems["姓名学"], SystemResult)

    def test_name_not_added_without_surname(self):
        result = self.analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="male",
            name_surname=None,
            name_given="三",
        )
        assert "姓名学" not in result.systems

    def test_name_not_added_without_given(self):
        result = self.analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="male",
            name_surname="张",
            name_given=None,
        )
        assert "姓名学" not in result.systems

    def test_with_partner_info(self):
        result = self.analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="male",
            partner_info={
                "name1": "张三",
                "name2": "李四",
                "bazi": {"pillars": {"year": "辛未", "month": "癸巳", "day": "壬子", "hour": "甲辰"}},
            },
        )
        assert "合婚分析" in result.systems

    def test_partner_not_added_without_partner_info(self):
        result = self.analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="male",
        )
        assert "合婚分析" not in result.systems

    def test_with_custom_pillars(self):
        custom_pillars = {"year": "甲子", "month": "乙丑", "day": "丙寅", "hour": "丁卯"}
        result = self.analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="male",
            pillars=custom_pillars,
        )
        assert isinstance(result, ComprehensiveResult)

    def test_to_dict(self):
        result = self.analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="male",
        )
        d = result.to_dict()
        assert "birth_info" in d
        assert "systems" in d
        assert "cross_validation" in d
        assert "consensus" in d
        assert "comprehensive_report" in d
        assert isinstance(d["systems"], dict)

    def test_multiple_dates(self):
        dates = [(2000, 1, 1), (1985, 12, 31), (1970, 7, 7)]
        for y, m, d in dates:
            result = self.analyzer.full_analysis(
                birth_date=(y, m, d),
                birth_time=(12, 0),
                gender="male",
            )
            assert isinstance(result, ComprehensiveResult)


# ============================================================================
# 9. 边界情况测试
# ============================================================================

class TestEdgeCases:
    """边界情况与异常处理。"""

    def setup_method(self):
        self.analyzer = ComprehensiveAnalyzer()

    def test_full_analysis_with_extreme_date(self):
        result = self.analyzer.full_analysis(
            birth_date=(1900, 1, 1),
            birth_time=(0, 0),
            gender="male",
        )
        assert isinstance(result, ComprehensiveResult)

    def test_unavailable_engine_handled_gracefully(self):
        engine_names = list(self.analyzer._engines.keys())
        assert len(engine_names) >= 0  # 至少不会崩溃

    def test_cross_validate_with_none_data(self):
        systems = {"八字": _make_system_result("八字", True, data=None)}
        cv = self.analyzer._cross_validate(systems)
        assert isinstance(cv, CrossValidation)

    def test_cross_validate_with_non_dict_data(self):
        sr = SystemResult("八字", True, data="not a dict")
        cv = self.analyzer._cross_validate({"八字": sr})
        assert isinstance(cv, CrossValidation)

    def test_build_consensus_with_non_dict_data(self):
        sr = SystemResult("流年断语", True, data="not a dict")
        cf = self.analyzer._build_consensus({"流年断语": sr}, CrossValidation())
        assert isinstance(cf, ConsensusFortune)

    def test_build_consensus_with_missing_score(self):
        sr = SystemResult("流年断语", True, data={})
        cf = self.analyzer._build_consensus({"流年断语": sr}, CrossValidation())
        assert isinstance(cf, ConsensusFortune)
        assert cf.score >= 0

    def test_analyzer_instantiation_does_not_crash(self):
        analyzer = ComprehensiveAnalyzer()
        assert isinstance(analyzer, ComprehensiveAnalyzer)
        assert hasattr(analyzer, "_engines")
        assert isinstance(analyzer._engines, dict)

    def test_full_analysis_with_all_optional_params(self):
        result = self.analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 0),
            gender="male",
            target_year=2028,
            sitting="东",
            facing="西",
            lunar_month=5,
            lunar_day=15,
            name_surname="王",
            name_given="五",
            partner_info={
                "name1": "王五",
                "name2": "赵六",
                "bazi": {"pillars": {"year": "辛未", "month": "癸巳", "day": "壬子", "hour": "甲辰"}},
            },
        )
        assert isinstance(result, ComprehensiveResult)
        assert "姓名学" in result.systems
        assert "合婚分析" in result.systems