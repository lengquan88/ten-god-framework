"""
name_engine.py 综合测试

覆盖：
- WugeResult / NameAnalysis 数据模型
- KANGXI_STROKES 字典查询
- NameEngine 所有公有/内部方法
- analyze_name 便捷函数
- 边界情况（空字符串、非中文、长名等）
"""

import pytest
from tengod.name_engine import (
    NameEngine,
    NameAnalysis,
    WugeResult,
    analyze_name,
    KANGXI_STROKES,
    SANCAI_JIXIONG,
    _SHU_LI_JI_XIONG,
    BIHUA_WUXING,
)


# ============================================================================
# WugeResult 数据模型
# ============================================================================

class TestWugeResult:
    """WugeResult 数据类测试"""

    def test_create_default(self):
        r = WugeResult(
            tian_ge=5, ren_ge=15, di_ge=10, wai_ge=6, zong_ge=20,
            tian_ge_ji="大吉", ren_ge_ji="大吉", di_ge_ji="大吉",
            wai_ge_ji="大吉", zong_ge_ji="大吉",
        )
        assert r.tian_ge == 5
        assert r.ren_ge == 15
        assert r.di_ge == 10
        assert r.wai_ge == 6
        assert r.zong_ge == 20
        assert r.tian_ge_ji == "大吉"
        assert r.ren_ge_ji == "大吉"
        assert r.di_ge_ji == "大吉"
        assert r.wai_ge_ji == "大吉"
        assert r.zong_ge_ji == "大吉"

    def test_create_with_xiong(self):
        r = WugeResult(
            tian_ge=4, ren_ge=12, di_ge=14, wai_ge=7, zong_ge=19,
            tian_ge_ji="凶", ren_ge_ji="凶", di_ge_ji="凶",
            wai_ge_ji="大吉", zong_ge_ji="凶",
        )
        assert r.tian_ge_ji == "凶"
        assert r.ren_ge_ji == "凶"
        assert r.zong_ge_ji == "凶"

    def test_all_fields_are_ints(self):
        r = WugeResult(
            tian_ge=1, ren_ge=2, di_ge=3, wai_ge=4, zong_ge=5,
            tian_ge_ji="大吉", ren_ge_ji="大吉", di_ge_ji="大吉",
            wai_ge_ji="大吉", zong_ge_ji="大吉",
        )
        assert isinstance(r.tian_ge, int)
        assert isinstance(r.ren_ge, int)
        assert isinstance(r.di_ge, int)
        assert isinstance(r.wai_ge, int)
        assert isinstance(r.zong_ge, int)

    def test_all_ji_fields_are_str(self):
        r = WugeResult(
            tian_ge=1, ren_ge=2, di_ge=3, wai_ge=4, zong_ge=5,
            tian_ge_ji="大吉", ren_ge_ji="大吉", di_ge_ji="大吉",
            wai_ge_ji="大吉", zong_ge_ji="大吉",
        )
        assert isinstance(r.tian_ge_ji, str)
        assert isinstance(r.ren_ge_ji, str)
        assert isinstance(r.di_ge_ji, str)
        assert isinstance(r.wai_ge_ji, str)
        assert isinstance(r.zong_ge_ji, str)


# ============================================================================
# NameAnalysis 数据模型
# ============================================================================

