"""
archive.py — 时空索引与语义归档 v4.6.0
=============================================
道曰："执古之道，以御今之有。能知古始，是谓道纪。"

归档（Archive）：
- JPEG+Exif → 时空索引+语义绑定
- 生态知识归档
- 归档门禁裁决

映射仓库：
  - awesome-deepseek-integration：集成生态归档
  - awesome-deepseek-agent：智能体生态归档
  - awesome-deepseek-coder：代码生态归档
  - awesome-deepseek-data：数据生态归档
  - open-infra-index：开放基础设施索引

核心模块：
  1. SpatioTemporalIndex — 时空索引
  2. SemanticBinding   — 语义绑定
  3. ArchiveGate       — 归档门禁
  4. ArchiveEngine     — 归档引擎
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import time
import hashlib

from .tbce_unit import GateState


# ============================================================================
# 归档类型
# ============================================================================

class ArchiveType(Enum):
    """归档类型"""
    INTEGRATION = "integration"    # 集成生态
    AGENT = "agent"               # 智能体生态
    CODER = "coder"               # 代码生态
    DATA = "data"                 # 数据生态
    INFRA = "infra"               # 基础设施
    KNOWLEDGE = "knowledge"       # 知识库
    INTERNAL = "internal"         # 内部归档


# ============================================================================
# 时空索引
# ============================================================================

@dataclass
class SpatioTemporalIndex:
    """时空索引 —— JPEG+Exif 映射

    索引维度：
    - 时间：创建时间 / 修改时间 / 访问时间
    - 空间：TBCE六维坐标定位
    - 语义：关键词/标签/分类
    - 层次：认知层L1-L8
    """
    index_id: str
    archive_type: ArchiveType
    temporal_coord: float     # 时间坐标 T [0, 1]
    spatial_coords: List[float]  # TBCE六维: [S, T, P, C, I, E]
    semantic_tags: List[str]  # 语义标签
    cognitive_layer: int      # 认知层 L1-L8
    palace_id: Optional[int] = None  # 九宫格
    reference_count: int = 0  # 被引用次数
    last_accessed: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    content_hash: str = ""

    def compute_hash(self, content: Dict[str, Any]) -> str:
        content_str = str(sorted(content.items()))
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index_id": self.index_id,
            "archive_type": self.archive_type.value,
            "temporal_coord": round(self.temporal_coord, 3),
            "spatial_coords": [round(c, 3) for c in self.spatial_coords],
            "semantic_tags": self.semantic_tags,
            "cognitive_layer": self.cognitive_layer,
            "palace_id": self.palace_id,
            "reference_count": self.reference_count,
            "last_accessed": self.last_accessed,
        }


# ============================================================================
# 语义绑定
# ============================================================================

@dataclass
class SemanticBinding:
    """语义绑定 —— 知识关联

    绑定类型：
    - 直接引用：A 直接引用 B
    - 语义相似：A 和 B 语义相关
    - 因果关联：A 是 B 的前置条件
    - 层次归属：A 属于 B 的认知层
    """
    source_id: str
    target_id: str
    binding_type: str      # reference/similarity/causal/hierarchical
    strength: float        # 绑定强度 [0, 1]
    evidence: List[str]    # 绑定证据
    created_at: float = field(default_factory=time.time)


class SemanticBinder:
    """语义绑定器 —— 知识图谱关联

    生态知识归档的核心：
    不是简单地存储，而是建立知识之间的语义关联。
    """

    def __init__(self):
        self._bindings: Dict[str, List[SemanticBinding]] = {}

    def bind(
        self,
        source_id: str,
        target_id: str,
        binding_type: str,
        strength: float = 0.5,
        evidence: Optional[List[str]] = None,
    ) -> SemanticBinding:
        """创建语义绑定"""
        binding = SemanticBinding(
            source_id=source_id,
            target_id=target_id,
            binding_type=binding_type,
            strength=strength,
            evidence=evidence or [],
        )

        if source_id not in self._bindings:
            self._bindings[source_id] = []
        self._bindings[source_id].append(binding)

        return binding

    def get_bindings(self, source_id: str) -> List[SemanticBinding]:
        """获取源ID的所有绑定"""
        return self._bindings.get(source_id, [])

    def find_related(
        self, source_id: str, min_strength: float = 0.3
    ) -> List[str]:
        """查找语义相关的目标"""
        bindings = self.get_bindings(source_id)
        return [
            b.target_id for b in bindings
            if b.strength >= min_strength
        ]

    def get_binding_graph(self) -> Dict[str, List[str]]:
        """获取绑定图"""
        graph = {}
        for source, bindings in self._bindings.items():
            graph[source] = [b.target_id for b in bindings]
        return graph

    def binding_count(self) -> int:
        return sum(len(b) for b in self._bindings.values())


# ============================================================================
# 归档门禁
# ============================================================================

class ArchiveGate:
    """归档门禁 —— 生态门禁裁决

    裁决逻辑：
    - 文档完整 + 语义绑定完整 → 开
    - 文档不完整但有基本索引 → 徘徊
    - 缺少关键信息 → 关

    归档质量因素：
    1. 索引完整性：是否有时空索引
    2. 语义绑定：是否有相关知识关联
    3. 标签完整性：是否有足够的语义标签
    4. 引用验证：是否被其他条目引用
    """

    MIN_TAGS = 2            # 最少语义标签
    MIN_BINDINGS = 1        # 最少语义绑定
    QUALITY_OPEN_THRESHOLD = 0.7
    QUALITY_CLOSED_THRESHOLD = 0.3

    def judge(
        self,
        index: SpatioTemporalIndex,
        binding_count: int,
        content: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """归档门禁裁决

        Returns:
            (门禁状态, 理由)
        """
        issues = []

        # 检查语义标签
        if len(index.semantic_tags) < self.MIN_TAGS:
            issues.append(f"语义标签不足({len(index.semantic_tags)}/{self.MIN_TAGS})")

        # 检查语义绑定
        if binding_count < self.MIN_BINDINGS:
            issues.append(f"语义绑定不足({binding_count}/{self.MIN_BINDINGS})")

        # 检查时空坐标
        if not index.spatial_coords or len(index.spatial_coords) < 6:
            issues.append("缺少TBCE空间坐标")

        # 检查内容哈希
        if not index.content_hash and content:
            index.content_hash = index.compute_hash(content)

        if not index.content_hash:
            issues.append("缺少内容哈希")

        # 计算归档质量
        tag_score = min(1.0, len(index.semantic_tags) / 5.0)
        binding_score = min(1.0, binding_count / 3.0)
        coord_score = 1.0 if index.spatial_coords and len(index.spatial_coords) >= 6 else 0.0
        ref_score = min(1.0, index.reference_count / 5.0)
        hash_score = 1.0 if index.content_hash else 0.0

        quality = (
            tag_score * 0.2 +
            binding_score * 0.3 +
            coord_score * 0.2 +
            ref_score * 0.15 +
            hash_score * 0.15
        )

        if quality >= self.QUALITY_OPEN_THRESHOLD and not issues:
            return GateState.OPEN, f"归档质量高({quality:.2f})"

        if quality >= self.QUALITY_CLOSED_THRESHOLD:
            reason = f"归档质量中等({quality:.2f})"
            if issues:
                reason += f": {', '.join(issues)}"
            return GateState.PENDING, reason

        return GateState.CLOSED, f"归档质量过低({quality:.2f}): {', '.join(issues)}"


# ============================================================================
# 归档引擎
# ============================================================================

class ArchiveEngine:
    """归档引擎 —— 时空索引 + 语义绑定主控

    流程：
    1. 创建时空索引
    2. 语义绑定关联
    3. 归档门禁裁决
    4. 写入归档存储
    """

    def __init__(self):
        self.binder = SemanticBinder()
        self.gate = ArchiveGate()
        self._archives: Dict[str, SpatioTemporalIndex] = {}
        self._content_store: Dict[str, Dict[str, Any]] = {}

    def archive(
        self,
        archive_type: ArchiveType,
        spatial_coords: List[float],
        semantic_tags: List[str],
        cognitive_layer: int,
        content: Dict[str, Any],
        related_ids: Optional[List[str]] = None,
    ) -> Tuple[SpatioTemporalIndex, str, str]:
        """归档条目

        Args:
            archive_type: 归档类型
            spatial_coords: TBCE六维空间坐标
            semantic_tags: 语义标签
            cognitive_layer: 认知层
            content: 归档内容
            related_ids: 关联条目ID

        Returns:
            (时空索引, 门禁状态, 理由)
        """
        # 创建时空索引
        index_id = f"arch_{archive_type.value}_{int(time.time()*1000)}"
        temporal_coord = spatial_coords[1] if len(spatial_coords) >= 2 else 0.5

        index = SpatioTemporalIndex(
            index_id=index_id,
            archive_type=archive_type,
            temporal_coord=temporal_coord,
            spatial_coords=list(spatial_coords),
            semantic_tags=list(semantic_tags),
            cognitive_layer=cognitive_layer,
        )
        index.content_hash = index.compute_hash(content)

        # 语义绑定
        if related_ids:
            for rid in related_ids:
                self.binder.bind(
                    index_id, rid,
                    binding_type="reference",
                    strength=0.7,
                    evidence=[f"关联归档: {rid}"],
                )

        # 归档门禁裁决
        binding_count = len(self.binder.get_bindings(index_id))
        gate_state, reason = self.gate.judge(index, binding_count, content)

        # 存储
        self._archives[index_id] = index
        self._content_store[index_id] = content

        return index, gate_state, reason

    def search(
        self,
        archive_type: Optional[ArchiveType] = None,
        cognitive_layer: Optional[int] = None,
        tags: Optional[List[str]] = None,
        min_tags: int = 0,
    ) -> List[SpatioTemporalIndex]:
        """搜索归档条目

        Args:
            archive_type: 按类型过滤
            cognitive_layer: 按认知层过滤
            tags: 按标签过滤
            min_tags: 最少匹配标签数

        Returns:
            匹配的时空索引列表
        """
        results = []
        for index in self._archives.values():
            if archive_type and index.archive_type != archive_type:
                continue
            if cognitive_layer and index.cognitive_layer != cognitive_layer:
                continue
            if tags:
                matched = sum(1 for t in tags if t in index.semantic_tags)
                if matched < min_tags:
                    continue
            results.append(index)
        return results

    def get_content(self, index_id: str) -> Optional[Dict[str, Any]]:
        """获取归档内容"""
        return self._content_store.get(index_id)

    def get_related(self, index_id: str) -> List[SpatioTemporalIndex]:
        """获取语义相关条目"""
        related_ids = self.binder.find_related(index_id)
        return [
            self._archives[rid]
            for rid in related_ids
            if rid in self._archives
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """获取归档统计"""
        total = len(self._archives)
        type_counts = {}
        layer_counts = {}
        gate_counts = {'open': 0, 'pending': 0, 'closed': 0}

        for index in self._archives.values():
            at = index.archive_type.value
            type_counts[at] = type_counts.get(at, 0) + 1
            cl = index.cognitive_layer
            layer_counts[cl] = layer_counts.get(cl, 0) + 1

        return {
            "total_archives": total,
            "type_distribution": type_counts,
            "layer_distribution": layer_counts,
            "total_bindings": self.binder.binding_count(),
            "binding_graph_size": len(self.binder.get_binding_graph()),
        }

    def get_binding_graph(self) -> Dict[str, List[str]]:
        """获取语义绑定图"""
        return self.binder.get_binding_graph()


__all__ = [
    "ArchiveType", "SpatioTemporalIndex", "SemanticBinding",
    "SemanticBinder", "ArchiveGate", "ArchiveEngine",
]