"""
交互式命盘可视化器 v2.1
======================
中华文明数字永生体 · 用户体验优化

功能：
- 交互式命盘展示
- 实时数据更新
- 响应式设计支持
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from html import escape
import json


def _esc(value: Any) -> str:
    """HTML 转义用户输入，防止 XSS"""
    return escape(str(value)) if value is not None else ""


@dataclass
class VisualizationConfig:
    """可视化配置"""
    theme: str = "classic"  # classic/modern/minimal
    show_shensha: bool = True
    show_wuxing: bool = True
    show_geju: bool = True
    language: str = "zh"  # zh/en
    interactive: bool = True


class BaziChartVisualizer:
    """八字命盘可视化器"""

    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()

    def generate_html(self, bazi_data: Dict[str, Any]) -> str:
        """
        生成交互式HTML命盘

        Args:
            bazi_data: 八字数据

        Returns:
            str: HTML内容
        """
        pillars = bazi_data.get("pillars", {})
        wuxing = bazi_data.get("wuxing", {})
        geju = bazi_data.get("geju", "")
        shensha = bazi_data.get("shensha", [])

        html = f"""
<!DOCTYPE html>
<html lang="{self.config.language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>八字命盘 - TenGod v2.1</title>
    <style>
        :root {{
            --primary-color: #8B4513;
            --secondary-color: #D4AF37;
            --bg-color: #F5F5DC;
            --text-color: #333;
        }}
        
        body {{
            font-family: 'Microsoft YaHei', sans-serif;
            background: var(--bg-color);
            margin: 0;
            padding: 20px;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .header {{
            text-align: center;
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        .pillars {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin: 30px 0;
        }}
        
        .pillar {{
            background: var(--bg-color);
            border: 2px solid var(--primary-color);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            transition: transform 0.3s;
        }}
        
        .pillar:hover {{
            transform: scale(1.05);
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}
        
        .pillar-title {{
            font-size: 1.2em;
            color: var(--primary-color);
            margin-bottom: 10px;
        }}
        
        .pillar-content {{
            font-size: 2em;
            font-weight: bold;
            color: var(--text-color);
        }}
        
        .wuxing-chart {{
            display: flex;
            justify-content: space-around;
            margin: 30px 0;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 8px;
        }}
        
        .wuxing-item {{
            text-align: center;
            padding: 10px;
        }}
        
        .wuxing-bar {{
            width: 60px;
            background: var(--primary-color);
            border-radius: 4px;
            margin: 10px auto;
        }}
        
        .info-section {{
            margin: 20px 0;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 8px;
        }}
        
        .info-title {{
            color: var(--primary-color);
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .shensha-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        
        .shensha-tag {{
            background: var(--secondary-color);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
        }}
        
        @media (max-width: 600px) {{
            .pillars {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>八字命盘</h1>
            <p>TenGod Framework v2.1</p>
        </div>
        
        <div class="pillars">
            <div class="pillar" onclick="showDetail('year')">
                <div class="pillar-title">年柱</div>
                <div class="pillar-content">{_esc(pillars.get('year', '--'))}</div>
            </div>
            <div class="pillar" onclick="showDetail('month')">
                <div class="pillar-title">月柱</div>
                <div class="pillar-content">{_esc(pillars.get('month', '--'))}</div>
            </div>
            <div class="pillar" onclick="showDetail('day')">
                <div class="pillar-title">日柱</div>
                <div class="pillar-content">{_esc(pillars.get('day', '--'))}</div>
            </div>
            <div class="pillar" onclick="showDetail('hour')">
                <div class="pillar-title">时柱</div>
                <div class="pillar-content">{_esc(pillars.get('hour', '--'))}</div>
            </div>
        </div>
        
        {self._generate_wuxing_html(wuxing) if self.config.show_wuxing else ''}
        
        {self._generate_geju_html(geju) if self.config.show_geju else ''}
        
        {self._generate_shensha_html(shensha) if self.config.show_shensha else ''}
    </div>
    
    <script>
        function showDetail(pillar) {{
            alert('点击查看' + pillar + '柱详细信息');
        }}
    </script>
</body>
</html>
"""
        return html

    def _generate_wuxing_html(self, wuxing: Dict[str, int]) -> str:
        """生成五行分布HTML"""
        max_val = max(wuxing.values()) if wuxing else 1
        items = []
        for wx in ["木", "火", "土", "金", "水"]:
            val = wuxing.get(wx, 0)
            height = int((val / max_val) * 100) if max_val > 0 else 0
            items.append(f"""
            <div class="wuxing-item">
                <div>{wx}</div>
                <div class="wuxing-bar" style="height: {height}px;"></div>
                <div>{val}</div>
            </div>
            """)
        return f"""
        <div class="wuxing-chart">
            {"".join(items)}
        </div>
        """

    def _generate_geju_html(self, geju: str) -> str:
        """生成格局HTML"""
        return f"""
        <div class="info-section">
            <div class="info-title">格局</div>
            <div>{_esc(geju) or '未判断'}</div>
        </div>
        """

    def _generate_shensha_html(self, shensha: List[str]) -> str:
        """生成神煞HTML"""
        tags = "".join([f'<span class="shensha-tag">{_esc(s)}</span>' for s in shensha])
        return f"""
        <div class="info-section">
            <div class="info-title">神煞</div>
            <div class="shensha-tags">
                {tags or '<span>无特殊神煞</span>'}
            </div>
        </div>
        """

    def generate_json(self, bazi_data: Dict[str, Any]) -> str:
        """
        生成JSON数据（供前端渲染）

        Args:
            bazi_data: 八字数据

        Returns:
            str: JSON字符串
        """
        return json.dumps(bazi_data, ensure_ascii=False, indent=2)


class ZiweiChartVisualizer:
    """紫微斗数可视化器 — 完整 12 宫位渲染"""

    # 地支 → 4x4 网格位置 (row, col)
    # 传统紫微命盘布局：子居右下，逆时针排列
    _ZHI_GRID = {
        "巳": (0, 0), "午": (0, 1), "未": (0, 2), "申": (0, 3),
        "辰": (1, 0),                         "酉": (1, 3),
        "卯": (2, 0),                         "戌": (2, 3),
        "寅": (3, 0), "丑": (3, 1), "子": (3, 2), "亥": (3, 3),
    }

    # 主星颜色映射
    _STAR_COLORS = {
        "紫微": "#8B0000", "天机": "#4169E1", "太阳": "#FF8C00", "武曲": "#B8860B",
        "天同": "#20B2AA", "廉贞": "#DC143C", "天府": "#DAA520", "太阴": "#4169E1",
        "贪狼": "#9932CC", "巨门": "#696969", "天相": "#2E8B57", "天梁": "#D2691E",
        "七杀": "#800000", "破军": "#4682B4",
    }

    # 四化标记颜色
    _SIHUA_COLORS = {"禄": "#DAA520", "权": "#DC143C", "科": "#2E8B57", "忌": "#696969"}

    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()

    def generate_html(self, ziwei_data: Dict[str, Any], lang: str = "zh-CN") -> str:
        """
        生成完整紫微命盘 HTML

        Args:
            ziwei_data: ZiweiEngine.to_dict() 返回的命盘数据
            lang: 语言代码 (zh-CN/zh-TW/en)

        Returns:
            str: 完整 HTML 页面
        """
        from tengod.i18n import t

        gongs = ziwei_data.get("gongs", [])
        sihua = ziwei_data.get("sihua", {})
        daxian_list = ziwei_data.get("daxian", [])
        ming_idx = ziwei_data.get("ming_gong", {}).get("index", 0)
        shen_idx = ziwei_data.get("shen_gong", {}).get("index", 0)

        # 构建 zhi → gong 映射
        zhi_to_gong = {}
        for i, g in enumerate(gongs):
            zhi = g.get("ganzhi", "")[-1]  # 取地支
            zhi_to_gong[zhi] = (g, i)

        # 构建 daxian gong_index → age_range 映射
        dx_map = {}
        for dx in daxian_list:
            dx_map[dx.get("gong_index", -1)] = dx.get("age_range", "")

        # 生成 4x4 网格
        grid = [[None] * 4 for _ in range(4)]
        for zhi, (row, col) in self._ZHI_GRID.items():
            gong_data, gong_idx = zhi_to_gong.get(zhi, (None, None))
            if gong_data:
                is_ming = (gong_idx == ming_idx)
                is_shen = (gong_idx == shen_idx)
                dx_range = dx_map.get(gong_idx, "")
                grid[row][col] = self._render_palace(gong_data, gong_idx, is_ming, is_shen, dx_range, lang)

        # 中心区域
        center_html = self._render_center(ziwei_data, lang)

        # 组装网格 HTML
        cells = []
        for row in range(4):
            for col in range(4):
                if row in (1, 2) and col in (1, 2):
                    if row == 1 and col == 1:
                        cells.append(f'<div class="zw-center" style="grid-area:{row+1}/{col+1}/{row+3}/{col+3}">{center_html}</div>')
                elif grid[row][col]:
                    cells.append(grid[row][col])

        title = t("紫微斗数命盘", lang)
        html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - TenGod v2.4</title>
    <style>
        :root {{
            --zw-bg: #0a0a0f;
            --zw-card: #1a1a2e;
            --zw-border: #8B4513;
            --zw-text: #e0e0e0;
            --zw-gold: #DAA520;
            --zw-red: #DC143C;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            background: var(--zw-bg);
            color: var(--zw-text);
            padding: 10px;
        }}
        .zw-container {{
            max-width: 720px;
            margin: 0 auto;
        }}
        .zw-header {{
            text-align: center;
            padding: 15px 0;
            border-bottom: 1px solid var(--zw-border);
        }}
        .zw-header h1 {{
            font-size: 1.4em;
            color: var(--zw-gold);
            letter-spacing: 4px;
        }}
        .zw-header .info {{
            font-size: 0.8em;
            color: #888;
            margin-top: 5px;
        }}
        .zw-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            grid-template-rows: repeat(4, auto);
            gap: 2px;
            background: var(--zw-border);
            border: 2px solid var(--zw-border);
            border-radius: 4px;
            overflow: hidden;
        }}
        .zw-palace {{
            background: var(--zw-card);
            padding: 8px 6px;
            min-height: 100px;
            display: flex;
            flex-direction: column;
            position: relative;
            font-size: 0.75em;
            transition: background 0.2s;
        }}
        .zw-palace:hover {{
            background: #252540;
        }}
        .zw-palace.is-ming {{
            border: 2px solid var(--zw-gold);
        }}
        .zw-palace.is-shen::after {{
            content: "{t('身宫', lang)}";
            position: absolute;
            top: 2px;
            right: 2px;
            font-size: 0.6em;
            color: var(--zw-red);
        }}
        .zw-palace-head {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #333;
            padding-bottom: 3px;
            margin-bottom: 4px;
        }}
        .zw-palace-name {{
            color: var(--zw-gold);
            font-weight: bold;
            font-size: 1.05em;
        }}
        .zw-palace-ganzhi {{
            color: #888;
            font-size: 0.85em;
        }}
        .zw-daxian {{
            font-size: 0.7em;
            color: #666;
            margin-bottom: 3px;
        }}
        .zw-stars {{
            flex: 1;
            display: flex;
            flex-wrap: wrap;
            gap: 1px 4px;
        }}
        .zw-star {{
            font-size: 0.9em;
            white-space: nowrap;
        }}
        .zw-star-main {{
            font-weight: bold;
        }}
        .zw-star-aux {{
            color: #aaa;
            font-size: 0.85em;
        }}
        .zw-sihua {{
            font-size: 0.75em;
            font-weight: bold;
            margin-left: 1px;
        }}
        .zw-center {{
            background: var(--zw-card);
            padding: 12px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            font-size: 0.75em;
            text-align: center;
        }}
        .zw-center .row {{
            margin: 3px 0;
            color: #ccc;
        }}
        .zw-center .label {{
            color: var(--zw-gold);
            font-weight: bold;
        }}
        .zw-center .sihua-row {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            justify-content: center;
            margin-top: 6px;
        }}
        .zw-center .sihua-item {{
            font-size: 0.9em;
        }}
        @media (max-width: 600px) {{
            .zw-palace {{ min-height: 80px; font-size: 0.65em; padding: 5px 3px; }}
            .zw-header h1 {{ font-size: 1.1em; }}
            .zw-center {{ font-size: 0.65em; padding: 8px; }}
        }}
        @media (max-width: 400px) {{
            .zw-palace {{ min-height: 65px; font-size: 0.55em; }}
        }}
    </style>
</head>
<body>
    <div class="zw-container">
        <div class="zw-header">
            <h1>{title}</h1>
            <div class="info">{_esc(ziwei_data.get('input', {}).get('solar', ''))} | {_esc(ziwei_data.get('input', {}).get('lunar', ''))} | {_esc(ziwei_data.get('input', {}).get('gender', ''))}</div>
        </div>
        <div class="zw-grid ziwei-grid">
            {"".join(cells)}
        </div>
    </div>
</body>
</html>"""
        return html

    def _render_palace(self, gong: Dict[str, Any], gong_idx: int,
                       is_ming: bool, is_shen: bool, dx_range: str,
                       lang: str = "zh-CN") -> str:
        """渲染单个宫位"""
        from tengod.i18n import t

        name = t(gong.get("name", ""), lang)
        ganzhi = gong.get("ganzhi", "")
        main_stars = gong.get("main_stars", [])
        aux_stars = gong.get("aux_stars", [])
        sihua_str = gong.get("sihua", "")

        # 主星
        star_html = []
        for s in main_stars:
            color = self._STAR_COLORS.get(s, "#e0e0e0")
            sihua_tag = ""
            if sihua_str:
                for tag in sihua_str.split(", "):
                    if s in tag:
                        hua_char = tag[-1] if tag else ""
                        hua_color = self._SIHUA_COLORS.get(hua_char, "#888")
                        sihua_tag = f'<span class="zw-sihua" style="color:{hua_color}">{hua_char}</span>'
                        break
            star_html.append(f'<span class="zw-star zw-star-main" style="color:{color}">{_esc(t(s, lang))}{sihua_tag}</span>')

        # 辅星
        for s in aux_stars:
            star_html.append(f'<span class="zw-star zw-star-aux">{_esc(t(s, lang))}</span>')

        classes = "zw-palace"
        if is_ming:
            classes += " is-ming"
        if is_shen:
            classes += " is-shen"

        dx_html = f'<div class="zw-daxian">{_esc(dx_range)}</div>' if dx_range else ''

        return f"""<div class="{classes}" style="grid-area:{self._ZHI_GRID.get(ganzhi[-1], (0,0))[0]+1}/{self._ZHI_GRID.get(ganzhi[-1], (0,0))[1]+1}">
            <div class="zw-palace-head">
                <span class="zw-palace-name">{_esc(name)}</span>
                <span class="zw-palace-ganzhi">{_esc(ganzhi)}</span>
            </div>
            {dx_html}
            <div class="zw-stars">{"".join(star_html)}</div>
        </div>"""

    def _render_center(self, data: Dict[str, Any], lang: str = "zh-CN") -> str:
        """渲染中心信息区"""
        from tengod.i18n import t

        wuxing_ju = data.get("wuxing_ju", "")
        ming_zhu = data.get("ming_zhu", "")
        shen_zhu = data.get("shen_zhu", "")
        sihua = data.get("sihua", {})

        sihua_items = []
        for key, star in sihua.items():
            hua_char = key[-1] if key else ""
            color = self._SIHUA_COLORS.get(hua_char, "#888")
            sihua_items.append(
                f'<span class="sihua-item" style="color:{color}">{_esc(t(key, lang))}: {_esc(t(star, lang))}</span>'
            )

        return f"""
            <div class="row"><span class="label">{t('五行局', lang)}:</span> {_esc(wuxing_ju)}</div>
            <div class="row"><span class="label">{t('命主', lang)}:</span> {_esc(t(ming_zhu, lang))}</div>
            <div class="row"><span class="label">{t('身主', lang)}:</span> {_esc(t(shen_zhu, lang))}</div>
            <div class="sihua-row">{"".join(sihua_items)}</div>
        """

    def generate_svg(self, ziwei_data: Dict[str, Any], lang: str = "zh-CN") -> str:
        """生成 SVG 矢量命盘"""
        from tengod.i18n import t

        gongs = ziwei_data.get("gongs", [])
        ming_idx = ziwei_data.get("ming_gong", {}).get("index", 0)
        shen_idx = ziwei_data.get("shen_gong", {}).get("index", 0)

        # SVG 尺寸
        cell_w, cell_h = 160, 120
        total_w = cell_w * 4 + 20
        total_h = cell_h * 4 + 20

        # 构建 zhi → gong 映射
        zhi_to_gong = {}
        for i, g in enumerate(gongs):
            zhi = g.get("ganzhi", "")[-1]
            zhi_to_gong[zhi] = (g, i)

        elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{total_h}" viewBox="0 0 {total_w} {total_h}" style="background:#0a0a0f">']

        for zhi, (row, col) in self._ZHI_GRID.items():
            x = col * cell_w + 10
            y = row * cell_h + 10
            gong_data, gong_idx = zhi_to_gong.get(zhi, (None, None))
            if not gong_data:
                continue

            is_ming = (gong_idx == ming_idx)
            border_color = "#DAA520" if is_ming else "#8B4513"
            stroke_w = "2" if is_ming else "1"

            # 宫位边框
            elements.append(f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" fill="#1a1a2e" stroke="{border_color}" stroke-width="{stroke_w}" rx="3"/>')

            # 宫名
            name = t(gong_data.get("name", ""), lang)
            ganzhi = gong_data.get("ganzhi", "")
            elements.append(f'<text x="{x+8}" y="{y+18}" fill="#DAA520" font-size="14" font-weight="bold">{_esc(name)}</text>')
            elements.append(f'<text x="{x+cell_w-8}" y="{y+18}" fill="#888" font-size="11" text-anchor="end">{_esc(ganzhi)}</text>')

            # 主星
            main_stars = gong_data.get("main_stars", [])
            aux_stars = gong_data.get("aux_stars", [])
            sihua_str = gong_data.get("sihua", "")

            star_y = y + 38
            for s in main_stars:
                color = self._STAR_COLORS.get(s, "#e0e0e0")
                label = t(s, lang)
                # 检查四化
                sihua_suffix = ""
                if sihua_str:
                    for tag in sihua_str.split(", "):
                        if s in tag and len(tag) > 0:
                            sihua_suffix = f"({tag[-1]})"
                            break
                elements.append(f'<text x="{x+8}" y="{star_y}" fill="{color}" font-size="12" font-weight="bold">{_esc(label)}{_esc(sihua_suffix)}</text>')
                star_y += 16

            # 辅星
            if aux_stars:
                aux_text = " ".join(t(s, lang) for s in aux_stars)
                elements.append(f'<text x="{x+8}" y="{star_y}" fill="#aaa" font-size="10">{_esc(aux_text)}</text>')

            # 身宫标记
            if gong_idx == shen_idx:
                elements.append(f'<text x="{x+cell_w-8}" y="{y+cell_h-8}" fill="#DC143C" font-size="10" text-anchor="end">{_esc(t("身宫", lang))}</text>')

        # 中心信息
        cx = cell_w * 2 + 10
        cy = cell_h * 2 + 10
        wuxing_ju = ziwei_data.get("wuxing_ju", "")
        elements.append(f'<text x="{cx}" y="{cy+20}" fill="#DAA520" font-size="12" text-anchor="middle">{_esc(t("五行局", lang))}: {_esc(wuxing_ju)}</text>')
        elements.append(f'<text x="{cx}" y="{cy+40}" fill="#ccc" font-size="11" text-anchor="middle">{_esc(t("命主", lang))}: {_esc(t(ziwei_data.get("ming_zhu",""), lang))}</text>')
        elements.append(f'<text x="{cx}" y="{cy+56}" fill="#ccc" font-size="11" text-anchor="middle">{_esc(t("身主", lang))}: {_esc(t(ziwei_data.get("shen_zhu",""), lang))}</text>')

        elements.append('</svg>')
        return "\n".join(elements)


# ── 便捷函数 ──────────────────────────────────────────────────────────────
def visualize_bazi(bazi_data: Dict[str, Any], theme: str = "classic") -> str:
    """
    快速生成八字命盘HTML

    Args:
        bazi_data: 八字数据
        theme: 主题风格

    Returns:
        str: HTML内容
    """
    config = VisualizationConfig(theme=theme)
    viz = BaziChartVisualizer(config)
    return viz.generate_html(bazi_data)


def visualize_ziwei(ziwei_data: Dict[str, Any], lang: str = "zh-CN",
                    fmt: str = "html") -> str:
    """
    快速生成紫微命盘

    Args:
        ziwei_data: 命盘数据
        lang: 语言代码 (zh-CN/zh-TW/en)
        fmt: 输出格式 (html/svg)

    Returns:
        str: HTML 或 SVG 内容
    """
    viz = ZiweiChartVisualizer()
    if fmt == "svg":
        return viz.generate_svg(ziwei_data, lang)
    return viz.generate_html(ziwei_data, lang)


__all__ = [
    "BaziChartVisualizer",
    "ZiweiChartVisualizer",
    "VisualizationConfig",
    "visualize_bazi",
    "visualize_ziwei",
]