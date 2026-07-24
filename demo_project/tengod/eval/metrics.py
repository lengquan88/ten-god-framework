"""
eval/metrics.py — 评估指标 v4.6.0
==========================================
道曰："为之于未有，治之于未乱。"

门禁认知系统评估指标体系：
  - 检索指标：Precision@K, Recall@K, F1@K, MRR, NDCG@K, HitRate@K
  - 门禁指标：GatePassRate, GatePrecision, GateRecall, FalsePositiveRate
  - 意图指标：IntentAccuracy, IntentConfidence, DisambiguationRate
  - 生成指标：BLEU, ROUGE-L, SemanticSimilarity, Faithfulness
  - 综合指标：OverallScore, LatencyP50/P95/P99, Throughput
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np


# ============================================================================
# 检索指标
# ============================================================================

def precision_at_k(relevant: Set[str], retrieved: List[str], k: int) -> float:
    """Precision@K：检索结果中相关的比例"""
    if k <= 0 or not retrieved:
        return 0.0
    top_k = set(retrieved[:k])
    return len(top_k & relevant) / k


def recall_at_k(relevant: Set[str], retrieved: List[str], k: int) -> float:
    """Recall@K：相关结果中被检索到的比例"""
    if not relevant:
        return 1.0
    if k <= 0 or not retrieved:
        return 0.0
    top_k = set(retrieved[:k])
    return len(top_k & relevant) / len(relevant)


def f1_at_k(relevant: Set[str], retrieved: List[str], k: int) -> float:
    """F1@K：Precision 和 Recall 的调和平均"""
    p = precision_at_k(relevant, retrieved, k)
    r = recall_at_k(relevant, retrieved, k)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


def mrr(relevant: Set[str], retrieved: List[str]) -> float:
    """MRR (Mean Reciprocal Rank)：第一个相关结果的倒数排名"""
    if not relevant:
        return 0.0
    for i, item in enumerate(retrieved, 1):
        if item in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(relevant: Set[str], retrieved: List[str], k: int,
              relevance_scores: Optional[Dict[str, float]] = None) -> float:
    """NDCG@K (Normalized Discounted Cumulative Gain)"""
    if k <= 0 or not retrieved:
        return 0.0

    # 默认二值相关性：相关=1，不相关=0
    if relevance_scores is None:
        relevance_scores = {item: 1.0 for item in relevant}

    # DCG
    dcg = 0.0
    for i, item in enumerate(retrieved[:k], 1):
        rel = relevance_scores.get(item, 0.0)
        dcg += (2 ** rel - 1) / math.log2(i + 1)

    # IDCG (理想排序)
    ideal_scores = sorted(relevance_scores.values(), reverse=True)[:k]
    idcg = 0.0
    for i, rel in enumerate(ideal_scores, 1):
        idcg += (2 ** rel - 1) / math.log2(i + 1)

    if idcg == 0:
        return 0.0
    return dcg / idcg


def hit_rate_at_k(relevant: Set[str], retrieved: List[str], k: int) -> float:
    """HitRate@K：至少有一个相关结果的比例"""
    if k <= 0 or not retrieved:
        return 0.0
    top_k = set(retrieved[:k])
    return 1.0 if top_k & relevant else 0.0


# ============================================================================
# 门禁指标
# ============================================================================

def gate_pass_rate(passed: int, total: int) -> float:
    """门禁通过率"""
    if total <= 0:
        return 0.0
    return passed / total


def gate_precision(tp: int, fp: int) -> float:
    """门禁精确率：通过门禁的结果中真正应通过的"""
    if tp + fp <= 0:
        return 0.0
    return tp / (tp + fp)


def gate_recall(tp: int, fn: int) -> float:
    """门禁召回率：真正应通过的结果中被门禁放行的"""
    if tp + fn <= 0:
        return 0.0
    return tp / (tp + fn)


def gate_f1(tp: int, fp: int, fn: int) -> float:
    """门禁 F1"""
    p = gate_precision(tp, fp)
    r = gate_recall(tp, fn)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


# ============================================================================
# 意图指标
# ============================================================================

def intent_accuracy(predictions: List[str], labels: List[str]) -> float:
    """意图识别准确率"""
    if not predictions:
        return 0.0
    correct = sum(1 for p, l in zip(predictions, labels) if p == l)
    return correct / len(predictions)


def intent_confidence(confidences: List[float]) -> float:
    """意图识别平均置信度"""
    if not confidences:
        return 0.0
    return float(np.mean(confidences))


def disambiguation_rate(disambiguated: int, total_ambiguous: int) -> float:
    """歧义消解成功率"""
    if total_ambiguous <= 0:
        return 1.0
    return disambiguated / total_ambiguous


# ============================================================================
# 生成指标
# ============================================================================

def semantic_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """语义相似度（余弦相似度）"""
    norm1 = np.linalg.norm(emb1)
    norm2 = np.linalg.norm(emb2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(emb1, emb2) / (norm1 * norm2))


def rouge_l(prediction: str, reference: str) -> float:
    """ROUGE-L：最长公共子序列 F1"""
    if not prediction or not reference:
        return 0.0

    def _lcs(s1: str, s2: str) -> int:
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        return dp[m][n]

    lcs_len = _lcs(prediction, reference)
    p = lcs_len / len(prediction) if prediction else 0
    r = lcs_len / len(reference) if reference else 0
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


# ============================================================================
# 综合指标
# ============================================================================

@dataclass
class EvaluationMetrics:
    """评估指标汇总"""
    # 检索
    precision_at_1: float = 0.0
    precision_at_3: float = 0.0
    precision_at_5: float = 0.0
    recall_at_5: float = 0.0
    f1_at_5: float = 0.0
    mrr: float = 0.0
    ndcg_at_5: float = 0.0
    hit_rate_at_5: float = 0.0

    # 门禁
    gate_pass_rate: float = 0.0
    gate_precision: float = 0.0
    gate_recall: float = 0.0
    gate_f1: float = 0.0

    # 意图
    intent_accuracy: float = 0.0
    intent_confidence: float = 0.0
    disambiguation_rate: float = 0.0

    # 生成
    semantic_similarity: float = 0.0
    rouge_l: float = 0.0

    # 综合
    overall_score: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    throughput_qps: float = 0.0

    # 元数据
    num_queries: int = 0
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "retrieval": {
                "precision@1": round(self.precision_at_1, 4),
                "precision@3": round(self.precision_at_3, 4),
                "precision@5": round(self.precision_at_5, 4),
                "recall@5": round(self.recall_at_5, 4),
                "f1@5": round(self.f1_at_5, 4),
                "mrr": round(self.mrr, 4),
                "ndcg@5": round(self.ndcg_at_5, 4),
                "hit_rate@5": round(self.hit_rate_at_5, 4),
            },
            "gate": {
                "pass_rate": round(self.gate_pass_rate, 4),
                "precision": round(self.gate_precision, 4),
                "recall": round(self.gate_recall, 4),
                "f1": round(self.gate_f1, 4),
            },
            "intent": {
                "accuracy": round(self.intent_accuracy, 4),
                "confidence": round(self.intent_confidence, 4),
                "disambiguation_rate": round(self.disambiguation_rate, 4),
            },
            "generation": {
                "semantic_similarity": round(self.semantic_similarity, 4),
                "rouge_l": round(self.rouge_l, 4),
            },
            "overall": {
                "score": round(self.overall_score, 4),
                "latency_p50_ms": round(self.latency_p50_ms, 2),
                "latency_p95_ms": round(self.latency_p95_ms, 2),
                "latency_p99_ms": round(self.latency_p99_ms, 2),
                "throughput_qps": round(self.throughput_qps, 2),
            },
            "meta": {
                "num_queries": self.num_queries,
                "timestamp": self.timestamp,
            },
        }