class TestNameAnalysis:
    """NameAnalysis 数据类测试"""

    def _make_wuge(self):
        return WugeResult(
            tian_ge=5, ren_ge=15, di_ge=10, wai_ge=6, zong_ge=20,
            tian_ge_ji="大吉", ren_ge_ji="大吉", di_ge_ji="大吉",
            wai_ge_ji="大吉", zong_ge_ji="大吉",
        )

    def test_create_full(self):
        wuge = self._make_wuge()
        result = NameAnalysis(
            surname="张",
            given_name="伟",
            surname_strokes=11,
            given_strokes=[11],
            wuge=wuge,
            sancai=("木", "木", "木"),
            sancai_ji="大吉",
            sancai_desc="顺利发展",
            overall_score=85.0,
            overall_grade="优",
            suggestions=["建议1", "建议2"],
        )
        assert result.surname == "张"
        assert result.given_name == "伟"
        assert result.surname_strokes == 11
        assert result.given_strokes == [11]
        assert result.wuge is wuge
        assert result.sancai == ("木", "木", "木")
        assert result.sancai_ji == "大吉"
        assert result.sancai_desc == "顺利发展"
        assert result.overall_score == 85.0
        assert result.overall_grade == "优"
        assert result.suggestions == ["建议1", "建议2"]

    def test_default_suggestions(self):
        wuge = self._make_wuge()
        result = NameAnalysis(
            surname="李",
            given_name="娜",
            surname_strokes=7,
            given_strokes=[10],
            wuge=wuge,
            sancai=("水", "水", "水"),
            sancai_ji="大吉",
            sancai_desc="一帆风顺",
            overall_score=90.0,
            overall_grade="优",
        )
        assert result.suggestions == []

    def test_overall_score_is_float(self):
        wuge = self._make_wuge()
        result = NameAnalysis(
            surname="王",
            given_name="五",
            surname_strokes=4,
            given_strokes=[5],
            wuge=wuge,
            sancai=("土", "土", "土"),
            sancai_ji="大吉",
            sancai_desc="",
            overall_score=75.5,
            overall_grade="良",
        )
        assert isinstance(result.overall_score, float)

    def test_overall_grade_options(self):
        wuge = self._make_wuge()
        for grade in ["优", "良", "中", "差"]:
            result = NameAnalysis(
                surname="张", given_name="伟",
                surname_strokes=11, given_strokes=[11],
                wuge=wuge, sancai=("木", "木", "木"),
                sancai_ji="大吉", sancai_desc="",
                overall_score=50.0, overall_grade=grade,
            )
            assert result.overall_grade == grade


# ============================================================================
# KANGXI_STROKES 字典
# ============================================================================

class TestKangxiStrokes:
    """KANGXI_STROKES 字典查询测试"""

    def test_known_surname(self):
        assert KANGXI_STROKES["张"] == 11
        assert KANGXI_STROKES["李"] == 7
        assert KANGXI_STROKES["王"] == 4
        assert KANGXI_STROKES["刘"] == 15
        assert KANGXI_STROKES["陈"] == 16

    def test_known_given_name_char(self):
        assert KANGXI_STROKES["伟"] == 11
        assert KANGXI_STROKES["娜"] == 10
        assert KANGXI_STROKES["强"] == 12
        assert KANGXI_STROKES["涛"] == 18
        assert KANGXI_STROKES["宇"] == 6

    def test_stroke_range(self):
        for char, strokes in KANGXI_STROKES.items():
            assert strokes > 0, f"Character '{char}' has non-positive strokes: {strokes}"

    def test_single_stroke_char(self):
        assert KANGXI_STROKES["一"] == 1

    def test_high_stroke_chars(self):
        assert KANGXI_STROKES["艳"] == 24
        assert KANGXI_STROKES["鑫"] == 24
        assert KANGXI_STROKES["苏"] == 22
        assert KANGXI_STROKES["龚"] == 22


# ============================================================================
# _SHU_LI_JI_XIONG 字典
# ============================================================================

class TestShuLiJiXiong:
    """81 数理吉凶数据测试"""

    def test_all_81_entries_exist(self):
        for i in range(1, 82):
            assert i in _SHU_LI_JI_XIONG, f"Missing entry for {i}"

    def test_all_entries_have_valid_classification(self):
        for num, (ji, desc) in _SHU_LI_JI_XIONG.items():
            assert ji in ("大吉", "凶"), f"Entry {num} has unexpected ji: {ji}"
            assert len(desc) > 0, f"Entry {num} has empty description"

    def test_daji_and_xiong_counts(self):
        daji = sum(1 for ji, _ in _SHU_LI_JI_XIONG.values() if ji == "大吉")
        xiong = sum(1 for ji, _ in _SHU_LI_JI_XIONG.values() if ji == "凶")
        assert daji + xiong == 81
        assert daji > 0
        assert xiong > 0


# ============================================================================
# SANCAI_JIXIONG 字典
# ============================================================================

