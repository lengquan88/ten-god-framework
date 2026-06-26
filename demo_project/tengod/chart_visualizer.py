"""
交互式命盘可视化器 v2.4
======================
中华文明数字永生体 · 用户体验优化

功能：
- 交互式命盘展示
- 紫微斗数完整12宫位可视化
- 实时数据更新
- 响应式设计支持
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from html import escape
import json


def _esc(value: Any) -> str:
    """HTML 转义用户输入，防止 XSS"""
    return escape(str(value)) if value is not None else ""


# ── 紫微斗数基础数据 ──────────────────────────────────────────────────────

# 12宫位名称（从寅宫开始顺时针）
GONG_NAMES_12 = ["命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄", "迁移", "交友", "官禄", "田宅", "福德", "父母"]
GONG_EN_12 = ["Life", "Siblings", "Spouse", "Children", "Wealth", "Health", "Travel", "Friends", "Career", "Property", "Fortune", "Parents"]

# 地支（从寅开始顺时针）
DI_ZHI_12 = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]

# 主星显示颜色
STAR_COLORS = {
    "紫微": "#9b59b6", "天机": "#2ecc71", "太阳": "#e74c3c", "武曲": "#f39c12",
    "天同": "#3498db", "廉贞": "#e67e22", "天府": "#1abc9c", "太阴": "#8e44ad",
    "贪狼": "#d35400", "巨门": "#7f8c8d", "天相": "#27ae60", "天梁": "#2980b9",
    "七杀": "#c0392b", "破军": "#16a085",
}

# 四化星颜色
SIHUA_COLORS = {
    "化禄": "#27ae60", "化权": "#e74c3c", "化科": "#3498db", "化忌": "#7f8c8d",
}

# 辅星颜色
AUX_STAR_COLORS = {
    "文昌": "#3498db", "文曲": "#2980b9", "左辅": "#2ecc71", "右弼": "#27ae60",
    "天魁": "#e74c3c", "天钺": "#c0392b", "禄存": "#f39c12", "天马": "#16a085",
    "擎羊": "#e74c3c", "陀罗": "#c0392b", "火星": "#d35400", "铃星": "#e67e22",
    "地空": "#7f8c8d", "地劫": "#95a5a6", "天刑": "#34495e", "天姚": "#8e44ad",
}

# 宫位背景色
GONG_BG_COLORS = {
    "命宫": "#fdf2e9", "兄弟": "#eaf2f8", "夫妻": "#fdedec", "子女": "#e8f8f5",
    "财帛": "#fef9e7", "疾厄": "#f4ecf7", "迁移": "#ebf5fb", "交友": "#f5eef8",
    "官禄": "#fdebd0", "田宅": "#eafaf1", "福德": "#f9ebea", "父母": "#e8f6f3",
}


@dataclass
class VisualizationConfig:
    """可视化配置"""
    theme: str = "classic"  # classic/modern/minimal/dark
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
    <title>八字命盘 - TenGod v2.4</title>
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
            <p>TenGod Framework v2.4</p>
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
    """紫微斗数可视化器 v2.4 — 完整12宫位渲染"""

    # 12宫位标准布局（从寅宫开始顺时针，4x4 网格）
    # 网格位置映射：
    #   巳(0,0)  午(0,1)  未(0,2)  申(0,3)
    #   辰(1,0)  [中心]    [中心]   酉(1,3)
    #   卯(2,0)  [中心]    [中心]   戌(2,3)
    #   寅(3,0)  丑(3,1)  子(3,2)  亥(3,3)
    GRID_POSITIONS = [
        # (row, col)  — 从寅宫(index=0)开始顺时针
        (3, 0),  # 0 寅 = 命宫
        (2, 0),  # 1 卯 = 兄弟
        (1, 0),  # 2 辰 = 夫妻
        (0, 0),  # 3 巳 = 子女
        (0, 1),  # 4 午 = 财帛
        (0, 2),  # 5 未 = 疾厄
        (0, 3),  # 6 申 = 迁移
        (1, 3),  # 7 酉 = 交友
        (2, 3),  # 8 戌 = 官禄
        (3, 3),  # 9 亥 = 田宅
        (3, 2),  # 10 子 = 福德
        (3, 1),  # 11 丑 = 父母
    ]

    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()

    def generate_html(self, ziwei_data: Dict[str, Any]) -> str:
        """
        生成完整紫微斗数命盘HTML

        Args:
            ziwei_data: 紫微斗数数据（ZiweiEngine.to_dict() 输出）

        Returns:
            str: HTML内容
        """
        gongs = ziwei_data.get("gongs", [])
        ming_gong = ziwei_data.get("ming_gong", {})
        shen_gong = ziwei_data.get("shen_gong", {})
        sihua = ziwei_data.get("sihua", {})
        daxian = ziwei_data.get("daxian", [])
        info = ziwei_data.get("input", {})
        wuxing_ju = ziwei_data.get("wuxing_ju", "")
        ming_zhu = ziwei_data.get("ming_zhu", "")
        shen_zhu = ziwei_data.get("shen_zhu", "")

        # 构建宫位网格（12宫位按地支顺序排列）
        palaces_html = self._generate_palaces_grid(gongs, ming_gong, shen_gong, daxian)

        # 四化星标签
        sihua_tags = "".join([
            f'<span class="sihua-tag" style="background:{SIHUA_COLORS.get(k, "#888")}">{k}({v})</span>'
            for k, v in sihua.items() if v
        ])

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>紫微斗数命盘 - TenGod v2.4</title>
    <style>
        :root {{
            --ziwei-bg: #1a1a2e;
            --ziwei-card: #16213e;
            --ziwei-accent: #e2c498;
            --ziwei-text: #e0d6c2;
            --ziwei-gold: #d4a853;
            --ziwei-red: #c0392b;
            --ziwei-blue: #2980b9;
            --ziwei-green: #27ae60;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            background: var(--ziwei-bg);
            color: var(--ziwei-text);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .ziwei-container {{
            max-width: 900px;
            width: 100%;
            background: var(--ziwei-card);
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
            border: 1px solid #333;
        }}
        .ziwei-header {{
            text-align: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--ziwei-gold);
        }}
        .ziwei-header h1 {{ color: var(--ziwei-accent); font-size: 1.8em; margin-bottom: 8px; }}
        .ziwei-header .info-row {{ font-size: 0.9em; color: #999; display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; }}
        .ziwei-header .info-row span {{ color: var(--ziwei-accent); }}
        .sihua-bar {{
            display: flex; justify-content: center; gap: 12px; margin: 15px 0;
            flex-wrap: wrap;
        }}
        .sihua-tag {{
            padding: 4px 14px; border-radius: 20px; font-size: 0.85em; color: #fff; font-weight: bold;
        }}
        .ziwei-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            grid-template-rows: repeat(4, 1fr);
            gap: 8px;
            margin: 20px 0;
            min-height: 0;
        }}
        .ziwei-palace {{
            border: 1px solid #444;
            border-radius: 8px;
            padding: 10px 8px;
            min-height: 120px;
            position: relative;
            transition: all 0.3s;
            cursor: pointer;
        }}
        .ziwei-palace:hover {{
            border-color: var(--ziwei-gold);
            box-shadow: 0 0 12px rgba(212,168,83,0.3);
            transform: translateY(-2px);
        }}
        .ziwei-palace.ming-gong {{
            border-color: var(--ziwei-red);
            border-width: 2px;
            box-shadow: 0 0 8px rgba(192,57,43,0.3);
        }}
        .ziwei-palace.shen-gong {{
            border-color: var(--ziwei-blue);
            border-width: 2px;
        }}
        .palace-header {{
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 6px; font-size: 0.8em; color: #888;
        }}
        .palace-name {{
            font-weight: bold; font-size: 1.05em; color: var(--ziwei-accent);
        }}
        .palace-ganzhi {{ color: #777; font-size: 0.8em; }}
        .palace-stars {{
            display: flex; flex-wrap: wrap; gap: 3px; margin: 4px 0;
        }}
        .star-tag {{
            font-size: 0.7em; padding: 2px 6px; border-radius: 10px;
            color: #fff; white-space: nowrap; font-weight: bold;
        }}
        .star-tag.aux {{
            font-size: 0.65em; opacity: 0.85; padding: 1px 5px;
        }}
        .star-tag.sihua-star {{
            border: 1px dashed rgba(255,255,255,0.5);
        }}
        .palace-dayun {{
            font-size: 0.65em; color: #666; margin-top: 4px;
            border-top: 1px dotted #333; padding-top: 4px;
        }}
        .dayun-age {{ color: var(--ziwei-accent); }}
        .center-panel {{
            grid-column: 2 / 4; grid-row: 2 / 4;
            display: flex; flex-direction: column;
            justify-content: center; align-items: center;
            border: 1px dashed #444; border-radius: 8px;
            padding: 15px;
        }}
        .center-panel h3 {{ color: var(--ziwei-gold); font-size: 1em; }}
        .center-panel p {{ font-size: 0.75em; color: #777; margin: 3px 0; }}
        @media (max-width: 768px) {{
            .ziwei-grid {{ grid-template-columns: repeat(4, 1fr); gap: 4px; }}
            .ziwei-palace {{ padding: 6px 4px; min-height: 90px; }}
            .palace-name {{ font-size: 0.85em; }}
            .star-tag {{ font-size: 0.6em; }}
            .ziwei-container {{ padding: 15px; }}
        }}
        @media (max-width: 480px) {{
            .ziwei-grid {{ grid-template-columns: repeat(3, 1fr); grid-template-rows: auto; }}
            .center-panel {{ grid-column: 1 / 4; grid-row: auto; }}
            .ziwei-palace {{ min-height: 80px; }}
        }}
    </style>
</head>
<body>
    <div class="ziwei-container">
        <div class="ziwei-header">
            <h1>紫微斗数命盘</h1>
            <div class="info-row">
                <span>{_esc(info.get('solar', '--'))}</span>
                <span>{_esc(info.get('lunar', '--'))}</span>
                <span>{_esc(info.get('year_ganzhi', '--'))}年</span>
                <span>{_esc(info.get('gender', '--'))}</span>
            </div>
            <div class="info-row" style="margin-top:6px;">
                <span>命宫: {_esc(ming_gong.get('name', '--'))}</span>
                <span>身宫: {_esc(shen_gong.get('name', '--'))}</span>
                <span>{_esc(wuxing_ju)}</span>
                <span>命主: {_esc(ming_zhu)}</span>
                <span>身主: {_esc(shen_zhu)}</span>
            </div>
            <div class="sihua-bar">{sihua_tags}</div>
        </div>
        <div class="ziwei-grid">
            {palaces_html}
        </div>
    </div>
</body>
</html>"""

    def _generate_palaces_grid(self, gongs: List[Dict], ming_gong: Dict,
                                shen_gong: Dict, daxian: List[Dict]) -> str:
        """生成12宫位网格HTML"""
        if not gongs or len(gongs) < 12:
            return '<div class="center-panel"><h3>暂无数据</h3></div>'

        # 构建 4x3 网格
        grid_cells = [""] * 12  # 0=寅 ... 11=丑

        # 按地支顺序排列宫位（从寅开始）
        for i, gong in enumerate(gongs[:12]):
            zhi = gong.get("ganzhi", "")[-1:] if len(gong.get("ganzhi", "")) >= 2 else ""
            # 计算该宫对应的地支索引
            zhi_idx = DI_ZHI_12.index(zhi) if zhi in DI_ZHI_12 else i
            grid_cells[i] = self._render_palace(gong, zhi_idx, ming_gong, shen_gong, daxian)

        # 构建 4列 x 4行 网格（标准紫微命盘布局）
        # 地支位置映射到网格坐标：
        #   巳(0,0)  午(0,1)  未(0,2)  申(0,3)
        #   辰(1,0)  [中心]    [中心]   酉(1,3)
        #   卯(2,0)  [中心]    [中心]   戌(2,3)
        #   寅(3,0)  丑(3,1)  子(3,2)  亥(3,3)
        # 索引: 0寅, 1卯, 2辰, 3巳, 4午, 5未, 6申, 7酉, 8戌, 9亥, 10子, 11丑
        ROW_MAP = [3, 2, 1, 0, 0, 0, 0, 1, 2, 3, 3, 3]  # 行
        COL_MAP = [0, 0, 0, 0, 1, 2, 3, 3, 3, 3, 2, 1]  # 列

        # 构建 4x4 网格 (row 0-3, col 0-3)
        grid = [[None for _ in range(4)] for _ in range(4)]
        for i in range(12):
            r, c = ROW_MAP[i], COL_MAP[i]
            grid[r][c] = grid_cells[i]

        # 在 (1,1) 到 (2,2) 位置插入中心面板（跨越 rows 1-2, cols 1-2）
        center_html = f"""<div class="center-panel">
            <h3>紫微斗数</h3>
            <p>命宫: {_esc(ming_gong.get('name', '--'))}</p>
            <p>身宫: {_esc(shen_gong.get('name', '--'))}</p>
            <p>TenGod v2.4</p>
        </div>"""

        # 渲染网格
        rows_html = []
        for row_idx in range(4):
            cells = []
            for col_idx in range(4):
                if row_idx >= 1 and row_idx <= 2 and col_idx >= 1 and col_idx <= 2:
                    if row_idx == 1 and col_idx == 1:
                        cells.append(center_html)
                    continue
                if grid[row_idx][col_idx] is not None:
                    cells.append(grid[row_idx][col_idx])
                else:
                    cells.append('<div class="ziwei-palace" style="opacity:0.3"><div class="palace-name">空</div></div>')
            rows_html.extend(cells)

        return "\n".join(rows_html)

    def _render_palace(self, gong: Dict, zhi_idx: int, ming_gong: Dict,
                        shen_gong: Dict, daxian: List[Dict]) -> str:
        """渲染单个宫位"""
        name = gong.get("name", "--")
        ganzhi = gong.get("ganzhi", "--")
        main_stars = gong.get("main_stars", [])
        aux_stars = gong.get("aux_stars", [])
        sihua_star = gong.get("sihua", "")

        # 标记命宫/身宫
        extra_classes = []
        if name == ming_gong.get("name", ""):
            extra_classes.append("ming-gong")
        if name == shen_gong.get("name", ""):
            extra_classes.append("shen-gong")

        # 主星标签
        star_tags = []
        for star in main_stars:
            if not star:
                continue
            color = STAR_COLORS.get(star, "#888")
            cls = "star-tag"
            if star == sihua_star:
                cls += " sihua-star"
                color = SIHUA_COLORS.get(sihua_star, color)
            star_tags.append(f'<span class="{cls}" style="background:{color}">{_esc(star)}</span>')

        # 辅星标签
        for star in aux_stars:
            if not star:
                continue
            color = AUX_STAR_COLORS.get(star, "#666")
            star_tags.append(f'<span class="star-tag aux" style="background:{color}">{_esc(star)}</span>')

        # 大运信息
        dayun_html = ""
        for dx in daxian:
            if dx.get("gong_name") == name:
                dayun_html = f'<div class="palace-dayun">大限: <span class="dayun-age">{_esc(dx.get("age_range", ""))}</span></div>'
                break

        bg = GONG_BG_COLORS.get(name, "#1a1a2e")

        return f"""<div class="ziwei-palace {' '.join(extra_classes)}" style="background:{bg}11">
            <div class="palace-header">
                <span class="palace-name">{_esc(name)}</span>
                <span class="palace-ganzhi">{_esc(ganzhi)}</span>
            </div>
            <div class="palace-stars">{''.join(star_tags) if star_tags else '<span style="font-size:0.7em;color:#555">—</span>'}</div>
            {dayun_html}
        </div>"""

    def generate_svg(self, ziwei_data: Dict[str, Any]) -> str:
        """
        生成紫微命盘SVG

        Args:
            ziwei_data: 紫微斗数数据

        Returns:
            str: SVG内容
        """
        gongs = ziwei_data.get("gongs", [])
        if not gongs or len(gongs) < 12:
            return '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100"><text x="10" y="30" fill="#999">No data</text></svg>'

        ming_gong = ziwei_data.get("ming_gong", {})
        shen_gong = ziwei_data.get("shen_gong", {})
        sihua = ziwei_data.get("sihua", {})
        daxian = ziwei_data.get("daxian", [])

        # SVG 布局参数
        width, height = 800, 640
        cx = width // 2
        inner_r = 130

        svg_parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
        svg_parts.append(f'<rect width="{width}" height="{height}" fill="#1a1a2e"/>')
        svg_parts.append(f'<text x="{cx}" y="30" text-anchor="middle" fill="#e2c498" font-size="22" font-weight="bold">紫微斗数命盘</text>')

        # 绘制12宫位扇形
        for i, gong in enumerate(gongs[:12]):
            angle = -90 + i * 30  # 从顶部顺时针
            

            # 扇形路径
            # 使用多边形近似扇形
            pts = []
            for a in [angle, angle + 30]:
                
                pts.append(f"{cx + inner_r * 3.14159 / 180 * (90 - a) * 0}")

            # 简化为使用圆环 + 文字
            

            # 改用简单的网格布局SVG
            pass

        # 使用简单网格布局的SVG
        svg_parts.append(self._generate_svg_grid(gongs, ming_gong, shen_gong, sihua, daxian))
        svg_parts.append('</svg>')
        return "\n".join(svg_parts)

    def _generate_svg_grid(self, gongs: List[Dict], ming_gong: Dict,
                            shen_gong: Dict, sihua: Dict, daxian: List[Dict]) -> str:
        """生成SVG网格布局紫微命盘"""
        parts = []
        # 4x4 网格参数
        cell_w, cell_h = 180, 130
        start_x, start_y = 40, 80
        gap = 10

        # 地支位置映射（4x4 网格）
        ROW_MAP = [3, 2, 1, 0, 0, 0, 0, 1, 2, 3, 3, 3]
        COL_MAP = [0, 0, 0, 0, 1, 2, 3, 3, 3, 3, 2, 1]

        for i, gong in enumerate(gongs[:12]):
            r, c = ROW_MAP[i], COL_MAP[i]
            x = start_x + c * (cell_w + gap)
            y = start_y + r * (cell_h + gap)

            name = gong.get("name", "--")
            ganzhi = gong.get("ganzhi", "--")
            main_stars = gong.get("main_stars", [])
            aux_stars = gong.get("aux_stars", [])

            # 边框颜色
            stroke = "#444"
            stroke_w = 1
            if name == ming_gong.get("name", ""):
                stroke = "#c0392b"
                stroke_w = 2
            elif name == shen_gong.get("name", ""):
                stroke = "#2980b9"
                stroke_w = 2

            parts.append(f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" rx="8" fill="#16213e" stroke="{stroke}" stroke-width="{stroke_w}"/>')
            # 宫位名称
            parts.append(f'<text x="{x + cell_w/2}" y="{y + 22}" text-anchor="middle" fill="#e2c498" font-size="14" font-weight="bold">{_esc(name)}</text>')
            # 干支
            parts.append(f'<text x="{x + cell_w/2}" y="{y + 40}" text-anchor="middle" fill="#777" font-size="11">{_esc(ganzhi)}</text>')

            # 主星
            star_y = y + 58
            for star in main_stars:
                if not star:
                    continue
                color = STAR_COLORS.get(star, "#888")
                parts.append(f'<rect x="{x + 8}" y="{star_y - 10}" width="64" height="16" rx="8" fill="{color}"/>')
                parts.append(f'<text x="{x + 40}" y="{star_y + 2}" text-anchor="middle" fill="#fff" font-size="9">{_esc(star)}</text>')
                star_y += 18

            # 辅星
            for star in aux_stars[:3]:  # 最多显示3个辅星
                if not star:
                    continue
                color = AUX_STAR_COLORS.get(star, "#666")
                parts.append(f'<text x="{x + 8}" y="{star_y + 2}" fill="{color}" font-size="9">{_esc(star)}</text>')
                star_y += 12

        # 中心面板（跨越 rows 1-2, cols 1-2）
        cx_center = start_x + 1 * (cell_w + gap)
        cy_center = start_y + 1 * (cell_h + gap)
        center_w = 2 * cell_w + gap
        center_h = 2 * cell_h + gap
        parts.append(f'<rect x="{cx_center}" y="{cy_center}" width="{center_w}" height="{center_h}" rx="8" fill="none" stroke="#555" stroke-dasharray="5,5"/>')
        parts.append(f'<text x="{cx_center + center_w/2}" y="{cy_center + center_h/2 - 10}" text-anchor="middle" fill="#d4a853" font-size="16">紫微斗数</text>')
        parts.append(f'<text x="{cx_center + center_w/2}" y="{cy_center + center_h/2 + 15}" text-anchor="middle" fill="#777" font-size="11">TenGod v2.4</text>')

        return "\n".join(parts)


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


def visualize_ziwei(ziwei_data: Dict[str, Any]) -> str:
    """快速生成紫微命盘HTML"""
    viz = ZiweiChartVisualizer()
    return viz.generate_html(ziwei_data)


def visualize_ziwei_svg(ziwei_data: Dict[str, Any]) -> str:
    """快速生成紫微命盘SVG"""
    viz = ZiweiChartVisualizer()
    return viz.generate_svg(ziwei_data)


class TrajectoryTimeline:
    """命运轨迹时间线可视化器 v2.5"""

    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()

    def generate_html(
        self,
        dayuns: List[Dict],
        liunians: List[Dict],
        birth_year: int = 1990,
        title: str = "命运轨迹时间线",
    ) -> str:
        """
        生成命运轨迹时间线HTML

        Args:
            dayuns: 大运列表 [{"age": 4, "start_year": 1994, "pillar": "癸未"}, ...]
            liunians: 流年列表 [{"year": 2024, "pillar": "甲辰", "gan_shigan": "偏印"}, ...]
            birth_year: 出生年份
            title: 图表标题

        Returns:
            str: HTML内容
        """
        # 构建时间线数据
        events_json = json.dumps(self._build_timeline(dayuns, liunians, birth_year),
                                 ensure_ascii=False)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_esc(title)} - TenGod v2.5</title>
    <style>
        :root {{
            --timeline-bg: #0d1117;
            --timeline-card: #161b22;
            --timeline-accent: #58a6ff;
            --timeline-gold: #d4a853;
            --timeline-green: #3fb950;
            --timeline-red: #f85149;
            --timeline-text: #c9d1d9;
            --timeline-muted: #8b949e;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            background: var(--timeline-bg);
            color: var(--timeline-text);
            min-height: 100vh;
            padding: 30px;
        }}
        .timeline-container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        .timeline-header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .timeline-header h1 {{
            color: var(--timeline-accent);
            font-size: 2em;
            margin-bottom: 8px;
        }}
        .timeline-header p {{ color: var(--timeline-muted); }}
        .timeline {{ position: relative; padding: 20px 0; }}
        .timeline::before {{
            content: '';
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            width: 3px;
            height: 100%;
            background: linear-gradient(to bottom, var(--timeline-gold), var(--timeline-accent), var(--timeline-green));
            border-radius: 2px;
        }}
        .timeline-event {{
            position: relative;
            width: 50%;
            padding: 20px 40px;
            margin-bottom: 20px;
        }}
        .timeline-event.left {{ left: 0; text-align: right; }}
        .timeline-event.right {{ left: 50%; text-align: left; }}
        .timeline-event::before {{
            content: '';
            position: absolute;
            top: 30px;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            border: 3px solid var(--timeline-gold);
            background: var(--timeline-bg);
            z-index: 2;
        }}
        .timeline-event.left::before {{ right: -7px; }}
        .timeline-event.right::before {{ left: -7px; }}
        .timeline-event.major::before {{
            background: var(--timeline-gold);
            box-shadow: 0 0 10px rgba(212,168,83,0.5);
        }}
        .timeline-event.yearly::before {{
            border-color: var(--timeline-accent);
            width: 10px; height: 10px;
        }}
        .timeline-event.yearly.left::before {{ right: -5px; }}
        .timeline-event.yearly.right::before {{ left: -5px; }}
        .event-card {{
            background: var(--timeline-card);
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 18px;
            transition: all 0.3s;
        }}
        .event-card:hover {{
            border-color: var(--timeline-gold);
            box-shadow: 0 0 16px rgba(212,168,83,0.15);
            transform: translateY(-2px);
        }}
        .event-type {{
            font-size: 0.75em;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 6px;
        }}
        .event-type.major {{ color: var(--timeline-gold); }}
        .event-type.yearly {{ color: var(--timeline-accent); }}
        .event-type.monthly {{ color: var(--timeline-green); }}
        .event-pillar {{
            font-size: 1.4em;
            font-weight: bold;
            color: var(--timeline-text);
            margin: 4px 0;
        }}
        .event-period {{
            font-size: 0.85em;
            color: var(--timeline-muted);
        }}
        .event-score {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-top: 6px;
        }}
        .event-score.good {{ background: #1a3a2a; color: var(--timeline-green); }}
        .event-score.neutral {{ background: #2a2a1a; color: var(--timeline-gold); }}
        .event-score.bad {{ background: #3a1a1a; color: var(--timeline-red); }}
        .legend {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin: 30px 0;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.85em;
            color: var(--timeline-muted);
        }}
        .legend-dot {{
            width: 12px; height: 12px;
            border-radius: 50%;
        }}
        .legend-dot.major {{ background: var(--timeline-gold); }}
        .legend-dot.yearly {{ border: 2px solid var(--timeline-accent); }}
        .legend-dot.monthly {{ border: 2px solid var(--timeline-green); }}

        .score-bar {{
            margin: 30px 0;
            padding: 20px;
            background: var(--timeline-card);
            border-radius: 10px;
            border: 1px solid #30363d;
        }}
        .score-bar h3 {{ color: var(--timeline-accent); margin-bottom: 15px; }}
        .score-row {{
            display: flex;
            align-items: center;
            margin: 8px 0;
            gap: 10px;
        }}
        .score-label {{
            width: 80px;
            text-align: right;
            font-size: 0.85em;
            color: var(--timeline-muted);
        }}
        .score-track {{
            flex: 1;
            height: 20px;
            background: #21262d;
            border-radius: 10px;
            overflow: hidden;
        }}
        .score-fill {{
            height: 100%;
            border-radius: 10px;
            transition: width 0.8s ease;
        }}
        .score-fill.good {{ background: linear-gradient(90deg, #238636, #3fb950); }}
        .score-fill.neutral {{ background: linear-gradient(90deg, #9e6a03, #d4a853); }}
        .score-fill.bad {{ background: linear-gradient(90deg, #da3633, #f85149); }}
        .score-value {{
            width: 40px;
            font-size: 0.85em;
            font-weight: bold;
        }}

        @media (max-width: 768px) {{
            .timeline::before {{ left: 20px; }}
            .timeline-event {{ width: 100%; left: 0 !important; padding-left: 50px; text-align: left !important; }}
            .timeline-event::before {{ left: 13px !important; right: auto !important; }}
        }}
    </style>
</head>
<body>
    <div class="timeline-container">
        <div class="timeline-header">
            <h1>{_esc(title)}</h1>
            <p>TenGod Framework v2.5 · 命运轨迹全维度可视化</p>
        </div>
        <div class="legend">
            <div class="legend-item"><div class="legend-dot major"></div> 大运（10年周期）</div>
            <div class="legend-item"><div class="legend-dot yearly"></div> 流年（年度）</div>
            <div class="legend-item"><div class="legend-dot monthly"></div> 流月</div>
        </div>
        {self._generate_score_bars(dayuns, liunians)}
        <div class="timeline" id="timeline">
            {self._generate_timeline_events(dayuns, liunians, birth_year)}
        </div>
    </div>
    <script>
        const events = {events_json};
        document.querySelectorAll('.event-card').forEach(card => {{
            card.addEventListener('click', function() {{
                const idx = this.dataset.index;
                if (idx !== undefined && events[idx]) {{
                    const ev = events[idx];
                    alert(ev.type + ': ' + ev.label + '\\n' + (ev.detail || ''));
                }}
            }});
        }});
    </script>
</body>
</html>"""

    def _build_timeline(
        self, dayuns: List[Dict], liunians: List[Dict], birth_year: int
    ) -> List[Dict]:
        """构建时间线数据"""
        events = []
        for dx in dayuns:
            if isinstance(dx, dict):
                age = dx.get("age", 0)
                events.append({
                    "type": "大运",
                    "css_class": "major",
                    "label": f"大运 {dx.get('pillar', '')}",
                    "period": f"{age}-{age + 9}岁（{birth_year + age}年 - {birth_year + age + 9}年）",
                    "detail": f"大运干支：{dx.get('pillar', '')}",
                    "side": "left" if age % 2 == 0 else "right",
                })
        for ln in liunians:
            if isinstance(ln, dict):
                year = ln.get("year", 0)
                score = ln.get("score", ln.get("judgment_score", 50))
                score_class = "good" if score >= 70 else ("bad" if score < 45 else "neutral")
                events.append({
                    "type": "流年",
                    "css_class": "yearly",
                    "label": f"{year}年 {ln.get('pillar', '')}",
                    "period": f"{year}年",
                    "detail": f"十神：{ln.get('gan_shigan', '')}，评分：{score}",
                    "score": score,
                    "score_class": score_class,
                    "side": "left" if year % 2 == 0 else "right",
                })
        events.sort(key=lambda e: str(e.get("period", "")))
        return events

    def _generate_score_bars(self, dayuns: List[Dict], liunians: List[Dict]) -> str:
        """生成评分柱状图"""
        if not liunians:
            return ""

        bars = []
        for ln in liunians[:8]:
            if not isinstance(ln, dict):
                continue
            score = ln.get("score", ln.get("judgment_score", 50))
            score_class = "good" if score >= 70 else ("bad" if score < 45 else "neutral")
            year = ln.get("year", "")
            bars.append(f"""<div class="score-row">
                <span class="score-label">{year}</span>
                <div class="score-track">
                    <div class="score-fill {score_class}" style="width:{score}%"></div>
                </div>
                <span class="score-value">{score}</span>
            </div>""")

        return f"""<div class="score-bar">
            <h3>流年运势趋势</h3>
            {''.join(bars) if bars else '<p style="color:var(--timeline-muted)">暂无数据</p>'}
        </div>"""

    def _generate_timeline_events(
        self, dayuns: List[Dict], liunians: List[Dict], birth_year: int
    ) -> str:
        """生成时间线事件HTML"""
        events = self._build_timeline(dayuns, liunians, birth_year)
        html_parts = []
        for i, ev in enumerate(events):
            css_class = ev.get("css_class", "yearly")
            side = ev.get("side", "left")
            score_html = ""
            if ev.get("score") is not None:
                score_html = f'<span class="event-score {ev["score_class"]}">{ev["score"]}分</span>'
            html_parts.append(f"""<div class="timeline-event {side} {css_class}">
                <div class="event-card" data-index="{i}">
                    <div class="event-type {css_class}">{ev['type']}</div>
                    <div class="event-pillar">{_esc(ev['label'])}</div>
                    <div class="event-period">{_esc(ev['period'])}</div>
                    {score_html}
                </div>
            </div>""")
        return "\n".join(html_parts)

    def generate_svg(
        self,
        dayuns: List[Dict],
        liunians: List[Dict],
        birth_year: int = 1990,
        title: str = "命运轨迹",
    ) -> str:
        """生成SVG时间线"""
        width, height = 900, 120 + max(len(dayuns) * 60, len(liunians) * 30, 300)
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<rect width="{width}" height="{height}" fill="#0d1117"/>',
            f'<text x="{width/2}" y="35" text-anchor="middle" fill="#58a6ff" font-size="20" font-weight="bold">{_esc(title)}</text>',
            f'<line x1="{width/2}" y1="60" x2="{width/2}" y2="{height - 20}" stroke="#30363d" stroke-width="2"/>',
        ]

        y = 80
        # 大运节点
        for dx in dayuns:
            if not isinstance(dx, dict):
                continue
            age = dx.get("age", 0)
            pillar = dx.get("pillar", "")
            parts.append(f'<circle cx="{width/2}" cy="{y}" r="8" fill="#d4a853" stroke="#0d1117" stroke-width="2"/>')
            parts.append(f'<text x="{width/2 - 20}" y="{y + 4}" text-anchor="end" fill="#d4a853" font-size="12">大运 {pillar}</text>')
            parts.append(f'<text x="{width/2 + 20}" y="{y + 4}" text-anchor="start" fill="#8b949e" font-size="10">{age}-{age+9}岁</text>')
            y += 60

        # 流年节点
        y += 20
        for ln in liunians[:10]:
            if not isinstance(ln, dict):
                continue
            year = ln.get("year", "")
            pillar = ln.get("pillar", "")
            score = ln.get("score", ln.get("judgment_score", 50))
            color = "#3fb950" if score >= 70 else ("#f85149" if score < 45 else "#d4a853")
            parts.append(f'<circle cx="{width/2}" cy="{y}" r="4" fill="{color}"/>')
            parts.append(f'<text x="{width/2 - 15}" y="{y + 4}" text-anchor="end" fill="#c9d1d9" font-size="10">{year}</text>')
            parts.append(f'<text x="{width/2 + 15}" y="{y + 4}" text-anchor="start" fill="#8b949e" font-size="10">{pillar} ({score})</text>')
            y += 25

        parts.append('</svg>')
        return "\n".join(parts)


def visualize_trajectory(
    dayuns: List[Dict],
    liunians: List[Dict],
    birth_year: int = 1990,
    title: str = "命运轨迹时间线",
) -> str:
    """快速生成命运轨迹HTML"""
    viz = TrajectoryTimeline()
    return viz.generate_html(dayuns, liunians, birth_year, title)


def visualize_trajectory_svg(
    dayuns: List[Dict],
    liunians: List[Dict],
    birth_year: int = 1990,
) -> str:
    """快速生成命运轨迹SVG"""
    viz = TrajectoryTimeline()
    return viz.generate_svg(dayuns, liunians, birth_year)


class QimenChartVisualizer:
    """奇门遁甲可视化器 v2.6"""

    # 九宫洛书布局：row 0-2, col 0-2
    # 4巽  9离  2坤
    # 3震  5中  7兑
    # 8艮  1坎  6乾
    GONG_LAYOUT = {4: (0, 0), 9: (0, 1), 2: (0, 2),
                   3: (1, 0), 5: (1, 1), 7: (1, 2),
                   8: (2, 0), 1: (2, 1), 6: (2, 2)}

    MEN_COLORS = {"休": "#3fb950", "生": "#3fb950", "开": "#3fb950",
                  "死": "#f85149", "惊": "#f85149", "伤": "#f85149",
                  "杜": "#d4a853", "景": "#d4a853", "中": "#8b949e"}

    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()

    def generate_html(self, qimen_data: Dict) -> str:
        """生成奇门遁甲HTML盘面"""
        chart = qimen_data.get("chart", qimen_data)
        gongs = chart.get("gongs", {})
        yin_yang = chart.get("yin_yang", "阳")
        ju_num = chart.get("ju_num", 1)
        sizhu = chart.get("sizhu", {})
        xun_shou = chart.get("xun_shou", "")
        zhi_fu = chart.get("zhi_fu", "")
        zhi_shi = chart.get("zhi_shi", "")

        grid_cells = [""] * 9
        for num in range(1, 10):
            gong = gongs.get(str(num), gongs.get(num, {}))
            if isinstance(gong, dict):
                name = gong.get("name", "?")
                di_gan = gong.get("di_gan", "?")
                tian_gan = gong.get("tian_gan", "?")
                men = gong.get("men", "?")
                xing = gong.get("xing", "?")
                shen = gong.get("shen", "?")
                wuxing = gong.get("wuxing", "?")
                men_color = self.MEN_COLORS.get(men, "#8b949e")
                cell = f"""<div class="qimen-gong" style="border-color:{men_color}">
                    <div class="gong-name">{name}宫</div>
                    <div class="gong-stars">
                        <span class="star-xing">{xing}</span>
                        <span class="star-shen">{shen}</span>
                    </div>
                    <div class="gong-gans">
                        <span class="gan-tian">{tian_gan}</span>
                        <span class="gan-di">{di_gan}</span>
                    </div>
                    <div class="gong-men">{men}</div>
                    <div class="gong-wx">{wuxing}</div>
                </div>"""
                row, col = self.GONG_LAYOUT.get(num, (1, 1))
                grid_cells[row * 3 + col] = cell

        year_str = f"{sizhu.get('year', '')} {sizhu.get('month', '')} {sizhu.get('day', '')} {sizhu.get('hour', '')}"

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>奇门遁甲 - TenGod v2.6</title>
    <style>
        :root {{
            --qm-bg: #0d1117;
            --qm-card: #161b22;
            --qm-accent: #d4a853;
            --qm-text: #c9d1d9;
            --qm-muted: #8b949e;
        }}
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{
            font-family: 'Microsoft YaHei','PingFang SC',sans-serif;
            background: var(--qm-bg);
            color: var(--qm-text);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .qimen-container {{
            max-width: 700px;
            width: 100%;
        }}
        .qimen-header {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .qimen-header h1 {{
            color: var(--qm-accent);
            font-size: 1.8em;
            margin-bottom: 4px;
        }}
        .qimen-info {{
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
            margin-bottom: 20px;
            font-size: 0.9em;
            color: var(--qm-muted);
        }}
        .qimen-info span {{ color: var(--qm-accent); }}
        .qimen-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 8px;
            aspect-ratio: 1;
        }}
        .qimen-gong {{
            background: var(--qm-card);
            border: 2px solid #30363d;
            border-radius: 10px;
            padding: 10px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 4px;
            transition: all 0.3s;
            cursor: pointer;
        }}
        .qimen-gong:hover {{
            border-color: var(--qm-accent);
            box-shadow: 0 0 12px rgba(212,168,83,0.2);
            transform: scale(1.02);
        }}
        .gong-name {{
            font-size: 0.8em;
            color: var(--qm-muted);
            font-weight: bold;
        }}
        .gong-stars {{
            display: flex;
            gap: 6px;
            font-size: 0.75em;
        }}
        .star-xing {{ color: #58a6ff; }}
        .star-shen {{ color: #d2a8ff; }}
        .gong-gans {{
            display: flex;
            gap: 8px;
            font-size: 1.2em;
            font-weight: bold;
        }}
        .gan-tian {{ color: #ffa657; }}
        .gan-di {{ color: var(--qm-text); }}
        .gong-men {{
            font-size: 1.1em;
            font-weight: bold;
            padding: 1px 12px;
            border-radius: 10px;
        }}
        .gong-wx {{
            font-size: 0.7em;
            color: var(--qm-muted);
        }}
        @media (max-width: 480px) {{
            .qimen-grid {{ gap: 4px; }}
            .qimen-gong {{ padding: 6px; }}
            .gong-gans {{ font-size: 1em; }}
        }}
    </style>
</head>
<body>
    <div class="qimen-container">
        <div class="qimen-header">
            <h1>奇门遁甲</h1>
            <div class="qimen-info">
                <span>{yin_yang}遁{ju_num}局</span>
                <span>旬首：{xun_shou}</span>
                <span>值符：{zhi_fu}</span>
                <span>值使：{zhi_shi}</span>
            </div>
            <div class="qimen-info" style="font-size:0.8em">{year_str}</div>
        </div>
        <div class="qimen-grid">
            {''.join(grid_cells)}
        </div>
    </div>
</body>
</html>"""

    def generate_svg(self, qimen_data: Dict) -> str:
        """生成奇门遁甲SVG"""
        chart = qimen_data.get("chart", qimen_data)
        gongs = chart.get("gongs", {})
        yin_yang = chart.get("yin_yang", "阳")
        ju_num = chart.get("ju_num", 1)

        w, h = 600, 640
        cell_s = 160
        gap = 6
        start_x = (w - 3 * cell_s - 2 * gap) // 2
        start_y = 100

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
            f'<rect width="{w}" height="{h}" fill="#0d1117"/>',
            f'<text x="{w/2}" y="35" text-anchor="middle" fill="#d4a853" font-size="20" font-weight="bold">奇门遁甲</text>',
            f'<text x="{w/2}" y="60" text-anchor="middle" fill="#8b949e" font-size="13">{yin_yang}遁{ju_num}局</text>',
        ]

        for num in range(1, 10):
            gong = gongs.get(str(num), gongs.get(num, {}))
            if not isinstance(gong, dict):
                continue
            row, col = self.GONG_LAYOUT.get(num, (1, 1))
            x = start_x + col * (cell_s + gap)
            y = start_y + row * (cell_s + gap)
            name = gong.get("name", "?")
            men = gong.get("men", "?")
            men_color = self.MEN_COLORS.get(men, "#8b949e")

            parts.append(f'<rect x="{x}" y="{y}" width="{cell_s}" height="{cell_s}" rx="8" '
                         f'fill="#161b22" stroke="{men_color}" stroke-width="2"/>')
            parts.append(f'<text x="{x + cell_s/2}" y="{y + 25}" text-anchor="middle" '
                         f'fill="#8b949e" font-size="12">{name}宫</text>')
            parts.append(f'<text x="{x + cell_s/2}" y="{y + 55}" text-anchor="middle" '
                         f'fill="#58a6ff" font-size="12">{gong.get("xing", "?")}</text>')
            parts.append(f'<text x="{x + cell_s/2}" y="{y + 75}" text-anchor="middle" '
                         f'fill="#d2a8ff" font-size="11">{gong.get("shen", "?")}</text>')
            parts.append(f'<text x="{x + cell_s/2}" y="{y + 105}" text-anchor="middle" '
                         f'fill="#ffa657" font-size="18" font-weight="bold">{gong.get("tian_gan", "?")}</text>')
            parts.append(f'<text x="{x + cell_s/2}" y="{y + 128}" text-anchor="middle" '
                         f'fill="#c9d1d9" font-size="14">{gong.get("di_gan", "?")}</text>')
            parts.append(f'<text x="{x + cell_s/2}" y="{y + 150}" text-anchor="middle" '
                         f'fill="{men_color}" font-size="16" font-weight="bold">{men}</text>')

        parts.append('</svg>')
        return "\n".join(parts)


class FengshuiVisualizer:
    """风水可视化器 v2.6 — 玄空飞星+罗盘"""

    # 九宫布局（上南下北）
    GONG_LAYOUT = {4: (0, 0), 9: (0, 1), 2: (0, 2),
                   3: (1, 0), 5: (1, 1), 7: (1, 2),
                   8: (2, 0), 1: (2, 1), 6: (2, 2)}

    STAR_NAMES = {1: "一白", 2: "二黑", 3: "三碧", 4: "四绿",
                  5: "五黄", 6: "六白", 7: "七赤", 8: "八白", 9: "九紫"}
    STAR_FORTUNE = {1: "吉", 2: "凶", 3: "凶", 4: "吉", 5: "大凶",
                    6: "吉", 7: "吉", 8: "吉", 9: "吉"}
    STAR_COLORS = {1: "#3fb950", 2: "#f85149", 3: "#f85149", 4: "#3fb950",
                   5: "#ff0000", 6: "#3fb950", 7: "#3fb950", 8: "#3fb950", 9: "#3fb950"}
    PALACE_NAMES = {1: "坎(北)", 2: "坤(西南)", 3: "震(东)", 4: "巽(东南)",
                    5: "中宫", 6: "乾(西北)", 7: "兑(西)", 8: "艮(东北)", 9: "离(南)"}

    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()

    def generate_html(self, fengshui_data: Dict) -> str:
        """生成玄空飞星HTML"""
        yun_name = fengshui_data.get("yun_name", "")
        direction = fengshui_data.get("direction", "")
        yun_pan = fengshui_data.get("yun_pan", {})
        shan_pan = fengshui_data.get("shan_pan", {})
        xiang_pan = fengshui_data.get("xiang_pan", {})
        liunian_pan = fengshui_data.get("liunian_pan", {})
        judgments = fengshui_data.get("judgments", [])

        def _label_to_num(label: str) -> int:
            try:
                parts = label.split("(")
                return int(parts[0]) if parts[0].isdigit() else 5
            except Exception:
                return 5

        # 构建简单的 dict[int,int] 如果传入的是标签格式
        if yun_pan and isinstance(next(iter(yun_pan.values())), str):
            yun_pan = {_label_to_num(k): _label_to_num(v.split("(")[0]) if "(" in v else v
                       for k, v in yun_pan.items()}

        grid_cells = []
        for num in range(1, 10):
            row, col = self.GONG_LAYOUT.get(num, (1, 1))
            yun_s = yun_pan.get(num, yun_pan.get(str(num), 5)) if isinstance(yun_pan, dict) else 5
            shan_s = shan_pan.get(num, shan_pan.get(str(num), 5)) if isinstance(shan_pan, dict) else 5
            xiang_s = xiang_pan.get(num, xiang_pan.get(str(num), 5)) if isinstance(xiang_pan, dict) else 5
            ln_s = liunian_pan.get(num, liunian_pan.get(str(num), 5)) if isinstance(liunian_pan, dict) else 5

            if isinstance(yun_s, str):
                yun_s = 5
            if isinstance(shan_s, str):
                shan_s = 5
            if isinstance(xiang_s, str):
                xiang_s = 5
            if isinstance(ln_s, str):
                ln_s = 5

            ln_color = self.STAR_COLORS.get(ln_s, "#8b949e")
            fortune = self.STAR_FORTUNE.get(ln_s, "吉")

            cell = f"""<div class="fs-gong" style="border-color:{ln_color}">
                <div class="fs-palace">{self.PALACE_NAMES.get(num, str(num))}</div>
                <div class="fs-stars">
                    <span class="fs-star yun">运{self.STAR_NAMES.get(yun_s, str(yun_s))}</span>
                    <span class="fs-star shan">山{self.STAR_NAMES.get(shan_s, str(shan_s))}</span>
                    <span class="fs-star xiang">向{self.STAR_NAMES.get(xiang_s, str(xiang_s))}</span>
                </div>
                <div class="fs-liunian">流年{self.STAR_NAMES.get(ln_s, str(ln_s))}</div>
                <div class="fs-fortune">{fortune}</div>
            </div>"""
            grid_cells.append(cell)

        judgment_html = "".join(f'<li>{_esc(j)}</li>' for j in judgments[:5])

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>玄空飞星风水 - TenGod v2.6</title>
    <style>
        :root {{
            --fs-bg: #0d1117;
            --fs-card: #161b22;
            --fs-accent: #d4a853;
            --fs-text: #c9d1d9;
            --fs-muted: #8b949e;
        }}
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{
            font-family: 'Microsoft YaHei','PingFang SC',sans-serif;
            background: var(--fs-bg);
            color: var(--fs-text);
            min-height: 100vh;
            padding: 20px;
        }}
        .fs-container {{
            max-width: 750px;
            margin: 0 auto;
        }}
        .fs-header {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .fs-header h1 {{
            color: var(--fs-accent);
            font-size: 1.8em;
            margin-bottom: 4px;
        }}
        .fs-info {{
            color: var(--fs-muted);
            font-size: 0.9em;
        }}
        .fs-info span {{ color: var(--fs-accent); }}
        .fs-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            gap: 8px;
            aspect-ratio: 1;
            margin-bottom: 20px;
        }}
        .fs-gong {{
            background: var(--fs-card);
            border: 2px solid #30363d;
            border-radius: 10px;
            padding: 10px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 4px;
            transition: all 0.3s;
            cursor: pointer;
        }}
        .fs-gong:hover {{
            border-color: var(--fs-accent);
            box-shadow: 0 0 12px rgba(212,168,83,0.2);
            transform: scale(1.02);
        }}
        .fs-palace {{
            font-size: 0.8em;
            color: var(--fs-muted);
        }}
        .fs-stars {{
            display: flex;
            gap: 4px;
            flex-wrap: wrap;
            justify-content: center;
        }}
        .fs-star {{
            font-size: 0.7em;
            padding: 1px 6px;
            border-radius: 8px;
        }}
        .fs-star.yun {{ background: #1a3a2a; color: #3fb950; }}
        .fs-star.shan {{ background: #2a1a3a; color: #d2a8ff; }}
        .fs-star.xiang {{ background: #3a2a1a; color: #ffa657; }}
        .fs-liunian {{
            font-size: 1em;
            font-weight: bold;
            margin-top: 2px;
        }}
        .fs-fortune {{
            font-size: 0.7em;
            padding: 1px 8px;
            border-radius: 8px;
        }}
        .fs-judgments {{
            background: var(--fs-card);
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 16px;
        }}
        .fs-judgments h3 {{
            color: var(--fs-accent);
            margin-bottom: 10px;
        }}
        .fs-judgments li {{
            margin: 6px 0 6px 20px;
            font-size: 0.9em;
            color: var(--fs-muted);
        }}
        @media (max-width: 480px) {{
            .fs-grid {{ gap: 4px; }}
            .fs-gong {{ padding: 6px; }}
        }}
    </style>
</head>
<body>
    <div class="fs-container">
        <div class="fs-header">
            <h1>玄空飞星风水</h1>
            <div class="fs-info">
                <span>{yun_name}</span> · {direction}
            </div>
        </div>
        <div class="fs-grid">
            {''.join(grid_cells)}
        </div>
        <div class="fs-judgments">
            <h3>风水断语</h3>
            <ul>{judgment_html}</ul>
        </div>
    </div>
</body>
</html>"""

    def generate_svg(self, fengshui_data: Dict) -> str:
        """生成玄空飞星SVG"""
        yun_name = fengshui_data.get("yun_name", "")
        direction = fengshui_data.get("direction", "")
        yun_pan = fengshui_data.get("yun_pan", {})
        liunian_pan = fengshui_data.get("liunian_pan", {})

        w, h = 600, 620
        cell_s = 160
        gap = 6
        start_x = (w - 3 * cell_s - 2 * gap) // 2
        start_y = 80

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
            f'<rect width="{w}" height="{h}" fill="#0d1117"/>',
            f'<text x="{w/2}" y="35" text-anchor="middle" fill="#d4a853" font-size="20" font-weight="bold">玄空飞星 {yun_name}</text>',
            f'<text x="{w/2}" y="60" text-anchor="middle" fill="#8b949e" font-size="13">{direction}</text>',
        ]

        for num in range(1, 10):
            row, col = self.GONG_LAYOUT.get(num, (1, 1))
            x = start_x + col * (cell_s + gap)
            y = start_y + row * (cell_s + gap)
            palace = self.PALACE_NAMES.get(num, str(num))

            ln_s = liunian_pan.get(num, liunian_pan.get(str(num), 5)) if isinstance(liunian_pan, dict) else 5
            if isinstance(ln_s, str):
                ln_s = 5
            ln_color = self.STAR_COLORS.get(ln_s, "#8b949e")

            parts.append(f'<rect x="{x}" y="{y}" width="{cell_s}" height="{cell_s}" rx="8" '
                         f'fill="#161b22" stroke="{ln_color}" stroke-width="2"/>')
            parts.append(f'<text x="{x + cell_s/2}" y="{y + 30}" text-anchor="middle" '
                         f'fill="#8b949e" font-size="13">{palace}</text>')
            parts.append(f'<text x="{x + cell_s/2}" y="{y + 70}" text-anchor="middle" '
                         f'fill="#3fb950" font-size="12">运 {self.STAR_NAMES.get(yun_pan.get(num, yun_pan.get(str(num), 5)) if isinstance(yun_pan, dict) else 5, "?")}</text>')
            parts.append(f'<text x="{x + cell_s/2}" y="{y + 110}" text-anchor="middle" '
                         f'fill="{ln_color}" font-size="22" font-weight="bold">{self.STAR_NAMES.get(ln_s, str(ln_s))}</text>')
            parts.append(f'<text x="{x + cell_s/2}" y="{y + 140}" text-anchor="middle" '
                         f'fill="{ln_color}" font-size="13">{self.STAR_FORTUNE.get(ln_s, "吉")}</text>')

        parts.append('</svg>')
        return "\n".join(parts)


def visualize_qimen(qimen_data: Dict) -> str:
    """快速生成奇门遁甲HTML"""
    viz = QimenChartVisualizer()
    return viz.generate_html(qimen_data)


def visualize_qimen_svg(qimen_data: Dict) -> str:
    """快速生成奇门遁甲SVG"""
    viz = QimenChartVisualizer()
    return viz.generate_svg(qimen_data)


def visualize_fengshui(fengshui_data: Dict) -> str:
    """快速生成风水HTML"""
    viz = FengshuiVisualizer()
    return viz.generate_html(fengshui_data)


def visualize_fengshui_svg(fengshui_data: Dict) -> str:
    """快速生成风水SVG"""
    viz = FengshuiVisualizer()
    return viz.generate_svg(fengshui_data)


class LiuyaoChartVisualizer:
    """六爻卦象可视化器 v2.7"""

    # 六亲颜色
    LIUQIN_COLORS = {
        "父母": "#58a6ff", "兄弟": "#d4a853", "官鬼": "#f85149",
        "妻财": "#3fb950", "子孙": "#d2a8ff",
    }
    # 六神颜色
    LIUSHEN_COLORS = {
        "青龙": "#3fb950", "朱雀": "#f85149", "勾陈": "#d4a853",
        "螣蛇": "#ffa657", "白虎": "#8b949e", "玄武": "#58a6ff",
    }
    # 五行颜色
    WUXING_COLORS = {"金": "#ffa657", "木": "#3fb950", "水": "#58a6ff",
                     "火": "#f85149", "土": "#d4a853"}

    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()

    def generate_html(self, liuyao_result) -> str:
        """生成六爻卦象HTML"""
        # 支持 dict 和 dataclass 两种格式
        if isinstance(liuyao_result, dict):
            ben = liuyao_result.get("ben_gua_name", "")
            bian = liuyao_result.get("bian_gua_name", "")
            hu = liuyao_result.get("hu_gua_name", "")
            yaos = liuyao_result.get("yaos", [])
            judgment = liuyao_result.get("overall_judgment", "")
            day_ganzhi = liuyao_result.get("day_ganzhi", "")
            gua_gong = liuyao_result.get("gua_gong", "")
        else:
            ben = getattr(liuyao_result, "ben_gua_name", "")
            bian = getattr(liuyao_result, "bian_gua_name", "")
            hu = getattr(liuyao_result, "hu_gua_name", "")
            yaos = getattr(liuyao_result, "yaos", [])
            judgment = getattr(liuyao_result, "overall_judgment", "")
            day_ganzhi = getattr(liuyao_result, "day_ganzhi", "")
            gua_gong = getattr(liuyao_result, "gua_gong", "")

        yao_rows = []
        for i, yao in enumerate(reversed(yaos)):
            if isinstance(yao, dict):
                pos = yao.get("position", 6 - i)
                yao_type = yao.get("yao_type", "")
                is_dong = yao.get("is_dong", False)
                liuqin = yao.get("liuqin", "")
                liushen = yao.get("liushen", "")
                shi = yao.get("shi", False)
                ying = yao.get("ying", False)
                zhi = yao.get("zhi", "")
            else:
                pos = getattr(yao, "position", 6 - i)
                yao_type = str(getattr(yao, "yao_type", ""))
                is_dong = getattr(yao, "is_dong", False)
                liuqin = getattr(yao, "liuqin", "")
                liushen = getattr(yao, "liushen", "")
                shi = getattr(yao, "shi", False)
                ying = getattr(yao, "ying", False)
                zhi = getattr(yao, "zhi", "")

            liuqin_color = self.LIUQIN_COLORS.get(liuqin, "#8b949e")
            liushen_color = self.LIUSHEN_COLORS.get(liushen, "#8b949e")

            is_yang = "YANG" in str(yao_type).upper() or "阳" in str(yao_type)
            dong_class = "dong" if is_dong else ""
            yao_line = "—————" if is_yang else "—— —"
            yao_line_class = "yang" if is_yang else "yin"

            badges = []
            if shi:
                badges.append('<span class="badge shi">世</span>')
            if ying:
                badges.append('<span class="badge ying">应</span>')
            if is_dong:
                badges.append('<span class="badge dong">动</span>')
            badges_html = " ".join(badges)

            yao_rows.append(f"""<div class="yao-row {dong_class}" style="--liuqin-color:{liuqin_color};--liushen-color:{liushen_color}">
                <div class="yao-meta">
                    <span class="yao-pos">{['', '初','二','三','四','五','上'][pos]}</span>
                    <span class="yao-liuqin" style="color:{liuqin_color}">{liuqin}</span>
                    <span class="yao-zhi">{zhi}</span>
                </div>
                <div class="yao-line {yao_line_class}">{yao_line}</div>
                <div class="yao-badges">{badges_html}</div>
                <div class="yao-liushen" style="color:{liushen_color}">{liushen}</div>
            </div>""")

        gua_list = []
        for name in [ben, bian, hu]:
            if name:
                gua_list.append(f'<span class="gua-tag">{name}</span>')

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>六爻卦象 - TenGod v2.7</title>
    <style>
        :root {{
            --ly-bg: #0d1117;
            --ly-card: #161b22;
            --ly-accent: #d4a853;
            --ly-text: #c9d1d9;
            --ly-muted: #8b949e;
        }}
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{
            font-family: 'Microsoft YaHei','PingFang SC',sans-serif;
            background: var(--ly-bg);
            color: var(--ly-text);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            padding: 20px;
        }}
        .liuyao-container {{
            max-width: 600px;
            width: 100%;
        }}
        .liuyao-header {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .liuyao-header h1 {{
            color: var(--ly-accent);
            font-size: 1.8em;
            margin-bottom: 4px;
        }}
        .liuyao-info {{
            display: flex;
            justify-content: center;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }}
        .gua-tag {{
            background: var(--ly-card);
            border: 1px solid var(--ly-accent);
            color: var(--ly-accent);
            padding: 4px 14px;
            border-radius: 16px;
            font-size: 0.9em;
        }}
        .yao-card {{
            background: var(--ly-card);
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 16px;
        }}
        .yao-row {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 8px;
            border-bottom: 1px solid #21262d;
            transition: all 0.3s;
            border-radius: 8px;
        }}
        .yao-row:last-child {{ border-bottom: none; }}
        .yao-row:hover {{
            background: #1a1f2e;
        }}
        .yao-row.dong {{
            background: linear-gradient(90deg, rgba(248,81,73,0.08), transparent);
            border-left: 3px solid #f85149;
        }}
        .yao-meta {{
            display: flex;
            align-items: center;
            gap: 8px;
            min-width: 120px;
            font-size: 0.85em;
        }}
        .yao-pos {{
            color: var(--ly-muted);
            font-weight: bold;
            width: 24px;
        }}
        .yao-zhi {{
            color: var(--ly-muted);
            font-size: 0.8em;
        }}
        .yao-line {{
            flex: 1;
            text-align: center;
            font-size: 1.6em;
            font-weight: bold;
            letter-spacing: 4px;
            padding: 4px 0;
        }}
        .yao-line.yang {{ color: #ffa657; }}
        .yao-line.yin {{ color: #58a6ff; }}
        .yao-badges {{
            display: flex;
            gap: 4px;
            min-width: 50px;
        }}
        .badge {{
            font-size: 0.7em;
            padding: 1px 8px;
            border-radius: 8px;
            font-weight: bold;
        }}
        .badge.shi {{ background: #3a1a1a; color: #f85149; }}
        .badge.ying {{ background: #1a3a1a; color: #3fb950; }}
        .badge.dong {{ background: #3a1a2a; color: #ffa657; }}
        .yao-liushen {{
            font-size: 0.8em;
            min-width: 40px;
            text-align: right;
        }}
        .judgment {{
            background: var(--ly-card);
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 16px;
            margin-top: 16px;
        }}
        .judgment h3 {{
            color: var(--ly-accent);
            margin-bottom: 8px;
        }}
        .judgment p {{
            color: var(--ly-muted);
            font-size: 0.9em;
            line-height: 1.6;
        }}
        @media (max-width: 480px) {{
            .yao-meta {{ min-width: 90px; font-size: 0.75em; }}
            .yao-line {{ font-size: 1.2em; }}
        }}
    </style>
</head>
<body>
    <div class="liuyao-container">
        <div class="liuyao-header">
            <h1>六爻卦象</h1>
            <div class="liuyao-info">{''.join(gua_list)}</div>
            <div style="color:var(--ly-muted);font-size:0.8em">{day_ganzhi} · {gua_gong}宫</div>
        </div>
        <div class="yao-card">
            {''.join(yao_rows)}
        </div>
        <div class="judgment">
            <h3>断辞</h3>
            <p>{_esc(judgment) if judgment else '暂无断辞'}</p>
        </div>
    </div>
</body>
</html>"""

    def generate_svg(self, liuyao_result) -> str:
        """生成六爻卦象SVG"""
        if isinstance(liuyao_result, dict):
            ben = liuyao_result.get("ben_gua_name", "")
            yaos = liuyao_result.get("yaos", [])
        else:
            ben = getattr(liuyao_result, "ben_gua_name", "")
            yaos = getattr(liuyao_result, "yaos", [])

        w, h = 500, 420
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
            f'<rect width="{w}" height="{h}" fill="#0d1117"/>',
            f'<text x="{w/2}" y="30" text-anchor="middle" fill="#d4a853" font-size="18" font-weight="bold">{_esc(ben)}</text>',
        ]

        y = 60
        for i, yao in enumerate(reversed(list(yaos))):
            if isinstance(yao, dict):
                is_yang = "YANG" in str(yao.get("yao_type", "")).upper() or "阳" in str(yao.get("yao_type", ""))
                is_dong = yao.get("is_dong", False)
                liuqin = yao.get("liuqin", "")
                shi = yao.get("shi", False)
                pos = yao.get("position", 6 - i)
            else:
                is_yang = "YANG" in str(getattr(yao, "yao_type", "")).upper() or "阳" in str(getattr(yao, "yao_type", ""))
                is_dong = getattr(yao, "is_dong", False)
                liuqin = getattr(yao, "liuqin", "")
                shi = getattr(yao, "shi", False)
                pos = getattr(yao, "position", 6 - i)

            color = self.LIUQIN_COLORS.get(liuqin, "#8b949e")
            stroke_color = "#f85149" if is_dong else color

            cx = w / 2
            parts.append(f'<text x="{cx - 140}" y="{y + 12}" text-anchor="end" fill="{color}" font-size="11">{liuqin}</text>')
            parts.append(f'<text x="{cx - 95}" y="{y + 12}" text-anchor="end" fill="#8b949e" font-size="10">{["","初","二","三","四","五","上"][pos]}</text>')

            if is_yang:
                parts.append(f'<line x1="{cx - 60}" y1="{y}" x2="{cx + 60}" y2="{y}" stroke="{stroke_color}" stroke-width="3" stroke-linecap="round"/>')
            else:
                parts.append(f'<line x1="{cx - 40}" y1="{y}" x2="{cx + 60}" y2="{y}" stroke="{stroke_color}" stroke-width="2" stroke-linecap="round"/>')
                parts.append(f'<line x1="{cx - 40}" y1="{y}" x2="{cx - 40}" y2="{y + 12}" stroke="transparent" stroke-width="0"/>')

            if shi:
                parts.append(f'<circle cx="{cx + 85}" cy="{y + 6}" r="6" fill="none" stroke="#f85149" stroke-width="2"/>')
                parts.append(f'<text x="{cx + 85}" y="{y + 10}" text-anchor="middle" fill="#f85149" font-size="8">世</text>')

            if is_dong:
                parts.append(f'<circle cx="{cx + 105}" cy="{y + 6}" r="5" fill="#f85149" opacity="0.5"/>')

            y += 30

        parts.append('</svg>')
        return "\n".join(parts)


def visualize_liuyao(liuyao_result) -> str:
    """快速生成六爻HTML"""
    viz = LiuyaoChartVisualizer()
    return viz.generate_html(liuyao_result)


def visualize_liuyao_svg(liuyao_result) -> str:
    """快速生成六爻SVG"""
    viz = LiuyaoChartVisualizer()
    return viz.generate_svg(liuyao_result)


__all__ = [
    "BaziChartVisualizer",
    "ZiweiChartVisualizer",
    "TrajectoryTimeline",
    "QimenChartVisualizer",
    "FengshuiVisualizer",
    "LiuyaoChartVisualizer",
    "VisualizationConfig",
    "visualize_bazi",
    "visualize_ziwei",
    "visualize_ziwei_svg",
    "visualize_trajectory",
    "visualize_trajectory_svg",
    "visualize_qimen",
    "visualize_qimen_svg",
    "visualize_fengshui",
    "visualize_fengshui_svg",
    "visualize_liuyao",
    "visualize_liuyao_svg",
]