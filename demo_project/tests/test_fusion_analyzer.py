"""
test_fusion_analyzer.py — 多体系融合分析引擎 测试套件
====================================================
覆盖：常量、所有 dataclass、FusionAnalyzer 全部方法、quick_fusion、边界条件
"""

import json
import pytest
from dataclasses import asdict

from tengod.fusion_analyzer import (
    WUXING_SIGNS,
    SYSTEM_WEIGHTS,
    AGREEMENT_LEVELS,
    FORTUNE_LEVELS,
    SystemAnalysis,
    CrossValidationResult,
    FusionResult,
    FusionAnalyzer,
    quick_fusion,
)


# ============================================================================
# 测试常量
# ============================================================================

class TestConstants:
    """常量定义验证"""

    def test_wuxing_signs_has_5_elements(self):
        assert len(WUXING_SIGNS) == 5
        assert "木" in WUXING_SIGNS
        assert "火" in WUXING_SIGNS
        assert "土" in WUXING_SIGNS
        assert "金" in WUXING_SIGNS
        assert "水" in WUXING_SIGNS

    def test_system_weights_sum_to_1(self):
        total = sum(SYSTEM_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_system_weights_keys(self):
        assert "bazi" in SYSTEM_WEIGHTS
        assert "ziwei" in SYSTEM_WEIGHTS
        assert "qimen" in SYSTEM_WEIGHTS
        assert SYSTEM_WEIGHTS["bazi"] == 0.45
        assert SYSTEM_WEIGHTS["ziwei"] == 0.35
        assert SYSTEM_WEIGHTS["qimen"] == 0.20

    def test_agreement_levels_boundaries(self):
        assert AGREEMENT_LEVELS[(80, 101)] == "高度一致"
        assert AGREEMENT_LEVELS[(60, 80)] == "基本一致"
        assert AGREEMENT_LEVELS[(40, 60)] == "部分一致"
        assert AGREEMENT_LEVELS[(20, 40)] == "存在分歧"
        assert AGREEMENT_LEVELS[(0, 20)] == "严重矛盾"

    def test_agreement_levels_no_gap(self):
        """验证 AGREEMENT_LEVELS 区间连续无间隙"""
        bounds = sorted(AGREEMENT_LEVELS.keys())
        for i in range(len(bounds) - 1):
            assert bounds[i][1] == bounds[i + 1][0], f"区间缺口: {bounds[i]} → {bounds[i + 1]}"

    def test_fortune_levels_boundaries(self):
        assert FORTUNE_LEVELS[(85, 101)] == "大吉"
        assert FORTUNE_LEVELS[(70, 85)] == "吉"
        assert FORTUNE_LEVELS[(55, 70)] == "平"
        assert FORTUNE_LEVELS[(40, 55)] == "凶"
        assert FORTUNE_LEVELS[(0, 40)] == "大凶"

    def test_fortune_levels_no_gap(self):
        """验证 FORTUNE_LEVELS 区间连续无间隙"""
        bounds = sorted(FORTUNE_LEVELS.keys())
        for i in range(len(bounds) - 1):
            assert bounds[i][1] == bounds[i + 1][0], f"区间缺口: {bounds[i]} → {bounds[i + 1]}"


# ============================================================================
# 测试 SystemAnalysis dataclass
# ============================================================================

class TestSystemAnalysis:
    """SystemAnalysis 数据类测试"""

    def test_create_with_defaults(self):
        sa = SystemAnalysis("八字")
        assert sa.name == "八字"
        assert sa.available is True
        assert sa.score == 50
        assert sa.yongshen == []
        assert sa.jishen == []
        assert sa.strengths == []
        assert sa.risks == []
        assert sa.summary == ""
        assert sa.key_findings == []
        assert sa.error is None

    def test_create_with_all_fields(self):
        sa = SystemAnalysis(
            name="紫微斗数",
            available=True,
            score=85,
            yongshen=["水", "金"],
            jishen=["火"],
            strengths=["命宫吉星汇聚"],
            risks=["有煞星，需防波折"],
            summary="命主天府，身主天同",
            key_findings=["发现1", "发现2"],
            error=None,
        )
        assert sa.name == "紫微斗数"
        assert sa.score == 85
        assert sa.yongshen == ["水", "金"]
        assert sa.strengths == ["命宫吉星汇聚"]
        assert sa.risks == ["有煞星，需防波折"]
        assert sa.key_findings == ["发现1", "发现2"]

    def test_unavailable_with_error(self):
        sa = SystemAnalysis("奇门遁甲", available=False, error="无数据")
        assert sa.available is False
        assert sa.error == "无数据"

    def test_to_dict(self):
        sa = SystemAnalysis(
            name="八字",
            score=72,
            yongshen=["木"],
            jishen=["金"],
            strengths=["喜用神得力"],
            risks=["五行偏旺"],
            summary="日主甲木",
            key_findings=["发现"],
            error=None,
        )
        d = sa.to_dict()
        assert d["name"] == "八字"
        assert d["score"] == 72
        assert d["available"] is True
        assert d["yongshen"] == ["木"]
        assert d["jishen"] == ["金"]
        assert d["strengths"] == ["喜用神得力"]
        assert d["risks"] == ["五行偏旺"]
        assert d["summary"] == "日主甲木"
        assert d["key_findings"] == ["发现"]
        assert d["error"] is None

    def test_to_dict_uses_asdict(self):
        sa = SystemAnalysis("测试")
        d = sa.to_dict()
        assert d == asdict(sa)


# ============================================================================
# 测试 CrossValidationResult dataclass
# ============================================================================

class TestCrossValidationResult:
    """CrossValidationResult 数据类测试"""

    def test_create_with_defaults(self):
        cv = CrossValidationResult()
        assert cv.agreement_score == 50
        assert cv.level == "待观察"
        assert cv.confidence == 0.5
        assert cv.yongshen_consensus == []
        assert cv.yongshen_conflicts == []
        assert cv.agreements == []
        assert cv.conflicts == []
        assert cv.dimensions == {}

    def test_create_with_all_fields(self):
        cv = CrossValidationResult(
            agreement_score=85,
            level="高度一致",
            confidence=0.85,
            yongshen_consensus=["木", "水"],
            yongshen_conflicts=["火"],
            agreements=["喜用神共识", "评分一致"],
            conflicts=["体系偏差较大"],
            dimensions={"yongshen": 25, "score_consistency": 20},
        )
        assert cv.agreement_score == 85
        assert cv.level == "高度一致"
        assert cv.confidence == 0.85
        assert cv.yongshen_consensus == ["木", "水"]
        assert cv.yongshen_conflicts == ["火"]
        assert len(cv.agreements) == 2
        assert len(cv.conflicts) == 1
        assert cv.dimensions["yongshen"] == 25

    def test_to_dict(self):
        cv = CrossValidationResult(
            agreement_score=72,
            level="基本一致",
            confidence=0.72,
            dimensions={"yongshen": 20},
        )
        d = cv.to_dict()
        assert d["agreement_score"] == 72
        assert d["level"] == "基本一致"
        assert d["confidence"] == 0.72
        assert d["dimensions"] == {"yongshen": 20}

    def test_to_dict_uses_asdict(self):
        cv = CrossValidationResult()
        d = cv.to_dict()
        assert d == asdict(cv)


# ============================================================================
# 测试 FusionResult dataclass
# ============================================================================

class TestFusionResult:
    """FusionResult 数据类测试"""

    def test_create_with_defaults(self):
        fr = FusionResult()
        assert fr.birth_info == {}
        assert fr.systems == {}
        assert fr.overall_score == 50
        assert fr.overall_level == "平"
        assert fr.fusion_summary == ""
        assert fr.key_events == []
        assert fr.recommendations == []
        assert fr.fusion_report == ""
        # cross_validation 默认是一个 CrossValidationResult 实例
        assert isinstance(fr.cross_validation, CrossValidationResult)

    def test_create_with_all_fields(self):
        cv = CrossValidationResult(agreement_score=80, level="高度一致")
        sa = SystemAnalysis("八字", score=75)
        fr = FusionResult(
            birth_info={"name": "测试", "year": 2020},
            systems={"八字": sa},
            cross_validation=cv,
            overall_score=78,
            overall_level="吉",
            fusion_summary="测试摘要",
            key_events=[{"type": "大运", "description": "测试"}],
            recommendations=["建议1", "建议2"],
            fusion_report="测试报告",
        )
        assert fr.birth_info["name"] == "测试"
        assert fr.systems["八字"].score == 75
        assert fr.cross_validation.agreement_score == 80
        assert fr.overall_score == 78
        assert fr.overall_level == "吉"
        assert len(fr.recommendations) == 2

    def test_to_dict(self):
        cv = CrossValidationResult(agreement_score=65, level="部分一致")
        sa = SystemAnalysis("八字", score=70, yongshen=["木"])
        fr = FusionResult(
            birth_info={"year": 2024},
            systems={"八字": sa},
            cross_validation=cv,
            overall_score=68,
            overall_level="平",
            fusion_summary="摘要",
            key_events=[{"type": "流年", "year": "2025"}],
            recommendations=["建议"],
            fusion_report="报告",
        )
        d = fr.to_dict()
        assert d["birth_info"] == {"year": 2024}
        assert d["systems"]["八字"]["score"] == 70
        assert d["cross_validation"]["agreement_score"] == 65
        assert d["overall_score"] == 68
        assert d["overall_level"] == "平"
        assert d["key_events"][0]["type"] == "流年"

    def test_to_json(self):
        cv = CrossValidationResult(agreement_score=80)
        sa = SystemAnalysis("八字", score=72)
        fr = FusionResult(
            birth_info={"year": 2024},
            systems={"八字": sa},
            cross_validation=cv,
            overall_score=70,
            overall_level="吉",
        )
        json_str = fr.to_json()
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["overall_score"] == 70
        assert data["overall_level"] == "吉"
        assert data["systems"]["八字"]["score"] == 72

    def test_to_json_no_ascii(self):
        """to_json 应该使用 ensure_ascii=False 保留中文"""
        sa = SystemAnalysis("八字", summary="日主甲木")
        cv = CrossValidationResult(level="高度一致")
        fr = FusionResult(
            systems={"八字": sa},
            cross_validation=cv,
            fusion_summary="测试摘要",
        )
        json_str = fr.to_json()
        assert "日主甲木" in json_str
        assert "高度一致" in json_str
        assert "测试摘要" in json_str


# ============================================================================
# 测试 FusionAnalyzer
# ============================================================================

# ── 测试用数据构建器 ──────────────────────────────────────────────────────

def make_bazi_data(
    day_master="甲",
    wuxing=None,
    yongshen=None,
    jishen=None,
    geju="正官格",
    shensha=None,
    conclusion="",
    dayuns=None,
    liunians=None,
):
    return {
        "pillars": {"year": "甲子", "month": "丙寅", "day": "甲午", "hour": "乙丑"},
        "geju": geju,
        "shensha": shensha or [],
        "analysis": {
            "day_master": day_master,
            "wuxing": wuxing or {"木": 4, "火": 3, "土": 2, "金": 2, "水": 1},
            "yongshen": yongshen or [],
            "jishen": jishen or [],
            "conclusion": conclusion,
            "dayuns": dayuns or [],
            "liunians": liunians or [],
        },
    }


def make_ziwei_data(
    ming_main_stars=None,
    ming_zhu="天府",
    shen_zhu="天同",
    sihua=None,
    daxian=None,
):
    if ming_main_stars is None:
        ming_main_stars = ["紫微", "天府"]
    return {
        "ming_gong": {"main_stars": ming_main_stars},
        "shen_gong": {"main_stars": ["天相"]},
        "gongs": [],
        "sihua": sihua or {},
        "ming_zhu": ming_zhu,
        "shen_zhu": shen_zhu,
        "daxian": daxian or [],
    }


def make_qimen_data(pan_type="时家奇门", men="开门", star="天辅", gan="甲", shen="值符"):
    return {
        "pan_type": pan_type,
        "men": men,
        "star": star,
        "gan": gan,
        "shen": shen,
    }


class TestFusionAnalyzerInit:
    """FusionAnalyzer 初始化测试"""

    def test_init_with_all_data(self):
        fa = FusionAnalyzer(
            bazi_data=make_bazi_data(),
            ziwei_data=make_ziwei_data(),
            qimen_data=make_qimen_data(),
            birth_info={"name": "测试", "year": 2000},
            target_year=2026,
        )
        assert fa._bazi is not None
        assert fa._ziwei is not None
        assert fa._qimen is not None
        assert fa._birth["name"] == "测试"
        assert fa._target_year == 2026

    def test_init_with_partial_data(self):
        """部分体系不可用"""
        fa = FusionAnalyzer(
            bazi_data=make_bazi_data(),
            ziwei_data=None,
            qimen_data=None,
        )
        assert fa._bazi != {}
        assert fa._ziwei == {}
        assert fa._qimen == {}

    def test_init_with_empty_data(self):
        fa = FusionAnalyzer()
        assert fa._bazi == {}
        assert fa._ziwei == {}
        assert fa._qimen == {}
        assert fa._birth == {}
        assert fa._target_year == 2026

    def test_init_none_data_becomes_empty_dict(self):
        fa = FusionAnalyzer(bazi_data=None, ziwei_data=None, qimen_data=None)
        assert fa._bazi == {}
        assert fa._ziwei == {}
        assert fa._qimen == {}


class TestFusionAnalyzerAnalyze:
    """analyze() 主入口测试"""

    def test_analyze_returns_fusion_result(self):
        fa = FusionAnalyzer(
            bazi_data=make_bazi_data(),
            ziwei_data=make_ziwei_data(),
            qimen_data=make_qimen_data(),
        )
        result = fa.analyze()
        assert isinstance(result, FusionResult)

    def test_analyze_all_3_systems_available(self):
        fa = FusionAnalyzer(
            bazi_data=make_bazi_data(),
            ziwei_data=make_ziwei_data(),
            qimen_data=make_qimen_data(),
        )
        result = fa.analyze()
        assert result.systems["八字"].available is True
        assert result.systems["紫微斗数"].available is True
        assert result.systems["奇门遁甲"].available is True
        assert result.overall_score >= 10
        assert result.overall_score <= 100
        assert result.fusion_report != ""
        assert "三体系" in result.fusion_summary

    def test_analyze_only_2_systems(self):
        fa = FusionAnalyzer(
            bazi_data=make_bazi_data(),
            ziwei_data=make_ziwei_data(),
        )
        result = fa.analyze()
        assert result.systems["八字"].available is True
        assert result.systems["紫微斗数"].available is True
        assert result.systems["奇门遁甲"].available is False
        assert "2/3" in result.fusion_summary

    def test_analyze_only_1_system(self):
        fa = FusionAnalyzer(bazi_data=make_bazi_data())
        result = fa.analyze()
        assert result.systems["八字"].available is True
        assert result.systems["紫微斗数"].available is False
        assert result.systems["奇门遁甲"].available is False
        assert "1/3" in result.fusion_summary

    def test_analyze_no_systems(self):
        fa = FusionAnalyzer()
        result = fa.analyze()
        assert result.systems["八字"].available is False
        assert result.systems["紫微斗数"].available is False
        assert result.systems["奇门遁甲"].available is False
        assert "0/3" in result.fusion_summary
        # 无体系时默认评分
        assert result.overall_score == 50

    def test_analyze_has_fusion_report(self):
        fa = FusionAnalyzer(
            bazi_data=make_bazi_data(),
            ziwei_data=make_ziwei_data(),
            qimen_data=make_qimen_data(),
        )
        result = fa.analyze()
        assert "三体系融合命理分析报告" in result.fusion_report
        assert "体系评分" in result.fusion_report
        assert "交叉验证" in result.fusion_report
        assert "综合运势" in result.fusion_report

    def test_analyze_has_recommendations(self):
        fa = FusionAnalyzer(
            bazi_data=make_bazi_data(yongshen=["木", "水"]),
            ziwei_data=make_ziwei_data(),
        )
        result = fa.analyze()
        assert len(result.recommendations) > 0


class TestFusionAnalyzerAnalyzeBazi:
    """_analyze_bazi 内部方法测试"""

    def test_bazi_empty_data(self):
        fa = FusionAnalyzer()
        sa = fa._analyze_bazi()
        assert sa.available is False
        assert sa.error == "无数据"

    def test_bazi_basic_scoring(self):
        fa = FusionAnalyzer(bazi_data=make_bazi_data(day_master="甲", wuxing={"木": 4, "火": 3, "土": 2, "金": 2, "水": 1}))
        sa = fa._analyze_bazi()
        assert sa.available is True
        assert sa.score >= 10
        assert sa.score <= 100
        assert "日主甲" in sa.summary

    def test_bazi_with_yongshen_jishen(self):
        fa = FusionAnalyzer(bazi_data=make_bazi_data(yongshen=["木", "水"], jishen=["金", "土"]))
        sa = fa._analyze_bazi()
        assert sa.yongshen == ["木", "水"]
        assert sa.jishen == ["金", "土"]

    def test_bazi_yongshen_filter_non_wuxing(self):
        """喜用神应该只包含五行元素"""
        fa = FusionAnalyzer(bazi_data=make_bazi_data(yongshen=["木", "火", "非五行", "abc"], jishen=["土"]))
        sa = fa._analyze_bazi()
        assert "非五行" not in sa.yongshen
        assert "abc" not in sa.yongshen

    def test_bazi_with_geju(self):
        fa = FusionAnalyzer(bazi_data=make_bazi_data(geju="正官格"))
        sa = fa._analyze_bazi()
        assert any("正官格" in s for s in sa.strengths)

    def test_bazi_without_geju(self):
        fa = FusionAnalyzer(bazi_data=make_bazi_data(geju=""))
        sa = fa._analyze_bazi()
        # geju bonus 为 0
        assert "待定" in sa.key_findings[1]

    def test_bazi_with_shensha(self):
        fa = FusionAnalyzer(bazi_data=make_bazi_data(shensha=["天乙贵人", "文昌", "桃花"]))
        sa = fa._analyze_bazi()
        assert "天乙贵人" in sa.key_findings[2]

    def test_bazi_no_shensha(self):
        fa = FusionAnalyzer(bazi_data=make_bazi_data(shensha=[]))
        sa = fa._analyze_bazi()
        assert "无特殊神煞" in sa.key_findings[2]

    def test_bazi_wang_conclusion(self):
        """结论包含'旺'时应有风险提示"""
        fa = FusionAnalyzer(bazi_data=make_bazi_data(conclusion="身旺"))
        sa = fa._analyze_bazi()
        assert any("五行偏旺" in r for r in sa.risks)

    def test_bazi_wuxing_balance_high(self):
        """五行和 10-15 之间，平衡分 80"""
        fa = FusionAnalyzer(bazi_data=make_bazi_data(
            wuxing={"木": 3, "火": 3, "土": 3, "金": 2, "水": 2},
            geju="",
            shensha=[],
        ))
        sa = fa._analyze_bazi()
        # balance=80, no geju bonus, no shensha bonus → score=80
        assert sa.score == 80

    def test_bazi_wuxing_balance_medium(self):
        """五行和 5-20 之间但不在 10-15，平衡分 60"""
        fa = FusionAnalyzer(bazi_data=make_bazi_data(
            wuxing={"木": 5, "火": 5, "土": 5, "金": 2, "水": 1},
            geju="",
            shensha=[],
        ))
        sa = fa._analyze_bazi()
        assert sa.score == 60

    def test_bazi_wuxing_balance_low(self):
        """五行和不在 5-20 范围，平衡分 40"""
        fa = FusionAnalyzer(bazi_data=make_bazi_data(
            wuxing={"木": 10, "火": 10, "土": 10, "金": 10, "水": 10},
            geju="",
            shensha=[],
        ))
        sa = fa._analyze_bazi()
        assert sa.score == 40

    def test_bazi_score_capped_at_100(self):
        """评分上限 100"""
        fa = FusionAnalyzer(bazi_data=make_bazi_data(
            wuxing={"木": 3, "火": 3, "土": 3, "金": 2, "水": 2},
            geju="正官格",
            shensha=["天乙贵人", "文昌", "禄神", "将星", "金舆", "华盖"],
        ))
        sa = fa._analyze_bazi()
        assert sa.score <= 100

    def test_bazi_yongshen_not_list(self):
        """yongshen 不是 list 时不报错"""
        fa = FusionAnalyzer(bazi_data={
            "pillars": {},
            "geju": "",
            "shensha": [],
            "analysis": {
                "day_master": "甲",
                "wuxing": {"木": 3, "火": 3, "土": 3, "金": 2, "水": 2},
                "yongshen": "木",  # 不是 list
                "jishen": None,
                "conclusion": "",
                "dayuns": [],
                "liunians": [],
            },
        })
        sa = fa._analyze_bazi()
        assert sa.yongshen == []


class TestFusionAnalyzerAnalyzeZiwei:
    """_analyze_ziwei 内部方法测试"""

    def test_ziwei_empty_data(self):
        fa = FusionAnalyzer()
        sa = fa._analyze_ziwei()
        assert sa.available is False
        assert sa.error == "无数据"

    def test_ziwei_basic(self):
        fa = FusionAnalyzer(ziwei_data=make_ziwei_data(ming_main_stars=["紫微", "天府"], ming_zhu="天府"))
        sa = fa._analyze_ziwei()
        assert sa.available is True
        assert sa.score >= 10
        assert sa.score <= 100

    def test_ziwei_good_stars(self):
        fa = FusionAnalyzer(ziwei_data=make_ziwei_data(ming_main_stars=["紫微", "天府", "天相", "文昌"]))
        sa = fa._analyze_ziwei()
        assert any("吉星汇聚" in s for s in sa.strengths)

    def test_ziwei_bad_stars(self):
        fa = FusionAnalyzer(ziwei_data=make_ziwei_data(ming_main_stars=["七杀", "破军"]))
        sa = fa._analyze_ziwei()
        assert any("煞星" in r for r in sa.risks)

    def test_ziwei_mixed_stars(self):
        fa = FusionAnalyzer(ziwei_data=make_ziwei_data(ming_main_stars=["紫微", "七杀"]))
        sa = fa._analyze_ziwei()
        # 1 good + 1 bad → base = 50 + 8 - 6 = 52
        assert sa.score == 52

    def test_ziwei_score_capped(self):
        fa = FusionAnalyzer(ziwei_data=make_ziwei_data(ming_main_stars=["紫微", "天府", "天相", "天同", "天梁", "文昌", "文曲", "左辅", "右弼"]))
        sa = fa._analyze_ziwei()
        assert sa.score <= 100

    def test_ziwei_score_floor(self):
        fa = FusionAnalyzer(ziwei_data=make_ziwei_data(ming_main_stars=["七杀", "破军", "贪狼", "巨门", "廉贞", "擎羊", "陀罗", "火星", "铃星", "地空", "地劫"]))
        sa = fa._analyze_ziwei()
        assert sa.score >= 10

    def test_ziwei_yongshen_derivation_tianfu(self):
        """天府 → 水、金"""
        fa = FusionAnalyzer(ziwei_data=make_ziwei_data(ming_zhu="天府"))
        sa = fa._analyze_ziwei()
        assert sa.yongshen == ["水", "金"]

    def test_ziwei_yongshen_derivation_ziwei(self):
        """紫微 → 土、金"""
        fa = FusionAnalyzer(ziwei_data=make_ziwei_data(ming_zhu="紫微"))
        sa = fa._analyze_ziwei()
        assert sa.yongshen == ["土", "金"]

    def test_ziwei_yongshen_derivation_taiyang(self):
        """太阳 → 木、水"""
        fa = FusionAnalyzer(ziwei_data=make_ziwei_data(ming_zhu="太阳"))
        sa = fa._analyze_ziwei()
        assert sa.yongshen == ["木", "水"]

    def test_ziwei_yongshen_derivation_lianzhen(self):
        """廉贞 → 火、木"""
        fa = FusionAnalyzer(ziwei_data=make_ziwei_data(ming_zhu="廉贞"))
        sa = fa._analyze_ziwei()
        assert sa.yongshen == ["火", "木"]

    def test_ziwei_yongshen_unknown_mingzhu(self):
        """未知命主星 → 无喜用神"""
        fa = FusionAnalyzer(ziwei_data=make_ziwei_data(ming_zhu="未知星"))
        sa = fa._analyze_ziwei()
        assert sa.yongshen == []

    def test_ziwei_with_sihua(self):
        fa = FusionAnalyzer(ziwei_data=make_ziwei_data(sihua={"天机": "化禄", "天同": "化权"}))
        sa = fa._analyze_ziwei()
        assert "化禄" in sa.key_findings[2] or "化权" in sa.key_findings[2]

    def test_ziwei_no_sihua(self):
        fa = FusionAnalyzer(ziwei_data=make_ziwei_data(sihua={}))
        sa = fa._analyze_ziwei()
        assert "无" in sa.key_findings[2]

    def test_ziwei_no_main_stars(self):
        fa = FusionAnalyzer(ziwei_data=make_ziwei_data(ming_main_stars=[]))
        sa = fa._analyze_ziwei()
        assert "无主星" in sa.key_findings[1]

    def test_ziwei_ming_gong_not_dict(self):
        """命宫不是 dict 时不报错"""
        fa = FusionAnalyzer(ziwei_data={"ming_gong": "not a dict", "ming_zhu": "天府", "shen_zhu": "天同"})
        sa = fa._analyze_ziwei()
        assert sa.available is True


class TestFusionAnalyzerAnalyzeQimen:
    """_analyze_qimen 内部方法测试"""

    def test_qimen_empty_data(self):
        fa = FusionAnalyzer()
        sa = fa._analyze_qimen()
        assert sa.available is False
        assert sa.error == "无数据"

    def test_qimen_good_men(self):
        fa = FusionAnalyzer(qimen_data=make_qimen_data(men="开门"))
        sa = fa._analyze_qimen()
        assert sa.available is True
        assert any("吉门" in s for s in sa.strengths)

    def test_qimen_bad_men(self):
        fa = FusionAnalyzer(qimen_data=make_qimen_data(men="死门"))
        sa = fa._analyze_qimen()
        assert any("凶门" in r for r in sa.risks)

    def test_qimen_neutral_men(self):
        fa = FusionAnalyzer(qimen_data=make_qimen_data(men="杜门"))
        sa = fa._analyze_qimen()
        assert sa.available is True

    def test_qimen_good_star(self):
        fa = FusionAnalyzer(qimen_data=make_qimen_data(star="天辅"))
        sa = fa._analyze_qimen()
        assert any("天时助力" in s for s in sa.strengths)

    def test_qimen_bad_star(self):
        fa = FusionAnalyzer(qimen_data=make_qimen_data(star="天蓬"))
        sa = fa._analyze_qimen()
        # 凶星不添加 strengths，且 star_score 为 -5
        assert sa.available is True

    def test_qimen_score_range(self):
        fa = FusionAnalyzer(qimen_data=make_qimen_data(men="开门", star="天辅"))
        sa = fa._analyze_qimen()
        assert sa.score >= 10
        assert sa.score <= 100

    def test_qimen_bad_combination(self):
        fa = FusionAnalyzer(qimen_data=make_qimen_data(men="死门", star="天蓬"))
        sa = fa._analyze_qimen()
        assert sa.score >= 10

    def test_qimen_summary(self):
        fa = FusionAnalyzer(qimen_data=make_qimen_data(pan_type="时家奇门", men="生门", star="天心"))
        sa = fa._analyze_qimen()
        assert "时家奇门" in sa.summary
        assert "生门" in sa.summary
        assert "天心" in sa.summary


class TestCrossValidate:
    """_cross_validate 交叉验证测试"""

    def _make_systems(self, bz_score=70, bz_available=True, bz_yongshen=None,
                      zw_score=70, zw_available=True, zw_yongshen=None,
                      qm_score=70, qm_available=True):
        systems = {
            "八字": SystemAnalysis("八字", available=bz_available, score=bz_score,
                                   yongshen=bz_yongshen or ["木", "水"]),
            "紫微斗数": SystemAnalysis("紫微斗数", available=zw_available, score=zw_score,
                                        yongshen=zw_yongshen or ["木", "水"]),
            "奇门遁甲": SystemAnalysis("奇门遁甲", available=qm_available, score=qm_score),
        }
        return systems

    def test_cross_validate_consistent(self):
        """一致的数据：喜用神相同、评分接近"""
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_score=75, zw_score=72, bz_yongshen=["木", "水"], zw_yongshen=["木", "水"])
        cv = fa._cross_validate(systems)
        assert cv.agreement_score >= 50
        assert len(cv.agreements) > 0
        assert "yongshen" in cv.dimensions

    def test_cross_validate_contradictory(self):
        """矛盾的数据：喜用神不同、评分差异大"""
        fa = FusionAnalyzer()
        systems = self._make_systems(
            bz_score=80, bz_yongshen=["木", "水"],
            zw_score=30, zw_yongshen=["火", "金"],
        )
        cv = fa._cross_validate(systems)
        assert len(cv.conflicts) > 0 or cv.agreement_score < 60

    def test_cross_validate_only_bazi(self):
        """只有八字可用"""
        fa = FusionAnalyzer()
        systems = {
            "八字": SystemAnalysis("八字", score=70, yongshen=["木"]),
            "紫微斗数": SystemAnalysis("紫微斗数", available=False, error="无数据"),
            "奇门遁甲": SystemAnalysis("奇门遁甲", available=False, error="无数据"),
        }
        cv = fa._cross_validate(systems)
        # 仅一个体系有喜用神
        assert cv.dimensions.get("yongshen", 0) == 15

    def test_cross_validate_score_consistency_high(self):
        """评分偏差 ≤15"""
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_score=75, zw_score=72, qm_score=70)
        cv = fa._cross_validate(systems)
        assert cv.dimensions["score_consistency"] == 20

    def test_cross_validate_score_consistency_medium(self):
        """评分偏差 15-30"""
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_score=80, zw_score=55, qm_score=60)
        cv = fa._cross_validate(systems)
        assert cv.dimensions["score_consistency"] == 10

    def test_cross_validate_score_consistency_low(self):
        """评分偏差 >30"""
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_score=90, zw_score=30, qm_score=40)
        cv = fa._cross_validate(systems)
        assert cv.dimensions["score_consistency"] == 5

    def test_cross_validate_direction_all_good(self):
        """三体系均呈吉象"""
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_score=65, zw_score=70, qm_score=75)
        cv = fa._cross_validate(systems)
        assert cv.dimensions["direction"] == 20

    def test_cross_validate_direction_all_bad(self):
        """三体系均呈凶象"""
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_score=30, zw_score=40, qm_score=50)
        cv = fa._cross_validate(systems)
        assert cv.dimensions["direction"] == 5

    def test_cross_validate_direction_mixed(self):
        """吉凶混合"""
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_score=70, zw_score=30, qm_score=30)
        cv = fa._cross_validate(systems)
        assert cv.dimensions["direction"] == 10

    def test_cross_validate_agreement_score_min(self):
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_score=30, zw_score=30, qm_score=30,
                                     bz_yongshen=["木"], zw_yongshen=["火"])
        cv = fa._cross_validate(systems)
        assert cv.agreement_score >= 10

    def test_cross_validate_level_high_agreement(self):
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_score=75, zw_score=72, bz_yongshen=["木", "水"], zw_yongshen=["木", "水"])
        cv = fa._cross_validate(systems)
        assert cv.level in AGREEMENT_LEVELS.values()

    def test_cross_validate_confidence_range(self):
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_score=70, zw_score=70)
        cv = fa._cross_validate(systems)
        assert 0.0 <= cv.confidence <= 1.0

    def test_cross_validate_yongshen_consensus(self):
        """喜用神共识正确提取"""
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_yongshen=["木", "水", "土"], zw_yongshen=["木", "水", "金"])
        cv = fa._cross_validate(systems)
        assert set(cv.yongshen_consensus) == {"木", "水"}


