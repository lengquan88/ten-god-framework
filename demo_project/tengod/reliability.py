#!/usr/bin/env python3
"""
reliability.py — Stage 29 · 性能与可靠性增强

综合可靠性模块，提供：
  - TokenBucket / SlidingWindow / RateLimiter 限流
  - CircuitBreaker 熔断器
  - EnhancedHealthChecker 健康检查
  - PerformanceBenchmark 性能基准
  - ReliabilityConfig / ReliabilityMonitor
  - 工具：timeit / retry / safe_call
"""

from __future__ import annotations

import functools
import json
import logging
import math
import os
import statistics
import threading
import time
import traceback
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("tengod.reliability")


# ============================================================================
# 1. RateLimiter —— 限流
# ============================================================================

class TokenBucket:
    """令牌桶限流器。"""

    def __init__(self, capacity: int, refill_rate_per_second: float):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_rate_per_second <= 0:
            raise ValueError("refill_rate_per_second must be positive")
        self.capacity = capacity
        self.refill_rate_per_second = refill_rate_per_second
        self.tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        if elapsed > 0:
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate_per_second,
            )
            self._last_refill = now

    def allow(self, cost: int = 1) -> bool:
        with self._lock:
            self._refill()
            if self.tokens >= cost:
                self.tokens -= cost
                return True
            return False

    def get_remaining(self) -> int:
        with self._lock:
            self._refill()
            return int(self.tokens)


