"""
lens_zoom.py — 透镜缩放引擎 v2.24.0
===========================================
道曰："大曰逝，逝曰远，远曰反。"

变焦（Lens Zoom）：
- 广角↔长焦的动态拓扑调节
- 认知分辨率随负载自适应缩放
- 推测解码节奏调度（DSpark 半自回归+置信度调度）

核心模块：
  1. LensZoomEngine  — 透镜缩放引擎
  2. LoadBalancer    — 负载均衡器（EPLB/LPLB）
  3. RhythmScheduler — 推测解码节奏调度器（DeepSpec）
  4. ZoomRing        — 变焦环状态机

映射关系：
  - 广角（Wide）→ 全并行，低精度，高吞吐
  - 标准（Normal）→ 平衡模式
  - 长焦（Tele）→ 半自回归，高精度，低吞吐
  - 推测解码变焦 → draft(广角捕获) ↔ target(长焦验证)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import time

from .tbce_unit import TBCECoordinates, CognitiveUnit, GateState


# ============================================================================
# 变焦模式
# ============================================================================

class ZoomMode(Enum):
    """变焦模式"""
    WIDE = "wide"        # 广角：全并行，低精度，高吞吐
    NORMAL = "normal"    # 标准：平衡模式
    TELE = "tele"        # 长焦：半自回归，高精度，低吞吐
    SPECULATIVE = "speculative"  # 推测解码：draft广角 ↔ target长焦

    @property
    def label(self) -> str:
        labels = {
            ZoomMode.WIDE: "广角·全并行",
            ZoomMode.NORMAL: "标准·平衡",
            ZoomMode.TELE: "长焦·半自回归",
            ZoomMode.SPECULATIVE: "推测解码·变焦环",
        }
        return labels[self]

    @property
    def precision(self) -> float:
        """精度系数 [0, 1]"""
        return {
            ZoomMode.WIDE: 0.4,
            ZoomMode.NORMAL: 0.7,
            ZoomMode.TELE: 0.95,
            ZoomMode.SPECULATIVE: 0.85,
        }[self]

    @property
    def throughput(self) -> float:
        """吞吐系数 [0, 1]"""
        return {
            ZoomMode.WIDE: 0.95,
            ZoomMode.NORMAL: 0.7,
            ZoomMode.TELE: 0.3,
            ZoomMode.SPECULATIVE: 0.6,
        }[self]


# ============================================================================
# 变焦环状态
# ============================================================================

@dataclass
class ZoomState:
    """变焦环当前状态"""
    mode: ZoomMode = ZoomMode.NORMAL
    focal_length: float = 0.5    # 焦距 [0, 1]，0=广角，1=长焦
    load_level: float = 0.0      # 负载水平 [0, 1]
    burst_size: int = 2          # 推测解码批大小
    confidence_threshold: float = 0.7  # 置信度阈值
    precision: float = 0.7       # 当前精度
    throughput: float = 0.7      # 当前吞吐
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "focal_length": round(self.focal_length, 3),
            "load_level": round(self.load_level, 3),
            "burst_size": self.burst_size,
            "confidence_threshold": round(self.confidence_threshold, 3),
            "precision": round(self.precision, 3),
            "throughput": round(self.throughput, 3),
        }


# ============================================================================
# 透镜缩放引擎
# ============================================================================

class LensZoomEngine:
    """透镜缩放引擎 —— 动态调整认知分辨率

    道曰："大曰逝，逝曰远，远曰反。"

    变焦环：
    - 广角（Wide）：全并行，低精度，高吞吐 → 适合探索/初步扫描
    - 标准（Normal）：平衡模式 → 适合常规推理
    - 长焦（Tele）：半自回归，高精度，低吞吐 → 适合关键决策/验证
    - 推测解码（Speculative）：draft广角 + target长焦 → 5-10x速度

    自动缩放策略：
    - 负载高 → 自动缩放到广角（降低精度，提高吞吐）
    - 负载低 → 自动缩放到长焦（提高精度，降低吞吐）
    - 置信度低 → 切换到长焦（需要更多验证）
    - 置信度高 → 切换到广角（可以快速通过）
    """

    # 缩放阈值
    LOAD_HIGH_THRESHOLD = 0.7    # 负载 > 0.7 → 广角
    LOAD_LOW_THRESHOLD = 0.3     # 负载 < 0.3 → 长焦
    CONFIDENCE_HIGH_THRESHOLD = 0.8  # 置信度 > 0.8 → 广角
    CONFIDENCE_LOW_THRESHOLD = 0.4   # 置信度 < 0.4 → 长焦

    def __init__(self, initial_mode: ZoomMode = ZoomMode.NORMAL):
        self.state = ZoomState(mode=initial_mode)
        self._zoom_log: List[ZoomState] = []

    def auto_zoom(
        self,
        load_level: float,
        confidence: float = 0.5,
        unit_count: int = 1,
    ) -> ZoomState:
        """自动变焦：根据负载和置信度动态调整

        Args:
            load_level: 当前负载水平 [0, 1]
            confidence: 当前置信度 [0, 1]
            unit_count: 待处理单元数量

        Returns:
            新的变焦状态
        """
        old_mode = self.state.mode

        # 负载驱动缩放
        if load_level > self.LOAD_HIGH_THRESHOLD:
            new_mode = ZoomMode.WIDE
            new_focal = max(0.0, self.state.focal_length - 0.2)
        elif load_level < self.LOAD_LOW_THRESHOLD:
            new_mode = ZoomMode.TELE
            new_focal = min(1.0, self.state.focal_length + 0.2)
        else:
            # 置信度驱动缩放
            if confidence > self.CONFIDENCE_HIGH_THRESHOLD:
                new_mode = ZoomMode.WIDE
                new_focal = max(0.0, self.state.focal_length - 0.1)
            elif confidence < self.CONFIDENCE_LOW_THRESHOLD:
                new_mode = ZoomMode.TELE
                new_focal = min(1.0, self.state.focal_length + 0.1)
            else:
                new_mode = ZoomMode.NORMAL
                new_focal = self.state.focal_length

        # 推测解码模式选择
        if load_level > 0.5 and confidence > 0.5:
            new_mode = ZoomMode.SPECULATIVE
            new_focal = 0.5  # 推测解码固定在中焦距

        # 更新状态
        self.state = ZoomState(
            mode=new_mode,
            focal_length=new_focal,
            load_level=load_level,
            precision=new_mode.precision,
            throughput=new_mode.throughput,
            burst_size=self._calc_burst_size(new_mode, unit_count),
            confidence_threshold=self._calc_confidence_threshold(new_mode),
        )

        if old_mode != new_mode:
            self._zoom_log.append(self.state)

        return self.state

    def _calc_burst_size(self, mode: ZoomMode, unit_count: int) -> int:
        """计算推测解码批大小"""
        if mode == ZoomMode.SPECULATIVE:
            # 推测解码：2-6 token动态窗口
            if unit_count <= 2:
                return 2
            elif unit_count <= 4:
                return 4
            else:
                return 6
        elif mode == ZoomMode.WIDE:
            return min(8, unit_count)
        elif mode == ZoomMode.TELE:
            return 1
        else:
            return 2

    def _calc_confidence_threshold(self, mode: ZoomMode) -> float:
        """计算置信度阈值"""
        if mode == ZoomMode.TELE:
            return 0.9   # 长焦：高置信度要求
        elif mode == ZoomMode.WIDE:
            return 0.5   # 广角：低置信度要求
        elif mode == ZoomMode.SPECULATIVE:
            return 0.7   # 推测解码：中等置信度
        else:
            return 0.7

    def zoom_to(self, mode: ZoomMode) -> ZoomState:
        """手动变焦到指定模式"""
        self.state = ZoomState(
            mode=mode,
            focal_length=0.0 if mode == ZoomMode.WIDE else (1.0 if mode == ZoomMode.TELE else 0.5),
            precision=mode.precision,
            throughput=mode.throughput,
            burst_size=self._calc_burst_size(mode, 1),
            confidence_threshold=self._calc_confidence_threshold(mode),
        )
        self._zoom_log.append(self.state)
        return self.state

    def get_zoom_history(self) -> List[ZoomState]:
        """获取变焦历史"""
        return self._zoom_log

    def get_statistics(self) -> Dict[str, Any]:
        """获取变焦统计"""
        if not self._zoom_log:
            return {"current": self.state.to_dict(), "transitions": 0}
        return {
            "current": self.state.to_dict(),
            "transitions": len(self._zoom_log),
            "modes": {
                m.value: sum(1 for s in self._zoom_log if s.mode == m)
                for m in ZoomMode
            },
        }


# ============================================================================
# 负载均衡器（EPLB/LPLB 映射）
# ============================================================================

@dataclass
class LoadMetric:
    """负载度量"""
    node_id: str
    load: float          # 当前负载 [0, 1]
    capacity: float      # 容量 [0, 1]
    queue_depth: int     # 队列深度
    processing_rate: float  # 处理速率 (units/s)
    assigned: int = 0    # 已分配单元数

@dataclass
class BalanceResult:
    """负载均衡结果"""
    assignments: Dict[str, int]   # node_id → assigned_count
    total_units: int
    imbalance: float              # 不平衡度 [0, 1]，0=完美均衡
    strategy: str
    timestamp: float = field(default_factory=time.time)


class LoadBalancer:
    """负载均衡器 —— EPLB/LPLB 认知映射

    EPLB（Expert-Parallel Load Balancing）：
    - 专家级负载均衡
    - 动态权重调整

    LPLB（Layer-Parallel Load Balancing）：
    - 层级负载均衡
    - 认知层间负载分配

    核心策略：
    1. 加权最小连接：负载低的节点优先
    2. 容量感知：不超过节点容量
    3. 动态再平衡：定期检查并迁移
    """

    # 均衡策略
    STRATEGY_WEIGHTED_LEAST = "weighted_least_connections"
    STRATEGY_ROUND_ROBIN = "round_robin"
    STRATEGY_CAPACITY_AWARE = "capacity_aware"
    STRATEGY_COGNITIVE_LAYER = "cognitive_layer"  # 认知层感知

    def __init__(self, strategy: str = STRATEGY_WEIGHTED_LEAST):
        self.strategy = strategy
        self._nodes: Dict[str, LoadMetric] = {}
        self._balance_log: List[BalanceResult] = []

    def register_node(
        self,
        node_id: str,
        capacity: float = 1.0,
        processing_rate: float = 1.0,
    ) -> None:
        """注册均衡节点"""
        self._nodes[node_id] = LoadMetric(
            node_id=node_id,
            load=0.0,
            capacity=capacity,
            queue_depth=0,
            processing_rate=processing_rate,
        )

    def update_node_load(self, node_id: str, load: float, queue_depth: int = 0) -> None:
        """更新节点负载"""
        if node_id in self._nodes:
            self._nodes[node_id].load = min(1.0, max(0.0, load))
            self._nodes[node_id].queue_depth = queue_depth

    def balance(
        self,
        units: List[CognitiveUnit],
        override_strategy: Optional[str] = None,
    ) -> BalanceResult:
        """负载均衡分配

        Args:
            units: 待分配的认知单元
            override_strategy: 覆盖策略

        Returns:
            均衡结果
        """
        strategy = override_strategy or self.strategy
        if not self._nodes:
            return BalanceResult(assignments={}, total_units=len(units), imbalance=1.0, strategy=strategy)

        assignments: Dict[str, int] = {nid: 0 for nid in self._nodes}

        if strategy == self.STRATEGY_ROUND_ROBIN:
            assignments = self._round_robin(units)
        elif strategy == self.STRATEGY_CAPACITY_AWARE:
            assignments = self._capacity_aware(units)
        elif strategy == self.STRATEGY_COGNITIVE_LAYER:
            assignments = self._cognitive_layer_aware(units)
        else:
            assignments = self._weighted_least(units)

        # 更新已分配计数
        for nid, count in assignments.items():
            if nid in self._nodes:
                self._nodes[nid].assigned = count

        # 计算不平衡度
        imbalance = self._calc_imbalance(assignments)

        result = BalanceResult(
            assignments=assignments,
            total_units=len(units),
            imbalance=imbalance,
            strategy=strategy,
        )
        self._balance_log.append(result)
        return result

    def _weighted_least(self, units: List[CognitiveUnit]) -> Dict[str, int]:
        """加权最小连接算法"""
        assignments = {nid: 0 for nid in self._nodes}
        for unit in units:
            # 选择负载最低的节点
            best_node = min(
                self._nodes.keys(),
                key=lambda nid: (
                    self._nodes[nid].load / max(0.01, self._nodes[nid].capacity),
                    assignments[nid],
                ),
            )
            assignments[best_node] += 1
        return assignments

    def _round_robin(self, units: List[CognitiveUnit]) -> Dict[str, int]:
        """轮询分配"""
        assignments = {nid: 0 for nid in self._nodes}
        node_ids = list(self._nodes.keys())
        for i, unit in enumerate(units):
            nid = node_ids[i % len(node_ids)]
            assignments[nid] += 1
        return assignments

    def _capacity_aware(self, units: List[CognitiveUnit]) -> Dict[str, int]:
        """容量感知分配"""
        assignments = {nid: 0 for nid in self._nodes}
        # 按容量比例分配
        total_capacity = sum(n.capacity for n in self._nodes.values())
        if total_capacity == 0:
            return assignments

        remaining = len(units)
        node_ids = sorted(self._nodes.keys(), key=lambda nid: -self._nodes[nid].capacity)
        for nid in node_ids:
            node = self._nodes[nid]
            share = int(remaining * node.capacity / total_capacity)
            assignments[nid] = min(share, remaining)
            remaining -= assignments[nid]
            total_capacity -= node.capacity

        # 剩余分配给第一个节点
        if remaining > 0 and node_ids:
            assignments[node_ids[0]] += remaining

        return assignments

    def _cognitive_layer_aware(self, units: List[CognitiveUnit]) -> Dict[str, int]:
        """认知层感知分配：高层级单元优先分配高容量节点"""
        assignments = {nid: 0 for nid in self._nodes}
        sorted_nodes = sorted(
            self._nodes.keys(),
            key=lambda nid: -self._nodes[nid].capacity,
        )
        sorted_units = sorted(units, key=lambda u: -u.cognitive_layer)

        for unit in sorted_units:
            # 高层级 → 高容量节点
            layer_ratio = unit.cognitive_layer / 8.0
            node_idx = int((1.0 - layer_ratio) * (len(sorted_nodes) - 1))
            nid = sorted_nodes[min(node_idx, len(sorted_nodes) - 1)]
            assignments[nid] += 1

        return assignments

    def _calc_imbalance(self, assignments: Dict[str, int]) -> float:
        """计算不平衡度 (0=完美均衡)"""
        counts = list(assignments.values())
        if not counts or max(counts) == 0:
            return 0.0 if not counts else 1.0
        return (max(counts) - min(counts)) / max(1, max(counts))

    def get_node_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取节点统计"""
        return {
            nid: {
                "load": node.load,
                "capacity": node.capacity,
                "queue_depth": node.queue_depth,
                "assigned": node.assigned,
                "utilization": node.load / max(0.01, node.capacity),
            }
            for nid, node in self._nodes.items()
        }

    def get_balance_history(self) -> List[BalanceResult]:
        return self._balance_log


