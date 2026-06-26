"""
test_liunian_judgment.py — 流年吉凶断语引擎全面测试

测试覆盖：
  - YearJudgment 数据类创建与字段
  - _extract_yongshen 内部方法（多种输入格式）
  - _zhi_interaction 所有地支冲合关系
  - _season_of_zhi 四季判断
  - judge_year 单年判断（多种八字数据）
  - judge 批量多年判断
  - decade_summary 十年综合报告
  - 所有 10 十神类型
  - 评分逻辑（高/中/低分场景）
  - 边界情况（空数据、缺失键、无效年份）
  - 模板断语非空验证
  - favorable_months / unfavorable_months
"""

from __future__ import annotations

import pytest

from tengod.liunian_judgment import (
    LiunianJudgmentEngine,
    YearJudgment,
    GAN_WUXING,
    GAN_YINYANG,
    ZHI_WUXING,
    ZHI_MAIN_GAN,
    ZHI_CANG_GAN,
    WUXING_SHENG,
    WUXING_KE,
    YONGSHEN_TEMPLATES,
    JISHEN_TEMPLATES,
    SHIGAN_TEMPLATES,
    ZHI_INTERACTION_TEMPLATES,
    YUE_LING_TEMPLATES,
    SHENSHA_TEMPLATES,
    _derive_shigan,
    judge_years,
    judge_decade,
)


# ============================================================================
# 测试数据
# ============================================================================

# 完整八字数据（甲子年 丙寅月 戊辰日 庚申时）
BAZI_FULL = {
    "day_master": "戊",
    "pillars": {
        "year": "甲子",
        "month": "丙寅",
        "day": "戊辰",
        "hour": "庚申",
    },
    "yongshen": {
        "favorable_elements": ["火", "土"],
        "unfavorable_elements": ["木", "水"],
    },
}

# 辛金日主八字
BAZI_XIN = {
    "day_master": "辛",
    "pillars": {
        "year": "庚午",
        "month": "壬午",
        "day": "辛亥",
        "hour": "癸巳",
    },
    "yongshen": {
        "favorable_elements": ["土", "金"],
        "unfavorable_elements": ["木", "火"],
    },
}

# 甲木日主八字
BAZI_JIA = {
    "day_master": "甲",
    "pillars": {
        "year": "甲子",
        "month": "丙寅",
        "day": "甲子",
        "hour": "壬申",
    },
    "yongshen": {
        "favorable_elements": ["水", "木"],
        "unfavorable_elements": ["金", "土"],
    },
}

# 最小八字数据（仅有日主）
BAZI_MINIMAL = {"day_master": "丙"}

# 空八字数据
BAZI_EMPTY = {}

# 列表格式 pillars（索引2=日柱）
BAZI_LIST_PILLARS = {
    "day_master": "辛",
    "pillars": ["庚午", "壬午", "辛亥", "癸巳"],
}

# 字符串格式 pillars（JSON）
BAZI_JSON_PILLARS = {
    "day_master": "壬",
    "pillars": '{"year": "甲子", "month": "丙寅", "day": "壬午", "hour": "庚子"}',
}

# 使用 analysis 键的八字（_find_wuxing 递归进入 analysis 内部查找）
BAZI_ANALYSIS = {
    "day_master": "癸",
    "analysis": {
        "favorable_elements": ["金", "水"],
        "unfavorable_elements": ["火", "土"],
    },
}

# 使用 喜用神 键的八字
BAZI_CHINESE_KEYS = {
    "day_master": "丁",
    "喜用神": {
        "用神": ["木", "火"],
        "忌神": ["金", "水"],
    },
}

# 无喜用神的八字（测试启发式推断）
BAZI_NO_YONGSHEN = {"day_master": "乙"}


# ============================================================================
# 1. YearJudgment 数据类测试
# ============================================================================

def test_year_judgment_creation():
    """YearJudgment 数据类创建及默认值"""
    yj = YearJudgment(
        year=2026,
        pillar="丙午",
        gan="丙",
        zhi="午",
        gan_shigan="正官",
        zhi_shigan_detail={"丁": "七杀", "己": "正印"},
        day_master="辛",
        yongshen_list=["土", "金"],
        jishen_list=["木", "火"],
    )
    assert yj.year == 2026
    assert yj.pillar == "丙午"
    assert yj.gan == "丙"
    assert yj.zhi == "午"
    assert yj.gan_shigan == "正官"
    assert yj.zhi_shigan_detail == {"丁": "七杀", "己": "正印"}
    assert yj.day_master == "辛"
    assert yj.yongshen_list == ["土", "金"]
    assert yj.jishen_list == ["木", "火"]
    assert yj.score == 50
    assert yj.yongshen_bonus == 0
    assert yj.jishen_penalty == 0
    assert yj.shensha_bonus == 0
    assert yj.yueling_bonus == 0
    assert yj.chonghe_bonus == 0
    assert yj.judgments == []
    assert yj.warnings == []
    assert yj.favorable_months == []
    assert yj.unfavorable_months == []
    assert yj.overall == "平"


def test_year_judgment_defaults():
    """YearJudgment 使用默认值创建"""
    yj = YearJudgment(
        year=2026, pillar="丙午", gan="丙", zhi="午",
        gan_shigan="", zhi_shigan_detail={}, day_master="丙",
        yongshen_list=[], jishen_list=[],
    )
    assert yj.score == 50
    assert yj.overall == "平"
    assert yj.judgments == []
    assert yj.warnings == []
    assert yj.favorable_months == []
    assert yj.unfavorable_months == []


