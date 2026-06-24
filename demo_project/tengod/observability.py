"""
observability.py — 可观测性模块 v2.8
=====================================
结构化日志、健康检查、Prometheus 指标、请求追踪
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import threading
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable

# ── 请求追踪 ────────────────────────────────────────────────────────────────

_request_id: ContextVar[str] = ContextVar("request_id", default="")
_request_start: ContextVar[float] = ContextVar("request_start", default=0.0)


def generate_request_id() -> str:
    return uuid.uuid4().hex[:12]


def get_request_id() -> str:
    return _request_id.get() or ""


def set_request_id(rid: str) -> None:
    _request_id.set(rid)


# ── 结构化日志 ──────────────────────────────────────────────────────────────

class JsonFormatter(logging.Formatter):
    """JSON 格式日志输出"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "request_id": get_request_id(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(
    level: str = "INFO",
    fmt: str = "json",
    log_file: Optional[str] = None,
) -> None:
    """配置全局日志

    Args:
        level: 日志级别
        fmt: 格式 (json/text)
        log_file: 日志文件路径 (可选)
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 清除已有 handler
    root.handlers.clear()

    if fmt == "json":
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))

    root.addHandler(handler)

    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(JsonFormatter() if fmt == "json" else logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))
        root.addHandler(fh)

    # 降低第三方库日志级别
    for lib in ["uvicorn", "httpx", "httpcore", "openai", "faiss"]:
        logging.getLogger(lib).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取带请求ID的日志器"""
    return logging.getLogger(name)


# ── 健康检查 ────────────────────────────────────────────────────────────────

class HealthCheck:
    """健康检查注册与执行"""

    def __init__(self):
        self._checks: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def register(self, name: str, check_fn: Callable[[], Dict[str, Any]]) -> None:
        """注册健康检查

        check_fn 返回 {"status": "healthy"|"degraded"|"unhealthy", "detail": str}
        """
        with self._lock:
            self._checks[name] = check_fn

    def run_all(self) -> Dict[str, Any]:
        """执行所有健康检查"""
        results = {}
        overall = "healthy"

        for name, check_fn in self._checks.items():
            try:
                result = check_fn()
                status = result.get("status", "unknown")
                results[name] = result
                if status == "unhealthy":
                    overall = "unhealthy"
                elif status == "degraded" and overall == "healthy":
                    overall = "degraded"
            except Exception as e:
                results[name] = {"status": "unhealthy", "detail": str(e)}
                overall = "unhealthy"

        return {
            "status": overall,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": results,
        }


_health_checker = HealthCheck()


def get_health_checker() -> HealthCheck:
    return _health_checker


def register_health_check(name: str, check_fn: Callable[[], Dict[str, Any]]) -> None:
    _health_checker.register(name, check_fn)


# ── Prometheus 指标 ─────────────────────────────────────────────────────────

class MetricsCollector:
    """简易 Prometheus 指标收集器 v2.8"""

    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._gauges: Dict[str, float] = {}
        self._lock = threading.Lock()

    def counter_inc(self, name: str, labels: Optional[Dict[str, str]] = None) -> None:
        key = _metric_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + 1

    def histogram_observe(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """记录直方图值（保留最近1000个值）"""
        key = _metric_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]

    def gauge_set(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = _metric_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def get_metrics(self) -> str:
        """生成 Prometheus 格式文本"""
        lines = []
        with self._lock:
            for key, val in self._counters.items():
                name, label_str = _parse_key(key)
                lines.append(f"# HELP {name} Counter metric")
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name}{{{label_str}}} {val}")

            for key, vals in self._histograms.items():
                name, label_str = _parse_key(key)
                if vals:
                    lines.append(f"# HELP {name} Histogram metric")
                    lines.append(f"# TYPE {name} histogram")
                    lines.append(f"{name}_sum{{{label_str}}} {sum(vals)}")
                    lines.append(f"{name}_count{{{label_str}}} {len(vals)}")
                    lines.append(f"{name}_avg{{{label_str}}} {sum(vals) / len(vals):.3f}")

            for key, val in self._gauges.items():
                name, label_str = _parse_key(key)
                lines.append(f"# HELP {name} Gauge metric")
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name}{{{label_str}}} {val}")

        lines.append(f"# EOF {datetime.now(timezone.utc).isoformat()}")
        return "\n".join(lines) + "\n"


def _metric_key(name: str, labels: Optional[Dict[str, str]]) -> str:
    if not labels:
        return name
    parts = [f'{k}="{v}"' for k, v in sorted(labels.items())]
    return f"{name}:{';'.join(parts)}"


def _parse_key(key: str) -> tuple:
    if ":" in key:
        name, label_part = key.split(":", 1)
        return name, label_part.replace(";", ",")
    return key, ""


_metrics = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    return _metrics


# ── 请求追踪中间件 ──────────────────────────────────────────────────────────

class RequestTracker:
    """请求追踪中间件（支持 FastAPI/WSGI）"""

    def __init__(self):
        self._active_requests: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def start_request(self, request_id: str, method: str, path: str) -> None:
        with self._lock:
            self._active_requests[request_id] = {
                "method": method,
                "path": path,
                "start_time": time.time(),
                "status": "processing",
            }
        _metrics.counter_inc("http_requests_total", {"method": method, "path": path})

    def end_request(self, request_id: str, status_code: int, duration_ms: float) -> None:
        with self._lock:
            self._active_requests.pop(request_id, None)
        _metrics.histogram_observe("http_request_duration_ms", duration_ms)
        _metrics.counter_inc("http_responses_total", {"status": str(status_code)})

    def get_active_requests(self) -> List[Dict[str, Any]]:
        with self._lock:
            result = []
            for rid, info in self._active_requests.items():
                info["request_id"] = rid
                info["elapsed_ms"] = (time.time() - info["start_time"]) * 1000
                result.append(info)
            return result


_request_tracker = RequestTracker()


def get_request_tracker() -> RequestTracker:
    return _request_tracker


# ── 便捷函数 ────────────────────────────────────────────────────────────────

def health_check_response() -> Dict[str, Any]:
    """生成健康检查响应"""
    result = _health_checker.run_all()
    result["active_requests"] = _request_tracker.get_active_requests()
    result["uptime_seconds"] = time.time() - _startup_time
    return result


_startup_time = time.time()


def reset_startup_time() -> None:
    global _startup_time
    _startup_time = time.time()


__all__ = [
    "setup_logging",
    "get_logger",
    "get_request_id",
    "set_request_id",
    "generate_request_id",
    "HealthCheck",
    "get_health_checker",
    "register_health_check",
    "health_check_response",
    "MetricsCollector",
    "get_metrics_collector",
    "RequestTracker",
    "get_request_tracker",
    "reset_startup_time",
]