class TestSancaiJixiong:
    """三才配置吉凶数据测试"""

    def test_known_configurations(self):
        assert SANCAI_JIXIONG[("木", "木", "木")] == ("大吉", "成功顺利伸展，境遇安泰")
        assert SANCAI_JIXIONG[("水", "水", "水")] == ("大吉", "一帆风顺")
        assert SANCAI_JIXIONG[("金", "木", "木")] == ("凶", "成功运被压抑")

    def test_all_entries_valid(self):
        for key, (ji, desc) in SANCAI_JIXIONG.items():
            assert len(key) == 3
            assert ji in ("大吉", "凶")
            assert len(desc) > 0


# ============================================================================
# BIHUA_WUXING 字典
# ============================================================================

class TestBihuaWuxing:
    """笔画五行数据测试"""

    def test_all_81_entries_exist(self):
        for i in range(1, 82):
            assert i in BIHUA_WUXING, f"Missing entry for {i}"

    def test_all_entries_valid_wuxing(self):
        for num, wx in BIHUA_WUXING.items():
            assert wx in ("木", "火", "土", "金", "水"), f"Entry {num} has unexpected wuxing: {wx}"

    def test_pattern(self):
        # 1-2: 木, 3-4: 火, 5-6: 土, 7-8: 金, 9-10: 水 (repeats every 10)
        assert BIHUA_WUXING[1] == "木"
        assert BIHUA_WUXING[2] == "木"
        assert BIHUA_WUXING[3] == "火"
        assert BIHUA_WUXING[4] == "火"
        assert BIHUA_WUXING[5] == "土"
        assert BIHUA_WUXING[6] == "土"
        assert BIHUA_WUXING[7] == "金"
        assert BIHUA_WUXING[8] == "金"
        assert BIHUA_WUXING[9] == "水"
        assert BIHUA_WUXING[10] == "水"


# ============================================================================
# _get_stroke
# ============================================================================

class TestGetStroke:
    """_get_stroke 内部方法测试"""

    def test_known_character(self):
        assert NameEngine._get_stroke("张") == 11
        assert NameEngine._get_stroke("李") == 7
        assert NameEngine._get_stroke("王") == 4

    def test_unknown_character_fallback(self):
        # Fallback: len(char) * 2 + 4
        # 'A' (len=1) → 1*2+4 = 6
        assert NameEngine._get_stroke("A") == 6
        assert NameEngine._get_stroke("Z") == 6
        # '好' is not in KANGXI_STROKES (let's check)... actually it's not
        # If it's not there, fallback applies
        result = NameEngine._get_stroke("好")
        # '好' is not in the dict, so fallback: len=1, 1*2+4=6
        assert isinstance(result, int)

    def test_empty_string_fallback(self):
        # Empty string: len=0, 0*2+4=4
        assert NameEngine._get_stroke("") == 4

    def test_unknown_chinese_char_fallback(self):
        # '嘿' is not in KANGXI_STROKES
        result = NameEngine._get_stroke("嘿")
        assert result == 6  # len=1, 1*2+4=6

    def test_unknown_multi_byte_char(self):
        # '😀' len=1, 1*2+4=6
        result = NameEngine._get_stroke("😀")
        assert result == 6

    def test_returns_int(self):
        for char in ["张", "A", "", "!"]:
            assert isinstance(NameEngine._get_stroke(char), int)


# ============================================================================
# _get_shuli_jixiong
# ============================================================================

class TestGetShuliJixiong:
    """_get_shuli_jixiong 内部方法测试"""

    def test_all_81_numbers(self):
        for i in range(1, 82):
            ji, desc = NameEngine._get_shuli_jixiong(i)
            assert ji in ("大吉", "凶"), f"Num {i}: unexpected ji={ji}"
            assert len(desc) > 0, f"Num {i}: empty desc"

    def test_greater_than_81_wraps(self):
        # 82 % 81 = 1 → same as 1
        ji82, desc82 = NameEngine._get_shuli_jixiong(82)
        ji1, desc1 = NameEngine._get_shuli_jixiong(1)
        assert ji82 == ji1
        assert desc82 == desc1

    def test_exact_multiple_of_81(self):
        # 81 % 81 = 0, or 0 → 81
        ji81, desc81 = NameEngine._get_shuli_jixiong(81)
        ji162, desc162 = NameEngine._get_shuli_jixiong(162)  # 162 % 81 = 0 → 81
        assert ji162 == ji81
        assert desc162 == desc81

    def test_zero(self):
        # 0 % 81 = 0, or 0 → 81
        ji, desc = NameEngine._get_shuli_jixiong(0)
        assert ji in ("大吉", "凶")

    def test_negative_number(self):
        # -1 is not > 81, so it doesn't wrap; falls through to default
        ji, desc = NameEngine._get_shuli_jixiong(-1)
        assert ji == "凶"
        assert desc == "数理不详"

    def test_very_large_number(self):
        ji, desc = NameEngine._get_shuli_jixiong(10000)
        assert ji in ("大吉", "凶")
        assert len(desc) > 0


