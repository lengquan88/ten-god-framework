#!/usr/bin/env python3
"""
report_generator.py — 食神·创生输出 · 命理报告自然语言生成器 v1.0.0

整合所有阶段产出，生成结构化的自然语言命理分析报告。

输入源：
  - 第一阶段：BaziAnalyzer（八字排盘/五行/十神/大运/流年）
  - 第四阶段：ShenshaEngine（神煞）、GejuEngine（格局）、YongshenEngine（喜用神）
  - 第五阶段：VectorStore（知识检索增强）

输出格式：
  - 纯文本报告（text_report）
  - Markdown 报告（markdown_report）
  - JSON 结构化报告（json_report）
  - HTML 单文件报告（html_report）

用法：
  >>> from tengod.report_generator import BaziReportGenerator
  >>> gen = BaziReportGenerator(bazi_analyzer)
  >>> print(gen.text_report())
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

__all__ = [
    "BaziReportGenerator",
    "ComprehensiveReportGenerator",
    "generate_report",
    "generate_html_report",
]
__version__ = "1.0.0"


# ============================================================================
# 五行/天干基础数据
# ============================================================================

WUXING_COLORS = {
    "木": "#4CAF50", "火": "#F44336", "土": "#FF9800",
    "金": "#FFD700", "水": "#2196F3",
}

WUXING_EMOJI = {"木": "🌳", "火": "🔥", "土": "🏔️", "金": "⚜️", "水": "💧"}

SHIGAN_DESC = {
    "比肩": "同辈助力，竞争意识强，自我主张明确",
    "劫财": "社交活跃，但需防破财，合作需谨慎",
    "食神": "才艺出众，温和善良，享受生活",
    "伤官": "聪明叛逆，创造力强，但需防口舌是非",
    "正财": "稳定收入，勤俭持家，财运稳健",
    "偏财": "意外之财，投资运强，但不稳定",
    "正官": "正直守法，事业心强，易得贵人相助",
    "七杀": "果断刚强，行动力强，但需防冲动",
    "正印": "学业有成，贵人扶持，心地善良",
    "偏印": "特殊才能，思维独特，但个性孤僻",
}

SHIGAN_ADVICE = {
    "比肩": "宜团队合作，忌单打独斗",
    "劫财": "宜理财规划，忌冲动消费",
    "食神": "宜发挥才艺，忌懒散懈怠",
    "伤官": "宜创新突破，忌锋芒过露",
    "正财": "宜稳健投资，忌投机冒险",
    "偏财": "宜灵活应变，忌贪心不足",
    "正官": "宜遵纪守法，忌越权行事",
    "七杀": "宜果断决策，忌鲁莽冲动",
    "正印": "宜学习进修，忌纸上谈兵",
    "偏印": "宜深度钻研，忌标新立异",
}

WUXING_ADVICE = {
    "木": "宜教育、文化、医疗行业，培养耐心与包容心",
    "火": "宜能源、餐饮、娱乐行业，注意情绪管理",
    "土": "宜地产、建筑、农业行业，培养诚信与稳重",
    "金": "宜金融、法律、科技行业，培养决断力与正义感",
    "水": "宜物流、贸易、传媒行业，培养智慧与变通能力",
}


# ============================================================================
# 报告生成器
# ============================================================================

class BaziReportGenerator:
    """八字命理综合报告生成器

    整合八字排盘、神煞、格局、喜用神、调候等全部信息，
    生成结构化的自然语言命理分析报告。
    """

    def __init__(self, bazi_analyzer=None):
        """
        Args:
            bazi_analyzer: BaziAnalyzer 实例（可选，可后续通过 set_* 方法设置）
        """
        self._analyzer = bazi_analyzer
        self._shensha = None
        self._geju = None
        self._yongshen = None
        self._tiaohou = None
        self._vector_store = None

        if bazi_analyzer is not None:
            self._extract_basic()

    # ── 设置器 ──────────────────────────────────────────────────────────

    def set_analyzer(self, bazi_analyzer) -> None:
        self._analyzer = bazi_analyzer
        self._extract_basic()

    def set_shensha(self, shensha_result) -> None:
        self._shensha = shensha_result

    def set_geju(self, geju_result) -> None:
        self._geju = geju_result

    def set_yongshen(self, yongshen_result) -> None:
        self._yongshen = yongshen_result

    def set_tiaohou(self, tiaohou_result) -> None:
        self._tiaohou = tiaohou_result

    def set_vector_store(self, store) -> None:
        self._vector_store = store

    # ── 数据提取 ──────────────────────────────────────────────────────────

    def _extract_basic(self) -> None:
        a = self._analyzer
        self._year = a.year
        self._month = a.month
        self._day = a.day
        self._hour = a.hour
        self._minute = a.minute
        self._is_male = a.is_male
        self._longitude = a.longitude
        self._chart = a.chart
        self._analysis = a.analysis

    def _safe_get(self, d, key, default=""):
        """安全获取字典值"""
        try:
            return d.get(key, default)
        except AttributeError:
            return getattr(d, key, default)

    # ── 文本报告 ──────────────────────────────────────────────────────────

    def text_report(self) -> str:
        """生成纯文本综合命理报告"""
        lines = []
        lines.extend(self._header_text())
        lines.append("")
        lines.extend(self._basic_info_text())
        lines.append("")
        lines.extend(self._pillars_text())
        lines.append("")
        lines.extend(self._wuxing_text())
        lines.append("")
        lines.extend(self._shigan_text())
        lines.append("")
        lines.extend(self._shensha_text())
        lines.append("")
        lines.extend(self._geju_text())
        lines.append("")
        lines.extend(self._yongshen_text())
        lines.append("")
        lines.extend(self._dayun_text())
        lines.append("")
        lines.extend(self._liunian_text())
        lines.append("")
        lines.extend(self._advice_text())
        lines.append("")
        lines.extend(self._footer_text())
        return "\n".join(lines)

    def _header_text(self) -> List[str]:
        return [
            "╔" + "═" * 58 + "╗",
            "║" + "  八字命理综合分析报告".center(52) + "║",
            "║" + "  食神·创生输出  v1.0.0".center(58) + "║",
            "╚" + "═" * 58 + "╝",
        ]

    def _basic_info_text(self) -> List[str]:
        a = self._analysis
        gender = "男命" if self._is_male else "女命"
        return [
            "▎一、基本信息",
            f"  出生时间：{self._year}年{self._month:02d}月{self._day:02d}日 "
            f"{self._hour:02d}:{self._minute:02d}（{gender}）",
            f"  真太阳时：{self._chart.true_hour:02d}:{self._chart.true_minute:02d} "
            f"（经度 {self._longitude}°）",
            f"  八字四柱：{a['pillars']['year']} {a['pillars']['month']} "
            f"{a['pillars']['day']} {a['pillars']['hour']}",
            f"  日主：{a['day_master']}",
        ]

    def _pillars_text(self) -> List[str]:
        a = self._analysis
        lines = ["▎二、四柱分析"]
        pillar_names = [
            ("年柱", "year", "year_gan"),
            ("月柱", "month", "month_gan"),
            ("日柱", "day", "day"),
            ("时柱", "hour", "hour_gan"),
        ]
        for label, pk, sk in pillar_names:
            pillar = a['pillars'][pk]
            if pk == "day":
                shigan = f"日主 {pillar[0]}"
            else:
                shigan = a['shigan_map'].get(sk, "")
            desc = SHIGAN_DESC.get(shigan, "")
            lines.append(f"  {label}：{pillar}  │  十神：{shigan}")
            if desc:
                lines.append(f"         {desc}")
        return lines

    def _wuxing_text(self) -> List[str]:
        a = self._analysis
        lines = ["▎三、五行分析"]
        lines.append("  五行分布：")
        for wx in ["木", "火", "土", "金", "水"]:
            score = a['wuxing_score'].get(wx, "-")
            emoji = WUXING_EMOJI.get(wx, "")
            lines.append(f"    {emoji} {wx}：{score}")

        # 旺衰判断
        sorted_wx = sorted(a['wuxing'].items(), key=lambda x: -x[1])
        if sorted_wx:
            top_wx = sorted_wx[0][0]
            advice = WUXING_ADVICE.get(top_wx, "")
            lines.append(f"  最旺五行：{top_wx}")
            if advice:
                lines.append(f"    {advice}")

        missing = [wx for wx in ["木", "火", "土", "金", "水"] if a['wuxing'].get(wx, 0) == 0]
        if missing:
            lines.append(f"  缺失五行：{'、'.join(missing)}（需通过喜用神调和）")

        return lines

    def _shigan_text(self) -> List[str]:
        a = self._analysis
        lines = ["▎四、十神分析"]
        good = sum(a['shigan_count'].get(s, 0) for s in ["正官", "正印", "正财", "食神", "比肩"])
        bad = sum(a['shigan_count'].get(s, 0) for s in ["七杀", "伤官", "劫财", "偏印", "偏财"])
        lines.append(f"  善神：{good} 个  │  凶神：{bad} 个")
        if good > bad:
            lines.append("  十神以善神为主，整体格局温和稳固，为人正直善良。")
        elif bad > good:
            lines.append("  十神中凶神偏多，行动力与决断力较强，但需注意人际关系与情绪管理。")
        else:
            lines.append("  善恶平衡，性格刚柔并济，宜灵活应对不同局面。")

        lines.append("  十神分布：")
        for sg, cnt in sorted(a['shigan_count'].items(), key=lambda x: -x[1]):
            desc = SHIGAN_DESC.get(sg, "")
            lines.append(f"    {sg}：{cnt} 个 — {desc}")

        return lines

    def _shensha_text(self) -> List[str]:
        lines = ["▎五、神煞分析"]
        if self._shensha is None:
            lines.append("  （未加载神煞数据）")
            return lines

        s = self._shensha
        all_s = s.all_shensha
        ji_list = [(n, v) for n, v in all_s.items() if v.get("cat") in ("吉神", "吉")]
        xiong_list = [(n, v) for n, v in all_s.items() if v.get("cat") in ("凶", "大凶")]
        ping_list = [(n, v) for n, v in all_s.items() if v.get("cat") == "平"]

        lines.append(f"  共 {len(all_s)} 种神煞：吉神 {len(ji_list)} 个，凶神 {len(xiong_list)} 个，中性 {len(ping_list)} 个")

        if ji_list:
            lines.append("  【吉神】")
            for name, info in ji_list[:8]:
                lines.append(f"    ☆ {name}（{info.get('pillar', '')}）：{info.get('desc', '')}")

        if xiong_list:
            lines.append("  【凶神/警示】")
            for name, info in xiong_list[:6]:
                lines.append(f"    ✗ {name}（{info.get('pillar', '')}）：{info.get('desc', '')}")

        return lines

    def _geju_text(self) -> List[str]:
        lines = ["▎六、格局分析"]
        if self._geju is None:
            lines.append("  （未加载格局数据）")
            return lines

        g = self._geju
        lines.append(f"  格局名称：{g.geju_name}")
        lines.append(f"  格局类型：{g.geju_type}")
        lines.append(f"  格局纯度：{g.score:.1f}/100")
        lines.append(f"  格局解读：{g.geju_desc}")

        if g.is_cong:
            lines.append("  特殊格局：从格（命局某一五行极旺，从旺而从）")
        if g.is_huaqi:
            lines.append("  特殊格局：化气格（天干五合化气成格）")

        if g.shiyongshen:
            lines.append(f"  适用神：{', '.join(g.shiyongshen)}")
        if g.jishen:
            lines.append(f"  忌神：{', '.join(g.jishen)}")

        return lines

    def _yongshen_text(self) -> List[str]:
        lines = ["▎七、喜用神与调候"]
        if self._yongshen is None and self._tiaohou is None:
            lines.append("  （未加载喜用神/调候数据）")
            return lines

        if self._yongshen:
            y = self._yongshen
            lines.append(f"  日主旺衰：{y.wang_shuai}（强度：{y.wang_shuai_level:.0f}/100）")
            if y.yong_shen:
                lines.append(f"  用神（有益五行）：{', '.join(y.yong_shen)}")
            if y.ji_shen:
                lines.append(f"  忌神（不利五行）：{', '.join(y.ji_shen)}")
            lines.append(f"  分析：{y.yongshen_desc}")

        if self._tiaohou:
            t = self._tiaohou
            lines.append(f"  调候需求：{'需要' if t.required_tiaohou else '不需'}调候（季节：{t.season}）")
            if t.tiaohou_shens:
                lines.append(f"  调候用神：{', '.join(t.tiaohou_shens)}")
            if t.desc:
                lines.append(f"  调候说明：{t.desc}")

        return lines

    def _dayun_text(self) -> List[str]:
        a = self._analysis
        lines = ["▎八、大运分析（每步十年）"]
        try:
            from tengod.dayun_liunian import derive_shigan
        except ImportError:
            derive_shigan = lambda dm, g: ""

        for du in a['dayuns'][:5]:
            gan_shigan = derive_shigan(a['day_master'], du['pillar'][0])
            lines.append(
                f"  {du['age']:>3d}-{du['age']+9:>3d}岁 "
                f"（{du['start_year']}-{du['start_year']+9}）"
                f"  {du['pillar']}  [{gan_shigan}]"
            )
        return lines

    def _liunian_text(self) -> List[str]:
        a = self._analysis
        lines = ["▎九、近期流年"]
        for ln in a['liunians'][:6]:
            lines.append(
                f"  {ln['year']}年：{ln['pillar']}  [{ln['gan_shigan']}]"
            )
        return lines

    def _advice_text(self) -> List[str]:
        lines = ["▎十、综合建议"]
        a = self._analysis
        day_master = a['day_master']

        # 基于日主五行的建议
        try:
            from tengod.dayun_liunian import GAN_WUXING
            dm_wx = GAN_WUXING.get(day_master, "")
        except ImportError:
            dm_wx = ""

        if dm_wx:
            lines.append(f"  日主{day_master}属{dm_wx}，{WUXING_ADVICE.get(dm_wx, '')}")

        # 基于喜用神
        if self._yongshen:
            y = self._yongshen
            if y.yong_shen:
                lines.append(f"  宜补充：{', '.join(y.yong_shen)}")
            if y.ji_shen:
                lines.append(f"  宜避免：{', '.join(y.ji_shen)}")

        # 基于最强十神
        if a['shigan_count']:
            top_shigan = max(a['shigan_count'], key=lambda k: a['shigan_count'][k])
            advice = SHIGAN_ADVICE.get(top_shigan, "")
            if advice:
                lines.append(f"  十神建议：{advice}")

        # 基于五行缺失
        missing = [wx for wx in ["木", "火", "土", "金", "水"] if a['wuxing'].get(wx, 0) == 0]
        if missing:
            lines.append(f"  补缺建议：命局缺少{'、'.join(missing)}，可通过名字、方位、颜色、职业等方面补充")

        return lines

    def _footer_text(self) -> List[str]:
        return [
            "",
            "─" * 60,
            f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "本报告由 食神·创生输出 引擎自动生成，仅供参考。",
            "─" * 60,
        ]

    # ── Markdown 报告 ──────────────────────────────────────────────────────

    def markdown_report(self) -> str:
        """生成 Markdown 格式报告"""
        lines = []
        lines.append("# 八字命理综合分析报告")
        lines.append("")
        lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"> 引擎版本：食神·创生输出 v{__version__}")
        lines.append("")

        gender = "男命" if self._is_male else "女命"
        a = self._analysis

        lines.append("## 一、基本信息")
        lines.append("")
        lines.append(f"- **出生时间**：{self._year}年{self._month:02d}月{self._day:02d}日 {self._hour:02d}:{self._minute:02d}（{gender}）")
        lines.append(f"- **真太阳时**：{self._chart.true_hour:02d}:{self._chart.true_minute:02d}（经度 {self._longitude}°）")
        lines.append(f"- **八字四柱**：`{a['pillars']['year']}` `{a['pillars']['month']}` `{a['pillars']['day']}` `{a['pillars']['hour']}`")
        lines.append(f"- **日主**：{a['day_master']}")
        lines.append("")

        lines.append("## 二、四柱分析")
        lines.append("")
        pillar_names = [
            ("年柱", "year", "year_gan"), ("月柱", "month", "month_gan"),
            ("日柱", "day", "day"), ("时柱", "hour", "hour_gan"),
        ]
        for label, pk, sk in pillar_names:
            pillar = a['pillars'][pk]
            if pk == "day":
                shigan = f"日主 {pillar[0]}"
            else:
                shigan = a['shigan_map'].get(sk, "")
            lines.append(f"- **{label}**：`{pillar}` — {shigan}")
        lines.append("")

        lines.append("## 三、五行分析")
        lines.append("")
        lines.append("| 五行 | 数量 | 评分 | 状态 |")
        lines.append("|------|------|------|------|")
        for wx in ["木", "火", "土", "金", "水"]:
            count = a['wuxing'].get(wx, 0)
            score = a['wuxing_score'].get(wx, "-")
            lines.append(f"| {WUXING_EMOJI.get(wx, '')} {wx} | {count} | {score} | |")
        lines.append("")

        lines.append("## 四、十神分析")
        lines.append("")
        for sg, cnt in sorted(a['shigan_count'].items(), key=lambda x: -x[1]):
            desc = SHIGAN_DESC.get(sg, "")
            lines.append(f"- **{sg}**：{cnt} 个 — {desc}")
        lines.append("")

        if self._shensha:
            lines.append("## 五、神煞分析")
            lines.append("")
            all_s = self._shensha.all_shensha
            ji_list = [(n, v) for n, v in all_s.items() if v.get("cat") in ("吉神", "吉")]
            xiong_list = [(n, v) for n, v in all_s.items() if v.get("cat") in ("凶", "大凶")]
            lines.append(f"共 {len(all_s)} 种神煞（吉 {len(ji_list)} / 凶 {len(xiong_list)}）")
            lines.append("")
            if ji_list:
                lines.append("### 吉神")
                for name, info in ji_list[:5]:
                    lines.append(f"- **{name}**（{info.get('pillar', '')}）：{info.get('desc', '')}")
            if xiong_list:
                lines.append("### 凶神/警示")
                for name, info in xiong_list[:5]:
                    lines.append(f"- **{name}**（{info.get('pillar', '')}）：{info.get('desc', '')}")
            lines.append("")

        if self._geju:
            g = self._geju
            lines.append("## 六、格局分析")
            lines.append("")
            lines.append(f"- **格局**：{g.geju_name}（{g.geju_type}）")
            lines.append(f"- **纯度**：{g.score:.1f}/100")
            lines.append(f"- **解读**：{g.geju_desc}")
            lines.append("")

        if self._yongshen:
            y = self._yongshen
            lines.append("## 七、喜用神与调候")
            lines.append("")
            lines.append(f"- **日主状态**：{y.wang_shuai}（{y.wang_shuai_level:.0f}/100）")
            if y.yong_shen:
                lines.append(f"- **用神**：{', '.join(y.yong_shen)}")
            if y.ji_shen:
                lines.append(f"- **忌神**：{', '.join(y.ji_shen)}")
            lines.append("")

        lines.append("## 八、综合建议")
        lines.append("")
        if self._yongshen and self._yongshen.yong_shen:
            lines.append(f"宜补充：{', '.join(self._yongshen.yong_shen)}")
        else:
            lines.append("请根据五行平衡和十神分布综合判断。")
        lines.append("")

        lines.append("---")
        lines.append(f"*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("*本报告由 食神·创生输出 引擎自动生成，仅供参考。*")

        return "\n".join(lines)

    # ── JSON 报告 ──────────────────────────────────────────────────────────

    def json_report(self) -> Dict[str, Any]:
        """生成 JSON 结构化报告"""
        a = self._analysis
        report = {
            "meta": {
                "version": __version__,
                "generated_at": datetime.now().isoformat(),
                "engine": "食神·创生输出",
            },
            "basic": {
                "year": self._year,
                "month": self._month,
                "day": self._day,
                "hour": self._hour,
                "minute": self._minute,
                "is_male": self._is_male,
                "longitude": self._longitude,
                "true_solar_time": f"{self._chart.true_hour:02d}:{self._chart.true_minute:02d}",
                "pillars": a['pillars'],
                "day_master": a['day_master'],
            },
            "wuxing": {
                "distribution": a['wuxing'],
                "scores": a['wuxing_score'],
            },
            "shigan": {
                "distribution": a['shigan_count'],
                "map": {k: v for k, v in a['shigan_map'].items() if k != "day"},
            },
            "shensha": self._shensha.json_report() if self._shensha else None,
            "geju": {
                "name": self._geju.geju_name,
                "type": self._geju.geju_type,
                "desc": self._geju.geju_desc,
                "score": self._geju.score,
                "is_cong": self._geju.is_cong,
                "is_huaqi": self._geju.is_huaqi,
            } if self._geju else None,
            "yongshen": {
                "wang_shuai": self._yongshen.wang_shuai,
                "yong_shen": self._yongshen.yong_shen,
                "ji_shen": self._yongshen.ji_shen,
                "desc": self._yongshen.yongshen_desc,
            } if self._yongshen else None,
            "tiaohou": {
                "required": self._tiaohou.required_tiaohou,
                "tiaohou_shens": self._tiaohou.tiaohou_shens,
                "season": self._tiaohou.season,
                "desc": self._tiaohou.desc,
            } if self._tiaohou else None,
            "dayun": a['dayuns'][:5],
            "liunian": a['liunians'][:6],
            "conclusion": a['conclusion'],
        }
        return report

    # ── HTML 报告 ──────────────────────────────────────────────────────────

    def html_report(self) -> str:
        """生成 HTML 单文件报告"""
        return _HTML_TEMPLATE.format(
            title=f"{self._year}-{self._month:02d}-{self._day:02d} "
                  f"{'男命' if self._is_male else '女命'}八字命理报告",
            version=__version__,
            generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            body=self.markdown_report(),
        )


# ============================================================================
# HTML 模板
# ============================================================================

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif;
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    color: #e0e0e0; min-height: 100vh; padding: 20px;
    line-height: 1.8;
  }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  h1 {{
    text-align: center; font-size: 28px; margin: 20px 0 10px;
    background: linear-gradient(90deg, #f5d76e, #e8b14f);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }}
  h2 {{
    font-size: 18px; color: #f5d76e; margin: 24px 0 12px;
    border-bottom: 1px solid rgba(245,215,110,0.2); padding-bottom: 6px;
  }}
  blockquote {{
    border-left: 3px solid rgba(245,215,110,0.3); padding: 4px 12px;
    margin: 8px 0; color: #8e9aaf; font-size: 13px;
  }}
  table {{ width: 100%; border-collapse: collapse; margin: 8px 0; }}
  th, td {{
    padding: 8px 12px; border: 1px solid rgba(255,255,255,0.1);
    text-align: left; font-size: 14px;
  }}
  th {{ background: rgba(245,215,110,0.1); color: #f5d76e; }}
  code {{
    background: rgba(255,255,255,0.06); padding: 1px 6px;
    border-radius: 4px; font-size: 14px; color: #fff5d6;
  }}
  ul, ol {{ padding-left: 20px; }}
  li {{ margin: 4px 0; font-size: 14px; }}
  hr {{ border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 20px 0; }}
  .footer {{ text-align: center; color: #6e7a8f; font-size: 12px; margin-top: 30px; }}
</style>
</head>
<body>
<div class="container">
<h1>{title}</h1>
<div class="footer">引擎版本：{version} | 生成时间：{generated_at}</div>
<hr>
{body}
</div>
</body>
</html>"""


