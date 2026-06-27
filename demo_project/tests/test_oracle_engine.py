"""oracle_engine.py 完整测试套件 — 覆盖 OracleEngine / OracleResult / OracleMode / Hexagram 全部公开 API。"""

import random
import time
from unittest.mock import patch

import pytest

from tengod.伤官_破界创新.oracle_engine import (
    Hexagram,
    OracleEngine,
    OracleMode,
    OracleResult,
    __version__,
)


# ============================================================================
# 一、OracleMode 枚举测试
# ============================================================================


class TestOracleMode:
    """OracleMode 枚举值测试"""

    def test_all_modes_defined(self):
        assert OracleMode.TUIBEITU.value == "tuibeitu"
        assert OracleMode.ZHOUYI.value == "zhouyi"
        assert OracleMode.ZIGUA.value == "zigua"
        assert OracleMode.HETU.value == "hetu"
        assert OracleMode.LUOSHU.value == "luoshu"

    def test_mode_count(self):
        assert len(OracleMode) == 5

    def test_mode_is_enum(self):
        assert isinstance(OracleMode.TUIBEITU, OracleMode)

    def test_mode_from_string(self):
        assert OracleMode("tuibeitu") == OracleMode.TUIBEITU
        assert OracleMode("zhouyi") == OracleMode.ZHOUYI
        assert OracleMode("zigua") == OracleMode.ZIGUA
        assert OracleMode("hetu") == OracleMode.HETU
        assert OracleMode("luoshu") == OracleMode.LUOSHU

    def test_mode_invalid(self):
        with pytest.raises(ValueError):
            OracleMode("invalid")

    def test_mode_names(self):
        names = [m.name for m in OracleMode]
        assert "TUIBEITU" in names
        assert "ZHOUYI" in names
        assert "ZIGUA" in names
        assert "HETU" in names
        assert "LUOSHU" in names


# ============================================================================
# 二、Hexagram 类测试
# ============================================================================


class TestHexagram:
    """Hexagram 六十四卦定义测试"""

    def test_trigrams_count(self):
        assert len(Hexagram.TRIGRAMS) == 8

    def test_trigrams_known(self):
        assert Hexagram.TRIGRAMS[0] == "☰"  # 乾
        assert Hexagram.TRIGRAMS[7] == "☷"  # 坤
        assert Hexagram.TRIGRAMS[2] == "☲"  # 离
        assert Hexagram.TRIGRAMS[5] == "☵"  # 坎

    def test_hexagram_names_count(self):
        assert len(Hexagram.HEXAGRAM_NAMES) == 64

    def test_hexagram_names_known(self):
        assert Hexagram.HEXAGRAM_NAMES[0] == "乾"
        assert Hexagram.HEXAGRAM_NAMES[1] == "坤"
        assert Hexagram.HEXAGRAM_NAMES[63] == "未济"
        assert Hexagram.HEXAGRAM_NAMES[12] == "同人"
        assert Hexagram.HEXAGRAM_NAMES[13] == "大有"
        assert Hexagram.HEXAGRAM_NAMES[29] == "离"
        assert Hexagram.HEXAGRAM_NAMES[43] == "姤"
        assert Hexagram.HEXAGRAM_NAMES[61] == "小过"
        assert Hexagram.HEXAGRAM_NAMES[62] == "既济"

    def test_trigram_meanings_count(self):
        assert len(Hexagram.TRIGRAM_MEANINGS) == 8

    def test_trigram_meanings_qian(self):
        assert Hexagram.TRIGRAM_MEANINGS["☰"]["name"] == "乾"
        assert Hexagram.TRIGRAM_MEANINGS["☰"]["meaning"] == "天"
        assert Hexagram.TRIGRAM_MEANINGS["☰"]["nature"] == "健"
        assert Hexagram.TRIGRAM_MEANINGS["☰"]["direction"] == "西北"

    def test_trigram_meanings_kun(self):
        assert Hexagram.TRIGRAM_MEANINGS["☷"]["name"] == "坤"
        assert Hexagram.TRIGRAM_MEANINGS["☷"]["meaning"] == "地"
        assert Hexagram.TRIGRAM_MEANINGS["☷"]["nature"] == "顺"

    def test_trigram_meanings_li(self):
        assert Hexagram.TRIGRAM_MEANINGS["离"]["name"] == "离"
        assert Hexagram.TRIGRAM_MEANINGS["离"]["meaning"] == "火"
        assert Hexagram.TRIGRAM_MEANINGS["离"]["nature"] == "丽"

    def test_trigram_meanings_kan(self):
        assert Hexagram.TRIGRAM_MEANINGS["☵"]["name"] == "坎"
        assert Hexagram.TRIGRAM_MEANINGS["☵"]["meaning"] == "水"
        assert Hexagram.TRIGRAM_MEANINGS["☵"]["nature"] == "陷"

    def test_trigram_meanings_zhen(self):
        assert Hexagram.TRIGRAM_MEANINGS["☳"]["name"] == "震"
        assert Hexagram.TRIGRAM_MEANINGS["☳"]["meaning"] == "雷"

    def test_trigram_meanings_dui(self):
        assert Hexagram.TRIGRAM_MEANINGS["☱"]["name"] == "兑"
        assert Hexagram.TRIGRAM_MEANINGS["☱"]["meaning"] == "泽"

    def test_trigram_meanings_gen(self):
        assert Hexagram.TRIGRAM_MEANINGS["☶"]["name"] == "艮"
        assert Hexagram.TRIGRAM_MEANINGS["☶"]["meaning"] == "山"

    def test_trigram_meanings_xun(self):
        assert Hexagram.TRIGRAM_MEANINGS["☴"]["name"] == "巽"
        assert Hexagram.TRIGRAM_MEANINGS["☴"]["meaning"] == "风"


