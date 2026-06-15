#!/usr/bin/env python3
"""
metrics.py — 统一日志与监控 v1.5.0
提供结构化日志、Prometheus 格式指标暴露、健康检查。
"""

import json
import sys
import threading
import time
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, List, Optional


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


LOG_LEVEL_MAP = {
    "DEBUG": LogLevel.DEBUG,
    "INFO": LogLevel.INFO,
    "WARNING": LogLevel.WARNING,
    "ERROR": LogLevel.ERROR,
}


class StructuredLogger:
    """统一结构化日志 — JSON 格式"""

    def __init__(self, name: str = "tengod", min_level: LogLevel = LogLevel.INFO):
        self._name = name
        self._min_level = min_level
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = defaultdict(int)

    def set_level(self, level: str) -> None:
        self._min_level = LOG_LEVEL_MAP.get(level.upper(), LogLevel.INFO)

    def _log(self, level: LogLevel, message: str, **kwargs: Any) -> None:
        if level.value in ("DEBUG",) and self._min_level == LogLevel.DEBUG:
            pass
        if self._min_level == LogLevel.DEBUG and level == LogLevel.INFO:
            pass
        # Simple level comparison based on enum order
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if levels.index(level.value) < levels.index(self._min_level.value):
            return

        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "level": level.value,
            "logger": self._name,
            "message": message,
        }
        entry.update(kwargs)

        with self._lock:
            print(json.dumps(entry, ensure_ascii=False, default=str), file=sys.stderr)
            self._counters[level.value] += 1

    def debug(self, message: str, **kwargs: Any) -> None:
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log(LogLevel.ERROR, message, **kwargs)

    def counters(self) -> Dict[str, int]:
        return dict(self._counters)


class PrometheusMetrics:
    """Prometheus 格式指标暴露器"""

    def __init__(self, name: str = "tengod"):
        self._name = name
        self._lock = threading.Lock()
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._start_time = time.time()

    def counter_inc(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        key = self._metric_key(name, labels)
        with self._lock:
            self._counters[key] += value

    def gauge_set(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        key = self._metric_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def histogram_observe(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        key = self._metric_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)

    def _metric_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        if labels:
            parts = [f'{k}="{v}"' for k, v in sorted(labels.items())]
            return name + "{" + ",".join(parts) + "}"
        return name

    def _extract_help(self, full_name: str) -> tuple:
        """从 metric key 提取 base name 和 labels"""
        if "{" in full_name:
            base = full_name[: full_name.index("{")]
            label_str = full_name[full_name.index("{") :]
        else:
            base = full_name
            label_str = ""
        help_map = {
            "tengod_http_requests_total": "Total HTTP requests processed",
            "tengod_http_request_duration_seconds": "HTTP request duration in seconds",
            "tengod_tasks_total": "Total tasks processed",
            "tengod_tasks_active": "Currently active tasks",
            "tengod_errors_total": "Total errors encountered",
            "tengod_db_connections": "Current database connections",
            "tengod_tokens_total": "Total tokens used",
            "tengod_rate_limit_hits": "Rate limit hits",
        }
        return help_map.get(base, f"Metric {base}"), label_str

    def generate_text(self) -> str:
        """生成 Prometheus text 格式输出"""
        lines: List[str] = []

        # HELP + TYPE lines
        seen_bases: set = set()
        with self._lock:
            all_keys = (
                list(self._counters.keys())
                + list(self._gauges.keys())
                + list(self._histograms.keys())
            )
        for key in all_keys:
            if "{" in key:
                base = key[: key.index("{")]
            else:
                base = key
            if base in seen_bases:
                continue
            seen_bases.add(base)
            help_text, _ = self._extract_help(key)
            lines.append(f"# HELP {base} {help_text}")
            if base in [k.split("{")[0] for k in self._counters]:
                lines.append(f"# TYPE {base} counter")
            elif base in [k.split("{")[0] for k in self._gauges]:
                lines.append(f"# TYPE {base} gauge")
            elif base in [k.split("{")[0] for k in self._histograms]:
                lines.append(f"# TYPE {base} histogram")

        # Values
        with self._lock:
            for key, val in self._counters.items():
                lines.append(f"{key} {val:.0f}")
            for key, val in self._gauges.items():
                lines.append(f"{key} {val:.6f}")
            for key, vals in self._histograms.items():
                base = key.split("{")[0] if "{" in key else key
                label_part = key[len(base) :]
                if vals:
                    lines.append(f"{base}_sum{label_part} {sum(vals):.6f}")
                    lines.append(f"{base}_count{label_part} {len(vals)}")

        # Uptime
        uptime = time.time() - self._start_time
        lines.append("# HELP tengod_uptime_seconds Service uptime in seconds")
        lines.append("# TYPE tengod_uptime_seconds gauge")
        lines.append(f"tengod_uptime_seconds {uptime:.2f}")

        return "\n".join(lines) + "\n"

    def get_stats(self) -> Dict[str, Any]:
        """获取统计摘要（JSON格式，用于API）"""
        with self._lock:
            uptime = time.time() - self._start_time
            return {
                "start_time": time.strftime(
                    "%Y-%m-%dT%H:%M:%S", time.localtime(self._start_time)
                ),
                "uptime_seconds": round(uptime, 2),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histogram_counts": {k: len(v) for k, v in self._histograms.items()},
            }


# 全局实例
logger = StructuredLogger("tengod")
metrics = PrometheusMetrics("tengod")


def get_logger() -> StructuredLogger:
    return logger


def get_metrics() -> PrometheusMetrics:
    return metrics


__all__ = [
    "StructuredLogger",
    "PrometheusMetrics",
    "LogLevel",
    "LOGGER",
    "get_logger",
    "get_metrics",
]
__version__ = "1.5.0"
