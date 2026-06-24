"""
命理智能分析引擎 v2.1
====================
中华文明数字永生体 · AI深度分析

功能：
- 命盘自动解读生成
- 流年运势预测分析
- 合婚匹配智能建议
- 事业财运趋势分析
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .deepseek_adapter import (
    DeepseekClient,
    DeepseekConfig,
    Message,
    get_client
)


@dataclass
class AnalysisResult:
    """分析结果"""
    title: str
    content: str
    score: float = 0.0
    tags: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class BaziInterpreter:
    """八字命盘解读器"""

    def __init__(self, client: Optional[DeepseekClient] = None):
        self.client = client or get_client()

    async def interpret(
        self,
        bazi_data: Dict[str, Any],
        focus: str = "综合"
    ) -> AnalysisResult:
        """
        解读八字命盘

        Args:
            bazi_data: 八字数据
            focus: 分析重点（综合/事业/财运/婚姻/健康）

        Returns:
            AnalysisResult: 解读结果
        """
        # 构建分析提示词
        prompt = self._build_prompt(bazi_data, focus)

        # 调用AI分析
        messages = [Message(role="user", content=prompt)]
        response = await self.client.chat(messages)

        # 解析结果
        return self._parse_response(response.content, focus)

    def _build_prompt(self, data: Dict[str, Any], focus: str) -> str:
        """构建分析提示词"""
        pillars = data.get("pillars", {})
        wuxing = data.get("wuxing", {})
        geju = data.get("geju", "")
        shensha = data.get("shensha", [])

        prompt = f"""请分析以下八字命盘，重点分析{focus}方面：

【四柱信息】
年柱：{pillars.get('year', '未知')}
月柱：{pillars.get('month', '未知')}
日柱：{pillars.get('day', '未知')}
时柱：{pillars.get('hour', '未知')}

【五行分布】
木：{wuxing.get('木', 0)}  火：{wuxing.get('火', 0)}
土：{wuxing.get('土', 0)}  金：{wuxing.get('金', 0)}
水：{wuxing.get('水', 0)}

【格局】
{geju}

【神煞】
{', '.join(shensha) if shensha else '无特殊神煞'}

请提供：
1. 命盘整体评价（100字以内）
2. {focus}方面详细分析（200字以内）
3. 具体建议（3条）
"""
        return prompt

    def _parse_response(self, content: str, focus: str) -> AnalysisResult:
        """解析AI响应"""
        # 简化解析，直接返回内容
        lines = content.split("\n")
        recommendations = []
        for line in lines:
            if "建议" in line or "推荐" in line:
                recommendations.append(line.strip())

        return AnalysisResult(
            title=f"{focus}分析",
            content=content,
            score=75.0,
            tags=[focus, "八字", "命理"],
            recommendations=recommendations[:3]
        )


class LiunianAnalyzer:
    """流年运势分析器"""

    async def analyze_year(
        self,
        bazi_data: Dict[str, Any],
        year: int
    ) -> AnalysisResult:
        """
        分析流年运势

        Args:
            bazi_data: 八字数据
            year: 分析年份

        Returns:
            AnalysisResult: 分析结果
        """
        prompt = f"""请分析以下八字命盘在{year}年的运势：

年柱：{bazi_data.get('pillars', {}).get('year', '')}
日柱：{bazi_data.get('pillars', {}).get('day', '')}

请分析：
1. 整体运势评分（1-100）
2. 事业运势
3. 财运
4. 健康
5. 人际关系
6. 关键月份提醒
"""
        messages = [Message(role="user", content=prompt)]
        response = await get_client().chat(messages)

        return AnalysisResult(
            title=f"{year}年运势分析",
            content=response.content,
            score=80.0,
            tags=["流年", "运势", str(year)]
        )


class MarriageAnalyzer:
    """合婚分析器"""

    async def analyze_compatibility(
        self,
        male_bazi: Dict[str, Any],
        female_bazi: Dict[str, Any]
    ) -> AnalysisResult:
        """
        分析合婚匹配度

        Args:
            male_bazi: 男方八字
            female_bazi: 女方八字

        Returns:
            AnalysisResult: 分析结果
        """
        prompt = f"""请分析以下两人的合婚匹配度：

