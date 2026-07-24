"""
eval/ — 门禁认知系统评估框架 v4.4.0
===========================================
道曰："知人者智，自知者明。"

评估框架：
  - metrics.py     — 评估指标（precision/recall/F1/MRR/NDCG）
  - evaluator.py   — 评估器主类（GateCognitiveEvaluator）
  - benchmark_dataset.py — 基准数据集（110 条命理问答对）
  - reporter.py    — 报告生成器（Markdown + JSON）
  - run_eval.py    — 一键评估脚本（v4.4.0）
"""

from .metrics import EvaluationMetrics
from .evaluator import GateCognitiveEvaluator
from .benchmark_dataset import BenchmarkDataset, BenchmarkQuery
from .reporter import EvaluationReporter
from .run_eval import run_evaluation

__all__ = [
    "EvaluationMetrics",
    "GateCognitiveEvaluator",
    "BenchmarkDataset",
    "BenchmarkQuery",
    "EvaluationReporter",
    "run_evaluation",
]