#!/usr/bin/env python3
"""
metrics_collector.py — 监控指标采集器 v1.0.0

阶段十二：生产化部署运维

提供 Prometheus 格式的指标采集，包括：
  - HTTP 请求计数/延迟
  - 活跃连接数
  - 数据库连接池状态
  - Redis 缓存命中率
  - 业务指标（排盘次数、AI对话次数等）
  - 系统资源（CPU/内存/磁盘）
"""

from __future__ import annotations
import os
import time
import psutil
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


# ============================================================================
# 指标数据结构
# ============================================================================

@dataclass
class RequestMetrics:
    """HTTP 请求指标"""
    total_requests: int = 0
    total_errors: int = 0
    total_latency_ms: float = 0.0
    status_counts: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    endpoint_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


@dataclass
class BusinessMetrics:
    """业务指标"""
    bazi_calcs: int = 0
    ziwei_calcs: int = 0
    liuyao_calcs: int = 0
    qimen_calcs: int = 0
    name_analyses: int = 0
    marriage_analyses: int = 0
    ai_chats: int = 0
    ai_reports: int = 0
    knowledge_searches: int = 0


@dataclass
class SystemMetrics:
    """系统资源指标"""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    disk_percent: float = 0.0
    uptime_seconds: float = 0.0


# ============================================================================
# 指标采集器
# ============================================================================

class MetricsCollector:
    """全局指标采集器（单例模式）"""

    _instance: Optional["MetricsCollector"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._start_time = time.time()
        self._request_metrics = RequestMetrics()
        self._business_metrics = BusinessMetrics()
        self._system_metrics = SystemMetrics()
        self._lock_data = threading.Lock()

    # ── 请求指标 ──────────────────────────────────────────────────

    def record_request(self, endpoint: str, status_code: int, latency_ms: float):
        """记录一次 HTTP 请求"""
        with self._lock_data:
            self._request_metrics.total_requests += 1
            self._request_metrics.total_latency_ms += latency_ms
            self._request_metrics.status_counts[status_code] += 1
            self._request_metrics.endpoint_counts[endpoint] += 1
            if status_code >= 400:
                self._request_metrics.total_errors += 1

    # ── 业务指标 ──────────────────────────────────────────────────

    def record_bazi_calc(self):
        with self._lock_data:
            self._business_metrics.bazi_calcs += 1

    def record_ziwei_calc(self):
        with self._lock_data:
            self._business_metrics.ziwei_calcs += 1

    def record_liuyao_calc(self):
        with self._lock_data:
            self._business_metrics.liuyao_calcs += 1

    def record_qimen_calc(self):
        with self._lock_data:
            self._business_metrics.qimen_calcs += 1

    def record_name_analysis(self):
        with self._lock_data:
            self._business_metrics.name_analyses += 1

    def record_marriage_analysis(self):
        with self._lock_data:
            self._business_metrics.marriage_analyses += 1

    def record_ai_chat(self):
        with self._lock_data:
            self._business_metrics.ai_chats += 1

    def record_ai_report(self):
        with self._lock_data:
            self._business_metrics.ai_reports += 1

    def record_knowledge_search(self):
        with self._lock_data:
            self._business_metrics.knowledge_searches += 1

    # ── 系统指标 ──────────────────────────────────────────────────

    def _collect_system_metrics(self):
        """采集系统资源指标"""
        try:
            self._system_metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            self._system_metrics.memory_percent = mem.percent
            self._system_metrics.memory_used_mb = round(mem.used / 1024 / 1024, 2)
            disk = psutil.disk_usage("/")
            self._system_metrics.disk_percent = disk.percent
            self._system_metrics.uptime_seconds = round(time.time() - self._start_time, 1)
        except Exception:
            pass

    # ── 获取快照 ──────────────────────────────────────────────────

    def get_snapshot(self) -> Dict[str, Any]:
        """获取所有指标的快照"""
        self._collect_system_metrics()
        with self._lock_data:
            rm = self._request_metrics
            bm = self._business_metrics
            sm = self._system_metrics

            avg_latency = rm.total_latency_ms / rm.total_requests if rm.total_requests > 0 else 0
            error_rate = rm.total_errors / rm.total_requests * 100 if rm.total_requests > 0 else 0

            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": sm.uptime_seconds,
                "requests": {
                    "total": rm.total_requests,
                    "errors": rm.total_errors,
                    "error_rate_percent": round(error_rate, 2),
                    "avg_latency_ms": round(avg_latency, 2),
                    "status_codes": dict(rm.status_counts),
                    "top_endpoints": dict(sorted(
                        rm.endpoint_counts.items(), key=lambda x: -x[1]
                    )[:10]),
                },
                "business": {
                    "bazi_calcs": bm.bazi_calcs,
                    "ziwei_calcs": bm.ziwei_calcs,
                    "liuyao_calcs": bm.liuyao_calcs,
                    "qimen_calcs": bm.qimen_calcs,
                    "name_analyses": bm.name_analyses,
                    "marriage_analyses": bm.marriage_analyses,
                    "ai_chats": bm.ai_chats,
                    "ai_reports": bm.ai_reports,
                    "knowledge_searches": bm.knowledge_searches,
                },
                "system": {
                    "cpu_percent": sm.cpu_percent,
                    "memory_percent": sm.memory_percent,
                    "memory_used_mb": sm.memory_used_mb,
                    "disk_percent": sm.disk_percent,
                },
            }

    # ── Prometheus 格式 ───────────────────────────────────────────

    def to_prometheus(self) -> str:
        """输出 Prometheus 格式指标"""
        snap = self.get_snapshot()
        lines = []

        # 请求指标
        lines.append(f"# HELP tengod_requests_total Total HTTP requests")
        lines.append(f"# TYPE tengod_requests_total counter")
        lines.append(f"tengod_requests_total {snap['requests']['total']}")
        lines.append(f"# HELP tengod_request_errors_total Total HTTP errors")
        lines.append(f"# TYPE tengod_request_errors_total counter")
        lines.append(f"tengod_request_errors_total {snap['requests']['errors']}")
        lines.append(f"# HELP tengod_request_latency_avg_ms Average request latency in ms")
        lines.append(f"# TYPE tengod_request_latency_avg_ms gauge")
        lines.append(f"tengod_request_latency_avg_ms {snap['requests']['avg_latency_ms']}")

        # 业务指标
        lines.append(f"# HELP tengod_bazi_calcs_total Total bazi calculations")
        lines.append(f"# TYPE tengod_bazi_calcs_total counter")
        lines.append(f"tengod_bazi_calcs_total {snap['business']['bazi_calcs']}")
        lines.append(f"tengod_ziwei_calcs_total {snap['business']['ziwei_calcs']}")
        lines.append(f"tengod_liuyao_calcs_total {snap['business']['liuyao_calcs']}")
        lines.append(f"tengod_qimen_calcs_total {snap['business']['qimen_calcs']}")
        lines.append(f"tengod_ai_chats_total {snap['business']['ai_chats']}")

        # 系统指标
        lines.append(f"# HELP tengod_cpu_percent CPU usage percent")
        lines.append(f"# TYPE tengod_cpu_percent gauge")
        lines.append(f"tengod_cpu_percent {snap['system']['cpu_percent']}")
        lines.append(f"# HELP tengod_memory_percent Memory usage percent")
        lines.append(f"# TYPE tengod_memory_percent gauge")
        lines.append(f"tengod_memory_percent {snap['system']['memory_percent']}")
        lines.append(f"# HELP tengod_uptime_seconds Uptime in seconds")
        lines.append(f"# TYPE tengod_uptime_seconds gauge")
        lines.append(f"tengod_uptime_seconds {snap['uptime_seconds']}")

        return "\n".join(lines) + "\n"