# ============================================================================
# 推测解码节奏调度器（DeepSpec）
# ============================================================================

@dataclass
class RhythmSlot:
    """节奏槽位"""
    slot_id: int
    confidence: float = 0.0
    accepted: bool = False
    draft_time_ms: float = 0.0
    verify_time_ms: float = 0.0

@dataclass
class RhythmResult:
    """节奏调度结果"""
    total_slots: int
    accepted_slots: int
    acceptance_rate: float
    speedup_ratio: float
    avg_confidence: float
    slots: List[RhythmSlot]
    timestamp: float = field(default_factory=time.time)


class RhythmScheduler:
    """推测解码节奏调度器 —— DeepSpec/DSpark 映射

    DSpark 核心创新：
    1. 半自回归生成：并行骨干(DFlash) + 轻量非线性纠缠头
    2. 置信度调度验证：STS非线性纠缠温度缩放 + 硬件感知前缀调度

    节奏调度三阶段：
    1. 嗅探（Sniff）：粗选候选 token，置信度快速评估
    2. 推测（Speculate）：半自回归生成，Markov/RNN 纠缠头
    3. 验证（Verify）：目标模型验证，接受/拒绝
    """

    # 默认参数
    DEFAULT_BURST_SIZE = 4       # 推测解码窗口
    DEFAULT_CONFIDENCE_THRESHOLD = 0.7
    MAX_BURST_SIZE = 6
    MIN_BURST_SIZE = 2

    # 加速比目标
    TARGET_SPEEDUP = 5.0         # 5x加速目标
    MIN_SPEEDUP = 2.0

    def __init__(
        self,
        burst_size: int = DEFAULT_BURST_SIZE,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ):
        self.burst_size = burst_size
        self.confidence_threshold = confidence_threshold
        self._rhythm_log: List[RhythmResult] = []

    def schedule(
        self,
        candidates: List[Dict[str, Any]],
        confidence_scores: Optional[List[float]] = None,
    ) -> RhythmResult:
        """推测解码节奏调度

        Args:
            candidates: 候选 token 列表
            confidence_scores: 置信度分数列表

        Returns:
            节奏调度结果
        """
        total = len(candidates)
        if confidence_scores is None:
            confidence_scores = self._estimate_confidence(candidates)

        # 动态调整批大小
        adjusted_burst = self._adjust_burst_size(
            confidence_scores[:self.burst_size]
        )

        slots = []
        accepted = 0

        for i in range(min(adjusted_burst, total)):
            conf = confidence_scores[i] if i < len(confidence_scores) else 0.5
            slot = RhythmSlot(
                slot_id=i,
                confidence=conf,
                accepted=conf >= self.confidence_threshold,
                draft_time_ms=0.5,   # draft 模型时间
                verify_time_ms=1.0,  # target 模型时间
            )
            if slot.accepted:
                accepted += 1
            slots.append(slot)

        # 加速比计算
        acceptance_rate = accepted / max(1, total)
        # 理论加速比 = target_time / (draft_time + verify_time * acceptance_rate)
        # 简化为基于接受率的加速比
        speedup = self._calc_speedup(acceptance_rate, adjusted_burst)

        result = RhythmResult(
            total_slots=total,
            accepted_slots=accepted,
            acceptance_rate=acceptance_rate,
            speedup_ratio=speedup,
            avg_confidence=sum(s.confidence for s in slots) / max(1, len(slots)),
            slots=slots,
        )
        self._rhythm_log.append(result)
        return result

    def _estimate_confidence(self, candidates: List[Dict]) -> List[float]:
        """估算置信度分数"""
        scores = []
        for c in candidates:
            if "confidence" in c:
                scores.append(c["confidence"])
            elif "score" in c:
                scores.append(c["score"])
            elif "probability" in c:
                scores.append(c["probability"])
            else:
                scores.append(0.5)
        return scores

    def _adjust_burst_size(self, confidence_scores: List[float]) -> int:
        """动态调整批大小：置信度高 → 更大窗口"""
        if not confidence_scores:
            return self.burst_size

        avg_conf = sum(confidence_scores) / len(confidence_scores)

        if avg_conf > 0.85:
            return min(self.MAX_BURST_SIZE, self.burst_size + 2)
        elif avg_conf < 0.5:
            return max(self.MIN_BURST_SIZE, self.burst_size - 1)
        return self.burst_size

    def _calc_speedup(self, acceptance_rate: float, burst_size: int) -> float:
        """计算推测解码加速比

        理论公式：
        speedup = burst_size / (1 + (1 - acceptance_rate) * burst_size)
        """
        if acceptance_rate >= 1.0:
            return float(burst_size)
        if acceptance_rate <= 0.0:
            return 1.0
        return burst_size / (1.0 + (1.0 - acceptance_rate) * burst_size)

    def get_statistics(self) -> Dict[str, Any]:
        """获取节奏统计"""
        if not self._rhythm_log:
            return {}
        total = len(self._rhythm_log)
        avg_speedup = sum(r.speedup_ratio for r in self._rhythm_log) / total
        avg_acceptance = sum(r.acceptance_rate for r in self._rhythm_log) / total
        return {
            "total_schedules": total,
            "avg_speedup": round(avg_speedup, 3),
            "avg_acceptance_rate": round(avg_acceptance, 3),
            "max_speedup": round(max(r.speedup_ratio for r in self._rhythm_log), 3),
        }

    def set_burst_size(self, size: int) -> None:
        self.burst_size = min(self.MAX_BURST_SIZE, max(self.MIN_BURST_SIZE, size))


