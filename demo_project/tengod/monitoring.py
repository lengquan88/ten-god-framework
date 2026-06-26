#!/usr/bin/env python3
"""
monitoring.py — 十神项目可观测性 v2.17.0
========================================
性能监控与可观测性模块，提供 Prometheus 风格指标收集。

特性：
- 请求延迟统计（p50/p95/p99）
- 错误计数
- 管道阶段耗时追踪
- 缓存命中率暴露
- Φ 熵值监控
- 内存使用估算

用法：
    from tengod.monitoring import MetricsCollector

    metrics = MetricsCollector()
    with metrics.track("graph_search"):
        result = do_search()
    print(metrics.summary())
"""
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class LatencyStats:
    """延迟统计"""
    count: int = 0
    total: float = 0.0
    min: float = float("inf")
    max: float = 0.0
    values: List[float] = field(default_factory=list)

    def record(self, duration: float):
        self.count += 1
        self.total += duration
        self.min = min(self.min, duration)
        self.max = max(self.max, duration)
        self.values.append(duration)
        # 保留最近 1000 个值用于百分位计算
        if len(self.values) > 1000:
            self.values = self.values[-1000:]

    @property
    def avg(self) -> float:
        return self.total / self.count if self.count > 0 else 0.0

    def percentile(self, p: float) -> float:
        """计算第 p 百分位延迟"""
        if not self.values:
            return 0.0
        sorted_vals = sorted(self.values)
        idx = int(len(sorted_vals) * p / 100)
        idx = min(idx, len(sorted_vals) - 1)
        return sorted_vals[idx]

    def summary(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "avg_ms": round(self.avg * 1000, 2),
            "p50_ms": round(self.percentile(50) * 1000, 2),
            "p95_ms": round(self.percentile(95) * 1000, 2),
            "p99_ms": round(self.percentile(99) * 1000, 2),
            "min_ms": round(self.min * 1000, 2) if self.min != float("inf") else 0,
            "max_ms": round(self.max * 1000, 2),
        }


class MetricsCollector:
    """指标收集器

    收集和暴露应用级性能指标，支持 Prometheus 文本格式导出。
    """

    def __init__(self, name: str = "tengod"):
        self._name = name
        self._lock = threading.Lock()

        # 计数器
        self._counters: Dict[str, int] = defaultdict(int)
        self._errors: Dict[str, int] = defaultdict(int)

        # 延迟
        self._latencies: Dict[str, LatencyStats] = defaultdict(LatencyStats)

        # 管道阶段耗时
        self._stage_latencies: Dict[str, List[float]] = defaultdict(list)

        # 缓存统计
        self._cache_hits: int = 0
        self._cache_misses: int = 0

        # Φ 熵值
        self._phi_entropy: float = 0.0
        self._phi_entropy_history: List[float] = []

        # 启动时间
        self._started_at: float = time.time()

    def increment(self, metric: str, value: int = 1):
        with self._lock:
            self._counters[metric] += value

    def record_error(self, endpoint: str, error_type: str = "unknown"):
        with self._lock:
            self._errors[f"{endpoint}:{error_type}"] += 1

    def record_latency(self, endpoint: str, duration: float):
        with self._lock:
            self._latencies[endpoint].record(duration)

    def record_stage_latency(self, stage: str, duration: float):
        with self._lock:
            self._stage_latencies[stage].append(duration)
            if len(self._stage_latencies[stage]) > 100:
                self._stage_latencies[stage] = self._stage_latencies[stage][-100:]

    def record_cache_hit(self):
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self):
        with self._lock:
            self._cache_misses += 1

    def set_phi_entropy(self, value: float):
        with self._lock:
            self._phi_entropy = value
            self._phi_entropy_history.append(value)
            if len(self._phi_entropy_history) > 100:
                self._phi_entropy_history = self._phi_entropy_history[-100:]

    def track(self, name: str):
        """上下文管理器，自动记录延迟"""
        class _Tracker:
            def __init__(self, collector, name):
                self._collector = collector
                self._name = name
                self._start = 0.0

            def __enter__(self):
                self._start = time.time()
                return self

            def __exit__(self, *args):
                duration = time.time() - self._start
                self._collector.record_latency(self._name, duration)

        return _Tracker(self, name)

    @property
    def uptime(self) -> float:
        return time.time() - self._started_at

    @property
    def cache_hit_rate(self) -> float:
        total = self._cache_hits + self._cache_misses
        return round(self._cache_hits / total, 3) if total > 0 else 0.0

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            pipeline_p95 = self._latencies.get("pipeline", LatencyStats()).percentile(95)
            return {
                "name": self._name,
                "uptime_s": round(self.uptime, 1),
                "total_requests": self._counters.get("requests", 0),
                "total_errors": sum(self._errors.values()),
                "pipeline_p95_ms": round(pipeline_p95 * 1000, 2),
                "endpoints": {
                    ep: stats.summary() for ep, stats in self._latencies.items()
                },
                "stages": {
                    stage: {
                        "count": len(vals),
                        "avg_ms": round(sum(vals) / len(vals) * 1000, 2) if vals else 0,
                        "p95_ms": round(sorted(vals)[int(len(vals) * 0.95)] * 1000, 2) if len(vals) >= 20 else 0,
                    }
                    for stage, vals in self._stage_latencies.items()
                },
                "cache": {
                    "hits": self._cache_hits,
                    "misses": self._cache_misses,
                    "hit_rate": self.cache_hit_rate,
                },
                "phi_entropy": self._phi_entropy,
                "phi_history_len": len(self._phi_entropy_history),
            }

    def prometheus_text(self) -> str:
        """导出 Prometheus 文本格式"""
        lines = []
        lines.append("# HELP tengod_uptime_seconds Application uptime")
        lines.append("# TYPE tengod_uptime_seconds gauge")
        lines.append(f"tengod_uptime_seconds {self.uptime:.1f}")

        lines.append("# HELP tengod_requests_total Total requests")
        lines.append("# TYPE tengod_requests_total counter")
        lines.append(f"tengod_requests_total {self._counters.get('requests', 0)}")

        lines.append("# HELP tengod_errors_total Total errors")
        lines.append("# TYPE tengod_errors_total counter")
        lines.append(f"tengod_errors_total {sum(self._errors.values())}")

        for ep, stats in self._latencies.items():
            safe_name = ep.replace("/", "_").replace(".", "_")
            lines.append(f"# HELP tengod_latency_{safe_name}_seconds Endpoint latency")
            lines.append(f"# TYPE tengod_latency_{safe_name}_seconds summary")
            lines.append(f"tengod_latency_{safe_name}_seconds{{quantile=\"0.5\"}} {stats.percentile(50):.4f}")
            lines.append(f"tengod_latency_{safe_name}_seconds{{quantile=\"0.95\"}} {stats.percentile(95):.4f}")
            lines.append(f"tengod_latency_{safe_name}_seconds{{quantile=\"0.99\"}} {stats.percentile(99):.4f}")

        lines.append("# HELP tengod_cache_hit_rate Cache hit rate")
        lines.append("# TYPE tengod_cache_hit_rate gauge")
        lines.append(f"tengod_cache_hit_rate {self.cache_hit_rate:.3f}")

        lines.append("# HELP tengod_phi_entropy Current Φ entropy")
        lines.append("# TYPE tengod_phi_entropy gauge")
        lines.append(f"tengod_phi_entropy {self._phi_entropy:.4f}")

        return "\n".join(lines) + "\n"


# ── 全局指标收集器 ──
global_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    return global_metrics


__all__ = [
    "MetricsCollector",
    "LatencyStats",
    "global_metrics",
    "get_metrics",
]