# ============================================================================
# 全局单例
# ============================================================================

metrics = MetricsCollector()


# ============================================================================
# 健康检查器
# ============================================================================

class HealthChecker:
    """系统健康检查器"""

    @staticmethod
    def check_all() -> Dict[str, Any]:
        """执行全面健康检查"""
        checks = {}

        # 1. API 进程检查
        checks["api"] = {"status": "healthy", "message": "API server running"}

        # 2. 数据库检查
        try:
            from tengod.data_store import DataStore
            store = DataStore()
            store.stats()
            checks["database"] = {"status": "healthy", "message": "Database connected"}
        except Exception as e:
            checks["database"] = {"status": "unhealthy", "message": str(e)}

        # 3. Redis 检查（如果配置了）
        redis_url = os.environ.get("TENGOD_REDIS_URL", "")
        if redis_url:
            try:
                import redis
                r = redis.from_url(redis_url)
                r.ping()
                checks["redis"] = {"status": "healthy", "message": "Redis connected"}
            except Exception as e:
                checks["redis"] = {"status": "unhealthy", "message": str(e)}
        else:
            checks["redis"] = {"status": "skipped", "message": "Redis not configured"}

        # 4. 向量存储检查
        try:
            from tengod.vector_store import VectorStore
            vs = VectorStore()
            info = vs.info()
            checks["vector_store"] = {
                "status": "healthy",
                "message": f"Vector store: {info.get('total_nodes', 0)} nodes"
            }
        except Exception as e:
            checks["vector_store"] = {"status": "unhealthy", "message": str(e)}

        # 5. 系统资源检查
        snap = metrics.get_snapshot()
        sys_status = "healthy"
        if snap["system"]["cpu_percent"] > 90:
            sys_status = "warning"
        if snap["system"]["memory_percent"] > 90:
            sys_status = "warning"
        if snap["system"]["disk_percent"] > 90:
            sys_status = "critical"
        checks["system"] = {
            "status": sys_status,
            "cpu_percent": snap["system"]["cpu_percent"],
            "memory_percent": snap["system"]["memory_percent"],
            "disk_percent": snap["system"]["disk_percent"],
        }

        # 总体状态
        all_healthy = all(
            c.get("status") in ("healthy", "skipped") for c in checks.values()
        )
        overall = "healthy" if all_healthy else "degraded"

        return {
            "status": overall,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": snap["uptime_seconds"],
            "checks": checks,
        }


__all__ = ["MetricsCollector", "HealthChecker", "metrics"]