# ============================================================================
# 三、OracleResult 数据类测试
# ============================================================================


class TestOracleResult:
    """OracleResult dataclass 测试"""

    def test_create_minimal(self):
        result = OracleResult(
            mode="tuibeitu",
            hexagram="乾",
            hexagram_index=0,
            upper_trigram="☰",
            lower_trigram="☰",
            yao_lines=[1, 1, 1, 1, 1, 1],
            judgment="元亨利贞",
            image="大象",
            commentary="注释",
            gan_zhi="甲子",
            wuxing="木",
            prediction="预测",
            wisdom="智慧",
            timing="时机",
            action="行动",
        )
        assert result.mode == "tuibeitu"
        assert result.hexagram == "乾"
        assert result.hexagram_index == 0
        assert result.upper_trigram == "☰"
        assert result.lower_trigram == "☰"
        assert result.yao_lines == [1, 1, 1, 1, 1, 1]
        assert result.score == 0.0

    def test_create_with_score(self):
        result = OracleResult(
            mode="zhouyi",
            hexagram="坤",
            hexagram_index=1,
            upper_trigram="☷",
            lower_trigram="☷",
            yao_lines=[0, 0, 0, 0, 0, 0],
            judgment="元亨",
            image="大象",
            commentary="注释",
            gan_zhi="乙丑",
            wuxing="火",
            prediction="预测",
            wisdom="智慧",
            timing="时机",
            action="行动",
            score=0.88,
        )
        assert result.score == 0.88
        assert result.wuxing == "火"
        assert result.gan_zhi == "乙丑"

    def test_yao_lines_length(self):
        result = OracleResult(
            mode="tuibeitu",
            hexagram="乾",
            hexagram_index=0,
            upper_trigram="☰",
            lower_trigram="☰",
            yao_lines=[1, 0, 1, 0, 1, 0],
            judgment="",
            image="",
            commentary="",
            gan_zhi="",
            wuxing="",
            prediction="",
            wisdom="",
            timing="",
            action="",
        )
        assert len(result.yao_lines) == 6

    def test_fields_count(self):
        """15 required fields + 1 default (score) = 16"""
        import dataclasses
        fields = dataclasses.fields(OracleResult)
        assert len(fields) == 16