# ============================================================================
# _get_bihua_wuxing
# ============================================================================

class TestGetBihuaWuxing:
    """_get_bihua_wuxing 内部方法测试"""

    def test_all_81_numbers(self):
        for i in range(1, 82):
            wx = NameEngine._get_bihua_wuxing(i)
            assert wx in ("木", "火", "土", "金", "水"), f"Num {i}: unexpected wx={wx}"

    def test_greater_than_81_wraps(self):
        w82 = NameEngine._get_bihua_wuxing(82)
        w1 = NameEngine._get_bihua_wuxing(1)
        assert w82 == w1

    def test_exact_multiple_of_81(self):
        w81 = NameEngine._get_bihua_wuxing(81)
        w162 = NameEngine._get_bihua_wuxing(162)  # 162%81=0 → 81
        assert w162 == w81

    def test_zero(self):
        wx = NameEngine._get_bihua_wuxing(0)
        assert wx in ("木", "火", "土", "金", "水")

    def test_negative(self):
        # -1 is not > 81, so it doesn't wrap; falls through to default "土"
        wx = NameEngine._get_bihua_wuxing(-1)
        assert wx == "土"

    def test_very_large(self):
        wx = NameEngine._get_bihua_wuxing(9999)
        assert wx in ("木", "火", "土", "金", "水")


# ============================================================================
# _calc_wuge
# ============================================================================

class TestCalcWuge:
    """_calc_wuge 内部方法测试"""

    def test_single_char_given_name(self):
        # 张(11) + 伟(11): 天=12, 人=22, 地=11, 总=22, 外=22-22+1=1
        wuge = NameEngine._calc_wuge(11, [11])
        assert wuge.tian_ge == 12
        assert wuge.ren_ge == 22
        assert wuge.di_ge == 11
        assert wuge.zong_ge == 22
        assert wuge.wai_ge == 1

    def test_two_char_given_name(self):
        # 李(7) + 娜(10) + 子(3): 天=8, 人=17, 地=13, 总=20, 外=20-17+1=4
        wuge = NameEngine._calc_wuge(7, [10, 3])
        assert wuge.tian_ge == 8
        assert wuge.ren_ge == 17
        assert wuge.di_ge == 13
        assert wuge.zong_ge == 20
        assert wuge.wai_ge == 4

    def test_returns_wuge_result(self):
        wuge = NameEngine._calc_wuge(4, [5])
        assert isinstance(wuge, WugeResult)

    def test_all_ji_fields_set(self):
        wuge = NameEngine._calc_wuge(7, [10])
        assert wuge.tian_ge_ji in ("大吉", "凶")
        assert wuge.ren_ge_ji in ("大吉", "凶")
        assert wuge.di_ge_ji in ("大吉", "凶")
        assert wuge.wai_ge_ji in ("大吉", "凶")
        assert wuge.zong_ge_ji in ("大吉", "凶")

    def test_small_stroke_values(self):
        # 丁(2) + 一(1): 天=3, 人=3, 地=1, 总=3, 外=3-3+1=1
        wuge = NameEngine._calc_wuge(2, [1])
        assert wuge.tian_ge == 3
        assert wuge.ren_ge == 3
        assert wuge.di_ge == 1
        assert wuge.zong_ge == 3
        assert wuge.wai_ge == 1

    def test_large_stroke_values(self):
        # 苏(22) + 艳(24): 天=23, 人=46, 地=24, 总=46, 外=46-46+1=1
        wuge = NameEngine._calc_wuge(22, [24])
        assert wuge.tian_ge == 23
        assert wuge.ren_ge == 46
        assert wuge.di_ge == 24
        assert wuge.zong_ge == 46
        assert wuge.wai_ge == 1

    def test_empty_given_strokes(self):
        # 张(11) + []: 天=12, 人=11, 地=0, 总=11, 外=11-11+1=1
        wuge = NameEngine._calc_wuge(11, [])
        assert wuge.tian_ge == 12
        assert wuge.ren_ge == 11
        assert wuge.di_ge == 0
        assert wuge.zong_ge == 11
        assert wuge.wai_ge == 1

    def test_three_char_given_name(self):
        # Only first two chars are used for di_ge, and zong_ge = surname + g1 + g2
        # 李(7) + [10, 3, 5]: 天=8, 人=17, 地=10+3=13, 总=7+10+3=20, 外=20-17+1=4
        wuge = NameEngine._calc_wuge(7, [10, 3, 5])
        assert wuge.tian_ge == 8
        assert wuge.ren_ge == 17
        assert wuge.di_ge == 13
        assert wuge.zong_ge == 20
        assert wuge.wai_ge == 4


