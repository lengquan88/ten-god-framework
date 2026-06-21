"""阶段28测试：前端可视化增强 + 知识图谱交互"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import unittest
from unittest.mock import patch, MagicMock


class TestPhase28FrontendVisualization(unittest.TestCase):
    """前端可视化组件测试（紫微/六爻/奇门）"""

    def setUp(self):
        """加载 index.html 验证结构完整性"""
        html_path = os.path.join(
            os.path.dirname(__file__), '..', 'web_console', 'index.html'
        )
        self.assertTrue(os.path.exists(html_path), "index.html 应存在")
        with open(html_path, 'r', encoding='utf-8') as f:
            self.html_content = f.read()

    def test_ziwei_visualization_components(self):
        """紫微斗数应包含核心可视化组件"""
        # 命宫/身宫等宫位名称引用
        required_gongs = ['命宫', '身宫', '兄弟', '夫妻', '子女']
        for gong in required_gongs:
            self.assertIn(gong, self.html_content, f"应包含宫位：{gong}")

        # 主星/辅星/四化标签
        star_labels = ['main_stars', 'aux_stars']
        for label in star_labels:
            self.assertIn(label, self.html_content, f"应包含星耀字段：{label}")

    def test_liuyao_hexagram_rendering(self):
        """六爻应包含本卦/变卦对比渲染"""
        required_elements = ['本卦', '变卦', '初爻', '动']
        for elem in required_elements:
            self.assertIn(elem, self.html_content, f"六爻组件应包含：{elem}")

    def test_qimen_nine_palace_layout(self):
        """奇门遁甲应包含九宫飞星布局"""
        # 洛书九宫数字应在布局数据中（五宫称为中宫）
        palace_numbers = ['一宫', '二宫', '三宫', '四宫', '中宫', '六宫', '七宫', '八宫', '九宫']
        for palace in palace_numbers:
            self.assertIn(palace, self.html_content, f"奇门组件应包含宫位：{palace}")

        # 八卦映射应包含
        bagua = ['坎', '坤', '震', '巽', '乾', '兑', '艮', '离']
        for b in bagua:
            self.assertIn(b, self.html_content, f"奇门组件应包含八卦：{b}")

    def test_knowledge_graph_search_filter(self):
        """知识图谱应包含搜索筛选功能"""
        search_features = [
            '搜索节点',
            '类型',
            '清除筛选',
            '相关节点',
            '节点详情'
        ]
        for feature in search_features:
            self.assertIn(feature, self.html_content, f"知识图谱应包含：{feature}")

    def test_all_main_component_functions(self):
        """所有核心组件函数应定义完整"""
        components = [
            'function ZiweiPage',
            'function LiuyaoPage',
            'function QimenPage',
            'function KnowledgeGraph',
        ]
        for comp in components:
            self.assertIn(comp, self.html_content, f"应定义组件函数：{comp}")


class TestPhase28APIIntegration(unittest.TestCase):
    """阶段28 API 集成测试"""

    def test_ziwei_calc_api_reference(self):
        """前端应正确引用紫微斗数 API"""
        self.assertIn('/ziwei/calc', open(
            os.path.join(os.path.dirname(__file__), '..', 'web_console', 'index.html'),
            'r', encoding='utf-8'
        ).read())

    def test_liuyao_shake_api_reference(self):
        """前端应正确引用六爻起卦 API"""
        self.assertIn('/liuyao/shake', open(
            os.path.join(os.path.dirname(__file__), '..', 'web_console', 'index.html'),
            'r', encoding='utf-8'
        ).read())

    def test_qimen_calc_api_reference(self):
        """前端应正确引用奇门遁甲 API"""
        self.assertIn('/qimen/calc', open(
            os.path.join(os.path.dirname(__file__), '..', 'web_console', 'index.html'),
            'r', encoding='utf-8'
        ).read())

    def test_knowledge_nodes_api_reference(self):
        """前端应正确引用知识图谱节点 API"""
        self.assertIn('/knowledge/nodes', open(
            os.path.join(os.path.dirname(__file__), '..', 'web_console', 'index.html'),
            'r', encoding='utf-8'
        ).read())


class TestPhase28CSSAndStyling(unittest.TestCase):
    """阶段28 CSS 样式测试（确保有适当的可视化样式）"""

    def test_card_styling_exists(self):
        """应包含 card 组件样式"""
        with open(os.path.join(os.path.dirname(__file__), '..', 'web_console', 'index.html'),
                  'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('.card', content)

    def test_color_scheme_exists(self):
        """应包含五行颜色方案定义"""
        with open(os.path.join(os.path.dirname(__file__), '..', 'web_console', 'index.html'),
                  'r', encoding='utf-8') as f:
            content = f.read()
        # 至少包含一种五行颜色定义
        color_refs = ['#4CAF50', '#F44336', '#FFC107', '#2196F3', '#FF9800']
        self.assertTrue(
            any(c in content for c in color_refs),
            "应至少包含一种五行颜色引用"
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
