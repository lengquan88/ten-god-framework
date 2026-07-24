"""
tbce_unit.py — TBCE六维认知元组 · 物方空间基础单元 v4.6.0
=========================================================
道曰："无名天地之始，有名万物之母。"

TBCE六维认知空间（黎曼流形）：
  S · Source (源)   — 事实层：数据来源与可信度
  T · Time   (时间) — 符号层：版本演化与时序定位
  P · Projection (投影) — 逻辑层：高维→低维保结构映射
  C · Canvas (图层) — 情感层：多模态输出语义融合
  I · Interweave (交织) — 通信层：跨层交织与同步
  E · Edge   (边缘) — 边界层：认知边界与预言失效

数学性质：TBCE六维空间是黎曼流形，不是欧几里得空间。
  - S和T构成类时方向（因果不可逆）
  - P和C构成类空方向（可自由切片）
  - I和E构成测地线偏离方向（度量认知曲率）

工程实现：每个模块对应一个TBCE认知元组，
在物方空间中有一个坐标，坐标之间的距离是测地线距离。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import math


# ============================================================================
# TBCE六维坐标定义
# ============================================================================

@dataclass
class TBCECoordinates:
    """TBCE六维认知坐标。

    每个维度的取值范围：
    - S: [0, 1] 事实可信度，0=完全不可信，1=完全可信
    - T: [0, ∞) 时间坐标，越大越靠近现在
    - P: [0, 1] 投影保真度，越高投影越保留结构
    - C: [0, 1] 图层对齐度，越高多模态语义越一致
    - I: [0, 1] 交织稳定性，越高通信越可靠
    - E: [0, 1] 边缘探索度，越高越接近认知边界

    门禁三态：
    - 开：满足阈值，允许通过
    - 徘徊：接近阈值，需要人类确认
    - 关：不满足阈值，禁止通过
    """

    S: float  #: Source - 事实可信度
    T: float  #: Time - 时间坐标
    P: float  #: Projection - 投影保真度
    C: float  #: Canvas - 图层对齐度
    I: float  #: Interweave - 交织稳定性
    E: float  #: Edge - 边缘探索度

    def to_list(self) -> List[float]:
        """转换为坐标列表"""
        return [self.S, self.T, self.P, self.C, self.I, self.E]

    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            'S': self.S,
            'T': self.T,
            'P': self.P,
            'C': self.C,
            'I': self.I,
            'E': self.E,
        }

    @classmethod
    def from_list(cls, coords: List[float]) -> 'TBCECoordinates':
        """从列表创建坐标"""
        assert len(coords) == 6, f"TBCE坐标必须是6维，得到{len(coords)}维"
        return cls(*coords)

    @classmethod
    def zero(cls) -> 'TBCECoordinates':
        """创建零坐标（初始占位）"""
        return cls(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    @classmethod
    def default(cls) -> 'TBCECoordinates':
        """创建默认坐标（中等可信度）"""
        return cls(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)

    def distance(self, other: 'TBCECoordinates', metric_tensor: Optional[List[List[float]]] = None) -> float:
        """计算测地线距离（黎曼流形上的距离）。

        简化实现：使用加权欧氏距离近似测地线距离，
        权重由度量张量给出，默认权重对应"类时-类空-偏离"结构。

        Args:
            other: 另一个TBCE坐标
            metric_tensor: 度量张量 g_μν，6x6矩阵，
                          如果为None，使用默认度量张量。

        Returns:
            测地线距离，≥ 0
        """
        # 默认度量张量对应TBCE空间的几何结构：
        # - S和T（类时）权重较大
        # - P和C（类空）权重中等
        # - I和E（偏离）权重较小
        if metric_tensor is None:
            metric_tensor = [
                [2.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 2.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 1.5, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 1.5, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
            ]

        diff = [
            self.S - other.S,
            self.T - other.T,
            self.P - other.P,
            self.C - other.C,
            self.I - other.I,
            self.E - other.E,
        ]

        # 黎曼度量：ds² = Σ Σ g_μν dx^μ dx^ν
        dist_sq = 0.0
        for i in range(6):
            for j in range(6):
                dist_sq += metric_tensor[i][j] * diff[i] * diff[j]

        return math.sqrt(max(dist_sq, 0.0))

    def gradient_norm(self, gradient: List[float], metric_tensor: Optional[List[List[float]]] = None) -> float:
        """计算梯度的范数（黎曼流形上）。"""
        if metric_tensor is None:
            metric_tensor = [
                [2.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 2.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 1.5, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 1.5, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
            ]

        norm_sq = 0.0
        for i in range(6):
            for j in range(6):
                norm_sq += metric_tensor[i][j] * gradient[i] * gradient[j]

        return math.sqrt(max(norm_sq, 0.0))


# ============================================================================
# 门禁三态定义
# ============================================================================

class GateState:
    """门禁三态：开 / 徘徊 / 关"""

    OPEN = "open"
    PENDING = "pending"  #: 徘徊，需要人类确认
    CLOSED = "closed"

    @classmethod
    def from_threshold(
        cls,
        value: float,
        open_min: float,
        pending_min: float,
    ) -> str:
        """根据阈值判断门禁状态"""
        if value >= open_min:
            return cls.OPEN
        elif value >= pending_min:
            return cls.PENDING
        else:
            return cls.CLOSED

    @classmethod
    def is_passable(cls, state: str) -> bool:
        """状态是否可通过"""
        return state == cls.OPEN

    @classmethod
    def requires_human(cls, state: str) -> bool:
        """是否需要人类确认"""
        return state == cls.PENDING


# ============================================================================
# 认知单元定义
# ============================================================================

@dataclass
class CognitiveUnit:
    """TBCE认知单元 —— 物方空间中的一个认知实体。

    每个模块、每个功能、每个概念，对应一个认知单元。
    认知单元在TBCE六维空间中有一个坐标，
    坐标之间的距离是测地线距离。
    """

    #: 唯一标识符，通常是模块路径如 "tengod.bazi_calculator"
    unit_id: str

    #: 单元名称，人类可读
    name: str

    #: 模块路径，指向实际代码
    module_path: str

    #: TBCE六维坐标
    coordinates: TBCECoordinates

    #: 认知层（L1-L8）
    #: L1=信息编码, L2=语义流, L3=拓扑结构, L4=意识涌现,
    #: L5=注意力调度, L6=元认知自反, L7=认知固化, L8=境界跃迁
    cognitive_layer: int  # 1-8

    #: Ψ算子（对应这个单元主要使用哪个Ψ算子）
    #: 可选值: "EmbeddingProvider", "Tortuosity", "PersistenceDiagram",
    #:         "PsiSelfRef", "ZuowangAttention", "RecursionDepth",
    #:         "CondInfoStability", "SpiritEvaluator"
    psi_operator: str

    #: 门禁宫（九宫格），None表示不分配
    #: 1=坎一, 2=坤二, 3=震三, 4=巽四, 5=中五, 6=乾六, 7=兑七, 8=艮八, 9=离九
    palace_id: Optional[int] = None

    #: 推背图时态
    #: "past" / "present" / "future"
    tense: str = "present"

    #: 共识网络位置（L1-L5），None表示不在共识网络中
    consensus_layer: Optional[int] = None

    #: 单元描述
    description: str = ""

    #: 门禁状态（本体论裁决后的结果）
    gate_state: str = GateState.PENDING

    #: 可信度评分（0-1）
    confidence: float = 0.5

    #: 发现时间（Unix时间戳）
    discovered_at: float = field(default_factory=lambda: __import__('time').time())

    #: 最后更新时间
    updated_at: float = field(default_factory=lambda: __import__('time').time())

    #: 验证次数
    verification_count: int = 0

    #: 元数据，存储额外信息
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_coordinates(self, new_coords: TBCECoordinates) -> None:
        """更新坐标，更新时间戳"""
        self.coordinates = new_coords
        self.updated_at = __import__('time').time()
        self.verification_count += 1

    def calculate_distance(
        self,
        other: 'CognitiveUnit',
        metric_tensor: Optional[List[List[float]]] = None,
    ) -> float:
        """计算与另一个认知单元的测地线距离"""
        return self.coordinates.distance(other.coordinates, metric_tensor)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于序列化"""
        return {
            'unit_id': self.unit_id,
            'name': self.name,
            'module_path': self.module_path,
            'coordinates': self.coordinates.to_dict(),
            'cognitive_layer': self.cognitive_layer,
            'psi_operator': self.psi_operator,
            'palace_id': self.palace_id,
            'tense': self.tense,
            'consensus_layer': self.consensus_layer,
            'description': self.description,
            'gate_state': self.gate_state,
            'confidence': self.confidence,
            'discovered_at': self.discovered_at,
            'updated_at': self.updated_at,
            'verification_count': self.verification_count,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CognitiveUnit':
        """从字典重建认知单元"""
        coords = TBCECoordinates(**data['coordinates'])
        return cls(
            unit_id=data['unit_id'],
            name=data['name'],
            module_path=data['module_path'],
            coordinates=coords,
            cognitive_layer=data['cognitive_layer'],
            psi_operator=data['psi_operator'],
            palace_id=data.get('palace_id'),
            tense=data.get('tense', 'present'),
            consensus_layer=data.get('consensus_layer'),
            description=data.get('description', ''),
            gate_state=data.get('gate_state', GateState.PENDING),
            confidence=data.get('confidence', 0.5),
            discovered_at=data.get('discovered_at', __import__('time').time()),
            updated_at=data.get('updated_at', __import__('time').time()),
            verification_count=data.get('verification_count', 0),
            metadata=data.get('metadata', {}),
        )


# ============================================================================
# 自动坐标生成器（基于模块静态分析）
# ============================================================================

class AutoCoordinateGenerator:
    """自动TBCE坐标生成器。

    基于模块的静态特征（代码行数、依赖数量、模块类型等）
    自动生成初始TBCE坐标，然后可以手动精调。
    """

    def __init__(self, seed: int = 42):
        import random
        self.rng = random.Random(seed)

    def generate_from_module_info(
        self,
        module_name: str,
        lines_of_code: int,
        dependency_count: int,
        is_core_module: bool,
        has_tests: bool,
        test_coverage: float,
    ) -> TBCECoordinates:
        """根据模块信息自动生成初始坐标。

        启发式规则：
        - S（事实可信度）：有测试 → 高，覆盖率越高 → 越高
        - T（时间）：核心模块 → 更新，最近修改的模块 → 高
        - P（投影保真度）：依赖越少 → 投影越清晰 → 越高
        - C（图层对齐度）：行数适中 → 对齐度好，太大或太小都不好
        - I（交织稳定性）：依赖适中 → 稳定，太少或太多都不好
        - E（边缘探索度）：新模块 → 边缘探索度高，老模块 → 低
        """
        # S: 事实可信度，主要由测试决定
        S = 0.3
        if has_tests:
            S = 0.5 + 0.4 * test_coverage
        else:
            S = 0.2 + 0.2 * test_coverage

        # T: 时间坐标，核心模块更靠近现在
        T = 0.5
        if is_core_module:
            T += 0.3
        if has_tests:
            T += 0.1

        # P: 投影保真度，依赖越少越好
        # 0-10 依赖: 0.8-0.9, 10-20: 0.6-0.8, >20: 0.4-0.6
        if dependency_count < 10:
            P = 0.7 + 0.2 * (10 - dependency_count) / 10
        elif dependency_count < 20:
            P = 0.6 + 0.1 * (20 - dependency_count) / 10
        else:
            P = max(0.4, 0.6 - 0.2 * (dependency_count - 20) / 20)

        # C: 图层对齐度，行数适中最好
        # 100-1000行最佳
        loc_norm = max(0, min(1, (lines_of_code - 100) / 900))  # 0-1
        # 二次函数，在中间最高
        C = 1.0 - 4 * (loc_norm - 0.5) ** 2  # 0-1

        # I: 交织稳定性，依赖数适中最好
        # 5-15个依赖最佳
        dep_norm = max(0, min(1, (dependency_count - 5) / 10))
        I = 1.0 - 4 * (dep_norm - 0.5) ** 2

        # E: 边缘探索度，新模块/低覆盖 → 探索度高
        E = 1.0 - (S + test_coverage) / 2
        # 加一点随机扰动
        E += self.rng.gauss(0, 0.05)
        E = max(0, min(1, E))

        # 轻微随机扰动，避免完全对齐
        S += self.rng.gauss(0, 0.02)
        T += self.rng.gauss(0, 0.02)
        P += self.rng.gauss(0, 0.02)
        C += self.rng.gauss(0, 0.02)
        I += self.rng.gauss(0, 0.02)

        # 剪裁到[0,1]
        S = max(0, min(1, S))
        T = max(0, min(1, T))
        P = max(0, min(1, P))
        C = max(0, min(1, C))
        I = max(0, min(1, I))
        E = max(0, min(1, E))

        return TBCECoordinates(S, T, P, C, I, E)

    def assign_cognitive_layer(
        self,
        lines_of_code: int,
        is_metacognition: bool,
        is_evaluation: bool,
    ) -> int:
        """自动分配认知层"""
        if is_evaluation:
            return 8  # L8 境界跃迁
        if is_metacognition:
            return 6  # L6 元认知自反
        if lines_of_code > 1000:
            return 4  # L4 意识涌现
        if lines_of_code > 500:
            return 3  # L3 拓扑结构
        return 1  # L1 信息编码（默认）
