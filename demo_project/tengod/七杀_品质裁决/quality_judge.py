#!/usr/bin/env python3
"""
quality_judge.py — 质量裁决器
七杀主理裁决，对系统输出与代码质量进行评分定级。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class Grade(Enum):
    """品质等级"""

    S = "S"  # 卓越
    A = "A"  # 优秀
    B = "B"  # 良好
    C = "C"  # 及格
    D = "D"  # 不及格


@dataclass
class Score:
    """评分项"""

    name: str
    value: float  # 0-100
    weight: float = 1.0
    comment: str = ""

    @property
    def weighted(self) -> float:
        return self.value * self.weight


class QualityJudge:
    """质量裁决器 — 裁决之剑

    对多方面进行加权评分，输出最终等级。
    """

    GRADE_THRESHOLDS = {
        Grade.S: 90,
        Grade.A: 80,
        Grade.B: 70,
        Grade.C: 60,
        Grade.D: 0,
    }

    def __init__(self):
        self._scores: List[Score] = []

    def add_score(
        self, name: str, value: float, weight: float = 1.0, comment: str = ""
    ) -> Score:
        """添加评分项"""
        score = Score(name=name, value=value, weight=weight, comment=comment)
        self._scores.append(score)
        return score

    def total_weighted(self) -> float:
        """加权总分"""
        if not self._scores:
            return 0.0
        total_weight = sum(s.weight for s in self._scores)
        if total_weight == 0:
            return 0.0
        weighted_sum = sum(s.weighted for s in self._scores)
        return weighted_sum / total_weight

    def grade(self) -> Grade:
        """最终等级"""
        total = self.total_weighted()
        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if total >= threshold:
                return grade
        return Grade.D

    def report(self) -> Dict[str, Any]:
        """生成裁决报告"""
        total = self.total_weighted()
        return {
            "total": round(total, 2),
            "grade": self.grade().value,
            "items": [
                {
                    "name": s.name,
                    "value": s.value,
                    "weight": s.weight,
                    "weighted": round(s.weighted, 2),
                    "comment": s.comment,
                }
                for s in self._scores
            ],
        }

    def reset(self) -> None:
        """重置评分"""
        self._scores.clear()
