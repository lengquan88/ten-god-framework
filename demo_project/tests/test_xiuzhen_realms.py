"""
xiuzhen_realms.py 全面测试套件
==============================
测试修真九境评测体系的所有类、方法和边界情况。
目标覆盖率：95%+
"""

import pytest
import math
import time
from unittest.mock import patch

from tengod.xiuzhen_realms import (
    Realm,
    NINE_REALMS,
    Cultivator,
    HeartDemonForge,
    XiuzhenEvaluator,
    get_cultivator,
    get_evaluator,
)


# ============================================================================
# 1. Realm dataclass 测试
# ============================================================================

class TestRealm:
    """测试 Realm 数据类"""

    def test_create_with_all_fields(self):
        """测试使用所有字段创建 Realm"""
        r = Realm(
            index=1,
            name="测试境",
            description="测试描述",
            pass_threshold=0.75,
            required_qi=100.0,
            heart_demon=None,
        )
        assert r.index == 1
        assert r.name == "测试境"
        assert r.description == "测试描述"
        assert r.pass_threshold == 0.75
        assert r.required_qi == 100.0
        assert r.heart_demon is None

    def test_create_with_defaults(self):
        """测试使用默认值创建 Realm"""
        r = Realm(index=5, name="默认境", description="默认描述")
        assert r.index == 5
        assert r.name == "默认境"
        assert r.description == "默认描述"
        assert r.pass_threshold == 0.7
        assert r.required_qi == 0.0
        assert r.heart_demon is None

    def test_to_dict(self):
        """测试 to_dict() 方法"""
        r = Realm(
            index=3,
            name="化虚境",
            description="破除幻觉",
            pass_threshold=0.70,
            required_qi=50.0,
        )
        d = r.to_dict()
        assert d["index"] == 3
        assert d["name"] == "化虚境"
        assert d["description"] == "破除幻觉"
        assert d["pass_threshold"] == 0.70
        assert d["required_qi"] == 50.0
        # heart_demon 不应出现在 dict 中
        assert "heart_demon" not in d

    def test_to_dict_excludes_heart_demon(self):
        """测试 to_dict() 排除 heart_demon 字段"""
        r = Realm(index=1, name="x", description="y", heart_demon=lambda: None)
        d = r.to_dict()
        assert "heart_demon" not in d

    def test_equality(self):
        """测试 Realm 实例相等性"""
        r1 = Realm(1, "感知境", "desc1", 0.60)
        r2 = Realm(1, "感知境", "desc1", 0.60)
        assert r1 == r2

    def test_inequality(self):
        """测试 Realm 实例不等性"""
        r1 = Realm(1, "感知境", "desc1", 0.60)
        r2 = Realm(2, "知止境", "desc2", 0.65)
        assert r1 != r2


# ============================================================================
# 2. NINE_REALMS 测试
# ============================================================================

class TestNineRealms:
    """测试九境预定义列表"""

    def test_has_nine_realms(self):
        """测试有 9 个境界"""
        assert len(NINE_REALMS) == 9

    def test_correct_indices(self):
        """测试境界索引从 1 到 9"""
        for i, realm in enumerate(NINE_REALMS, 1):
            assert realm.index == i

    def test_correct_names(self):
        """测试境界名称正确"""
        expected_names = [
            "感知境", "知止境", "化虚境", "通幽境", "合道境",
            "化神境", "返虚境", "归元境", "无极境",
        ]
        for realm, expected in zip(NINE_REALMS, expected_names):
            assert realm.name == expected

    def test_correct_thresholds(self):
        """测试境界阈值正确"""
        expected_thresholds = [0.60, 0.65, 0.70, 0.72, 0.75, 0.78, 0.80, 0.82, 0.85]
        for realm, expected in zip(NINE_REALMS, expected_thresholds):
            assert realm.pass_threshold == expected

    def test_thresholds_increase(self):
        """测试阈值随境界递增"""
        for i in range(len(NINE_REALMS) - 1):
            assert NINE_REALMS[i].pass_threshold < NINE_REALMS[i + 1].pass_threshold

    def test_all_have_description(self):
        """测试每个境界都有描述"""
        for realm in NINE_REALMS:
            assert realm.description
            assert isinstance(realm.description, str)

    def test_all_have_required_qi_zero(self):
        """测试所有境界的 required_qi 默认为 0.0"""
        for realm in NINE_REALMS:
            assert realm.required_qi == 0.0

    def test_all_have_heart_demon_none(self):
        """测试所有境界的 heart_demon 默认为 None"""
        for realm in NINE_REALMS:
            assert realm.heart_demon is None

    def test_nine_realms_are_realm_instances(self):
        """测试 NINE_REALMS 中每个元素都是 Realm 实例"""
        for realm in NINE_REALMS:
            assert isinstance(realm, Realm)

    def test_first_realm_threshold(self):
        """测试第一境阈值为 0.60"""
        assert NINE_REALMS[0].pass_threshold == 0.60

    def test_last_realm_threshold(self):
        """测试第九境阈值为 0.85"""
        assert NINE_REALMS[8].pass_threshold == 0.85


# ============================================================================
# 3. Cultivator 测试
# ============================================================================