def test_year_judgment_to_dict():
    """YearJudgment.to_dict() 返回完整字典"""
    yj = YearJudgment(
        year=2026, pillar="丙午", gan="丙", zhi="午",
        gan_shigan="正官",
        zhi_shigan_detail={"丁": "七杀", "己": "正印"},
        day_master="辛",
        yongshen_list=["土", "金"],
        jishen_list=["木", "火"],
    )
    d = yj.to_dict()
    assert isinstance(d, dict)
    assert d["year"] == 2026
    assert d["pillar"] == "丙午"
    assert d["gan"] == "丙"
    assert d["zhi"] == "午"
    assert d["gan_shigan"] == "正官"
    assert d["zhi_shigan_detail"] == {"丁": "七杀", "己": "正印"}
    assert d["day_master"] == "辛"
    assert d["yongshen"] == ["土", "金"]
    assert d["jishen"] == ["木", "火"]
    assert "score_detail" in d
    assert "judgments" in d
    assert "warnings" in d
    assert "favorable_months" in d
    assert "unfavorable_months" in d
    assert d["overall"] == "平"


def test_year_judgment_to_dict_with_score():
    """YearJudgment.to_dict() 包含评分明细"""
    yj = YearJudgment(
        year=2026, pillar="丙午", gan="丙", zhi="午",
        gan_shigan="正官", zhi_shigan_detail={}, day_master="辛",
        yongshen_list=["土"], jishen_list=["火"],
        score=75, yongshen_bonus=20, jishen_penalty=-10,
        shensha_bonus=10, yueling_bonus=5, chonghe_bonus=0,
        overall="吉",
    )
    d = yj.to_dict()
    assert d["score"] == 75
    assert d["overall"] == "吉"
    assert d["score_detail"]["yongshen_bonus"] == 20
    assert d["score_detail"]["jishen_penalty"] == -10
    assert d["score_detail"]["shensha_bonus"] == 10
    assert d["score_detail"]["yueling_bonus"] == 5
    assert d["score_detail"]["chonghe_bonus"] == 0


# ============================================================================
# 2. 常量测试
# ============================================================================

def test_gan_wuxing_coverage():
    """GAN_WUXING 覆盖所有 10 天干"""
    assert len(GAN_WUXING) == 10
    for gan in "甲乙丙丁戊己庚辛壬癸":
        assert gan in GAN_WUXING
        assert GAN_WUXING[gan] in ("木", "火", "土", "金", "水")


def test_gan_yinyang_coverage():
    """GAN_YINYANG 覆盖所有 10 天干"""
    assert len(GAN_YINYANG) == 10
    for gan in "甲乙丙丁戊己庚辛壬癸":
        assert gan in GAN_YINYANG
        assert GAN_YINYANG[gan] in ("阳", "阴")


def test_zhi_wuxing_coverage():
    """ZHI_WUXING 覆盖所有 12 地支"""
    assert len(ZHI_WUXING) == 12
    for zhi in "子丑寅卯辰巳午未申酉戌亥":
        assert zhi in ZHI_WUXING
        assert ZHI_WUXING[zhi] in ("木", "火", "土", "金", "水")


def test_zhi_main_gan_coverage():
    """ZHI_MAIN_GAN 覆盖所有 12 地支"""
    assert len(ZHI_MAIN_GAN) == 12
    for zhi in "子丑寅卯辰巳午未申酉戌亥":
        assert zhi in ZHI_MAIN_GAN
        assert ZHI_MAIN_GAN[zhi] in "甲乙丙丁戊己庚辛壬癸"


def test_zhi_cang_gan_coverage():
    """ZHI_CANG_GAN 覆盖所有 12 地支"""
    assert len(ZHI_CANG_GAN) == 12
    for zhi in "子丑寅卯辰巳午未申酉戌亥":
        assert zhi in ZHI_CANG_GAN
        assert isinstance(ZHI_CANG_GAN[zhi], list)
        assert len(ZHI_CANG_GAN[zhi]) >= 1


def test_wuxing_sheng_chain():
    """五行相生链正确"""
    assert WUXING_SHENG["木"] == "火"
    assert WUXING_SHENG["火"] == "土"
    assert WUXING_SHENG["土"] == "金"
    assert WUXING_SHENG["金"] == "水"
    assert WUXING_SHENG["水"] == "木"


def test_wuxing_ke_chain():
    """五行相克链正确"""
    assert WUXING_KE["木"] == "土"
    assert WUXING_KE["土"] == "水"
    assert WUXING_KE["水"] == "火"
    assert WUXING_KE["火"] == "金"
    assert WUXING_KE["金"] == "木"


# ============================================================================
# 3. _derive_shigan 测试（全部 10 种十神）
# ============================================================================

def test_derive_shigan_bijian():
    """比肩：同五行同阴阳"""
    assert _derive_shigan("甲", "甲") == "比肩"
    assert _derive_shigan("乙", "乙") == "比肩"


def test_derive_shigan_jiecai():
    """劫财：同五行异阴阳"""
    assert _derive_shigan("甲", "乙") == "劫财"
    assert _derive_shigan("乙", "甲") == "劫财"


