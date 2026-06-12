#!/usr/bin/env python3
"""
innovator.py — 破界创新器
伤官主理破界，辅助系统在传统范式之外产生新解。
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import uuid
import time


class InnovationType(Enum):
    """创新类型"""
    COMBINATION = "combination"   # 组合创新
    TRANSFER = "transfer"         # 迁移创新
    REVERSE = "reverse"           # 逆向创新
    BREAKTHROUGH = "breakthrough" # 突破创新


@dataclass
class Idea:
    """创意"""
    id: str
    title: str
    description: str
    innovation_type: InnovationType
    feasibility: float  # 0-1
    impact: float       # 0-1
    created_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        """综合得分"""
        return (self.feasibility * 0.4 + self.impact * 0.6)


class Innovator:
    """破界创新器 — 破界之锋

    通过组合、迁移、逆向、突破四种方式产生新解。
    """

    def __init__(self):
        self._ideas: List[Idea] = []

    def combine(self, items: List[str], description: str = "") -> Idea:
        """组合创新：将多个元素组合产生新解"""
        title = f"组合: {' × '.join(items)}"
        if not description:
            description = f"将 {' 与 '.join(items)} 组合，形成新方案"
        idea = Idea(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            innovation_type=InnovationType.COMBINATION,
            feasibility=0.7,
            impact=0.7,
            tags=items,
        )
        self._ideas.append(idea)
        return idea

    def transfer(self, source: str, target: str, description: str = "") -> Idea:
        """迁移创新：将一领域的方案迁移到另一领域"""
        title = f"迁移: {source} → {target}"
        if not description:
            description = f"将 {source} 领域的做法迁移到 {target} 领域"
        idea = Idea(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            innovation_type=InnovationType.TRANSFER,
            feasibility=0.6,
            impact=0.8,
            tags=[source, target],
        )
        self._ideas.append(idea)
        return idea

    def reverse(self, original: str, description: str = "") -> Idea:
        """逆向创新：反向思考"""
        title = f"逆向: {original}"
        if not description:
            description = f"对 {original} 进行反向思考"
        idea = Idea(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            innovation_type=InnovationType.REVERSE,
            feasibility=0.5,
            impact=0.9,
            tags=["逆向"],
        )
        self._ideas.append(idea)
        return idea

    def top_ideas(self, n: int = 5) -> List[Idea]:
        """获取得分最高的创意"""
        return sorted(self._ideas, key=lambda i: i.score, reverse=True)[:n]

    def list_by_type(self, itype: InnovationType) -> List[Idea]:
        """按类型筛选"""
        return [i for i in self._ideas if i.innovation_type == itype]

    def report(self) -> Dict[str, Any]:
        """生成创意报告"""
        return {
            "total": len(self._ideas),
            "by_type": {
                itype.value: len(self.list_by_type(itype))
                for itype in InnovationType
            },
            "top_ideas": [
                {
                    "id": i.id,
                    "title": i.title,
                    "score": round(i.score, 3),
                    "type": i.innovation_type.value,
                }
                for i in self.top_ideas()
            ],
        }