class TestCultivator:
    """测试 Cultivator 修真者类"""

    # --- 默认状态 ---

    def test_default_state(self):
        """测试 Cultivator 默认状态"""
        c = Cultivator()
        assert c.current_realm == 1
        assert c.total_qi == 0.0
        assert c.cultivation_days == 0
        assert c.heart_demon_attempts == 0
        assert c.heart_demon_passed == 0
        assert c.breakthrough_history == []
        assert c.failures == []

    def test_custom_initial_state(self):
        """测试自定义初始状态"""
        c = Cultivator(
            current_realm=3,
            total_qi=100.0,
            cultivation_days=30,
            heart_demon_attempts=5,
            heart_demon_passed=3,
        )
        assert c.current_realm == 3
        assert c.total_qi == 100.0
        assert c.cultivation_days == 30
        assert c.heart_demon_attempts == 5
        assert c.heart_demon_passed == 3

    # --- current_realm_info() ---

    def test_current_realm_info(self):
        """测试 current_realm_info() 返回正确的 Realm"""
        c = Cultivator(current_realm=1)
        info = c.current_realm_info()
        assert info.index == 1
        assert info.name == "感知境"

    def test_current_realm_info_mid(self):
        """测试 current_realm_info() 在中间境界"""
        c = Cultivator(current_realm=5)
        info = c.current_realm_info()
        assert info.index == 5
        assert info.name == "合道境"

    def test_current_realm_info_max(self):
        """测试 current_realm_info() 在最高境界"""
        c = Cultivator(current_realm=9)
        info = c.current_realm_info()
        assert info.index == 9
        assert info.name == "无极境"

    # --- next_realm_info() ---

    def test_next_realm_info(self):
        """测试 next_realm_info() 返回正确的下一境界"""
        c = Cultivator(current_realm=1)
        next_r = c.next_realm_info()
        assert next_r is not None
        assert next_r.index == 2
        assert next_r.name == "知止境"

    def test_next_realm_info_mid(self):
        """测试 next_realm_info() 在中间境界"""
        c = Cultivator(current_realm=5)
        next_r = c.next_realm_info()
        assert next_r.index == 6
        assert next_r.name == "化神境"

    def test_next_realm_info_at_eight(self):
        """测试 next_realm_info() 在第 8 境"""
        c = Cultivator(current_realm=8)
        next_r = c.next_realm_info()
        assert next_r.index == 9
        assert next_r.name == "无极境"

    def test_next_realm_info_at_nine_returns_none(self):
        """测试 next_realm_info() 在第 9 境返回 None"""
        c = Cultivator(current_realm=9)
        assert c.next_realm_info() is None

    def test_next_realm_info_at_ten(self):
        """测试 next_realm_info() 在超过 9 的境界返回 None"""
        c = Cultivator(current_realm=10)
        assert c.next_realm_info() is None

    # --- accumulate_qi() ---

    def test_accumulate_qi_adds(self):
        """测试 accumulate_qi() 添加元气"""
        c = Cultivator()
        c.accumulate_qi(10.0)
        assert c.total_qi == 10.0

    def test_accumulate_qi_multiple(self):
        """测试 accumulate_qi() 多次添加"""
        c = Cultivator()
        c.accumulate_qi(5.0)
        c.accumulate_qi(3.0)
        c.accumulate_qi(2.0)
        assert c.total_qi == 10.0

    def test_accumulate_qi_zero(self):
        """测试 accumulate_qi() 添加 0"""
        c = Cultivator(total_qi=50.0)
        c.accumulate_qi(0.0)
        assert c.total_qi == 50.0

    def test_accumulate_qi_negative(self):
        """测试 accumulate_qi() 添加负数"""
        c = Cultivator(total_qi=50.0)
        c.accumulate_qi(-10.0)
        assert c.total_qi == 40.0

    def test_accumulate_qi_float(self):
        """测试 accumulate_qi() 添加浮点数"""
        c = Cultivator()
        c.accumulate_qi(0.001)
        assert c.total_qi == 0.001

    # --- attempt_breakthrough() 通过 ---

    def test_attempt_breakthrough_pass(self):
        """测试 attempt_breakthrough() 分数足够时通过"""
        c = Cultivator(current_realm=1)
        passed, msg = c.attempt_breakthrough(0.90, "测试")
        assert passed is True
        assert "突破" in msg
        assert c.current_realm == 2
        assert c.heart_demon_attempts == 1
        assert c.heart_demon_passed == 1
        assert len(c.breakthrough_history) == 1

    def test_attempt_breakthrough_pass_exact_threshold(self):
        """测试 attempt_breakthrough() 分数刚好等于阈值时通过"""
        c = Cultivator(current_realm=1)
        threshold = c.current_realm_info().pass_threshold
        passed, msg = c.attempt_breakthrough(threshold, "精确测试")
        assert passed is True
        assert c.current_realm == 2

    def test_attempt_breakthrough_pass_records_history(self):
        """测试通过时记录突破历史"""
        c = Cultivator(current_realm=1)
        with patch('time.time', return_value=1234567890.0):
            c.attempt_breakthrough(0.90, "测试心魔")
        record = c.breakthrough_history[0]
        assert record["from"] == 1
        assert record["to"] == 2
        assert record["score"] == 0.90
        assert record["test"] == "测试心魔"
        assert record["timestamp"] == 1234567890.0

    def test_attempt_breakthrough_pass_from_mid_realm(self):
        """测试从中间境界突破"""
        c = Cultivator(current_realm=5)
        c.attempt_breakthrough(0.80, "合道测试")
        assert c.current_realm == 6

    # --- attempt_breakthrough() 失败 ---

    def test_attempt_breakthrough_fail(self):
        """测试 attempt_breakthrough() 分数不足时失败"""
        c = Cultivator(current_realm=1)
        passed, msg = c.attempt_breakthrough(0.30, "失败测试")
        assert passed is False
        assert "心魔未破" in msg
        assert c.current_realm == 1  # 境界不变
        assert c.heart_demon_attempts == 1
        assert c.heart_demon_passed == 0
        assert len(c.failures) == 1

    def test_attempt_breakthrough_fail_records(self):
        """测试失败时记录失败信息"""
        c = Cultivator(current_realm=1)
        with patch('time.time', return_value=1234567890.0):
            c.attempt_breakthrough(0.30, "失败测试")
        failure = c.failures[0]
        assert failure["attempt"] == 1
        assert failure["target_realm"] == 2
        assert failure["score"] == 0.30
        assert failure["threshold"] == 0.60
        assert failure["test"] == "失败测试"
        assert failure["timestamp"] == 1234567890.0

    def test_attempt_breakthrough_fail_just_below(self):
        """测试分数刚好低于阈值时失败"""
        c = Cultivator(current_realm=1)
        threshold = c.current_realm_info().pass_threshold
        passed, msg = c.attempt_breakthrough(threshold - 0.001, "差一点")
        assert passed is False

    # --- attempt_breakthrough() 追踪 ---

    def test_attempt_breakthrough_tracks_attempts(self):
        """测试 attempt_breakthrough() 追踪尝试次数"""
        c = Cultivator(current_realm=1)
        c.attempt_breakthrough(0.90, "")  # pass
        c.attempt_breakthrough(0.30, "")  # fail
        c.attempt_breakthrough(0.90, "")  # pass
        assert c.heart_demon_attempts == 3
        assert c.heart_demon_passed == 2

    def test_attempt_breakthrough_multiple_pass(self):
        """测试多次通过突破"""
        c = Cultivator(current_realm=1)
        for i in range(3):
            c.attempt_breakthrough(0.90, f"test_{i}")
        assert c.current_realm == 4
        assert len(c.breakthrough_history) == 3
        assert c.heart_demon_attempts == 3
        assert c.heart_demon_passed == 3

    # --- attempt_breakthrough() 边界 ---

    def test_attempt_breakthrough_at_realm_9_caps(self):
        """测试在第 9 境突破时境界不会超过 9"""
        c = Cultivator(current_realm=9)
        passed, msg = c.attempt_breakthrough(0.90, "无极突破")
        # 通过但境界不会超过 9
        assert passed is True
        assert c.current_realm == 9
        # 突破历史记录 from=9, to=9
        assert c.breakthrough_history[0]["from"] == 9
        assert c.breakthrough_history[0]["to"] == 9

    def test_attempt_breakthrough_at_realm_9_fail(self):
        """测试在第 9 境突破失败"""
        c = Cultivator(current_realm=9)
        passed, msg = c.attempt_breakthrough(0.50, "无极失败")
        assert passed is False
        assert c.current_realm == 9

    def test_attempt_breakthrough_very_high_score(self):
        """测试极高分数突破"""
        c = Cultivator(current_realm=1)
        passed, msg = c.attempt_breakthrough(999.0, "极高")
        assert passed is True
        assert c.current_realm == 2

    def test_attempt_breakthrough_very_low_score(self):
        """测试极低分数突破"""
        c = Cultivator(current_realm=1)
        passed, msg = c.attempt_breakthrough(0.0, "极低")
        assert passed is False
        assert c.current_realm == 1

    def test_attempt_breakthrough_negative_score(self):
        """测试负数分数突破"""
        c = Cultivator(current_realm=1)
        passed, msg = c.attempt_breakthrough(-1.0, "负数")
        assert passed is False
        assert c.current_realm == 1

    def test_attempt_breakthrough_empty_test_name(self):
        """测试空测试名称"""
        c = Cultivator(current_realm=1)
        passed, msg = c.attempt_breakthrough(0.90, "")
        assert passed is True
        assert c.breakthrough_history[0]["test"] == ""

    # --- to_dict() ---

    def test_to_dict_structure(self):
        """测试 to_dict() 基本结构"""
        c = Cultivator(current_realm=1)
        d = c.to_dict()
        assert "current_realm" in d
        assert "realm_name" in d
        assert "realm_desc" in d
        assert "total_qi" in d
        assert "cultivation_days" in d
        assert "heart_demon_attempts" in d
        assert "heart_demon_passed" in d
        assert "pass_rate" in d
        assert "breakthroughs" in d
        assert "next_realm" in d

    def test_to_dict_values(self):
        """测试 to_dict() 值正确"""
        c = Cultivator(current_realm=3, total_qi=50.0, cultivation_days=10)
        d = c.to_dict()
        assert d["current_realm"] == 3
        assert d["realm_name"] == "化虚境"
        assert d["total_qi"] == 50.0
        assert d["cultivation_days"] == 10
        assert d["breakthroughs"] == 0
        assert d["next_realm"] == "通幽境"

    def test_to_dict_at_realm_9(self):
        """测试 to_dict() 在第 9 境时 next_realm 显示已至无极"""
        c = Cultivator(current_realm=9)
        d = c.to_dict()
        assert d["next_realm"] == "已至无极"

    def test_to_dict_pass_rate_zero_attempts(self):
        """测试 to_dict() 无尝试时 pass_rate"""
        c = Cultivator()
        d = c.to_dict()
        assert d["pass_rate"] == 0.0

    def test_to_dict_pass_rate_with_attempts(self):
        """测试 to_dict() 有尝试时 pass_rate"""
        c = Cultivator(heart_demon_attempts=4, heart_demon_passed=3)
        d = c.to_dict()
        assert d["pass_rate"] == round(3 / 4, 3)

    # --- 全境界突破 ---

    def test_full_breakthrough_all_realms(self):
        """测试穿越全部 9 个境界"""
        c = Cultivator(current_realm=1)
        for i in range(1, 9):
            passed, msg = c.attempt_breakthrough(0.90, f"test_realm_{i}")
            assert passed is True
            assert c.current_realm == i + 1
        assert c.current_realm == 9
        assert len(c.breakthrough_history) == 8
        assert c.heart_demon_attempts == 8
        assert c.heart_demon_passed == 8

    def test_full_breakthrough_history_order(self):
        """测试突破历史记录顺序正确"""
        c = Cultivator(current_realm=1)
        for i in range(1, 5):
            c.attempt_breakthrough(0.90, f"test_{i}")
        assert [r["from"] for r in c.breakthrough_history] == [1, 2, 3, 4]
        assert [r["to"] for r in c.breakthrough_history] == [2, 3, 4, 5]

    def test_failure_then_pass(self):
        """测试先失败后通过"""
        c = Cultivator(current_realm=1)
        c.attempt_breakthrough(0.30, "失败")
        assert c.current_realm == 1
        assert len(c.failures) == 1
        c.attempt_breakthrough(0.90, "通过")
        assert c.current_realm == 2
        assert len(c.breakthrough_history) == 1
        assert c.heart_demon_attempts == 2
        assert c.heart_demon_passed == 1