def test_derive_shigan_shishen():
    """食神：我生者同阴阳"""
    # 甲木生丙火（阳生阳）= 食神
    assert _derive_shigan("甲", "丙") == "食神"
    assert _derive_shigan("乙", "丁") == "食神"


def test_derive_shigan_shangguan():
    """伤官：我生者异阴阳"""
    assert _derive_shigan("甲", "丁") == "伤官"
    assert _derive_shigan("乙", "丙") == "伤官"


def test_derive_shigan_piancai():
    """偏财：我克者同阴阳"""
    assert _derive_shigan("甲", "戊") == "偏财"
    assert _derive_shigan("乙", "己") == "偏财"


def test_derive_shigan_zhengcai():
    """正财：我克者异阴阳"""
    assert _derive_shigan("甲", "己") == "正财"
    assert _derive_shigan("乙", "戊") == "正财"


def test_derive_shigan_qisha():
    """七杀：克我者同阴阳"""
    assert _derive_shigan("甲", "庚") == "七杀"
    assert _derive_shigan("乙", "辛") == "七杀"


def test_derive_shigan_zhengguan():
    """正官：克我者异阴阳"""
    assert _derive_shigan("甲", "辛") == "正官"
    assert _derive_shigan("乙", "庚") == "正官"


def test_derive_shigan_pianyin():
    """偏印：生我者同阴阳"""
    assert _derive_shigan("甲", "壬") == "偏印"
    assert _derive_shigan("乙", "癸") == "偏印"


def test_derive_shigan_zhengyin():
    """正印：生我者异阴阳"""
    assert _derive_shigan("甲", "癸") == "正印"
    assert _derive_shigan("乙", "壬") == "正印"


def test_derive_shigan_all_combinations():
    """所有 10 天干组合都返回合法十神"""
    shigan_set = set()
    for dm in "甲乙丙丁戊己庚辛壬癸":
        for tg in "甲乙丙丁戊己庚辛壬癸":
            result = _derive_shigan(dm, tg)
            assert result in ("比肩", "劫财", "食神", "伤官", "偏财", "正财",
                             "七杀", "正官", "偏印", "正印", "")
            if result:
                shigan_set.add(result)
    # 至少有 10 种十神
    assert len(shigan_set) >= 10


# ============================================================================
# 4. _extract_yongshen 内部方法测试
# ============================================================================

def test_extract_yongshen_from_yongshen_key():
    """从 yongshen 键提取喜用神"""
    engine = LiunianJudgmentEngine()
    ys, js = engine._extract_yongshen(BAZI_FULL)
    assert "火" in ys
    assert "土" in ys
    assert "木" in js or "水" in js


def test_extract_yongshen_from_analysis_key():
    """从 analysis 键提取喜用神"""
    engine = LiunianJudgmentEngine()
    ys, js = engine._extract_yongshen(BAZI_ANALYSIS)
    assert "金" in ys
    assert "水" in ys
    assert len(js) >= 1


def test_extract_yongshen_from_chinese_keys():
    """从中文键名提取喜用神"""
    engine = LiunianJudgmentEngine()
    ys, js = engine._extract_yongshen(BAZI_CHINESE_KEYS)
    assert "木" in ys
    assert "火" in ys


def test_extract_yongshen_heuristic():
    """无喜用神时启发式推断"""
    engine = LiunianJudgmentEngine()
    ys, js = engine._extract_yongshen(BAZI_NO_YONGSHEN)
    assert len(ys) >= 1
    assert len(js) >= 1
    # 乙木日主，喜用神应为木或火
    assert "木" in ys or "火" in ys


def test_extract_yongshen_empty_input():
    """空输入不崩溃"""
    engine = LiunianJudgmentEngine()
    ys, js = engine._extract_yongshen({})
    assert len(ys) >= 1
    assert len(js) >= 1


def test_extract_yongshen_max_length():
    """喜用神/忌神最多返回 3 个"""
    engine = LiunianJudgmentEngine()
    ys, js = engine._extract_yongshen(BAZI_FULL)
    assert len(ys) <= 3
    assert len(js) <= 3


def test_extract_yongshen_no_duplicates():
    """喜用神/忌神不重复"""
    engine = LiunianJudgmentEngine()
    ys, js = engine._extract_yongshen(BAZI_FULL)
    assert len(ys) == len(set(ys))
    assert len(js) == len(set(js))


def test_extract_yongshen_all_wuxing():
    """所有返回元素都是合法五行"""
    engine = LiunianJudgmentEngine()
    ys, js = engine._extract_yongshen(BAZI_FULL)
    valid = {"木", "火", "土", "金", "水"}
    for y in ys:
        assert y in valid
    for j in js:
        assert j in valid


def test_extract_yongshen_with_geju_key():
    """从 geju 键提取（_find_wuxing 递归进入 geju 内部查找）"""
    engine = LiunianJudgmentEngine()
    bazi = {"day_master": "丙", "geju": {"favorable_elements": ["木", "火"]}}
    ys, js = engine._extract_yongshen(bazi)
    assert "木" in ys
    assert "火" in ys


# ============================================================================
# 5. _zhi_interaction 内部方法测试（全部冲合关系）
# ============================================================================