# ============================================================================
# _calc_sancai
# ============================================================================

class TestCalcSancai:
    """_calc_sancai 内部方法测试"""

    def test_returns_three_tuple(self):
        wuge = NameEngine._calc_wuge(7, [10])
        sancai = NameEngine._calc_sancai(wuge)
        assert len(sancai) == 3
        assert all(wx in ("木", "火", "土", "金", "水") for wx in sancai)

    def test_known_mapping(self):
        # 天格=8 → 金, 人格=17 → 金, 地格=10 → 水
        wuge = NameEngine._calc_wuge(7, [10])
        sancai = NameEngine._calc_sancai(wuge)
        assert sancai == ("金", "金", "水")

    def test_consistent_with_bihua_wuxing(self):
        wuge = NameEngine._calc_wuge(11, [11])
        sancai = NameEngine._calc_sancai(wuge)
        assert sancai[0] == NameEngine._get_bihua_wuxing(wuge.tian_ge)
        assert sancai[1] == NameEngine._get_bihua_wuxing(wuge.ren_ge)
        assert sancai[2] == NameEngine._get_bihua_wuxing(wuge.di_ge)


# ============================================================================
# analyze
# ============================================================================

class TestAnalyze:
    """analyze 公有方法测试"""

    # ── 常见中文名 ──

    def test_common_name_zhangwei(self):
        result = NameEngine.analyze("张", "伟")
        assert result.surname == "张"
        assert result.given_name == "伟"
        assert result.surname_strokes == 11
        assert result.given_strokes == [11]
        assert isinstance(result.wuge, WugeResult)
        assert len(result.sancai) == 3
        assert isinstance(result.overall_score, float)
        assert result.overall_grade in ("优", "良", "中", "差")
        assert isinstance(result.suggestions, list)

    def test_common_name_lina(self):
        result = NameEngine.analyze("李", "娜")
        assert result.surname == "李"
        assert result.given_name == "娜"
        assert result.surname_strokes == 7
        assert result.given_strokes == [10]

    def test_common_name_wangwu(self):
        result = NameEngine.analyze("王", "五")
        assert result.surname == "王"
        assert result.given_name == "五"
        assert result.surname_strokes == 4
        # "五" is not in KANGXI_STROKES, fallback: len=1, 1*2+4=6
        assert result.given_strokes == [6]

    # ── 单字名 ──

    def test_single_char_given_name(self):
        result = NameEngine.analyze("周", "杰")
        assert result.given_name == "杰"
        assert len(result.given_strokes) == 1
        assert result.given_strokes == [8]

    # ── 双字名 ──

    def test_two_char_given_name(self):
        result = NameEngine.analyze("陈", "晓明")
        assert result.given_name == "晓明"
        assert len(result.given_strokes) == 2

    def test_two_char_given_name_strokes(self):
        # 刘(15) + 德(15) + 华(12)
        result = NameEngine.analyze("刘", "德华")
        assert result.given_strokes == [15, 12]

    # ── 评分与等级 ──

    def test_overall_score_range(self):
        for surname, given in [("张", "伟"), ("李", "娜"), ("王", "五"), ("刘", "德华"), ("周", "杰")]:
            result = NameEngine.analyze(surname, given)
            assert 0 <= result.overall_score <= 100, f"{surname}{given}: score={result.overall_score}"

    def test_overall_grade_is_valid(self):
        result = NameEngine.analyze("张", "伟")
        assert result.overall_grade in ("优", "良", "中", "差")

    def test_grade_cha(self):
        """于一杰: 于(3)+一(1)+杰(8), 五格全凶, 三才(火火水)=凶, 应得"差"等"""
        result = NameEngine.analyze("于", "一杰")
        assert result.overall_grade == "差"
        assert result.overall_score < 40

    # ── 建议 ──

    def test_suggestions_is_list(self):
        result = NameEngine.analyze("张", "伟")
        assert isinstance(result.suggestions, list)

    def test_suggestions_not_empty(self):
        result = NameEngine.analyze("张", "伟")
        assert len(result.suggestions) > 0

    def test_suggestions_are_strings(self):
        result = NameEngine.analyze("张", "伟")
        for s in result.suggestions:
            assert isinstance(s, str)
            assert len(s) > 0

    # ── 三才字段 ──

    def test_sancai_fields(self):
        result = NameEngine.analyze("张", "伟")
        assert len(result.sancai) == 3
        assert all(wx in ("木", "火", "土", "金", "水") for wx in result.sancai)
        assert result.sancai_ji in ("大吉", "凶", "半吉")
        assert len(result.sancai_desc) > 0

    # ── 边界情况 ──

    def test_empty_surname(self):
        result = NameEngine.analyze("", "伟")
        assert result.surname == ""
        assert result.surname_strokes == 4  # fallback for empty string

    def test_empty_given_name(self):
        result = NameEngine.analyze("张", "")
        assert result.given_name == ""
        assert result.given_strokes == []

    def test_both_empty(self):
        result = NameEngine.analyze("", "")
        assert result.surname == ""
        assert result.given_name == ""
        assert isinstance(result.wuge, WugeResult)

    def test_non_chinese_characters(self):
        result = NameEngine.analyze("A", "B")
        assert result.surname == "A"
        assert result.given_name == "B"
        assert isinstance(result.overall_score, float)

    def test_very_long_name(self):
        result = NameEngine.analyze("张", "伟伟伟伟伟")
        assert len(result.given_name) == 5
        assert len(result.given_strokes) == 5

    def test_unknown_chinese_surname(self):
        # A character not in KANGXI_STROKES; fallback applies
        result = NameEngine.analyze("嘿", "伟")
        assert result.surname == "嘿"
        assert result.surname_strokes == 6  # fallback

    def test_mixed_known_unknown(self):
        result = NameEngine.analyze("张", "Z")
        assert result.given_strokes[0] == 6  # fallback for 'Z'

    # ── 多种姓氏 ──

    def test_many_surnames(self):
        surnames = ["张", "李", "王", "刘", "陈", "杨", "赵", "黄", "周", "吴"]
        for s in surnames:
            result = NameEngine.analyze(s, "伟")
            assert result.surname == s
            assert isinstance(result.wuge, WugeResult)

    # ── 返回类型 ──

    def test_returns_name_analysis(self):
        result = NameEngine.analyze("张", "伟")
        assert isinstance(result, NameAnalysis)