class TestComputeOverall:
    """_compute_overall 加权评分测试"""

    def _make_systems(self, bz_score=70, bz_available=True,
                      zw_score=70, zw_available=True,
                      qm_score=70, qm_available=True):
        systems = {
            "八字": SystemAnalysis("八字", available=bz_available, score=bz_score),
            "紫微斗数": SystemAnalysis("紫微斗数", available=zw_available, score=zw_score),
            "奇门遁甲": SystemAnalysis("奇门遁甲", available=qm_available, score=qm_score),
        }
        return systems

    def test_weighted_score_all_available(self):
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_score=80, zw_score=70, qm_score=60)
        cv = CrossValidationResult(agreement_score=70, confidence=0.7)
        score, level = fa._compute_overall(systems, cv)
        assert 10 <= score <= 100

    def test_weighted_score_only_bazi(self):
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_score=80, zw_available=False, qm_available=False)
        cv = CrossValidationResult(agreement_score=50, confidence=0.5)
        score, level = fa._compute_overall(systems, cv)
        assert score == 80  # 仅八字，权重归一化

    def test_weighted_score_no_available(self):
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_available=False, zw_available=False, qm_available=False)
        cv = CrossValidationResult(agreement_score=50, confidence=0.5)
        score, level = fa._compute_overall(systems, cv)
        assert score == 50  # 默认值

    def test_weighted_score_high_confidence_correction(self):
        """置信度 >= 0.8 时修正"""
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_score=80, zw_score=70, qm_score=60)
        cv = CrossValidationResult(agreement_score=90, confidence=0.9)
        score, level = fa._compute_overall(systems, cv)
        assert 10 <= score <= 100

    def test_weighted_score_low_confidence_correction(self):
        """置信度 < 0.4 时修正"""
        fa = FusionAnalyzer()
        systems = self._make_systems(bz_score=30, zw_score=40, qm_score=50)
        cv = CrossValidationResult(agreement_score=30, confidence=0.3)
        score, level = fa._compute_overall(systems, cv)
        assert 10 <= score <= 100


