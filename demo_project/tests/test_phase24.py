#!/usr/bin/env python3
"""
test_phase24.py — 阶段二十四：AI 解读 + 综合报告生成测试

覆盖：
  - build_comprehensive_context() 上下文构建
  - interpret_comprehensive() AI 解读（mock 模式）
  - interpret_comprehensive_stream() 流式解读
  - ComprehensiveReportGenerator (text/markdown/json/html)
  - 新 API 端点 /api/prediction/comprehensive/interpret（若 fastapi 可用）
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.pop("TENGOD_API_KEY", None)
os.environ["TENGOD_LLM_BACKEND"] = "mock"


# ════════════════════════════════════════
# 1. 上下文构建
# ════════════════════════════════════════

class TestBuildContext:
    def test_context_contains_birth_info(self):
        from tengod.ai_interpreter import build_comprehensive_context
        comp = {
            "birth_info": {"gender": "male", "target_year": 2026},
            "systems": {},
            "cross_validation": {},
            "consensus": {},
            "comprehensive_report": "",
        }
        ctx = build_comprehensive_context(comp)
        assert "男" in ctx
        assert "2026" in ctx

    def test_context_contains_systems(self):
        from tengod.ai_interpreter import build_comprehensive_context
        comp = {
            "birth_info": {},
            "systems": {
                "八字": {"available": True, "summary": "日主辛金身弱"},
                "紫微": {"available": False, "error": "数据不可用"},
            },
            "cross_validation": {},
            "consensus": {},
            "comprehensive_report": "",
        }
        ctx = build_comprehensive_context(comp)
        assert "八字" in ctx
        assert "日主辛金身弱" in ctx
        assert "紫微" in ctx
        assert "不可用" in ctx

    def test_context_contains_cross_validation(self):
        from tengod.ai_interpreter import build_comprehensive_context
        comp = {
            "birth_info": {},
            "systems": {},
            "cross_validation": {
                "score": 85,
                "level": "高度一致",
                "agreements": ["八字", "紫微"],
                "conflicts": ["奇门"],
                "interpretations": ["多数体系支持正印格局"],
            },
            "consensus": {},
            "comprehensive_report": "",
        }
        ctx = build_comprehensive_context(comp)
        assert "85" in ctx
        assert "高度一致" in ctx
        assert "八字" in ctx
        assert "奇门" in ctx

    def test_context_contains_consensus(self):
        from tengod.ai_interpreter import build_comprehensive_context
        comp = {
            "birth_info": {},
            "systems": {},
            "cross_validation": {},
            "consensus": {
                "overall": "中吉",
                "score": 72,
                "career": "事业稳固",
                "wealth": "财运中等",
                "relationships": "感情和睦",
                "health": "注意脾胃",
                "key_strengths": ["正印护身"],
                "key_risks": ["伤官见官"],
                "best_timing": ["寅卯月"],
            },
            "comprehensive_report": "原始报告内容",
        }
        ctx = build_comprehensive_context(comp)
        assert "中吉" in ctx
        assert "72" in ctx
        assert "事业稳固" in ctx
        assert "正印护身" in ctx
        assert "伤官见官" in ctx


# ════════════════════════════════════════
# 2. AI 解读（非流式）
# ════════════════════════════════════════

class TestInterpretComprehensive:
    def test_interpret_comprehensive_returns_string(self):
        import asyncio
        from tengod.ai_interpreter import interpret_comprehensive
        comp = {
            "birth_info": {"gender": "male", "target_year": 2026},
            "systems": {
                "八字": {"available": True, "summary": "日主辛金", "data": {"yongshen": ["土", "金"]}},
                "紫微": {"available": True, "summary": "天同星入命", "data": {}},
            },
            "cross_validation": {
                "score": 80, "level": "基本一致",
                "agreements": ["八字", "紫微"], "conflicts": [], "interpretations": [],
            },
            "consensus": {
                "overall": "中吉", "score": 75,
                "career": "事业稳固", "wealth": "财运中等",
                "relationships": "感情和睦", "health": "注意脾胃",
                "key_strengths": ["正印护身"], "key_risks": ["伤官"],
                "best_timing": ["寅卯月"], "weak_timing": [],
            },
            "comprehensive_report": "多体系综合分析已完成",
        }

        async def run():
            result = await interpret_comprehensive(comp)
            assert isinstance(result, str)
            assert len(result) > 0
            return result

        asyncio.run(run())

    def test_interpret_comprehensive_with_question(self):
        import asyncio
        from tengod.ai_interpreter import interpret_comprehensive
        comp = {
            "birth_info": {"gender": "female", "target_year": 2026},
            "systems": {"八字": {"available": True, "summary": "甲木日主", "data": {}}},
            "cross_validation": {"score": 70, "level": "中等", "agreements": [], "conflicts": [], "interpretations": []},
            "consensus": {"overall": "平", "score": 60, "career": "", "wealth": "", "relationships": "", "health": ""},
            "comprehensive_report": "",
        }

        async def run():
            result = await interpret_comprehensive(comp, question="我的事业运如何")
            assert isinstance(result, str)
            return result

        asyncio.run(run())


# ════════════════════════════════════════
# 3. 流式解读
# ════════════════════════════════════════

class TestInterpretComprehensiveStream:
    def test_interpret_stream_yields_chunks(self):
        import asyncio
        from tengod.ai_interpreter import interpret_comprehensive_stream
        comp = {
            "birth_info": {"gender": "male", "target_year": 2026},
            "systems": {"八字": {"available": True, "summary": "辛金日主", "data": {}}},
            "cross_validation": {"score": 75, "level": "中", "agreements": [], "conflicts": [], "interpretations": []},
            "consensus": {"overall": "吉", "score": 70, "career": "", "wealth": "", "relationships": "", "health": ""},
            "comprehensive_report": "",
        }

        async def run():
            chunks = []
            async for chunk in interpret_comprehensive_stream(comp):
                chunks.append(chunk)
                assert isinstance(chunk, str)
            assert len(chunks) > 0
            full = "".join(chunks)
            assert len(full) > 0
            return full

        asyncio.run(run())


# ════════════════════════════════════════
# 4. 综合报告生成器
# ════════════════════════════════════════

class TestComprehensiveReportGenerator:
    def test_text_report_structure(self):
        from tengod.report_generator import ComprehensiveReportGenerator
        comp = {
            "birth_info": {"gender": "male", "target_year": 2026},
            "systems": {
                "八字": {"available": True, "summary": "辛金日主，身弱用印"},
                "紫微": {"available": False, "error": "引擎不可用"},
            },
            "cross_validation": {
                "score": 82, "level": "高度一致",
                "agreements": ["八字"], "conflicts": [],
                "interpretations": ["格局支持正印"],
            },
            "consensus": {
                "overall": "中吉", "score": 78,
                "career": "事业稳固", "wealth": "财运中等",
                "relationships": "感情和睦", "health": "注意脾胃",
                "key_strengths": ["正印护身"],
                "key_risks": ["伤官"],
                "best_timing": ["寅卯月"], "weak_timing": [],
            },
            "comprehensive_report": "综合报告正文内容",
        }
        gen = ComprehensiveReportGenerator(comp)
        text = gen.text_report()
        assert isinstance(text, str)
        assert len(text) > 50
        assert "中吉" in text
        assert "事业稳固" in text
        assert "正印护身" in text
        assert "82" in text  # cross score

    def test_markdown_report_structure(self):
        from tengod.report_generator import ComprehensiveReportGenerator
        comp = {
            "birth_info": {"gender": "female", "target_year": 2026},
            "systems": {"八字": {"available": True, "summary": "甲木日主"}},
            "cross_validation": {"score": 60, "level": "中等",
                                "agreements": [], "conflicts": [], "interpretations": []},
            "consensus": {"overall": "平", "score": 55, "career": "事业平",
                         "wealth": "", "relationships": "", "health": ""},
            "comprehensive_report": "报告",
        }
        gen = ComprehensiveReportGenerator(comp)
        md = gen.markdown_report()
        assert "# 多体系" in md
        assert "★" in md
        assert "事业平" in md

    def test_json_report_has_summary(self):
        from tengod.report_generator import ComprehensiveReportGenerator
        comp = {
            "birth_info": {"gender": "male", "target_year": 2026},
            "systems": {"八字": {"available": True, "summary": ""}},
            "cross_validation": {"score": 90, "level": "高度",
                                "agreements": ["八字"], "conflicts": [], "interpretations": []},
            "consensus": {"overall": "大吉", "score": 88,
                         "career": "", "wealth": "", "relationships": "", "health": ""},
            "comprehensive_report": "",
        }
        gen = ComprehensiveReportGenerator(comp)
        j = gen.json_report()
        assert "summary" in j
        assert j["summary"]["overall"] == "大吉"
        assert j["summary"]["score"] == 88
        assert j["summary"]["agreed_count"] == 1
        assert j["summary"]["system_count"] == 1

    def test_html_report_is_complete(self):
        from tengod.report_generator import ComprehensiveReportGenerator
        comp = {
            "birth_info": {"gender": "male", "target_year": 2026},
            "systems": {},
            "cross_validation": {"score": 70, "level": "中",
                                "agreements": [], "conflicts": [], "interpretations": []},
            "consensus": {"overall": "平", "score": 65, "career": "", "wealth": "", "relationships": "", "health": ""},
            "comprehensive_report": "",
        }
        gen = ComprehensiveReportGenerator(comp)
        html = gen.html_report()
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "<title>" in html
        assert "多体系综合" in html

    def test_level_bar_five_stars(self):
        from tengod.report_generator import ComprehensiveReportGenerator
        comp = {"birth_info": {}, "systems": {},
                "cross_validation": {}, "consensus": {}, "comprehensive_report": ""}
        gen = ComprehensiveReportGenerator(comp)
        assert "★" * 5 in gen._level_bar(100)
        assert "☆" * 5 in gen._level_bar(0)
        assert gen._level_bar(50) == "★★" + "☆" * 3


# ════════════════════════════════════════
# 5. API 端点（若 fastapi 可用）
# ════════════════════════════════════════

try:
    from fastapi.testclient import TestClient
    from tengod.api_server import app
    from tengod.auth import JWTManager
    HAS_FASTAPI = True
except Exception:
    HAS_FASTAPI = False


def unwrap(r):
    """解包内在小孩门禁包裹的响应 {output, confidence, uncertainty} → output"""
    data = r.json()
    if isinstance(data, dict) and "output" in data and "confidence" in data:
        return data["output"]
    return data


@pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi / tengod.api_server 不可用")
class TestComprehensiveInterpretAPI:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def user_headers(self):
        token = JWTManager.create_access_token(1, "testuser", "user")
        return {"Authorization": f"Bearer {token}"}

    def test_interpret_endpoint_success(self, client, user_headers):
        resp = client.post("/api/prediction/comprehensive/interpret",
                          headers=user_headers, json={
            "birth_year": 1990, "birth_month": 6, "birth_day": 15,
            "birth_hour": 10, "birth_minute": 0, "gender": "male",
            "target_year": 2026, "sitting": "北", "facing": "南",
            "report_format": "text",
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert "ai_interpretation" in data
        assert "formatted_report" in data
        assert "raw_result" in data
        assert data["format"] == "text"
        assert isinstance(data["ai_interpretation"], str)
        assert len(data["ai_interpretation"]) > 0

    def test_interpret_endpoint_markdown_format(self, client, user_headers):
        resp = client.post("/api/prediction/comprehensive/interpret",
                          headers=user_headers, json={
            "birth_year": 1985, "birth_month": 3, "birth_day": 20,
            "birth_hour": 14, "birth_minute": 0, "gender": "female",
            "target_year": 2026, "report_format": "markdown",
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert data["format"] == "markdown"
        assert "多体系" in data["formatted_report"]
        assert "# " in data["formatted_report"]

    def test_interpret_endpoint_validation(self, client, user_headers):
        resp = client.post("/api/prediction/comprehensive/interpret",
                          headers=user_headers, json={"birth_year": 1990})
        assert resp.status_code == 422

    def test_interpret_endpoint_with_pillars(self, client, user_headers):
        resp = client.post("/api/prediction/comprehensive/interpret",
                          headers=user_headers, json={
            "birth_year": 1990, "birth_month": 6, "birth_day": 15,
            "birth_hour": 10, "birth_minute": 0, "gender": "male",
            "target_year": 2026,
            "pillars": {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            "report_format": "text",
        })
        assert resp.status_code == 200
        data = unwrap(resp)
        assert "ai_interpretation" in data


# ════════════════════════════════════════
# 6. 端到端集成（Mock LLM）
# ════════════════════════════════════════

class TestEndToEnd:
    def test_full_pipeline_analyzer_to_interpret(self):
        """从 ComprehensiveAnalyzer → AI 解读 → 报告生成 全流程"""
        import asyncio
        from tengod.multi_system_engine import ComprehensiveAnalyzer
        from tengod.ai_interpreter import interpret_comprehensive
        from tengod.report_generator import ComprehensiveReportGenerator

        async def run():
            analyzer = ComprehensiveAnalyzer()
            result = analyzer.full_analysis(
                birth_date=(1990, 6, 15),
                birth_time=(10, 30),
                gender="male",
                target_year=2026,
            )
            comp_dict = result.to_dict()

            # AI 解读
            ai_report = await interpret_comprehensive(comp_dict)
            assert isinstance(ai_report, str)
            assert len(ai_report) > 0

            # 报告生成
            gen = ComprehensiveReportGenerator(comp_dict)
            text_report = gen.text_report()
            md_report = gen.markdown_report()
            json_report = gen.json_report()

            assert len(text_report) > 50
            assert "# 多体系" in md_report
            assert "summary" in json_report
            assert json_report["summary"]["system_count"] == len(comp_dict["systems"])

        asyncio.run(run())

    def test_report_generator_different_formats(self):
        """四种报告格式均能正确生成"""
        from tengod.report_generator import ComprehensiveReportGenerator
        comp = {
            "birth_info": {"gender": "male", "target_year": 2026},
            "systems": {
                "八字": {"available": True, "summary": "辛金日主"},
                "紫微": {"available": True, "summary": "天同入命"},
            },
            "cross_validation": {"score": 75, "level": "中",
                                "agreements": ["八字"], "conflicts": [], "interpretations": []},
            "consensus": {"overall": "吉", "score": 70, "career": "事业佳",
                         "wealth": "财运平", "relationships": "", "health": "",
                         "key_strengths": ["正印"], "key_risks": [], "best_timing": [], "weak_timing": []},
            "comprehensive_report": "综合分析正文",
        }
        gen = ComprehensiveReportGenerator(comp)
        assert len(gen.text_report()) > 0
        assert len(gen.markdown_report()) > 50
        assert len(gen.html_report()) > 100
        assert "summary" in gen.json_report()
        assert gen.json_report()["summary"]["overall"] == "吉"
        assert gen.json_report()["summary"]["score"] == 70


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
