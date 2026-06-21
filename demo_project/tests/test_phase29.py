"""阶段29测试：多体系综合决策支持与可视化增强"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import unittest
from unittest.mock import patch, MagicMock


class TestPhase29ComprehensiveEnhancement(unittest.TestCase):
    """多体系综合分析前端增强测试"""

    def setUp(self):
        html_path = os.path.join(
            os.path.dirname(__file__), '..', 'web_console', 'index.html'
        )
        self.assertTrue(os.path.exists(html_path), "index.html 应存在")
        with open(html_path, 'r', encoding='utf-8') as f:
            self.content = f.read()

    def test_consensus_view_mode(self):
        """共识运势视图应包含各核心组件"""
        components = [
            '共识运势',
            '综合研判',
            '核心优势',
            '风险提示',
        ]
        for comp in components:
            self.assertIn(comp, self.content, f"共识视图应包含：{comp}")

    def test_score_ring_svg(self):
        """评分环应使用SVG圆形进度条"""
        svg_elements = ['strokeDasharray', 'strokeLinecap', 'viewBox="0 0 120 120"']
        for elem in svg_elements:
            self.assertIn(elem, self.content, f"评分环应包含SVG元素：{elem}")

    def test_progress_bars(self):
        """分项研判应包含进度条"""
        dimensions = ['事业', '财运', '感情', '健康']
        for dim in dimensions:
            self.assertIn(dim, self.content, f"应包含分项维度：{dim}")

    def test_system_comparison_matrix(self):
        """体系对比矩阵应包含各体系图标"""
        icons = ['streamline', '星', '遁', '卦', '年', '宅']
        # 只需检查包含体系图标映射
        system_icons_keywords = ['systemIcons', '八字', '紫微斗数', '奇门遁甲', '六爻卦']
        for kw in system_icons_keywords:
            self.assertIn(kw, self.content, f"体系图标映射应包含：{kw}")

    def test_timing_decision_panel(self):
        """时机决策面板应包含最佳/谨慎时段"""
        timing_keywords = ['最佳时机', '需谨慎', '宜：', '慎：']
        for kw in timing_keywords:
            self.assertIn(kw, self.content, f"时机面板应包含：{kw}")

    def test_view_mode_switching(self):
        """视图切换应包含四个模式"""
        modes = ['consensus', 'matrix', 'timing', 'detail']
        for mode in modes:
            self.assertIn(mode, self.content, f"视图模式应包含：{mode}")

    def test_detailed_view(self):
        """详细数据视图应包含体系详情卡片"""
        detail_components = ['体系详情', '全部显示', '展开数据']
        for comp in detail_components:
            self.assertIn(comp, self.content, f"详情视图应包含：{comp}")

    def test_cross_validation_bar(self):
        """交叉验证应包含进度条"""
        cross_elements = ['交叉验证', '系统一致性', 'gradient']
        for elem in cross_elements:
            self.assertIn(elem, self.content, f"交叉验证应包含：{elem}")

    def test_api_reference(self):
        """综合分析API引用应正确"""
        self.assertIn('/prediction/comprehensive', self.content)
        self.assertIn('/prediction/comprehensive/interpret', self.content)

    def test_additional_state_variables(self):
        """新增状态变量应存在"""
        self.assertIn('viewMode', self.content, "应包含viewMode状态变量")


class TestPhase29SpecialCases(unittest.TestCase):
    """边界情况测试"""

    def test_empty_consensus_handling(self):
        """空共识数据应被正确处理（|| 和 ?.）"""
        with open(os.path.join(os.path.dirname(__file__), '..', 'web_console', 'index.html'),
                  'r', encoding='utf-8') as f:
            content = f.read()
        # 应有空值防护
        self.assertIn('consensus.overall ||', content)
        self.assertIn('consensus.score || 0', content)

    def test_system_availability_check(self):
        """体系可用性检查"""
        with open(os.path.join(os.path.dirname(__file__), '..', 'web_console', 'index.html'),
                  'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('available !== false', content)


if __name__ == '__main__':
    unittest.main(verbosity=2)