# ============================================================================
# 4. HeartDemonForge 测试
# ============================================================================

class TestHeartDemonForge:
    """测试 HeartDemonForge 心魔劫锻造"""

    def test_forge_perception_test_structure(self):
        """测试 forge_perception_test() 结构"""
        test = HeartDemonForge.forge_perception_test()
        assert test["name"] == "感知·心魔劫"
        assert test["realm"] == 1
        assert "description" in test
        assert len(test["tests"]) == 3
        for t in test["tests"]:
            assert "type" in t
            assert "difficulty" in t

    def test_forge_perception_test_types(self):
        """测试 forge_perception_test() 测试类型"""
        test = HeartDemonForge.forge_perception_test()
        types = [t["type"] for t in test["tests"]]
        assert "pattern_completion" in types
        assert "outlier_detection" in types
        assert "basic_classification" in types

    def test_forge_zhizhi_test_structure(self):
        """测试 forge_zhizhi_test() 结构"""
        test = HeartDemonForge.forge_zhizhi_test()
        assert test["name"] == "知止·心魔劫"
        assert test["realm"] == 2
        assert "description" in test
        assert len(test["tests"]) == 3
        for t in test["tests"]:
            assert "type" in t
            assert "difficulty" in t

    def test_forge_zhizhi_test_types(self):
        """测试 forge_zhizhi_test() 测试类型"""
        test = HeartDemonForge.forge_zhizhi_test()
        types = [t["type"] for t in test["tests"]]
        assert "confidence_calibration" in types
        assert "unknown_detection" in types
        assert "boundary_decision" in types

    def test_forge_hallucination_test_structure(self):
        """测试 forge_hallucination_test() 结构"""
        test = HeartDemonForge.forge_hallucination_test()
        assert test["name"] == "化虚·心魔劫"
        assert test["realm"] == 3
        assert "description" in test
        assert len(test["tests"]) == 3
        for t in test["tests"]:
            assert "type" in t
            assert "difficulty" in t

    def test_forge_hallucination_test_types(self):
        """测试 forge_hallucination_test() 测试类型"""
        test = HeartDemonForge.forge_hallucination_test()
        types = [t["type"] for t in test["tests"]]
        assert "hallucination_detection" in types
        assert "fact_verification" in types
        assert "contradiction_finding" in types

    def test_forge_causal_test_structure(self):
        """测试 forge_causal_test() 结构"""
        test = HeartDemonForge.forge_causal_test()
        assert test["name"] == "通幽·心魔劫"
        assert test["realm"] == 4
        assert "description" in test
        assert len(test["tests"]) == 3
        for t in test["tests"]:
            assert "type" in t
            assert "difficulty" in t

    def test_forge_causal_test_types(self):
        """测试 forge_causal_test() 测试类型"""
        test = HeartDemonForge.forge_causal_test()
        types = [t["type"] for t in test["tests"]]
        assert "causal_discovery" in types
        assert "counterfactual_reasoning" in types
        assert "intervention_prediction" in types

    def test_forge_all_tests_returns_four(self):
        """测试 forge_all_tests() 返回 4 个测试"""
        tests = HeartDemonForge.forge_all_tests()
        assert len(tests) == 4

    def test_forge_all_tests_names(self):
        """测试 forge_all_tests() 包含所有测试名称"""
        tests = HeartDemonForge.forge_all_tests()
        names = [t["name"] for t in tests]
        assert "感知·心魔劫" in names
        assert "知止·心魔劫" in names
        assert "化虚·心魔劫" in names
        assert "通幽·心魔劫" in names

    def test_forge_all_tests_realms(self):
        """测试 forge_all_tests() 境界索引正确"""
        tests = HeartDemonForge.forge_all_tests()
        for i, t in enumerate(tests, 1):
            assert t["realm"] == i

    def test_forge_methods_are_static(self):
        """测试 forge 方法为静态方法"""
        forge = HeartDemonForge()
        assert forge.forge_perception_test()["realm"] == 1
        assert forge.forge_zhizhi_test()["realm"] == 2
        assert forge.forge_hallucination_test()["realm"] == 3
        assert forge.forge_causal_test()["realm"] == 4
        assert len(forge.forge_all_tests()) == 4