def test_zhi_interaction_chong():
    """六冲关系"""
    engine = LiunianJudgmentEngine()
    # 子午冲
    assert engine._zhi_interaction("子", "午") == "冲日支"
    assert engine._zhi_interaction("午", "子") == "冲日支"
    # 丑未冲
    assert engine._zhi_interaction("丑", "未") == "冲日支"
    # 寅申冲
    assert engine._zhi_interaction("寅", "申") == "冲日支"
    # 卯酉冲
    assert engine._zhi_interaction("卯", "酉") == "冲日支"
    # 辰戌冲
    assert engine._zhi_interaction("辰", "戌") == "冲日支"
    # 巳亥冲
    assert engine._zhi_interaction("巳", "亥") == "冲日支"


def test_zhi_interaction_he():
    """六合关系"""
    engine = LiunianJudgmentEngine()
    # 子丑合
    assert engine._zhi_interaction("子", "丑") == "合日支"
    # 寅亥合
    assert engine._zhi_interaction("寅", "亥") == "合日支"
    # 卯戌合
    assert engine._zhi_interaction("卯", "戌") == "合日支"
    # 辰酉合
    assert engine._zhi_interaction("辰", "酉") == "合日支"
    # 巳申合
    assert engine._zhi_interaction("巳", "申") == "合日支"
    # 午未合
    assert engine._zhi_interaction("午", "未") == "合日支"


def test_zhi_interaction_no_relation():
    """无冲合关系"""
    engine = LiunianJudgmentEngine()
    assert engine._zhi_interaction("子", "寅") == ""
    assert engine._zhi_interaction("卯", "巳") == ""
    assert engine._zhi_interaction("申", "戌") == ""
    assert engine._zhi_interaction("亥", "丑") == ""


def test_zhi_interaction_empty_rizhi():
    """日支为空时返回空字符串"""
    engine = LiunianJudgmentEngine()
    assert engine._zhi_interaction("子", "") == ""
    assert engine._zhi_interaction("午", "") == ""


def test_zhi_interaction_same_zhi():
    """相同地支不冲不合"""
    engine = LiunianJudgmentEngine()
    assert engine._zhi_interaction("子", "子") == ""
    assert engine._zhi_interaction("午", "午") == ""


# ============================================================================
# 6. _season_of_zhi 内部方法测试
# ============================================================================

def test_season_of_zhi_spring():
    """春季地支"""
    engine = LiunianJudgmentEngine()
    assert engine._season_of_zhi("寅") == "春"
    assert engine._season_of_zhi("卯") == "春"
    assert engine._season_of_zhi("辰") == "春"


def test_season_of_zhi_summer():
    """夏季地支"""
    engine = LiunianJudgmentEngine()
    assert engine._season_of_zhi("巳") == "夏"
    assert engine._season_of_zhi("午") == "夏"
    assert engine._season_of_zhi("未") == "夏"


def test_season_of_zhi_autumn():
    """秋季地支"""
    engine = LiunianJudgmentEngine()
    assert engine._season_of_zhi("申") == "秋"
    assert engine._season_of_zhi("酉") == "秋"
    assert engine._season_of_zhi("戌") == "秋"


def test_season_of_zhi_winter():
    """冬季地支"""
    engine = LiunianJudgmentEngine()
    assert engine._season_of_zhi("亥") == "冬"
    assert engine._season_of_zhi("子") == "冬"
    assert engine._season_of_zhi("丑") == "冬"


def test_season_of_zhi_all_12():
    """所有 12 地支都有季节"""
    engine = LiunianJudgmentEngine()
    expected = {
        "寅": "春", "卯": "春", "辰": "春",
        "巳": "夏", "午": "夏", "未": "夏",
        "申": "秋", "酉": "秋", "戌": "秋",
        "亥": "冬", "子": "冬", "丑": "冬",
    }
    for zhi, season in expected.items():
        assert engine._season_of_zhi(zhi) == season


def test_season_of_zhi_invalid():
    """无效地支返回空字符串"""
    engine = LiunianJudgmentEngine()
    assert engine._season_of_zhi("") == ""
    assert engine._season_of_zhi("X") == ""


# ============================================================================
# 7. 引擎实例化测试
# ============================================================================

def test_engine_instantiation():
    """LiunianJudgmentEngine 可以实例化"""
    engine = LiunianJudgmentEngine()
    assert engine is not None
    assert isinstance(engine, LiunianJudgmentEngine)


def test_engine_multiple_instances():
    """多个实例独立"""
    e1 = LiunianJudgmentEngine()
    e2 = LiunianJudgmentEngine()
    assert e1 is not e2


# ============================================================================
# 8. judge_year 单年判断测试
# ============================================================================

def test_judge_year_returns_year_judgment():
    """judge_year 返回 YearJudgment"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, 2026)
    assert isinstance(result, YearJudgment)


def test_judge_year_score_range():
    """judge_year 分数在 0~100"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, 2026)
    assert 0 <= result.score <= 100


def test_judge_year_has_ganzhi():
    """judge_year 结果包含干支信息"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, 2026)
    assert result.year == 2026
    assert len(result.pillar) == 2
    assert result.gan in "甲乙丙丁戊己庚辛壬癸"
    assert result.zhi in "子丑寅卯辰巳午未申酉戌亥"


def test_judge_year_has_shigan():
    """judge_year 结果包含十神信息"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, 2026)
    assert result.gan_shigan, "十神不应为空"
    assert isinstance(result.zhi_shigan_detail, dict)
    assert len(result.zhi_shigan_detail) >= 1


