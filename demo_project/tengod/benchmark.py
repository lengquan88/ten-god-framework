"""
benchmark.py — 性能基准测试 v4.1.0
========================================
道曰："天下难事，必作于易；天下大事，必作于细。"

性能基准测试框架：
  - 推测解码加速比回归
  - 十二神门禁裁决吞吐量
  - 七阶段成像管道延迟
  - 自修正收敛速度
  - 负载均衡压测
  - 认知单元创建/查询QPS
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import math
import time
import statistics
import uuid


# ============================================================================
# 基准测试结果
# ============================================================================

@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    description: str
    iterations: int
    total_duration_ms: float
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    std_ms: float
    throughput_per_sec: float
    success_count: int
    failure_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "iterations": self.iterations,
            "total_duration_ms": round(self.total_duration_ms, 1),
            "min_ms": round(self.min_ms, 3),
            "max_ms": round(self.max_ms, 3),
            "mean_ms": round(self.mean_ms, 3),
            "median_ms": round(self.median_ms, 3),
            "p95_ms": round(self.p95_ms, 3),
            "p99_ms": round(self.p99_ms, 3),
            "std_ms": round(self.std_ms, 3),
            "throughput_per_sec": round(self.throughput_per_sec, 1),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "metadata": self.metadata,
        }


@dataclass
class BenchmarkSuite:
    """基准测试套件"""
    suite_name: str
    results: List[BenchmarkResult] = field(default_factory=list)
    total_duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "suite_name": self.suite_name,
            "results": [r.to_dict() for r in self.results],
            "total_duration_ms": round(self.total_duration_ms, 1),
            "timestamp": self.timestamp,
        }


# ============================================================================
# 基准测试运行器
# ============================================================================

class BenchmarkRunner:
    """基准测试运行器 v2.36.0

    支持：
    - 单次基准测试
    - 多次迭代统计
    - 推测解码加速比回归
    - 负载均衡压测
    - 回归检测（与历史基线对比）
    """

    VERSION = "2.36.0"

    def __init__(self):
        self._baselines: Dict[str, BenchmarkResult] = {}
        self._suites: List[BenchmarkSuite] = []

    # ── 基准测试执行 ──────────────────────────────────────────────────

    def run(
        self,
        name: str,
        description: str,
        func: Callable[[], Any],
        iterations: int = 100,
        warmup: int = 5,
        metadata: Optional[Dict] = None,
    ) -> BenchmarkResult:
        """执行基准测试

        Args:
            name: 测试名称
            description: 测试描述
            func: 被测函数
            iterations: 迭代次数
            warmup: 预热次数
            metadata: 附加元数据

        Returns:
            BenchmarkResult
        """
        # 预热
        for _ in range(warmup):
            try:
                func()
            except Exception:
                pass

        # 正式测试
        durations = []
        success_count = 0
        failure_count = 0

        start = time.time()
        for _ in range(iterations):
            t0 = time.perf_counter()
            try:
                func()
                success_count += 1
            except Exception:
                failure_count += 1
            t1 = time.perf_counter()
            durations.append((t1 - t0) * 1000)

        total_duration = (time.time() - start) * 1000

        sorted_durations = sorted(durations)
        n = len(sorted_durations)

        result = BenchmarkResult(
            name=name,
            description=description,
            iterations=iterations,
            total_duration_ms=total_duration,
            min_ms=min(durations),
            max_ms=max(durations),
            mean_ms=statistics.mean(durations),
            median_ms=statistics.median(durations),
            p95_ms=sorted_durations[int(n * 0.95)] if n > 0 else 0,
            p99_ms=sorted_durations[int(n * 0.99)] if n > 0 else 0,
            std_ms=statistics.stdev(durations) if n > 1 else 0,
            throughput_per_sec=iterations / (total_duration / 1000) if total_duration > 0 else 0,
            success_count=success_count,
            failure_count=failure_count,
            metadata=metadata or {},
        )

        return result

    # ── 推测解码基准 ──────────────────────────────────────────────────

    def benchmark_speculation(
        self,
        speculation_func: Callable[[], bool],
        iterations: int = 200,
    ) -> BenchmarkResult:
        """推测解码加速比基准测试

        Args:
            speculation_func: 推测函数，返回是否命中
            iterations: 迭代次数

        Returns:
            BenchmarkResult
        """
        hits = 0
        durations = []
        success = 0
        failures = 0

        start = time.time()
        for _ in range(iterations):
            t0 = time.perf_counter()
            try:
                hit = speculation_func()
                if hit:
                    hits += 1
                success += 1
            except Exception:
                failures += 1
            t1 = time.perf_counter()
            durations.append((t1 - t0) * 1000)

        total_duration = (time.time() - start) * 1000
        hit_rate = hits / max(1, iterations)
        speedup = 1.0 / (1.0 - hit_rate) if hit_rate < 1.0 and hit_rate > 0 else 1.0

        sorted_durations = sorted(durations)
        n = len(sorted_durations)

        return BenchmarkResult(
            name="speculation_decoding",
            description="推测解码加速比基准",
            iterations=iterations,
            total_duration_ms=total_duration,
            min_ms=min(durations) if durations else 0,
            max_ms=max(durations) if durations else 0,
            mean_ms=statistics.mean(durations) if durations else 0,
            median_ms=statistics.median(durations) if durations else 0,
            p95_ms=sorted_durations[int(n * 0.95)] if n > 0 else 0,
            p99_ms=sorted_durations[int(n * 0.99)] if n > 0 else 0,
            std_ms=statistics.stdev(durations) if n > 1 else 0,
            throughput_per_sec=iterations / (total_duration / 1000) if total_duration > 0 else 0,
            success_count=success,
            failure_count=failures,
            metadata={
                "hit_rate": round(hit_rate, 4),
                "speedup_estimate": round(speedup, 2),
                "hits": hits,
            },
        )

    # ── 负载均衡压测 ──────────────────────────────────────────────────

    def benchmark_load(
        self,
        name: str,
        func: Callable[[], Any],
        concurrent: int = 5,
        iterations_per_worker: int = 50,
    ) -> BenchmarkResult:
        """负载均衡压测

        Args:
            name: 测试名称
            func: 被测函数
            concurrent: 并发数
            iterations_per_worker: 每个worker的迭代次数

        Returns:
            BenchmarkResult
        """
        import threading
        import queue

        results_queue: queue.Queue = queue.Queue()
        errors = []
        lock = threading.Lock()

        def worker(worker_id: int):
            for i in range(iterations_per_worker):
                t0 = time.perf_counter()
                try:
                    func()
                    success = True
                except Exception as e:
                    with lock:
                        errors.append(str(e))
                    success = False
                t1 = time.perf_counter()
                results_queue.put((t1 - t0) * 1000)

        start = time.time()
        threads = []
        for c in range(concurrent):
            t = threading.Thread(target=worker, args=(c,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        total_duration = (time.time() - start) * 1000
        durations = []
        while not results_queue.empty():
            durations.append(results_queue.get())

        total_iterations = concurrent * iterations_per_worker
        sorted_durations = sorted(durations)
        n = len(sorted_durations)

        return BenchmarkResult(
            name=f"{name}_load_{concurrent}w",
            description=f"负载均衡压测 ({concurrent}并发)",
            iterations=total_iterations,
            total_duration_ms=total_duration,
            min_ms=min(durations) if durations else 0,
            max_ms=max(durations) if durations else 0,
            mean_ms=statistics.mean(durations) if durations else 0,
            median_ms=statistics.median(durations) if durations else 0,
            p95_ms=sorted_durations[int(n * 0.95)] if n > 0 else 0,
            p99_ms=sorted_durations[int(n * 0.99)] if n > 0 else 0,
            std_ms=statistics.stdev(durations) if n > 1 else 0,
            throughput_per_sec=total_iterations / (total_duration / 1000) if total_duration > 0 else 0,
            success_count=total_iterations - len(errors),
            failure_count=len(errors),
            metadata={
                "concurrent_workers": concurrent,
                "iterations_per_worker": iterations_per_worker,
                "errors": errors[:10],
            },
        )

    # ── 十二神门禁基准 ──────────────────────────────────────────────

    def benchmark_twelve_gates(
        self,
        iterations: int = 100,
    ) -> BenchmarkResult:
        """十二神门禁裁决吞吐量基准"""
        try:
            from .holographic_system import get_holographic_system
            system = get_holographic_system()

            def gate_judge():
                system.execute(
                    unit_id=f"bench_{uuid.uuid4().hex[:8]}",
                    unit_name="基准测试单元",
                    coords={"S": 0.8, "T": 0.5, "P": 0.7, "C": 0.6, "I": 0.7, "E": 0.3},
                    enable_imaging=False,
                    enable_self_correction=False,
                    enable_oracle=False,
                )

            return self.run(
                name="twelve_gates_judge",
                description="十二神门禁裁决吞吐量",
                func=gate_judge,
                iterations=iterations,
                metadata={"gates": 12},
            )
        except Exception as e:
            return BenchmarkResult(
                name="twelve_gates_judge",
                description="十二神门禁裁决吞吐量",
                iterations=0,
                total_duration_ms=0, min_ms=0, max_ms=0,
                mean_ms=0, median_ms=0, p95_ms=0, p99_ms=0, std_ms=0,
                throughput_per_sec=0,
                success_count=0, failure_count=1,
                metadata={"error": str(e)},
            )

    def benchmark_tbce_creation(
        self,
        iterations: int = 1000,
    ) -> BenchmarkResult:
        """TBCE认知单元创建QPS"""
        from .tbce_unit import TBCECoordinates, CognitiveUnit

        def create_unit():
            CognitiveUnit(
                unit_id=f"bench_{uuid.uuid4().hex[:8]}",
                name="基准单元",
                module_path="bench.test",
                coordinates=TBCECoordinates(0.5, 0.5, 0.5, 0.5, 0.5, 0.5),
                psi_operator="ZuowangAttention",
                cognitive_layer=1,
            )

        return self.run(
            name="tbce_unit_creation",
            description="TBCE认知单元创建QPS",
            func=create_unit,
            iterations=iterations,
        )

    def benchmark_tbce_query(
        self,
        iterations: int = 1000,
    ) -> BenchmarkResult:
        """TBCE坐标查询QPS"""
        from .tbce_unit import TBCECoordinates

        coords = TBCECoordinates(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)

        def query():
            coords.distance(TBCECoordinates(0.3, 0.4, 0.6, 0.7, 0.8, 0.9))
            coords.to_dict()

        return self.run(
            name="tbce_query",
            description="TBCE坐标查询QPS",
            func=query,
            iterations=iterations,
        )

    def benchmark_element_cycle(
        self,
        iterations: int = 1000,
    ) -> BenchmarkResult:
        """五行生克计算基准"""
        from .twelve_gods_base import FiveElements

        elements = list(FiveElements)

        def cycle():
            for e in elements:
                _ = e.generates
                _ = e.overcomes

        return self.run(
            name="element_cycle",
            description="五行生克计算QPS",
            func=cycle,
            iterations=iterations,
        )

    # ── 回归检测 ──────────────────────────────────────────────────────

    def set_baseline(self, name: str, result: BenchmarkResult) -> None:
        """设置基准线"""
        self._baselines[name] = result

    def check_regression(
        self, name: str, result: BenchmarkResult, max_degradation: float = 0.2
    ) -> Dict[str, Any]:
        """检查回归

        Args:
            name: 基准测试名称
            result: 当前结果
            max_degradation: 最大允许的退化比例 (0.2 = 20%)

        Returns:
            {"regression": bool, "degradation": float, "baseline": ..., "current": ...}
        """
        baseline = self._baselines.get(name)
        if baseline is None:
            return {
                "regression": False,
                "message": "无历史基线",
                "current": result.to_dict(),
            }

        # 比较平均延迟
        if baseline.mean_ms > 0:
            degradation = (result.mean_ms - baseline.mean_ms) / baseline.mean_ms
        else:
            degradation = 0

        return {
            "regression": degradation > max_degradation,
            "degradation": round(degradation, 4),
            "baseline": {"mean_ms": round(baseline.mean_ms, 3)},
            "current": {"mean_ms": round(result.mean_ms, 3)},
            "threshold": max_degradation,
        }

    # ── 完整套件 ──────────────────────────────────────────────────────

    def run_full_suite(
        self,
        name: str = "tengod_benchmark_suite",
        include_load_test: bool = False,
    ) -> BenchmarkSuite:
        """运行完整基准测试套件"""
        suite = BenchmarkSuite(suite_name=name)
        start = time.time()

        # 1. TBCE创建
        suite.results.append(self.benchmark_tbce_creation(iterations=500))

        # 2. TBCE查询
        suite.results.append(self.benchmark_tbce_query(iterations=500))

        # 3. 五行生克
        suite.results.append(self.benchmark_element_cycle(iterations=500))

        # 4. 推测解码
        total = 200
        hits = 0
        import random
        def speculation():
            nonlocal hits
            hit = random.random() > 0.3  # 70%命中率
            if hit:
                hits += 1
            return hit

        suite.results.append(self.benchmark_speculation(speculation, iterations=total))

        # 5. 十二神门禁
        suite.results.append(self.benchmark_twelve_gates(iterations=30))

        # 6. 门禁认知引擎（v4.5.0）
        suite.results.append(self.benchmark_cognitive_engine(iterations=20))

        # 7. 负载测试
        if include_load_test:
            def light_task():
                sum(i * i for i in range(100))

            suite.results.append(self.benchmark_load(
                "light_compute", light_task, concurrent=5, iterations_per_worker=20,
            ))

        suite.total_duration_ms = (time.time() - start) * 1000
        self._suites.append(suite)
        return suite

    # ── 门禁认知引擎基准（v4.5.0）─────────────────────────────────────

    def benchmark_cognitive_engine(
        self,
        iterations: int = 20,
        embed_dim: int = 384,
    ) -> BenchmarkResult:
        """门禁认知引擎端到端延迟基准"""

        from .open_source_bridge import GateCognitiveEngine

        engine = GateCognitiveEngine(embed_dim=embed_dim)

        queries = [
            "什么是天干五合？",
            "我的八字喜用神是什么？",
            "紫微星坐命宫代表什么？",
            "六爻中如何看财运？",
            "这个房子风水好不好？",
            "正官格的人有什么特点？",
            "地支三合局有哪些？",
            "今年运势如何？",
        ]

        def run_cognitive():
            q = queries[hash(str(iterations)) % len(queries)]
            engine.process(query=q)

        return self.run(
            name="cognitive_engine_e2e",
            description="门禁认知引擎端到端处理延迟",
            func=run_cognitive,
            iterations=iterations,
        )

    # ── 回归报告 ──────────────────────────────────────────────────────

    def get_regression_report(self) -> Dict[str, Any]:
        """获取回归检测报告"""
        report = {}
        for name, baseline in self._baselines.items():
            report[name] = {
                "baseline_mean_ms": round(baseline.mean_ms, 3),
                "baseline_p95_ms": round(baseline.p95_ms, 3),
                "baseline_throughput": round(baseline.throughput_per_sec, 1),
            }
        return report


# ============================================================================
# 全局单例
# ============================================================================

_benchmark_runner: Optional[BenchmarkRunner] = None


def get_benchmark_runner() -> BenchmarkRunner:
    global _benchmark_runner
    if _benchmark_runner is None:
        _benchmark_runner = BenchmarkRunner()
    return _benchmark_runner


def reset_benchmark_runner() -> None:
    global _benchmark_runner
    _benchmark_runner = None


__all__ = [
    "BenchmarkResult",
    "BenchmarkSuite",
    "BenchmarkRunner",
    "get_benchmark_runner",
    "reset_benchmark_runner",
]