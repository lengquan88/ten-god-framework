"""
object_space.py — 物方空间管理器 v4.6.0
=========================================
道曰："玄之又玄，众妙之门。"

物方空间是TBCE认知元的容器与索引。
所有认知单元在此空间中注册、定位、相互观察。

核心功能：
1. 认知单元注册与发现
2. 测地线距离计算
3. 基于"嗅探"(sniff)的推测解码：快速探测→推测分布→验证
4. 物方空间的门禁裁决（本体论：这个模块"存在"吗？）
"""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .tbce_unit import (
    TBCECoordinates,
    CognitiveUnit,
    GateState,
    AutoCoordinateGenerator,
)


# ============================================================================
# 推测解码（Speculative Decoding）定义
# ============================================================================

@dataclass
class SniffResult:
    """嗅探结果 —— 推测解码的中间产出。

    推测解码（Speculative Decoding）：
    1. 快速嗅探（Sniff）：粗略扫描，产生候选认知单元
    2. 推测分布（Speculate）：基于候选，推测最可能的K个单元
    3. 验证（Verify）：精确计算测地线距离，过滤误报
    """

    unit_id: str
    coarse_score: float  #: 粗略评分（快速嗅探）
    predictive_score: float  #: 推测评分（推测分布）
    verified_score: float  #: 验证评分（精确距离）
    distance: float  #: 测地线距离
    verified: bool = False  #: 是否已验证
    pending: bool = True  #: 是否仍在存疑（徘徊）


@dataclass
class SpeculativeDecodingResult:
    """推测解码完整结果"""

    query_id: str
    top_k: int
    sniff_results: List[SniffResult] = field(default_factory=list)
    verified_results: List[SniffResult] = field(default_factory=list)
    sniff_duration_ms: float = 0.0
    spec_duration_ms: float = 0.0
    verify_duration_ms: float = 0.0
    total_duration_ms: float = 0.0

    @property
    def speedup_ratio(self) -> float:
        """推测解码加速比：全量验证耗时 / 推测解码耗时"""
        if self.total_duration_ms == 0 or self.sniff_duration_ms == 0:
            return 1.0
        full_verify = max(self.sniff_duration_ms * len(self.sniff_results), 1.0)
        return full_verify / self.total_duration_ms


# ============================================================================
# 本体论裁决器
# ============================================================================

class OntologyJudge:
    """本体论裁决器 —— 判断一个认知单元是否"存在"。

    道曰："道可道，非常道。"

    本体论裁决的核心命题：
    - 这个模块在物方空间中是否有一个合法的坐标？
    - 这个坐标是否在可接受的范围内？
    - 这个模块是否拥有"名"（unit_id）和"形"（module_path）？

    三态裁决：
    - 开（open）：模块存在，坐标合法，可以进入认知系统
    - 徘徊（pending）：模块部分存在，但坐标不确定，需要人类确认
    - 关（closed）：模块不存在，坐标不合法，禁止进入认知系统
    """

    # 默认阈值
    DEFAULT_OPEN_MIN = 0.6
    DEFAULT_PENDING_MIN = 0.3

    # 各维度的阈值
    THRESHOLD_S_OPEN = 0.5  # 事实可信度最低需要0.5
    THRESHOLD_S_PENDING = 0.2
    THRESHOLD_P_OPEN = 0.4  # 投影保真度最低需要0.4
    THRESHOLD_P_PENDING = 0.2
    THRESHOLD_C_OPEN = 0.3  # 图层对齐度最低需要0.3
    THRESHOLD_C_PENDING = 0.1

    def __init__(self):
        self.judgment_log: List[Dict[str, Any]] = []

    def judge(self, unit: CognitiveUnit) -> str:
        """本体论裁决：这个认知单元是否存在？

        Args:
            unit: 认知单元

        Returns:
            门禁三态之一：open/pending/closed
        """
        reasons = []

        # 1. 检查基本存在性（有名？有实？）
        if not unit.unit_id or not unit.module_path:
            reasons.append("缺少unit_id或module_path")
            return self._close(unit, reasons)

        # 2. 检查各维度坐标的合法性
        coord = unit.coordinates

        # S维度：事实可信度
        if coord.S < 0:
            reasons.append(f"S维度为负({coord.S})")
            return self._close(unit, reasons)

        s_state = GateState.from_threshold(
            coord.S, self.THRESHOLD_S_OPEN, self.THRESHOLD_S_PENDING
        )
        if s_state == GateState.CLOSED:
            reasons.append(f"S维度过低({coord.S:.2f})")
            return self._close(unit, reasons)

        # P维度：投影保真度
        p_state = GateState.from_threshold(
            coord.P, self.THRESHOLD_P_OPEN, self.THRESHOLD_P_PENDING
        )
        if p_state == GateState.CLOSED:
            reasons.append(f"P维度过低({coord.P:.2f})")
            return self._close(unit, reasons)

        # C维度：图层对齐度
        c_state = GateState.from_threshold(
            coord.C, self.THRESHOLD_C_OPEN, self.THRESHOLD_C_PENDING
        )
        if c_state == GateState.CLOSED:
            reasons.append(f"C维度过低({coord.C:.2f})")
            return self._close(unit, reasons)

        # 3. 综合评分
        overall_score = (coord.S + coord.P + coord.C + coord.I) / 4

        state = GateState.from_threshold(
            overall_score, self.DEFAULT_OPEN_MIN, self.DEFAULT_PENDING_MIN
        )

        if state == GateState.OPEN:
            unit.gate_state = GateState.OPEN
            unit.confidence = overall_score
            self._log(unit, state, reasons)
            return state
        elif state == GateState.PENDING:
            reasons.append(f"综合评分({overall_score:.2f})处于徘徊区间")
            unit.gate_state = GateState.PENDING
            unit.confidence = overall_score
            self._log(unit, state, reasons)
            return state
        else:
            reasons.append(f"综合评分({overall_score:.2f})过低")
            unit.gate_state = GateState.CLOSED
            unit.confidence = overall_score
            self._log(unit, state, reasons)
            return state

    def _close(self, unit: CognitiveUnit, reasons: List[str]) -> str:
        unit.gate_state = GateState.CLOSED
        unit.confidence = 0.0
        self._log(unit, GateState.CLOSED, reasons)
        return GateState.CLOSED

    def _log(self, unit: CognitiveUnit, state: str, reasons: List[str]) -> None:
        self.judgment_log.append({
            'unit_id': unit.unit_id,
            'state': state,
            'reasons': reasons,
            'timestamp': time.time(),
        })

    def get_statistics(self) -> Dict[str, int]:
        """获取裁决统计"""
        stats = {'open': 0, 'pending': 0, 'closed': 0}
        for entry in self.judgment_log:
            stats[entry['state']] += 1
        return stats


