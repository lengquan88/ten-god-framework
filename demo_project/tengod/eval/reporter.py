"""
eval/reporter.py — 评估报告生成器 v4.6.0
=============================================
道曰："言有宗，事有君。"

生成格式化的评估报告：
  - Markdown 格式（可读性高）
  - JSON 格式（机器可解析）
  - 支持按类别/意图分组
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from .metrics import EvaluationMetrics


class EvaluationReporter:
    """评估报告生成器"""

    def __init__(self, metrics: EvaluationMetrics, results: List[Any] = None):
        self.metrics = metrics
        self.results = results or []

    # ── Markdown 报告 ─────────────────────────────────────────────

    def generate_markdown(self) -> str:
        m = self.metrics.to_dict()

        lines = [
            "# 门禁认知系统评估报告 v3.9.0",
            "",
            f"**评估时间**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.metrics.timestamp))}",
            f"**查询数量**: {self.metrics.num_queries}",
            f"**综合评分**: **{m['overall']['score']:.4f}**",
            "",
            "---",
            "",
            "## 1. 检索指标",
            "",
            "| 指标 | 值 | 目标 | 状态 |",
            "|------|-----|------|------|",
        ]

        retrieval_targets = {
            "precision@1": (0.60, "P@1 ≥ 0.60"),
            "precision@3": (0.50, "P@3 ≥ 0.50"),
            "precision@5": (0.40, "P@5 ≥ 0.40"),
            "recall@5": (0.70, "R@5 ≥ 0.70"),
            "f1@5": (0.50, "F1@5 ≥ 0.50"),
            "mrr": (0.50, "MRR ≥ 0.50"),
            "ndcg@5": (0.50, "NDCG@5 ≥ 0.50"),
            "hit_rate@5": (0.80, "HR@5 ≥ 0.80"),
        }

        for key, val in m["retrieval"].items():
            target, desc = retrieval_targets.get(key, (0.0, "-"))
            status = "✅" if val >= target else "⚠️"
            lines.append(f"| {key} | {val:.4f} | {desc} | {status} |")

        lines.extend([
            "",
            "## 2. 门禁指标",
            "",
            "| 指标 | 值 | 目标 | 状态 |",
            "|------|-----|------|------|",
        ])

        gate_targets = {
            "pass_rate": (0.70, "通过率 ≥ 0.70"),
            "precision": (0.80, "精确率 ≥ 0.80"),
            "recall": (0.80, "召回率 ≥ 0.80"),
            "f1": (0.80, "F1 ≥ 0.80"),
        }

        for key, val in m["gate"].items():
            target, desc = gate_targets.get(key, (0.0, "-"))
            status = "✅" if val >= target else "⚠️"
            lines.append(f"| {key} | {val:.4f} | {desc} | {status} |")

        lines.extend([
            "",
            "## 3. 意图识别",
            "",
            "| 指标 | 值 | 目标 | 状态 |",
            "|------|-----|------|------|",
        ])

        intent_targets = {
            "accuracy": (0.70, "准确率 ≥ 0.70"),
            "confidence": (0.60, "置信度 ≥ 0.60"),
            "disambiguation_rate": (0.60, "消解率 ≥ 0.60"),
        }

        for key, val in m["intent"].items():
            target, desc = intent_targets.get(key, (0.0, "-"))
            status = "✅" if val >= target else "⚠️"
            lines.append(f"| {key} | {val:.4f} | {desc} | {status} |")

        lines.extend([
            "",
            "## 4. 生成质量",
            "",
            "| 指标 | 值 | 目标 | 状态 |",
            "|------|-----|------|------|",
        ])

        gen_targets = {
            "semantic_similarity": (0.60, "语义相似度 ≥ 0.60"),
            "rouge_l": (0.30, "ROUGE-L ≥ 0.30"),
        }

        for key, val in m["generation"].items():
            target, desc = gen_targets.get(key, (0.0, "-"))
            status = "✅" if val >= target else "⚠️"
            lines.append(f"| {key} | {val:.4f} | {desc} | {status} |")

        lines.extend([
            "",
            "## 5. 性能",
            "",
            "| 指标 | 值 |",
            "|------|-----|",
            f"| P50 延迟 | {m['overall']['latency_p50_ms']:.2f} ms |",
            f"| P95 延迟 | {m['overall']['latency_p95_ms']:.2f} ms |",
            f"| P99 延迟 | {m['overall']['latency_p99_ms']:.2f} ms |",
            f"| 吞吐量 | {m['overall']['throughput_qps']:.2f} QPS |",
            "",
            "## 6. 错误详情",
            "",
        ])

        errors = [r for r in self.results if getattr(r, 'error', None)]
        if errors:
            for r in errors[:10]:
                lines.append(f"- **[{r.query_id}]** {r.query}: `{r.error}`")
            if len(errors) > 10:
                lines.append(f"- ... 及其他 {len(errors) - 10} 个错误")
        else:
            lines.append("无错误。")

        lines.extend([
            "",
            "---",
            "",
            f"*报告由 GateCognitiveEvaluator v3.9.0 自动生成*",
        ])

        return "\n".join(lines)

    # ── JSON 分组报告 ─────────────────────────────────────────────

    def generate_by_category(self) -> Dict[str, Any]:
        """按类别分组统计"""
        if not self.results:
            return {}

        categories: Dict[str, List] = {}
        for r in self.results:
            cat = getattr(r, 'expected_intent', 'unknown')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r)

        report = {}
        for cat, results in categories.items():
            n = len(results)
            correct = sum(1 for r in results if getattr(r, 'intent_correct', False))
            hit5 = sum(1 for r in results if getattr(r, 'hit_at_5', False))
            report[cat] = {
                "count": n,
                "intent_accuracy": correct / n if n > 0 else 0,
                "hit_rate@5": hit5 / n if n > 0 else 0,
            }

        return report

    # ── 对比报告 ──────────────────────────────────────────────────

    def generate_comparison(self, baseline: EvaluationMetrics) -> str:
        """生成与基线对比报告"""
        m = self.metrics.to_dict()
        b = baseline.to_dict()

        lines = [
            "# 门禁认知系统 对比评估报告",
            "",
            f"## 当前版本 vs 基线",
            "",
            "| 指标 | 当前 | 基线 | 变化 |",
            "|------|------|------|------|",
        ]

        for section in ["retrieval", "gate", "intent", "generation"]:
            for key in m.get(section, {}):
                cur = m[section][key]
                prev = b[section].get(key, 0.0)
                delta = cur - prev
                arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
                lines.append(f"| {section}/{key} | {cur:.4f} | {prev:.4f} | {arrow} {delta:+.4f} |")

        lines.extend([
            "",
            "### 综合评分",
            "",
            f"- 当前: **{m['overall']['score']:.4f}**",
            f"- 基线: **{b['overall']['score']:.4f}**",
            f"- 变化: **{m['overall']['score'] - b['overall']['score']:+.4f}**",
        ])

        return "\n".join(lines)