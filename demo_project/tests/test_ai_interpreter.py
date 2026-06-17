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
        data = r.json()
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
        data = r.json()
        assert "interpretation" in data

    def test_liuyao_interpret(self):
        """六爻 AI 解读"""
        r = client.post("/api/ai/interpret/liuyao",
                       params={"question": "事业发展"},
                       headers=get_auth_headers())
        assert r.status_code == 200
        data = r.json()
        assert "interpretation" in data
        assert "gua_name" in data

    def test_name_interpret(self):
        """姓名学 AI 解读"""
        r = client.post("/api/ai/interpret/name",
                       params={"surname": "张", "given_name": "伟"},
                       headers=get_auth_headers())
        assert r.status_code == 200
        data = r.json()
        assert "interpretation" in data
        assert "score" in data

    def test_oracle_interpret(self):
        """Oracle AI 解读"""
        r = client.post("/api/ai/interpret/oracle",
                       params={"question": "事业发展", "mode": "tuibeitu"},
                       headers=get_auth_headers())
        assert r.status_code == 200
        data = r.json()
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
        data = r.json()
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
