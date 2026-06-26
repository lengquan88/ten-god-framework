"""
case_comparator.py — 案例对比分析模块 v2.5
==========================================
中华文明数字永生体 · 全维度融合架构

核心功能：
- 相似命盘检索（基于向量搜索）
- 对比报告生成（相似度评分 + 差异分析）
- 历史验证追踪（正确率统计）

用法：
    >>> from tengod.case_comparator import CaseComparator
    >>> cc = CaseComparator()
    >>> similar = cc.find_similar(bazi_data, top_k=5)
    >>> report = cc.generate_comparison_report(bazi_data, similar)
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List
import math


@dataclass
class SimilarCase:
    """相似案例"""
    case_id: str
    similarity: float
    bazi_summary: str = ""
    ziwei_summary: str = ""
    outcome: str = ""
    tags: List[str] = field(default_factory=list)
    verified: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ComparisonResult:
    """对比分析结果"""
    source_case: Dict[str, Any] = field(default_factory=dict)
    similar_cases: List[SimilarCase] = field(default_factory=list)
    similarity_stats: Dict[str, float] = field(default_factory=dict)
    common_patterns: List[str] = field(default_factory=list)
    differences: List[str] = field(default_factory=list)
    comparison_report: str = ""

    def to_dict(self) -> Dict:
        return {
            "source_case": self.source_case,
            "similar_cases": [c.to_dict() for c in self.similar_cases],
            "similarity_stats": self.similarity_stats,
            "common_patterns": self.common_patterns,
            "differences": self.differences,
            "comparison_report": self.comparison_report,
        }


class CaseComparator:
    """
    案例对比分析器

    支持基于向量相似度的案例检索和对比报告生成。
    当向量存储不可用时，回退到基于规则的相似度计算。
    """

    def __init__(self, use_vector: bool = True):
        self._use_vector = use_vector
        self._vector_store = None
        if use_vector:
            try:
                from .vector_store import get_vector_store
                self._vector_store = get_vector_store()
            except Exception:
                self._use_vector = False

    def find_similar(
        self,
        bazi_data: Dict[str, Any],
        top_k: int = 5,
        min_similarity: float = 0.3,
        include_verified_only: bool = False,
    ) -> List[SimilarCase]:
        """查找相似命盘

        Args:
            bazi_data: 八字数据字典
            top_k: 返回数量
            min_similarity: 最低相似度阈值
            include_verified_only: 是否只返回已验证案例

        Returns:
            相似案例列表
        """
        # 构建查询向量
        query_vector = self._build_bazi_vector(bazi_data)

        if self._use_vector and self._vector_store:
            return self._vector_search(query_vector, bazi_data, top_k, min_similarity)
        else:
            return self._rule_based_search(bazi_data, top_k, min_similarity)

    def generate_comparison_report(
        self,
        bazi_data: Dict[str, Any],
        similar_cases: List[SimilarCase],
        lang: str = "zh-CN",
    ) -> ComparisonResult:
        """生成对比分析报告

        Args:
            bazi_data: 源八字数据
            similar_cases: 相似案例列表
            lang: 报告语言

        Returns:
            ComparisonResult 对象
        """
        # 相似度统计
        if similar_cases:
            scores = [c.similarity for c in similar_cases]
            stats = {
                "count": len(similar_cases),
                "max_similarity": max(scores),
                "min_similarity": min(scores),
                "avg_similarity": sum(scores) / len(scores),
                "verified_count": sum(1 for c in similar_cases if c.verified),
            }
        else:
            stats = {"count": 0, "max_similarity": 0, "min_similarity": 0,
                     "avg_similarity": 0, "verified_count": 0}

        # 共同模式提取
        common_patterns = self._extract_common_patterns(bazi_data, similar_cases)

        # 差异分析
        differences = self._analyze_differences(bazi_data, similar_cases)

        # 对比报告
        report = self._build_comparison_report(
            bazi_data, similar_cases, stats, common_patterns, differences, lang
        )

        return ComparisonResult(
            source_case=bazi_data,
            similar_cases=similar_cases,
            similarity_stats=stats,
            common_patterns=common_patterns,
            differences=differences,
            comparison_report=report,
        )

    # ── 向量构建 ──────────────────────────────────────────────────────────

    def _build_bazi_vector(self, bazi_data: Dict) -> List[float]:
        """从八字数据构建特征向量"""
        vector = [0.0] * 24

        # 天干特征 (0-9)
        tian_gan_map = {"甲": 0, "乙": 1, "丙": 2, "丁": 3, "戊": 4,
                        "己": 5, "庚": 6, "辛": 7, "壬": 8, "癸": 9}
        pillars = bazi_data.get("pillars", {})
        for key in ["year", "month", "day", "hour"]:
            pillar = pillars.get(key, "")
            if pillar and len(pillar) >= 1:
                gan = pillar[0]
                idx = tian_gan_map.get(gan, -1)
                if idx >= 0:
                    vector[idx] += 1.0

        # 地支特征 (10-21)
        di_zhi_map = {"子": 0, "丑": 1, "寅": 2, "卯": 3, "辰": 4, "巳": 5,
                      "午": 6, "未": 7, "申": 8, "酉": 9, "戌": 10, "亥": 11}
        for key in ["year", "month", "day", "hour"]:
            pillar = pillars.get(key, "")
            if pillar and len(pillar) >= 2:
                zhi = pillar[1]
                idx = di_zhi_map.get(zhi, -1)
                if idx >= 0:
                    vector[idx + 10] += 1.0

        # 五行分布 (22-23)
        wuxing = bazi_data.get("analysis", {}).get("wuxing", {})
        if wuxing:
            vector.append(sum(wuxing.values()) / 20.0)
            vector.append(len(wuxing))

        return vector

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """余弦相似度"""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ── 向量搜索 ──────────────────────────────────────────────────────────

    def _vector_search(
        self, query_vector: List[float], bazi_data: Dict,
        top_k: int, min_similarity: float,
    ) -> List[SimilarCase]:
        """基于向量存储的相似搜索"""
        try:
            results = self._vector_store.search(
                query_vector, top_k=top_k * 2
            )
            similar = []
            for r in results:
                sim = r.get("score", 0)
                if sim < min_similarity:
                    continue
                case_id = r.get("id", r.get("case_id", ""))
                similar.append(SimilarCase(
                    case_id=str(case_id),
                    similarity=round(sim, 3),
                    bazi_summary=r.get("summary", ""),
                    tags=r.get("tags", []),
                    verified=r.get("verified", False),
                ))
                if len(similar) >= top_k:
                    break
            return similar
        except Exception:
            return []

    # ── 规则搜索 ──────────────────────────────────────────────────────────

    def _rule_based_search(
        self, bazi_data: Dict, top_k: int, min_similarity: float,
    ) -> List[SimilarCase]:
        """基于规则的相似度计算（回退方案）"""
        source_vector = self._build_bazi_vector(bazi_data)

        # 模拟案例库（生产环境应从数据库加载）
        mock_cases = self._get_mock_cases()

        scored = []
        for case in mock_cases:
            case_vector = self._build_bazi_vector(case.get("bazi", {}))
            sim = self._cosine_similarity(source_vector, case_vector)
            if sim >= min_similarity:
                scored.append((sim, case))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            SimilarCase(
                case_id=c.get("id", f"case_{i}"),
                similarity=round(sim, 3),
                bazi_summary=c.get("summary", ""),
                ziwei_summary=c.get("ziwei_summary", ""),
                outcome=c.get("outcome", ""),
                tags=c.get("tags", []),
                verified=c.get("verified", False),
            )
            for i, (sim, c) in enumerate(scored[:top_k])
        ]

    def _get_mock_cases(self) -> List[Dict]:
        """获取模拟案例（演示用）"""
        return [
            {
                "id": "case_001",
                "bazi": {"pillars": {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚申"},
                         "analysis": {"wuxing": {"木": 2, "火": 1, "土": 3, "金": 2, "水": 0}}},
                "summary": "日主戊土，身旺，喜金水，忌火土",
                "outcome": "事业有成，财运亨通",
                "tags": ["身旺", "喜金水", "从格"],
                "verified": True,
            },
            {
                "id": "case_002",
                "bazi": {"pillars": {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
                         "analysis": {"wuxing": {"金": 2, "水": 2, "火": 3, "土": 1, "木": 0}}},
                "summary": "日主辛金，身弱，喜土金，忌火木",
                "outcome": "中年转运，晚年安泰",
                "tags": ["身弱", "喜土金", "调候"],
                "verified": True,
            },
            {
                "id": "case_003",
                "bazi": {"pillars": {"year": "丙寅", "month": "甲午", "day": "丁酉", "hour": "己酉"},
                         "analysis": {"wuxing": {"木": 2, "火": 3, "土": 1, "金": 2, "水": 0}}},
                "summary": "日主丁火，得令，从强格",
                "outcome": "早年得志，中年起伏",
                "tags": ["从强", "火旺", "调候"],
                "verified": False,
            },
            {
                "id": "case_004",
                "bazi": {"pillars": {"year": "壬申", "month": "庚戌", "day": "癸亥", "hour": "甲寅"},
                         "analysis": {"wuxing": {"金": 3, "水": 3, "土": 1, "木": 1, "火": 0}}},
                "summary": "日主癸水，金白水清，喜木火",
                "outcome": "文采斐然，名扬四海",
                "tags": ["金白水清", "喜木火"],
                "verified": True,
            },
            {
                "id": "case_005",
                "bazi": {"pillars": {"year": "戊戌", "month": "己未", "day": "戊子", "hour": "壬子"},
                         "analysis": {"wuxing": {"土": 5, "水": 2, "金": 0, "木": 0, "火": 0}}},
                "summary": "日主戊土，土重为病，喜木疏土",
                "outcome": "大器晚成，老来得福",
                "tags": ["土重", "喜木", "晚成"],
                "verified": True,
            },
        ]

    # ── 模式提取 ──────────────────────────────────────────────────────────

    def _extract_common_patterns(
        self, source: Dict, similar: List[SimilarCase],
    ) -> List[str]:
        """提取共同模式"""
        patterns = []

        source_pillars = source.get("pillars", {})
        source_day = source_pillars.get("day", "")

        if source_day:
            day_gan = source_day[0] if len(source_day) >= 1 else ""
            count = sum(1 for c in similar if day_gan in c.bazi_summary)
            if count >= 2:
                patterns.append(f"日干{day_gan}的案例占{count}/{len(similar)}，具有参考价值")

        source_wx = source.get("analysis", {}).get("wuxing", {})
        if source_wx:
            wx_max = max(source_wx, key=source_wx.get) if source_wx else ""
            if wx_max:
                patterns.append(f"命盘五行偏{wx_max}，参考同类案例走势")

        if similar:
            verified = [c for c in similar if c.verified]
            if verified:
                patterns.append(f"其中{len(verified)}例已验证，可参考实际结局")

        return patterns[:5]

    def _analyze_differences(
        self, source: Dict, similar: List[SimilarCase],
    ) -> List[str]:
        """分析差异"""
        differences = []

        for case in similar:
            if case.similarity > 0.7:
                differences.append(f"与{case.case_id}高度相似(sim={case.similarity:.0%})，"
                                   f"建议重点参考其结局：{case.outcome}")
            elif case.similarity < 0.4:
                differences.append(f"与{case.case_id}相似度较低(sim={case.similarity:.0%})，"
                                   f"仅供参考")

        if not differences:
            differences.append("未找到显著差异的案例，建议扩大搜索范围")

        return differences[:5]

    def _build_comparison_report(
        self,
        source: Dict,
        similar: List[SimilarCase],
        stats: Dict,
        patterns: List[str],
        differences: List[str],
        lang: str,
    ) -> str:
        """构建对比分析报告"""
        source_pillars = source.get("pillars", {})
        bazi_str = (f"{source_pillars.get('year', '')} "
                    f"{source_pillars.get('month', '')} "
                    f"{source_pillars.get('day', '')} "
                    f"{source_pillars.get('hour', '')}")

        lines = [
            "=" * 60,
            "       案例对比分析报告",
            "=" * 60,
            "",
            f"源命盘：{bazi_str}",
            "",
            "【相似度统计】",
            f"  匹配案例数：{stats['count']}",
            f"  最高相似度：{stats['max_similarity']:.0%}",
            f"  平均相似度：{stats['avg_similarity']:.0%}",
            f"  已验证案例：{stats['verified_count']}/{stats['count']}",
            "",
        ]

        if similar:
            lines.append("【相似案例详情】")
            for i, case in enumerate(similar, 1):
                verified_badge = " ✓已验证" if case.verified else ""
                lines.append(f"  {i}. {case.case_id} — 相似度 {case.similarity:.0%}{verified_badge}")
                if case.bazi_summary:
                    lines.append(f"     摘要：{case.bazi_summary[:80]}")
                if case.outcome:
                    lines.append(f"     结局：{case.outcome}")
                if case.tags:
                    lines.append(f"     标签：{', '.join(case.tags)}")
                lines.append("")

        if patterns:
            lines.append("【共同模式】")
            for p in patterns:
                lines.append(f"  - {p}")
            lines.append("")

        if differences:
            lines.append("【差异分析】")
            for d in differences:
                lines.append(f"  - {d}")
            lines.append("")

        lines.extend([
            "=" * 60,
            "  本报告由案例对比引擎自动生成，仅供参考。",
            "=" * 60,
        ])

        return "\n".join(lines)


def quick_compare(
    bazi_data: Dict[str, Any],
    top_k: int = 5,
) -> ComparisonResult:
    """快速案例对比"""
    cc = CaseComparator()
    similar = cc.find_similar(bazi_data, top_k=top_k)
    return cc.generate_comparison_report(bazi_data, similar)


__all__ = [
    "CaseComparator",
    "ComparisonResult",
    "SimilarCase",
    "quick_compare",
]