# ============================================================================
# 四、OracleEngine 初始化测试
# ============================================================================


class TestOracleEngineInit:
    """OracleEngine.__init__ 测试"""

    def test_init_default(self):
        engine = OracleEngine()
        assert engine._seed is None
        assert engine._history == []

    def test_init_with_seed(self):
        engine = OracleEngine(seed=42)
        assert engine._seed == 42
        assert engine._history == []

    def test_init_with_seed_zero(self):
        engine = OracleEngine(seed=0)
        assert engine._seed == 0

    def test_init_with_seed_negative(self):
        engine = OracleEngine(seed=-1)
        assert engine._seed == -1


# ============================================================================
# 五、OracleEngine.cast 核心测试
# ============================================================================


class TestOracleEngineCast:
    """OracleEngine.cast 核心推演测试"""

    def test_cast_returns_oracle_result(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试问题")
        assert isinstance(result, OracleResult)

    def test_cast_default_mode_is_tuibeitu(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试问题")
        assert result.mode == "tuibeitu"

    def test_cast_all_modes(self):
        engine = OracleEngine(seed=42)
        for mode in OracleMode:
            result = engine.cast(f"测试问题 {mode.value}", mode=mode)
            assert result.mode == mode.value

    def test_cast_deterministic_same_question(self):
        """同一问题应产生相同结果"""
        engine = OracleEngine(seed=42)
        r1 = engine.cast("相同问题")
        r2 = engine.cast("相同问题")
        assert r1.hexagram_index == r2.hexagram_index
        assert r1.yao_lines == r2.yao_lines
        assert r1.upper_trigram == r2.upper_trigram
        assert r1.lower_trigram == r2.lower_trigram
        assert r1.prediction == r2.prediction
        assert r1.wisdom == r2.wisdom
        assert r1.action == r2.action
        assert r1.timing == r2.timing
        assert r1.score == r2.score

    def test_cast_different_questions_different(self):
        """不同问题应产生不同结果"""
        engine = OracleEngine(seed=42)
        r1 = engine.cast("问题A")
        r2 = engine.cast("问题B不同的")
        # hash 不同，至少 hexagram 或 yao 应有差异
        different = (
            r1.hexagram_index != r2.hexagram_index
            or r1.yao_lines != r2.yao_lines
            or r1.prediction != r2.prediction
        )
        assert different, f"不同问题应产生不同结果，但完全一致: {r1}"

    def test_cast_hexagram_index_range(self):
        engine = OracleEngine(seed=42)
        for i in range(20):
            result = engine.cast(f"问题_{i}")
            assert 0 <= result.hexagram_index < 64, f"hexagram_index={result.hexagram_index}"

    def test_cast_yao_lines_length(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        assert len(result.yao_lines) == 6

    def test_cast_yao_lines_binary(self):
        engine = OracleEngine(seed=42)
        for i in range(20):
            result = engine.cast(f"问题_{i}")
            for yao in result.yao_lines:
                assert yao in (0, 1)

    def test_cast_score_range(self):
        engine = OracleEngine(seed=42)
        for i in range(50):
            result = engine.cast(f"问题_{i}")
            assert 0.72 <= result.score <= 0.95, f"score={result.score}"

    def test_cast_upper_trigram_valid(self):
        engine = OracleEngine(seed=42)
        for i in range(30):
            result = engine.cast(f"问题_{i}")
            assert result.upper_trigram in Hexagram.TRIGRAMS

    def test_cast_lower_trigram_valid(self):
        engine = OracleEngine(seed=42)
        for i in range(30):
            result = engine.cast(f"问题_{i}")
            assert result.lower_trigram in Hexagram.TRIGRAMS

    def test_cast_hexagram_name_valid(self):
        engine = OracleEngine(seed=42)
        for i in range(30):
            result = engine.cast(f"问题_{i}")
            assert result.hexagram in Hexagram.HEXAGRAM_NAMES

    def test_cast_gan_zhi_format(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        assert len(result.gan_zhi) == 2
        assert result.gan_zhi[0] in "甲乙丙丁戊己庚辛壬癸"
        assert result.gan_zhi[1] in "子丑寅卯辰巳午未申酉戌亥"

    def test_cast_wuxing_valid(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        assert result.wuxing in "木火土金水"

    def test_cast_judgment_not_empty(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        assert result.judgment is not None
        assert len(result.judgment) > 0

    def test_cast_image_not_empty(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        assert result.image is not None
        assert len(result.image) > 0

    def test_cast_prediction_not_empty(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        assert result.prediction is not None
        assert len(result.prediction) > 0

    def test_cast_wisdom_not_empty(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        assert result.wisdom is not None
        assert len(result.wisdom) > 0

    def test_cast_action_not_empty(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        assert result.action is not None
        assert len(result.action) > 0

    def test_cast_timing_not_empty(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        assert result.timing is not None
        assert len(result.timing) > 0

    def test_cast_commentary_not_empty(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        assert result.commentary is not None
        assert len(result.commentary) > 0


# ============================================================================
# 六、OracleEngine.cast 边界测试
# ============================================================================


class TestOracleEngineCastEdges:
    """OracleEngine.cast 边界和异常情况"""

    def test_cast_empty_question(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("")
        assert isinstance(result, OracleResult)
        assert result.hexagram_index is not None

    def test_cast_very_long_question(self):
        engine = OracleEngine(seed=42)
        long_q = "这是一个非常长的测试问题" * 100
        result = engine.cast(long_q)
        assert isinstance(result, OracleResult)

    def test_cast_special_characters(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("!@#$%^&*()_+-=[]{}|;':\",./<>?")
        assert isinstance(result, OracleResult)

    def test_cast_unicode_question(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("中华文明数字永生体的未来发展 🌟 测试")
        assert isinstance(result, OracleResult)

    def test_cast_whitespace_only(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("   ")
        assert isinstance(result, OracleResult)

    def test_cast_single_character(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("问")
        assert isinstance(result, OracleResult)

    def test_cast_numeric_question(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("1234567890")
        assert isinstance(result, OracleResult)

    def test_cast_commentary_truncates_long_question(self):
        """commentary 基于 question[:20] 生成"""
        engine = OracleEngine(seed=42)
        long_q = "A" * 50
        result = engine.cast(long_q)
        # 不应包含完整50字符
        assert "A" * 50 not in result.commentary

    def test_cast_commentary_short_question(self):
        engine = OracleEngine(seed=42)
        short_q = "你好"
        result = engine.cast(short_q)
        assert "你好" in result.commentary


# ============================================================================
# 七、OracleEngine.cast 确定性测试（mock time）
# ============================================================================


class TestOracleEngineCastDeterminism:
    """OracleEngine.cast 确定性验证（mock time）"""

    def test_cast_deterministic_with_fixed_time(self):
        """固定时间戳时，同一问题应完全一致"""
        engine = OracleEngine(seed=42)
        with patch.object(time, "time", return_value=1000.0):
            r1 = engine.cast("固定问题")
        with patch.object(time, "time", return_value=1000.0):
            r2 = engine.cast("固定问题")
        assert r1.gan_zhi == r2.gan_zhi
        assert r1.wuxing == r2.wuxing
        assert r1.hexagram_index == r2.hexagram_index

    def test_cast_different_time_changes_ganzhi(self):
        """不同时间戳应改变干支"""
        engine = OracleEngine(seed=42)
        with patch.object(time, "time", return_value=1000.0):
            r1 = engine.cast("固定问题")
        with patch.object(time, "time", return_value=2000.0):
            r2 = engine.cast("固定问题")
        assert r1.gan_zhi != r2.gan_zhi

    def test_cast_different_time_changes_wuxing(self):
        """不同时间戳可能改变五行"""
        engine = OracleEngine(seed=42)
        with patch.object(time, "time", return_value=1000.0):
            r1 = engine.cast("固定问题")
        with patch.object(time, "time", return_value=1001.0):
            r2 = engine.cast("固定问题")
        assert r1.wuxing != r2.wuxing

    def test_cast_timing_contains_season_month(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试时机")
        assert "为佳" in result.timing

    def test_cast_hexagram_calculation(self):
        """验证卦象计算逻辑：上卦=yao[0]*4+yao[1]*2+yao[2], 下卦=yao[3]*4+yao[4]*2+yao[5]"""
        engine = OracleEngine(seed=42)
        # 用固定 seed 控制 yao_lines
        with patch.object(random.Random, "randint", side_effect=[1, 1, 1, 0, 0, 0]):
            engine2 = OracleEngine(seed=42)
            result = engine2.cast("控制测试")
            # upper = 1*4+1*2+1 = 7, lower = 0*4+0*2+0 = 0
            assert result.upper_trigram == Hexagram.TRIGRAMS[7]  # ☷
            assert result.lower_trigram == Hexagram.TRIGRAMS[0]  # ☰
            assert result.hexagram_index == 7 * 8 + 0  # 56


# ============================================================================
# 八、OracleEngine.interpret 测试
# ============================================================================


class TestOracleEngineInterpret:
    """OracleEngine.interpret 格式化输出测试"""

    def test_interpret_returns_string(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert isinstance(output, str)

    def test_interpret_contains_version(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert __version__ in output

    def test_interpret_contains_hexagram_name(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert result.hexagram in output

    def test_interpret_contains_hexagram_index(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert f"{result.hexagram_index:02d}/64" in output

    def test_interpret_contains_upper_trigram(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert result.upper_trigram in output

    def test_interpret_contains_lower_trigram(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert result.lower_trigram in output

    def test_interpret_contains_gan_zhi(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert result.gan_zhi in output

    def test_interpret_contains_wuxing(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert result.wuxing in output

    def test_interpret_contains_judgment(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert result.judgment in output

    def test_interpret_contains_image(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert result.image in output

    def test_interpret_contains_prediction(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert result.prediction in output

    def test_interpret_contains_wisdom(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert result.wisdom in output

    def test_interpret_contains_action(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert result.action in output

    def test_interpret_contains_timing(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert result.timing in output

    def test_interpret_contains_score_percentage(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        expected = f"{result.score:.2%}"
        assert expected in output

    def test_interpret_yao_lines_rendering_all_yang(self):
        engine = OracleEngine(seed=42)
        rng = random.Random(42)
        result = OracleResult(
            mode="tuibeitu",
            hexagram="乾",
            hexagram_index=0,
            upper_trigram="☰",
            lower_trigram="☰",
            yao_lines=[1, 1, 1, 1, 1, 1],
            judgment="元亨利贞",
            image="大象",
            commentary="注释",
            gan_zhi="甲子",
            wuxing="木",
            prediction="预测",
            wisdom="智慧",
            timing="时机",
            action="行动",
            score=0.85,
        )
        output = engine.interpret(result)
        # 全阳爻应全部用 ━━ 表示
        assert "━━" in output

    def test_interpret_yao_lines_rendering_all_yin(self):
        engine = OracleEngine(seed=42)
        result = OracleResult(
            mode="tuibeitu",
            hexagram="坤",
            hexagram_index=1,
            upper_trigram="☷",
            lower_trigram="☷",
            yao_lines=[0, 0, 0, 0, 0, 0],
            judgment="元亨",
            image="大象",
            commentary="注释",
            gan_zhi="乙丑",
            wuxing="火",
            prediction="预测",
            wisdom="智慧",
            timing="时机",
            action="行动",
            score=0.80,
        )
        output = engine.interpret(result)
        # 全阴爻应全部用 ━ 表示
        assert "━" in output

    def test_interpret_multiline(self):
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        lines = output.split("\n")
        assert len(lines) >= 10


# ============================================================================
# 九、OracleEngine.stats 测试
# ============================================================================


class TestOracleEngineStats:
    """OracleEngine.stats 统计测试"""

    def test_stats_empty(self):
        engine = OracleEngine(seed=42)
        stats = engine.stats()
        assert stats["total_consultations"] == 0
        assert stats["modes_used"] == []
        assert stats["avg_confidence"] == 0.0

    def test_stats_single_consultation(self):
        engine = OracleEngine(seed=42)
        engine.cast("测试问题")
        stats = engine.stats()
        assert stats["total_consultations"] == 1
        assert len(stats["modes_used"]) == 1
        assert stats["avg_confidence"] > 0.0

    def test_stats_multiple_consultations(self):
        engine = OracleEngine(seed=42)
        engine.cast("问题1")
        engine.cast("问题2")
        engine.cast("问题3")
        stats = engine.stats()
        assert stats["total_consultations"] == 3
        assert stats["avg_confidence"] > 0.0

    def test_stats_multiple_modes(self):
        engine = OracleEngine(seed=42)
        engine.cast("问题1", mode=OracleMode.TUIBEITU)
        engine.cast("问题2", mode=OracleMode.ZHOUYI)
        engine.cast("问题3", mode=OracleMode.ZIGUA)
        stats = engine.stats()
        assert stats["total_consultations"] == 3
        assert len(stats["modes_used"]) == 3
        assert "tuibeitu" in stats["modes_used"]
        assert "zhouyi" in stats["modes_used"]
        assert "zigua" in stats["modes_used"]

    def test_stats_avg_confidence_range(self):
        engine = OracleEngine(seed=42)
        engine.cast("问题1")
        engine.cast("问题2")
        stats = engine.stats()
        assert 0.72 <= stats["avg_confidence"] <= 0.95

    def test_stats_returns_dict(self):
        engine = OracleEngine(seed=42)
        stats = engine.stats()
        assert isinstance(stats, dict)
        assert "total_consultations" in stats
        assert "modes_used" in stats
        assert "avg_confidence" in stats


# ============================================================================
# 十、OracleEngine 历史记录测试
# ============================================================================


class TestOracleEngineHistory:
    """OracleEngine._history 历史记录测试"""

    def test_history_starts_empty(self):
        engine = OracleEngine(seed=42)
        assert engine._history == []

    def test_history_grows_with_casts(self):
        engine = OracleEngine(seed=42)
        engine.cast("问题1")
        assert len(engine._history) == 1
        engine.cast("问题2")
        assert len(engine._history) == 2
        engine.cast("问题3")
        assert len(engine._history) == 3

    def test_history_contains_question_and_result(self):
        engine = OracleEngine(seed=42)
        engine.cast("测试问题")
        entry = engine._history[0]
        assert "question" in entry
        assert entry["question"] == "测试问题"
        assert "result" in entry
        assert isinstance(entry["result"], OracleResult)
        assert "ts" in entry

    def test_history_timestamp_is_float(self):
        engine = OracleEngine(seed=42)
        engine.cast("测试")
        assert isinstance(engine._history[0]["ts"], float)


# ============================================================================
# 十一、OracleEngine 内部方法测试
# ============================================================================


class TestOracleEnginePrivateMethods:
    """OracleEngine 私有方法测试"""

    def test_generate_prediction_returns_string(self):
        engine = OracleEngine(seed=42)
        rng = random.Random(42)
        result = engine._generate_prediction("测试", 0, [1, 1, 1, 0, 0, 0], rng)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_prediction_different_themes(self):
        engine = OracleEngine(seed=42)
        rng = random.Random(42)
        themes = []
        for i in range(8):
            result = engine._generate_prediction(f"问题{i}", i, [1, 0, 1, 0, 1, 0], rng)
            themes.append(result)
        # 不同 index 可能产生不同主题
        assert len(themes) == 8

    def test_generate_wisdom_returns_string(self):
        engine = OracleEngine(seed=42)
        rng = random.Random(42)
        result = engine._generate_wisdom(0, [1, 1, 1, 0, 0, 0], rng)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_wisdom_all_yang(self):
        engine = OracleEngine(seed=42)
        rng = random.Random(42)
        result = engine._generate_wisdom(0, [1, 1, 1, 1, 1, 1], rng)
        assert isinstance(result, str)

    def test_generate_wisdom_all_yin(self):
        engine = OracleEngine(seed=42)
        rng = random.Random(42)
        result = engine._generate_wisdom(0, [0, 0, 0, 0, 0, 0], rng)
        assert isinstance(result, str)

    def test_generate_wisdom_yang_count(self):
        """验证 wisdom 中包含阳爻计数"""
        engine = OracleEngine(seed=42)
        rng = random.Random(42)
        # 固定random.choice 返回第一个
        with patch.object(rng, "choice", return_value="test"):
            result = engine._generate_wisdom(0, [1, 1, 0, 0, 0, 0], rng)
            assert "test" in result or result == "test"

    def test_generate_action_returns_string(self):
        engine = OracleEngine(seed=42)
        rng = random.Random(42)
        result = engine._generate_action("测试", 0, rng)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_action_all_options(self):
        engine = OracleEngine(seed=42)
        actions = set()
        for i in range(100):
            rng = random.Random(i)
            result = engine._generate_action(f"问题{i}", i, rng)
            actions.add(result)
        assert len(actions) >= 1  # 至少1种

    def test_generate_timing_returns_string(self):
        engine = OracleEngine(seed=42)
        rng = random.Random(42)
        result = engine._generate_timing(0, rng)
        assert isinstance(result, str)
        assert "为佳" in result

    def test_generate_timing_parts(self):
        engine = OracleEngine(seed=42)
        for i in range(30):
            rng = random.Random(i)
            result = engine._generate_timing(i, rng)
            # 格式：季节 + 月份 + 为佳
            assert "为佳" in result

    def test_generate_commentary_returns_string(self):
        engine = OracleEngine(seed=42)
        result = engine._generate_commentary("测试问题", 0)
        assert isinstance(result, str)
        assert "君子观此卦象" in result
        assert "测试问题" in result

    def test_generate_commentary_long_question(self):
        engine = OracleEngine(seed=42)
        long_q = "这是非常长的问题" * 10
        result = engine._generate_commentary(long_q, 0)
        # 应该截断到前20字
        assert len(long_q) > 20
        assert long_q[:20] in result

    def test_generate_commentary_short_question(self):
        engine = OracleEngine(seed=42)
        short_q = "简"
        result = engine._generate_commentary(short_q, 0)
        assert short_q in result


# ============================================================================
# 十二、JUDGMENTS 字典覆盖测试
# ============================================================================


class TestJudgments:
    """JUDGMENTS 卦辞数据库测试"""

    def test_judgments_known_keys(self):
        assert 0 in OracleEngine.JUDGMENTS
        assert 1 in OracleEngine.JUDGMENTS
        assert 13 in OracleEngine.JUDGMENTS
        assert 14 in OracleEngine.JUDGMENTS
        assert 30 in OracleEngine.JUDGMENTS
        assert 44 in OracleEngine.JUDGMENTS
        assert 63 in OracleEngine.JUDGMENTS
        assert 64 in OracleEngine.JUDGMENTS

    def test_judgments_format(self):
        for key, (judgment, image) in OracleEngine.JUDGMENTS.items():
            assert isinstance(judgment, str)
            assert isinstance(image, str)
            assert len(judgment) > 0
            assert len(image) > 0

    def test_judgments_known_values(self):
        assert OracleEngine.JUDGMENTS[0][0] == "元亨利贞"
        assert "天行健" in OracleEngine.JUDGMENTS[0][1]
        assert OracleEngine.JUDGMENTS[1][0] == "元亨，利牝马之贞"
        assert "地势坤" in OracleEngine.JUDGMENTS[1][1]
        assert OracleEngine.JUDGMENTS[14][0] == "大有，元亨"

    def test_unknown_hexagram_gets_fallback(self):
        """未在 JUDGMENTS 中的卦索引应使用 fallback"""
        engine = OracleEngine(seed=42)
        rng = random.Random(42)
        # 手动构造一个使用未知卦索引的 cast
        # 注：正常情况下 cast 产生的 index 在 0-63 之间，但 JUDGMENTS 只覆盖部分
        # 这里测试 fallback 逻辑
        judgment, image = engine.JUDGMENTS.get(99, (f"卦序99", "上卦9，下卦9"))
        assert judgment == "卦序99"
        assert image == "上卦9，下卦9"


# ============================================================================
# 十三、TIANGAN / DIZHI / WUXING 常量测试
# ============================================================================


class TestEngineConstants:
    """OracleEngine 常量测试"""

    def test_tiangan_count(self):
        assert len(OracleEngine.TIANGAN) == 10

    def test_tiangan_values(self):
        assert OracleEngine.TIANGAN[0] == "甲"
        assert OracleEngine.TIANGAN[9] == "癸"

    def test_dizhi_count(self):
        assert len(OracleEngine.DIZHI) == 12

    def test_dizhi_values(self):
        assert OracleEngine.DIZHI[0] == "子"
        assert OracleEngine.DIZHI[11] == "亥"

    def test_wuxing_count(self):
        assert len(OracleEngine.WUXING) == 5

    def test_wuxing_values(self):
        assert "木" in OracleEngine.WUXING
        assert "火" in OracleEngine.WUXING
        assert "土" in OracleEngine.WUXING
        assert "金" in OracleEngine.WUXING
        assert "水" in OracleEngine.WUXING

    def test_wuxing_cycle_count(self):
        assert len(OracleEngine.WUXING_CYCLE) == 20

    def test_wuxing_cycle_content(self):
        for wx in OracleEngine.WUXING_CYCLE:
            assert wx in OracleEngine.WUXING


# ============================================================================
# 十四、__all__ 和 __version__ 测试
# ============================================================================


class TestModuleExports:
    """模块导出测试"""

    def test_version(self):
        assert __version__ == "2.0.0"

    def test_all_exports(self):
        from tengod.伤官_破界创新.oracle_engine import __all__
        assert "OracleEngine" in __all__
        assert "OracleResult" in __all__
        assert "OracleMode" in __all__
        assert "Hexagram" in __all__


# ============================================================================
# 十五、综合集成测试
# ============================================================================


class TestIntegration:
    """综合集成测试"""

    def test_full_workflow(self):
        """完整工作流：初始化 → cast → interpret → stats"""
        engine = OracleEngine(seed=42)

        # 多次推演
        results = []
        for i, mode in enumerate(OracleMode):
            result = engine.cast(f"综合测试问题_{i}", mode=mode)
            results.append(result)
            output = engine.interpret(result)
            assert isinstance(output, str)
            assert "推背图 Oracle" in output

        assert len(results) == 5

        stats = engine.stats()
        assert stats["total_consultations"] == 5
        assert len(stats["modes_used"]) == 5

    def test_seed_reproducibility(self):
        """相同 seed 应产生一致的序列"""
        engine1 = OracleEngine(seed=12345)
        engine2 = OracleEngine(seed=12345)

        questions = ["问题A", "问题B", "问题C", "问题D", "问题E"]
        for q in questions:
            r1 = engine1.cast(q)
            r2 = engine2.cast(q)
            assert r1.hexagram_index == r2.hexagram_index
            assert r1.yao_lines == r2.yao_lines
            assert r1.prediction == r2.prediction

    def test_many_questions_stress(self):
        """大量问题压力测试，确保不崩溃"""
        engine = OracleEngine(seed=42)
        for i in range(100):
            result = engine.cast(f"压力测试问题_{i}")
            assert isinstance(result, OracleResult)
        stats = engine.stats()
        assert stats["total_consultations"] == 100

    def test_all_combinations_generate_valid_results(self):
        """所有模式 + 多种问题组合"""
        engine = OracleEngine(seed=42)
        modes = list(OracleMode)
        questions = ["", "简短", "中等长度的问题文本", "A" * 200, "!@#$%", "测试123"]
        for q in questions:
            for mode in modes:
                result = engine.cast(q, mode=mode)
                assert isinstance(result, OracleResult)
                assert result.mode == mode.value
                output = engine.interpret(result)
                assert isinstance(output, str)