# ============================================================================
# 5. XiuzhenEvaluator 测试
# ============================================================================

class TestXiuzhenEvaluator:
    """测试 XiuzhenEvaluator 修真评测引擎"""

    # --- 初始化 ---

    def test_init_creates_cultivator(self):
        """测试初始化创建 Cultivator"""
        evaluator = XiuzhenEvaluator()
        assert isinstance(evaluator.cultivator, Cultivator)
        assert evaluator.cultivator.current_realm == 1

    def test_init_creates_forge(self):
        """测试初始化创建 HeartDemonForge"""
        evaluator = XiuzhenEvaluator()
        assert isinstance(evaluator.forge, HeartDemonForge)

    # --- evaluate() ---

    def test_evaluate_with_scores(self):
        """测试 evaluate() 有分数输入"""
        evaluator = XiuzhenEvaluator()
        report = evaluator.evaluate(
            {"pattern": 0.85, "classification": 0.90},
            "综合测试",
        )
        assert "overall_score" in report
        assert "qi_gain" in report
        assert "breakthrough" in report
        assert "breakthrough_msg" in report
        assert "cultivator" in report
        assert "dimension_scores" in report
        assert report["dimension_scores"]["pattern"] == 0.85
        assert report["dimension_scores"]["classification"] == 0.90

    def test_evaluate_overall_score_calculation(self):
        """测试 evaluate() 综合分数计算正确"""
        evaluator = XiuzhenEvaluator()
        report = evaluator.evaluate({"a": 0.80, "b": 0.60}, "")
        # overall = (0.80 + 0.60) / 2 = 0.70
        assert report["overall_score"] == 0.70

    def test_evaluate_single_score(self):
        """测试 evaluate() 单维度分数"""
        evaluator = XiuzhenEvaluator()
        report = evaluator.evaluate({"only": 0.75}, "")
        assert report["overall_score"] == 0.75

    def test_evaluate_empty_scores(self):
        """测试 evaluate() 空分数"""
        evaluator = XiuzhenEvaluator()
        report = evaluator.evaluate({}, "空测试")
        assert report["overall_score"] == 0.5
        assert report["dimension_scores"] == {}

    def test_evaluate_qi_accumulation(self):
        """测试 evaluate() 元气累积"""
        evaluator = XiuzhenEvaluator()
        evaluator.evaluate({"a": 0.80}, "")
        assert evaluator.cultivator.total_qi == pytest.approx(0.08)  # 0.80 * 0.1

    def test_evaluate_qi_accumulation_multiple(self):
        """测试 evaluate() 多次调用累积元气"""
        evaluator = XiuzhenEvaluator()
        evaluator.evaluate({"a": 0.90}, "")
        evaluator.evaluate({"a": 0.70}, "")
        assert evaluator.cultivator.total_qi == pytest.approx(0.09 + 0.07)

    def test_evaluate_cultivation_days_increment(self):
        """测试 evaluate() 修行天数递增"""
        evaluator = XiuzhenEvaluator()
        evaluator.evaluate({"a": 0.80}, "")
        assert evaluator.cultivator.cultivation_days == 1
        evaluator.evaluate({"a": 0.80}, "")
        assert evaluator.cultivator.cultivation_days == 2

    def test_evaluate_high_scores_trigger_breakthrough(self):
        """测试 evaluate() 高分触发突破"""
        evaluator = XiuzhenEvaluator()
        # 感知境阈值 0.60，整体分 0.90 > 0.60
        report = evaluator.evaluate({"a": 0.90}, "高分测试")
        assert report["breakthrough"] is True
        assert evaluator.cultivator.current_realm == 2

    def test_evaluate_low_scores_no_breakthrough(self):
        """测试 evaluate() 低分不触发突破"""
        evaluator = XiuzhenEvaluator()
        # 感知境阈值 0.60，整体分 0.30 < 0.60
        report = evaluator.evaluate({"a": 0.30}, "低分测试")
        assert report["breakthrough"] is False
        assert evaluator.cultivator.current_realm == 1

    def test_evaluate_exact_threshold(self):
        """测试 evaluate() 分数刚好等于阈值"""
        evaluator = XiuzhenEvaluator()
        # 感知境阈值 0.60
        report = evaluator.evaluate({"a": 0.60, "b": 0.60}, "精确")
        assert report["breakthrough"] is True

    def test_evaluate_rounds_scores(self):
        """测试 evaluate() 分数四舍五入"""
        evaluator = XiuzhenEvaluator()
        report = evaluator.evaluate({"a": 0.123456}, "")
        assert report["overall_score"] == 0.123

    def test_evaluate_dimension_scores_rounded(self):
        """测试 evaluate() 维度分数四舍五入"""
        evaluator = XiuzhenEvaluator()
        report = evaluator.evaluate({"a": 0.123456}, "")
        assert report["dimension_scores"]["a"] == 0.123

    # --- simulate_breakthrough() ---

    def test_simulate_breakthrough_sets_realm(self):
        """测试 simulate_breakthrough() 设置境界"""
        evaluator = XiuzhenEvaluator()
        # 使用低于阈值的分数避免触发二次突破（第5境阈值 0.75）
        result = evaluator.simulate_breakthrough(5, 0.50)
        assert evaluator.cultivator.current_realm == 5

    def test_simulate_breakthrough_returns_report(self):
        """测试 simulate_breakthrough() 返回报告"""
        evaluator = XiuzhenEvaluator()
        result = evaluator.simulate_breakthrough(3, 0.80)
        assert "overall_score" in result
        assert "cultivator" in result
        assert "dimension_scores" in result
        assert result["dimension_scores"]["simulated"] == 0.80

    def test_simulate_breakthrough_to_realm_9(self):
        """测试 simulate_breakthrough() 到第 9 境"""
        evaluator = XiuzhenEvaluator()
        result = evaluator.simulate_breakthrough(9, 0.90)
        assert evaluator.cultivator.current_realm == 9

    def test_simulate_breakthrough_from_realm_1(self):
        """测试 simulate_breakthrough() 设置到第 1 境"""
        evaluator = XiuzhenEvaluator()
        evaluator.simulate_breakthrough(1, 0.50)
        assert evaluator.cultivator.current_realm == 1

    # --- get_realm_progress() ---

    def test_get_realm_progress_structure(self):
        """测试 get_realm_progress() 结构"""
        evaluator = XiuzhenEvaluator()
        progress = evaluator.get_realm_progress()
        assert "current_realm" in progress
        assert "realm_name" in progress
        assert "progress_to_next" in progress
        assert "next_threshold" in progress
        assert "total_qi" in progress

    def test_get_realm_progress_at_start(self):
        """测试 get_realm_progress() 初始状态"""
        evaluator = XiuzhenEvaluator()
        progress = evaluator.get_realm_progress()
        assert progress["current_realm"] == 1
        assert progress["realm_name"] == "感知境"
        assert progress["next_threshold"] == 0.65

    def test_get_realm_progress_after_qi(self):
        """测试 get_realm_progress() 累积元气后"""
        evaluator = XiuzhenEvaluator()
        evaluator.cultivator.total_qi = 50.0
        progress = evaluator.get_realm_progress()
        # next_realm required_qi = 0.0, so progress = 50.0 / max(0.01, 0.0) = 5000.0
        assert progress["progress_to_next"] == 5000.0

    def test_get_realm_progress_at_realm_9(self):
        """测试 get_realm_progress() 在第 9 境"""
        evaluator = XiuzhenEvaluator()
        evaluator.cultivator.current_realm = 9
        progress = evaluator.get_realm_progress()
        assert progress["progress_to_next"] == 1.0
        assert progress["next_threshold"] == 1.0

    # --- get_progress() ---

    def test_get_progress_structure(self):
        """测试 get_progress() 结构"""
        evaluator = XiuzhenEvaluator()
        progress = evaluator.get_progress()
        assert "current_realm" in progress
        assert "next_realm" in progress
        assert "total_qi" in progress
        assert "cultivation_days" in progress
        assert "breakthroughs" in progress
        assert "heart_demon_attempts" in progress
        assert "heart_demon_passed" in progress
        assert "all_realms" in progress

    def test_get_progress_all_realms_count(self):
        """测试 get_progress() all_realms 有 9 个境界"""
        evaluator = XiuzhenEvaluator()
        progress = evaluator.get_progress()
        assert len(progress["all_realms"]) == 9

    def test_get_progress_all_realms_current(self):
        """测试 get_progress() 标记当前境界"""
        evaluator = XiuzhenEvaluator()
        evaluator.cultivator.current_realm = 3
        progress = evaluator.get_progress()
        for r in progress["all_realms"]:
            if r["index"] == 3:
                assert r["current"] is True
            else:
                assert r["current"] is False

    def test_get_progress_all_realms_passed(self):
        """测试 get_progress() 标记已通过的境界"""
        evaluator = XiuzhenEvaluator()
        evaluator.cultivator.current_realm = 4
        progress = evaluator.get_progress()
        for r in progress["all_realms"]:
            if r["index"] < 4:
                assert r["passed"] is True
            else:
                assert r["passed"] is False

    def test_get_progress_all_realms_at_realm_1(self):
        """测试 get_progress() 在第 1 境无已通过境界"""
        evaluator = XiuzhenEvaluator()
        progress = evaluator.get_progress()
        for r in progress["all_realms"]:
            assert r["passed"] is False
        assert progress["all_realms"][0]["current"] is True

    def test_get_progress_all_realms_at_realm_9(self):
        """测试 get_progress() 在第 9 境所有前 8 境已通过"""
        evaluator = XiuzhenEvaluator()
        evaluator.cultivator.current_realm = 9
        progress = evaluator.get_progress()
        for r in progress["all_realms"]:
            if r["index"] < 9:
                assert r["passed"] is True
            if r["index"] == 9:
                assert r["current"] is True
                assert r["passed"] is False

    def test_get_progress_next_realm_at_9(self):
        """测试 get_progress() 在第 9 境 next_realm 为 None"""
        evaluator = XiuzhenEvaluator()
        evaluator.cultivator.current_realm = 9
        progress = evaluator.get_progress()
        assert progress["next_realm"] is None

    def test_get_progress_current_realm_is_dict(self):
        """测试 get_progress() current_realm 是 dict"""
        evaluator = XiuzhenEvaluator()
        progress = evaluator.get_progress()
        assert isinstance(progress["current_realm"], dict)
        assert progress["current_realm"]["index"] == 1

    def test_get_progress_after_breakthrough(self):
        """测试 get_progress() 突破后状态更新"""
        evaluator = XiuzhenEvaluator()
        evaluator.evaluate({"a": 0.90}, "test")
        progress = evaluator.get_progress()
        assert progress["breakthroughs"] == 1
        assert progress["current_realm"]["index"] == 2

    def test_get_progress_all_realms_values(self):
        """测试 get_progress() all_realms 各项值"""
        evaluator = XiuzhenEvaluator()
        evaluator.cultivator.current_realm = 3
        progress = evaluator.get_progress()
        r = progress["all_realms"][2]  # index 3
        assert r["index"] == 3
        assert r["name"] == "化虚境"
        assert r["threshold"] == 0.70
        assert r["current"] is True
        assert r["passed"] is False


