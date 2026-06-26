"""
fusion_analyzer.py — 多体系融合分析引擎 v2.5
=============================================
中华文明数字永生体 · 全维度融合架构

核心功能：
- 三体系交叉验证：八字 + 紫微斗数 + 奇门遁甲
- 加权综合评分（一致性/矛盾性检测/置信度）
- 融合报告生成（与 report_generator 集成）
- 命运轨迹关键节点提取

用法：
    >>> from tengod.fusion_analyzer import FusionAnalyzer
    >>> fa = FusionAnalyzer(bazi_data, ziwei_data, qimen_data)
    >>> result = fa.analyze()
    >>> print(result.fusion_report)
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
import json


# ============================================================================
# 常量定义
# ============================================================================

WUXING_SIGNS = ["木", "火", "土", "金", "水"]

# 体系权重（基于历史验证准确率）
SYSTEM_WEIGHTS = {
    "bazi": 0.45,    # 八字：核心体系，权重最高
    "ziwei": 0.35,   # 紫微斗数：宫位体系，中等权重
    "qimen": 0.20,   # 奇门遁甲：时空体系，辅助权重
}

# 一致性等级
AGREEMENT_LEVELS = {
    (80, 101): "高度一致",
    (60, 80): "基本一致",
    (40, 60): "部分一致",
    (20, 40): "存在分歧",
    (0, 20): "严重矛盾",
}

# 运势等级
FORTUNE_LEVELS = {
    (85, 101): "大吉",
    (70, 85): "吉",
    (55, 70): "平",
    (40, 55): "凶",
    (0, 40): "大凶",
}


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class SystemAnalysis:
    """单体系分析结果"""
    name: str
    available: bool = True
    score: int = 50
    yongshen: List[str] = field(default_factory=list)
    jishen: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    summary: str = ""
    key_findings: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CrossValidationResult:
    """交叉验证结果"""
    agreement_score: int = 50
    level: str = "待观察"
    confidence: float = 0.5
    yongshen_consensus: List[str] = field(default_factory=list)
    yongshen_conflicts: List[str] = field(default_factory=list)
    agreements: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    dimensions: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class FusionResult:
    """融合分析最终结果"""
    birth_info: Dict[str, Any] = field(default_factory=dict)
    systems: Dict[str, SystemAnalysis] = field(default_factory=dict)
    cross_validation: CrossValidationResult = field(default_factory=CrossValidationResult)
    overall_score: int = 50
    overall_level: str = "平"
    fusion_summary: str = ""
    key_events: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    fusion_report: str = ""

    def to_dict(self) -> Dict:
        return {
            "birth_info": self.birth_info,
            "systems": {k: v.to_dict() for k, v in self.systems.items()},
            "cross_validation": self.cross_validation.to_dict(),
            "overall_score": self.overall_score,
            "overall_level": self.overall_level,
            "fusion_summary": self.fusion_summary,
            "key_events": self.key_events,
            "recommendations": self.recommendations,
            "fusion_report": self.fusion_report,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================================
# 融合分析引擎
# ============================================================================

class FusionAnalyzer:
    """
    三体系融合分析引擎

    整合八字、紫微斗数、奇门遁甲三方分析结果，
    通过加权交叉验证产出综合评分与融合报告。
    """

    def __init__(
        self,
        bazi_data: Optional[Dict[str, Any]] = None,
        ziwei_data: Optional[Dict[str, Any]] = None,
        qimen_data: Optional[Dict[str, Any]] = None,
        birth_info: Optional[Dict[str, Any]] = None,
        target_year: int = 2026,
    ):
        self._bazi = bazi_data or {}
        self._ziwei = ziwei_data or {}
        self._qimen = qimen_data or {}
        self._birth = birth_info or {}
        self._target_year = target_year

    # ── 单体系分析 ──────────────────────────────────────────────────────

    def _analyze_bazi(self) -> SystemAnalysis:
        """八字体系分析"""
        if not self._bazi:
            return SystemAnalysis("八字", available=False, error="无数据")

        analysis = self._bazi.get("analysis", {})
        day_master = analysis.get("day_master", "")
        wuxing = analysis.get("wuxing", {})
        geju = self._bazi.get("geju", "")
        shensha = self._bazi.get("shensha", [])
        conclusion = analysis.get("conclusion", "")

        # 喜用神提取
        yongshen = []
        jishen = []
        if isinstance(analysis.get("yongshen"), list):
            yongshen = [y for y in analysis["yongshen"] if y in WUXING_SIGNS]
        if isinstance(analysis.get("jishen"), list):
            jishen = [j for j in analysis["jishen"] if j in WUXING_SIGNS]

        # 五行评分
        wuxing_score = sum(wuxing.values()) if wuxing else 0
        balance = 80 if 10 <= wuxing_score <= 15 else (60 if 5 <= wuxing_score <= 20 else 40)

        # 格局加分
        geju_bonus = 10 if geju and "格" in str(geju) else 0

        # 神煞影响
        shensha_bonus = min(10, len(shensha) * 2) if shensha else 0

        score = min(100, balance + geju_bonus + shensha_bonus)

        strengths = []
        risks = []
        if yongshen:
            strengths.append(f"喜用神{'、'.join(yongshen)}得力")
        if geju:
            strengths.append(f"格局{geju}")
        if "旺" in str(conclusion):
            risks.append("五行偏旺，需注意平衡")

        summary = f"日主{day_master}，{conclusion[:30] if conclusion else '五行平衡'}"
        key_findings = [
            f"日主{day_master}，{'、'.join(yongshen) if yongshen else '五行平衡'}为喜用",
            f"格局：{geju or '待定'}",
            f"神煞：{', '.join(shensha[:3]) if shensha else '无特殊神煞'}",
        ]

        return SystemAnalysis(
            name="八字",
            score=score,
            yongshen=yongshen,
            jishen=jishen,
            strengths=strengths,
            risks=risks,
            summary=summary,
            key_findings=key_findings,
        )

    def _analyze_ziwei(self) -> SystemAnalysis:
        """紫微斗数体系分析"""
        if not self._ziwei:
            return SystemAnalysis("紫微斗数", available=False, error="无数据")

        ming_gong = self._ziwei.get("ming_gong", {})
        sihua = self._ziwei.get("sihua", {})
        ming_zhu = self._ziwei.get("ming_zhu", "")
        shen_zhu = self._ziwei.get("shen_zhu", "")

        # 命宫主星分析
        ming_stars = ming_gong.get("main_stars", []) if isinstance(ming_gong, dict) else []

        # 吉星/煞星判断
        auspicious = {"紫微", "天府", "天相", "天同", "天梁", "太阳", "太阴", "文昌", "文曲", "左辅", "右弼", "天魁", "天钺", "禄存"}
        inauspicious = {"七杀", "破军", "贪狼", "巨门", "廉贞", "擎羊", "陀罗", "火星", "铃星", "地空", "地劫"}

        good_count = sum(1 for s in ming_stars if s in auspicious)
        bad_count = sum(1 for s in ming_stars if s in inauspicious)

        base_score = 50 + good_count * 8 - bad_count * 6
        score = max(10, min(100, base_score))

        # 喜用神推导
        yongshen = []
        if any(s in str(ming_zhu) for s in ["天同", "天梁", "天府", "太阴", "文曲"]):
            yongshen = ["水", "金"]
        elif any(s in str(ming_zhu) for s in ["紫微", "武曲", "贪狼", "七杀"]):
            yongshen = ["土", "金"]
        elif any(s in str(ming_zhu) for s in ["太阳", "巨门", "天机"]):
            yongshen = ["木", "水"]
        elif any(s in str(ming_zhu) for s in ["廉贞", "破军"]):
            yongshen = ["火", "木"]

        strengths = []
        risks = []
        if good_count > bad_count:
            strengths.append(f"命宫{good_count}吉星汇聚")
        if bad_count > 0:
            risks.append(f"命宫有{bad_count}煞星，需防波折")

        sihua_list = [f"{k}({v})" for k, v in sihua.items() if v]
        summary = f"命主{ming_zhu}，身主{shen_zhu}"
        key_findings = [
            f"命主星：{ming_zhu}，身主星：{shen_zhu}",
            f"命宫主星：{', '.join(ming_stars) if ming_stars else '无主星'}",
            f"四化：{', '.join(sihua_list) if sihua_list else '无'}",
        ]

        return SystemAnalysis(
            name="紫微斗数",
            score=score,
            yongshen=yongshen,
            strengths=strengths,
            risks=risks,
            summary=summary,
            key_findings=key_findings,
        )

    def _analyze_qimen(self) -> SystemAnalysis:
        """奇门遁甲体系分析"""
        if not self._qimen:
            return SystemAnalysis("奇门遁甲", available=False, error="无数据")

        pan_type = self._qimen.get("pan_type", "时家奇门")
        men = self._qimen.get("men", "")
        star = self._qimen.get("star", "")
        

        # 八门吉凶
        good_men = {"开门", "休门", "生门"}
        bad_men = {"死门", "惊门", "伤门"}
        if men in good_men:
            men_score = 20
        elif men in bad_men:
            men_score = -10
        else:
            men_score = 5

        # 九星吉凶
        good_stars = {"天辅", "天禽", "天心", "天任", "天冲", "天英"}

        if star in good_stars:
            star_score = 15
        else:
            star_score = -5

        base_score = 55 + men_score + star_score
        score = max(10, min(100, base_score))

        strengths = []
        risks = []
        if men in good_men:
            strengths.append(f"值{men}吉门，时机有利")
        if men in bad_men:
            risks.append(f"值{men}凶门，需谨慎行事")
        if star in good_stars:
            strengths.append(f"{star}星照临，天时助力")

        summary = f"{pan_type}，{men}门{star}星"
        key_findings = [
            f"盘式：{pan_type}",
            f"八门：{men or '未知'}",
            f"九星：{star or '未知'}",
        ]

        return SystemAnalysis(
            name="奇门遁甲",
            score=score,
            strengths=strengths,
            risks=risks,
            summary=summary,
            key_findings=key_findings,
        )

    # ── 交叉验证 ──────────────────────────────────────────────────────────

    def _cross_validate(
        self, systems: Dict[str, SystemAnalysis]
    ) -> CrossValidationResult:
        """三方交叉验证"""
        bz = systems.get("八字")
        zw = systems.get("紫微斗数")
        qm = systems.get("奇门遁甲")

        agreements: List[str] = []
        conflicts: List[str] = []
        dimensions: Dict[str, int] = {}

        # 1. 喜用神一致性检查
        yongshen_sets = {}
        for sa in [bz, zw]:
            if sa and sa.available and sa.yongshen:
                yongshen_sets[sa.name] = set(sa.yongshen)

        if len(yongshen_sets) >= 2:
            all_yong = list(yongshen_sets.values())
            common = all_yong[0].intersection(*all_yong[1:])
            if common:
                agreements.append(f"喜用神共识：{'、'.join(sorted(common))}")
                dimensions["yongshen"] = 25
            else:
                conflicts.append("八字与紫微喜用神判断不一致（不同算法体系，属正常现象）")
                dimensions["yongshen"] = 5
        elif len(yongshen_sets) == 1:
            dimensions["yongshen"] = 15

        # 2. 评分一致性检查
        scores = []
        for sa in [bz, zw, qm]:
            if sa and sa.available:
                scores.append(sa.score)

        if len(scores) >= 2:
            score_range = max(scores) - min(scores)
            if score_range <= 15:
                agreements.append("三体系评分一致（偏差≤15分）")
                dimensions["score_consistency"] = 20
            elif score_range <= 30:
                dimensions["score_consistency"] = 10
            else:
                conflicts.append(f"体系评分偏差较大（{score_range}分），建议重点参考八字")
                dimensions["score_consistency"] = 5

        # 3. 吉凶方向一致性
        bz_good = bz and bz.score >= 60
        zw_good = zw and zw.score >= 60
        qm_good = qm and qm.score >= 60

        good_count = sum([bz_good, zw_good, qm_good])
        if good_count >= 2:
            agreements.append(f"{good_count}/3 体系呈吉象")
            dimensions["direction"] = 20
        elif good_count == 0:
            conflicts.append("三体系均呈凶象，需特别注意")
            dimensions["direction"] = 5
        else:
            dimensions["direction"] = 10

        # 4. 综合评分配比
        agreement_score = sum(dimensions.values())
        agreement_score = max(10, min(100, agreement_score + 35))

        level = "待观察"
        for (lo, hi), label in AGREEMENT_LEVELS.items():
            if lo <= agreement_score < hi:
                level = label
                break

        confidence = agreement_score / 100.0

        return CrossValidationResult(
            agreement_score=agreement_score,
            level=level,
            confidence=confidence,
            yongshen_consensus=list(set.intersection(*yongshen_sets.values())) if len(yongshen_sets) >= 2 and set.intersection(*yongshen_sets.values()) else [],
            agreements=agreements,
            conflicts=conflicts,
            dimensions=dimensions,
        )

    # ── 融合评分 ──────────────────────────────────────────────────────────

    def _compute_overall(
        self,
        systems: Dict[str, SystemAnalysis],
        cross: CrossValidationResult,
    ) -> Tuple[int, str]:
        """加权综合评分"""
        weighted = 0.0
        total_weight = 0.0

        for name, sa in systems.items():
            if sa.available:
                w = SYSTEM_WEIGHTS.get({
                    "八字": "bazi", "紫微斗数": "ziwei", "奇门遁甲": "qimen",
                }.get(name, "bazi"), 0.33)
                weighted += sa.score * w
                total_weight += w

        if total_weight > 0:
            raw_score = weighted / total_weight
        else:
            raw_score = 50

        # 交叉验证修正
        if cross.confidence >= 0.8:
            raw_score = raw_score * 0.85 + cross.agreement_score * 0.15
        elif cross.confidence < 0.4:
            raw_score = raw_score * 0.7 + 50 * 0.3

        overall = int(min(100, max(10, raw_score)))

        level = "平"
        for (lo, hi), label in FORTUNE_LEVELS.items():
            if lo <= overall < hi:
                level = label
                break

        return overall, level

    # ── 关键事件提取 ──────────────────────────────────────────────────────

    def _extract_key_events(self, systems: Dict[str, SystemAnalysis]) -> List[Dict]:
        """提取命运轨迹关键节点"""
        events = []

        bz = systems.get("八字")
        if bz and bz.available:
            dayuns = self._bazi.get("analysis", {}).get("dayuns", [])
            liunians = self._bazi.get("analysis", {}).get("liunians", [])
            for dx in dayuns[:3]:
                if isinstance(dx, dict):
                    events.append({
                        "type": "大运",
                        "period": f"{dx.get('age', '')}-{dx.get('age', 0) + 9}岁",
                        "pillar": dx.get("pillar", ""),
                        "description": f"大运{dx.get('pillar', '')}",
                        "significance": "major",
                    })
            for ln in liunians[:3]:
                if isinstance(ln, dict):
                    events.append({
                        "type": "流年",
                        "year": str(ln.get("year", "")),
                        "pillar": ln.get("pillar", ""),
                        "description": f"{ln.get('year', '')}年{ln.get('pillar', '')}",
                        "significance": "yearly",
                    })

        zw = systems.get("紫微斗数")
        if zw and zw.available:
            daxian = self._ziwei.get("daxian", [])
            for dx in daxian[:3]:
                if isinstance(dx, dict):
                    events.append({
                        "type": "大限",
                        "period": dx.get("age_range", ""),
                        "gong": dx.get("gong_name", ""),
                        "description": f"大限{dx.get('gong_name', '')}({dx.get('age_range', '')})",
                        "significance": "major",
                    })

        # 按时间排序
        events.sort(key=lambda e: str(e.get("period", e.get("year", ""))))
        return events[:10]

    # ── 建议生成 ──────────────────────────────────────────────────────────

    def _generate_recommendations(
        self,
        systems: Dict[str, SystemAnalysis],
        cross: CrossValidationResult,
        overall_level: str,
    ) -> List[str]:
        """生成个性化建议"""
        recs = []

        bz = systems.get("八字")
        zw = systems.get("紫微斗数")

        if bz and bz.available:
            if bz.yongshen:
                recs.append(f"宜补{'、'.join(bz.yongshen)}五行，可增强运势")
            if bz.risks:
                recs.append(f"注意：{bz.risks[0]}")

        if zw and zw.available:
            if zw.strengths:
                recs.append(f"紫微提示：{zw.strengths[0]}")

        if cross.confidence >= 0.7:
            recs.append("多体系一致性高，建议积极把握当前时机")
        elif cross.confidence < 0.4:
            recs.append("体系间存在分歧，建议保守行事，多方参考")

        if overall_level in ("大吉", "吉"):
            recs.append("整体运势向好，适合开拓进取")
        elif overall_level in ("凶", "大凶"):
            recs.append("当前运势低迷，宜静不宜动，修身养性")

        return recs[:5]

    # ── 融合报告生成 ──────────────────────────────────────────────────────

    def _generate_fusion_report(
        self,
        systems: Dict[str, SystemAnalysis],
        cross: CrossValidationResult,
        overall_score: int,
        overall_level: str,
        events: List[Dict],
        recs: List[str],
    ) -> str:
        """生成融合分析报告"""
        lines = [
            "=" * 60,
            "       三体系融合命理分析报告",
            "=" * 60,
            "",
            "【体系评分】",
        ]

        for name, sa in systems.items():
            status = f"{sa.score}分" if sa.available else f"不可用（{sa.error}）"
            lines.append(f"  {name}：{status}")
            if sa.available and sa.key_findings:
                for f in sa.key_findings[:2]:
                    lines.append(f"    └ {f}")

        lines.extend([
            "",
            "【交叉验证】",
            f"  一致性评分：{cross.agreement_score}/100（{cross.level}）",
            f"  置信度：{cross.confidence:.0%}",
        ])
        if cross.agreements:
            for a in cross.agreements:
                lines.append(f"  ✓ {a}")
        if cross.conflicts:
            for c in cross.conflicts:
                lines.append(f"  ✗ {c}")

        lines.extend([
            "",
            "【综合运势】",
            f"  加权评分：{overall_score}/100",
            f"  运势等级：{overall_level}",
        ])

        if events:
            lines.append("")
            lines.append("【关键节点】")
            for ev in events[:6]:
                lines.append(f"  [{ev['type']}] {ev['description']}")

        if recs:
            lines.append("")
            lines.append("【建议】")
            for i, r in enumerate(recs, 1):
                lines.append(f"  {i}. {r}")

        lines.extend([
            "",
            "=" * 60,
            "  本报告由三体系融合引擎自动生成，仅供参考。",
            "  命运掌握在自己手中，愿您前程似锦！",
            "=" * 60,
        ])

        return "\n".join(lines)

    # ── 主入口 ────────────────────────────────────────────────────────────

    def analyze(self) -> FusionResult:
        """
        执行三体系融合分析

        Returns:
            FusionResult: 包含所有分析结果的融合对象
        """
        systems: Dict[str, SystemAnalysis] = {}

        # 各体系独立分析
        systems["八字"] = self._analyze_bazi()
        systems["紫微斗数"] = self._analyze_ziwei()
        systems["奇门遁甲"] = self._analyze_qimen()

        # 交叉验证
        cross = self._cross_validate(systems)

        # 综合评分
        overall_score, overall_level = self._compute_overall(systems, cross)

        # 关键事件
        events = self._extract_key_events(systems)

        # 建议
        recs = self._generate_recommendations(systems, cross, overall_level)

        # 融合报告
        report = self._generate_fusion_report(
            systems, cross, overall_score, overall_level, events, recs
        )

        # 融合摘要
        available_count = sum(1 for s in systems.values() if s.available)
        fusion_summary = (
            f"三体系融合分析完成（{available_count}/3 体系可用），"
            f"综合评分{overall_score}分，运势{overall_level}，"
            f"体系一致性{cross.level}"
        )

        return FusionResult(
            birth_info=self._birth,
            systems=systems,
            cross_validation=cross,
            overall_score=overall_score,
            overall_level=overall_level,
            fusion_summary=fusion_summary,
            key_events=events,
            recommendations=recs,
            fusion_report=report,
        )


# ============================================================================
# 便捷函数
# ============================================================================

def quick_fusion(
    bazi: Optional[Dict] = None,
    ziwei: Optional[Dict] = None,
    qimen: Optional[Dict] = None,
    birth: Optional[Dict] = None,
    target_year: int = 2026,
) -> FusionResult:
    """快速三体系融合分析"""
    fa = FusionAnalyzer(bazi, ziwei, qimen, birth, target_year)
    return fa.analyze()


__all__ = [
    "FusionAnalyzer",
    "FusionResult",
    "CrossValidationResult",
    "SystemAnalysis",
    "quick_fusion",
    "SYSTEM_WEIGHTS",
    "AGREEMENT_LEVELS",
    "FORTUNE_LEVELS",
]