# ============================================================================
# 便捷函数
# ============================================================================

def generate_report(bazi_analyzer,
                    shensha_result=None,
                    geju_result=None,
                    yongshen_result=None,
                    tiaohou_result=None) -> str:
    """便捷函数：生成完整文本报告

    Args:
        bazi_analyzer: BaziAnalyzer 实例
        shensha_result: ShenshaResult 实例（可选）
        geju_result: GejuResult 实例（可选）
        yongshen_result: YongshenResult 实例（可选）
        tiaohou_result: TiaohouResult 实例（可选）

    Returns:
        str: 完整的文本报告
    """
    gen = BaziReportGenerator(bazi_analyzer)
    if shensha_result:
        gen.set_shensha(shensha_result)
    if geju_result:
        gen.set_geju(geju_result)
    if yongshen_result:
        gen.set_yongshen(yongshen_result)
    if tiaohou_result:
        gen.set_tiaohou(tiaohou_result)
    return gen.text_report()


def generate_html_report(bazi_analyzer,
                         shensha_result=None,
                         geju_result=None,
                         yongshen_result=None,
                         tiaohou_result=None) -> str:
    """便捷函数：生成 HTML 报告

    Args:
        bazi_analyzer: BaziAnalyzer 实例
        shensha_result: ShenshaResult 实例
        geju_result: GejuResult 实例
        yongshen_result: YongshenResult 实例
        tiaohou_result: TiaohouResult 实例

    Returns:
        str: HTML 报告字符串
    """
    gen = BaziReportGenerator(bazi_analyzer)
    if shensha_result:
        gen.set_shensha(shensha_result)
    if geju_result:
        gen.set_geju(geju_result)
    if yongshen_result:
        gen.set_yongshen(yongshen_result)
    if tiaohou_result:
        gen.set_tiaohou(tiaohou_result)
    return gen.html_report()