# ============================================================================
# 6. 单例函数测试
# ============================================================================

class TestSingletons:
    """测试 get_cultivator() 和 get_evaluator() 单例"""

    def test_get_cultivator_returns_cultivator(self):
        """测试 get_cultivator() 返回 Cultivator 实例"""
        c = get_cultivator()
        assert isinstance(c, Cultivator)

    def test_get_cultivator_is_singleton(self):
        """测试 get_cultivator() 返回同一实例"""
        c1 = get_cultivator()
        c2 = get_cultivator()
        assert c1 is c2

    def test_get_evaluator_returns_evaluator(self):
        """测试 get_evaluator() 返回 XiuzhenEvaluator 实例"""
        e = get_evaluator()
        assert isinstance(e, XiuzhenEvaluator)

    def test_get_evaluator_is_singleton(self):
        """测试 get_evaluator() 返回同一实例"""
        e1 = get_evaluator()
        e2 = get_evaluator()
        assert e1 is e2

    def test_get_cultivator_and_get_evaluator_independent(self):
        """测试两个单例函数独立"""
        c = get_cultivator()
        e = get_evaluator()
        assert isinstance(c, Cultivator)
        assert isinstance(e, XiuzhenEvaluator)
        assert c is not e


# ============================================================================
# 7. 边界情况测试
# ============================================================================

