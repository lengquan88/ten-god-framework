"""
report_generator.py — 门禁报告生成器 v4.6.0
=================================================
道曰："信言不美，美言不信。"

自动生成门禁报告：十二神裁决、七论可视化、混沌海存疑。

核心能力：
  - 自动生成门禁裁决报告（Markdown/JSON）
  - 七论裁决可视化数据
  - 混沌海存疑汇总
  - 十二神门禁综合评估
  - 五行生克影响分析
  - 报告版本化与归档
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import json
import time
import uuid

from .tbce_unit import GateState
from .twelve_gods_base import TwelveGods, FiveElements, GOD_ELEMENT_MAP


# ============================================================================
# 报告组件
# ============================================================================

@dataclass
class GateReportSection:
    """门禁报告章节"""
    title: str
    level: int  # 1-6 Header级别
    content: str
    data: Optional[Dict] = None
    subsections: List["GateReportSection"] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "level": self.level,
            "content": self.content,
            "data": self.data,
            "subsections": [s.to_dict() for s in self.subsections],
        }


@dataclass
class GateReport:
    """门禁综合报告"""
    report_id: str
    title: str
    version: str = "2.34.0"
    generated_at: float = field(default_factory=time.time)
    sections: List[GateReportSection] = field(default_factory=list)
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "report_id": self.report_id,
            "title": self.title,
            "version": self.version,
            "generated_at": self.generated_at,
            "sections": [s.to_dict() for s in self.sections],
            "summary": self.summary,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }


# ============================================================================
# 报告生成器
# ============================================================================

class ReportGenerator:
    """门禁报告生成器 v2.34.0

    自动生成门禁裁决报告，支持：
    - 十二神门禁综合评估
    - 七论裁决可视化
    - 混沌海存疑汇总
    - 五行生克影响分析
    - Markdown/JSON 双格式输出
    """

    VERSION = "2.34.0"

    def __init__(self):
        self._report_history: List[GateReport] = []
        self._max_history = 100

    # ── 报告生成 ──────────────────────────────────────────────────────

    def generate_report(
        self,
        title: str = "十二神门禁综合评估报告",
        gate_verdicts: Optional[Dict[str, Any]] = None,
        unit_info: Optional[Dict[str, Any]] = None,
        include_seven_theories: bool = True,
        include_chaos_sea: bool = True,
        include_element_analysis: bool = True,
    ) -> GateReport:
        """生成门禁综合报告

        Args:
            title: 报告标题
            gate_verdicts: 门禁裁决结果 {god_name: verdict_dict}
            unit_info: 认知单元信息
            include_seven_theories: 是否包含七论分析
            include_chaos_sea: 是否包含混沌海分析
            include_element_analysis: 是否包含五行分析

        Returns:
            GateReport 完整报告
        """
        report_id = f"report_{uuid.uuid4().hex[:12]}"
        report = GateReport(
            report_id=report_id,
            title=title,
            metadata={
                "unit_info": unit_info or {},
                "gate_count": len(gate_verdicts) if gate_verdicts else 0,
            },
        )

        # 1. 摘要
        if gate_verdicts:
            report.summary = self._generate_summary(gate_verdicts)
            report.recommendations = self._generate_recommendations(gate_verdicts)

        # 2. 十二神门禁裁决
        if gate_verdicts:
            report.sections.append(self._build_gate_verdicts_section(gate_verdicts))

        # 3. 五行生克分析
        if include_element_analysis and gate_verdicts:
            report.sections.append(self._build_element_analysis_section(gate_verdicts))

        # 4. 七论裁决
        if include_seven_theories:
            report.sections.append(self._build_seven_theories_section())

        # 5. 混沌海存疑
        if include_chaos_sea:
            report.sections.append(self._build_chaos_sea_section())

        # 6. 综合建议
        if report.recommendations:
            report.sections.append(self._build_recommendations_section(report.recommendations))

        self._report_history.append(report)
        if len(self._report_history) > self._max_history:
            self._report_history = self._report_history[-self._max_history:]

        return report

    # ── 摘要生成 ──────────────────────────────────────────────────────

    def _generate_summary(self, verdicts: Dict[str, Any]) -> str:
        """生成报告摘要"""
        total = len(verdicts)
        open_count = sum(1 for v in verdicts.values() if v.get("state") == GateState.OPEN)
        pending_count = sum(1 for v in verdicts.values() if v.get("state") == GateState.PENDING)
        closed_count = sum(1 for v in verdicts.values() if v.get("state") == GateState.CLOSED)

        pass_rate = open_count / max(1, total)

        # 五行通过率
        elem_stats = {}
        for name, v in verdicts.items():
            elem = v.get("element", "未知")
            if elem not in elem_stats:
                elem_stats[elem] = {"total": 0, "open": 0}
            elem_stats[elem]["total"] += 1
            if v.get("state") == GateState.OPEN:
                elem_stats[elem]["open"] += 1

        summary_parts = [
            f"## 执行摘要",
            f"",
            f"- **裁决时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **门禁总数**: {total}（十二神门禁体系）",
            f"- **通过**: {open_count} | **待定**: {pending_count} | **关闭**: {closed_count}",
            f"- **整体通过率**: {pass_rate:.1%}",
            f"",
        ]

        if closed_count > 0:
            closed_gates = [n for n, v in verdicts.items() if v.get("state") == GateState.CLOSED]
            summary_parts.append(f"- **未通过门禁**: {', '.join(closed_gates)}")
            summary_parts.append("")

        # 五行分布
        summary_parts.append("### 五行分布")
        summary_parts.append("")
        summary_parts.append("| 五行 | 通过率 | 状态 |")
        summary_parts.append("|------|--------|------|")
        for elem, stats in sorted(elem_stats.items()):
            rate = stats["open"] / max(1, stats["total"])
            status = "✅" if rate >= 0.5 else "⚠️" if rate > 0 else "❌"
            summary_parts.append(f"| {elem} | {rate:.0%} | {status} |")

        if pass_rate >= 0.7:
            summary_parts.append("")
            summary_parts.append("**结论**: 系统整体健康，门禁体系运行正常。")
        elif pass_rate >= 0.5:
            summary_parts.append("")
            summary_parts.append("**结论**: 系统存在一定风险，建议关注未通过门禁。")
        else:
            summary_parts.append("")
            summary_parts.append("**结论**: 系统存在严重问题，需要立即干预。")

        return "\n".join(summary_parts)

    # ── 建议生成 ──────────────────────────────────────────────────────

    def _generate_recommendations(self, verdicts: Dict[str, Any]) -> List[str]:
        """生成建议"""
        recs = []

        for name, v in verdicts.items():
            state = v.get("state", GateState.CLOSED)
            score = v.get("score", 0.0)
            reason = v.get("reason", "")

            if state == GateState.CLOSED:
                recs.append(f"**{name}门禁关闭**: {reason[:100]}，建议优先修复")
            elif state == GateState.PENDING:
                if score < 0.5:
                    recs.append(f"**{name}门禁待定**: 分数 {score:.2f}，建议复查")

        # 检查五行平衡
        element_issues = self._check_element_balance(verdicts)
        recs.extend(element_issues)

        if not recs:
            recs.append("所有门禁运行正常，无需特别关注。")

        return recs

    def _check_element_balance(self, verdicts: Dict[str, Any]) -> List[str]:
        """检查五行平衡"""
        recs = []
        elem_stats = {}
        for name, v in verdicts.items():
            elem = v.get("element", "未知")
            if elem not in elem_stats:
                elem_stats[elem] = {"total": 0, "open": 0}
            elem_stats[elem]["total"] += 1
            if v.get("state") == GateState.OPEN:
                elem_stats[elem]["open"] += 1

        for elem, stats in elem_stats.items():
            rate = stats["open"] / max(1, stats["total"])
            if rate == 0 and stats["total"] > 0:
                recs.append(f"**{elem}行失衡**: 所有{elem}行门禁均未通过，五行生克链断裂")
            elif rate < 0.5:
                recs.append(f"**{elem}行偏弱**: {elem}行门禁通过率仅{rate:.0%}")

        return recs

    # ── 报告章节构建 ──────────────────────────────────────────────────

    def _build_gate_verdicts_section(
        self, verdicts: Dict[str, Any]
    ) -> GateReportSection:
        """构建门禁裁决章节"""
        section = GateReportSection(
            title="十二神门禁裁决",
            level=1,
            content="以下为十二神门禁体系对当前认知单元的裁决结果。",
            data={"verdicts": verdicts},
        )

        # 按元素分组
        by_element: Dict[str, List[Tuple[str, Dict]]] = {}
        for name, v in verdicts.items():
            elem = v.get("element", "未知")
            if elem not in by_element:
                by_element[elem] = []
            by_element[elem].append((name, v))

        for elem, items in sorted(by_element.items()):
            # 统计
            total = len(items)
            open_count = sum(1 for _, v in items if v.get("state") == GateState.OPEN)
            pass_rate = open_count / total

            content_lines = [
                f"### {elem}行门禁（通过率: {pass_rate:.0%}）",
                "",
                "| 神位 | 状态 | 分数 | 五行加成 | 裁决理由 |",
                "|------|------|------|----------|----------|",
            ]

            for name, v in items:
                state = v.get("state", "closed")
                state_icon = "✅" if state == GateState.OPEN else "⏳" if state == GateState.PENDING else "❌"
                score = v.get("score", 0.0)
                boost = v.get("element_boost", 0.0)
                reason = v.get("reason", "")[:60]

                content_lines.append(
                    f"| {name} | {state_icon} | {score:.2f} | {boost:+.2f} | {reason} |"
                )

            subsection = GateReportSection(
                title=f"{elem}行门禁",
                level=2,
                content="\n".join(content_lines),
                data={"element": elem, "pass_rate": pass_rate},
            )
            section.subsections.append(subsection)

        return section

    def _build_element_analysis_section(
        self, verdicts: Dict[str, Any]
    ) -> GateReportSection:
        """构建五行生克分析章节"""
        section = GateReportSection(
            title="五行生克影响分析",
            level=1,
            content="分析五行生克关系对门禁裁决的加成影响。",
        )

        # 计算生克加成
        generating_cycle = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
        overcoming_cycle = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

        content_lines = [
            "### 相生链（生成→被生）",
            "",
            "| 生者五行 | 被生五行 | 生者通过率 | 被生者通过率 | 加成效果 |",
            "|----------|----------|------------|-------------|----------|",
        ]

        for gen, gened in generating_cycle.items():
            gen_verdicts = [v for n, v in verdicts.items() if v.get("element") == gen]
            gened_verdicts = [v for n, v in verdicts.items() if v.get("element") == gened]

            gen_rate = (sum(1 for v in gen_verdicts if v.get("state") == GateState.OPEN) /
                        max(1, len(gen_verdicts)))
            gened_rate = (sum(1 for v in gened_verdicts if v.get("state") == GateState.OPEN) /
                          max(1, len(gened_verdicts)))

            boost = min(gen_rate * 0.15, 0.15)  # 最大加成15%
            effect = "✅ 有效" if boost > 0.05 else "⚠️ 不足" if gen_rate > 0 else "❌ 无加成"

            content_lines.append(
                f"| {gen} | {gened} | {gen_rate:.0%} | {gened_rate:.0%} | {boost:.2f} {effect} |"
            )

        content_lines.extend([
            "",
            "### 相克链（克制→被克）",
            "",
            "| 克者五行 | 被克五行 | 克者通过率 | 被克者通过率 | 抑制效果 |",
            "|----------|----------|------------|-------------|----------|",
        ])

        for over, overed in overcoming_cycle.items():
            over_verdicts = [v for n, v in verdicts.items() if v.get("element") == over]
            overed_verdicts = [v for n, v in verdicts.items() if v.get("element") == overed]

            over_rate = (sum(1 for v in over_verdicts if v.get("state") == GateState.OPEN) /
                         max(1, len(over_verdicts)))
            overed_rate = (sum(1 for v in overed_verdicts if v.get("state") == GateState.OPEN) /
                           max(1, len(overed_verdicts)))

            penalty = min(over_rate * 0.1, 0.1)
            effect = "⚠️ 抑制" if penalty > 0.03 else "— 正常"

            content_lines.append(
                f"| {over} | {overed} | {over_rate:.0%} | {overed_rate:.0%} | {penalty:.2f} {effect} |"
            )

        section.content = "\n".join(content_lines)
        return section

    def _build_seven_theories_section(self) -> GateReportSection:
        """构建七论裁决章节"""
        section = GateReportSection(
            title="七论裁决器分析",
            level=1,
            content="认知成像的七论裁决器分析结果。",
        )

        try:
            from .seven_theories_judge import get_seven_theories_judge
            judge = get_seven_theories_judge()
            history = judge.get_verdict_history()

            if history:
                content_lines = [
                    "| 论域 | 裁决数 | 通过数 | 通过率 | 状态 |",
                    "|------|--------|--------|--------|------|",
                ]

                theories = ["ontology", "epistemology", "practice", "realm",
                           "future", "metacognition", "chaos_sea"]
                theory_names = ["本体论", "认识论", "实践论", "境界论",
                               "未来论", "元认知", "混沌海"]

                for t, name in zip(theories, theory_names):
                    t_records = [r for r in history if r.get("theory") == t]
                    total = len(t_records)
                    passed = sum(1 for r in t_records if r.get("passed"))
                    rate = passed / max(1, total)
                    status = "✅" if rate >= 0.7 else "⚠️" if rate >= 0.4 else "❌"

                    content_lines.append(
                        f"| {name} | {total} | {passed} | {rate:.0%} | {status} |"
                    )

                section.content = "\n".join(content_lines)
            else:
                section.content = "七论裁决器尚无裁决记录。"
        except Exception:
            section.content = "七论裁决器不可用。"

        return section

    def _build_chaos_sea_section(self) -> GateReportSection:
        """构建混沌海存疑章节"""
        section = GateReportSection(
            title="混沌海存疑汇总",
            level=1,
            content="",
        )

        try:
            from .hundun_sea import HundunSea
            sea = HundunSea()
            trails = sea.get_trails(limit=20)

            if trails:
                content_lines = [
                    f"混沌海共收录 **{len(trails)}** 条存疑记录。",
                    "",
                    "| 路径 | 置信度 | 时间 |",
                    "|------|--------|------|",
                ]

                for t in trails:
                    route = t.get("route", "未知")[:50]
                    conf = t.get("confidence", 0.0)
                    ts = t.get("timestamp", 0)
                    time_str = time.strftime("%m-%d %H:%M", time.localtime(ts)) if ts else "—"

                    content_lines.append(f"| {route} | {conf:.2f} | {time_str} |")

                section.content = "\n".join(content_lines)
            else:
                section.content = "混沌海当前无存疑记录。系统运行正常。"
        except Exception:
            section.content = "混沌海不可用。"

        return section

    def _build_recommendations_section(
        self, recommendations: List[str]
    ) -> GateReportSection:
        """构建综合建议章节"""
        content_lines = ["## 综合建议", ""]
        for i, rec in enumerate(recommendations, 1):
            content_lines.append(f"{i}. {rec}")

        return GateReportSection(
            title="综合建议",
            level=1,
            content="\n".join(content_lines),
            data={"recommendations": recommendations},
        )

    # ── 输出格式 ──────────────────────────────────────────────────────

    def to_markdown(self, report: GateReport) -> str:
        """将报告转换为 Markdown 格式"""
        lines = [
            f"# {report.title}",
            f"",
            f"**报告ID**: {report.report_id}",
            f"**版本**: {report.version}",
            f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report.generated_at))}",
            f"",
            "---",
            f"",
        ]

        # 摘要
        lines.append(report.summary)
        lines.append("")
        lines.append("---")
        lines.append("")

        # 各章节
        for section in report.sections:
            lines.append(self._section_to_markdown(section))

        return "\n".join(lines)

    def _section_to_markdown(self, section: GateReportSection) -> str:
        """将章节转换为 Markdown"""
        prefix = "#" * min(section.level, 6)
        lines = [f"{prefix} {section.title}", ""]

        if section.content:
            lines.append(section.content)
            lines.append("")

        for sub in section.subsections:
            lines.append(self._section_to_markdown(sub))

        return "\n".join(lines)

    def to_json(self, report: GateReport) -> str:
        """将报告转换为 JSON 格式"""
        return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, default=str)

    # ── 报告查询 ──────────────────────────────────────────────────────

    def get_report(self, report_id: str) -> Optional[Dict]:
        """按ID获取报告"""
        for report in self._report_history:
            if report.report_id == report_id:
                return report.to_dict()
        return None

    def get_recent_reports(self, limit: int = 10) -> List[Dict]:
        """获取最近报告"""
        return [r.to_dict() for r in self._report_history[-limit:]]

    def reset(self) -> None:
        """重置报告生成器"""
        self._report_history.clear()


# ============================================================================
# 全局单例
# ============================================================================

_report_generator: Optional[ReportGenerator] = None


def get_report_generator() -> ReportGenerator:
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator


def reset_report_generator() -> None:
    global _report_generator
    _report_generator = None


__all__ = [
    "GateReportSection",
    "GateReport",
    "ReportGenerator",
    "get_report_generator",
    "reset_report_generator",
]