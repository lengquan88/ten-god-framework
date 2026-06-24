"""
visualization.py — 阶段二十八：高级可视化
=======================================
功能:
  1. BaziChartRenderer    — 八字图表渲染（ASCII / SVG / JSON
  2. TrajectoryVisualizer — 命运轨迹可视化
  3. ZiweiStarMap       — 紫微斗数命盘可视化
  4. LiuyaoHexagramDisplay — 六爻卦象显示
  5. QimenBoard        — 奇门遁甲九宫布局
  6. InteractiveWidgetSpec — 前端组件规格
  7. ThemeSystem      — 主题系统
  8. Export utilities   — 导出工具
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 7. 主题系统
# ---------------------------------------------------------------------------


@dataclass
class ThemeConfig:
    name: str
    primary: str
    secondary: str
    accent: str
    background: str
    text: str
    text_muted: str
    font_family: str = "sans-serif"

    def as_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "primary": self.primary,
            "secondary": self.secondary,
            "accent": self.accent,
            "background": self.background,
            "text": self.text,
            "text_muted": self.text_muted,
            "font_family": self.font_family,
        }


THEMES: Dict[str, ThemeConfig] = {
    "light": ThemeConfig(
        name="light",
        primary="#2b6cb0",
        secondary="#4a5568",
        accent="#d69e2e",
        background="#ffffff",
        text="#1a202c",
        text_muted="#718096",
    ),
    "dark": ThemeConfig(
        name="dark",
        primary="#63b3ed",
        secondary="#a0aec0",
        accent="#ecc94b",
        background="#1a202c",
        text="#e2e8f0",
        text_muted="#a0aec0",
    ),
    "high-contrast": ThemeConfig(
        name="high-contrast",
        primary="#000000",
        secondary="#333333",
        accent="#ff0000",
        background="#ffffff",
        text="#000000",
        text_muted="#000000",
    ),
    "traditional": ThemeConfig(
        name="traditional",
        primary="#2d1f10",
        secondary="#5c3a1e",
        accent="#8b1a1a",
        background="#f5ecd7",
        text="#1a0f08",
        text_muted="#6b4423",
        font_family="serif",
    ),
}


def apply_theme(chart_data: Dict[str, Any], theme_name: str = "light") -> Dict[str, Any]:
    """将主题色应用于图表数据"""
    theme = THEMES.get(theme_name, THEMES["light"])
    out = dict(chart_data)
    out["theme"] = theme.as_dict()
    if "colors" in out and isinstance(out["colors"], dict):
        out["colors"] = {**out["colors"], "primary": theme.primary, "accent": theme.accent}
    return out


# ---------------------------------------------------------------------------
# 五行颜色映射
# ---------------------------------------------------------------------------

WUXING_COLORS = {
    "金": "#c9b072",   # 金色
    "木": "#5aa469",   # 绿色
    "水": "#4a90e2",   # 蓝色
    "火": "#e25858",   # 红色
    "土": "#c9a66b",   # 土黄色
}

WUXING_LIST = ["金", "木", "水", "火", "土"]

GAN_ZHI_ELEMENT = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
    "子": "水", "丑": "土",
    "寅": "木", "卯": "木",
    "辰": "土", "巳": "火",
    "午": "火", "未": "土",
    "申": "金", "酉": "金",
    "戌": "土", "亥": "水",
}


# ---------------------------------------------------------------------------
# 1. BaziChartRenderer
# ---------------------------------------------------------------------------


class BaziChartRenderer:
    """八字图表渲染器"""

    @staticmethod
    def get_colors_by_wuxing(element: str) -> str:
        return WUXING_COLORS.get(element, "#888888")

    @classmethod
    def render_json_chart(cls, pillars: Dict[str, str]) -> Dict[str, Any]:
        pillar_keys = ["year", "month", "day", "hour"]
        pillar_labels = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}
        result_pillars = []
        for i, key in enumerate(pillar_keys):
            text = pillars.get(key, "")
            stem = text[0] if len(text) >= 1 else ""
            branch = text[1] if len(text) >= 2 else ""
            el_stem = GAN_ZHI_ELEMENT.get(stem, "")
            el_branch = GAN_ZHI_ELEMENT.get(branch, "")
            result_pillars.append({
                "index": i,
                "key": key,
                "label": pillar_labels.get(key, key),
                "stem": stem,
                "branch": branch,
                "stem_element": el_stem,
                "branch_element": el_branch,
                "stem_color": cls.get_colors_by_wuxing(el_stem),
                "branch_color": cls.get_colors_by_wuxing(el_branch),
            })
        return {
            "type": "bazi_chart",
            "pillars": result_pillars,
            "colors": dict(WUXING_COLORS),
        }

    @classmethod
    def render_ascii(cls, pillars: Dict[str, str], day_master: str = "") -> str:
        lines = []
        lines.append("=" * 48)
        lines.append(f" 八字命盘{'（日主：' + day_master + '）' if day_master else ' 八字命盘'}")
        lines.append("=" * 48)
        pillar_keys = ["year", "month", "day", "hour"]
        labels = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}
        header = "  ".join([f"{labels[k]:>6}" for k in pillar_keys])
        stems = "  ".join([f"{pillars.get(k, '')[0]:>6}" if len(pillars.get(k, '')) >= 1 else f"{'':>6}" for k in pillar_keys])
        branches = "  ".join([f"{pillars.get(k, '')[1]:>6}" if len(pillars.get(k, '')) >= 2 else f"{'':>6}" for k in pillar_keys])
        lines.append(header)
        lines.append("-" * 48)
        lines.append(stems)
        lines.append(branches)
        lines.append("=" * 48)
        return "\n".join(lines)

    @classmethod
    def render_svg(
        cls, pillars: Dict[str, str], day_master: str = "", geju: Optional[Dict[str, Any]] = None, analysis: Optional[Dict[str, Any]] = None) -> str:
        chart_data = cls.render_json_chart(pillars)
        theme = THEMES.get("traditional")
        pillar_items = chart_data["pillars"]
        width = 480
        height = 260
        cell_w = width / 4
        svg_parts = [
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<rect x="0" y="0" width="{width}" height="{height}" fill="{theme.background}"/>'
        ]
        for i, pillar in enumerate(pillar_items):
            x = i * cell_w + 20
            svg_parts.append(
                f'<g transform="translate({x}, 40)">'
                f'<text x="40" y="10" text-anchor="middle" font-family="{theme.font_family}" font-size="14" fill="{theme.text}">{pillar["label"]}</text>'
                f'<circle cx="40" cy="70" r="32" fill="{pillar["stem_color"]}" opacity="0.3"/>'
                f'<text x="40" y="76" text-anchor="middle" font-size="28" fill="{theme.text}">{pillar["stem"]}</text>'
                f'<circle cx="40" cy="140" r="32" fill="{pillar["branch_color"]}" opacity="0.3"/>'
                f'<text x="40" y="146" text-anchor="middle" font-size="28" fill="{theme.text}">{pillar["branch"]}</text>'
                f'</g>'
            )
        if day_master:
            svg_parts.append(
                f'<text x="{width/2}" y="230" text-anchor="middle" font-size="14" fill="{theme.text_muted}">日主: {html.escape(day_master)}</text>'
            )
        svg_parts.append('</svg>')
        return "".join(svg_parts)

    @classmethod
    def add_interactive_hints(cls, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """为图表数据添加交互式提示（hover/tooltip）"""
        hints: Dict[str, str] = {}
        for pillar in chart_data.get("pillars", []):
            key = pillar.get("key", "")
            hints[key] = (
                f"{pillar.get('label', key)}: {pillar.get('stem', '')}{pillar.get('branch', '')} "
                f"(天干: {pillar.get('stem_element', '')}, 地支: {pillar.get('branch_element', '')})"
            )
        chart_data["hints"] = hints
        return chart_data


# ---------------------------------------------------------------------------
# 2. TrajectoryVisualizer
# ---------------------------------------------------------------------------


class TrajectoryVisualizer:
    """命运轨迹可视化"""

    DIMENSIONS = ["事业", "财富", "健康", "感情", "学业", "人际"]

    @classmethod
    def generate_line_chart(
        cls,
        trajectory_data: Optional[Dict[str, Any]] = None,
        year_range: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        if year_range is None:
            year_range = [2020, 2021, 2022, 2023, 2024, 2025]
        if trajectory_data is None:
            trajectory_data = {}
        points = []
        for year in year_range:
            score = trajectory_data.get(str(year), 50 + (year % 7) * 5)
            points.append({"year": year, "score": score})
        return {
            "type": "line_chart",
            "x_label": "年份",
            "y_label": "运势评分",
            "data": points,
            "years": list(year_range),
        }

    @classmethod
    def generate_heatmap(
        cls,
        trajectory_data: Optional[Dict[str, Any]] = None,
        year_range: Optional[List[int]] = None,
        element: str = "wood",
    ) -> Dict[str, Any]:
        if year_range is None:
            year_range = [2020, 2021, 2022, 2023, 2024, 2025]
        if trajectory_data is None:
            trajectory_data = {}
        cells = []
        for month in range(1, 13):
            for year in year_range:
                key = f"{year}-{month:02d}"
                score = trajectory_data.get(key, 40 + ((year + month) % 60))
                cells.append({"year": year, "month": month, "score": score})
        return {
            "type": "heatmap",
            "element": element,
            "cells": cells,
            "years": list(year_range),
        }

    @classmethod
    def generate_radar_chart(
        cls,
        analysis_scores: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        if analysis_scores is None:
            analysis_scores = {}
        axes = []
        for dim in cls.DIMENSIONS:
            score = float(analysis_scores.get(dim, 60.0))
            axes.append({"dimension": dim, "score": score})
        return {
            "type": "radar_chart",
            "dimensions": cls.DIMENSIONS,
            "axes": axes,
        }

    @classmethod
    def generate_bar_chart(
        cls,
        distribution: Optional[Dict[str, int]] = None,
        title: str = "分布",
    ) -> Dict[str, Any]:
        if distribution is None:
            distribution = {}
        labels = list(distribution.keys()) or ["A", "B", "C", "D", "E"]
        if not distribution:
            values = [10, 20, 15, 25, 30]
        else:
            values = [int(distribution.get(lbl, 0)) for lbl in labels]
        return {
            "type": "bar_chart",
            "title": title,
            "labels": labels,
            "values": values,
        }


# ---------------------------------------------------------------------------
# 3. ZiweiStarMap
# ---------------------------------------------------------------------------


ZIWEI_PALACE_NAMES = [
    "命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄",
    "迁移", "交友", "官禄", "田宅", "福德", "父母",
]

ZIWEI_MAIN_STARS = [
    "紫微", "天机", "太阳", "武曲", "天同",
    "廉贞", "天府", "太阴", "贪狼", "巨门",
    "天相", "天梁", "七杀", "破军",
]


class ZiweiStarMap:
    """紫微斗数命盘可视化"""

    @classmethod
    def generate_palace_layout(cls, palace_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if palace_data is None:
            palace_data = {}
        palaces = []
        for i, name in enumerate(ZIWEI_PALACE_NAMES):
            stars = palace_data.get(name, [])
            if not stars:
                stars = [ZIWEI_MAIN_STARS[i % len(ZIWEI_MAIN_STARS)]]
            palaces.append({
                "index": i,
                "name": name,
                "main_stars": stars[:2],
                "aux_stars": [f"辅星{j+1}" for j in range(2)],
                "position": {"row": i // 4, "col": i % 4},
            })
        return palaces

    @classmethod
    def generate_interactive_stars(cls, palace_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        palaces = cls.generate_palace_layout(palace_data)
        result = []
        for palace in palaces:
            for star_name in palace["main_stars"]:
                result.append({
                    "star": star_name,
                    "palace": palace["name"],
                    "position": palace["position"],
                    "tooltip": f"{star_name} 星位于 {palace['name']}",
                    "is_main": True,
                })
        return result

    @classmethod
    def generate_major_transits(cls, current_year: int = 2025) -> Dict[str, Any]:
        offset = current_year % 12
        return {
            "current_year": current_year,
            "大运": [
                {
                    "index": i,
                    "start_year": current_year + i * 10,
                    "palace_name": ZIWEI_PALACE_NAMES[(offset + i) % 12],
                }
                for i in range(6)
            ],
        }


# ---------------------------------------------------------------------------
# 4. LiuyaoHexagramDisplay
# ---------------------------------------------------------------------------


class LiuyaoHexagramDisplay:
    """六爻卦象显示"""

    TRIGRAMS = {
        "乾": "111", "兑": "011", "离": "101", "震": "001",
        "巽": "110", "坎": "010", "艮": "100", "坤": "000",
    }

    @classmethod
    def render_hexagram(cls, yao_data: Optional[List[int]] = None) -> Dict[str, Any]:
        if yao_data is None:
            yao_data = [1, 0, 1, 1, 0, 1]
        lines = []
        for i, v in enumerate(yao_data):
            lines.append({
                "position": i + 1,
                "value": int(v),
                "is_changing": False,
            })
        binary = "".join([str(int(v)) for v in yao_data])
        return {
            "type": "hexagram",
            "lines": lines,
            "binary": binary,
            "yao_count": len(yao_data),
        }

    @classmethod
    def render_changing_lines(
        cls,
        original_yang: Optional[List[int]] = None,
        changing_yin: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        if original_yang is None:
            original_yang = [1, 1, 1, 1, 1, 1]
        if changing_yin is None:
            changing_yin = [0, 0, 0, 0, 0, 0]
        lines = []
        for i in range(6):
            orig = original_yang[i]
            chg = changing_yin[i]
            is_changing = orig != chg
            lines.append({
                "position": i + 1,
                "original_value": int(orig),
                "changed_value": int(chg),
                "is_changing": is_changing,
            })
        return {
            "type": "changing_hexagram",
            "lines": lines,
            "changing_count": sum(1 for line in lines if line["is_changing"]),
        }

    @classmethod
    def render_hexagram_pair(
        cls,
        primary_hex: Optional[List[int]] = None,
        transformed_hex: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        if primary_hex is None:
            primary_hex = [1, 0, 1, 1, 0, 1]
        if transformed_hex is None:
            transformed_hex = [0, 1, 0, 0, 1, 0]
        return {
            "type": "hexagram_pair",
            "primary": cls.render_hexagram(primary_hex),
            "transformed": cls.render_hexagram(transformed_hex),
            "changes": [i + 1 for i in range(6) if primary_hex[i] != transformed_hex[i]],
        }


# ---------------------------------------------------------------------------
# 5. QimenBoard
# ---------------------------------------------------------------------------


QIMEN_DIRECTIONS = ["坎", "坤", "震", "巽", "中", "乾", "兑", "艮", "离"]
# 九宫顺序：一坎 二坤 三震 四巽 五中 六乾 七兑 八艮 九离
QIMEN_PALACES = ["一宫", "二宫", "三宫", "四宫", "五宫", "六宫", "七宫", "八宫", "九宫"]


class QimenBoard:
    """奇门遁甲可视化"""

    @classmethod
    def render_nine_palace_board(cls, board_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if board_data is None:
            board_data = {}
        palaces = []
        # 3x3 grid
        # 正确的奇门九宫布局
        layout = [
            (0, 0, 4, "巽"),
            (0, 1, 9, "离"),
            (0, 2, 2, "坤"),
            (1, 0, 3, "震"),
            (1, 1, 5, "中"),
            (1, 2, 7, "兑"),
            (2, 0, 8, "艮"),
            (2, 1, 1, "坎"),
            (2, 2, 6, "乾"),
        ]
        for row, col, num, direction in layout:
            palaces.append({
                "row": row,
                "col": col,
                "number": num,
                "direction": direction,
                "name": f"{num}宫",
                "stars": board_data.get(f"{num}宫", []),
            })
        return {
            "type": "qimen_board",
            "grid_size": 3,
            "palaces": palaces,
        }

    @classmethod
    def render_shensha_overlays(cls, board_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if board_data is None:
            board_data = {}
        shensha_list = ["值符", "螣蛇", "太阴", "六合", "白虎", "玄武", "九地", "九天"]
        overlays = []
        for i, s in enumerate(shensha_list):
            overlays.append({
                "shensha": s,
                "palace_index": (i + 1) % 9,
                "position": {"row": i // 3, "col": i % 3},
            })
        return {
            "type": "shensha_overlays",
            "overlays": overlays,
        }

    @classmethod
    def render_time_dimension(cls, year: int = 2025, month: int = 1, day: int = 1, hour: int = 0) -> Dict[str, Any]:
        segments = []
        for h in range(12):
            segments.append({
                "hour": h * 2,
                "label": f"{h * 2:02d}:00",
                "active": h == hour // 2,
            })
        return {
            "type": "time_dimension",
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "segments": segments,
        }


# ---------------------------------------------------------------------------
# 6. InteractiveWidgetSpec
# ---------------------------------------------------------------------------


class InteractiveWidgetSpec:
    """前端组件规格生成器"""

    @classmethod
    def build_bazi_widget_spec(cls, pillars: Dict[str, str]) -> Dict[str, Any]:
        chart = BaziChartRenderer.render_json_chart(pillars)
        chart = BaziChartRenderer.add_interactive_hints(chart)
        return {
            "widget_type": "bazi_chart",
            "version": "1.0",
            "title": "八字命盘",
            "data": chart,
            "interactive": True,
        }

    @classmethod
    def build_trajectory_widget_spec(cls, trajectory: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if trajectory is None:
            trajectory = {}
        return {
            "widget_type": "trajectory_chart",
            "version": "1.0",
            "title": "命运轨迹",
            "data": {
                "line_chart": TrajectoryVisualizer.generate_line_chart(trajectory),
                "radar_chart": TrajectoryVisualizer.generate_radar_chart(),
            },
            "interactive": True,
        }

    @classmethod
    def build_hexagram_widget_spec(cls, yao: Optional[List[int]] = None) -> Dict[str, Any]:
        return {
            "widget_type": "hexagram_chart",
            "version": "1.0",
            "title": "六爻卦象",
            "data": LiuyaoHexagramDisplay.render_hexagram(yao),
            "interactive": True,
        }

    @classmethod
    def build_ziwei_widget_spec(cls, palace_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "widget_type": "ziwei_chart",
            "title": "紫微斗数命盘",
            "version": "1.0",
            "data": {
                "palaces": ZiweiStarMap.generate_palace_layout(palace_data),
                "stars": ZiweiStarMap.generate_interactive_stars(palace_data),
            },
            "interactive": True,
        }

    @classmethod
    def build_qimen_widget_spec(cls, board_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "widget_type": "qimen_chart",
            "version": "1.0",
            "title": "奇门遁甲九宫",
            "data": {
                "board": QimenBoard.render_nine_palace_board(board_data),
                "shensha": QimenBoard.render_shensha_overlays(board_data),
            },
            "interactive": True,
        }


# ---------------------------------------------------------------------------
# 8. Export utilities
# ---------------------------------------------------------------------------


def export_to_png(svg_content: str, output_path: str = "") -> str:
    """将 SVG 转换为 PNG 图片

    Args:
        svg_content: SVG 字符串
        output_path: 输出路径（可选）

    Returns:
        str: 成功时返回文件路径，失败时返回 SVG 内容
    """
    try:
        import cairosvg
        png_data = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'))
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(png_data)
            return output_path
        else:
            out_path = "/tmp/export.png"
            with open(out_path, 'wb') as f:
                f.write(png_data)
            return out_path
    except ImportError:
        # cairosvg 未安装时回退
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            return output_path
        return svg_content


def export_to_html(chart_name: str, chart_html_or_data: Any = None) -> str:
    """将图表或数据导出为独立 HTML 页面"""
    if chart_html_or_data is None:
        chart_html_or_data = {}
    if isinstance(chart_html_or_data, str):
        body = chart_html_or_data
    else:
        try:
            body = f"<pre>{html.escape(json.dumps(chart_html_or_data, ensure_ascii=False, indent=2))}</pre>"
        except Exception:
            body = str(chart_html_or_data)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh-CN">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        f"  <title>{html.escape(chart_name)}</title>\n"
        "</head>\n"
        "<body>\n"
        f"  <h1>{html.escape(chart_name)}</h1>\n"
        f"  <div>{body}</div>\n"
        "</body>\n"
        "</html>\n"
    )


def generate_share_image(bazi_data: Dict[str, Any], score: float = 75.0, theme: str = "traditional") -> Dict[str, Any]:
    """生成分享就绪的图片数据（SVG/图片元数据）"""
    return {
        "format": "svg",
        "width": 800,
        "height": 600,
        "theme": theme,
        "score": float(score),
        "bazi_data": bazi_data,
    }
