"""
eval/run_eval.py — 一键评估脚本 v4.4.0
===========================================
道曰："知不知，尚矣；不知知，病也。"

首次运行门禁认知系统全量评估，生成 Markdown + JSON 报告。

用法：
    # 命令行
    python -m tengod.eval.run_eval

    # 代码调用
    from tengod.eval.run_eval import run_evaluation
    report = run_evaluation(output_dir="/data/eval")

输出：
    - eval_report.json   — 完整评估数据（指标 + 逐条结果）
    - eval_report.md     — 可读评估报告
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Dict, Optional

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_TENGOD_DIR = os.path.dirname(_THIS_DIR)
if _TENGOD_DIR not in sys.path:
    sys.path.insert(0, _TENGOD_DIR)


def run_evaluation(
    embed_dim: int = 384,
    output_dir: Optional[str] = None,
    verbose: bool = True,
    quick: bool = False,
) -> Dict:
    """运行全量评估

    Args:
        embed_dim: 嵌入维度（默认 384，匹配 all-MiniLM-L6-v2）
        output_dir: 报告输出目录（默认当前目录）
        verbose: 是否打印详细进度
        quick: 快速模式（仅跑 20 条）

    Returns:
        评估结果字典
    """
    from .benchmark_dataset import BenchmarkDataset
    from .evaluator import GateCognitiveEvaluator
    from ..open_source_bridge import GateCognitiveEngine
    from ..local_embedding import create_embedder

    if output_dir is None:
        output_dir = os.getcwd()

    os.makedirs(output_dir, exist_ok=True)

    # ── 加载数据集 ─────────────────────────────────────────────
    ds = BenchmarkDataset().load_default()
    if quick:
        ds.queries = ds.queries[:20]

    if verbose:
        print("=" * 60)
        print("  门禁认知系统评估 v4.4.0")
        print("=" * 60)
        print(f"\n  数据集: {ds.count} 条查询")
        print(f"  类别: {ds.categories}")
        print(f"  意图: {ds.intents}")

    # ── 初始化引擎 ─────────────────────────────────────────────
    if verbose:
        print("\n  初始化门禁认知引擎...")

    embedder = create_embedder(dim=embed_dim)
    engine = GateCognitiveEngine(embed_dim=embed_dim)

    if verbose:
        print(f"  Embedder: {embedder.mode} (dim={embedder.get_dim()})")
        print(f"  GateFilter: {engine.gate_filter}")
        print(f"  KG Bridge: {type(engine.kg_bridge).__name__}")

    # ── 运行评估 ───────────────────────────────────────────────
    if verbose:
        print(f"\n  运行评估（{ds.count} 条）...")

    t0 = time.time()
    evaluator = GateCognitiveEvaluator(engine=engine, embedder=embedder)
    evaluator.dataset = ds
    metrics = evaluator.evaluate_full(verbose=verbose)
    t1 = time.time()

    if verbose:
        print(f"\n  评估完成，耗时 {t1 - t0:.1f}s")

    # ── 生成报告 ───────────────────────────────────────────────
    md_path = os.path.join(output_dir, "eval_report.md")
    json_path = os.path.join(output_dir, "eval_report.json")

    md_report = evaluator.generate_report(md_path)
    json_report = evaluator.generate_json_report(json_path)

    if verbose:
        print(f"\n  报告已生成:")
        print(f"    Markdown: {md_path}")
        print(f"    JSON:     {json_path}")
        print(f"\n  ── 综合评分 ──")
        m = metrics.to_dict()
        print(f"    综合: {m['overall']['score']:.4f}")
        print(f"    检索: P@1={m['retrieval']['precision@1']:.4f} MRR={m['retrieval']['mrr']:.4f}")
        print(f"    门禁: F1={m['gate']['f1']:.4f}")
        print(f"    意图: Acc={m['intent']['accuracy']:.4f}")
        print(f"    生成: SemSim={m['generation']['semantic_similarity']:.4f}")
        print(f"    性能: P50={m['overall']['latency_p50_ms']:.1f}ms")
        print(f"\n  ✅ 评估完成")

    return {
        "metrics": metrics.to_dict(),
        "per_query": json_report.get("per_query", []),
        "duration_s": round(t1 - t0, 1),
        "num_queries": ds.count,
        "md_path": md_path,
        "json_path": json_path,
    }


# ============================================================================
# 命令行入口
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="门禁认知系统评估")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="报告输出目录")
    parser.add_argument("--quick", "-q", action="store_true",
                        help="快速模式（仅 20 条）")
    parser.add_argument("--quiet", action="store_true",
                        help="静默模式")
    parser.add_argument("--dim", type=int, default=384,
                        help="嵌入维度")
    args = parser.parse_args()

    run_evaluation(
        embed_dim=args.dim,
        output_dir=args.output,
        verbose=not args.quiet,
        quick=args.quick,
    )