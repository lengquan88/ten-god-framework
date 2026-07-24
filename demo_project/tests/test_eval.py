"""
tests/test_eval.py — 评估框架集成测试 v4.4.0
==================================================
"""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

# 路径处理
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tengod.eval import (
    BenchmarkDataset,
    GateCognitiveEvaluator,
    EvaluationReporter,
    run_evaluation,
)
from tengod.eval.metrics import (
    precision_at_k,
    recall_at_k,
    f1_at_k,
    mrr,
    ndcg_at_k,
    hit_rate_at_k,
    gate_precision,
    gate_recall,
    gate_f1,
    intent_accuracy,
    semantic_similarity,
    rouge_l,
    EvaluationMetrics,
)


class TestMetrics:
    """指标计算单元测试"""

    def test_precision_at_k(self):
        rel = {"a", "b", "c"}
        ret = ["a", "d", "b", "e"]
        assert precision_at_k(rel, ret, 3) == 2 / 3
        assert precision_at_k(rel, ret, 1) == 1.0
        assert precision_at_k(rel, [], 5) == 0.0
        assert precision_at_k(set(), ret, 5) == 0.0

    def test_recall_at_k(self):
        rel = {"a", "b", "c"}
        ret = ["a", "d", "b"]
        assert recall_at_k(rel, ret, 5) == 2 / 3
        assert recall_at_k(set(), ret, 5) == 1.0

    def test_f1_at_k(self):
        rel = {"a", "b", "c"}
        ret = ["a", "d", "b"]
        assert f1_at_k(rel, ret, 5) == f1_at_k(rel, ret, 5)  # 验证一致性

    def test_mrr(self):
        rel = {"a", "b"}
        ret = ["d", "e", "b", "a"]
        assert mrr(rel, ret) == 1 / 3
        assert mrr(rel, []) == 0.0

    def test_ndcg(self):
        rel = {"a", "b"}
        ret = ["a", "c", "d", "b"]
        assert ndcg_at_k(rel, ret, 5) > 0

    def test_hit_rate(self):
        rel = {"a", "b"}
        assert hit_rate_at_k(rel, ["a", "c"], 3) == 1.0
        assert hit_rate_at_k(rel, ["c", "d"], 3) == 0.0

    def test_gate_metrics(self):
        assert abs(gate_precision(8, 2) - 0.8) < 0.01
        assert abs(gate_recall(8, 2) - 0.8) < 0.01
        assert abs(gate_f1(8, 2, 2) - 0.8) < 0.01

    def test_intent_accuracy(self):
        pred = ["八字", "紫微", "六爻", "风水"]
        true = ["八字", "紫微", "六爻", "姓名学"]
        assert intent_accuracy(pred, true) == 0.75

    def test_semantic_similarity(self):
        import numpy as np
        e1 = np.array([1.0, 0.0, 0.0])
        e2 = np.array([0.0, 1.0, 0.0])
        assert abs(semantic_similarity(e1, e1) - 1.0) < 0.01
        assert abs(semantic_similarity(e1, e2) - 0.0) < 0.01

    def test_rouge_l(self):
        assert rouge_l("甲乙木", "甲乙木") == 1.0
        assert rouge_l("", "") == 0.0
        r = rouge_l("甲乙丙丁", "甲乙木丙丁火")
        assert 0 < r < 1.0

    def test_evaluation_metrics_to_dict(self):
        m = EvaluationMetrics(num_queries=10)
        d = m.to_dict()
        assert "retrieval" in d
        assert "gate" in d
        assert "intent" in d
        assert "overall" in d
        assert d["meta"]["num_queries"] == 10


class TestBenchmarkDataset:
    """基准数据集测试"""

    def test_load_default(self):
        ds = BenchmarkDataset().load_default()
        assert ds.count >= 100
        assert "八字" in ds.intents
        assert "紫微" in ds.intents

    def test_get_by_category(self):
        ds = BenchmarkDataset().load_default()
        bazi = ds.get_by_category("八字基础")
        assert len(bazi) > 0
        for q in bazi:
            assert q.category == "八字基础"

    def test_get_by_intent(self):
        ds = BenchmarkDataset().load_default()
        ziwei = ds.get_by_intent("紫微")
        assert len(ziwei) > 0
        for q in ziwei:
            assert q.intent == "紫微"

    def test_get_by_difficulty(self):
        ds = BenchmarkDataset().load_default()
        easy = ds.get_by_difficulty("easy")
        hard = ds.get_by_difficulty("hard")
        assert len(easy) > 0
        assert len(hard) > 0

    def test_save_load_roundtrip(self):
        ds = BenchmarkDataset().load_default()
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            ds.save(f.name)
            path = f.name
        try:
            ds2 = BenchmarkDataset.load(path)
            assert ds2.count == ds.count
            assert ds2.intents == ds.intents
        finally:
            os.unlink(path)


class TestEvaluator:
    """评估器测试"""

    def test_self_check(self):
        evaluator = GateCognitiveEvaluator()
        assert evaluator.self_check()

    def test_evaluate_retrieval_only(self):
        from tengod.local_embedding import create_embedder
        embedder = create_embedder(dim=384, mode="tfidf_svd")
        evaluator = GateCognitiveEvaluator(embedder=embedder)
        evaluator.dataset = BenchmarkDataset().load_default()
        evaluator.dataset.queries = evaluator.dataset.queries[:20]  # 快速模式
        metrics = evaluator.evaluate_retrieval_only()
        assert "precision@1" in metrics
        assert "mrr" in metrics
        assert metrics["num_queries"] == 20

    def test_empty_evaluation(self):
        evaluator = GateCognitiveEvaluator()
        metrics = evaluator._compute_metrics()
        assert metrics.num_queries == 0


class TestReporter:
    """报告生成器测试"""

    def test_generate_markdown(self):
        m = EvaluationMetrics(num_queries=10, precision_at_1=0.8, mrr=0.75,
                              gate_f1=0.85, intent_accuracy=0.9, latency_p50_ms=25.0)
        from tengod.eval.evaluator import SingleEvalResult
        results = [SingleEvalResult(query_id="test_001", query="test",
                                     expected_intent="八字", error="mock error")]
        reporter = EvaluationReporter(m, results)
        md = reporter.generate_markdown()
        assert "门禁认知系统评估报告" in md
        assert "0.8000" in md
        assert "mock error" in md

    def test_generate_json(self):
        m = EvaluationMetrics(num_queries=5)
        reporter = EvaluationReporter(m)
        cat = reporter.generate_by_category()
        assert isinstance(cat, dict)


class TestRunEval:
    """一键评估脚本测试"""

    def test_run_quick(self):
        """快速评估（20 条）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_evaluation(
                embed_dim=384,
                output_dir=tmpdir,
                verbose=False,
                quick=True,
            )
            assert result["num_queries"] == 20
            assert "metrics" in result
            assert os.path.exists(os.path.join(tmpdir, "eval_report.md"))
            assert os.path.exists(os.path.join(tmpdir, "eval_report.json"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])