"""
error_handler.py — 分级错误处理与九宫格错误分类 v2.31.0
===========================================================
道曰："祸兮福之所倚，福兮祸之所伏。"

将错误视为系统的"免疫反应"，分级处理，自动回退。

核心能力：
  - 五级错误分级：DEBUG/INFO/WARNING/ERROR/CRITICAL/FATAL
  - 九宫格错误分类（坎1-离9）：按认知维度归因错误
  - 自动回退策略：降级→重试→混沌海→熔断
  - 十二神门禁集成：错误影响门禁裁决
  - 错误恢复管道：自动修复常见错误
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
import threading
import time
import traceback


# ============================================================================
# 错误分级
# ============================================================================

class ErrorLevel(Enum):
    """错误严重级别"""
    DEBUG = 0      # 调试信息，不影响运行
    INFO = 1       # 信息性，记录但不处理
    WARNING = 2    # 警告，可能影响但不中断
    ERROR = 3      # 错误，需要处理但可恢复
    CRITICAL = 4   # 严重错误，部分功能不可用
    FATAL = 5      # 致命错误，系统不可用

    @property
    def is_recoverable(self) -> bool:
        """是否可恢复"""
        return self.value <= 3

    @property
    def requires_immediate_action(self) -> bool:
        """是否需要立即处理"""
        return self.value >= 4


# ============================================================================
# 九宫格错误分类
# ============================================================================

class NinePalaceErrorCategory(Enum):
    """九宫格错误分类 — 按认知维度归因

    九宫→五行→错误类型映射：
      坎1(水): 数据源错误 — 输入不可信、数据污染
      坤2(土): 存储错误   — 持久化失败、知识丢失
      震3(木): 初始化错误 — 启动失败、模块加载异常
      巽4(木): 通信错误   — 网络超时、协议不匹配
      中5(土): 核心错误   — 逻辑缺陷、推理失败
      乾6(金): 权限错误   — 认证失败、越权访问
      兑7(金): 输出错误   — 序列化失败、格式错误
      艮8(土): 边界错误   — 输入校验失败、越界
      离9(火): 渲染错误   — 可视化失败、展示异常
    """
    KAN1 = ("坎一", "水", "数据源错误", "输入不可信、数据污染")
    KUN2 = ("坤二", "土", "存储错误", "持久化失败、知识丢失")
    ZHEN3 = ("震三", "木", "初始化错误", "启动失败、模块加载异常")
    XUN4 = ("巽四", "木", "通信错误", "网络超时、协议不匹配")
    ZHONG5 = ("中五", "土", "核心错误", "逻辑缺陷、推理失败")
    QIAN6 = ("乾六", "金", "权限错误", "认证失败、越权访问")
    DUI7 = ("兑七", "金", "输出错误", "序列化失败、格式错误")
    GEN8 = ("艮八", "土", "边界错误", "输入校验失败、越界")
    LI9 = ("离九", "火", "渲染错误", "可视化失败、展示异常")

    @property
    def palace_name(self) -> str:
        return self.value[0]

    @property
    def element(self) -> str:
        return self.value[1]

    @property
    def category_name(self) -> str:
        return self.value[2]

    @property
    def description(self) -> str:
        return self.value[3]

    @classmethod
    def classify(cls, error: Exception) -> "NinePalaceErrorCategory":
        """根据异常类型自动分类到九宫格"""
        error_type = type(error).__name__
        error_msg = str(error).lower()

        # 数据源错误 → 坎1
        if any(k in error_msg for k in ["data", "input", "parse", "decode", "corrupt"]):
            return cls.KAN1
        if error_type in ("ValueError", "KeyError", "IndexError"):
            return cls.KAN1

        # 存储错误 → 坤2
        if any(k in error_msg for k in ["storage", "disk", "write", "save", "persist", "io"]):
            return cls.KUN2
        if error_type in ("IOError", "OSError", "FileNotFoundError"):
            return cls.KUN2

        # 初始化错误 → 震3
        if any(k in error_msg for k in ["init", "import", "module", "load", "start"]):
            return cls.ZHEN3
        if error_type in ("ImportError", "ModuleNotFoundError"):
            return cls.ZHEN3

        # 通信错误 → 巽4
        if any(k in error_msg for k in ["network", "timeout", "connect", "socket", "http", "request"]):
            return cls.XUN4
        if error_type in ("ConnectionError", "TimeoutError"):
            return cls.XUN4

        # 权限错误 → 乾6
        if any(k in error_msg for k in ["permission", "auth", "denied", "forbidden", "unauthorized"]):
            return cls.QIAN6
        if error_type in ("PermissionError",):
            return cls.QIAN6

        # 输出错误 → 兑7
        if any(k in error_msg for k in ["serialize", "format", "encode", "json", "marshal"]):
            return cls.DUI7
        if error_type in ("TypeError", "AttributeError"):
            return cls.DUI7

        # 边界错误 → 艮8
        if any(k in error_msg for k in ["bound", "range", "overflow", "limit", "validate"]):
            return cls.GEN8
        if error_type in ("AssertionError",):
            return cls.GEN8

        # 渲染错误 → 离9
        if any(k in error_msg for k in ["render", "display", "visual", "draw", "paint"]):
            return cls.LI9

        # 默认：核心错误 → 中5
        return cls.ZHONG5


# ============================================================================
# 回退策略
# ============================================================================

class FallbackStrategy(Enum):
    """自动回退策略"""
    DEGRADE = "degrade"       # 降级：使用简化版本
    RETRY = "retry"           # 重试：指数退避重试
    CHAOS_SEA = "chaos_sea"   # 混沌海：标记为存疑
    CIRCUIT_BREAK = "break"   # 熔断：停止该路径
    SKIP = "skip"             # 跳过：忽略该步骤
    DEFAULT = "default"       # 默认值：返回安全默认值


# ============================================================================
# 错误记录
# ============================================================================

@dataclass
class ErrorRecord:
    """错误记录"""
    error_id: str
    level: ErrorLevel
    category: NinePalaceErrorCategory
    message: str
    exception_type: str
    traceback: str
    timestamp: float = field(default_factory=time.time)
    module: str = ""
    function: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_attempted: bool = False
    recovery_success: bool = False
    fallback_used: Optional[FallbackStrategy] = None
    gate_impact: Optional[Dict[str, Any]] = None  # 对门禁的影响

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "level": self.level.name,
            "category": self.category.palace_name,
            "category_name": self.category.category_name,
            "element": self.category.element,
            "message": self.message,
            "exception_type": self.exception_type,
            "module": self.module,
            "function": self.function,
            "recovery_success": self.recovery_success,
            "fallback": self.fallback_used.value if self.fallback_used else None,
            "timestamp": self.timestamp,
        }


# ============================================================================
# 分级错误处理器
# ============================================================================

class ErrorHandler:
    """分级错误处理器 v2.31.0

    五级错误分级 + 九宫格分类 + 自动回退策略 + 十二神门禁集成。
    """

    _instance: Optional["ErrorHandler"] = None
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

        self._error_log: List[ErrorRecord] = []
        self._error_counters: Dict[ErrorLevel, int] = {
            level: 0 for level in ErrorLevel
        }
        self._category_counters: Dict[NinePalaceErrorCategory, int] = {
            cat: 0 for cat in NinePalaceErrorCategory
        }
        self._circuit_breakers: Dict[str, int] = {}  # 路径→连续失败次数
        self._circuit_breaker_threshold: int = 5
        self._error_counter = 0
        self._recovery_handlers: Dict[str, Callable] = {}

    # ── 错误捕获与分级 ──────────────────────────────────────────────

    def handle(
        self,
        error: Exception,
        level: Optional[ErrorLevel] = None,
        module: str = "",
        function: str = "",
        context: Optional[Dict] = None,
        auto_recover: bool = True,
    ) -> ErrorRecord:
        """处理错误：分级→分类→记录→回退

        Args:
            error: 异常对象
            level: 错误级别（None则自动判断）
            module: 发生模块
            function: 发生函数
            context: 上下文信息
            auto_recover: 是否自动尝试恢复

        Returns:
            ErrorRecord 错误记录
        """
        self._error_counter += 1

        # 自动分级
        if level is None:
            level = self._classify_level(error)

        # 九宫格分类
        category = NinePalaceErrorCategory.classify(error)

        # 创建记录
        record = ErrorRecord(
            error_id=f"err_{self._error_counter}_{int(time.time())}",
            level=level,
            category=category,
            message=str(error)[:500],
            exception_type=type(error).__name__,
            traceback=traceback.format_exc()[:2000],
            module=module,
            function=function,
            context=context or {},
        )

        # 更新计数器
        self._error_counters[level] += 1
        self._category_counters[category] += 1
        self._error_log.append(record)

        # 裁剪日志
        if len(self._error_log) > 1000:
            self._error_log = self._error_log[-1000:]

        # 自动恢复
        if auto_recover and level.is_recoverable:
            record.recovery_attempted = True
            record.recovery_success = self._attempt_recovery(record)

        # 严重错误触发熔断检查
        if not level.is_recoverable:
            self._check_circuit_breaker(record)

        # 门禁影响评估
        record.gate_impact = self._assess_gate_impact(record)

        return record

    def _classify_level(self, error: Exception) -> ErrorLevel:
        """根据异常类型自动分级"""
        error_type = type(error).__name__

        fatal_types = {"SystemExit", "MemoryError", "KeyboardInterrupt"}
        critical_types = {"RuntimeError", "RecursionError"}
        warning_types = {"UserWarning", "DeprecationWarning", "FutureWarning"}

        if error_type in fatal_types:
            return ErrorLevel.FATAL
        if error_type in critical_types:
            return ErrorLevel.CRITICAL
        if error_type in warning_types:
            return ErrorLevel.WARNING
        if isinstance(error, (ValueError, TypeError, KeyError, AttributeError)):
            return ErrorLevel.ERROR

        return ErrorLevel.ERROR

    # ── 自动回退策略 ──────────────────────────────────────────────────

    def _attempt_recovery(self, record: ErrorRecord) -> bool:
        """尝试自动恢复"""
        strategies = self._get_recovery_strategies(record)

        for strategy in strategies:
            try:
                if strategy == FallbackStrategy.DEFAULT:
                    record.fallback_used = strategy
                    return True
                elif strategy == FallbackStrategy.DEGRADE:
                    record.fallback_used = strategy
                    return True
                elif strategy == FallbackStrategy.SKIP:
                    record.fallback_used = strategy
                    return True
                elif strategy == FallbackStrategy.CHAOS_SEA:
                    self._send_to_chaos_sea(record)
                    record.fallback_used = strategy
                    return True
                elif strategy == FallbackStrategy.RETRY:
                    # 重试已由调用方处理
                    record.fallback_used = strategy
                    return True
                elif strategy == FallbackStrategy.CIRCUIT_BREAK:
                    self._activate_circuit_breaker(record)
                    record.fallback_used = strategy
                    return False
            except Exception:
                continue

        return False

    def _get_recovery_strategies(
        self, record: ErrorRecord
    ) -> List[FallbackStrategy]:
        """根据错误类型获取回退策略列表"""
        cat = record.category

        strategies = {
            NinePalaceErrorCategory.KAN1: [  # 数据源错误
                FallbackStrategy.DEFAULT, FallbackStrategy.SKIP,
                FallbackStrategy.CHAOS_SEA,
            ],
            NinePalaceErrorCategory.KUN2: [  # 存储错误
                FallbackStrategy.RETRY, FallbackStrategy.DEGRADE,
                FallbackStrategy.CHAOS_SEA,
            ],
            NinePalaceErrorCategory.ZHEN3: [  # 初始化错误
                FallbackStrategy.RETRY, FallbackStrategy.DEGRADE,
                FallbackStrategy.CIRCUIT_BREAK,
            ],
            NinePalaceErrorCategory.XUN4: [  # 通信错误
                FallbackStrategy.RETRY, FallbackStrategy.DEGRADE,
                FallbackStrategy.CHAOS_SEA,
            ],
            NinePalaceErrorCategory.ZHONG5: [  # 核心错误
                FallbackStrategy.CHAOS_SEA, FallbackStrategy.CIRCUIT_BREAK,
            ],
            NinePalaceErrorCategory.QIAN6: [  # 权限错误
                FallbackStrategy.DEFAULT, FallbackStrategy.CIRCUIT_BREAK,
            ],
            NinePalaceErrorCategory.DUI7: [  # 输出错误
                FallbackStrategy.DEFAULT, FallbackStrategy.DEGRADE,
                FallbackStrategy.CHAOS_SEA,
            ],
            NinePalaceErrorCategory.GEN8: [  # 边界错误
                FallbackStrategy.DEFAULT, FallbackStrategy.SKIP,
            ],
            NinePalaceErrorCategory.LI9: [  # 渲染错误
                FallbackStrategy.DEGRADE, FallbackStrategy.SKIP,
            ],
        }

        return strategies.get(cat, [FallbackStrategy.CHAOS_SEA])

    # ── 熔断器 ────────────────────────────────────────────────────────

    def _check_circuit_breaker(self, record: ErrorRecord) -> None:
        """检查是否需要熔断"""
        path = f"{record.module}.{record.function}"
        self._circuit_breakers[path] = self._circuit_breakers.get(path, 0) + 1

        if self._circuit_breakers[path] >= self._circuit_breaker_threshold:
            self._activate_circuit_breaker(record)

    def _activate_circuit_breaker(self, record: ErrorRecord) -> None:
        """激活熔断器"""
        path = f"{record.module}.{record.function}"
        self._circuit_breakers[path] = self._circuit_breaker_threshold + 1

    def is_circuit_broken(self, module: str, function: str = "") -> bool:
        """检查路径是否已熔断"""
        path = f"{module}.{function}" if function else module
        return self._circuit_breakers.get(path, 0) > self._circuit_breaker_threshold

    def reset_circuit_breaker(self, module: str, function: str = "") -> None:
        """重置熔断器"""
        path = f"{module}.{function}" if function else module
        self._circuit_breakers.pop(path, None)

    # ── 混沌海 ────────────────────────────────────────────────────────

    def _send_to_chaos_sea(self, record: ErrorRecord) -> None:
        """将错误发送到混沌海存疑"""
        try:
            from .hundun_sea import HundunSea
            sea = HundunSea()
            sea.explore(
                features={
                    "error_id": record.error_id,
                    "category": record.category.palace_name,
                    "level": record.level.name,
                },
                confidence=0.3,
                active_route=f"error_{record.error_id}",
            )
        except Exception:
            pass

    # ── 门禁影响评估 ──────────────────────────────────────────────────

    def _assess_gate_impact(self, record: ErrorRecord) -> Dict[str, Any]:
        """评估错误对十二神门禁的影响"""
        cat = record.category

        # 九宫格→十二神门禁影响映射
        gate_impact_map = {
            NinePalaceErrorCategory.KAN1: ["坎一·水", "比肩·劫财(木)", "数据源可信度下降"],
            NinePalaceErrorCategory.KUN2: ["坤二·土", "正财·偏财(土)", "知识存储可靠性下降"],
            NinePalaceErrorCategory.ZHEN3: ["震三·木", "比肩·劫财(木)", "系统架构稳定性下降"],
            NinePalaceErrorCategory.XUN4: ["巽四·木", "比肩·劫财(木)", "模块间通信受阻"],
            NinePalaceErrorCategory.ZHONG5: ["中五·土", "正官·七杀(金)", "核心逻辑可信度下降"],
            NinePalaceErrorCategory.QIAN6: ["乾六·金", "太极·元辰", "系统自指涉能力受损"],
            NinePalaceErrorCategory.DUI7: ["兑七·金", "食神·伤官(火)", "输出质量下降"],
            NinePalaceErrorCategory.GEN8: ["艮八·土", "正印·偏印(水)", "配置边界受损"],
            NinePalaceErrorCategory.LI9: ["离九·火", "食神·伤官(火)", "展示质量下降"],
        }

        impact = gate_impact_map.get(cat, ["未知", "未知", "未知影响"])
        return {
            "palace": impact[0],
            "affected_god": impact[1],
            "impact_description": impact[2],
            "severity": record.level.name,
        }

    # ── 安全执行包装器 ──────────────────────────────────────────────

    def safe_execute(
        self,
        func: Callable,
        *args,
        module: str = "",
        function: str = "",
        default: Any = None,
        max_retries: int = 3,
        **kwargs,
    ) -> Tuple[Any, Optional[ErrorRecord]]:
        """安全执行函数，自动错误处理和回退

        Args:
            func: 要执行的函数
            *args: 位置参数
            module: 模块名
            function: 函数名
            default: 失败时的默认返回值
            max_retries: 最大重试次数
            **kwargs: 关键字参数

        Returns:
            (结果, 错误记录或None)
        """
        if self.is_circuit_broken(module, function):
            return default, None

        last_error = None
        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                self.reset_circuit_breaker(module, function)
                return result, None
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = 2 ** attempt * 0.1  # 指数退避
                    time.sleep(wait)
                    continue

        record = self.handle(
            last_error,
            module=module,
            function=function,
            auto_recover=True,
        )
        return default, record

    # ── 统计与查询 ──────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        return {
            "total_errors": sum(self._error_counters.values()),
            "by_level": {k.name: v for k, v in self._error_counters.items()},
            "by_category": {k.palace_name: v for k, v in self._category_counters.items()},
            "circuit_broken": len([
                p for p, c in self._circuit_breakers.items()
                if c > self._circuit_breaker_threshold
            ]),
            "recovery_rate": round(
                sum(1 for r in self._error_log[-100:] if r.recovery_success)
                / max(1, sum(1 for r in self._error_log[-100:] if r.recovery_attempted)),
                3,
            ),
        }

    def get_recent_errors(self, limit: int = 20) -> List[Dict]:
        """获取最近的错误记录"""
        return [r.to_dict() for r in self._error_log[-limit:]]

    def get_errors_by_category(
        self, category: NinePalaceErrorCategory
    ) -> List[Dict]:
        """按九宫格分类获取错误"""
        return [
            r.to_dict() for r in self._error_log
            if r.category == category
        ][-50:]

    def get_gate_impact_summary(self) -> Dict[str, Any]:
        """获取门禁影响摘要"""
        impacts = {}
        for r in self._error_log[-100:]:
            if r.gate_impact:
                god = r.gate_impact.get("affected_god", "unknown")
                if god not in impacts:
                    impacts[god] = {"count": 0, "severities": {}}
                impacts[god]["count"] += 1
                sev = r.level.name
                impacts[god]["severities"][sev] = impacts[god]["severities"].get(sev, 0) + 1
        return impacts

    def reset(self) -> None:
        """重置错误处理器"""
        self._error_log.clear()
        self._error_counters = {level: 0 for level in ErrorLevel}
        self._category_counters = {cat: 0 for cat in NinePalaceErrorCategory}
        self._circuit_breakers.clear()
        self._error_counter = 0


# ============================================================================
# 全局单例
# ============================================================================

_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """获取错误处理器单例"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def reset_error_handler() -> None:
    """重置错误处理器"""
    global _error_handler
    _error_handler = None
    ErrorHandler._instance = None


__all__ = [
    "ErrorLevel",
    "NinePalaceErrorCategory",
    "FallbackStrategy",
    "ErrorRecord",
    "ErrorHandler",
    "get_error_handler",
    "reset_error_handler",
]