class TestEdgeCases:
    """边界情况测试"""

    def test_realm_9_no_breakthrough_beyond(self):
        """测试第 9 境不能突破到第 10 境"""
        c = Cultivator(current_realm=9)
        passed, _ = c.attempt_breakthrough(0.95, "test")
        assert c.current_realm == 9

    def test_cultivator_init_negative_qi(self):
        """测试 Cultivator 初始负元气"""
        c = Cultivator(total_qi=-100.0)
        assert c.total_qi == -100.0

    def test_cultivator_init_high_qi(self):
        """测试 Cultivator 初始极高元气"""
        c = Cultivator(total_qi=1e10)
        assert c.total_qi == 1e10

    def test_evaluate_very_high_scores(self):
        """测试 evaluate() 极高分数"""
        evaluator = XiuzhenEvaluator()
        report = evaluator.evaluate({"a": 1000.0, "b": 2000.0}, "超级高分")
        assert report["overall_score"] == 1500.0
        assert report["breakthrough"] is True

    def test_evaluate_very_low_scores(self):
        """测试 evaluate() 极低分数"""
        evaluator = XiuzhenEvaluator()
        report = evaluator.evaluate({"a": 0.0, "b": 0.0}, "零分")
        assert report["overall_score"] == 0.0
        assert report["breakthrough"] is False

    def test_evaluate_negative_scores(self):
        """测试 evaluate() 负数分数"""
        evaluator = XiuzhenEvaluator()
        report = evaluator.evaluate({"a": -0.5, "b": -0.3}, "负数")
        assert report["overall_score"] == -0.4
        assert report["breakthrough"] is False

    def test_evaluate_zero_qi_accumulation(self):
        """测试零分不累积元气"""
        evaluator = XiuzhenEvaluator()
        evaluator.evaluate({"a": 0.0}, "")
        assert evaluator.cultivator.total_qi == 0.0

    def test_evaluate_negative_qi_accumulation(self):
        """测试负分元气累积"""
        evaluator = XiuzhenEvaluator()
        evaluator.evaluate({"a": -0.5}, "")
        assert evaluator.cultivator.total_qi == pytest.approx(-0.05)

    def test_multiple_breakthroughs_full_journey(self):
        """测试完整修真旅程：从感知境到无极境"""
        evaluator = XiuzhenEvaluator()
        realms_before = evaluator.cultivator.current_realm
        for i in range(8):
            evaluator.evaluate({"a": 0.90}, f"journey_{i}")
        assert evaluator.cultivator.current_realm == 9
        assert len(evaluator.cultivator.breakthrough_history) == 8

    def test_cultivator_to_dict_after_breakthrough(self):
        """测试突破后 to_dict() 正确"""
        c = Cultivator(current_realm=1)
        c.attempt_breakthrough(0.90, "test")
        d = c.to_dict()
        assert d["current_realm"] == 2
        assert d["breakthroughs"] == 1
        assert d["pass_rate"] == 1.0

    def test_cultivator_to_dict_after_failure(self):
        """测试失败后 to_dict() 正确"""
        c = Cultivator(current_realm=1)
        c.attempt_breakthrough(0.30, "test")
        d = c.to_dict()
        assert d["current_realm"] == 1
        assert d["breakthroughs"] == 0
        assert d["pass_rate"] == 0.0

    def test_heart_demon_forge_instantiation(self):
        """测试 HeartDemonForge 可以实例化"""
        forge = HeartDemonForge()
        assert isinstance(forge, HeartDemonForge)

    def test_evaluator_instantiation_multiple(self):
        """测试多个 XiuzhenEvaluator 实例独立"""
        e1 = XiuzhenEvaluator()
        e2 = XiuzhenEvaluator()
        assert e1 is not e2
        e1.evaluate({"a": 0.90}, "")
        assert e1.cultivator.current_realm != e2.cultivator.current_realm

    def test_get_progress_after_partial_breakthrough(self):
        """测试部分突破后 get_progress()"""
        evaluator = XiuzhenEvaluator()
        evaluator.evaluate({"a": 0.90}, "")  # 突破到 2
        evaluator.evaluate({"a": 0.90}, "")  # 突破到 3
        evaluator.evaluate({"a": 0.50}, "")  # 失败
        progress = evaluator.get_progress()
        assert progress["current_realm"]["index"] == 3
        assert progress["breakthroughs"] == 2
        assert progress["heart_demon_attempts"] == 3
        assert progress["heart_demon_passed"] == 2
        assert progress["all_realms"][0]["passed"] is True
        assert progress["all_realms"][1]["passed"] is True
        assert progress["all_realms"][2]["passed"] is False
        assert progress["all_realms"][2]["current"] is True

    def test_to_dict_total_qi_rounded(self):
        """测试 to_dict() total_qi 四舍五入到 3 位"""
        c = Cultivator(total_qi=3.14159265)
        d = c.to_dict()
        assert d["total_qi"] == 3.142

    def test_to_dict_total_qi_rounded_int(self):
        """测试 to_dict() total_qi 整数也是 3 位小数"""
        c = Cultivator(total_qi=100.0)
        d = c.to_dict()
        assert d["total_qi"] == 100.0

    def test_attempt_breakthrough_msg_format(self):
        """测试突破消息格式"""
        c = Cultivator(current_realm=1)
        _, msg = c.attempt_breakthrough(0.90, "心魔测试")
        assert "突破" in msg
        assert "感知境" in msg
        assert "知止境" in msg

    def test_attempt_breakthrough_fail_msg_format(self):
        """测试失败消息格式"""
        c = Cultivator(current_realm=1)
        _, msg = c.attempt_breakthrough(0.30, "失败测试")
        assert "心魔未破" in msg
        assert "0.30" in msg
        assert "0.6" in msg

    def test_realm_to_dict_all_fields(self):
        """测试 to_dict() 包含所有关键字段"""
        r = Realm(1, "x", "y")
        d = r.to_dict()
        assert set(d.keys()) == {"index", "name", "description", "pass_threshold", "required_qi"}

    def test_evaluate_dimension_scores_are_copies(self):
        """测试 evaluate() 返回的 dimension_scores 是副本"""
        evaluator = XiuzhenEvaluator()
        scores = {"a": 0.80}
        report = evaluator.evaluate(scores, "")
        scores["a"] = 999.0
        assert report["dimension_scores"]["a"] == 0.80

    def test_cultivator_breakthrough_history_is_copy(self):
        """测试突破历史可以通过列表方法操作"""
        c = Cultivator(current_realm=1)
        c.attempt_breakthrough(0.90, "t1")
        c.attempt_breakthrough(0.90, "t2")
        # 检查列表完整性
        assert len(c.breakthrough_history) == 2
        assert c.breakthrough_history[0]["test"] == "t1"
        assert c.breakthrough_history[1]["test"] == "t2"

    def test_accumulate_qi_after_breakthrough(self):
        """测试突破后仍然可以累积元气"""
        c = Cultivator(current_realm=1)
        c.attempt_breakthrough(0.90, "test")
        c.accumulate_qi(10.0)
        assert c.total_qi == 10.0
        assert c.current_realm == 2