# ============================================================================
# format_text
# ============================================================================

class TestFormatText:
    """format_text 公有方法测试"""

    def test_produces_non_empty_output(self):
        result = NameEngine.analyze("张", "伟")
        text = NameEngine.format_text(result)
        assert len(text) > 0

    def test_contains_name(self):
        result = NameEngine.analyze("张", "伟")
        text = NameEngine.format_text(result)
        assert "张伟" in text

    def test_contains_wuge(self):
        result = NameEngine.analyze("张", "伟")
        text = NameEngine.format_text(result)
        assert "天格" in text
        assert "人格" in text
        assert "地格" in text
        assert "外格" in text
        assert "总格" in text

    def test_contains_sancai(self):
        result = NameEngine.analyze("张", "伟")
        text = NameEngine.format_text(result)
        assert "三才" in text

    def test_contains_score(self):
        result = NameEngine.analyze("张", "伟")
        text = NameEngine.format_text(result)
        assert "综合评分" in text
        assert str(result.overall_score) in text

    def test_contains_grade(self):
        result = NameEngine.analyze("张", "伟")
        text = NameEngine.format_text(result)
        assert result.overall_grade in text

    def test_contains_suggestion(self):
        result = NameEngine.analyze("张", "伟")
        text = NameEngine.format_text(result)
        assert "建议" in text
        assert result.suggestions[0] in text

    def test_returns_string(self):
        result = NameEngine.analyze("张", "伟")
        text = NameEngine.format_text(result)
        assert isinstance(text, str)

    def test_multiline(self):
        result = NameEngine.analyze("张", "伟")
        text = NameEngine.format_text(result)
        assert "\n" in text or len(text.splitlines()) > 1

    def test_format_text_with_poor_name(self):
        # A name that might have poor scores
        result = NameEngine.analyze("", "")
        text = NameEngine.format_text(result)
        assert len(text) > 0

    def test_format_text_various_names(self):
        for surname, given in [("李", "娜"), ("王", "五"), ("刘", "德华"), ("周", "杰")]:
            result = NameEngine.analyze(surname, given)
            text = NameEngine.format_text(result)
            assert len(text) > 0
            assert surname + given in text