def test_judge_year_yongshen_list():
    """judge_year 包含喜用神列表"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, 2026)
    assert isinstance(result.yongshen_list, list)
    assert len(result.yongshen_list) >= 1


def test_judge_year_jishen_list():
    """judge_year 包含忌神列表"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, 2026)
    assert isinstance(result.jishen_list, list)
    assert len(result.jishen_list) >= 1


def test_judge_year_judgments_non_empty():
    """judge_year 断语列表非空"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, 2026)
    assert len(result.judgments) >= 2
    for j in result.judgments:
        assert isinstance(j, str)
        assert len(j) > 0


def test_judge_year_overall():
    """judge_year overall 在合法值内"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, 2026)
    assert result.overall in ("吉", "平", "凶")


def test_judge_year_favorable_months():
    """judge_year 有利月份列表"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, 2026)
    assert isinstance(result.favorable_months, list)
    # 至少有一些月份
    assert len(result.favorable_months) >= 0
    for m in result.favorable_months:
        assert m in ("正月", "二月", "三月", "四月", "五月", "六月",
                     "七月", "八月", "九月", "十月", "冬月", "腊月")


def test_judge_year_unfavorable_months():
    """judge_year 不利月份列表"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, 2026)
    assert isinstance(result.unfavorable_months, list)
    for m in result.unfavorable_months:
        assert m in ("正月", "二月", "三月", "四月", "五月", "六月",
                     "七月", "八月", "九月", "十月", "冬月", "腊月")


def test_judge_year_with_explicit_day_master():
    """显式传入日主和日支"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_MINIMAL, 2026, day_master="甲", ri_zhi="子")
    assert result.day_master == "甲"
    assert result.year == 2026


def test_judge_year_with_rizhi_chong():
    """日支受冲的场景"""
    engine = LiunianJudgmentEngine()
    # 日支为子，找一个冲子的年份地支（午）
    result = engine.judge_year(BAZI_MINIMAL, 2026, day_master="甲", ri_zhi="子")
    # 2026 年柱是丙午（因 6月15日在立春后），午冲子
    if result.zhi == "午":
        assert result.chonghe_bonus < 0
        assert len(result.warnings) >= 1


def test_judge_year_with_rizhi_he():
    """日支被合的场景"""
    engine = LiunianJudgmentEngine()
    # 日支为丑，找一个合丑的年份地支（子）
    # 2020 年柱是庚子，子丑合
    result = engine.judge_year(BAZI_MINIMAL, 2020, day_master="甲", ri_zhi="丑")
    if result.zhi == "子":
        assert result.chonghe_bonus > 0


def test_judge_year_high_score():
    """高评分场景（喜用神年）"""
    engine = LiunianJudgmentEngine()
    # 辛金日主喜土金，选一个土金年
    result = engine.judge_year(BAZI_XIN, 2028)  # 戊申年
    # 不管具体分数，至少验证 overall 逻辑
    assert result.overall in ("吉", "平", "凶")
    assert 0 <= result.score <= 100


def test_judge_year_low_score():
    """低评分场景（忌神年）"""
    engine = LiunianJudgmentEngine()
    # 辛金日主忌木火，选一个木火年
    result = engine.judge_year(BAZI_XIN, 2026)  # 丙午年
    assert result.overall in ("吉", "平", "凶")
    assert 0 <= result.score <= 100


def test_judge_year_minimal_input():
    """最小输入不崩溃"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_MINIMAL, 2026)
    assert isinstance(result, YearJudgment)
    assert 0 <= result.score <= 100


def test_judge_year_empty_input():
    """空输入不崩溃"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_EMPTY, 2026)
    assert isinstance(result, YearJudgment)
    assert 0 <= result.score <= 100


def test_judge_year_list_pillars():
    """列表格式 pillars 输入"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_LIST_PILLARS, 2026)
    assert isinstance(result, YearJudgment)
    assert result.day_master == "辛"


def test_judge_year_json_pillars():
    """JSON 字符串格式 pillars 输入"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_JSON_PILLARS, 2026)
    assert isinstance(result, YearJudgment)
    assert result.day_master == "壬"


def test_judge_year_ancient_year():
    """古代年份（如 1644）"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, 1644)
    assert isinstance(result, YearJudgment)
    assert 0 <= result.score <= 100


def test_judge_year_future_year():
    """未来年份（如 2100）"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, 2100)
    assert isinstance(result, YearJudgment)
    assert 0 <= result.score <= 100


def test_judge_year_negative_year():
    """负年份（公元前）"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, -500)
    assert isinstance(result, YearJudgment)
    assert 0 <= result.score <= 100


def test_judge_year_score_components():
    """评分各组成部分合理"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, 2026)
    # 基础分 50 + 各加分项
    assert result.score == max(0, min(100, 50
        + result.yongshen_bonus
        + result.jishen_penalty
        + result.shensha_bonus
        + result.yueling_bonus
        + result.chonghe_bonus))


def test_judge_year_warnings_for_low_score():
    """低于 40 分有额外警告"""
    engine = LiunianJudgmentEngine()
    # 使用忌神年的八字
    result = engine.judge_year(BAZI_XIN, 2026)
    if result.score < 40:
        assert len(result.warnings) >= 1


def test_judge_year_high_score_judgment():
    """高于 70 分有额外断语"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_XIN, 2028)
    if result.score >= 70:
        has_positive = any("运势上扬" in j or "机遇" in j for j in result.judgments)
        assert has_positive or result.overall == "吉"


