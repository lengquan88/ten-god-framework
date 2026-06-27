#!/usr/bin/env python3
"""
test_ai_interpreter.py — AI 智能解读服务测试
覆盖：上下文构建器、解读函数、API 端点
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.pop("TENGOD_API_KEY", None)
os.environ["TENGOD_LLM_BACKEND"] = "mock"

from fastapi.testclient import TestClient

from tengod.ai_interpreter import (
    BAZI_INTERPRET_PROMPT,
    LIUYAO_INTERPRET_PROMPT,
    MARRIAGE_INTERPRET_PROMPT,
    NAME_INTERPRET_PROMPT,
    ORACLE_INTERPRET_PROMPT,
    ZIWEI_INTERPRET_PROMPT,
    _to_dict,
    build_bazi_context,
    build_liuyao_context,
    build_marriage_context,
    build_name_context,
    build_oracle_context,
    build_ziwei_context,
    interpret_bazi,
    interpret_bazi_from_analysis,
    interpret_liuyao,
    interpret_marriage,
    interpret_name,
    interpret_oracle,
    interpret_ziwei,
)
from tengod.api_server import app
from tengod.auth import JWTManager, QuotaManager

client = TestClient(app)


# ════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════

def unwrap(r):
    """解包内在小孩门禁包裹的响应 {output, confidence, uncertainty} → output"""
    data = r.json()
    if isinstance(data, dict) and "output" in data and "confidence" in data:
        return data["output"]
    return data


def get_auth_headers():
    """获取认证用户 token"""
    token = JWTManager.create_access_token(1, "testuser", "user")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_state():
    """每个测试前清空配额和限流状态"""
    QuotaManager._usage.clear()
    from tengod.api_server import _request_counts
    _request_counts.clear()
    yield
    QuotaManager._usage.clear()
    _request_counts.clear()


# ════════════════════════════════════════
# 1. Prompt 模板测试
# ════════════════════════════════════════

class TestPromptTemplates:
    """Prompt 模板完整性测试"""

    def test_bazi_prompt_exists(self):
        assert "八字" in BAZI_INTERPRET_PROMPT
        assert "格局" in BAZI_INTERPRET_PROMPT
        assert "喜用神" in BAZI_INTERPRET_PROMPT
        assert "神煞" in BAZI_INTERPRET_PROMPT
        assert "大运" in BAZI_INTERPRET_PROMPT

    def test_ziwei_prompt_exists(self):
        assert "紫微斗数" in ZIWEI_INTERPRET_PROMPT
        assert "命宫" in ZIWEI_INTERPRET_PROMPT
        assert "十二宫" in ZIWEI_INTERPRET_PROMPT

    def test_liuyao_prompt_exists(self):
        assert "六爻" in LIUYAO_INTERPRET_PROMPT
        assert "用神" in LIUYAO_INTERPRET_PROMPT
        assert "世应" in LIUYAO_INTERPRET_PROMPT

    def test_name_prompt_exists(self):
        assert "姓名学" in NAME_INTERPRET_PROMPT
        assert "五格" in NAME_INTERPRET_PROMPT
        assert "三才" in NAME_INTERPRET_PROMPT

    def test_marriage_prompt_exists(self):
        assert "合婚" in MARRIAGE_INTERPRET_PROMPT
        assert "纳音" in MARRIAGE_INTERPRET_PROMPT

    def test_oracle_prompt_exists(self):
        assert "推背图" in ORACLE_INTERPRET_PROMPT or "易经" in ORACLE_INTERPRET_PROMPT
        assert "卦辞" in ORACLE_INTERPRET_PROMPT


# ════════════════════════════════════════
# 2. 上下文构建器测试
# ════════════════════════════════════════

class TestContextBuilders:
    """结构化数据 → 上下文转换器测试"""

    def test_build_bazi_context_basic(self):
        """八字上下文基本构建"""
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
            gender="male",
        )
        assert "庚午" in ctx
        assert "壬午" in ctx
        assert "辛亥" in ctx
        assert "癸巳" in ctx
        assert "辛金" in ctx
        assert "male" in ctx

    def test_build_bazi_context_full(self):
        """八字上下文完整构建（含神煞/格局/喜用神/调候/大运）"""
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
            gender="male",
            wuxing={"金": 2, "水": 2, "火": 3, "土": 1},
            shigan_map={"year_gan": "劫财", "month_gan": "伤官"},
            shensha={
                "year_shens": {"天乙贵人": {"category": "吉神"}},
                "month_shens": {"驿马": {"category": "凶神"}},
            },
            geju={"geju_name": "伤官格", "geju_type": "伤官", "geju_desc": "聪明叛逆", "is_cong": False},
            yongshen={"wang_shuai": "衰", "yong_shen": ["土", "金"], "ji_shen": ["火"]},
            tiaohou={"season": "夏", "required_tiaohou": True, "tiaohou_shens": ["壬", "癸"]},
            dayuns=[{"start_age": 6, "end_age": 15, "ganzhi": "癸未"}],
            branch_relations={"六合": ["午未"], "三合": []},
        )
        assert "五行分布" in ctx
        assert "金2个" in ctx
        assert "十神" in ctx
        assert "劫财" in ctx
        assert "神煞" in ctx
        assert "天乙贵人" in ctx
        assert "年柱" in ctx
        assert "格局" in ctx
        assert "伤官格" in ctx
        assert "喜用神" in ctx
        assert "土" in ctx
        assert "金" in ctx
        assert "调候" in ctx
        assert "夏" in ctx
        assert "大运" in ctx
        assert "癸未" in ctx
        assert "地支关系" in ctx
        assert "午未" in ctx

    def test_build_ziwei_context(self):
        """紫微斗数上下文构建"""
        ctx = build_ziwei_context({
            "gender": "male",
            "lunar_month": 5,
            "lunar_day": 15,
            "year_gan": "庚",
            "year_zhi": "午",
            "hour_zhi": "巳",
            "ming_gong": {"gong_name": "命宫", "gong_zhi": "寅", "stars": [{"name": "紫微"}]},
            "palaces": [{"gong_name": "命宫", "gong_zhi": "寅", "stars": [{"name": "紫微"}]}],
        })
        assert "紫微斗数" in ctx
        assert "male" in ctx
        assert "命宫" in ctx
        assert "紫微" in ctx

    def test_build_liuyao_context(self):
        """六爻上下文构建"""
        ctx = build_liuyao_context({
            "ben_gua_name": "乾为天",
            "ben_gua_symbol": "䷀",
            "bian_gua_name": "天风姤",
            "shang_gua": "乾",
            "xia_gua": "乾",
            "gua_gong": "乾宫",
            "liuqin": ["父母", "兄弟", "妻财", "官鬼", "父母", "子孙"],
            "liushen": ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"],
            "shi_yao": "6",
            "ying_yao": "3",
            "day_ganzhi": "甲子",
            "dong_yao": [0, 2],
            "duan_ci": "吉卦",
        })
        assert "乾为天" in ctx
        assert "乾" in ctx
        assert "六亲" in ctx
        assert "父母" in ctx
        assert "六神" in ctx
        assert "青龙" in ctx
        assert "世爻" in ctx
        assert "应爻" in ctx
        assert "甲子" in ctx
        assert "动爻" in ctx

    def test_build_name_context(self):
        """姓名学上下文构建"""
        ctx = build_name_context({
            "surname": "张",
            "given_name": "伟",
            "surname_strokes": 11,
            "given_strokes": [6],
            "wuge": {"tian": 12, "ren": 17, "di": 7, "wai": 2, "zong": 17},
            "sancai": ("木", "金", "金"),
            "sancai_ji": "凶",
            "sancai_desc": "金克木",
            "score": 65,
            "suggestions": ["建议改名"],
        })
        assert "张伟" in ctx
        assert "五格" in ctx
        assert "天格" in ctx
        assert "三才" in ctx
        assert "木" in ctx
        assert "65" in ctx

    def test_build_marriage_context(self):
        """合婚上下文构建"""
        ctx = build_marriage_context({
            "name1": "张三",
            "name2": "李四",
            "nayin1": "路旁土",
            "nayin2": "海中金",
            "nayin_match": "土生金",
            "nayin_score": 90,
            "day_gan1": "辛",
            "day_gan2": "甲",
            "day_gan_relation": "甲木克辛金",
            "day_gan_score": 60,
            "total_score": 75,
            "conclusion": "中等匹配",
        })
        assert "张三" in ctx
        assert "李四" in ctx
        assert "路旁土" in ctx
        assert "海中金" in ctx
        assert "纳音" in ctx
        assert "75" in ctx

    def test_build_oracle_context(self):
        """Oracle 上下文构建"""
        ctx = build_oracle_context({
            "mode": "TUIBEITU",
            "hexagram": "䷀",
            "hexagram_index": 1,
            "upper_trigram": "乾",
            "lower_trigram": "乾",
            "yao_lines": ["阳", "阳", "阳", "阳", "阳", "阳"],
            "judgment": "元亨利贞",
            "image": "天行健",
        })
        assert "推背图" in ctx or "周易" in ctx
        assert "乾" in ctx
        assert "元亨利贞" in ctx
        assert "爻象" in ctx


# ════════════════════════════════════════
# 3. 解读函数测试（Mock LLM）
# ════════════════════════════════════════

class TestInterpretFunctions:
    """AI 解读函数测试（使用 Mock LLM）"""

    @pytest.mark.asyncio
    async def test_interpret_bazi(self):
        """八字解读"""
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
        )
        result = await interpret_bazi(ctx)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_ziwei(self):
        """紫微解读"""
        ctx = build_ziwei_context({"gender": "male", "ming_gong": {"gong_name": "命宫"}})
        result = await interpret_ziwei(ctx)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_liuyao(self):
        """六爻解读"""
        ctx = build_liuyao_context({"ben_gua_name": "乾为天", "shang_gua": "乾", "xia_gua": "乾"})
        result = await interpret_liuyao(ctx, question="事业")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_name(self):
        """姓名解读"""
        ctx = build_name_context({"surname": "张", "given_name": "伟", "score": 65})
        result = await interpret_name(ctx)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_marriage(self):
        """合婚解读"""
        ctx = build_marriage_context({"name1": "张三", "name2": "李四", "total_score": 75})
        result = await interpret_marriage(ctx)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_oracle(self):
        """Oracle 解读"""
        ctx = build_oracle_context({"hexagram": "䷀", "upper_trigram": "乾", "lower_trigram": "乾"})
        result = await interpret_oracle(ctx, question="事业")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_bazi_with_question(self):
        """八字解读带具体问题"""
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
        )
        result = await interpret_bazi(ctx, question="我的事业运如何？")
        assert isinstance(result, str)
        assert len(result) > 0


# ════════════════════════════════════════
# 4. _to_dict 辅助函数测试
# ════════════════════════════════════════

class TestToDict:
    """_to_dict 转换函数测试"""

    def test_to_dict_primitive(self):
        assert _to_dict(42) == 42
        assert _to_dict("hello") == "hello"
        assert _to_dict(None) is None

    def test_to_dict_list(self):
        assert _to_dict([1, 2, 3]) == [1, 2, 3]

    def test_to_dict_dict(self):
        d = {"a": 1, "b": [2, 3]}
        result = _to_dict(d)
        assert result == d

    def test_to_dict_dataclass(self):
        from dataclasses import dataclass

        @dataclass
        class Sample:
            x: int
            y: str

        s = Sample(1, "hello")
        result = _to_dict(s)
        assert result == {"x": 1, "y": "hello"}


# ════════════════════════════════════════
# 5. API 端点测试
# ════════════════════════════════════════

class TestAIInterpretAPI:
    """AI 解读 API 端点测试"""

    def test_bazi_interpret_unauthorized(self):
        """未认证用户不能访问（需要 ai:interpret 权限）"""
        r = client.post("/api/ai/interpret/bazi", json={
            "year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male",
        })
        assert r.status_code in (401, 403)

    def test_bazi_interpret_authorized(self):
        """认证用户可访问八字 AI 解读"""
        r = client.post("/api/ai/interpret/bazi", json={
            "year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male",
        }, headers=get_auth_headers())
        assert r.status_code == 200
        data = unwrap(r)
        assert "interpretation" in data
        assert "model" in data
        assert isinstance(data["interpretation"], str)
        assert len(data["interpretation"]) > 0

    def test_bazi_interpret_with_question(self):
        """带问题的八字解读"""
        r = client.post("/api/ai/interpret/bazi", json={
            "year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male",
        }, params={"question": "事业运如何？"}, headers=get_auth_headers())
        assert r.status_code == 200

    def test_ziwei_interpret(self):
        """紫微斗数 AI 解读"""
        r = client.post("/api/ai/interpret/ziwei", json={
            "year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male",
        }, headers=get_auth_headers())
        assert r.status_code == 200
        data = unwrap(r)
        assert "interpretation" in data

    def test_liuyao_interpret(self):
        """六爻 AI 解读"""
        r = client.post("/api/ai/interpret/liuyao",
                       params={"question": "事业发展"},
                       headers=get_auth_headers())
        assert r.status_code == 200
        data = unwrap(r)
        assert "interpretation" in data
        assert "gua_name" in data

    def test_name_interpret(self):
        """姓名学 AI 解读"""
        r = client.post("/api/ai/interpret/name",
                       params={"surname": "张", "given_name": "伟"},
                       headers=get_auth_headers())
        assert r.status_code == 200
        data = unwrap(r)
        assert "interpretation" in data
        assert "score" in data

    def test_oracle_interpret(self):
        """Oracle AI 解读"""
        r = client.post("/api/ai/interpret/oracle",
                       params={"question": "事业发展", "mode": "tuibeitu"},
                       headers=get_auth_headers())
        assert r.status_code == 200
        data = unwrap(r)
        assert "interpretation" in data

    def test_marriage_interpret(self):
        """合婚 AI 解读"""
        r = client.post("/api/ai/interpret/marriage", json={
            "name1": "张三",
            "name2": "李四",
            "bazi1": {"day_master": "辛", "pillars": {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"}},
            "bazi2": {"day_master": "甲", "pillars": {"year": "甲子", "month": "丙寅", "day": "甲午", "hour": "乙丑"}},
        }, headers=get_auth_headers())
        assert r.status_code == 200
        data = unwrap(r)
        assert "interpretation" in data

    def test_bazi_interpret_validation_error(self):
        """八字解读参数校验"""
        r = client.post("/api/ai/interpret/bazi", json={
            "year": 1800,  # 超出范围
            "month": 6, "day": 15, "hour": 10, "gender": "male",
        }, headers=get_auth_headers())
        assert r.status_code == 422


# ════════════════════════════════════════
# 6. 集成测试：从引擎结果直接解读
# ════════════════════════════════════════

class TestIntegrationFromEngines:
    """从引擎结果直接生成解读的集成测试"""

    @pytest.mark.asyncio
    async def test_interpret_from_bazi_analysis(self):
        """从 BaziAnalyzer.analysis 生成解读"""
        from tengod.bazi_analyzer import BaziAnalyzer
        from tengod.geju_engine import analyze_bazi_comprehensive
        from tengod.shensha_engine import calc_all_shensha

        analyzer = BaziAnalyzer(1990, 6, 15, 10, 30, is_male=True)
        shensha = calc_all_shensha(analyzer.analysis["pillars"])
        comprehensive = analyze_bazi_comprehensive(analyzer.analysis["pillars"])

        result = await interpret_bazi_from_analysis(
            analysis=analyzer.analysis,
            shensha_result=shensha,
            comprehensive_result=comprehensive,
        )
        assert isinstance(result, str)
        assert len(result) > 0


# ════════════════════════════════════════
# 7. 流式解读测试
# ════════════════════════════════════════

class TestStreamInterpret:
    """流式 AI 解读测试"""

    @pytest.mark.asyncio
    async def test_interpret_bazi_stream(self):
        """八字流式解读"""
        from tengod.ai_interpreter import interpret_bazi_stream
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
        )
        chunks = []
        async for chunk in interpret_bazi_stream(ctx):
            chunks.append(chunk)
        assert len(chunks) > 0
        result = "".join(chunks)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_bazi_stream_with_question(self):
        """八字流式解读带问题"""
        from tengod.ai_interpreter import interpret_bazi_stream
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
        )
        chunks = []
        async for chunk in interpret_bazi_stream(ctx, question="我的财运如何？"):
            chunks.append(chunk)
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_interpret_bazi_stream_with_rag(self):
        """八字流式解读 + RAG"""
        from tengod.ai_interpreter import interpret_bazi_stream
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
        )
        chunks = []
        async for chunk in interpret_bazi_stream(ctx, use_rag=True):
            chunks.append(chunk)
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_interpret_comprehensive_stream(self):
        """综合分析流式解读"""
        from tengod.ai_interpreter import interpret_comprehensive_stream
        comp_dict = {
            "birth_info": {"gender": "male", "target_year": 2025},
            "systems": {
                "bazi": {"available": True, "summary": "身弱喜印比", "data": {"yongshen": ["土", "金"]}},
            },
            "cross_validation": {
                "score": 85, "level": "高",
                "agreements": ["喜土金", "忌火木"],
                "conflicts": [],
                "interpretations": ["各体系一致"],
            },
            "consensus": {
                "overall": "中上", "score": 78,
                "career": "吉", "wealth": "平", "relationships": "吉", "health": "平",
            },
            "comprehensive_report": "测试报告",
        }
        chunks = []
        async for chunk in interpret_comprehensive_stream(comp_dict):
            chunks.append(chunk)
        assert len(chunks) > 0


# ════════════════════════════════════════
# 8. 综合分析上下文构建与解读
# ════════════════════════════════════════

class TestComprehensive:
    """多体系综合分析测试"""

    def test_system_prompt_for_comprehensive(self):
        """综合 Prompt 模板"""
        from tengod.ai_interpreter import (
            SYSTEM_PROMPT_FOR_COMPREHENSIVE,
            SYSTEM_PROMPT_FOR_MOCK_COMPREHENSIVE,
        )
        assert "八字" in SYSTEM_PROMPT_FOR_COMPREHENSIVE
        assert "紫微" in SYSTEM_PROMPT_FOR_COMPREHENSIVE
        assert "以上仅供参考" in SYSTEM_PROMPT_FOR_COMPREHENSIVE
        assert "以上仅供参考" in SYSTEM_PROMPT_FOR_MOCK_COMPREHENSIVE

    def test_build_comprehensive_context_basic(self):
        """综合分析上下文构建"""
        from tengod.ai_interpreter import build_comprehensive_context
        comp_dict = {
            "birth_info": {"gender": "male", "target_year": 2025},
            "systems": {
                "bazi": {
                    "available": True,
                    "summary": "身弱喜印比",
                    "data": {"yongshen": ["土", "金"], "geju_name": "正印格"},
                },
            },
            "cross_validation": {
                "score": 85, "level": "高",
                "agreements": ["喜土金"],
                "conflicts": [],
                "interpretations": ["各体系一致"],
            },
            "consensus": {
                "overall": "中上", "score": 78,
                "career": "吉", "wealth": "平", "relationships": "吉", "health": "平",
                "key_strengths": ["贵人运强"],
                "key_risks": ["火旺之年需注意"],
                "best_timing": ["2025年秋"],
                "weak_timing": ["2026年夏"],
            },
            "comprehensive_report": "测试报告",
        }
        ctx = build_comprehensive_context(comp_dict)
        assert "基础信息" in ctx
        assert "男" in ctx
        assert "2025" in ctx
        assert "各体系结论摘要" in ctx
        assert "bazi" in ctx
        assert "身弱喜印比" in ctx
        assert "交叉验证结果" in ctx
        assert "85" in ctx
        assert "共识运势" in ctx
        assert "核心优势" in ctx
        assert "核心风险" in ctx
        assert "最佳时机" in ctx
        assert "弱运时机" in ctx
        assert "系统原始报告摘要" in ctx

    def test_build_comprehensive_context_unavailable_system(self):
        """综合分析上下文 - 不可用体系"""
        from tengod.ai_interpreter import build_comprehensive_context
        comp_dict = {
            "birth_info": {"gender": "female", "target_year": 2025},
            "systems": {
                "qimen": {"available": False, "error": "引擎未加载"},
            },
            "cross_validation": {"score": 50, "level": "低"},
            "consensus": {"overall": "中", "score": 50, "career": "平", "wealth": "平", "relationships": "平", "health": "平"},
            "comprehensive_report": "",
        }
        ctx = build_comprehensive_context(comp_dict)
        assert "不可用" in ctx
        assert "引擎未加载" in ctx

    def test_build_comprehensive_context_female(self):
        """综合分析上下文 - 女性"""
        from tengod.ai_interpreter import build_comprehensive_context
        comp_dict = {
            "birth_info": {"gender": "female", "target_year": 2025},
            "systems": {},
            "cross_validation": {"score": 50, "level": "中"},
            "consensus": {"overall": "中", "score": 50, "career": "平", "wealth": "平", "relationships": "平", "health": "平"},
            "comprehensive_report": "",
        }
        ctx = build_comprehensive_context(comp_dict)
        assert "女" in ctx

    def test_build_comprehensive_context_with_conflicts(self):
        """综合分析上下文 - 有分歧"""
        from tengod.ai_interpreter import build_comprehensive_context
        comp_dict = {
            "birth_info": {"gender": "male", "target_year": 2025},
            "systems": {},
            "cross_validation": {
                "score": 60, "level": "中",
                "agreements": [],
                "conflicts": ["八字喜土金，紫微喜水木"],
                "interpretations": ["体系间存在分歧，需综合判断"],
            },
            "consensus": {"overall": "中", "score": 60, "career": "平", "wealth": "平", "relationships": "平", "health": "平"},
            "comprehensive_report": "",
        }
        ctx = build_comprehensive_context(comp_dict)
        assert "存在分歧" in ctx

    @pytest.mark.asyncio
    async def test_interpret_comprehensive(self):
        """综合分析解读"""
        from tengod.ai_interpreter import interpret_comprehensive
        comp_dict = {
            "birth_info": {"gender": "male", "target_year": 2025},
            "systems": {
                "bazi": {"available": True, "summary": "身弱喜印比", "data": {"yongshen": ["土", "金"]}},
            },
            "cross_validation": {"score": 85, "level": "高"},
            "consensus": {"overall": "中上", "score": 78, "career": "吉", "wealth": "平", "relationships": "吉", "health": "平"},
            "comprehensive_report": "",
        }
        result = await interpret_comprehensive(comp_dict)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_comprehensive_with_question(self):
        """综合分析解读带问题"""
        from tengod.ai_interpreter import interpret_comprehensive
        comp_dict = {
            "birth_info": {"gender": "male", "target_year": 2025},
            "systems": {},
            "cross_validation": {"score": 50, "level": "中"},
            "consensus": {"overall": "中", "score": 50, "career": "平", "wealth": "平", "relationships": "平", "health": "平"},
            "comprehensive_report": "",
        }
        result = await interpret_comprehensive(comp_dict, question="我的事业如何？")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_comprehensive_with_rag(self):
        """综合分析解读 + RAG"""
        from tengod.ai_interpreter import interpret_comprehensive
        comp_dict = {
            "birth_info": {"gender": "male", "target_year": 2025},
            "systems": {},
            "cross_validation": {"score": 50, "level": "中"},
            "consensus": {"overall": "中", "score": 50, "career": "平", "wealth": "平", "relationships": "平", "health": "平"},
            "comprehensive_report": "",
        }
        result = await interpret_comprehensive(comp_dict, use_rag=True)
        assert isinstance(result, str)
        assert len(result) > 0


# ════════════════════════════════════════
# 9. 上下文构建器边缘情况测试
# ════════════════════════════════════════

class TestContextBuilderEdgeCases:
    """上下文构建器边缘情况"""

    def test_build_bazi_context_empty(self):
        """八字上下文 - 空参数"""
        ctx = build_bazi_context(pillars={})
        assert "未指定" in ctx
        assert "未知" in ctx

    def test_build_bazi_context_extra(self):
        """八字上下文 - 补充信息"""
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
            extra={"备注": "测试", "来源": "自动化"},
        )
        assert "补充信息" in ctx
        assert "备注" in ctx
        assert "测试" in ctx
        assert "来源" in ctx

    def test_build_bazi_context_non_dict_dayuns(self):
        """八字上下文 - 非字典大运"""
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
            dayuns=["癸未", "壬午", "辛巳"],
        )
        assert "癸未" in ctx
        assert "大运1" in ctx

    def test_build_bazi_context_empty_branch_relations(self):
        """八字上下文 - 空地支关系"""
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
            branch_relations={"六合": [], "三合": [], "六冲": []},
        )
        assert "地支关系" in ctx

    def test_build_bazi_context_no_optional(self):
        """八字上下文 - 无任何可选字段"""
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
            gender="female",
        )
        assert "female" in ctx
        assert "庚午" in ctx

    def test_build_bazi_context_cong_ge(self):
        """八字上下文 - 从格"""
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
            geju={"geju_name": "从财格", "geju_type": "从格", "geju_desc": "从财", "is_cong": True},
        )
        assert "从格" in ctx

    def test_build_ziwei_context_full(self):
        """紫微上下文 - 完整数据"""
        ctx = build_ziwei_context({
            "gender": "female",
            "lunar_month": 3,
            "lunar_day": 8,
            "year_gan": "甲",
            "year_zhi": "子",
            "hour_zhi": "卯",
            "ming_gong": {"gong_name": "命宫", "gong_zhi": "寅", "stars": ["紫微", "天相"]},
            "shen_gong": {"gong_name": "身宫", "gong_zhi": "申"},
            "palaces": [
                {"gong_name": "命宫", "gong_zhi": "寅", "stars": ["紫微"]},
                {"gong_name": "兄弟宫", "gong_zhi": "卯", "stars": []},
            ],
            "sihua": {"化禄": "天机", "化权": "太阳"},
        })
        assert "紫微斗数" in ctx
        assert "身宫" in ctx
        assert "四化" in ctx
        assert "化禄" in ctx
        assert "空宫" in ctx

    def test_build_ziwei_context_minimal(self):
        """紫微上下文 - 最小数据"""
        ctx = build_ziwei_context({"gender": "male"})
        assert "紫微斗数" in ctx
        assert isinstance(ctx, str)

    def test_build_liuyao_context_full(self):
        """六爻上下文 - 完整数据"""
        ctx = build_liuyao_context({
            "ben_gua_name": "乾为天",
            "ben_gua_symbol": "䷀",
            "bian_gua_name": "天风姤",
            "bian_gua_symbol": "䷫",
            "hu_gua_name": "乾为天",
            "shang_gua": "乾",
            "xia_gua": "乾",
            "gua_gong": "乾宫",
            "liuqin": ["父母", "兄弟", "妻财", "官鬼", "父母", "子孙"],
            "liushen": ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"],
            "shi_yao": "6",
            "ying_yao": "3",
            "day_ganzhi": "甲子",
            "dong_yao": [0, 2, 4],
            "duan_ci": "大吉之卦",
        })
        assert "互卦" in ctx
        assert "乾为天" in ctx
        assert "大吉之卦" in ctx

    def test_build_liuyao_context_minimal(self):
        """六爻上下文 - 最小数据"""
        ctx = build_liuyao_context({"ben_gua_name": "乾为天"})
        assert "乾为天" in ctx
        assert isinstance(ctx, str)

    def test_build_name_context_minimal(self):
        """姓名学上下文 - 最小数据"""
        ctx = build_name_context({"surname": "张", "given_name": "三"})
        assert "张三" in ctx
        assert isinstance(ctx, str)

    def test_build_name_context_no_sancai(self):
        """姓名学上下文 - 无三才"""
        ctx = build_name_context({
            "surname": "李", "given_name": "四",
            "score": 80,
            "suggestions": ["建议1", "建议2"],
        })
        assert "李四" in ctx
        assert "80" in ctx
        assert "建议1" in ctx
        assert "建议2" in ctx

    def test_build_marriage_context_full(self):
        """合婚上下文 - 完整数据"""
        ctx = build_marriage_context({
            "name1": "张三", "name2": "李四",
            "nayin1": "路旁土", "nayin2": "海中金",
            "nayin_match": "土生金", "nayin_score": 90,
            "day_gan1": "辛", "day_gan2": "甲",
            "day_gan_relation": "甲木克辛金", "day_gan_score": 60,
            "branch_relation": "六合", "branch_score": 85,
            "wuxing_match": "良好", "wuxing_score": 75,
            "shengxiao_match": "匹配", "shengxiao_score": 80,
            "total_score": 78, "conclusion": "中等匹配",
        })
        assert "地支关系" in ctx
        assert "五行互补" in ctx
        assert "生肖匹配" in ctx
        assert "78" in ctx

    def test_build_marriage_context_minimal(self):
        """合婚上下文 - 最小数据"""
        ctx = build_marriage_context({"name1": "张三", "name2": "李四", "total_score": 50, "conclusion": "一般"})
        assert "张三" in ctx
        assert "李四" in ctx
        assert "50" in ctx

    def test_build_oracle_context_full(self):
        """Oracle 上下文 - 完整数据"""
        ctx = build_oracle_context({
            "mode": "TUIBEITU",
            "hexagram": "䷀",
            "hexagram_index": 1,
            "upper_trigram": "乾",
            "lower_trigram": "乾",
            "yao_lines": ["阳", "阳", "阳", "阳", "阳", "阳"],
            "judgment": "元亨利贞",
            "image": "天行健，君子以自强不息",
            "commentary": "此为乾卦",
            "gan_zhi": "甲子",
            "wuxing": "金",
        })
        assert "注释" in ctx
        assert "干支" in ctx
        assert "五行" in ctx
        assert "甲子" in ctx

    def test_build_oracle_context_minimal(self):
        """Oracle 上下文 - 最小数据"""
        ctx = build_oracle_context({"mode": "TUIBEITU", "hexagram": "䷀", "hexagram_index": 1, "upper_trigram": "乾", "lower_trigram": "乾"})
        assert "乾" in ctx
        assert isinstance(ctx, str)


# ════════════════════════════════════════
# 10. v2.5 对话记忆测试
# ════════════════════════════════════════

class TestConversationMemory:
    """对话记忆管理测试"""

    @pytest.fixture(autouse=True)
    def clear_memory(self):
        """每个测试前后清空全局对话记忆"""
        from tengod.ai_interpreter import _conversation_memory
        _conversation_memory.clear()
        yield
        _conversation_memory.clear()

    def test_init_conversation(self):
        """初始化会话"""
        from tengod.ai_interpreter import init_conversation, _conversation_memory
        init_conversation("sess_001")
        assert "sess_001" in _conversation_memory
        assert _conversation_memory["sess_001"] == []

    def test_add_to_conversation(self):
        """添加消息到对话"""
        from tengod.ai_interpreter import add_to_conversation, _conversation_memory
        add_to_conversation("sess_001", "user", "我的事业运如何？")
        assert "sess_001" in _conversation_memory
        assert len(_conversation_memory["sess_001"]) == 1
        assert _conversation_memory["sess_001"][0]["role"] == "user"
        assert "事业" in _conversation_memory["sess_001"][0]["content"]
        assert "timestamp" in _conversation_memory["sess_001"][0]

    def test_add_to_conversation_truncates_long(self):
        """长消息被截断"""
        from tengod.ai_interpreter import add_to_conversation, _conversation_memory
        long_msg = "A" * 1000
        add_to_conversation("sess_001", "user", long_msg)
        assert len(_conversation_memory["sess_001"][0]["content"]) <= 500

    def test_add_to_conversation_auto_init(self):
        """未初始化会话自动创建"""
        from tengod.ai_interpreter import add_to_conversation, _conversation_memory
        add_to_conversation("sess_new", "assistant", "好的，我来分析")
        assert "sess_new" in _conversation_memory

    def test_get_conversation_history(self):
        """获取对话历史"""
        from tengod.ai_interpreter import (
            add_to_conversation, get_conversation_history,
        )
        add_to_conversation("sess_001", "user", "第一个问题")
        add_to_conversation("sess_001", "assistant", "第一个回答")
        history = get_conversation_history("sess_001")
        assert "用户" in history
        assert "顾问" in history
        assert "第一个问题" in history

    def test_get_conversation_history_empty(self):
        """获取空会话历史"""
        from tengod.ai_interpreter import get_conversation_history
        history = get_conversation_history("nonexistent")
        assert history == ""

    def test_get_conversation_history_max_turns(self):
        """获取历史 - 限制轮数"""
        from tengod.ai_interpreter import (
            add_to_conversation, get_conversation_history,
        )
        for i in range(10):
            add_to_conversation("sess_001", "user", f"问题{i}")
            add_to_conversation("sess_001", "assistant", f"回答{i}")
        history = get_conversation_history("sess_001", max_turns=2)
        assert "问题8" in history or "问题9" in history
        assert "问题0" not in history

    def test_clear_conversation(self):
        """清除对话记忆"""
        from tengod.ai_interpreter import (
            add_to_conversation, clear_conversation, _conversation_memory,
        )
        add_to_conversation("sess_001", "user", "测试")
        clear_conversation("sess_001")
        assert "sess_001" not in _conversation_memory

    def test_clear_conversation_nonexistent(self):
        """清除不存在的会话"""
        from tengod.ai_interpreter import clear_conversation
        clear_conversation("nonexistent")


# ════════════════════════════════════════
# 11. v2.5 个性化建议测试
# ════════════════════════════════════════

class TestPersonalizedRecommendations:
    """个性化建议生成测试"""

    @pytest.fixture(autouse=True)
    def clear_memory(self):
        from tengod.ai_interpreter import _conversation_memory
        _conversation_memory.clear()
        yield
        _conversation_memory.clear()

    def test_generate_basic_recommendations(self):
        """基本建议生成"""
        from tengod.ai_interpreter import generate_personalized_recommendations
        recs = generate_personalized_recommendations(
            yongshen=["土", "金"],
            jishen=["火"],
            current_fortune="平",
            user_goal="综合",
        )
        assert isinstance(recs, list)
        assert len(recs) >= 2
        categories = [r["category"] for r in recs]
        assert "五行调补" in categories

    def test_generate_recommendations_good_fortune(self):
        """运势好时的建议"""
        from tengod.ai_interpreter import generate_personalized_recommendations
        recs = generate_personalized_recommendations(
            yongshen=["木"],
            jishen=["金"],
            current_fortune="大吉",
            user_goal="综合",
        )
        categories = [r["category"] for r in recs]
        assert "时机把握" in categories

    def test_generate_recommendations_bad_fortune(self):
        """运势差时的建议"""
        from tengod.ai_interpreter import generate_personalized_recommendations
        recs = generate_personalized_recommendations(
            yongshen=["水"],
            jishen=["土"],
            current_fortune="凶",
            user_goal="综合",
        )
        categories = [r["category"] for r in recs]
        assert "风险提示" in categories

    def test_generate_recommendations_very_bad_fortune(self):
        """大凶运势建议"""
        from tengod.ai_interpreter import generate_personalized_recommendations
        recs = generate_personalized_recommendations(
            yongshen=["金"],
            jishen=["火"],
            current_fortune="大凶",
            user_goal="综合",
        )
        categories = [r["category"] for r in recs]
        assert "风险提示" in categories

    def test_generate_recommendations_goal_career(self):
        """事业目标建议"""
        from tengod.ai_interpreter import generate_personalized_recommendations
        recs = generate_personalized_recommendations(
            yongshen=["土"],
            jishen=["水"],
            user_goal="事业",
        )
        categories = [r["category"] for r in recs]
        assert "事业发展" in categories

    def test_generate_recommendations_goal_wealth(self):
        """财运目标建议"""
        from tengod.ai_interpreter import generate_personalized_recommendations
        recs = generate_personalized_recommendations(
            yongshen=["金"],
            jishen=["木"],
            user_goal="财运",
        )
        categories = [r["category"] for r in recs]
        assert "财富管理" in categories

    def test_generate_recommendations_goal_relationships(self):
        """感情目标建议"""
        from tengod.ai_interpreter import generate_personalized_recommendations
        recs = generate_personalized_recommendations(
            yongshen=["水"],
            jishen=["火"],
            user_goal="感情",
        )
        categories = [r["category"] for r in recs]
        assert "感情经营" in categories

    def test_generate_recommendations_goal_health(self):
        """健康目标建议"""
        from tengod.ai_interpreter import generate_personalized_recommendations
        recs = generate_personalized_recommendations(
            yongshen=["木"],
            jishen=["土"],
            user_goal="健康",
        )
        categories = [r["category"] for r in recs]
        assert "健康养生" in categories

    def test_generate_recommendations_max_5(self):
        """建议不超过5条"""
        from tengod.ai_interpreter import generate_personalized_recommendations
        recs = generate_personalized_recommendations(
            yongshen=["土", "金", "水"],
            jishen=["火", "木"],
            current_fortune="吉",
            user_goal="事业",
        )
        assert len(recs) <= 5

    def test_generate_recommendations_unknown_wuxing(self):
        """未知五行不报错"""
        from tengod.ai_interpreter import generate_personalized_recommendations
        recs = generate_personalized_recommendations(
            yongshen=["XYZ"],
            jishen=["ABC"],
        )
        assert isinstance(recs, list)

    def test_generate_recommendations_empty(self):
        """空喜用神"""
        from tengod.ai_interpreter import generate_personalized_recommendations
        recs = generate_personalized_recommendations(
            yongshen=[],
            jishen=[],
        )
        assert isinstance(recs, list)

    def test_generate_recommendations_jishen_avoidance(self):
        """忌神规避建议"""
        from tengod.ai_interpreter import generate_personalized_recommendations
        recs = generate_personalized_recommendations(
            yongshen=["木"],
            jishen=["火"],
        )
        categories = [r["category"] for r in recs]
        assert "风险规避" in categories


# ════════════════════════════════════════
# 12. v2.5 上下文感知解读与对话测试
# ════════════════════════════════════════

class TestContextualInterpret:
    """上下文感知解读测试"""

    @pytest.fixture(autouse=True)
    def clear_memory(self):
        from tengod.ai_interpreter import _conversation_memory
        _conversation_memory.clear()
        yield
        _conversation_memory.clear()

    @pytest.mark.asyncio
    async def test_interpret_bazi_contextual(self):
        """上下文感知八字解读"""
        from tengod.ai_interpreter import interpret_bazi_contextual
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
        )
        result = await interpret_bazi_contextual(
            ctx, session_id="sess_001", user_goal="事业", question="我的事业如何？"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_bazi_contextual_no_session(self):
        """上下文感知 - 无会话ID"""
        from tengod.ai_interpreter import interpret_bazi_contextual
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
        )
        result = await interpret_bazi_contextual(ctx, session_id="", user_goal="")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_bazi_contextual_with_history(self):
        """上下文感知 - 有对话历史"""
        from tengod.ai_interpreter import (
            interpret_bazi_contextual, add_to_conversation,
        )
        add_to_conversation("sess_002", "user", "我最近总失眠")
        add_to_conversation("sess_002", "assistant", "需要关注水元素的平衡")
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
        )
        result = await interpret_bazi_contextual(
            ctx, session_id="sess_002", question="那我该怎么办？"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_chat_with_memory(self):
        """带记忆的命理对话"""
        from tengod.ai_interpreter import chat_with_memory, add_to_conversation
        add_to_conversation("sess_003", "user", "我的财运如何？")
        add_to_conversation("sess_003", "assistant", "您的财运整体向好")
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
        )
        result = await chat_with_memory(ctx, "那投资方向呢？", "sess_003")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_chat_with_memory_new_session(self):
        """带记忆对话 - 新会话"""
        from tengod.ai_interpreter import chat_with_memory
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
        )
        result = await chat_with_memory(ctx, "帮我分析一下八字", "sess_new")
        assert isinstance(result, str)
        assert len(result) > 0


# ════════════════════════════════════════
# 13. v2.9 IntentTracker 测试
# ════════════════════════════════════════

class TestIntentTracker:
    """意图追踪器测试"""

    def test_init(self):
        """初始化"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        assert tracker._current_topic == ""
        assert tracker._topic_depth == 0
        assert tracker._conversation_state == "greeting"
        assert tracker._history == []

    def test_track_basic(self):
        """基本意图追踪"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        result = tracker.track("我想了解一下我的事业发展方向")
        assert result["primary_topic"] == "事业"
        assert result["topic_depth"] == 1
        assert result["state"] in ["follow_up", "exploring"]
        assert "timestamp" in result

    def test_track_wealth(self):
        """财运话题"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        result = tracker.track("我最近投资亏了很多钱")
        assert result["primary_topic"] == "财运"

    def test_track_relationships(self):
        """感情话题"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        result = tracker.track("我的婚姻状况如何？")
        assert result["primary_topic"] == "感情"

    def test_track_health(self):
        """健康话题"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        result = tracker.track("我最近身体不好，经常失眠")
        assert result["primary_topic"] == "健康"

    def test_track_family(self):
        """家庭话题"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        result = tracker.track("我的孩子教育问题应该怎么处理")
        assert result["primary_topic"] == "家庭"

    def test_track_study(self):
        """学业话题"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        result = tracker.track("我考研能成功吗？")
        assert result["primary_topic"] == "学业"

    def test_track_multiple_topics(self):
        """多话题消息"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        result = tracker.track("我的事业和财运如何？")
        assert "事业" in result["topics"]
        assert "财运" in result["topics"]

    def test_track_default_topic(self):
        """默认话题（无法匹配）"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        result = tracker.track("你好")
        assert result["primary_topic"] == "综合"

    def test_track_topic_depth(self):
        """话题深度追踪"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        tracker.track("我的事业怎么样呢？")  # 事业, depth 1
        result = tracker.track("那具体是什么行业比较好？")  # 事业, depth 2
        assert result["topic_depth"] == 2
        assert result["topic_changed"] is False
        result = tracker.track("我的事业前景如何看呢？")  # 事业, depth 3
        assert result["topic_depth"] == 3

    def test_track_topic_switch(self):
        """话题切换检测"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        tracker.track("我的事业怎么样？")
        result = tracker.track("那我的婚姻呢？")
        assert result["topic_changed"] is True
        assert result["topic_depth"] == 1

    def test_track_state_summary(self):
        """总结状态"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        result = tracker.track("帮我总结一下")
        assert result["state"] == "summary"

    def test_track_state_deep_analysis(self):
        """深度分析状态"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        result = tracker.track("为什么我的财运一直不好？")
        assert result["state"] == "deep_analysis"

    def test_track_state_deep_by_depth(self):
        """深度分析状态 - 通过深度触发"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        tracker.track("我的事业怎么样呢？")  # 事业, depth 1
        tracker.track("那具体什么行业比较好？")  # 事业, depth 2
        result = tracker.track("我的事业前景如何看呢？")  # 事业, depth 3
        assert result["state"] == "deep_analysis"

    def test_track_state_greeting(self):
        """问候状态"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        result = tracker.track("你好")
        assert result["state"] == "greeting"

    def test_get_context(self):
        """获取对话上下文"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        tracker.track("我的事业怎么样？")
        tracker.track("那财运呢？")
        ctx = tracker.get_context()
        assert "current_topic" in ctx
        assert "topic_depth" in ctx
        assert "state" in ctx
        assert "total_turns" in ctx
        assert ctx["total_turns"] == 2
        assert "recent_topics" in ctx

    def test_reset(self):
        """重置追踪器"""
        from tengod.ai_interpreter import IntentTracker
        tracker = IntentTracker()
        tracker.track("我的事业怎么样？")
        tracker.reset()
        assert tracker._current_topic == ""
        assert tracker._topic_depth == 0
        assert tracker._conversation_state == "greeting"
        assert tracker._history == []


# ════════════════════════════════════════
# 14. v2.9 ProactiveAdvisor 测试
# ════════════════════════════════════════

class TestProactiveAdvisor:
    """主动建议生成器测试"""

    def test_init(self):
        """初始化"""
        from tengod.ai_interpreter import ProactiveAdvisor
        advisor = ProactiveAdvisor()
        assert advisor._suggested == set()

    def test_generate_suggestions_basic(self):
        """基本建议生成"""
        from tengod.ai_interpreter import ProactiveAdvisor
        advisor = ProactiveAdvisor()
        suggestions = advisor.generate_suggestions({
            "current_topic": "事业",
            "topic_depth": 1,
            "state": "follow_up",
        })
        assert isinstance(suggestions, list)
        assert len(suggestions) >= 1
        assert "question" in suggestions[0]
        assert "context" in suggestions[0]
        assert "reason" in suggestions[0]
        assert "type" in suggestions[0]

    def test_generate_suggestions_deep_analysis(self):
        """深度分析触发建议"""
        from tengod.ai_interpreter import ProactiveAdvisor
        advisor = ProactiveAdvisor()
        suggestions = advisor.generate_suggestions({
            "current_topic": "事业",
            "topic_depth": 3,
            "state": "deep_analysis",
        })
        assert len(suggestions) >= 1
        types = [s["type"] for s in suggestions]
        assert "depth_trigger" in types

    def test_generate_suggestions_summary(self):
        """总结状态建议"""
        from tengod.ai_interpreter import ProactiveAdvisor
        advisor = ProactiveAdvisor()
        suggestions = advisor.generate_suggestions({
            "current_topic": "命理",
            "topic_depth": 1,
            "state": "summary",
        })
        types = [s["type"] for s in suggestions]
        assert "state_trigger" in types

    def test_generate_suggestions_no_duplicate(self):
        """不重复建议"""
        from tengod.ai_interpreter import ProactiveAdvisor
        advisor = ProactiveAdvisor()
        s1 = advisor.generate_suggestions({
            "current_topic": "事业",
            "topic_depth": 1,
            "state": "follow_up",
        })
        s2 = advisor.generate_suggestions({
            "current_topic": "事业",
            "topic_depth": 1,
            "state": "follow_up",
        })
        q1 = {s["question"] for s in s1}
        q2 = {s["question"] for s in s2}
        assert len(q1 & q2) == 0 or len(s2) == 0

    def test_generate_suggestions_max(self):
        """限制建议数量"""
        from tengod.ai_interpreter import ProactiveAdvisor
        advisor = ProactiveAdvisor()
        suggestions = advisor.generate_suggestions(
            {"current_topic": "事业", "topic_depth": 1, "state": "follow_up"},
            max_suggestions=1,
        )
        assert len(suggestions) <= 1

    def test_generate_suggestions_unknown_topic(self):
        """未知话题 - 使用综合建议"""
        from tengod.ai_interpreter import ProactiveAdvisor
        advisor = ProactiveAdvisor()
        suggestions = advisor.generate_suggestions({
            "current_topic": "未知",
            "topic_depth": 1,
            "state": "follow_up",
        })
        assert isinstance(suggestions, list)

    def test_reset(self):
        """重置建议记录"""
        from tengod.ai_interpreter import ProactiveAdvisor
        advisor = ProactiveAdvisor()
        advisor.generate_suggestions({
            "current_topic": "事业",
            "topic_depth": 1,
            "state": "follow_up",
        })
        advisor.reset()
        assert advisor._suggested == set()


# ════════════════════════════════════════
# 15. v2.9 ConversationEngine 测试
# ════════════════════════════════════════

class TestConversationEngine:
    """智能对话引擎测试"""

    @pytest.fixture(autouse=True)
    def clear_memory(self):
        from tengod.ai_interpreter import _conversation_memory, _conversation_engine
        _conversation_memory.clear()
        import tengod.ai_interpreter as mod
        mod._conversation_engine = None
        yield
        _conversation_memory.clear()
        mod._conversation_engine = None

    def test_init(self):
        """初始化"""
        from tengod.ai_interpreter import ConversationEngine
        engine = ConversationEngine()
        assert engine._tracker is not None
        assert engine._advisor is not None
        assert engine._sessions == {}

    def test_process_message(self):
        """处理用户消息"""
        from tengod.ai_interpreter import ConversationEngine
        engine = ConversationEngine()
        result = engine.process_message("我的事业运如何？", "sess_001")
        assert result["session_id"] == "sess_001"
        assert result["intent"]["primary_topic"] == "事业"
        assert isinstance(result["suggestions"], list)
        assert "conversation_state" in result
        assert "session_stats" in result
        assert result["session_stats"]["message_count"] == 1

    def test_process_message_multi_turn(self):
        """多轮对话"""
        from tengod.ai_interpreter import ConversationEngine
        engine = ConversationEngine()
        engine.process_message("我的事业运如何？", "sess_001")
        result = engine.process_message("那财运呢？", "sess_001")
        assert result["session_stats"]["message_count"] == 2
        assert "事业" in result["session_stats"]["topics_covered"]
        assert "财运" in result["session_stats"]["topics_covered"]

    def test_process_message_no_bazi_context(self):
        """无八字上下文"""
        from tengod.ai_interpreter import ConversationEngine
        engine = ConversationEngine()
        result = engine.process_message("你好", "sess_001")
        assert result["session_id"] == "sess_001"

    @pytest.mark.asyncio
    async def test_chat(self):
        """自主对话"""
        from tengod.ai_interpreter import ConversationEngine
        engine = ConversationEngine()
        result = await engine.chat("我的事业运如何？", "sess_001")
        assert "response" in result
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0
        assert "response_length" in result
        assert "intent" in result
        assert "suggestions" in result

    @pytest.mark.asyncio
    async def test_chat_multi_turn(self):
        """多轮自主对话"""
        from tengod.ai_interpreter import ConversationEngine
        engine = ConversationEngine()
        await engine.chat("我的事业运如何？", "sess_001")
        result = await engine.chat("那具体什么行业好？", "sess_001")
        assert result["session_stats"]["message_count"] == 2

    @pytest.mark.asyncio
    async def test_chat_deep_topic(self):
        """深度话题自主对话 - 触发意图上下文注入"""
        from tengod.ai_interpreter import ConversationEngine
        engine = ConversationEngine()
        await engine.chat("我的事业运如何？", "sess_deep")
        await engine.chat("那具体什么行业比较好？", "sess_deep")
        result = await engine.chat("我想再深入了解一下事业前景", "sess_deep")
        assert "response" in result
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0

    def test_get_session_summary(self):
        """获取会话摘要"""
        from tengod.ai_interpreter import ConversationEngine
        engine = ConversationEngine()
        engine.process_message("我的事业运如何？", "sess_001")
        summary = engine.get_session_summary("sess_001")
        assert summary["session_id"] == "sess_001"
        assert summary["message_count"] == 1
        assert "topics_covered" in summary
        assert "conversation_history" in summary
        assert "intent_context" in summary

    def test_get_session_summary_nonexistent(self):
        """获取不存在会话摘要"""
        from tengod.ai_interpreter import ConversationEngine
        engine = ConversationEngine()
        summary = engine.get_session_summary("nonexistent")
        assert summary["session_id"] == "nonexistent"
        assert summary["message_count"] == 0

    def test_reset_session(self):
        """重置会话"""
        from tengod.ai_interpreter import ConversationEngine, _conversation_memory
        engine = ConversationEngine()
        engine.process_message("你好", "sess_001")
        engine.reset_session("sess_001")
        assert "sess_001" not in engine._sessions

    def test_load_session_from_db_not_persistent(self):
        """数据库未持久化时返回 None"""
        from tengod.ai_interpreter import ConversationEngine
        engine = ConversationEngine()
        result = engine.load_session_from_db("sess_001")
        assert result is None

    def test_get_conversation_engine_singleton(self):
        """全局对话引擎单例"""
        from tengod.ai_interpreter import get_conversation_engine, _conversation_engine
        import tengod.ai_interpreter as mod
        mod._conversation_engine = None
        engine1 = get_conversation_engine()
        engine2 = get_conversation_engine()
        assert engine1 is engine2

    @pytest.mark.asyncio
    async def test_smart_chat(self):
        """智能对话入口"""
        from tengod.ai_interpreter import smart_chat, _conversation_engine
        import tengod.ai_interpreter as mod
        mod._conversation_engine = None
        result = await smart_chat("我的事业运如何？", "sess_001")
        assert "response" in result
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0


# ════════════════════════════════════════
# 16. _to_dict 边缘情况测试
# ════════════════════════════════════════

class TestToDictEdgeCases:
    """_to_dict 边缘情况"""

    def test_to_dict_tuple(self):
        result = _to_dict((1, 2, 3))
        assert result == [1, 2, 3]

    def test_to_dict_nested_dict(self):
        result = _to_dict({"a": {"b": {"c": 1}}})
        assert result == {"a": {"b": {"c": 1}}}

    def test_to_dict_object_with_dict(self):
        class Obj:
            def __init__(self):
                self.name = "test"
                self.value = 42
                self._private = "hidden"
        result = _to_dict(Obj())
        assert result == {"name": "test", "value": 42}
        assert "_private" not in result

    def test_to_dict_nested_object(self):
        class Inner:
            def __init__(self):
                self.x = 10
        class Outer:
            def __init__(self):
                self.inner = Inner()
                self.label = "outer"
        result = _to_dict(Outer())
        assert result == {"inner": {"x": 10}, "label": "outer"}

    def test_to_dict_mixed_list(self):
        class Obj:
            def __init__(self):
                self.x = 1
        result = _to_dict([Obj(), 42, "hello"])
        assert result == [{"x": 1}, 42, "hello"]

    def test_to_dict_empty_list(self):
        assert _to_dict([]) == []

    def test_to_dict_empty_dict(self):
        assert _to_dict({}) == {}


# ════════════════════════════════════════
# 17. 常量与配置测试
# ════════════════════════════════════════

class TestConstants:
    """模块常量测试"""

    def test_conversation_states(self):
        from tengod.ai_interpreter import CONVERSATION_STATES
        assert "greeting" in CONVERSATION_STATES
        assert "deep_analysis" in CONVERSATION_STATES
        assert "follow_up" in CONVERSATION_STATES
        assert "summary" in CONVERSATION_STATES
        assert "idle" in CONVERSATION_STATES

    def test_topic_keywords(self):
        from tengod.ai_interpreter import TOPIC_KEYWORDS
        assert "事业" in TOPIC_KEYWORDS
        assert "财运" in TOPIC_KEYWORDS
        assert "感情" in TOPIC_KEYWORDS
        assert "健康" in TOPIC_KEYWORDS
        assert "命理" in TOPIC_KEYWORDS
        assert "紫微" in TOPIC_KEYWORDS
        assert "占卜" in TOPIC_KEYWORDS

    def test_proactive_suggestions(self):
        from tengod.ai_interpreter import PROACTIVE_SUGGESTIONS
        assert "事业" in PROACTIVE_SUGGESTIONS
        assert "财运" in PROACTIVE_SUGGESTIONS
        assert "感情" in PROACTIVE_SUGGESTIONS
        assert "综合" in PROACTIVE_SUGGESTIONS
        assert len(PROACTIVE_SUGGESTIONS["事业"]) >= 1

    def test_context_aware_prompt(self):
        from tengod.ai_interpreter import CONTEXT_AWARE_PROMPT
        assert "命理" in CONTEXT_AWARE_PROMPT
        assert "上下文" in CONTEXT_AWARE_PROMPT

    def test_personalized_recommendation_prompt(self):
        from tengod.ai_interpreter import PERSONALIZED_RECOMMENDATION_PROMPT
        assert "五行喜忌" in PERSONALIZED_RECOMMENDATION_PROMPT
        assert "建议" in PERSONALIZED_RECOMMENDATION_PROMPT


# ════════════════════════════════════════
# 18. 解读函数边缘情况测试
# ════════════════════════════════════════

class TestInterpretEdgeCases:
    """解读函数边缘情况"""

    @pytest.mark.asyncio
    async def test_interpret_liuyao_no_question(self):
        """六爻解读 - 无问题"""
        ctx = build_liuyao_context({"ben_gua_name": "乾为天", "shang_gua": "乾", "xia_gua": "乾"})
        result = await interpret_liuyao(ctx)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_oracle_no_question(self):
        """Oracle 解读 - 无问题"""
        ctx = build_oracle_context({"hexagram": "䷀", "upper_trigram": "乾", "lower_trigram": "乾", "hexagram_index": 1})
        result = await interpret_oracle(ctx)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_bazi_with_rag(self):
        """八字解读 + RAG"""
        ctx = build_bazi_context(
            pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
            day_master="辛金",
        )
        result = await interpret_bazi(ctx, use_rag=True)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_ziwei_with_question(self):
        """紫微解读 - 带问题"""
        ctx = build_ziwei_context({"gender": "male", "ming_gong": {"gong_name": "命宫"}})
        result = await interpret_ziwei(ctx, question="我的运势如何？")
        assert isinstance(result, str)
        assert len(result) > 0


# ════════════════════════════════════════
# 19. interpret_bazi_from_analysis 边缘情况测试
# ════════════════════════════════════════

class TestInterpretBaziFromAnalysisEdgeCases:
    """interpret_bazi_from_analysis 边缘情况"""

    @pytest.mark.asyncio
    async def test_interpret_from_analysis_female(self):
        """女性八字解读"""
        from tengod.bazi_analyzer import BaziAnalyzer
        analyzer = BaziAnalyzer(1990, 6, 15, 10, 30, is_male=False)
        result = await interpret_bazi_from_analysis(
            analysis=analyzer.analysis,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_from_analysis_no_comprehensive_no_shensha(self):
        """无综合结果和无神煞"""
        from tengod.bazi_analyzer import BaziAnalyzer
        analyzer = BaziAnalyzer(1990, 6, 15, 10, 30, is_male=True)
        result = await interpret_bazi_from_analysis(
            analysis=analyzer.analysis,
            shensha_result=None,
            comprehensive_result=None,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_interpret_from_analysis_with_question(self):
        """带问题的解读"""
        from tengod.bazi_analyzer import BaziAnalyzer
        analyzer = BaziAnalyzer(1990, 6, 15, 10, 30, is_male=True)
        result = await interpret_bazi_from_analysis(
            analysis=analyzer.analysis,
            question="我的感情运如何？",
        )
        assert isinstance(result, str)
        assert len(result) > 0
