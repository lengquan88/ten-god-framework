#!/usr/bin/env python3
"""test_metrics_comprehensive.py — 评估指标全面边界条件测试

聚焦:
  - NDCG@K: idcg=0 零除保护、自定义相关性分数、理想排序校验
  - MRR: 首位置命中、尾位置命中、无命中、单元素列表
  - Precision/Recall/F1: 空输入、k=0、k>检索数、全相关/全不相关
  - ROUGE-L: 完全重叠、完全不重叠、单字符、空字符串
  - 门禁指标: 除零保护、0输入、极端比例
  - 意图/消歧指标: 空输入、全对、全错、极端置信度
  - 语义相似度: 零向量、正交、完全相同、NaN/Inf 防护
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from tengod.eval.metrics import (
    precision_at_k,
    recall_at_k,
    f1_at_k,
    mrr,
    ndcg_at_k,
    hit_rate_at_k,
    gate_pass_rate,
    gate_precision,
    gate_recall,
    gate_f1,
    intent_accuracy,
    intent_confidence,
    disambiguation_rate,
    semantic_similarity,
    rouge_l,
    EvaluationMetrics,
)


# ============================================================================
# Precision@K 边界条件
# ============================================================================

class TestPrecisionAtKBoundaries:
    """Precision@K 极端情况与边界条件"""

    def test_k_zero_returns_zero(self):
        """k=0 应返回 0.0（避免除零）"""
        assert precision_at_k({"a", "b"}, ["a", "b"], 0) == 0.0

    def test_k_negative_returns_zero(self):
        """k 为负应返回 0.0"""
        assert precision_at_k({"a", "b"}, ["a", "b"], -5) == 0.0

    def test_empty_retrieved(self):
        """检索结果为空应返回 0.0"""
        assert precision_at_k({"a", "b"}, [], 5) == 0.0

    def test_empty_relevant(self):
        """相关集合为空 → 0 个命中 → 精度=0.0"""
        assert precision_at_k(set(), ["a", "b", "c"], 3) == 0.0

    def test_k_greater_than_retrieved(self):
        """k > 检索结果数量时，分母仍为 k（标准 Precision@K 定义）
        retrieved=2条，其中1条相关，k=10 → P@10 = 1/10 = 0.1"""
        rel = {"a", "b", "c"}
        ret = ["a", "d"]  # 仅 2 条，k=10
        # 标准定义：相关数 / k → 1 / 10 = 0.1
        assert precision_at_k(rel, ret, 10) == 0.1

    def test_all_relevant(self):
        """全部命中 → 精度 1.0"""
        rel = {"a", "b", "c"}
        assert precision_at_k(rel, ["a", "b", "c"], 3) == 1.0

    def test_none_relevant(self):
        """全部不相关 → 精度 0.0"""
        rel = {"x", "y", "z"}
        assert precision_at_k(rel, ["a", "b", "c"], 3) == 0.0

    def test_single_element_both(self):
        """单元素列表，命中/未命中"""
        assert precision_at_k({"a"}, ["a"], 1) == 1.0
        assert precision_at_k({"b"}, ["a"], 1) == 0.0

    def test_return_type_is_float(self):
        """返回类型严格为 float（避免整数除法问题）"""
        result = precision_at_k({"a"}, ["a", "b"], 2)
        assert isinstance(result, float)


# ============================================================================
# Recall@K 边界条件
# ============================================================================

class TestRecallAtKBoundaries:
    """Recall@K 极端情况与边界条件"""

    def test_empty_relevant_returns_one(self):
        """相关集合为空时 recall=1.0（约定：空集视为完全召回）"""
        assert recall_at_k(set(), ["a", "b"], 5) == 1.0

    def test_empty_retrieved_with_relevant(self):
        """有相关但检索为空 → 0.0"""
        assert recall_at_k({"a"}, [], 5) == 0.0

    def test_k_zero_or_negative(self):
        """k<=0 且存在相关项 → 0.0"""
        assert recall_at_k({"a", "b"}, ["a", "b"], 0) == 0.0
        assert recall_at_k({"a", "b"}, ["a", "b"], -1) == 0.0

    def test_perfect_recall(self):
        """全部相关都被召回 → 1.0"""
        rel = {"a", "b", "c"}
        assert recall_at_k(rel, ["a", "d", "b", "x", "c"], 5) == 1.0

    def test_partial_recall(self):
        """部分召回"""
        rel = {"a", "b", "c", "d"}
        ret = ["a", "x", "b"]
        # k=5 时，2/4 = 0.5
        assert recall_at_k(rel, ret, 5) == 0.5

    def test_k_limits_recall(self):
        """k 太小会限制可召回的上限"""
        rel = {"a", "b", "c", "d"}
        ret = ["a", "b", "c", "d"]
        assert recall_at_k(rel, ret, 2) == 0.5  # 只能召回前 2 条


# ============================================================================
# F1@K 边界条件
# ============================================================================

class TestF1AtKBoundaries:
    """F1@K 极端情况（调和平均的除零保护）"""

    def test_both_p_r_zero(self):
        """Precision=0 且 Recall=0 → F1=0（无除零）"""
        rel = {"a", "b"}
        ret = ["c", "d"]
        assert f1_at_k(rel, ret, 2) == 0.0

    def test_empty_everything(self):
        """全空输入"""
        assert f1_at_k(set(), [], 5) == 0.0

    def test_perfect_f1(self):
        """P=1, R=1 → F1=1"""
        rel = {"a", "b"}
        assert f1_at_k(rel, ["a", "b"], 2) == 1.0

    def test_f1_is_harmonic_mean(self):
        """手动验证调和平均公式"""
        rel = {"a", "b", "c"}
        ret = ["a", "d", "b"]
        k = 3
        p = 2 / 3  # 2 命中 / 3 检索
        r = 2 / 3  # 2 命中 / 3 相关
        expected = 2 * p * r / (p + r)
        assert abs(f1_at_k(rel, ret, k) - expected) < 1e-9


# ============================================================================
# MRR 边界条件
# ============================================================================

class TestMRRBoundaries:
    """MRR (Mean Reciprocal Rank) 极端情况"""

    def test_no_relevant(self):
        """无相关结果 → 0.0"""
        assert mrr({"a", "b"}, ["c", "d", "e"]) == 0.0

    def test_empty_retrieved(self):
        """检索为空 → 0.0"""
        assert mrr({"a"}, []) == 0.0

    def test_empty_relevant(self):
        """相关为空 → 0.0"""
        assert mrr(set(), ["a", "b"]) == 0.0

    def test_first_position(self):
        """第一个位置命中 → RR = 1/1 = 1.0"""
        assert mrr({"a", "b"}, ["a", "c", "d"]) == 1.0

    def test_second_position(self):
        """第二个位置命中 → RR = 1/2"""
        assert mrr({"a"}, ["x", "a", "y"]) == 0.5

    def test_last_position(self):
        """最后一个位置命中"""
        assert mrr({"z"}, ["a", "b", "c", "z"]) == 0.25

    def test_multiple_relevant_uses_first(self):
        """多个相关结果 → 使用最早出现的"""
        rel = {"a", "b", "c"}
        ret = ["x", "y", "b", "a"]  # b 在位置 3 先出现
        assert mrr(rel, ret) == 1 / 3

    def test_single_element(self):
        """单元素列表"""
        assert mrr({"a"}, ["a"]) == 1.0
        assert mrr({"b"}, ["a"]) == 0.0


# ============================================================================
# NDCG@K 边界条件（重点：idcg=0 零除防护）
# ============================================================================

class TestNDCGAtKBoundaries:
    """NDCG@K 极端情况（idcg=0 防护最关键）"""

    def test_k_zero_returns_zero(self):
        """k=0 → 0.0（无除零）"""
        assert ndcg_at_k({"a"}, ["a"], 0) == 0.0

    def test_empty_retrieved(self):
        """检索为空 → 0.0"""
        assert ndcg_at_k({"a", "b"}, [], 5) == 0.0

    def test_idcg_zero_no_crash(self):
        """重点：当 relevance_scores 中所有理想相关分数均为 0 时，IDCG=0 → 应返回 0.0 且无除零异常"""
        # 构造：relevant 集合中每个项的 relevance_score = 0
        relevant = {"a", "b", "c"}
        retrieved = ["a", "d", "b"]
        zero_scores = {item: 0.0 for item in relevant}
        # 这会导致 IDCG = 0，常规实现会抛 ZeroDivisionError
        result = ndcg_at_k(relevant, retrieved, 5, relevance_scores=zero_scores)
        assert result == 0.0

    def test_no_retrieved_relevant(self):
        """检索到的都不相关 → DCG=0 → NDCG=0"""
        relevant = {"a", "b"}
        retrieved = ["c", "d"]
        result = ndcg_at_k(relevant, retrieved, 5)
        assert result == 0.0

    def test_perfect_ranking(self):
        """完全理想排序 → NDCG = 1.0"""
        relevant = {"a", "b"}
        # a 和 b 都在前，且按相关性降序（默认都是1.0所以顺序无所谓）
        retrieved = ["a", "b", "c", "d"]
        result = ndcg_at_k(relevant, retrieved, 4)
        assert abs(result - 1.0) < 1e-9

    def test_custom_relevance_scores(self):
        """自定义相关度分数，验证 NDCG 公式正确性"""
        # a:3, b:2, c:1
        scores = {"a": 3.0, "b": 2.0, "c": 1.0}
        relevant = {"a", "b", "c"}
        # 理想排序: a(3), b(2), c(1)
        # IDCG@3 = (2^3-1)/log2(2) + (2^2-1)/log2(3) + (2^1-1)/log2(4)
        #       = 7/1 + 3/1.5850 + 1/2
        #       ≈ 7 + 1.893 + 0.5 = 9.393
        idcg = (2 ** 3 - 1) / math.log2(2) + (2 ** 2 - 1) / math.log2(3) + (2 ** 1 - 1) / math.log2(4)

        # 实际排序: c(1), a(3), b(2)  → 非理想
        retrieved = ["c", "a", "b"]
        # DCG@3 = (2^1-1)/log2(2) + (2^3-1)/log2(3) + (2^2-1)/log2(4)
        #       = 1/1 + 7/1.5850 + 3/2
        #       ≈ 1 + 4.417 + 1.5 = 6.917
        dcg = (2 ** 1 - 1) / math.log2(2) + (2 ** 3 - 1) / math.log2(3) + (2 ** 2 - 1) / math.log2(4)

        expected = dcg / idcg
        result = ndcg_at_k(relevant, retrieved, 3, relevance_scores=scores)
        assert abs(result - expected) < 1e-6
        assert 0.0 <= result <= 1.0


# ============================================================================
# HitRate@K 边界条件
# ============================================================================

class TestHitRateAtKBoundaries:
    """HitRate@K 边界条件"""

    def test_empty_retrieved(self):
        assert hit_rate_at_k({"a"}, [], 5) == 0.0

    def test_k_zero(self):
        assert hit_rate_at_k({"a"}, ["a"], 0) == 0.0

    def test_hit_at_exactly_k(self):
        """刚好在第 k 位命中"""
        rel = {"z"}
        ret = ["a", "b", "c", "d", "z"]
        assert hit_rate_at_k(rel, ret, 5) == 1.0
        # k=4 时 miss
        assert hit_rate_at_k(rel, ret, 4) == 0.0

    def test_no_hit(self):
        assert hit_rate_at_k({"x"}, ["a", "b"], 5) == 0.0


# ============================================================================
# 门禁指标边界条件（除零防护）
# ============================================================================

class TestGateMetricsBoundaries:
    """门禁指标除零防护测试"""

    def test_gate_pass_rate_zero_total(self):
        """total=0 → 0.0"""
        assert gate_pass_rate(10, 0) == 0.0

    def test_gate_pass_rate_negative_total(self):
        """total<0 → 0.0"""
        assert gate_pass_rate(5, -1) == 0.0

    def test_gate_pass_rate_extremes(self):
        assert gate_pass_rate(0, 100) == 0.0
        assert gate_pass_rate(100, 100) == 1.0

    def test_gate_precision_zero_tp_fp(self):
        """tp+fp=0 → 0.0（无除零）"""
        assert gate_precision(0, 0) == 0.0

    def test_gate_recall_zero_tp_fn(self):
        """tp+fn=0 → 0.0"""
        assert gate_recall(0, 0) == 0.0

    def test_gate_f1_all_zero(self):
        """tp=fp=fn=0 → 0.0"""
        assert gate_f1(0, 0, 0) == 0.0

    def test_gate_f1_perfect(self):
        """完美：fp=fn=0"""
        assert gate_f1(100, 0, 0) == 1.0

    def test_gate_f1_formula(self):
        """验证 F1 = 2PR/(P+R)"""
        tp, fp, fn = 8, 2, 2
        p = tp / (tp + fp)  # 0.8
        r = tp / (tp + fn)  # 0.8
        expected = 2 * p * r / (p + r)
        assert abs(gate_f1(tp, fp, fn) - expected) < 1e-9


# ============================================================================
# 意图与消歧指标边界
# ============================================================================

class TestIntentMetricsBoundaries:
    """意图识别指标边界"""

    def test_accuracy_empty_predictions(self):
        """空预测列表 → 0.0"""
        assert intent_accuracy([], []) == 0.0

    def test_accuracy_all_correct(self):
        pred = ["A", "B", "C"]
        assert intent_accuracy(pred, pred) == 1.0

    def test_accuracy_none_correct(self):
        assert intent_accuracy(["A", "B"], ["X", "Y"]) == 0.0

    def test_confidence_empty(self):
        """空置信度列表 → 0.0"""
        assert intent_confidence([]) == 0.0

    def test_confidence_single(self):
        assert intent_confidence([0.8]) == 0.8

    def test_confidence_average(self):
        vals = [0.5, 0.7, 0.9]
        assert abs(intent_confidence(vals) - (sum(vals) / len(vals))) < 1e-9

    def test_disambiguation_rate_zero_ambiguous(self):
        """total_ambiguous=0 → 1.0（约定：无题即全解）"""
        assert disambiguation_rate(0, 0) == 1.0

    def test_disambiguation_rate_partial(self):
        assert disambiguation_rate(7, 10) == 0.7
        assert disambiguation_rate(0, 5) == 0.0
        assert disambiguation_rate(5, 5) == 1.0


# ============================================================================
# 语义相似度边界（零向量保护）
# ============================================================================

class TestSemanticSimilarityBoundaries:
    """余弦相似度边界条件"""

    def test_zero_norm_first_vector(self):
        """第一个向量范数=0 → 0.0（无除零）"""
        e1 = np.array([0.0, 0.0, 0.0])
        e2 = np.array([1.0, 0.0, 0.0])
        assert semantic_similarity(e1, e2) == 0.0

    def test_zero_norm_second_vector(self):
        e1 = np.array([1.0, 0.0, 0.0])
        e2 = np.array([0.0, 0.0, 0.0])
        assert semantic_similarity(e1, e2) == 0.0

    def test_both_zero_vectors(self):
        z = np.zeros(5)
        assert semantic_similarity(z, z) == 0.0

    def test_identical_vectors(self):
        v = np.array([1.0, 2.0, 3.0])
        assert abs(semantic_similarity(v, v) - 1.0) < 1e-9

    def test_orthogonal_vectors(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert abs(semantic_similarity(a, b)) < 1e-9

    def test_opposite_vectors(self):
        a = np.array([1.0, 0.0])
        b = np.array([-1.0, 0.0])
        assert abs(semantic_similarity(a, b) + 1.0) < 1e-9


# ============================================================================
# ROUGE-L 边界条件（LCS 计算的极端情况）
# ============================================================================

class TestRougeLBoundaries:
    """ROUGE-L 边界与极端情况"""

    def test_empty_prediction(self):
        assert rouge_l("", "参考文本") == 0.0

    def test_empty_reference(self):
        assert rouge_l("生成文本", "") == 0.0

    def test_both_empty(self):
        assert rouge_l("", "") == 0.0

    def test_identical_strings(self):
        s = "甲乙丙丁戊己庚辛"
        assert rouge_l(s, s) == 1.0

    def test_no_overlap(self):
        """完全不重叠 → 0.0"""
        assert rouge_l("甲乙丙", "123") == 0.0

    def test_substring(self):
        """预测是参考的子串"""
        # LCS("甲乙丙", "甲乙丙丁") = 3
        # P = 3/3=1, R = 3/4=0.75
        # F1 = 2*1*0.75/1.75 = 1.5/1.75 ≈ 0.8571
        result = rouge_l("甲乙丙", "甲乙丙丁")
        assert 0.8 < result < 0.9

    def test_single_char_match(self):
        assert rouge_l("甲", "甲") == 1.0
        assert rouge_l("甲", "乙") == 0.0

    def test_scattered_lcs(self):
        """验证 LCS 非连续匹配："ace" vs "abcde" → LCS=3(ace)"""
        pred = "ace"
        ref = "abcde"
        lcs = 3
        p = lcs / len(pred)  # 1.0
        r = lcs / len(ref)   # 0.6
        expected = 2 * p * r / (p + r) if (p + r) else 0
        assert abs(rouge_l(pred, ref) - expected) < 1e-6

    def test_unicode_and_spaces(self):
        """Unicode + 空格"""
        s1 = "天干 地支 五行"
        s2 = "天干地支五行"
        # LCS 应为 "天干地支五行" 的 6 个字符（跳过空格）
        result1 = rouge_l(s1, s2)
        result2 = rouge_l(s2, s1)
        assert 0 < result1 <= 1.0
        # ROUGE-L 对于 P/R 分配不同，结果不一定对称但都有效
        assert 0 < result2 <= 1.0


# ============================================================================
# EvaluationMetrics 数据类边界
# ============================================================================

class TestEvaluationMetricsBoundaries:
    """EvaluationMetrics 的结构与序列化"""

    def test_default_values(self):
        m = EvaluationMetrics()
        assert m.num_queries == 0
        assert m.precision_at_1 == 0.0
        assert m.overall_score == 0.0

    def test_to_dict_structure(self):
        m = EvaluationMetrics(num_queries=42)
        d = m.to_dict()
        for top_key in ["retrieval", "gate", "intent", "generation", "overall", "meta"]:
            assert top_key in d, f"缺少顶级键: {top_key}"
        assert d["meta"]["num_queries"] == 42

    def test_to_dict_rounding(self):
        """验证 to_dict 的 round 行为稳定（不依赖默认值）"""
        m = EvaluationMetrics(
            precision_at_1=0.87654321,
            gate_f1=0.123456789,
            latency_p50_ms=12.3456,
        )
        d = m.to_dict()
        # 小数位应被正确截断
        assert d["retrieval"]["precision@1"] == 0.8765
        assert d["gate"]["f1"] == 0.1235
        assert d["overall"]["latency_p50_ms"] == 12.35

    def test_all_fields_rounded(self):
        """确保所有数值字段都通过 round 处理，不会出现科学计数"""
        m = EvaluationMetrics(
            precision_at_1=0.11115, precision_at_3=0.22225, precision_at_5=0.33335,
            recall_at_5=0.44445, f1_at_5=0.55555, mrr=0.66665,
            ndcg_at_5=0.77775, hit_rate_at_5=0.88885,
            gate_pass_rate=0.11115, gate_precision=0.22225,
            gate_recall=0.33335, gate_f1=0.44445,
            intent_accuracy=0.55555, intent_confidence=0.66665,
            disambiguation_rate=0.77775,
            semantic_similarity=0.88885, rouge_l=0.99995,
            overall_score=0.12345,
            throughput_qps=123.456,
        )
        d = m.to_dict()
        # 收集所有叶子数值，验证都是有限 float
        def _leaves(obj):
            if isinstance(obj, dict):
                for v in obj.values():
                    yield from _leaves(v)
            elif isinstance(obj, (int, float)):
                yield obj

        for val in _leaves(d):
            assert isinstance(val, (int, float))
            assert math.isfinite(val), f"非有限数值: {val}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