class SlidingWindow:
    """滑动窗口限流器。优先使用 Redis，否则使用内存 deque。"""

    def __init__(self, limit: int, window_seconds: float, redis_client=None, key_prefix: str = "tengod:rl"):
        if limit <= 0:
            raise ValueError("limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self.redis_client = redis_client
        self.key_prefix = key_prefix
        self._requests: deque[float] = deque()
        self._lock = threading.Lock()
        self._use_redis = redis_client is not None

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _redis_key(self) -> str:
        return f"{self.key_prefix}:sw:{self.limit}:{self.window_seconds}"

    def allow(self) -> bool:
        if self._use_redis:
            try:
                return self._allow_redis()
            except Exception:
                logger.exception("SlidingWindow redis error, fallback to in-memory")
                self._use_redis = False
        with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()
            if len(self._requests) < self.limit:
                self._requests.append(now)
                return True
            return False

    def _allow_redis(self) -> bool:
        import redis
        key = self._redis_key()
        now_ms = self._now_ms()
        cutoff_ms = now_ms - int(self.window_seconds * 1000)
        pipe = self.redis_client.pipeline()
        try:
            pipe.zremrangebyscore(key, 0, cutoff_ms)
            pipe.zcard(key)
            pipe.zadd(key, {f"{now_ms}-{os.getpid()}-{int(time.time_ns())}": now_ms})
            pipe.expire(key, int(self.window_seconds) + 1)
            results = pipe.execute()
            current_count = int(results[1])
            return current_count < self.limit
        except Exception:
            raise

    def get_remaining(self) -> int:
        if self._use_redis:
            try:
                key = self._redis_key()
                now_ms = self._now_ms()
                cutoff_ms = now_ms - int(self.window_seconds * 1000)
                self.redis_client.zremrangebyscore(key, 0, cutoff_ms)
                count = self.redis_client.zcard(key)
                return max(0, self.limit - int(count))
            except Exception:
                self._use_redis = False
        with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()
            return max(0, self.limit - len(self._requests))


class RateLimiter:
    """统一限流器包装。"""

    def __init__(self, algorithm: str = "token_bucket", **kwargs):
        self.algorithm = algorithm
        if algorithm == "token_bucket":
            self._impl: Any = TokenBucket(
                capacity=kwargs.get("capacity", 100),
                refill_rate_per_second=kwargs.get("refill_rate_per_second", 10.0),
            )
        elif algorithm == "sliding_window":
            self._impl = SlidingWindow(
                limit=kwargs.get("limit", 100),
                window_seconds=kwargs.get("window_seconds", 60.0),
                redis_client=kwargs.get("redis_client", None),
            )
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

    def allow(self) -> bool:
        return self._impl.allow()

    def get_remaining(self) -> int:
        return int(self._impl.get_remaining())


# ============================================================================
# 2. CircuitBreaker —— 熔断器
# ============================================================================

class CircuitBreakerState:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    pass


class CircuitBreaker:
    """熔断器。"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
        name: str = "default",
        fallback: Optional[Callable[..., Any]] = None,
    ):
        if failure_threshold <= 0:
            raise ValueError("failure_threshold must be positive")
        if recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be positive")
        if success_threshold <= 0:
            raise ValueError("success_threshold must be positive")
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.name = name
        self.fallback = fallback
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._opened_at: Optional[float] = None
        self._lock = threading.RLock()

    # ── state ──────────────────────────────────────────────────

    @property
    def state(self) -> str:
        with self._lock:
            self._maybe_transition_to_half_open()
            return self._state

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failure_count

    @property
    def success_count(self) -> int:
        with self._lock:
            return self._success_count

    @property
    def last_failure_time(self) -> Optional[float]:
        with self._lock:
            return self._last_failure_time

    def _maybe_transition_to_half_open(self) -> None:
        if (
            self._state == CircuitBreakerState.OPEN
            and self._opened_at is not None
            and (time.monotonic() - self._opened_at) >= self.recovery_timeout
        ):
            self._state = CircuitBreakerState.HALF_OPEN
            self._success_count = 0

    def _on_success(self) -> None:
        with self._lock:
            self._last_failure_time = None
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = CircuitBreakerState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            else:
                self._failure_count = 0
                self._success_count += 1

    def _on_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            self._success_count = 0
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._state = CircuitBreakerState.OPEN
                self._opened_at = time.monotonic()
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitBreakerState.OPEN
                self._opened_at = time.monotonic()

    # ── actions ──────────────────────────────────────────────────

    def reset(self) -> None:
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self._opened_at = None

    def trip(self) -> None:
        with self._lock:
            self._state = CircuitBreakerState.OPEN
            self._opened_at = time.monotonic()

    # ── call ──────────────────────────────────────────────────

    def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        with self._lock:
            self._maybe_transition_to_half_open()
            if self._state == CircuitBreakerState.OPEN:
                if self.fallback is not None:
                    return self.fallback(*args, **kwargs)
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN"
                )
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            if self.fallback is not None:
                return self.fallback(*args, **kwargs)
            raise

    # ── context manager ──────────────────────────────────────────

    def __enter__(self) -> "CircuitBreaker":
        with self._lock:
            self._maybe_transition_to_half_open()
            if self._state == CircuitBreakerState.OPEN:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN"
                )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            self._on_success()
        else:
            self._on_failure()
            if self.fallback is not None:
                return True
        return False

    # ── decorator ──────────────────────────────────────────────────

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper


# ============================================================================
# 3. EnhancedHealthChecker —— 增强健康检查
# ============================================================================

class EnhancedHealthChecker:
    """扩展的健康检查器，覆盖 DB / Cache / 向量存储 / 系统资源 / 核心引擎。"""

    ENGINE_CLASSES = [
        ("liunian_judgment", "tengod.liunian_judgment", "LiunianJudgmentEngine"),
        ("xuankong", "tengod.fengshui.xuankong", "XuankongEngine"),
        ("qizheng", "tengod.qizheng.engine", "QizhengEngine"),
    ]

    def __init__(self):
        self._lock = threading.Lock()

    # ── 数据库 ──────────────────────────────────────────────────

    def check_database(self) -> Dict[str, Any]:
        try:
            from tengod.data_store import DataStore
            store = DataStore()
            stats = getattr(store, "stats", lambda: {})()
            return {
                "status": "healthy",
                "message": "database responsive",
                "stats": stats if isinstance(stats, dict) else {"ok": True},
            }
        except Exception as exc:
            return {"status": "unhealthy", "message": str(exc)}

    # ── 缓存 ──────────────────────────────────────────────────

    def check_cache(self) -> Dict[str, Any]:
        try:
            from tengod.cache_manager import get_cache_manager
            cm = get_cache_manager()
            health = getattr(cm, "health_check", lambda: {"status": "unknown"})()
            if isinstance(health, dict) and "status" in health:
                return health
            return {"status": "healthy", "message": "cache available"}
        except Exception as exc:
            try:
                from tengod.cache_manager import MemoryCacheManager
                mcm = MemoryCacheManager()
                mcm.set("tengod:health:ping", "1", ttl=5)
                val = mcm.get("tengod:health:ping")
                return {
                    "status": "healthy",
                    "message": f"in-memory cache works (got={val})",
                    "mode": "memory",
                }
            except Exception as exc2:
                return {"status": "unhealthy", "message": str(exc2)}

    # ── 向量存储 ──────────────────────────────────────────────────

    def check_vector_store(self) -> Dict[str, Any]:
        try:
            try:
                from tengod.vector_store import VectorStore
                vs = VectorStore()
                info = getattr(vs, "info", lambda: {})()
                return {
                    "status": "healthy",
                    "message": "vector store responsive",
                    "info": info if isinstance(info, dict) else {"ok": True},
                }
            except Exception:
                from tengod.vector_store_pg import VectorStore as VSPG
                vs = VSPG()
                info = getattr(vs, "info", lambda: {})()
                return {
                    "status": "healthy",
                    "message": "pg vector store responsive",
                    "info": info if isinstance(info, dict) else {"ok": True},
                }
        except Exception as exc:
            return {"status": "unhealthy", "message": str(exc)}

    # ── 系统资源 ──────────────────────────────────────────────────

    def check_system_resources(self) -> Dict[str, Any]:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            load_avg = None
            try:
                load_avg = list(os.getloadavg())
            except (OSError, AttributeError):
                pass
            return {
                "status": "healthy",
                "cpu_percent": cpu,
                "memory_percent": mem.percent,
                "memory_used_mb": round(mem.used / 1024 / 1024, 2),
                "disk_percent": disk.percent,
                "load_avg": load_avg,
            }
        except Exception as exc:
            return {
                "status": "degraded",
                "message": str(exc),
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "disk_percent": 0.0,
            }

    # ── 核心引擎 ──────────────────────────────────────────────────

    def check_core_engines(self) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        for engine_name, module_name, class_name in self.ENGINE_CLASSES:
            try:
                import importlib
                mod = importlib.import_module(module_name)
                cls = getattr(mod, class_name)
                engine = cls()
                # 基本 smoke test —— 尝试获取信息或简单调用
                info = getattr(engine, "info", None)
                if info is not None:
                    info()
                results[engine_name] = {
                    "status": "healthy",
                    "class": class_name,
                    "module": module_name,
                }
            except Exception as exc:
                results[engine_name] = {
                    "status": "unhealthy",
                    "message": str(exc),
                    "class": class_name,
                }
        return results

    # ── 综合检查 ──────────────────────────────────────────────────

    def check_all(self) -> Dict[str, Any]:
        with self._lock:
            checks = {
                "database": self.check_database(),
                "cache": self.check_cache(),
                "vector_store": self.check_vector_store(),
                "system_resources": self.check_system_resources(),
                "core_engines": self.check_core_engines(),
            }
            reasons: List[str] = []
            unhealthy_count = 0
            for name, result in checks.items():
                if isinstance(result, dict):
                    status = result.get("status", "unknown")
                else:
                    status = "unknown"
                if status == "unhealthy":
                    unhealthy_count += 1
                    reasons.append(f"{name}: {result.get('message', status)}")
                elif status == "degraded" and name == "system_resources":
                    reasons.append(f"{name}: resource warning")

            total_engines = 0
            healthy_engines = 0
            engines = checks.get("core_engines", {})
            if isinstance(engines, dict):
                for _, engine_info in engines.items():
                    total_engines += 1
                    if isinstance(engine_info, dict) and engine_info.get("status") == "healthy":
                        healthy_engines += 1

            if unhealthy_count == 0 and len(reasons) == 0:
                overall = "healthy"
            elif unhealthy_count >= 2:
                overall = "critical"
            else:
                overall = "degraded"

            return {
                "status": overall,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": checks,
                "reasons": reasons,
                "healthy_engines": healthy_engines,
                "total_engines": total_engines,
            }

    # ── 健康分数 ──────────────────────────────────────────────────

    def get_health_score(self) -> int:
        result = self.check_all()
        checks = result.get("checks", {})
        score = 100
        for name, info in checks.items():
            if not isinstance(info, dict):
                continue
            status = info.get("status", "unknown")
            if status == "unhealthy":
                score -= 20
            elif status == "degraded":
                score -= 10
            elif status == "skipped":
                score -= 2
        return max(0, min(100, int(score)))


# ============================================================================
# 4. PerformanceBenchmark —— 性能基准
# ============================================================================

class PerformanceBenchmark:
    """简单函数/管道的性能基准测试。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._history: Dict[str, Dict[str, Any]] = {}

    def benchmark_function(
        self,
        func: Callable[..., Any],
        iterations: int = 100,
        warmup: int = 10,
        *args,
        **kwargs,
    ) -> Dict[str, float]:
        if iterations <= 0:
            return {
                "avg_ms": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "max_ms": 0.0,
                "min_ms": 0.0,
                "iterations": iterations,
            }
        for _ in range(max(0, warmup)):
            try:
                func(*args, **kwargs)
            except Exception:
                pass
        times_ms: List[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                func(*args, **kwargs)
            except Exception:
                pass
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            times_ms.append(elapsed_ms)

        sorted_times = sorted(times_ms)

        def percentile(pct: float) -> float:
            if not sorted_times:
                return 0.0
            k = (len(sorted_times) - 1) * pct
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_times[int(k)]
            d0 = sorted_times[int(f)] * (c - k)
            d1 = sorted_times[int(c)] * (k - f)
            return d0 + d1

        stats = {
            "avg_ms": statistics.mean(times_ms),
            "p50": percentile(0.50),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
            "max_ms": max(times_ms) if times_ms else 0.0,
            "min_ms": min(times_ms) if times_ms else 0.0,
            "iterations": iterations,
        }
        with self._lock:
            self._history[getattr(func, "__name__", "anonymous")] = stats
        return stats

    def benchmark_bazi_calc(self, iterations: int = 50) -> Dict[str, float]:
        try:
            from tengod.bazi_calculator import BaziChart

            def _calc():
                BaziChart(1990, 6, 15, 10, 30, lon=116.4, lat=39.9)

            return self.benchmark_function(_calc, iterations=iterations, warmup=5)
        except Exception as exc:
            return {"error": str(exc), "avg_ms": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max_ms": 0.0, "min_ms": 0.0, "iterations": iterations}

    def benchmark_vector_search(self, iterations: int = 20) -> Dict[str, float]:
        try:
            from tengod.vector_store import VectorStore
            vs = VectorStore()

            def _search():
                if hasattr(vs, "search"):
                    try:
                        vs.search("test query", top_k=3)
                    except Exception:
                        pass

            return self.benchmark_function(_search, iterations=iterations, warmup=2)
        except Exception as exc:
            return {"error": str(exc), "avg_ms": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max_ms": 0.0, "min_ms": 0.0, "iterations": iterations}

    def benchmark_full_pipeline(self, iterations: int = 10) -> Dict[str, float]:
        try:
            from tengod.bazi_calculator import BaziChart

            def _pipeline():
                chart = BaziChart(1990, 6, 15, 10, 30, lon=116.4, lat=39.9)
                pillars = getattr(chart, "pillars", {})
                _ = len(str(pillars))

            return self.benchmark_function(_pipeline, iterations=iterations, warmup=2)
        except Exception as exc:
            return {"error": str(exc), "avg_ms": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max_ms": 0.0, "min_ms": 0.0, "iterations": iterations}

    def report(self) -> str:
        with self._lock:
            if not self._history:
                return "[PerformanceBenchmark] No benchmarks recorded yet."
            lines = ["=== Performance Benchmark Report ==="]
            for name, stats in self._history.items():
                lines.append(f"\n[{name}]")
                for key in ("iterations", "avg_ms", "p50", "p95", "p99", "min_ms", "max_ms"):
                    if key in stats:
                        val = stats[key]
                        if isinstance(val, float):
                            lines.append(f"  {key}: {val:.4f} ms")
                        else:
                            lines.append(f"  {key}: {val}")
            return "\n".join(lines)


# ============================================================================
# 5. ReliabilityConfig —— 配置
# ============================================================================

@dataclass
class ReliabilityConfig:
    max_error_rate: float = 0.05
    max_avg_latency_ms: float = 1000.0
    max_memory_percent: float = 90.0
    max_cpu_percent: float = 90.0
    min_available_engines: int = 3

    def as_dict(self) -> Dict[str, Any]:
        return {
            "max_error_rate": self.max_error_rate,
            "max_avg_latency_ms": self.max_avg_latency_ms,
            "max_memory_percent": self.max_memory_percent,
            "max_cpu_percent": self.max_cpu_percent,
            "min_available_engines": self.min_available_engines,
        }


# ============================================================================
# 6. ReliabilityMonitor —— 综合监控
# ============================================================================

class ReliabilityMonitor:
    """整合健康检查、性能、指标采集的综合监控器。"""

    def __init__(self, config: Optional[ReliabilityConfig] = None):
        self.config = config or ReliabilityConfig()
        self.health_checker = EnhancedHealthChecker()
        self.benchmark = PerformanceBenchmark()
        self._lock = threading.Lock()
        self._component_failures: Dict[str, int] = defaultdict(int)

    def record_failure(self, component: str) -> None:
        with self._lock:
            self._component_failures[component] += 1

    def get_component_failures(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._component_failures)

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        try:
            from tengod.metrics_collector import metrics
            return metrics.get_snapshot()
        except Exception as exc:
            return {
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def check_reliability(self, config: Optional[ReliabilityConfig] = None) -> Dict[str, Any]:
        cfg = config or self.config
        reasons: List[str] = []
        status = "healthy"

        health = self.health_checker.check_all()
        checks = health.get("checks", {})

        # 资源检查
        sys_res = checks.get("system_resources", {})
        if isinstance(sys_res, dict):
            cpu = float(sys_res.get("cpu_percent", 0.0) or 0.0)
            mem = float(sys_res.get("memory_percent", 0.0) or 0.0)
            if cpu > cfg.max_cpu_percent:
                reasons.append(f"CPU usage {cpu:.1f}% > {cfg.max_cpu_percent}%")
            if mem > cfg.max_memory_percent:
                reasons.append(f"Memory usage {mem:.1f}% > {cfg.max_memory_percent}%")

        # 引擎可用性
        engines = checks.get("core_engines", {})
        healthy_engines = 0
        total_engines = 0
        if isinstance(engines, dict):
            for _, info in engines.items():
                total_engines += 1
                if isinstance(info, dict) and info.get("status") == "healthy":
                    healthy_engines += 1
        if healthy_engines < cfg.min_available_engines:
            reasons.append(
                f"Only {healthy_engines}/{total_engines} engines available (need {cfg.min_available_engines})"
            )

        # 错误率 / 延迟 （基于 MetricsCollector）
        try:
            snap = self.get_metrics_snapshot()
            requests = snap.get("requests", {}) if isinstance(snap, dict) else {}
            total_req = int(requests.get("total", 0) or 0)
            total_errors = int(requests.get("errors", 0) or 0)
            error_rate = (total_errors / total_req) if total_req > 0 else 0.0
            avg_latency = float(requests.get("avg_latency_ms", 0.0) or 0.0)
            if error_rate > cfg.max_error_rate and total_req > 10:
                reasons.append(f"Error rate {error_rate:.3f} > {cfg.max_error_rate}")
            if avg_latency > cfg.max_avg_latency_ms and total_req > 0:
                reasons.append(f"Avg latency {avg_latency:.2f}ms > {cfg.max_avg_latency_ms}ms")
        except Exception:
            pass

        # 组件失败
        with self._lock:
            total_failures = sum(self._component_failures.values())
            if total_failures > 5:
                reasons.append(f"{total_failures} component failures recently")

        if reasons:
            critical = any(
                ("only" in r.lower() and "engine" in r.lower())
                or ("critical" in r.lower())
                for r in reasons
            )
            status = "critical" if critical and len(reasons) >= 2 else "degraded"

        return {
            "status": status,
            "reasons": reasons,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config": cfg.as_dict(),
            "health": health,
            "healthy_engines": healthy_engines,
            "total_engines": total_engines,
            "component_failures": dict(self._component_failures),
        }

    def get_reliability_score(self) -> int:
        score = 100
        cfg = self.config

        # 基础健康检查
        health_score = self.health_checker.get_health_score()
        score -= (100 - health_score) * 0.5

        # 资源
        sys_res = self.health_checker.check_system_resources()
        if isinstance(sys_res, dict):
            cpu = float(sys_res.get("cpu_percent", 0.0) or 0.0)
            mem = float(sys_res.get("memory_percent", 0.0) or 0.0)
            if cpu > cfg.max_cpu_percent:
                score -= (cpu - cfg.max_cpu_percent) * 0.5
            if mem > cfg.max_memory_percent:
                score -= (mem - cfg.max_memory_percent) * 0.5

        # 引擎可用性
        try:
            engines = self.health_checker.check_core_engines()
            healthy = sum(
                1 for _, info in engines.items()
                if isinstance(info, dict) and info.get("status") == "healthy"
            )
            if healthy < cfg.min_available_engines:
                score -= (cfg.min_available_engines - healthy) * 10
        except Exception:
            pass

        # 组件失败
        with self._lock:
            total_failures = sum(self._component_failures.values())
            score -= total_failures * 2

        return max(0, min(100, int(round(score))))


# ============================================================================
# 7. Helper functions
# ============================================================================

def timeit(func: Callable[..., Any], *args, **kwargs) -> Tuple[Any, float]:
    """执行 func，返回 (结果, 耗时毫秒)。"""
    start = time.perf_counter()
    try:
        result = func(*args, **kwargs)
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        raise
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return result, elapsed_ms


def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    exponential: bool = False,
    exceptions: Optional[tuple] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """装饰器：重试失败的函数。"""
    if exceptions is None:
        exceptions = (Exception,)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Optional[Exception] = None
            current_delay = delay
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt >= max_retries:
                        raise
                    time.sleep(current_delay)
                    if exponential:
                        current_delay *= 2
            if last_exc is not None:
                raise last_exc
        return wrapper

    return decorator


def safe_call(
    func: Callable[..., Any],
    *args,
    fallback: Any = None,
    timeout: float = 5.0,
    **kwargs,
) -> Any:
    """以超时+异常安全的方式调用函数。"""
    if timeout and timeout > 0 and timeout < 300:
        import signal

        def _handler(signum, frame):
            raise TimeoutError(f"safe_call timed out after {timeout}s")

        try:
            if hasattr(signal, "SIGALRM"):
                old_handler = signal.signal(signal.SIGALRM, _handler)
                signal.setitimer(signal.ITIMER_REAL, timeout)
                try:
                    return func(*args, **kwargs)
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    signal.signal(signal.SIGALRM, old_handler)
            else:
                return func(*args, **kwargs)
        except TimeoutError:
            return fallback
        except Exception:
            return fallback
    else:
        try:
            return func(*args, **kwargs)
        except Exception:
            return fallback


# ============================================================================
# 8. Self-test
# ============================================================================

def _self_test() -> Dict[str, Any]:
    results: Dict[str, Any] = {}

    # Rate limiter
    tb = TokenBucket(capacity=3, refill_rate_per_second=10.0)
    results["token_bucket_initial"] = tb.get_remaining()
    allow_count = sum(1 for _ in range(5) if tb.allow())
    results["token_bucket_allows"] = allow_count

    sw = SlidingWindow(limit=3, window_seconds=1.0)
    sw_allows = sum(1 for _ in range(5) if sw.allow())
    results["sliding_window_allows"] = sw_allows

    rl = RateLimiter("token_bucket", capacity=10, refill_rate_per_second=5.0)
    results["rate_limiter_remaining"] = rl.get_remaining()

    # Circuit breaker
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    results["cb_initial_state"] = cb.state
    try:
        for _ in range(3):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    except Exception:
        pass
    results["cb_state_after_failures"] = cb.state
    results["cb_failure_count"] = cb.failure_count
    cb.reset()

    # Health checker
    hc = EnhancedHealthChecker()
    results["health_score"] = hc.get_health_score()

    # Benchmark
    pb = PerformanceBenchmark()
    stats = pb.benchmark_function(lambda: sum(range(100)), iterations=20, warmup=2)
    results["benchmark_stats"] = {k: round(v, 4) for k, v in stats.items() if isinstance(v, (int, float))}

    # timeit
    _, elapsed = timeit(lambda: sum(range(1000)))
    results["timeit_elapsed_ms"] = round(elapsed, 4)

    # retry
    counter = {"calls": 0}

    def flaky():
        counter["calls"] += 1
        if counter["calls"] < 3:
            raise RuntimeError("flaky")
        return "ok"

    retried = retry(max_retries=3, delay=0.01)(flaky)
    try:
        results["retry_result"] = retried()
    except Exception as exc:
        results["retry_result"] = f"error: {exc}"

    # safe_call
    results["safe_call_exception"] = safe_call(lambda: 1 / 0, fallback=42)

    # Monitor
    monitor = ReliabilityMonitor()
    monitor.record_failure("test_component")
    results["monitor_reliability_score"] = monitor.get_reliability_score()
    results["monitor_status"] = monitor.check_reliability()["status"]

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    print(json.dumps(_self_test(), indent=2, ensure_ascii=False, default=str))


__all__ = [
    "TokenBucket",
    "SlidingWindow",
    "RateLimiter",
    "CircuitBreaker",
    "CircuitBreakerState",
    "CircuitBreakerError",
    "EnhancedHealthChecker",
    "PerformanceBenchmark",
    "ReliabilityConfig",
    "ReliabilityMonitor",
    "timeit",
    "retry",
    "safe_call",
]
