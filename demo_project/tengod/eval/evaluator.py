"""
eval/evaluator.py — 门禁认知评估器 v3.9.0
==============================================
道曰："胜人者有力，自胜者强。"

GateCognitiveEvaluator 评估器主类：
  - 加载基准数据集
  - 逐条运行引擎并收集结果
  - 计算四维指标（检索/门禁/意图/生成）
  - 生成评估报告
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

# 路径处理
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_TENGOD_DIR = os.path.dirname(_THIS_DIR)
if _TENGOD_DIR not in sys.path:
    sys.path.insert(0, _TENGOD_DIR)

from .metrics import (
    EvaluationMetrics,
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
)
from .benchmark_dataset import BenchmarkDataset, BenchmarkQuery
from .reporter import EvaluationReporter


# ============================================================================
# 单条评估结果
# ============================================================================

@dataclass
class SingleEvalResult:
    """单条查询评估结果"""
    query_id: str
    query: str
    expected_intent: str
    predicted_intent: str = ""
    intent_confidence: float = 0.0
    intent_correct: bool = False
    retrieved_ids: List[str] = field(default_factory=list)
    relevant_ids: Set[str] = field(default_factory=set)
    hit_at_1: bool = False
    hit_at_3: bool = False
    hit_at_5: bool = False
    reciprocal_rank: float = 0.0
    gate_passed: bool = False
    gate_should_pass: bool = True
    latency_ms: float = 0.0
    generated_text: str = ""
    expected_text: str = ""
    semantic_sim: float = 0.0
    rouge_l_score: float = 0.0
    error: Optional[str] = None


# ============================================================================
# 评估器
# ============================================================================

class GateCognitiveEvaluator:
    """门禁认知系统评估器

    用法：
        from tengod.open_source_bridge import GateCognitiveEngine
        from tengod.eval.evaluator import GateCognitiveEvaluator

        engine = GateCognitiveEngine(embed_dim=384)
        evaluator = GateCognitiveEvaluator(engine)
        metrics = evaluator.evaluate_full()
        print(metrics.to_dict())
    """

    def __init__(
        self,
        engine: Any = None,
        dataset_path: Optional[str] = None,
        embedder: Any = None,
    ):
        self.engine = engine
        self.embedder = embedder

        # 加载数据集
        self.dataset = BenchmarkDataset()
        if dataset_path:
            self.dataset = BenchmarkDataset.load(dataset_path)
        else:
            self.dataset.load_default()

        self.results: List[SingleEvalResult] = []
        self.latencies: List[float] = []

    # ── 评估执行 ──────────────────────────────────────────────────

    def evaluate_full(self, verbose: bool = False) -> EvaluationMetrics:
        """全量评估：运行所有查询并计算综合指标"""
        self.results = []
        self.latencies = []

        total = len(self.dataset.queries)
        for i, query in enumerate(self.dataset.queries):
            result = self._evaluate_single(query)
            self.results.append(result)
            self.latencies.append(result.latency_ms)

            if verbose and (i + 1) % 10 == 0:
                print(f"  [{i+1}/{total}] 已完成...")

        return self._compute_metrics()

    def evaluate_category(self, category: str, verbose: bool = False) -> EvaluationMetrics:
        """按类别评估"""
        queries = self.dataset.get_by_category(category)
        self.results = []
        self.latencies = []

        for i, query in enumerate(queries):
            result = self._evaluate_single(query)
            self.results.append(result)
            self.latencies.append(result.latency_ms)

            if verbose and (i + 1) % 5 == 0:
                print(f"  [{category}] {i+1}/{len(queries)} 已完成...")

        return self._compute_metrics()

    def evaluate_intent(self, intent_name: str, verbose: bool = False) -> EvaluationMetrics:
        """按意图类型评估"""
        queries = self.dataset.get_by_intent(intent_name)
        self.results = []
        self.latencies = []

        for i, query in enumerate(queries):
            result = self._evaluate_single(query)
            self.results.append(result)
            self.latencies.append(result.latency_ms)

            if verbose and (i + 1) % 5 == 0:
                print(f"  [{intent_name}] {i+1}/{len(queries)} 已完成...")

        return self._compute_metrics()

    def evaluate_retrieval_only(self) -> Dict[str, float]:
        """仅评估检索性能（不依赖引擎）"""
        results = []
        for query in self.dataset.queries:
            result = SingleEvalResult(
                query_id=query.id,
                query=query.query,
                expected_intent=query.intent,
                relevant_ids=query.relevant_ids,
            )
            # 模拟检索（使用 embedder）
            if self.embedder:
                q_emb = self.embedder.encode(query.query)
                # 简单 brute-force 评估
                all_embeddings = []
                all_ids = []
                for q2 in self.dataset.queries:
                    if q2.relevant_ids:
                        e = self.embedder.encode(q2.expected_answer)
                        all_embeddings.append(e)
                        all_ids.append(q2.id)
                if all_embeddings:
                    sims = [float(np.dot(q_emb, e) / (np.linalg.norm(q_emb) * np.linalg.norm(e) + 1e-8))
                            for e in all_embeddings]
                    sorted_idx = np.argsort(sims)[::-1]
                    result.retrieved_ids = [all_ids[i] for i in sorted_idx[:10]]
            results.append(result)

        return self._compute_retrieval_metrics(results)

    # ── 单条评估 ──────────────────────────────────────────────────

    def _evaluate_single(self, query: BenchmarkQuery) -> SingleEvalResult:
        result = SingleEvalResult(
            query_id=query.id,
            query=query.query,
            expected_intent=query.intent,
            relevant_ids=query.relevant_ids,
            expected_text=query.expected_answer,
        )

        try:
            t0 = time.time()

            if self.engine:
                response = self.engine.process(
                    query=query.query,
                    context=query.context or "",
                    query_id=query.id,
                )

                # 意图
                result.predicted_intent = response.get("intent", "")
                result.intent_confidence = response.get("intent_confidence", 0.0)
                result.intent_correct = (
                    result.predicted_intent == query.intent or
                    query.intent in result.predicted_intent
                )

                # 检索
                result.retrieved_ids = response.get("retrieved_ids", [])[:10]
                result.hit_at_1 = bool(set(result.retrieved_ids[:1]) & query.relevant_ids)
                result.hit_at_3 = bool(set(result.retrieved_ids[:3]) & query.relevant_ids)
                result.hit_at_5 = bool(set(result.retrieved_ids[:5]) & query.relevant_ids)

                # 门禁
                result.gate_passed = response.get("gate_passed", True)

                # 生成
                result.generated_text = response.get("answer", "") or response.get("result", {}).get("text", "")

            t1 = time.time()
            result.latency_ms = (t1 - t0) * 1000

            # 语义相似度
            if self.embedder and result.generated_text and query.expected_answer:
                emb_gen = self.embedder.encode(result.generated_text)
                emb_exp = self.embedder.encode(query.expected_answer)
                result.semantic_sim = semantic_similarity(emb_gen, emb_exp)

            # ROUGE-L
            if result.generated_text and query.expected_answer:
                result.rouge_l_score = rouge_l(result.generated_text, query.expected_answer)

            # MRR
            if query.relevant_ids:
                for i, rid in enumerate(result.retrieved_ids, 1):
                    if rid in query.relevant_ids:
                        result.reciprocal_rank = 1.0 / i
                        break

        except Exception as e:
            result.error = str(e)

        return result

    # ── 指标计算 ──────────────────────────────────────────────────

    def _compute_metrics(self) -> EvaluationMetrics:
        n = len(self.results)
        if n == 0:
            return EvaluationMetrics()

        # 检索
        all_relevant = []
        all_retrieved = []
        for r in self.results:
            all_relevant.append(r.relevant_ids)
            all_retrieved.append(r.retrieved_ids)

        p1 = np.mean([precision_at_k(rel, ret, 1) for rel, ret in zip(all_relevant, all_retrieved)])
        p3 = np.mean([precision_at_k(rel, ret, 3) for rel, ret in zip(all_relevant, all_retrieved)])
        p5 = np.mean([precision_at_k(rel, ret, 5) for rel, ret in zip(all_relevant, all_retrieved)])
        r5 = np.mean([recall_at_k(rel, ret, 5) for rel, ret in zip(all_relevant, all_retrieved)])
        f5 = np.mean([f1_at_k(rel, ret, 5) for rel, ret in zip(all_relevant, all_retrieved)])
        mrr_val = np.mean([mrr(rel, ret) for rel, ret in zip(all_relevant, all_retrieved)])
        ndcg_val = np.mean([ndcg_at_k(rel, ret, 5) for rel, ret in zip(all_relevant, all_retrieved)])
        hr5 = np.mean([hit_rate_at_k(rel, ret, 5) for rel, ret in zip(all_relevant, all_retrieved)])

        # 门禁
        passed = sum(1 for r in self.results if r.gate_passed)
        tp = sum(1 for r in self.results if r.gate_passed and r.gate_should_pass)
        fp = sum(1 for r in self.results if r.gate_passed and not r.gate_should_pass)
        fn = sum(1 for r in self.results if not r.gate_passed and r.gate_should_pass)

        # 意图
        intents_pred = [r.predicted_intent for r in self.results]
        intents_true = [r.expected_intent for r in self.results]
        intents_conf = [r.intent_confidence for r in self.results]
        ambiguous = sum(1 for r in self.results if r.expected_intent in ("歧义", "多义"))
        disambiguated = sum(1 for r in self.results if r.expected_intent in ("歧义", "多义") and r.intent_correct)

        # 生成
        sem_sims = [r.semantic_sim for r in self.results if r.semantic_sim > 0]
        rouge_ls = [r.rouge_l_score for r in self.results if r.rouge_l_score > 0]

        # 延迟
        lats = sorted(self.latencies)
        p50 = float(np.percentile(lats, 50)) if lats else 0.0
        p95 = float(np.percentile(lats, 95)) if lats else 0.0
        p99 = float(np.percentile(lats, 99)) if lats else 0.0

        # 综合评分（加权平均）
        retrieval_score = np.mean([p1, p3, p5, r5, mrr_val, ndcg_val, hr5])
        gate_score = gate_f1(tp, fp, fn)
        intent_score = intent_accuracy(intents_pred, intents_true)
        gen_score = np.mean(sem_sims) if sem_sims else 0.0
        overall = 0.35 * retrieval_score + 0.30 * gate_score + 0.20 * intent_score + 0.15 * gen_score

        return EvaluationMetrics(
            precision_at_1=float(p1),
            precision_at_3=float(p3),
            precision_at_5=float(p5),
            recall_at_5=float(r5),
            f1_at_5=float(f5),
            mrr=float(mrr_val),
            ndcg_at_5=float(ndcg_val),
            hit_rate_at_5=float(hr5),
            gate_pass_rate=gate_pass_rate(passed, n),
            gate_precision=gate_precision(tp, fp),
            gate_recall=gate_recall(tp, fn),
            gate_f1=gate_f1(tp, fp, fn),
            intent_accuracy=intent_score,
            intent_confidence=intent_confidence(intents_conf),
            disambiguation_rate=disambiguation_rate(disambiguated, ambiguous),
            semantic_similarity=float(np.mean(sem_sims)) if sem_sims else 0.0,
            rouge_l=float(np.mean(rouge_ls)) if rouge_ls else 0.0,
            overall_score=float(overall),
            latency_p50_ms=p50,
            latency_p95_ms=p95,
            latency_p99_ms=p99,
            throughput_qps=1000.0 / p50 if p50 > 0 else 0.0,
            num_queries=n,
            timestamp=time.time(),
        )

    def _compute_retrieval_metrics(self, results: List[SingleEvalResult]) -> Dict[str, float]:
        n = len(results)
        if n == 0:
            return {}

        all_relevant = [r.relevant_ids for r in results]
        all_retrieved = [r.retrieved_ids for r in results]

        return {
            "precision@1": float(np.mean([precision_at_k(rel, ret, 1) for rel, ret in zip(all_relevant, all_retrieved)])),
            "precision@3": float(np.mean([precision_at_k(rel, ret, 3) for rel, ret in zip(all_relevant, all_retrieved)])),
            "precision@5": float(np.mean([precision_at_k(rel, ret, 5) for rel, ret in zip(all_relevant, all_retrieved)])),
            "recall@5": float(np.mean([recall_at_k(rel, ret, 5) for rel, ret in zip(all_relevant, all_retrieved)])),
            "f1@5": float(np.mean([f1_at_k(rel, ret, 5) for rel, ret in zip(all_relevant, all_retrieved)])),
            "mrr": float(np.mean([mrr(rel, ret) for rel, ret in zip(all_relevant, all_retrieved)])),
            "ndcg@5": float(np.mean([ndcg_at_k(rel, ret, 5) for rel, ret in zip(all_relevant, all_retrieved)])),
            "hit_rate@5": float(np.mean([hit_rate_at_k(rel, ret, 5) for rel, ret in zip(all_relevant, all_retrieved)])),
            "num_queries": n,
        }

    # ── 报告生成 ──────────────────────────────────────────────────

    def generate_report(self, output_path: Optional[str] = None) -> str:
        """生成评估报告（Markdown）"""
        metrics = self._compute_metrics()
        reporter = EvaluationReporter(metrics, self.results)
        report = reporter.generate_markdown()

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)

        return report

    def generate_json_report(self, output_path: Optional[str] = None) -> Dict:
        """生成 JSON 格式评估报告"""
        metrics = self._compute_metrics()
        report = {
            "version": "3.9.0",
            "metrics": metrics.to_dict(),
            "per_query": [
                {
                    "query_id": r.query_id,
                    "query": r.query,
                    "expected_intent": r.expected_intent,
                    "predicted_intent": r.predicted_intent,
                    "intent_correct": r.intent_correct,
                    "hit_at_1": r.hit_at_1,
                    "hit_at_3": r.hit_at_3,
                    "hit_at_5": r.hit_at_5,
                    "gate_passed": r.gate_passed,
                    "latency_ms": round(r.latency_ms, 2),
                    "semantic_sim": round(r.semantic_sim, 4),
                    "rouge_l": round(r.rouge_l_score, 4),
                    "error": r.error,
                }
                for r in self.results
            ],
        }

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

        return report

    # ── 快速自检 ──────────────────────────────────────────────────

    def self_check(self) -> bool:
        """快速自检：加载数据集 + 计算基础指标"""
        try:
            self.dataset.load_default()
            assert len(self.dataset.queries) >= 50, f"数据集条目不足: {len(self.dataset.queries)}"

            # 测试指标计算
            rel = {"a", "b", "c"}
            ret = ["a", "d", "b", "e", "f"]
            assert precision_at_k(rel, ret, 3) == 2/3, "precision_at_k 错误"
            assert recall_at_k(rel, ret, 5) == 2/3, "recall_at_k 错误"
            assert mrr(rel, ret) == 1.0, "mrr 错误"
            assert hit_rate_at_k(rel, ret, 3) == 1.0, "hit_rate@k 错误"

            # 测试门禁指标
            assert gate_precision(8, 2) == 0.8, "gate_precision 错误"
            assert gate_recall(8, 2) == 0.8, "gate_recall 错误"

            # 测试意图指标
            assert intent_accuracy(["八字", "紫微", "六爻"], ["八字", "紫微", "风水"]) == 2/3, "intent_accuracy 错误"

            print(f"✅ 评估器自检通过: {len(self.dataset.queries)} 条查询已加载")
            return True

        except Exception as e:
            print(f"❌ 评估器自检失败: {e}")
            return False