# ============================================================================
# 自测
# ============================================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")

    from tengod.bazi_analyzer import BaziAnalyzer
    from tengod.shensha_engine import calc_all_shensha
    from tengod.geju_engine import calc_geju, calc_yongshen, calc_tiaohou

    # 示例八字
    analyzer = BaziAnalyzer(1990, 6, 15, 10, 30, is_male=True, longitude=116.4)
    shensha = calc_all_shensha(analyzer.analysis['pillars'])
    geju = calc_geju(analyzer.analysis['pillars'])
    yongshen = calc_yongshen(analyzer.analysis['pillars'])
    tiaohou = calc_tiaohou(analyzer.analysis['pillars'])

    gen = BaziReportGenerator(analyzer)
    gen.set_shensha(shensha)
    gen.set_geju(geju)
    gen.set_yongshen(yongshen)
    gen.set_tiaohou(tiaohou)

    print(gen.text_report())
    print("\n\n=== JSON Report ===")
    print(json.dumps(gen.json_report(), ensure_ascii=False, indent=2))


# ============================================================================
# 阶段二十四：多体系综合报告生成器
# ============================================================================

class ComprehensiveReportGenerator:
    """
    多体系综合报告生成器

    输入：ComprehensiveResult.to_dict() 字典
    输出：text / markdown / html / json 格式综合报告

    用法：
        >>> from tengod.report_generator import ComprehensiveReportGenerator
        >>> gen = ComprehensiveReportGenerator(comp_result.to_dict())
        >>> print(gen.markdown_report())
    """

    def __init__(self, comp_dict: Dict[str, Any]):
        self._d = comp_dict
        self._birth = comp_dict.get("birth_info", {})
        self._systems = comp_dict.get("systems", {})
        self._cross = comp_dict.get("cross_validation", {})
        self._consensus = comp_dict.get("consensus", {})
        self._raw_report = comp_dict.get("comprehensive_report", "")

    def _level_bar(self, score: int) -> str:
        """将 0-100 分数转换为星级条"""
        filled = min(5, max(0, round(score / 20)))
        return "★" * filled + "☆" * (5 - filled)

    def text_report(self) -> str:
        """纯文本综合报告"""
        lines = []
        gender_cn = "男" if self._birth.get("gender") == "male" else "女"
        year = self._birth.get("target_year", "")

        lines.append("=" * 60)
        lines.append("      多体系综合命理分析报告")
        lines.append(f"      分析年份：{year}  |  性别：{gender_cn}")
        lines.append("=" * 60)
        lines.append("")

        # 共识运势
        overall = self._consensus.get("overall", "—")
        score = self._consensus.get("score", 0)
        lines.append("【共识运势】")
        lines.append(f"  综合等级：{overall}  {self._level_bar(score)}")
        lines.append(f"  综合评分：{score}/100")
        lines.append("")
        for label, key in [
            ("事业", "career"), ("财运", "wealth"),
            ("感情", "relationships"), ("健康", "health"),
        ]:
            val = self._consensus.get(key, "—") or "—"
            lines.append(f"  {label}：{val}")
        strengths = self._consensus.get("key_strengths", [])
        if strengths:
            lines.append(f"  优势：{'、'.join(strengths)}")
        risks = self._consensus.get("key_risks", [])
        if risks:
            lines.append(f"  风险：{'、'.join(risks)}")
        best = self._consensus.get("best_timing", [])
        if best:
            lines.append(f"  最佳时机：{'、'.join(best)}")
        lines.append("")

        # 交叉验证
        cross_score = self._cross.get("score", 0)
        cross_level = self._cross.get("level", "—")
        lines.append("【交叉验证】")
        lines.append(f"  一致性：{cross_score}/100  ({cross_level})")
        agreed = self._cross.get("agreements", [])
        conflicts = self._cross.get("conflicts", [])
        if agreed:
            lines.append(f"  一致体系：{'、'.join(agreed)}")
        if conflicts:
            lines.append(f"  分歧体系：{'、'.join(conflicts)}")
        interp = self._cross.get("interpretations", [])
        for p in interp:
            lines.append(f"  解读：{p}")
        lines.append("")

        # 各体系结果
        lines.append("【各体系分析结果】")
        for name, sys_data in self._systems.items():
            if isinstance(sys_data, dict):
                lines.append(f"  ■ {name}")
                if sys_data.get("available") is False:
                    lines.append(f"    [不可用] {sys_data.get('error', '')}")
                else:
                    summary = sys_data.get("summary", "")
                    if summary:
                        lines.append(f"    {summary}")
                lines.append("")
        lines.append("")

        # 原始报告
        if self._raw_report:
            lines.append("【综合分析】")
            lines.append(self._raw_report[:600])
            if len(self._raw_report) > 600:
                lines.append(f"  ... (共 {len(self._raw_report)} 字)")
        lines.append("")
        lines.append("=" * 60)
        lines.append("  本报告由多体系综合分析引擎生成，仅供参考")
        lines.append("=" * 60)
        return "\n".join(lines)

    def markdown_report(self) -> str:
        """Markdown 格式综合报告"""
        gender_cn = "男" if self._birth.get("gender") == "male" else "女"
        year = self._birth.get("target_year", "")
        overall = self._consensus.get("overall", "—")
        score = self._consensus.get("score", 0)
        cross_score = self._cross.get("score", 0)
        cross_level = self._cross.get("level", "—")

        md = [
            "# 多体系综合命理分析报告",
            "",
            f"**分析年份**：{year}  &nbsp;&nbsp; **性别**：{gender_cn}",
            "",
            "---",
            "",
            "## 一、共识运势",
            "",
            "| 等级 | 评分 | ★评级 |",
            "| --- | --- | --- |",
            f"| {overall} | {score}/100 | {self._level_bar(score)} |",
            "",
            "### 分项研判",
            "",
            "| 事业 | 财运 | 感情 | 健康 |",
            "| --- | --- | --- | --- |",
            f"| {self._consensus.get('career', '—')} | "
            f"{self._consensus.get('wealth', '—')} | "
            f"{self._consensus.get('relationships', '—')} | "
            f"{self._consensus.get('health', '—')} |",
            "",
        ]

        strengths = self._consensus.get("key_strengths", [])
        if strengths:
            md.append(f"**核心优势**：{'、'.join(strengths)}")
        risks = self._consensus.get("key_risks", [])
        if risks:
            md.append(f"**核心风险**：{'、'.join(risks)}")
        best = self._consensus.get("best_timing", [])
        if best:
            md.append(f"**最佳时机**：{'、'.join(best)}")
        md.append("")

        md.extend([
            "---",
            "",
            "## 二、交叉验证",
            "",
            f"**一致性**：{cross_score}/100（{cross_level}）",
            "",
        ])
        agreed = self._cross.get("agreements", [])
        conflicts = self._cross.get("conflicts", [])
        if agreed:
            md.append(f"**一致体系**：{'、'.join(agreed)}")
        if conflicts:
            md.append(f"**分歧体系**：{'、'.join(conflicts)}")
        interp = self._cross.get("interpretations", [])
        for p in interp:
            md.append(f"- {p}")
        md.append("")

        md.extend([
            "---",
            "",
            "## 三、各体系分析结果",
            "",
        ])
        for name, sys_data in self._systems.items():
            if isinstance(sys_data, dict):
                available = sys_data.get("available", True)
                status = "✅" if available else "❌"
                summary = sys_data.get("summary", "（无摘要）")
                md.append(f"### {status} {name}")
                md.append(f"{summary}")
                if not available:
                    md.append(f"> 错误：{sys_data.get('error', '')}")
                md.append("")

        if self._raw_report:
            md.extend([
                "---",
                "",
                "## 四、综合分析",
                "",
                self._raw_report,
                "",
            ])

        md.extend([
            "---",
            "",
            "*本报告由多体系综合分析引擎生成，仅供参考*",
        ])
        return "\n".join(md)

    def json_report(self) -> Dict[str, Any]:
        """JSON 格式综合报告"""
        return {
            "birth_info": self._birth,
            "consensus": self._consensus,
            "cross_validation": self._cross,
            "systems": {
                k: v if isinstance(v, dict) else {}
                for k, v in self._systems.items()
            },
            "raw_report": self._raw_report,
            "summary": {
                "overall": self._consensus.get("overall", "—"),
                "score": self._consensus.get("score", 0),
                "cross_score": self._cross.get("score", 0),
                "agreed_count": len(self._cross.get("agreements", [])),
                "system_count": len(self._systems),
            },
        }

    def html_report(self) -> str:
        """HTML 格式综合报告（单文件，可直接用浏览器打开）"""
        md = self.markdown_report()
        # 简单 Markdown → HTML 转换（完整版需引入 markdown 库）
        html_body = md.replace("# ", "<h1>").replace("\n## ", "</h1>\n<h2>").replace(
            "\n### ", "</h2>\n<h3>").replace("\n", "<br/>")
        html_body = (
            html_body.replace("**", "")
            .replace("| ", "<tr><td>").replace(" |", "</td></tr>")
            .replace(" | ", "</td><td>")
            .replace("---\n", "<hr/>")
        )
        return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8"/>
<title>多体系综合命理分析报告</title>
<style>
body{{font-family:serif;max-width:800px;margin:2rem auto;padding:0 1rem;
      background:#1a1a1a;color:#c9b99a;line-height:1.8}}
h1,h2,h3{{color:#d4af37;border-bottom:1px solid #4a4a4a;padding-bottom:.3em}}
h1{{font-size:1.6em;text-align:center}}h2{{font-size:1.2em}}h3{{font-size:1em}}
table{{border-collapse:collapse;width:100%;margin:.5rem 0}}
td,th{{border:1px solid #4a4a4a;padding:.4rem .6rem}}
hr{{border:none;border-top:1px solid #4a4a4a;margin:1.5rem 0}}
blockquote{{background:#252525;border-left:3px solid #d4af37;padding:.5rem 1rem}}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