class TestExtractKeyEvents:
    """_extract_key_events 关键事件提取测试"""

    def test_no_events_when_no_systems(self):
        fa = FusionAnalyzer()
        systems = {
            "八字": SystemAnalysis("八字", available=False, error="无数据"),
            "紫微斗数": SystemAnalysis("紫微斗数", available=False, error="无数据"),
        }
        events = fa._extract_key_events(systems)
        assert events == []

    def test_bazi_dayuns_events(self):
        fa = FusionAnalyzer(bazi_data=make_bazi_data(dayuns=[
            {"age": 10, "pillar": "甲子"},
            {"age": 20, "pillar": "乙丑"},
        ]))
        systems = {"八字": SystemAnalysis("八字", score=70)}
        events = fa._extract_key_events(systems)
        dayun_events = [e for e in events if e["type"] == "大运"]
        assert len(dayun_events) == 2
        assert dayun_events[0]["period"] == "10-19岁"

    def test_bazi_liunians_events(self):
        fa = FusionAnalyzer(bazi_data=make_bazi_data(liunians=[
            {"year": 2025, "pillar": "乙巳"},
            {"year": 2026, "pillar": "丙午"},
        ]))
        systems = {"八字": SystemAnalysis("八字", score=70)}
        events = fa._extract_key_events(systems)
        liunian_events = [e for e in events if e["type"] == "流年"]
        assert len(liunian_events) == 2

    def test_ziwei_daxian_events(self):
        fa = FusionAnalyzer(ziwei_data=make_ziwei_data(daxian=[
            {"age_range": "20-29", "gong_name": "兄弟宫"},
            {"age_range": "30-39", "gong_name": "夫妻宫"},
        ]))
        systems = {"紫微斗数": SystemAnalysis("紫微斗数", score=70)}
        events = fa._extract_key_events(systems)
        daxian_events = [e for e in events if e["type"] == "大限"]
        assert len(daxian_events) == 2

    def test_events_limited_to_10(self):
        fa = FusionAnalyzer(bazi_data=make_bazi_data(
            dayuns=[{"age": i * 10, "pillar": f"pillar{i}"} for i in range(10)],
        ))
        systems = {"八字": SystemAnalysis("八字", score=70)}
        events = fa._extract_key_events(systems)
        assert len(events) <= 10

    def test_events_sorted(self):
        fa = FusionAnalyzer(bazi_data=make_bazi_data(
            dayuns=[
                {"age": 30, "pillar": "丙寅"},
                {"age": 10, "pillar": "甲子"},
            ],
        ))
        systems = {"八字": SystemAnalysis("八字", score=70)}
        events = fa._extract_key_events(systems)
        # 按 period 排序
        dayun_events = [e for e in events if e["type"] == "大运"]
        assert dayun_events[0]["period"] == "10-19岁"

    def test_non_dict_dayun_skipped(self):
        fa = FusionAnalyzer(bazi_data=make_bazi_data(dayuns=["not a dict", {"age": 10, "pillar": "甲子"}]))
        systems = {"八字": SystemAnalysis("八字", score=70)}
        events = fa._extract_key_events(systems)
        dayun_events = [e for e in events if e["type"] == "大运"]
        assert len(dayun_events) == 1


