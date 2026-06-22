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
    """紫微斗数可视化器"""

    def generate_html(self, ziwei_data: Dict[str, Any]) -> str:
        """生成紫微命盘HTML"""
        # 简化实现
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>紫微斗数命盘</title>
    <style>
        .ziwei-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }}
        .palace {{
            border: 1px solid #8B4513;
            padding: 10px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <h1>紫微斗数命盘</h1>
    <div class="ziwei-grid">
        <!-- 12宫位 -->
    </div>
</body>
</html>
"""


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


__all__ = [
    "BaziChartVisualizer",
    "ZiweiChartVisualizer",
    "VisualizationConfig",
    "visualize_bazi",
    "visualize_ziwei",
]