# ============================================================================
# 8. 综合场景测试
# ============================================================================

class TestIntegrationScenarios:
    """综合场景测试"""

    def test_full_evaluator_lifecycle(self):
        """测试评估器完整生命周期"""
        evaluator = XiuzhenEvaluator()

        # 初始状态
        assert evaluator.cultivator.current_realm == 1
        assert evaluator.cultivator.total_qi == 0.0

        # 多次评估逐步突破
        evaluator.evaluate({"pattern": 0.75, "classify": 0.80}, "感知测试")
        assert evaluator.cultivator.current_realm == 2

        evaluator.evaluate({"confidence": 0.85, "unknown": 0.70}, "知止测试")
        assert evaluator.cultivator.current_realm == 3

        evaluator.evaluate({"hallucination": 0.90, "fact": 0.85}, "化虚测试")
        assert evaluator.cultivator.current_realm == 4

        # 获取进度
        progress = evaluator.get_progress()
        assert progress["current_realm"]["index"] == 4
        assert progress["breakthroughs"] == 3
        assert len(progress["all_realms"]) == 9

        # 验证已通过境界
        passed_indices = [r["index"] for r in progress["all_realms"] if r["passed"]]
        assert passed_indices == [1, 2, 3]

        current = [r["index"] for r in progress["all_realms"] if r["current"]]
        assert current == [4]

    def test_simulate_breakthrough_then_evaluate(self):
        """测试模拟突破后继续评估"""
        evaluator = XiuzhenEvaluator()
        # 使用低于阈值的分数，避免 simulate_breakthrough 内部触发二次突破
        evaluator.simulate_breakthrough(5, 0.50)
        assert evaluator.cultivator.current_realm == 5

        # 在模拟的境界上继续评估，使用高分触发突破
        evaluator.evaluate({"a": 0.85}, "合道测试")
        assert evaluator.cultivator.current_realm == 6

    def test_mixed_pass_fail_sequence(self):
        """测试混合通过/失败序列"""
        c = Cultivator(current_realm=1)
        results = []
        scores = [0.30, 0.90, 0.40, 0.90, 0.50, 0.90]
        for s in scores:
            results.append(c.attempt_breakthrough(s, "test"))

        assert results[0][0] is False
        assert results[1][0] is True
        assert results[2][0] is False
        assert results[3][0] is True
        assert results[4][0] is False
        assert results[5][0] is True

        assert c.current_realm == 4
        assert c.heart_demon_attempts == 6
        assert c.heart_demon_passed == 3
        assert len(c.breakthrough_history) == 3
        assert len(c.failures) == 3

    def test_evaluator_realm_progress_after_qi(self):
        """测试累积元气后境界进度"""
        evaluator = XiuzhenEvaluator()
        evaluator.cultivator.accumulate_qi(100.0)
        evaluator.cultivator.cultivation_days = 50

        realm_progress = evaluator.get_realm_progress()
        assert realm_progress["total_qi"] == 100.0
        assert realm_progress["cultivation_days"] == 50

    def test_nine_realms_immutable_read(self):
        """测试 NINE_REALMS 可被读取"""
        assert NINE_REALMS[0].name == "感知境"
        assert NINE_REALMS[4].name == "合道境"
        assert NINE_REALMS[8].name == "无极境"

    def test_cultivator_fields_are_mutable(self):
        """测试 Cultivator 字段可变"""
        c = Cultivator()
        c.current_realm = 5
        c.total_qi = 999.0
        c.cultivation_days = 100
        assert c.current_realm == 5
        assert c.total_qi == 999.0
        assert c.cultivation_days == 100

    def test_realm_fields_are_mutable(self):
        """测试 Realm 字段可变"""
        r = Realm(1, "x", "y")
        r.pass_threshold = 0.99
        r.required_qi = 500.0
        assert r.pass_threshold == 0.99
        assert r.required_qi == 500.0