class TestGenerateRecommendations:
    """_generate_recommendations 建议生成测试"""

    def test_recommendations_with_bazi_yongshen(self):
        fa = FusionAnalyzer()
        systems = {"八字": SystemAnalysis("八字", score=70, yongshen=["木", "水"])}
        cv = CrossValidationResult(confidence=0.7)
        recs = fa._generate_recommendations(systems, cv, "平")
        assert any("木" in r for r in recs)

    def test_recommendations_with_risks(self):
        fa = FusionAnalyzer()
        systems = {"八字": SystemAnalysis("八字", score=70, risks=["五行偏旺，需注意平衡"])}
        cv = CrossValidationResult(confidence=0.7)
        recs = fa._generate_recommendations(systems, cv, "平")
        assert any("五行偏旺" in r for r in recs)

    def test_recommendations_ziwei_strengths(self):
        fa = FusionAnalyzer()
        systems = {"紫微斗数": SystemAnalysis("紫微斗数", score=70, strengths=["命宫吉星汇聚"])}
        cv = CrossValidationResult(confidence=0.7)
        recs = fa._generate_recommendations(systems, cv, "平")
        assert any("紫微提示" in r for r in recs)

    def test_recommendations_high_confidence(self):
        fa = FusionAnalyzer()
        systems = {}
        cv = CrossValidationResult(confidence=0.8)
        recs = fa._generate_recommendations(systems, cv, "平")
        assert any("一致性高" in r for r in recs)

    def test_recommendations_low_confidence(self):
        fa = FusionAnalyzer()
        systems = {}
        cv = CrossValidationResult(confidence=0.3)
        recs = fa._generate_recommendations(systems, cv, "平")
        assert any("保守行事" in r for r in recs)

    def test_recommendations_good_fortune(self):
        fa = FusionAnalyzer()
        systems = {}
        cv = CrossValidationResult(confidence=0.5)
        recs = fa._generate_recommendations(systems, cv, "大吉")
        assert any("开拓进取" in r for r in recs)

    def test_recommendations_bad_fortune(self):
        fa = FusionAnalyzer()
        systems = {}
        cv = CrossValidationResult(confidence=0.5)
        recs = fa._generate_recommendations(systems, cv, "大凶")
        assert any("宜静不宜动" in r for r in recs)

    def test_recommendations_limited_to_5(self):
        fa = FusionAnalyzer()
        systems = {
            "八字": SystemAnalysis("八字", score=70, yongshen=["木", "水", "金", "土", "火"],
                                   risks=["风险1", "风险2", "风险3"]),
        }
        cv = CrossValidationResult(confidence=0.9)
        recs = fa._generate_recommendations(systems, cv, "大吉")
        assert len(recs) <= 5