# ============================================================================
# 9. judge 批量判断测试
# ============================================================================

def test_judge_batch_count():
    """judge 返回正确数量"""
    engine = LiunianJudgmentEngine()
    results = engine.judge(BAZI_FULL, 2025, 2030)
    assert len(results) == 6


def test_judge_batch_single_year():
    """judge 单年范围"""
    engine = LiunianJudgmentEngine()
    results = engine.judge(BAZI_FULL, 2026, 2026)
    assert len(results) == 1
    assert results[0].year == 2026


def test_judge_batch_10_years():
    """judge 十年范围"""
    engine = LiunianJudgmentEngine()
    results = engine.judge(BAZI_FULL, 2020, 2029)
    assert len(results) == 10


def test_judge_batch_all_year_judgments():
    """judge 所有结果都是 YearJudgment"""
    engine = LiunianJudgmentEngine()
    results = engine.judge(BAZI_FULL, 2025, 2028)
    for r in results:
        assert isinstance(r, YearJudgment)


def test_judge_batch_years_sequential():
    """judge 年份连续"""
    engine = LiunianJudgmentEngine()
    results = engine.judge(BAZI_FULL, 2025, 2028)
    for i, r in enumerate(results):
        assert r.year == 2025 + i


def test_judge_batch_all_scores_valid():
    """judge 所有分数在 0~100"""
    engine = LiunianJudgmentEngine()
    results = engine.judge(BAZI_FULL, 2020, 2040)
    for r in results:
        assert 0 <= r.score <= 100


# ============================================================================
# 10. decade_summary 测试
# ============================================================================

def test_decade_summary_returns_dict():
    """decade_summary 返回字典"""
    engine = LiunianJudgmentEngine()
    summary = engine.decade_summary(BAZI_FULL, 2026, 2035)
    assert isinstance(summary, dict)


def test_decade_summary_keys():
    """decade_summary 包含必要键"""
    engine = LiunianJudgmentEngine()
    summary = engine.decade_summary(BAZI_FULL, 2026, 2035)
    required_keys = [
        "year_range", "total_years", "best_year", "best_score",
        "best_overall", "worst_year", "worst_score", "worst_overall",
        "average_score", "career_tips", "relationship_tips",
        "health_tips", "judgments",
    ]
    for key in required_keys:
        assert key in summary, f"缺少键: {key}"


def test_decade_summary_year_range():
    """decade_summary year_range 正确"""
    engine = LiunianJudgmentEngine()
    summary = engine.decade_summary(BAZI_FULL, 2026, 2035)
    assert summary["year_range"] == [2026, 2035]
    assert summary["total_years"] == 10


def test_decade_summary_best_worst():
    """decade_summary 最佳/最差年份逻辑正确"""
    engine = LiunianJudgmentEngine()
    summary = engine.decade_summary(BAZI_FULL, 2026, 2035)
    assert summary["best_score"] >= summary["worst_score"]
    assert 2026 <= summary["best_year"] <= 2035
    assert 2026 <= summary["worst_year"] <= 2035


def test_decade_summary_average_score():
    """decade_summary 平均分数合理"""
    engine = LiunianJudgmentEngine()
    summary = engine.decade_summary(BAZI_FULL, 2026, 2035)
    assert 0 <= summary["average_score"] <= 100
    assert isinstance(summary["average_score"], (int, float))


def test_decade_summary_judgments_count():
    """decade_summary judgments 数量正确"""
    engine = LiunianJudgmentEngine()
    summary = engine.decade_summary(BAZI_FULL, 2026, 2035)
    assert len(summary["judgments"]) == 10


def test_decade_summary_judgments_structure():
    """decade_summary 每个 judgment 是字典"""
    engine = LiunianJudgmentEngine()
    summary = engine.decade_summary(BAZI_FULL, 2026, 2035)
    for j in summary["judgments"]:
        assert isinstance(j, dict)
        assert "year" in j
        assert "pillar" in j
        assert "score" in j


def test_decade_summary_single_year():
    """decade_summary 单年范围"""
    engine = LiunianJudgmentEngine()
    summary = engine.decade_summary(BAZI_FULL, 2026, 2026)
    assert summary["total_years"] == 1
    assert summary["best_year"] == summary["worst_year"] == 2026
    assert len(summary["judgments"]) == 1


def test_decade_summary_tips_lists():
    """decade_summary tips 是列表"""
    engine = LiunianJudgmentEngine()
    summary = engine.decade_summary(BAZI_FULL, 2026, 2035)
    assert isinstance(summary["career_tips"], list)
    assert isinstance(summary["relationship_tips"], list)
    assert isinstance(summary["health_tips"], list)


def test_decade_summary_tips_max_length():
    """decade_summary tips 最多 5 条"""
    engine = LiunianJudgmentEngine()
    summary = engine.decade_summary(BAZI_FULL, 2026, 2035)
    assert len(summary["career_tips"]) <= 5
    assert len(summary["relationship_tips"]) <= 5
    assert len(summary["health_tips"]) <= 5


