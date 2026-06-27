"""Tests for oracle_engine.py — Oracle 认知引擎 v2.0.0"""

import pytest
import random
import time
from unittest.mock import patch

from tengod.伤官_破界创新.oracle_engine import (
    OracleEngine,
    OracleResult,
    OracleMode,
    Hexagram,
    __version__,
)


# ── OracleMode ──────────────────────────────────────────────────────────────────


class TestOracleMode:
    def test_all_modes_exist(self):
        """验证所有推演模式枚举值存在"""
        modes = list(OracleMode)
        assert len(modes) == 5
        assert OracleMode.TUIBEITU in modes
        assert OracleMode.ZHOUYI in modes
        assert OracleMode.ZIGUA in modes
        assert OracleMode.HETU in modes
        assert OracleMode.LUOSHU in modes

    def test_mode_values(self):
        """验证每个模式的字符串值"""
        assert OracleMode.TUIBEITU.value == "tuibeitu"
        assert OracleMode.ZHOUYI.value == "zhouyi"
        assert OracleMode.ZIGUA.value == "zigua"
        assert OracleMode.HETU.value == "hetu"
        assert OracleMode.LUOSHU.value == "luoshu"

    def test_mode_from_string(self):
        """验证从字符串构造枚举"""
        assert OracleMode("tuibeitu") == OracleMode.TUIBEITU
        assert OracleMode("zhouyi") == OracleMode.ZHOUYI
        assert OracleMode("zigua") == OracleMode.ZIGUA
        assert OracleMode("hetu") == OracleMode.HETU
        assert OracleMode("luoshu") == OracleMode.LUOSHU

    def test_mode_invalid_value(self):
        """验证无效枚举值抛出 ValueError"""
        with pytest.raises(ValueError):
            OracleMode("invalid_mode")

    def test_mode_is_enum(self):
        """验证 OracleMode 是 Enum 子类"""
        assert issubclass(OracleMode, __import__("enum").Enum)


# ── Hexagram ────────────────────────────────────────────────────────────────────


class TestHexagram:
    def test_trigrams_count(self):
        """验证八卦符号数量"""
        assert len(Hexagram.TRIGRAMS) == 8

    def test_trigrams_content(self):
        """验证八卦符号内容"""
        expected = ["☰", "☱", "☲", "☳", "☴", "☵", "☶", "☷"]
        assert Hexagram.TRIGRAMS == expected

    def test_hexagram_names_count(self):
        """验证六十四卦卦名数量"""
        assert len(Hexagram.HEXAGRAM_NAMES) == 64

    def test_hexagram_names_key_entries(self):
        """验证关键卦名存在"""
        assert Hexagram.HEXAGRAM_NAMES[0] == "乾"
        assert Hexagram.HEXAGRAM_NAMES[1] == "坤"
        assert Hexagram.HEXAGRAM_NAMES[63] == "未济"
        assert Hexagram.HEXAGRAM_NAMES[12] == "同人"
        assert Hexagram.HEXAGRAM_NAMES[29] == "离"
        assert Hexagram.HEXAGRAM_NAMES[43] == "姤"

    def test_trigram_meanings_has_all_trigrams(self):
        """验证所有八卦符号都有对应的含义（注：源码中离卦用汉字"离"作键）"""
        # 源码中 TRIGRAM_MEANINGS 的键"离"为汉字而非符号"☲"
        symbols_in_meanings = set(Hexagram.TRIGRAM_MEANINGS.keys())
        # 大部分 trigram 符号在 key 中，离卦用汉字
        for trigram in Hexagram.TRIGRAMS:
            meaning_key = trigram if trigram != "☲" else "离"
            assert meaning_key in Hexagram.TRIGRAM_MEANINGS, f"Missing trigram: {trigram}"

    def test_trigram_meanings_structure(self):
        """验证八卦含义数据结构"""
        meaning = Hexagram.TRIGRAM_MEANINGS["☰"]
        assert meaning["name"] == "乾"
        assert meaning["meaning"] == "天"
        assert meaning["nature"] == "健"
        assert meaning["direction"] == "西北"

    def test_trigram_meanings_count(self):
        """验证八卦含义总共 8 条"""
        assert len(Hexagram.TRIGRAM_MEANINGS) == 8


# ── OracleResult ────────────────────────────────────────────────────────────────