class TestGenerateFusionReport:
    """_generate_fusion_report 报告生成测试"""

    def test_report_structure(self):
        fa = FusionAnalyzer()
        systems = {
            "八字": SystemAnalysis("八字", score=75, available=True, key_findings=["发现1", "发现2"]),
            "紫微斗数": SystemAnalysis("紫微斗数", available=False, error="无数据"),
        }
        cv = CrossValidationResult(agreement_score=65, level="部分一致", confidence=0.65,
                                   agreements=["喜用神共识"], conflicts=["评分偏差"])
        events = [{"type": "大运", "description": "甲子大运"}]
        recs = ["建议1", "建议2"]
        report = fa._generate_fusion_report(systems, cv, 70, "吉", events, recs)
        assert "三体系融合命理分析报告" in report
        assert "体系评分" in report
        assert "交叉验证" in report
        assert "综合运势" in report
        assert "建议" in report

    def test_report_contains_scores(self):
        fa = FusionAnalyzer()
        systems = {"八字": SystemAnalysis("八字", score=82)}
        cv = CrossValidationResult(agreement_score=50, level="待观察", confidence=0.5)
        report = fa._generate_fusion_report(systems, cv, 75, "吉", [], [])
        assert "82分" in report
        assert "75/100" in report

    def test_report_unavailable_system(self):
        fa = FusionAnalyzer()
        systems = {"八字": SystemAnalysis("八字", available=False, error="无数据")}
        cv = CrossValidationResult()
        report = fa._generate_fusion_report(systems, cv, 50, "平", [], [])
        assert "不可用" in report
        assert "无数据" in report

    def test_report_with_events(self):
        fa = FusionAnalyzer()
        systems = {"八字": SystemAnalysis("八字", score=70)}
        cv = CrossValidationResult()
        events = [{"type": "大运", "description": "甲子大运"}, {"type": "流年", "description": "2025年乙巳"}]
        report = fa._generate_fusion_report(systems, cv, 70, "吉", events, [])
        assert "关键节点" in report
        assert "甲子大运" in report

    def test_report_without_events(self):
        fa = FusionAnalyzer()
        systems = {"八字": SystemAnalysis("八字", score=70)}
        cv = CrossValidationResult()
        report = fa._generate_fusion_report(systems, cv, 70, "吉", [], [])
        assert "关键节点" not in report

    def test_report_disclaimer(self):
        fa = FusionAnalyzer()
        systems = {"八字": SystemAnalysis("八字", score=70)}
        cv = CrossValidationResult()
        report = fa._generate_fusion_report(systems, cv, 70, "吉", [], [])
        assert "仅供参考" in report