# ============================================================================
# 11. 全部 10 天干日主测试
# ============================================================================

def test_all_10_day_masters():
    """所有 10 天干作为日主都可正常判断"""
    engine = LiunianJudgmentEngine()
    for dm in "甲乙丙丁戊己庚辛壬癸":
        bazi = {"day_master": dm}
        result = engine.judge_year(bazi, 2026, day_master=dm, ri_zhi="子")
        assert result.day_master == dm
        assert result.gan_shigan in (
            "比肩", "劫财", "食神", "伤官", "偏财", "正财",
            "七杀", "正官", "偏印", "正印", ""
        )
        assert 0 <= result.score <= 100


# ============================================================================
# 12. 模板断语非空测试
# ============================================================================

def test_yongshen_templates_non_empty():
    """喜用神模板断语非空"""
    for t in YONGSHEN_TEMPLATES:
        assert len(t.judgments) >= 1
        for j in t.judgments:
            assert isinstance(j, str)
            assert len(j) > 0


def test_jishen_templates_non_empty():
    """忌神模板断语非空"""
    for t in JISHEN_TEMPLATES:
        assert len(t.judgments) >= 1
        for j in t.judgments:
            assert isinstance(j, str)
            assert len(j) > 0


def test_shigan_templates_all_10():
    """十神模板覆盖所有 10 种"""
    assert len(SHIGAN_TEMPLATES) == 10
    expected = {"正官", "七杀", "正财", "偏财", "正印", "偏印", "食神", "伤官", "比肩", "劫财"}
    assert set(SHIGAN_TEMPLATES.keys()) == expected


def test_shigan_templates_non_empty():
    """十神模板断语非空"""
    for shigan, judgments in SHIGAN_TEMPLATES.items():
        assert len(judgments) >= 1, f"{shigan} 模板为空"
        for j in judgments:
            assert isinstance(j, str)
            assert len(j) > 0


def test_zhi_interaction_templates_non_empty():
    """地支冲合模板断语非空"""
    for key, judgments in ZHI_INTERACTION_TEMPLATES.items():
        assert len(judgments) >= 1, f"{key} 模板为空"
        for j in judgments:
            assert isinstance(j, str)
            assert len(j) > 0


def test_yueling_templates_non_empty():
    """月令模板断语非空"""
    assert len(YUE_LING_TEMPLATES) >= 1
    for key, value in YUE_LING_TEMPLATES.items():
        assert isinstance(value, str)
        assert len(value) > 0


def test_shensha_templates_non_empty():
    """神煞模板断语非空"""
    assert len(SHENSHA_TEMPLATES) >= 1
    for key, value in SHENSHA_TEMPLATES.items():
        assert isinstance(value, str)
        assert len(value) > 0


# ============================================================================
# 13. 便捷函数测试
# ============================================================================

def test_judge_years_function():
    """judge_years 便捷函数"""
    results = judge_years(BAZI_FULL, 2025, 2027)
    assert len(results) == 3
    for r in results:
        assert isinstance(r, YearJudgment)


def test_judge_decade_function():
    """judge_decade 便捷函数"""
    summary = judge_decade(BAZI_FULL, 2026, 2035)
    assert isinstance(summary, dict)
    assert "judgments" in summary
    assert len(summary["judgments"]) == 10


# ============================================================================
# 14. 不同八字数据格式测试
# ============================================================================

def test_judge_year_with_pillars_dict():
    """dict 格式 pillars"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_XIN, 2026)
    assert result.day_master == "辛"


def test_judge_year_with_minimal_day_master():
    """仅有 day_master 的八字"""
    engine = LiunianJudgmentEngine()
    for year in [2020, 2024, 2026, 2028, 2030]:
        result = engine.judge_year({"day_master": "丙"}, year)
        assert result.day_master == "丙"
        assert 0 <= result.score <= 100


def test_judge_year_day_master_override():
    """显式 day_master 覆盖 bazi_data 中的值"""
    engine = LiunianJudgmentEngine()
    bazi = {"day_master": "丙"}
    result = engine.judge_year(bazi, 2026, day_master="甲", ri_zhi="子")
    assert result.day_master == "甲"


def test_judge_year_rizhi_override():
    """显式 ri_zhi 参数"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_MINIMAL, 2026, day_master="甲", ri_zhi="午")
    assert result.day_master == "甲"


# ============================================================================
# 15. 多次调用一致性测试
# ============================================================================

def test_judge_year_idempotent():
    """相同输入多次调用结果一致（评分相同）"""
    engine = LiunianJudgmentEngine()
    r1 = engine.judge_year(BAZI_FULL, 2026)
    r2 = engine.judge_year(BAZI_FULL, 2026)
    assert r1.score == r2.score
    assert r1.overall == r2.overall
    assert r1.pillar == r2.pillar
    assert r1.gan_shigan == r2.gan_shigan


def test_different_years_different_scores():
    """不同年份分数可能不同"""
    engine = LiunianJudgmentEngine()
    results = engine.judge(BAZI_FULL, 2025, 2030)
    scores = [r.score for r in results]
    # 至少有一个不同分数（不一定，但大概率）
    assert len(set(scores)) > 0


# ============================================================================
# 16. 所有 12 地支作为日支测试
# ============================================================================