# ============================================================================
# 物方空间管理器
# ============================================================================

class ObjectSpaceManager:
    """物方空间管理器 —— TBCE认知元的容器与索引。

    物方空间：所有认知单元在此空间中存在。
    每个单元有一个TBCE六维坐标，
    坐标之间的距离是测地线距离。

    道曰："无名天地之始，有名万物之母。"
    —— 物方空间的建立，就是给万物命名（分配unit_id）的过程。
    """

    def __init__(self, seed: int = 42):
        self._units: Dict[str, CognitiveUnit] = {}
        self._judge: OntologyJudge = OntologyJudge()
        self._generator: AutoCoordinateGenerator = AutoCoordinateGenerator(seed)
        self._created_at = time.time()
        self._sniff_cache: Dict[str, Dict[str, float]] = {}  # 嗅探缓存

    # ── 注册与发现 ──────────────────────────────────────

    def register(self, unit: CognitiveUnit, auto_judge: bool = True) -> str:
        """注册一个认知单元到物方空间。

        Args:
            unit: 认知单元
            auto_judge: 是否自动进行本体论裁决

        Returns:
            门禁裁决结果
        """
        if auto_judge:
            gate_state = self._judge.judge(unit)
            if gate_state == GateState.CLOSED:
                return GateState.CLOSED

        self._units[unit.unit_id] = unit
        return unit.gate_state

    def discover(self, unit_id: str) -> Optional[CognitiveUnit]:
        """发现一个认知单元"""
        return self._units.get(unit_id)

    def list_all(self) -> List[CognitiveUnit]:
        """列出所有已注册的认知单元"""
        return list(self._units.values())

    def list_by_layer(self, layer: int) -> List[CognitiveUnit]:
        """按认知层列出认知单元"""
        return [u for u in self._units.values() if u.cognitive_layer == layer]

    def list_by_palace(self, palace_id: int) -> List[CognitiveUnit]:
        """按门禁宫列出认知单元"""
        return [u for u in self._units.values() if u.palace_id == palace_id]

    def list_by_tense(self, tense: str) -> List[CognitiveUnit]:
        """按时态列出认知单元"""
        return [u for u in self._units.values() if u.tense == tense]

    def list_by_gate_state(self, state: str) -> List[CognitiveUnit]:
        """按门禁状态列出"""
        return [u for u in self._units.values() if u.gate_state == state]

    def count(self) -> int:
        """注册单元总数"""
        return len(self._units)

    # ── 推测解码（Speculative Decoding）────────────────────

    def sniff(self, target_coords: TBCECoordinates, top_k: int = 5) -> SpeculativeDecodingResult:
        """推测解码：快速嗅探 → 推测分布 → 验证。

        三步推测解码流程：
        1. 嗅探(Sniff)：用粗略距离快速筛选候选
        2. 推测(Speculate)：基于候选推测最相关的K个单元
        3. 验证(Verify)：精确计算测地线距离，确认或拒绝

        Args:
            target_coords: 目标坐标（查询点）
            top_k: 返回前K个最相关的单元

        Returns:
            SpeculativeDecodingResult 包含完整推测解码过程
        """
        total_start = time.time()

        # Step 1: 嗅探 Sniff —— 快速粗略扫描
        sniff_start = time.time()
        sniff_results: List[SniffResult] = []

        # 使用一维过滤（仅比较S和P维度）快速筛选
        for unit_id, unit in self._units.items():
            if unit.gate_state == GateState.CLOSED:
                continue

            # 快速嗅探：只用S和P两个维度做粗略比较
            coarse_score = 1.0 - (
                abs(unit.coordinates.S - target_coords.S) * 0.6 +
                abs(unit.coordinates.P - target_coords.P) * 0.4
            )

            if coarse_score > 0.3:  # 至少30%的粗略相似度
                # 粗略距离（只用S和P）
                coarse_dist = math.sqrt(
                    (unit.coordinates.S - target_coords.S) ** 2 +
                    (unit.coordinates.P - target_coords.P) ** 2
                )
                sniff_results.append(SniffResult(
                    unit_id=unit_id,
                    coarse_score=coarse_score,
                    predictive_score=0.0,
                    verified_score=0.0,
                    distance=coarse_dist,
                ))

        sniff_results.sort(key=lambda x: x.coarse_score, reverse=True)
        sniff_results = sniff_results[:top_k * 2]  # 保留2倍候选
        sniff_duration = (time.time() - sniff_start) * 1000

        # Step 2: 推测 Speculate —— 用四维（S+T+P+C）做更精确的推测
        spec_start = time.time()
        for sr in sniff_results:
            unit = self._units[sr.unit_id]
            # 四维推测评分
            predictive_score = 1.0 - (
                abs(unit.coordinates.S - target_coords.S) * 0.3 +
                abs(unit.coordinates.T - target_coords.T) * 0.3 +
                abs(unit.coordinates.P - target_coords.P) * 0.2 +
                abs(unit.coordinates.C - target_coords.C) * 0.2
            )
            sr.predictive_score = predictive_score

        sniff_results.sort(key=lambda x: x.predictive_score, reverse=True)
        sniff_results = sniff_results[:top_k]  # 裁剪到top_k
        spec_duration = (time.time() - spec_start) * 1000

        # Step 3: 验证 Verify —— 六维全量测地线距离
        verify_start = time.time()
        for sr in sniff_results:
            unit = self._units[sr.unit_id]
            # 全量计算测地线距离
            true_distance = unit.coordinates.distance(target_coords)
            sr.distance = true_distance
            sr.verified_score = 1.0 / (1.0 + true_distance)  # 距离越小，评分越高
            sr.verified = True

            # 验证通过：距离小于阈值
            if true_distance < 1.0:
                sr.pending = False
            else:
                sr.pending = True  # 距离太大，徘徊

        # 按验证距离排序
        sniff_results.sort(key=lambda x: x.distance)
        verify_duration = (time.time() - verify_start) * 1000

        total_duration = (time.time() - total_start) * 1000

        return SpeculativeDecodingResult(
            query_id=f"sniff_{int(time.time())}",
            top_k=top_k,
            sniff_results=sniff_results,
            verified_results=sniff_results,
            sniff_duration_ms=sniff_duration,
            spec_duration_ms=spec_duration,
            verify_duration_ms=verify_duration,
            total_duration_ms=total_duration,
        )

    def nearest_neighbors(
        self,
        unit_id: str,
        k: int = 5,
        metric_tensor: Optional[List[List[float]]] = None,
    ) -> List[Tuple[CognitiveUnit, float]]:
        """查找最近邻单元（精确计算）"""
        target = self._units.get(unit_id)
        if not target:
            return []

        distances = []
        for uid, unit in self._units.items():
            if uid == unit_id:
                continue
            dist = target.calculate_distance(unit, metric_tensor)
            distances.append((unit, dist))

        distances.sort(key=lambda x: x[1])
        return distances[:k]

    # ── 本体论统计 ──────────────────────────────────────

    def get_ontology_stats(self) -> Dict[str, Any]:
        """获取物方空间的本体论统计"""
        stats = self._judge.get_statistics()
        total = stats['open'] + stats['pending'] + stats['closed']

        return {
            'total_units': self.count(),
            'gate_stats': stats,
            'open_ratio': stats['open'] / max(total, 1),
            'pending_ratio': stats['pending'] / max(total, 1),
            'closed_ratio': stats['closed'] / max(total, 1),
            'created_at': self._created_at,
            'judgment_log': self._judge.judgment_log[-50:],  # 最近50条
        }

    def get_coordinate_distribution(self) -> Dict[str, Dict[str, float]]:
        """获取各维度的坐标分布统计"""
        if not self._units:
            return {}

        dims = ['S', 'T', 'P', 'C', 'I', 'E']
        result = {}
        for dim in dims:
            values = [getattr(u.coordinates, dim) for u in self._units.values()]
            result[dim] = {
                'min': min(values),
                'max': max(values),
                'mean': sum(values) / len(values),
                'median': sorted(values)[len(values) // 2],
            }
        return result

    def get_layer_distribution(self) -> Dict[int, int]:
        """获取认知层分布"""
        dist = {}
        for unit in self._units.values():
            dist[unit.cognitive_layer] = dist.get(unit.cognitive_layer, 0) + 1
        return dict(sorted(dist.items()))

    # ── 序列化 ──────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """序列化整个物方空间"""
        return {
            'version': '2.21.0',
            'created_at': self._created_at,
            'units': {
                uid: unit.to_dict()
                for uid, unit in self._units.items()
            },
            'ontology_stats': self.get_ontology_stats(),
            'coordinate_distribution': self.get_coordinate_distribution(),
            'layer_distribution': self.get_layer_distribution(),
        }

    def save(self, filepath: str) -> None:
        """保存物方空间到JSON文件"""
        data = self.to_dict()
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'ObjectSpaceManager':
        """从JSON文件加载物方空间"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        space = cls()
        space._created_at = data.get('created_at', time.time())

        for uid, unit_data in data.get('units', {}).items():
            unit = CognitiveUnit.from_dict(unit_data)
            space._units[uid] = unit

        return space

    # ── 批量注册（自动骨架版）──────────────────────────────

    def auto_register(
        self,
        module_info_list: List[Dict[str, Any]],
        auto_judge: bool = True,
    ) -> Dict[str, str]:
        """批量自动注册认知单元。

        Args:
            module_info_list: 模块信息列表，每项包含:
                - name: 模块名
                - module_path: 模块路径
                - lines_of_code: 代码行数
                - dependency_count: 依赖数量
                - is_core_module: 是否核心模块
                - has_tests: 是否有测试
                - test_coverage: 测试覆盖率
                - psi_operator: Ψ算子
                - cognitive_layer: 认知层（可选，自动推断）
                - palace_id: 门禁宫（可选）
                - tense: 时态（可选，默认present）
                - description: 描述
            auto_judge: 是否自动执行本体论裁决

        Returns:
            {unit_id: gate_state} 映射
        """
        results = {}

        for info in module_info_list:
            # 生成unit_id
            unit_id = info.get('unit_id', f"tengod.{info['name']}")

            # 自动生成坐标
            coords = self._generator.generate_from_module_info(
                module_name=info['name'],
                lines_of_code=info.get('lines_of_code', 100),
                dependency_count=info.get('dependency_count', 5),
                is_core_module=info.get('is_core_module', False),
                has_tests=info.get('has_tests', False),
                test_coverage=info.get('test_coverage', 0.0),
            )

            # 自动分配认知层
            cognitive_layer = info.get('cognitive_layer')
            if cognitive_layer is None:
                cognitive_layer = self._generator.assign_cognitive_layer(
                    lines_of_code=info.get('lines_of_code', 100),
                    is_metacognition=info.get('is_metacognition', False),
                    is_evaluation=info.get('is_evaluation', False),
                )

            unit = CognitiveUnit(
                unit_id=unit_id,
                name=info['name'],
                module_path=info.get('module_path', f"tengod.{info['name']}"),
                coordinates=coords,
                cognitive_layer=cognitive_layer,
                psi_operator=info.get('psi_operator', 'EmbeddingProvider'),
                palace_id=info.get('palace_id'),
                tense=info.get('tense', 'present'),
                consensus_layer=info.get('consensus_layer'),
                description=info.get('description', ''),
                metadata={
                    'is_core_module': info.get('is_core_module', False),
                    'is_metacognition': info.get('is_metacognition', False),
                    'is_evaluation': info.get('is_evaluation', False),
                },
            )

            gate_state = self.register(unit, auto_judge=auto_judge)
            results[unit_id] = gate_state

        return results


# ============================================================================
# 全局单例
# ============================================================================

_OBJECT_SPACE_INSTANCE: Optional[ObjectSpaceManager] = None


def get_object_space() -> ObjectSpaceManager:
    """获取全局单例物方空间"""
    global _OBJECT_SPACE_INSTANCE
    if _OBJECT_SPACE_INSTANCE is None:
        _OBJECT_SPACE_INSTANCE = ObjectSpaceManager()
    return _OBJECT_SPACE_INSTANCE


def reset_object_space() -> None:
    """重置全局单例（用于测试）"""
    global _OBJECT_SPACE_INSTANCE
    _OBJECT_SPACE_INSTANCE = None