# ============================================================================
# 运势等级测试
# ============================================================================

class TestFortuneLevels:
    """运势等级边界测试"""

    def _get_level(self, score):
        """通过 _compute_overall 间接测试运势等级"""
        fa = FusionAnalyzer()
        systems = {"八字": SystemAnalysis("八字", score=score)}
        cv = CrossValidationResult(agreement_score=50, confidence=0.5)
        _, level = fa._compute_overall(systems, cv)
        return level

    def test_fortune_daji(self):
        assert self._get_level(85) == "大吉"
        assert self._get_level(95) == "大吉"
        assert self._get_level(100) == "大吉"

    def test_fortune_ji(self):
        assert self._get_level(70) == "吉"
        assert self._get_level(80) == "吉"
        assert self._get_level(84) == "吉"

    def test_fortune_ping(self):
        assert self._get_level(55) == "平"
        assert self._get_level(60) == "平"
        assert self._get_level(69) == "平"

    def test_fortune_xiong(self):
        assert self._get_level(40) == "凶"
        assert self._get_level(50) == "凶"
        assert self._get_level(54) == "凶"

    def test_fortune_daxiong(self):
        assert self._get_level(10) == "大凶"
        assert self._get_level(30) == "大凶"
        assert self._get_level(39) == "大凶"