# ============================================================================
# analyze_name 便捷函数
# ============================================================================

class TestAnalyzeNameFunction:
    """analyze_name 便捷函数测试"""

    def test_returns_name_analysis(self):
        result = analyze_name("张", "伟")
        assert isinstance(result, NameAnalysis)

    def test_equivalent_to_engine_analyze(self):
        r1 = analyze_name("张", "伟")
        r2 = NameEngine.analyze("张", "伟")
        assert r1.surname == r2.surname
        assert r1.given_name == r2.given_name
        assert r1.surname_strokes == r2.surname_strokes
        assert r1.given_strokes == r2.given_strokes
        assert r1.overall_score == r2.overall_score
        assert r1.overall_grade == r2.overall_grade

    def test_common_names(self):
        for surname, given in [("张", "伟"), ("李", "娜"), ("王", "五"), ("刘", "德华")]:
            result = analyze_name(surname, given)
            assert isinstance(result, NameAnalysis)
            assert result.surname == surname
            assert result.given_name == given

    def test_with_single_char_name(self):
        result = analyze_name("周", "杰")
        assert isinstance(result, NameAnalysis)
        assert len(result.given_strokes) == 1

    def test_with_two_char_name(self):
        result = analyze_name("陈", "晓明")
        assert isinstance(result, NameAnalysis)
        assert len(result.given_strokes) == 2


# ============================================================================
# 综合集成测试
# ============================================================================

class TestIntegration:
    """端到端集成测试"""

    def test_full_pipeline_zhangwei(self):
        result = analyze_name("张", "伟")
        text = NameEngine.format_text(result)
        assert isinstance(result, NameAnalysis)
        assert isinstance(result.wuge, WugeResult)
        assert len(result.sancai) == 3
        assert 0 <= result.overall_score <= 100
        assert result.overall_grade in ("优", "良", "中", "差")
        assert len(result.suggestions) > 0
        assert len(text) > 0

    def test_full_pipeline_lina(self):
        result = analyze_name("李", "娜")
        text = NameEngine.format_text(result)
        assert isinstance(result, NameAnalysis)
        assert len(text) > 0

    def test_full_pipeline_liudehua(self):
        result = analyze_name("刘", "德华")
        text = NameEngine.format_text(result)
        assert "刘德华" in text

    def test_consistency(self):
        """Multiple calls with same inputs produce same results"""
        r1 = NameEngine.analyze("张", "伟")
        r2 = NameEngine.analyze("张", "伟")
        assert r1.overall_score == r2.overall_score
        assert r1.overall_grade == r2.overall_grade
        assert r1.sancai == r2.sancai
        assert r1.suggestions == r2.suggestions

    def test_ji_xiong_ratio(self):
        """Test that all possible wuge fields have valid ji/xiong"""
        for surname, given in [("张", "伟"), ("李", "娜"), ("王", "五"), ("刘", "德华"), ("周", "杰")]:
            result = NameEngine.analyze(surname, given)
            for ji in [result.wuge.tian_ge_ji, result.wuge.ren_ge_ji, result.wuge.di_ge_ji,
                       result.wuge.wai_ge_ji, result.wuge.zong_ge_ji]:
                assert ji in ("大吉", "凶"), f"{surname}{given}: unexpected ji={ji}"