# ============================================================================
# 变焦环状态机
# ============================================================================

class ZoomRing:
    """变焦环状态机 —— 广角↔长焦的动态切换

    状态转移：
    - WIDE → NORMAL: 负载降低，需要更多精度
    - WIDE → SPECULATIVE: 中等负载，推测解码
    - NORMAL → WIDE: 负载升高，需要快速通过
    - NORMAL → TELE: 需要高精度决策
    - TELE → NORMAL: 精度需求降低
    - SPECULATIVE → NORMAL: 推测解码完成
    """

    # 合法转移
    TRANSITIONS = {
        ZoomMode.WIDE: {ZoomMode.NORMAL, ZoomMode.SPECULATIVE},
        ZoomMode.NORMAL: {ZoomMode.WIDE, ZoomMode.TELE, ZoomMode.SPECULATIVE},
        ZoomMode.TELE: {ZoomMode.NORMAL, ZoomMode.SPECULATIVE},
        ZoomMode.SPECULATIVE: {ZoomMode.NORMAL, ZoomMode.WIDE, ZoomMode.TELE},
    }

    def __init__(self, initial_mode: ZoomMode = ZoomMode.NORMAL):
        self.engine = LensZoomEngine(initial_mode=initial_mode)
        self._transition_log: List[Tuple[ZoomMode, ZoomMode, float]] = []

    def transition(
        self,
        target_mode: ZoomMode,
        load_level: float = 0.5,
        confidence: float = 0.5,
    ) -> Optional[ZoomState]:
        """变焦环状态转移

        Returns:
            新的变焦状态，或 None（非法转移）
        """
        current = self.engine.state.mode

        if target_mode not in self.TRANSITIONS.get(current, set()):
            return None

        old = self.engine.state.mode
        self.engine.zoom_to(target_mode)
        self.engine.state.load_level = load_level
        self._transition_log.append((old, target_mode, time.time()))
        return self.engine.state

    def auto(self, load_level: float, confidence: float = 0.5) -> ZoomState:
        """自动变焦"""
        return self.engine.auto_zoom(load_level, confidence)

    def get_state(self) -> ZoomState:
        return self.engine.state

    def get_transition_count(self) -> int:
        return len(self._transition_log)


