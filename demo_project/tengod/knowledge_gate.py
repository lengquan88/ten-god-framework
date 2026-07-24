"""
knowledge_gate.py — 知识门禁 (正财·偏财 / 土) v4.6.0
=========================================================
正财·知识固化：知识存储是否可靠？
偏财·奇招演化：知识演化是否健康？

五行属性：土
土生金（知识支撑法度）
土克水（知识约束滋养）
木克土（架构约束知识）

裁决维度：
  1. 知识完整性：存储数据是否完整、无损坏
  2. 知识一致性：新旧知识是否冲突
  3. 知识新鲜度：知识是否过期
  4. 知识演化路径：知识更新是否形成良性循环

与七论裁决器的集成：
  - 本体论：知识是否存在？
  - 认识论：知识是否可被认知？
  - 境界论：知识是否提升了系统境界？
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import time
import hashlib

from .tbce_unit import CognitiveUnit, GateState, TBCECoordinates
from .twelve_gods_base import (
    TwelveGods, FiveElements, GateVerdict, TwelveGodsGate,
)


# ============================================================================
# 知识条目
# ============================================================================

@dataclass
class KnowledgeEntry:
    """知识条目"""
    entry_id: str
    content: Dict[str, Any]
    source: str
    confidence: float
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    access_count: int = 0
    content_hash: str = ""
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    def compute_hash(self) -> str:
        content_str = str(sorted(self.content.items()))
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]

    def is_stale(self, max_age_days: float = 30.0) -> bool:
        age_seconds = time.time() - self.updated_at
        age_days = age_seconds / 86400.0
        return age_days > max_age_days


# ============================================================================
# 知识门禁
# ============================================================================

class KnowledgeGate(TwelveGodsGate):
    """知识门禁 —— 正财·偏财（土）

    正财·知识固化：知识存储是否可靠？
    偏财·奇招演化：知识演化是否健康？

    裁决逻辑：
    1. 知识完整性：content_hash 一致性校验
    2. 知识一致性：新旧知识无冲突
    3. 知识新鲜度：非过期知识
    4. 知识演化路径：更新频率合理

    正财与偏财的区别：
    - 正财（固化）：评分主要看完整性和一致性
    - 偏财（演化）：评分主要看新鲜度和演化路径
    """

    # 评分阈值
    KNOWLEDGE_OPEN = 0.8
    KNOWLEDGE_CLOSED = 0.4
    STALE_DAYS = 30.0

    def __init__(self, god: TwelveGods = TwelveGods.ZHENGCAI):
        super().__init__(god)
        self._knowledge_store: Dict[str, KnowledgeEntry] = {}
        self._conflict_log: List[Dict] = []

    def store_knowledge(
        self,
        entry_id: str,
        content: Dict[str, Any],
        source: str,
        confidence: float = 0.5,
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
    ) -> KnowledgeEntry:
        """存储知识条目，检测冲突"""
        entry = KnowledgeEntry(
            entry_id=entry_id,
            content=content,
            source=source,
            confidence=confidence,
            tags=tags or [],
            dependencies=dependencies or [],
        )
        entry.content_hash = entry.compute_hash()

        # 检测冲突
        if entry_id in self._knowledge_store:
            old = self._knowledge_store[entry_id]
            if old.content_hash != entry.content_hash:
                self._conflict_log.append({
                    "entry_id": entry_id,
                    "old_hash": old.content_hash,
                    "new_hash": entry.content_hash,
                    "timestamp": time.time(),
                })
            entry.version = old.version + 1
            entry.created_at = old.created_at

        self._knowledge_store[entry_id] = entry
        return entry

    def _judge_impl(self, unit: CognitiveUnit) -> GateVerdict:
        """知识门禁裁决"""
        score, issues, evidence = self._evaluate_knowledge(unit)

        if score >= self.KNOWLEDGE_OPEN:
            state = GateState.OPEN
        elif score >= self.KNOWLEDGE_CLOSED:
            state = GateState.PENDING
        else:
            state = GateState.CLOSED

        reason_parts = []
        if evidence:
            reason_parts.append("; ".join(evidence[:2]))
        if issues:
            reason_parts.append("问题: " + "; ".join(issues[:2]))
        reason = " | ".join(reason_parts) if reason_parts else "知识门禁评估"

        return GateVerdict(
            god=self.god,
            state=state,
            score=score,
            reason=reason,
            element=self.element,
        )

    def _evaluate_knowledge(
        self, unit: CognitiveUnit
    ) -> Tuple[float, List[str], List[str]]:
        """评估知识质量"""
        issues = []
        evidence = []

        # 从TBCE坐标提取知识度量
        coords = unit.coordinates

        # 完整性评分：S（事实可信度） + 内容哈希
        integrity = coords.S
        if unit.metadata and "content_hash" in unit.metadata:
            evidence.append("内容哈希一致")
        else:
            integrity *= 0.9

        # 一致性评分：C（图层对齐度）
        consistency = coords.C

        # 新鲜度评分：T（时间坐标）
        freshness = coords.T

        # 演化健康度：I（交织稳定性）
        evolution = coords.I

        # 冲突检测
        conflicts = self._count_conflicts(unit)
        if conflicts > 0:
            issues.append(f"知识冲突({conflicts}个)")
        else:
            evidence.append("无知识冲突")

        # 过期检测
        if freshness < 0.3:
            issues.append(f"知识可能过期(T={freshness:.2f})")
        elif freshness > 0.7:
            evidence.append(f"知识新鲜(T={freshness:.2f})")

        if self.god == TwelveGods.ZHENGCAI:
            # 正财：固化优先
            score = (
                integrity * 0.35 +
                consistency * 0.25 +
                freshness * 0.20 +
                evolution * 0.10 +
                (1.0 - min(conflicts * 0.1, 0.5)) * 0.10
            )
        elif self.god == TwelveGods.PIANCAI:
            # 偏财：演化优先
            score = (
                evolution * 0.30 +
                consistency * 0.20 +
                freshness * 0.20 +
                integrity * 0.15 +
                (1.0 - min(conflicts * 0.1, 0.5)) * 0.15
            )
        else:
            score = integrity

        # 冲突惩罚
        score -= conflicts * 0.05
        score = max(0.0, min(1.0, score))

        return score, issues, evidence

    def _count_conflicts(self, unit: CognitiveUnit) -> int:
        """统计知识冲突"""
        count = 0
        unit_id = unit.unit_id
        for conflict in self._conflict_log:
            if conflict["entry_id"] == unit_id:
                count += 1
        return count

    def get_knowledge(self, entry_id: str) -> Optional[KnowledgeEntry]:
        return self._knowledge_store.get(entry_id)

    def get_conflicts(self) -> List[Dict]:
        return self._conflict_log

    def get_knowledge_stats(self) -> Dict[str, Any]:
        total = len(self._knowledge_store)
        stale = sum(1 for e in self._knowledge_store.values() if e.is_stale())
        conflicts = len(self._conflict_log)
        return {
            "total_entries": total,
            "stale_entries": stale,
            "conflicts": conflicts,
            "freshness_ratio": (total - stale) / max(1, total),
        }


__all__ = [
    "KnowledgeEntry", "KnowledgeGate",
]