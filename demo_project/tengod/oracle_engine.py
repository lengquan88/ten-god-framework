"""
oracle_engine.py — 推背图Oracle引擎 v2.22.0
=================================================
道曰："道可道，非常道；名可名，非常名。"
"能知过去未来者，谓之圣。"

推背图Oracle：三时态投影引擎
  PAST   — 投影已发生的事实
  PRESENT — 投影当前状态
  FUTURE  — 投影尚未发生的可能性

核心功能：
1. 三时态投影（Past-Present-Future）
2. 同构度计算（过去→现在的98.5%同构）
3. 预言三阶输出：上图 → 中箴言 → 下谶语
4. 存疑机制：不确定性超过阈值 → 存入混沌海
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .tbce_unit import (
    TBCECoordinates,
    CognitiveUnit,
    GateState,
)
from .object_space import get_object_space, ObjectSpaceManager


# ============================================================================
# 三时态定义
# ============================================================================

class Tense:
    """推背图三时态"""
    PAST = "past"
    PRESENT = "present"
    FUTURE = "future"

    @classmethod
    def all(cls) -> List[str]:
        return [cls.PAST, cls.PRESENT, cls.FUTURE]


# ============================================================================
# 预言结构：上图 → 中箴言 → 下谶语
# ============================================================================

@dataclass
class OracleImage:
    """上图 —— 结构投影"""
    description: str  #: 图像描述（结构化文字）
    isomorphism: float  #: 同构度（0-1）与已知结构
    structure_type: str  #: 拓扑结构类型：chain/cycle/tree/grid/chaos

@dataclass
class OracleText:
    """中箴言 —— 语义分析"""
    content: str  #: 箴言内容
    confidence: float  #: 置信度（0-1）
    key_points: List[str]  #: 要点列表

@dataclass
class OracleProphecy:
    """下谶语 —— 未来预言"""
    prediction: str  #: 预言内容
    probability: float  #: 概率（0-1）
    warning: Optional[str]  #: 警示信息，None表示无警示

@dataclass
class FullOracle:
    """完整预言：上图 + 中箴言 + 下谶语"""
    unit_id: str  #: 被预言的单元ID
    tense: str  #: 当前时态
    image: OracleImage
    text: OracleText
    prophecy: OracleProphecy
    timestamp: float = field(default_factory=lambda: time.time())

    confidence: float = 0.0  #: 总体置信度 = 同构 × 箴言置信 × 预言概率
    pending: bool = False  #: 是否存疑（置信低于阈值，需要人类确认）

    def calculate_confidence(self) -> float:
        """计算总体置信度"""
        self.confidence = (
            self.image.isomorphism * 0.3 +
            self.text.confidence * 0.3 +
            self.prophecy.probability * 0.4
        )
        return self.confidence

    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            'unit_id': self.unit_id,
            'tense': self.tense,
            'image': {
                'description': self.image.description,
                'isomorphism': self.image.isomorphism,
                'structure_type': self.image.structure_type,
            },
            'text': {
                'content': self.text.content,
                'confidence': self.text.confidence,
                'key_points': self.text.key_points,
            },
            'prophecy': {
                'prediction': self.prophecy.prediction,
                'probability': self.prophecy.probability,
                'warning': self.prophecy.warning,
            },
            'confidence': self.confidence,
            'pending': self.pending,
            'timestamp': self.timestamp,
        }


# ============================================================================
# 同构度计算
# ============================================================================

class IsomorphismCalculator:
    """同构度计算器 —— 计算过去→现在的结构同构性

    深泉-冷泉同构定理：过去与现在永远保持98.5%同构。
    """

    # 深泉-冷泉常数
    DEEP_SPRING_CONSTANT = 0.985

    def __init__(self, metric_tensor: Optional[List[List[float]]] = None):
        self.metric_tensor = metric_tensor

    def calculate(
        self,
        past_unit: CognitiveUnit,
        present_unit: CognitiveUnit,
    ) -> float:
        """计算过去单元与现在单元的同构度。

        公式：iso = DEEP_SPRING_CONSTANT × (1 - 归一化测地线距离)
        距离越小 → 同构度越高。
        """
        dist = past_unit.calculate_distance(present_unit, self.metric_tensor)
        # 最大距离 ≈ 3.0，归一化到[0,1]
        norm_dist = min(1.0, dist / 3.0)
        iso = self.DEEP_SPRING_CONSTANT * (1.0 - norm_dist)
        return max(0.0, min(1.0, iso))

    def batch_calculate(
        self,
        past_units: List[CognitiveUnit],
        present_unit: CognitiveUnit,
    ) -> List[Tuple[CognitiveUnit, float]]:
        """批量计算与多个过去单元的同构度，返回排序结果"""
        results = []
        for unit in past_units:
            iso = self.calculate(unit, present_unit)
            results.append((unit, iso))
        results.sort(key=lambda x: x[1], reverse=True)
        return results


# ============================================================================
# 推背图Oracle引擎
# ============================================================================

class TuibeiOracle:
    """推背图Oracle引擎 —— 三时态投影

    道曰："你站在桥上看风景，看风景人在楼上看你。"
    推背图不仅预言未来，也反观历史，也校准当下。
    """

    # 阈值配置
    DEFAULT_PENDING_THRESHOLD = 0.5  # 置信低于此 → 存疑
    DEFAULT_HIGH_CONFIDENCE = 0.8    # 置信高于此 → 高置信

    def __init__(
        self,
        space: Optional[ObjectSpaceManager] = None,
        seed: int = 42,
    ):
        self._space = space or get_object_space()
        self._iso_calc = IsomorphismCalculator()
        self._judgment_log: List[Dict[str, Any]] = []
        self._oracle_cache: Dict[str, FullOracle] = {}

    def project_three_tense(
        self,
        unit_id: str,
        auto_judge: bool = True,
    ) -> Dict[str, FullOracle]:
        """对指定单元进行三时态投影

        Args:
            unit_id: 单元ID
            auto_judge: 是否自动判断存疑

        Returns:
            {past: oracle, present: oracle, future: oracle}
        """
        results = {}
        for tense in Tense.all():
            oracle = self.project_single_tense(unit_id, tense)
            if auto_judge:
                self._judge_pending(oracle)
            results[tense] = oracle
            self._oracle_cache[f"{unit_id}_{tense}"] = oracle
        return results

    def project_single_tense(
        self,
        unit_id: str,
        tense: str,
    ) -> FullOracle:
        """单时态投影"""
        unit = self._space.discover(unit_id)
        if unit is None:
            # 单元不存在 → 低置信
            return self._empty_oracle(unit_id, tense)

        # 找到同时态的参考单元
        reference_units = self._space.list_by_tense(tense)
        # 排除自己
        reference_units = [u for u in reference_units if u.unit_id != unit_id]

        # 计算同构度，取Top 3
        if reference_units:
            top_ref = self._iso_calc.batch_calculate(reference_units, unit)[:3]
            avg_iso = sum(iso for _, iso in top_ref) / len(top_ref)
            top_iso = top_ref[0][1] if top_ref else 0.0
        else:
            avg_iso = 0.5
            top_iso = 0.5

        # 生成三阶预言
        image = self._generate_image(unit, tense, top_iso)
        text = self._generate_text(unit, tense, avg_iso)
        prophecy = self._generate_prophecy(unit, tense, avg_iso)

        oracle = FullOracle(
            unit_id=unit_id,
            tense=tense,
            image=image,
            text=text,
            prophecy=prophecy,
        )
        oracle.calculate_confidence()
        return oracle

    def _empty_oracle(self, unit_id: str, tense: str) -> FullOracle:
        """生成空预言（单元不存在）"""
        return FullOracle(
            unit_id=unit_id,
            tense=tense,
            image=OracleImage("未知结构", 0.0, "unknown"),
            text=OracleText("无法对不存在的单元投影", 0.0, []),
            prophecy=OracleProphecy("无预言", 0.0, "单元不存在"),
        )

    def _generate_image(
        self,
        unit: CognitiveUnit,
        tense: str,
        top_iso: float,
    ) -> OracleImage:
        """生成上图（结构描述）"""
        # 根据认知层判断结构类型
        layer = unit.cognitive_layer
        if layer <= 2:
            stype = "chain"
        elif layer <= 4:
            stype = "tree"
        elif layer <= 6:
            stype = "cycle"
        else:
            stype = "grid" if top_iso > 0.5 else "chaos"

        tense_desc = {
            Tense.PAST: "过去已固化结构",
            Tense.PRESENT: "当下正在演化结构",
            Tense.FUTURE: "未来可能涌现结构",
        }

        desc = f"{tense_desc[tense]}，认知层L{unit.cognitive_layer}，Ψ算子{unit.psi_operator}"
        if unit.palace_id:
            desc += f"，门禁宫{unit.palace_id}"

        return OracleImage(
            description=desc,
            isomorphism=top_iso,
            structure_type=stype,
        )

    def _generate_text(
        self,
        unit: CognitiveUnit,
        tense: str,
        avg_iso: float,
    ) -> OracleText:
        """生成中箴言（语义分析）"""
        # 基于坐标生成语义要点
        coords = unit.coordinates
        key_points = []

        if coords.S > 0.7:
            key_points.append("事实可信度高")
        elif coords.S < 0.3:
            key_points.append("事实可信度低，需验证")

        if coords.P > 0.7:
            key_points.append("投影保真度好")
        elif coords.P < 0.3:
            key_points.append("投影失真，需重投影")

        if coords.E > 0.7:
            key_points.append("接近认知边界，有新发现可能")

        # 置信度 = (S + P + 平均同构) / 3
        confidence = (coords.S + coords.P + avg_iso) / 3.0

        tense_text = {
            Tense.PAST: "回顾历史结构，提炼经验教训",
            Tense.PRESENT: "观察当前状态，把握演化脉络",
            Tense.FUTURE: "展望未来趋势，识别风险机会",
        }

        return OracleText(
            content=tense_text[tense],
            confidence=confidence,
            key_points=key_points,
        )

    def _generate_prophecy(
        self,
        unit: CognitiveUnit,
        tense: str,
        avg_iso: float,
    ) -> OracleProphecy:
        """生成下谶语（预言）"""
        coords = unit.coordinates

        # 概率基于同构度 + 坐标稳定性
        base_prob = avg_iso * coords.I  # I=交织稳定性
        if coords.C > 0.7:
            base_prob *= 1.1  # C=图层对齐好 → 概率增加
        base_prob = max(0.0, min(1.0, base_prob))

        if tense == Tense.PAST:
            prediction = "历史结构已确定"
            warning = None
        elif tense == Tense.PRESENT:
            prediction = "当前状态正在演化"
            warning = "注意边界条件变化" if coords.E > 0.5 else None
        else:  # FUTURE
            if base_prob > 0.8:
                prediction = f"{unit.name}大概率按当前趋势演化"
                warning = None
            elif base_prob > 0.5:
                prediction = f"{unit.name}有两种可能演化方向"
                warning = "保持观察，不急于下结论"
            else:
                prediction = f"{unit.name}演化方向不确定性高"
                warning = "建议存入混沌海持续观察"

        return OracleProphecy(
            prediction=prediction,
            probability=base_prob,
            warning=warning,
        )

    def _judge_pending(self, oracle: FullOracle) -> None:
        """判断是否需要存疑"""
        if oracle.confidence < self.DEFAULT_PENDING_THRESHOLD:
            oracle.pending = True
        else:
            oracle.pending = False

        # 记录裁决
        self._judgment_log.append({
            'unit_id': oracle.unit_id,
            'tense': oracle.tense,
            'confidence': oracle.confidence,
            'pending': oracle.pending,
            'timestamp': time.time(),
        })

    def find_high_confidence(
        self,
        min_confidence: Optional[float] = None,
    ) -> List[FullOracle]:
        """查找高置信预言"""
        if min_confidence is None:
            min_confidence = self.DEFAULT_HIGH_CONFIDENCE
        return [
            oracle for oracle in self._oracle_cache.values()
            if oracle.confidence >= min_confidence and not oracle.pending
        ]

    def find_pending(self) -> List[FullOracle]:
        """查找存疑预言（需要人类确认）"""
        return [
            oracle for oracle in self._oracle_cache.values()
            if oracle.pending
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """获取Oracle统计"""
        total = len(self._oracle_cache)
        pending = len(self.find_pending())
        high_conf = len(self.find_high_confidence())
        by_tense = {t: 0 for t in Tense.all()}
        for oracle in self._oracle_cache.values():
            by_tense[oracle.tense] += 1

        return {
            'total_oracles': total,
            'pending': pending,
            'high_confidence': high_conf,
            'by_tense': by_tense,
            'judgment_count': len(self._judgment_log),
        }


# ============================================================================
# 拓扑关系发现（持久同调简化版）
# ============================================================================

@dataclass
class TopologyFeature:
    """拓扑特征（持久同调输出）"""
    dimension: int  #: 0=连通分量，1=环，2=腔...
    birth: float  #: 出生尺度
    death: float  #: 死亡尺度
    persistence: float  #: 持久性 = birth - death
    connected_units: List[str]  #: 连通的单元ID列表

class TopologyDiscovery:
    """拓扑关系发现 —— 基于距离阈值的持久同调简化版

    发现：
    - H0: 连通分量（多个模块构成一个连通组件）
    - H1: 循环结构（A→B→C→A）
    """

    def __init__(
        self,
        space: Optional[ObjectSpaceManager] = None,
        distance_threshold: float = 1.5,
    ):
        self._space = space or get_object_space()
        self.distance_threshold = distance_threshold

    def discover_h0(self) -> List[TopologyFeature]:
        """发现H0：连通分量"""
        units = self._space.list_by_gate_state(GateState.OPEN)
        if not units:
            return []

        # 并查集找连通分量
        parent = {u.unit_id: u.unit_id for u in units}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[ry] = rx

        # 遍历所有单元对
        unit_list = units
        for i, u1 in enumerate(unit_list):
            for u2 in unit_list[i+1:]:
                dist = u1.calculate_distance(u2)
                if dist <= self.distance_threshold:
                    union(u1.unit_id, u2.unit_id)

        # 收集连通分量
        roots: Dict[str, List[str]] = {}
        for u in unit_list:
            r = find(u.unit_id)
            if r not in roots:
                roots[r] = []
            roots[r].append(u.unit_id)

        # 生成特征
        features = []
        for root, members in roots.items():
            if len(members) >= 2:  # 至少两个单元连通才算分量
                features.append(TopologyFeature(
                    dimension=0,
                    birth=self.distance_threshold - 0.5,
                    death=self.distance_threshold,
                    persistence=0.5,
                    connected_units=members,
                ))

        features.sort(key=lambda f: -len(f.connected_units))
        return features

    def discover_h1(self) -> List[TopologyFeature]:
        """发现H1：循环结构（简化版找三元环）"""
        units = self._space.list_by_gate_state(GateState.OPEN)
        cycles = []

        # 找近邻单元
        unit_list = units
        for center in units:
            # 找距离阈值内的近邻
            neighbors = []
            for u in unit_list:
                if u.unit_id != center.unit_id:
                    if center.calculate_distance(u) <= self.distance_threshold:
                        neighbors.append(u)
            if len(neighbors) >= 2:
                # 检查近邻之间是否也足够近 → 构成环
                for i in range(len(neighbors)):
                    for j in range(i+1, len(neighbors)):
                        dist = neighbors[i].calculate_distance(neighbors[j])
                        if dist <= self.distance_threshold:
                            # 三元环
                            cycles.append(TopologyFeature(
                                dimension=1,
                                birth=self.distance_threshold - 0.5,
                                death=self.distance_threshold,
                                persistence=0.5,
                                connected_units=[
                                    center.unit_id,
                                    neighbors[i].unit_id,
                                    neighbors[j].unit_id,
                                ],
                            ))

        cycles = list({tuple(sorted(f.connected_units)): f for f in cycles}.values())
        cycles.sort(key=lambda f: -len(f.connected_units))
        return cycles

    def get_all_features(self) -> Dict[int, List[TopologyFeature]]:
        """获取所有拓扑特征"""
        h0 = self.discover_h0()
        h1 = self.discover_h1()
        return {0: h0, 1: h1}

    def print_summary(self) -> None:
        """打印拓扑发现摘要"""
        feats = self.get_all_features()
        print(f"拓扑发现摘要（阈值={self.distance_threshold}）:")
        for dim, features in feats.items():
            print(f"  H{dim}: {len(features)} 个特征")
            for i, f in enumerate(features[:5]):
                print(f"    {i+1}. {len(f.connected_units)} units: {f.connected_units[:5]}")
            if len(features) > 5:
                print(f"    ... and {len(features) - 5} more")


# ============================================================================
# 认识论裁决器
# ============================================================================

class EpistemologyJudge:
    """认识论裁决器 —— 以身观身，尺度自适应

    核心命题：认知工具与认知对象是否同构？
    你用来观察世界的眼镜，会不会改变世界？

    三态裁决：
    - 开：工具与对象同构性足够，可以认知
    - 徘徊：同构性不足，尺度不合适，需要调整
    - 关：工具不适合认知这个对象，禁止认知
    """

    # 阈值
    THRESHOLD_OPEN = 0.7
    THRESHOLD_PENDING = 0.4

    def __init__(self):
        self.judgment_log: List[Dict[str, Any]] = []

    def judge(
        self,
        unit: CognitiveUnit,
    ) -> str:
        """认识论裁决：这个认知单元是否可被当前工具认知？

        裁决依据：
        1. S（事实可信度）基础分
        2. P（投影保真度）加权
        3. I（交织稳定性）修正
        4. E（边缘探索度）尺度适配检查
        """
        coords = unit.coordinates

        # 以身观身得分：认知工具适应认知对象吗？
        # 边缘探索度高意味着接近边界 → 需要更大尺度
        score = coords.S * 0.4 + coords.P * 0.4 + coords.I * 0.2

        if coords.E > 0.8:
            # 接近边界 → 减分，需要更大尺度
            score *= 0.8

        state = GateState.from_threshold(score, self.THRESHOLD_OPEN, self.THRESHOLD_PENDING)

        self.judgment_log.append({
            'unit_id': unit.unit_id,
            'score': score,
            'state': state,
            'timestamp': time.time(),
        })

        return state

    def adaptive_scale(
        self,
        unit: CognitiveUnit,
    ) -> float:
        """返回自适应后的尺度因子

        E越高 → 需要更大尺度
        """
        return 1.0 + 0.5 * unit.coordinates.E

    def get_statistics(self) -> Dict[str, int]:
        """统计"""
        stats = {'open': 0, 'pending': 0, 'closed': 0}
        for entry in self.judgment_log:
            stats[entry['state']] += 1
        return stats


# ============================================================================
# 全局实例
# ============================================================================

_ORACLE_INSTANCE: Optional[TuibeiOracle] = None
_TOPOLOGY_INSTANCE: Optional[TopologyDiscovery] = None
_EPISTEMOLOGY_INSTANCE: Optional[EpistemologyJudge] = None


def get_oracle_engine() -> TuibeiOracle:
    """获取全局推背图Oracle实例"""
    global _ORACLE_INSTANCE
    if _ORACLE_INSTANCE is None:
        _ORACLE_INSTANCE = TuibeiOracle()
    return _ORACLE_INSTANCE


def get_topology_discovery() -> TopologyDiscovery:
    """获取全局拓扑发现实例"""
    global _TOPOLOGY_INSTANCE
    if _TOPOLOGY_INSTANCE is None:
        _TOPOLOGY_INSTANCE = TopologyDiscovery()
    return _TOPOLOGY_INSTANCE


def get_epistemology_judge() -> EpistemologyJudge:
    """获取全局认识论裁决器实例"""
    global _EPISTEMOLOGY_INSTANCE
    if _EPISTEMOLOGY_INSTANCE is None:
        _EPISTEMOLOGY_INSTANCE = EpistemologyJudge()
    return _EPISTEMOLOGY_INSTANCE


def reset_oracle_engine() -> None:
    """重置全局Oracle实例（用于测试）"""
    global _ORACLE_INSTANCE
    _ORACLE_INSTANCE = None