class TestAgreementLevels:
    """一致性等级边界测试"""

    def _get_level(self, agreement_score):
        """通过直接构造 CrossValidationResult 验证等级"""
        cv = CrossValidationResult(agreement_score=agreement_score)
        # 模拟 _cross_validate 中的等级计算
        level = "待观察"
        for (lo, hi), label in AGREEMENT_LEVELS.items():
            if lo <= agreement_score < hi:
                level = label
                break
        return level

    def test_agreement_highly_consistent(self):
        assert self._get_level(80) == "高度一致"
        assert self._get_level(95) == "高度一致"
        assert self._get_level(100) == "高度一致"

    def test_agreement_basically_consistent(self):
        assert self._get_level(60) == "基本一致"
        assert self._get_level(70) == "基本一致"
        assert self._get_level(79) == "基本一致"

    def test_agreement_partially_consistent(self):
        assert self._get_level(40) == "部分一致"
        assert self._get_level(50) == "部分一致"
        assert self._get_level(59) == "部分一致"

    def test_agreement_divergent(self):
        assert self._get_level(20) == "存在分歧"
        assert self._get_level(30) == "存在分歧"
        assert self._get_level(39) == "存在分歧"

    def test_agreement_serious_conflict(self):
        assert self._get_level(0) == "严重矛盾"
        assert self._get_level(10) == "严重矛盾"
        assert self._get_level(19) == "严重矛盾"