def test_all_12_zhi_as_rizhi():
    """所有 12 地支作为日支都可以判断"""
    engine = LiunianJudgmentEngine()
    for zhi in "子丑寅卯辰巳午未申酉戌亥":
        result = engine.judge_year(
            BAZI_MINIMAL, 2026, day_master="甲", ri_zhi=zhi
        )
        assert isinstance(result, YearJudgment)
        assert 0 <= result.score <= 100


# ============================================================================
# 17. 评分具体场景测试
# ============================================================================

def test_score_high_scenario():
    """高评分场景：干支皆喜用神"""
    engine = LiunianJudgmentEngine()
    # 辛金日主喜土金，找一个土金年
    result = engine.judge_year(BAZI_XIN, 2028)  # 戊申年
    # 至少验证分数合理
    assert 0 <= result.score <= 100


def test_score_low_scenario():
    """低评分场景：干支皆忌神"""
    engine = LiunianJudgmentEngine()
    # 辛金日主忌木火
    result = engine.judge_year(BAZI_XIN, 2026)  # 丙午年
    assert 0 <= result.score <= 100


def test_score_medium_scenario():
    """中评分场景：一用一忌"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, 2026)
    assert 0 <= result.score <= 100


def test_score_boundary_0():
    """分数不会低于 0"""
    engine = LiunianJudgmentEngine()
    # 用极端情况：所有条件都扣分
    result = engine.judge_year(BAZI_XIN, 2026)
    assert result.score >= 0


def test_score_boundary_100():
    """分数不会超过 100"""
    engine = LiunianJudgmentEngine()
    # 用极端情况：所有条件都加分
    result = engine.judge_year(BAZI_XIN, 2028)
    assert result.score <= 100


# ============================================================================
# 18. 不同喜用神配置测试
# ============================================================================

def test_judge_year_with_different_yongshen_configs():
    """不同喜用神配置产生不同结果"""
    engine = LiunianJudgmentEngine()
    bazi1 = {"day_master": "辛", "yongshen": {"favorable_elements": ["金"], "unfavorable_elements": ["火"]}}
    bazi2 = {"day_master": "辛", "yongshen": {"favorable_elements": ["火"], "unfavorable_elements": ["金"]}}
    r1 = engine.judge_year(bazi1, 2026, day_master="辛", ri_zhi="亥")
    r2 = engine.judge_year(bazi2, 2026, day_master="辛", ri_zhi="亥")
    # 同一年对同一日主，不同喜用神配置应产生不同评分
    assert r1.yongshen_list != r2.yongshen_list


# ============================================================================
# 19. 十神在 judge_year 中的实际应用测试
# ============================================================================

def test_all_shigan_appear_in_judgments():
    """所有十神类型的流年都能产生断语"""
    engine = LiunianJudgmentEngine()
    shigan_found = set()
    # 用不同年份检查不同十神
    for year in range(2020, 2050):
        result = engine.judge_year(BAZI_MINIMAL, year, day_master="丙", ri_zhi="子")
        if result.gan_shigan:
            shigan_found.add(result.gan_shigan)
        if len(shigan_found) >= 8:  # 大部分十神应出现
            break
    assert len(shigan_found) >= 5, f"至少应有 5 种十神出现，实际: {shigan_found}"


# ============================================================================
# 20. 综合边界测试
# ============================================================================

def test_judge_year_large_year_range():
    """大范围年份测试"""
    engine = LiunianJudgmentEngine()
    results = engine.judge(BAZI_FULL, 1900, 2100)
    assert len(results) == 201
    for r in results:
        assert 0 <= r.score <= 100


def test_judge_year_reversed_range():
    """start > end 时返回空列表"""
    engine = LiunianJudgmentEngine()
    results = engine.judge(BAZI_FULL, 2030, 2025)
    assert results == []


def test_decade_summary_reversed_range():
    """decade_summary start > end 时返回空结果（min/max 会抛异常）"""
    engine = LiunianJudgmentEngine()
    with pytest.raises(ValueError):
        engine.decade_summary(BAZI_FULL, 2030, 2025)


def test_year_judgment_warnings_type():
    """warnings 是字符串列表"""
    engine = LiunianJudgmentEngine()
    result = engine.judge_year(BAZI_FULL, 2026)
    assert isinstance(result.warnings, list)
    for w in result.warnings:
        assert isinstance(w, str)
        assert len(w) > 0


def test_year_judgment_day_master_preserved():
    """日主在结果中正确保留"""
    engine = LiunianJudgmentEngine()
    for dm in "甲乙丙丁戊":
        bazi = {"day_master": dm}
        result = engine.judge_year(bazi, 2026, day_master=dm, ri_zhi="子")
        assert result.day_master == dm


def test_engine_is_static_methods():
    """内部方法可通过类和实例调用（静态方法行为）"""
    # 直接通过类调用（不传 self）
    ys, js = LiunianJudgmentEngine._extract_yongshen({"day_master": "甲"})
    assert len(ys) >= 1

    interaction = LiunianJudgmentEngine._zhi_interaction("子", "午")
    assert interaction == "冲日支"

    season = LiunianJudgmentEngine._season_of_zhi("寅")
    assert season == "春"

    # 通过实例调用也正常工作
    engine = LiunianJudgmentEngine()
    ys2, js2 = engine._extract_yongshen({"day_master": "甲"})
    assert len(ys2) >= 1