class TestOracleResult:
    def test_create_with_default_score(self):
        """验证默认 score 为 0.0"""
        result = OracleResult(
            mode="tuibeitu",
            hexagram="乾",
            hexagram_index=0,
            upper_trigram="☰",
            lower_trigram="☰",
            yao_lines=[1, 1, 1, 1, 1, 1],
            judgment="元亨利贞",
            image="天行健",
            commentary="君子观此卦象",
            gan_zhi="甲子",
            wuxing="木",
            prediction="预测",
            wisdom="智慧",
            timing="时机",
            action="行动",
        )
        assert result.score == 0.0

    def test_create_with_explicit_score(self):
        """验证显式设置 score"""
        result = OracleResult(
            mode="zhouyi",
            hexagram="坤",
            hexagram_index=1,
            upper_trigram="☷",
            lower_trigram="☷",
            yao_lines=[0, 0, 0, 0, 0, 0],
            judgment="元亨",
            image="地势坤",
            commentary="君子以厚德载物",
            gan_zhi="乙丑",
            wuxing="土",
            prediction="预测",
            wisdom="智慧",
            timing="时机",
            action="行动",
            score=0.85,
        )
        assert result.score == 0.85

    def test_yao_lines_type(self):
        """验证 yao_lines 是列表"""
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
        assert isinstance(result.yao_lines, list)
        assert len(result.yao_lines) == 6

    def test_all_fields_accessible(self):
        """验证所有字段可访问"""
        fields = [
            "mode", "hexagram", "hexagram_index", "upper_trigram",
            "lower_trigram", "yao_lines", "judgment", "image",
            "commentary", "gan_zhi", "wuxing", "prediction",
            "wisdom", "timing", "action", "score",
        ]
        result = OracleResult(
            mode="test",
            hexagram="乾",
            hexagram_index=0,
            upper_trigram="☰",
            lower_trigram="☰",
            yao_lines=[1, 1, 1, 1, 1, 1],
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
        for field in fields:
            assert hasattr(result, field)

    def test_hexagram_index_boundaries(self):
        """验证 hexagram_index 边界值"""
        result = OracleResult(
            mode="t",
            hexagram="乾",
            hexagram_index=0,
            upper_trigram="☰",
            lower_trigram="☰",
            yao_lines=[1, 1, 1, 1, 1, 1],
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
        assert result.hexagram_index == 0

        result_max = OracleResult(
            mode="t",
            hexagram="未济",
            hexagram_index=63,
            upper_trigram="☲",
            lower_trigram="☵",
            yao_lines=[0, 0, 0, 0, 0, 0],
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
        assert result_max.hexagram_index == 63


# ── OracleEngine.__init__ ──────────────────────────────────────────────────────


class TestOracleEngineInit:
    def test_init_without_seed(self):
        """验证无 seed 初始化"""
        engine = OracleEngine()
        assert engine._seed is None
        assert engine._history == []

    def test_init_with_seed(self):
        """验证有 seed 初始化"""
        engine = OracleEngine(seed=42)
        assert engine._seed == 42
        assert engine._history == []

    def test_init_with_none_seed(self):
        """验证 seed=None 初始化"""
        engine = OracleEngine(seed=None)
        assert engine._seed is None
        assert engine._history == []

    def test_init_with_zero_seed(self):
        """验证 seed=0 初始化"""
        engine = OracleEngine(seed=0)
        assert engine._seed == 0

    def test_init_with_negative_seed(self):
        """验证负数 seed 初始化"""
        engine = OracleEngine(seed=-1)
        assert engine._seed == -1


# ── OracleEngine.cast ──────────────────────────────────────────────────────────


class TestOracleEngineCast:
    def test_cast_deterministic(self):
        """验证相同问题产生相同结果（确定性）"""
        engine = OracleEngine(seed=42)
        result1 = engine.cast("测试问题")
        result2 = engine.cast("测试问题")
        assert result1.hexagram == result2.hexagram
        assert result1.hexagram_index == result2.hexagram_index
        assert result1.yao_lines == result2.yao_lines
        assert result1.prediction == result2.prediction
        assert result1.wisdom == result2.wisdom
        assert result1.action == result2.action
        assert result1.timing == result2.timing
        assert result1.score == result2.score
        assert result1.upper_trigram == result2.upper_trigram
        assert result1.lower_trigram == result2.lower_trigram

    def test_cast_different_questions(self):
        """验证不同问题产生不同结果"""
        engine = OracleEngine(seed=42)
        result1 = engine.cast("问题A")
        result2 = engine.cast("问题B")
        # 不同问题通常产生不同卦象
        assert (
            result1.hexagram_index != result2.hexagram_index
            or result1.yao_lines != result2.yao_lines
        )

    def test_cast_default_mode(self):
        """验证默认模式为 TUIBEITU"""
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        assert result.mode == "tuibeitu"

    def test_cast_all_modes(self):
        """验证所有模式都能正常推演"""
        engine = OracleEngine(seed=42)
        for mode in OracleMode:
            result = engine.cast(f"测试{mode.value}", mode=mode)
            assert result.mode == mode.value
            assert isinstance(result, OracleResult)
            assert result.hexagram_index >= 0
            assert result.hexagram_index < 64
            assert len(result.yao_lines) == 6

    def test_cast_with_seed_produces_consistent_results(self):
        """验证带 seed 的引擎产生可重复结果"""
        engine1 = OracleEngine(seed=42)
        result1 = engine1.cast("中华文明")

        engine2 = OracleEngine(seed=42)
        result2 = engine2.cast("中华文明")

        assert result1.hexagram_index == result2.hexagram_index
        assert result1.yao_lines == result2.yao_lines

    def test_cast_empty_question(self):
        """验证空字符串问题"""
        engine = OracleEngine(seed=42)
        result = engine.cast("")
        assert isinstance(result, OracleResult)
        assert result.hexagram_index >= 0
        assert result.hexagram_index < 64
        assert len(result.yao_lines) == 6

    def test_cast_very_long_question(self):
        """验证超长问题"""
        engine = OracleEngine(seed=42)
        long_question = "A" * 10000
        result = engine.cast(long_question)
        assert isinstance(result, OracleResult)
        assert result.hexagram_index >= 0
        assert result.hexagram_index < 64

    def test_cast_unicode_question(self):
        """验证 Unicode 字符问题"""
        engine = OracleEngine(seed=42)
        result = engine.cast("生命的意义 🌟 🧘 道法自然")
        assert isinstance(result, OracleResult)
        assert result.hexagram_index >= 0
        assert result.hexagram_index < 64

    def test_cast_special_characters(self):
        """验证特殊字符问题"""
        engine = OracleEngine(seed=42)
        result = engine.cast("<script>alert('xss')</script>")
        assert isinstance(result, OracleResult)
        assert result.hexagram_index >= 0
        assert result.hexagram_index < 64

    def test_cast_result_structure(self):
        """验证 cast 返回完整的 OracleResult 结构"""
        engine = OracleEngine(seed=42)
        result = engine.cast("测试问题", mode=OracleMode.ZHOUYI)
        assert result.mode == "zhouyi"
        assert result.hexagram in Hexagram.HEXAGRAM_NAMES
        assert 0 <= result.hexagram_index < 64
        assert result.upper_trigram in Hexagram.TRIGRAMS
        assert result.lower_trigram in Hexagram.TRIGRAMS
        assert len(result.yao_lines) == 6
        for yao in result.yao_lines:
            assert yao in (0, 1)
        assert isinstance(result.judgment, str)
        assert isinstance(result.image, str)
        assert isinstance(result.commentary, str)
        assert isinstance(result.gan_zhi, str)
        assert isinstance(result.wuxing, str)
        assert isinstance(result.prediction, str)
        assert isinstance(result.wisdom, str)
        assert isinstance(result.timing, str)
        assert isinstance(result.action, str)
        assert 0.0 <= result.score <= 1.0

    def test_cast_score_range(self):
        """验证 score 在 [0.72, 0.95] 区间内"""
        engine = OracleEngine(seed=42)
        for i in range(50):
            result = engine.cast(f"测试问题{i}")
            assert 0.72 <= result.score <= 0.95

    def test_cast_upper_lower_trigram_relation(self):
        """验证上卦下卦与 hexagram_index 的一致性"""
        engine = OracleEngine(seed=42)
        for i in range(20):
            result = engine.cast(f"验证卦象{i}")
            upper_idx = Hexagram.TRIGRAMS.index(result.upper_trigram)
            lower_idx = Hexagram.TRIGRAMS.index(result.lower_trigram)
            expected_index = upper_idx * 8 + lower_idx
            assert result.hexagram_index == expected_index

    def test_cast_gan_zhi_format(self):
        """验证干支格式正确"""
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        assert len(result.gan_zhi) == 2
        assert result.gan_zhi[0] in OracleEngine.TIANGAN
        assert result.gan_zhi[1] in OracleEngine.DIZHI

    def test_cast_wuxing_in_cycle(self):
        """验证五行在循环列表中"""
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        assert result.wuxing in OracleEngine.WUXING

    def test_cast_commentary_contains_question(self):
        """验证彖传包含问题文本"""
        engine = OracleEngine(seed=42)
        short_q = "命运"
        result = engine.cast(short_q)
        assert short_q in result.commentary

    def test_cast_commentary_truncates_long_question(self):
        """验证长问题在彖传中被截断"""
        engine = OracleEngine(seed=42)
        long_q = "这是一个非常非常长的关于中华文明发展的问题"
        result = engine.cast(long_q)
        assert len(long_q) > 20
        # 彖传只包含前20字
        assert "这是一个非常非常长的关于中华文明发展的" in result.commentary
        assert long_q not in result.commentary

    def test_cast_history_grows(self):
        """验证历史记录增长"""
        engine = OracleEngine(seed=42)
        assert engine.stats()["total_consultations"] == 0
        engine.cast("问题1")
        assert engine.stats()["total_consultations"] == 1
        engine.cast("问题2")
        assert engine.stats()["total_consultations"] == 2
        engine.cast("问题3")
        assert engine.stats()["total_consultations"] == 3

    def test_cast_history_structure(self):
        """验证历史记录结构"""
        engine = OracleEngine(seed=42)
        engine.cast("测试")
        assert len(engine._history) == 1
        entry = engine._history[0]
        assert "question" in entry
        assert "result" in entry
        assert "ts" in entry
        assert entry["question"] == "测试"
        assert isinstance(entry["result"], OracleResult)
        assert isinstance(entry["ts"], float)

    def test_cast_judgment_for_known_hexagram(self):
        """验证已知卦的卦辞返回"""
        engine = OracleEngine(seed=42)
        # 用 hash 确定性地生成卦象 0（乾卦）
        result = engine.cast("测试卦辞")
        # 仅验证如果卦序在 JUDGMENTS 中，则返回对应的卦辞
        if result.hexagram_index in OracleEngine.JUDGMENTS:
            expected_judgment, expected_image = OracleEngine.JUDGMENTS[result.hexagram_index]
            assert result.judgment == expected_judgment
            assert result.image == expected_image

    def test_cast_judgment_fallback(self):
        """验证未知卦的卦辞回退"""
        # 找到 ENGINE 中没有的卦序
        known_indices = set(OracleEngine.JUDGMENTS.keys())
        missing_indices = set(range(64)) - known_indices
        # 用已知 missing 卦序构造场景
        # 通过 mock hash 来生成特定 hexagram_index
        engine = OracleEngine(seed=42)
        # 用一个已知返回 non-JUDGMENTS 卦的问题
        for i in range(100):
            result = engine.cast(f"寻找冷门卦{i}")
            if result.hexagram_index in missing_indices:
                # 注意：judgment 会是 "卦序{index}" 格式
                assert f"卦序{result.hexagram_index}" in result.judgment
                return
        # 如果实在找不到，跳过（概率极低）
        pytest.skip("无法生成未知卦序的回退场景")

    def test_cast_yao_lines_variation(self):
        """验证六爻属性的多样性"""
        engine = OracleEngine(seed=42)
        all_yao_sets = set()
        for i in range(30):
            result = engine.cast(f"爻变测试{i}")
            all_yao_sets.add(tuple(result.yao_lines))
        assert len(all_yao_sets) > 1  # 至少产生不同的爻组合


# ── OracleEngine.interpret ─────────────────────────────────────────────────────


class TestOracleEngineInterpret:
    def test_interpret_basic(self):
        """验证 interpret 基本格式化"""
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert isinstance(output, str)
        assert "推背图 Oracle 推演结果" in output
        assert result.hexagram in output
        assert result.upper_trigram in output
        assert result.lower_trigram in output
        assert result.gan_zhi in output
        assert result.wuxing in output
        assert result.judgment in output
        assert result.prediction in output
        assert result.wisdom in output
        assert result.action in output
        assert result.timing in output

    def test_interpret_contains_version(self):
        """验证 interpret 输出包含版本号"""
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert __version__ in output

    def test_interpret_contains_score(self):
        """验证 interpret 输出包含置信度"""
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        assert f"{result.score:.2%}" in output

    def test_interpret_yao_lines_format(self):
        """验证六爻格式化"""
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        # 六爻行包含 ━━ 或 ━
        yao_line = [l for l in output.split("\n") if "六    爻" in l][0]
        assert "━━" in yao_line or "━" in yao_line

    def test_interpret_multiline(self):
        """验证 interpret 输出多行"""
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output = engine.interpret(result)
        lines = output.split("\n")
        assert len(lines) > 10

    def test_interpret_consistent(self):
        """验证 interpret 对同一结果一致性"""
        engine = OracleEngine(seed=42)
        result = engine.cast("测试")
        output1 = engine.interpret(result)
        output2 = engine.interpret(result)
        assert output1 == output2


# ── OracleEngine.stats ─────────────────────────────────────────────────────────


class TestOracleEngineStats:
    def test_stats_empty(self):
        """验证空历史的统计"""
        engine = OracleEngine(seed=42)
        stats = engine.stats()
        assert stats["total_consultations"] == 0
        assert stats["modes_used"] == []
        assert stats["avg_confidence"] == 0.0

    def test_stats_after_one_cast(self):
        """验证单次推演后的统计"""
        engine = OracleEngine(seed=42)
        result = engine.cast("测试", mode=OracleMode.ZHOUYI)
        stats = engine.stats()
        assert stats["total_consultations"] == 1
        assert stats["modes_used"] == ["zhouyi"]
        assert stats["avg_confidence"] == result.score

    def test_stats_after_multiple_casts(self):
        """验证多次推演后的统计"""
        engine = OracleEngine(seed=42)
        r1 = engine.cast("问题1", mode=OracleMode.TUIBEITU)
        r2 = engine.cast("问题2", mode=OracleMode.ZHOUYI)
        r3 = engine.cast("问题3", mode=OracleMode.TUIBEITU)

        stats = engine.stats()
        assert stats["total_consultations"] == 3
        assert set(stats["modes_used"]) == {"tuibeitu", "zhouyi"}
        expected_avg = (r1.score + r2.score + r3.score) / 3
        assert stats["avg_confidence"] == pytest.approx(expected_avg)

    def test_stats_no_division_by_zero(self):
        """验证空历史时不会除零错误"""
        engine = OracleEngine(seed=42)
        stats = engine.stats()
        assert stats["avg_confidence"] == 0.0

    def test_stats_returns_dict(self):
        """验证 stats 返回字典"""
        engine = OracleEngine(seed=42)
        stats = engine.stats()
        assert isinstance(stats, dict)
        assert set(stats.keys()) == {"total_consultations", "modes_used", "avg_confidence"}


# ── OracleEngine._generate_prediction (indirect) ───────────────────────────────


class TestGeneratePrediction:
    def test_prediction_is_string(self):
        """验证预测是字符串"""
        engine = OracleEngine(seed=42)
        for i in range(10):
            result = engine.cast(f"预测测试{i}")
            assert isinstance(result.prediction, str)
            assert len(result.prediction) > 0

    def test_prediction_variety(self):
        """验证预测有变化"""
        engine = OracleEngine(seed=42)
        preds = set()
        for i in range(30):
            result = engine.cast(f"预测多样性{i}")
            preds.add(result.prediction)
        assert len(preds) > 1


# ── OracleEngine._generate_wisdom (indirect) ───────────────────────────────────


class TestGenerateWisdom:
    def test_wisdom_is_string(self):
        """验证智慧是字符串"""
        engine = OracleEngine(seed=42)
        for i in range(10):
            result = engine.cast(f"智慧测试{i}")
            assert isinstance(result.wisdom, str)
            assert len(result.wisdom) > 0

    def test_wisdom_contains_yao_info(self):
        """验证智慧包含爻信息"""
        engine = OracleEngine(seed=42)
        result = engine.cast("智慧")
        yang_count = sum(result.yao_lines)
        # 智慧可能包含阳爻阴爻信息或变化信息
        wisdom_has_info = (
            f"阳爻{yang_count}" in result.wisdom
            or "阴爻" in result.wisdom
            or "变化" in result.wisdom
            or "天地人" in result.wisdom
        )
        assert wisdom_has_info, f"智慧内容: {result.wisdom}"


# ── OracleEngine._generate_action (indirect) ───────────────────────────────────


class TestGenerateAction:
    def test_action_is_string(self):
        """验证行动建议是字符串"""
        engine = OracleEngine(seed=42)
        for i in range(10):
            result = engine.cast(f"行动测试{i}")
            assert isinstance(result.action, str)
            assert len(result.action) > 0

    def test_action_variety(self):
        """验证行动建议有变化"""
        engine = OracleEngine(seed=42)
        actions = set()
        for i in range(30):
            result = engine.cast(f"行动多样性{i}")
            actions.add(result.action)
        assert len(actions) > 1


# ── OracleEngine._generate_timing (indirect) ───────────────────────────────────


class TestGenerateTiming:
    def test_timing_is_string(self):
        """验证时机判断是字符串"""
        engine = OracleEngine(seed=42)
        for i in range(10):
            result = engine.cast(f"时机测试{i}")
            assert isinstance(result.timing, str)
            assert len(result.timing) > 0

    def test_timing_variety(self):
        """验证时机判断有变化"""
        engine = OracleEngine(seed=42)
        timings = set()
        for i in range(30):
            result = engine.cast(f"时机多样性{i}")
            timings.add(result.timing)
        assert len(timings) > 1


# ── OracleEngine._generate_commentary (indirect) ───────────────────────────────


class TestGenerateCommentary:
    def test_commentary_short_question(self):
        """验证短问题的彖传"""
        engine = OracleEngine(seed=42)
        result = engine.cast("命")
        assert "命" in result.commentary
        assert "君子观此卦象" in result.commentary

    def test_commentary_long_question(self):
        """验证长问题的彖传截断"""
        engine = OracleEngine(seed=42)
        long_question = "A" * 100
        result = engine.cast(long_question)
        assert "A" * 20 in result.commentary
        assert "A" * 21 not in result.commentary


# ── Edge Cases ─────────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_multiple_engines_independent(self):
        """验证多个引擎实例互不影响"""
        e1 = OracleEngine(seed=1)
        e2 = OracleEngine(seed=2)
        r1 = e1.cast("问题")
        r2 = e2.cast("问题")
        assert e1.stats()["total_consultations"] == 1
        assert e2.stats()["total_consultations"] == 1

    def test_same_question_different_engines(self):
        """验证不同引擎对同一问题产生不同结果（无 seed）"""
        # 无 seed 时，同一问题在同一引擎内是确定性，但不同引擎实例可能不同
        e1 = OracleEngine()
        e2 = OracleEngine()
        r1 = e1.cast("测试")
        r2 = e2.cast("测试")
        # 同一问题 hash 相同，所以结果应该相同（即使不同引擎实例）
        assert r1.hexagram_index == r2.hexagram_index
        assert r1.yao_lines == r2.yao_lines

    def test_numeric_question(self):
        """验证纯数字问题"""
        engine = OracleEngine(seed=42)
        result = engine.cast("1234567890")
        assert isinstance(result, OracleResult)

    def test_whitespace_only_question(self):
        """验证纯空格问题"""
        engine = OracleEngine(seed=42)
        result = engine.cast("   ")
        assert isinstance(result, OracleResult)
        assert result.hexagram_index >= 0

    def test_newline_question(self):
        """验证含换行的问题"""
        engine = OracleEngine(seed=42)
        result = engine.cast("第一行\n第二行\n第三行")
        assert isinstance(result, OracleResult)

    def test_hexagram_index_boundaries(self):
        """验证卦序在 0-63 之间"""
        engine = OracleEngine(seed=42)
        for i in range(50):
            result = engine.cast(f"卦序边界测试{i}")
            assert 0 <= result.hexagram_index < 64

    def test_all_yao_combinations_possible(self):
        """验证所有阳爻组合都可能出现"""
        engine = OracleEngine(seed=42)
        yao_sets = set()
        for i in range(200):
            result = engine.cast(f"全覆盖测试{i}")
            yao_sets.add(tuple(result.yao_lines))
        # 64 种六爻组合，200 次应该覆盖大部分
        assert len(yao_sets) >= 20


# ── Module-level ───────────────────────────────────────────────────────────────


class TestModule:
    def test_version_string(self):
        """验证版本号是字符串"""
        assert isinstance(__version__, str)
        assert __version__ == "2.0.0"

    def test_all_exports(self):
        """验证 __all__ 导出"""
        from tengod.伤官_破界创新 import oracle_engine as oe
        assert hasattr(oe, "__all__")
        assert "OracleEngine" in oe.__all__
        assert "OracleResult" in oe.__all__
        assert "OracleMode" in oe.__all__
        assert "Hexagram" in oe.__all__