【男方】
年柱：{male_bazi.get('pillars', {}).get('year', '')}
日柱：{male_bazi.get('pillars', {}).get('day', '')}

【女方】
年柱：{female_bazi.get('pillars', {}).get('year', '')}
日柱：{female_bazi.get('pillars', {}).get('day', '')}

请分析：
1. 匹配度评分（1-100）
2. 性格互补性
3. 感情运势
4. 婚姻建议
5. 注意事项
"""
        messages = [Message(role="user", content=prompt)]
        response = await get_client().chat(messages)

        return AnalysisResult(
            title="合婚分析",
            content=response.content,
            score=85.0,
            tags=["合婚", "婚姻", "匹配"]
        )


class CareerAnalyzer:
    """事业财运分析器"""

    async def analyze_career(
        self,
        bazi_data: Dict[str, Any],
        current_age: int
    ) -> AnalysisResult:
        """
        分析事业财运

        Args:
            bazi_data: 八字数据
            current_age: 当前年龄

        Returns:
            AnalysisResult: 分析结果
        """
        prompt = f"""请分析以下八字的事业财运：

日柱：{bazi_data.get('pillars', {}).get('day', '')}
格局：{bazi_data.get('geju', '')}
当前年龄：{current_age}岁

请分析：
1. 事业方向建议
2. 财运趋势
3. 关键年龄段
4. 投资建议
5. 职业发展建议
"""
        messages = [Message(role="user", content=prompt)]
        response = await get_client().chat(messages)

        return AnalysisResult(
            title="事业财运分析",
            content=response.content,
            score=78.0,
            tags=["事业", "财运", "发展"]
        )


# ── 综合分析引擎 ──────────────────────────────────────────────────────────
class IntelligentAnalysisEngine:
    """智能分析引擎"""

    def __init__(self):
        self.bazi_interpreter = BaziInterpreter()
        self.liunian_analyzer = LiunianAnalyzer()
        self.marriage_analyzer = MarriageAnalyzer()
        self.career_analyzer = CareerAnalyzer()

    async def full_analysis(
        self,
        bazi_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, AnalysisResult]:
        """
        全方位分析

        Args:
            bazi_data: 八字数据
            options: 分析选项

        Returns:
            Dict: 各维度分析结果
        """
        results = {}

        # 基础解读
        results["基础"] = await self.bazi_interpreter.interpret(bazi_data, "综合")

        # 事业分析
        if options and options.get("career"):
            results["事业"] = await self.career_analyzer.analyze_career(
                bazi_data, options.get("age", 30)
            )

        # 流年分析
        if options and options.get("year"):
            results["流年"] = await self.liunian_analyzer.analyze_year(
                bazi_data, options["year"]
            )

        return results

    async def quick_analysis(self, bazi_data: Dict[str, Any]) -> str:
        """
        快速分析（简化版）

        Args:
            bazi_data: 八字数据

        Returns:
            str: 分析摘要
        """
        pillars = bazi_data.get("pillars", {})
        prompt = f"""请用50字概括以下命盘特点：
年柱：{pillars.get('year', '')}
日柱：{pillars.get('day', '')}
"""
        messages = [Message(role="user", content=prompt)]
        response = await get_client().chat(messages)
        return response.content


# ── 便捷函数 ──────────────────────────────────────────────────────────────
_engine: Optional[IntelligentAnalysisEngine] = None


def get_engine() -> IntelligentAnalysisEngine:
    """获取分析引擎"""
    global _engine
    if _engine is None:
        _engine = IntelligentAnalysisEngine()
    return _engine


async def analyze_bazi(bazi_data: Dict[str, Any]) -> AnalysisResult:
    """快速八字分析"""
    engine = get_engine()
    return await engine.bazi_interpreter.interpret(bazi_data)


async def analyze_year(bazi_data: Dict[str, Any], year: int) -> AnalysisResult:
    """流年分析"""
    engine = get_engine()
    return await engine.liunian_analyzer.analyze_year(bazi_data, year)


__all__ = [
    "BaziInterpreter",
    "LiunianAnalyzer",
    "MarriageAnalyzer",
    "CareerAnalyzer",
    "IntelligentAnalysisEngine",
    "AnalysisResult",
    "get_engine",
    "analyze_bazi",
    "analyze_year",
]