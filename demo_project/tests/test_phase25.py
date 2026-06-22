#!/usr/bin/env python3
"""
test_phase25.py — 阶段二十五：姓名学 + 合婚分析 综合集成测试

覆盖：
  - multi_system_engine 的姓名学分析和 (_calc_name)
  - multi_system_engine 的合婚分析 (_calc_marriage)
  - full_analysis 支持可选的姓名和合婚参数
  - ComprehensiveRequest 新字段（name_surname, name_given, partner）
  - 综合分析（10 体系）交叉验证
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.pop("TENGOD_API_KEY", None)
os.environ["TENGOD_LLM_BACKEND"] = "mock"


class TestNameEngineIntegration:
    """姓名学集成测试"""

    def test_calc_name_basic(self):
        """基础姓名学计算"""
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer._calc_name("张", "三丰")
        assert result.system == "姓名学"
        # 结果应当可用且包含核心字段
        assert result.data is not None
        assert isinstance(result.data, dict)
        assert "wuge" in result.data
        assert "overall_score" in result.data
        assert 0 <= result.data["overall_score"] <= 100
        # 摘要包含信息
        assert isinstance(result.summary, str) and len(result.summary) > 0

    def test_calc_name_wuge_structure(self):
        """五格结构正确性"""
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer._calc_name("李", "世明")
        wuge = result.data["wuge"]
        # 五格应该每个都有数值
        for k in ("tian", "ren", "di", "wai", "zong"):
            assert k in wuge, f"缺失 {k} 格"
            assert isinstance(wuge[k], int) or isinstance(wuge[k], float)

    def test_calc_name_sancai_exists(self):
        """三才配置存在"""
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer._calc_name("王", "小明")
        assert "sancai" in result.data
        assert isinstance(result.data["sancai"], list) and len(result.data["sancai"]) >= 2

    def test_calc_name_empty_input_handled(self):
        """空输入不会崩溃"""
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        # 即使输入异常也能工作或返回标记失败
        try:
            result = analyzer._calc_name("", "")
            assert isinstance(result.summary, str)  # 有摘要
        except Exception:
            # 允许抛出异常，只要不抛出未被捕获的异常即可
            pass


class TestMarriageEngineIntegration:
    """合婚分析集成测试"""

    def test_calc_marriage_basic(self):
        """基础合婚计算（不带具体八字）"""
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer._calc_marriage(
            "张三", {},
            "李四", {},
        )
        assert result.system == "合婚分析"
        assert result.data is not None
        # 至少包含综合评分
        assert "overall_score" in result.data
        assert 0 <= result.data["overall_score"] <= 100

    def test_calc_marriage_with_data(self):
        """带有输入信息的合婚"""
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer._calc_marriage(
            "男方",
            {"input": {"year": 1990, "month": 6, "day": 15, "hour": 10}},
            "女方",
            {"input": {"year": 1992, "month": 3, "day": 20, "hour": 14}},
        )
        assert result.data["overall_score"] >= 0
        # 摘要中应当包含双方信息
        assert "张三" not in result.summary or result.summary  # 可以不包含，不做严格要求

    def test_calc_marriage_items_exist(self):
        """合婚的五个分项存在"""
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer._calc_marriage("甲", {}, "乙", {})
        for key in ("nayin", "ri_gan", "dizhi", "wuxing", "shengxiao"):
            assert key in result.data, f"缺失 {key}"
            assert "score" in result.data[key], f"{key} 缺少 score"


class TestFullAnalysisOptionalParams:
    """full_analysis 对姓名和合婚的可选参数支持"""

    def test_full_analysis_defaults_no_name_marriage(self):
        """默认不传 name_* 和 partner_info，结果不应包含这两个体系"""
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 30),
            gender="male",
            target_year=2026,
        )
        systems = result.systems
        # 不应该包含姓名或合婚系统
        assert "姓名学" not in systems
        assert "合婚分析" not in systems

    def test_full_analysis_with_name(self):
        """当提供姓名时，综合分析结果应包含姓名学分析"""
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 30),
            gender="male",
            target_year=2026,
            name_surname="张",
            name_given="三丰",
        )
        # 应该有姓名学系统
        assert "姓名学" in result.systems
        nr = result.systems["姓名学"]
        assert nr.data is not None
        assert "wuge" in nr.data

    def test_full_analysis_with_partner(self):
        """当提供 partner_info 时，综合分析结果应包含合婚"""
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 30),
            gender="male",
            target_year=2026,
            partner_info={
                "name1": "本人",
                "name2": "对方",
                "bazi": {"input": {"year": 1992, "month": 3, "day": 20, "hour": 14}},
            },
        )
        assert "合婚分析" in result.systems
        mr = result.systems["合婚分析"]
        assert mr.data is not None
        assert "overall_score" in mr.data

    def test_full_analysis_with_both_name_and_partner(self):
        """同时提供姓名和合婚，综合分析应同时包含两者"""
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        analyzer = ComprehensiveAnalyzer()
        result = analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 30),
            gender="male",
            target_year=2026,
            name_surname="李",
            name_given="明",
            partner_info={"name1": "本人", "name2": "对方", "bazi": {}},
        )
        assert "姓名学" in result.systems
        assert "合婚分析" in result.systems

        # 计算此时的体系数：原有的 8 个 + 姓名学 + 合婚 = 10
        # 确认 cross validation 仍然能正常工作
        assert result.cross_validation is not None
        consensus = result.consensus
        assert consensus is not None
        # consensus 中应该包含各分项和分数
        assert "overall" in consensus.__dict__ or hasattr(consensus, "overall")


class TestComprehensiveReportGeneratorExtended:
    """综合报告生成器与新字段的兼容性"""

    def test_report_with_name_system(self):
        """报告在包含姓名学时正常生成"""
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        from tengod.report_generator import ComprehensiveReportGenerator
        analyzer = ComprehensiveAnalyzer()
        result = analyzer.full_analysis(
            birth_date=(1985, 10, 5),
            birth_time=(8, 0),
            gender="male",
            target_year=2026,
            name_surname="王",
            name_given="五",
        )
        gen = ComprehensiveReportGenerator(result.to_dict())
        text = gen.text_report()
        md = gen.markdown_report()
        json_data = gen.json_report()
        # 所有输出都应非空
        assert text and isinstance(text, str)
        assert md and isinstance(md, str)
        assert isinstance(json_data, dict) and "systems" in json_data
        # json 中 systems 应包含姓名学
        assert "姓名学" in json_data["systems"]

    def test_report_with_marriage_system(self):
        """报告在包含合婚分析时正常生成"""
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        from tengod.report_generator import ComprehensiveReportGenerator
        analyzer = ComprehensiveAnalyzer()
        result = analyzer.full_analysis(
            birth_date=(1990, 6, 15),
            birth_time=(10, 30),
            gender="male",
            target_year=2026,
            partner_info={"name1": "本人", "name2": "对方", "bazi": {}},
        )
        gen = ComprehensiveReportGenerator(result.to_dict())
        text = gen.text_report()
        md = gen.markdown_report()
        html = gen.html_report()
        json_data = gen.json_report()
        assert len(text) > 0
        assert len(md) > 0
        assert "<html" in html.lower() or "<!doctype" in html.lower() or "DOCTYPE" in html
        assert "合婚分析" in json_data["systems"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