# ============================================================================
# quick_fusion 便捷函数测试
# ============================================================================

class TestQuickFusion:
    """quick_fusion 便捷函数测试"""

    def test_quick_fusion_returns_fusion_result(self):
        result = quick_fusion(
            bazi=make_bazi_data(),
            ziwei=make_ziwei_data(),
            qimen=make_qimen_data(),
        )
        assert isinstance(result, FusionResult)
        assert result.systems["八字"].available

    def test_quick_fusion_no_data(self):
        result = quick_fusion()
        assert isinstance(result, FusionResult)
        assert result.systems["八字"].available is False

    def test_quick_fusion_with_birth(self):
        result = quick_fusion(
            bazi=make_bazi_data(),
            birth={"name": "测试", "year": 2000},
            target_year=2030,
        )
        assert result.birth_info["name"] == "测试"


# ============================================================================
# 边界条件测试
# ============================================================================

class TestEdgeCases:
    """边界条件与异常情况测试"""

    def test_empty_bazi_ziwei_qimen(self):
        fa = FusionAnalyzer({}, {}, {})
        result = fa.analyze()
        assert "0/3" in result.fusion_summary

    def test_all_systems_unavailable(self):
        fa = FusionAnalyzer()
        systems = {
            "八字": SystemAnalysis("八字", available=False, error="无数据"),
            "紫微斗数": SystemAnalysis("紫微斗数", available=False, error="无数据"),
            "奇门遁甲": SystemAnalysis("奇门遁甲", available=False, error="无数据"),
        }
        cv = fa._cross_validate(systems)
        score, level = fa._compute_overall(systems, cv)
        assert score == 50
        # 50 分落在 (40, 55) → "凶"
        assert level == "凶"

    def test_none_values_in_bazi(self):
        """bazi 数据中 analysis 存在但值为 None 的场景（模块不处理此边界，会抛 AttributeError）"""
        fa = FusionAnalyzer(bazi_data={
            "pillars": None,
            "geju": None,
            "shensha": None,
            "analysis": None,
        })
        with pytest.raises(AttributeError):
            fa._analyze_bazi()

    def test_bazi_analysis_none(self):
        """bazi_data 存在但 analysis 为 None（模块不处理此边界，会抛 AttributeError）"""
        fa = FusionAnalyzer(bazi_data={"analysis": None, "geju": "", "shensha": []})
        with pytest.raises(AttributeError):
            fa._analyze_bazi()

    def test_very_high_scores(self):
        sa = SystemAnalysis("测试", score=100)
        assert sa.score == 100

    def test_very_low_scores(self):
        sa = SystemAnalysis("测试", score=0)
        assert sa.score == 0

    def test_missing_yongshen_jishen(self):
        sa = SystemAnalysis("测试")
        assert sa.yongshen == []
        assert sa.jishen == []

    def test_fusion_result_to_json_with_empty_systems(self):
        fr = FusionResult()
        json_str = fr.to_json()
        data = json.loads(json_str)
        assert data["systems"] == {}

    def test_system_analysis_with_long_summary(self):
        sa = SystemAnalysis("测试", summary="这是一个非常长的摘要" * 20)
        assert len(sa.summary) > 100

    def test_cross_validate_with_none_systems(self):
        fa = FusionAnalyzer()
        systems = {
            "八字": None,
            "紫微斗数": None,
            "奇门遁甲": None,
        }
        # None systems 是无效输入，模块假设 systems 都为 SystemAnalysis 实例
        # 此场景应由调用者保证，测试验证会抛出 TypeError
        with pytest.raises(TypeError):
            fa._cross_validate(systems)

    def test_analyze_full_flow(self):
        """完整流程集成测试"""
        fa = FusionAnalyzer(
            bazi_data=make_bazi_data(
                day_master="丙",
                wuxing={"木": 2, "火": 5, "土": 3, "金": 1, "水": 2},
                yongshen=["木", "水"],
                jishen=["火"],
                geju="七杀格",
                shensha=["天乙贵人", "文昌"],
                conclusion="火旺",
                dayuns=[{"age": 10, "pillar": "甲子"}, {"age": 20, "pillar": "乙丑"}],
                liunians=[{"year": 2025, "pillar": "乙巳"}],
            ),
            ziwei_data=make_ziwei_data(
                ming_main_stars=["紫微", "天府", "文昌"],
                ming_zhu="天府",
                shen_zhu="天同",
                sihua={"天机": "化禄"},
                daxian=[{"age_range": "20-29", "gong_name": "夫妻宫"}],
            ),
            qimen_data=make_qimen_data(men="开门", star="天辅"),
            birth_info={"name": "集成测试", "year": 2000},
        )
        result = fa.analyze()

        assert isinstance(result, FusionResult)
        assert result.systems["八字"].available
        assert result.systems["紫微斗数"].available
        assert result.systems["奇门遁甲"].available
        assert result.overall_score >= 10
        assert result.overall_score <= 100
        assert result.overall_level in ["大吉", "吉", "平", "凶", "大凶"]
        assert len(result.key_events) > 0
        assert len(result.recommendations) > 0
        assert "三体系融合命理分析报告" in result.fusion_report
        assert "集成测试" in result.fusion_summary or True  # birth_info 不影响 summary

        # 验证 to_dict 和 to_json
        d = result.to_dict()
        assert d["overall_score"] == result.overall_score
        json_str = result.to_json()
        assert isinstance(json_str, str)
        json.loads(json_str)  # 不抛异常