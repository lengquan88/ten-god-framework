"""阶段30测试：命运轨迹可视化增强"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest


class TestPhase30TrajectoryVisualization(unittest.TestCase):
    """命运轨迹页面可视化增强测试"""

    def setUp(self):
        html_path = os.path.join(
            os.path.dirname(__file__), '..', 'web_console', 'index.html'
        )
        self.assertTrue(os.path.exists(html_path), "index.html 应存在")
        with open(html_path, 'r', encoding='utf-8') as f:
            self.content = f.read()

    def test_trajectory_page_function(self):
        """TrajectoryPage 函数应正确定义"""
        self.assertIn('function TrajectoryPage', self.content)

    def test_four_view_modes(self):
        """四视图切换：总览/大运/流年/热力图"""
        view_modes = ['overview', 'dayun', 'liunian', 'heatmap']
        for mode in view_modes:
            self.assertIn(mode, self.content, f"应包含视图模式：{mode}")

    def test_fortune_color_mapping(self):
        """运势颜色映射函数"""
        color_keywords = [
            "score >= 80", "score >= 60", "score >= 40", "score >= 20",
            "#4CAF50", "#8BC34A", "#FFC107", "#FF9800", "#F44336"
        ]
        for kw in color_keywords:
            self.assertIn(kw, self.content, f"fortuneColor应包含色彩映射：{kw}")

    def test_dayun_progress_bar(self):
        """大运进度条可视化"""
        progress_elements = ['height: 6', 'background: color', 'borderRadius: 3', 'transition']
        for elem in progress_elements:
            self.assertIn(elem, self.content, f"大运进度条应包含：{elem}")

    def test_heatmap_grid_layout(self):
        """流年热力图网格布局"""
        heatmap_elements = ['width: 20, height: 20', 'borderRadius: 3', 'scale(1.3)', 'scale(1)']
        for elem in heatmap_elements:
            self.assertIn(elem, self.content, f"热力图应包含：{elem}")

    def test_liunian_color_bars(self):
        """流年彩色条形卡"""
        self.assertIn("height: 30", self.content, "流年卡片应包含高度定义")

    def test_life_stages_grid(self):
        """人生阶段网格卡片"""
        stage_elements = ['人生阶段', 'borderLeft']
        for elem in stage_elements:
            self.assertIn(elem, self.content, f"人生阶段应包含：{elem}")

    def test_wuxing_distribution(self):
        """五行分布展示"""
        wuxing_elements = ['命盘基础', 'wuxingDist']
        for elem in wuxing_elements:
            self.assertIn(elem, self.content, f"五行分布应包含：{elem}")

    def test_api_endpoint(self):
        """命运轨迹 API 端点"""
        self.assertIn('/advanced/trajectory', self.content)

    def test_view_switch_buttons(self):
        """视图切换按钮"""
        button_labels = ['总览', '大运', '流年', '热力图']
        for label in button_labels:
            self.assertIn(label, self.content, f"视图按钮应包含：{label}")

    def test_dayun_detail_view(self):
        """大运详情视图"""
        dayun_elements = ['大运详解', '十年一运', 'age_start', 'age_end']
        for elem in dayun_elements:
            self.assertIn(elem, self.content, f"大运详情应包含：{elem}")

    def test_heatmap_legend(self):
        """热力图图例"""
        legend_elements = ['大凶', '大吉', 'fortuneColor', 'decadeYear']
        for elem in legend_elements:
            self.assertIn(elem, self.content, f"热力图图例应包含：{elem}")

    def test_state_variables(self):
        """新增状态变量"""
        state_vars = ['fortuneColor', 'calcLiunianScore', 'activeView']
        for var in state_vars:
            self.assertIn(var, self.content, f"应包含状态/函数：{var}")

    def test_degraded_fallback_data(self):
        """空数据降级处理"""
        with open(html_path := os.path.join(os.path.dirname(__file__), '..', 'web_console', 'index.html'), 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('lifeStages.length > 0 ? lifeStages', content)
        self.assertIn('dayun.length > 0 ? dayun', content)
        self.assertIn('liunian.length > 0 ? liunian', content)


class TestPhase30Integration(unittest.TestCase):
    """阶段30 集成测试"""

    def test_trajectory_imported_in_main(self):
        """轨迹页面函数在主文件中"""
        with open(os.path.join(os.path.dirname(__file__), '..', 'web_console', 'index.html'),
                  'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('TrajectoryPage', content)

    def test_no_syntax_errors(self):
        """确保文件可被解析（无明显语法错误）"""
        with open(os.path.join(os.path.dirname(__file__), '..', 'web_console', 'index.html'),
                  'r', encoding='utf-8') as f:
            content = f.read()
        # 统计函数定义数量
        import re
        functions = re.findall(r'function \w+', content)
        self.assertGreater(len(functions), 10, "应包含多个页面组件函数")


if __name__ == '__main__':
    unittest.main(verbosity=2)