# ============================================================================
# 变焦门禁
# ============================================================================

class ZoomGate:
    """变焦门禁 —— 规模门禁裁决

    裁决逻辑：
    - 焦距在合理范围 → 开
    - 焦距偏离但可调 → 徘徊
    - 焦距严重偏离 → 关
    """

    OPTIMAL_FOCAL_RANGE = (0.3, 0.7)    # 最优焦距范围
    ACCEPTABLE_FOCAL_RANGE = (0.1, 0.9)  # 可接受焦距范围

    def judge(self, zoom_state: ZoomState) -> str:
        """裁决变焦状态"""
        f = zoom_state.focal_length

        if self.OPTIMAL_FOCAL_RANGE[0] <= f <= self.OPTIMAL_FOCAL_RANGE[1]:
            return GateState.OPEN

        if self.ACCEPTABLE_FOCAL_RANGE[0] <= f <= self.ACCEPTABLE_FOCAL_RANGE[1]:
            return GateState.PENDING

        return GateState.CLOSED


__all__ = [
    "ZoomMode", "ZoomState", "LensZoomEngine",
    "LoadMetric", "BalanceResult", "LoadBalancer",
    "RhythmSlot", "RhythmResult", "RhythmScheduler",
    "ZoomRing", "ZoomGate",
]