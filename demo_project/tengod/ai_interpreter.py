#!/usr/bin/env python3
"""
ai_interpreter.py — 阶段十七 · AI 智能解读服务 v1.0.0

统一各术数引擎的结构化数据 → LLM Prompt 转换与解读生成。

核心能力：
  - 八字深度解读（四柱+神煞+格局+喜用神+调候+大运）
  - 紫微斗数 AI 解读
  - 六爻 AI 解读
  - 姓名学 AI 解读
  - 合婚 AI 解读
  - Oracle 推背图 AI 深度解读
  - 流式输出支持

设计原则：
  - 复用 llm_adapter.py 的 BaseLLMAdapter（OpenAI/Mock）
  - 各术数专用 Prompt 模板，结构化上下文注入
  - Mock 模式下生成有意义的模板化解读（无需 API Key）

用法：
  >>> from tengod.ai_interpreter import interpret_bazi, interpret_ziwei
  >>> report = await interpret_bazi(bazi_data_dict)
  >>> ziwei_report = await interpret_ziwei(ziwei_dict)
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

from .llm_adapter import (
    BaseLLMAdapter,
    ChatMessage,
    get_llm,
)

# ============================================================================
# 术数专用 System Prompt 模板
# ============================================================================

BAZI_INTERPRET_PROMPT = """你是一位精通八字命理的资深专家，拥有深厚的传统命理学功底。

你将收到一份完整的八字排盘数据，包含：四柱、日主、五行分布、十神、神煞、格局、喜用神、调候、大运流年、地支关系。

请生成一份专业、有深度、易懂的八字命理分析报告，要求：
1. 使用流畅自然的中文，专业术语需附简要解释
2. 按以下结构组织：
   - 命局总论：日主强弱、格局层次、命局特点
   - 四柱逐柱分析：年柱（祖业）、月柱（父母）、日柱（自身配偶）、时柱（子女事业）
   - 五行与十神：五行旺衰、十神分布特点
   - 神煞分析：主要吉神与凶神的影响
   - 格局与喜用神：格局层次、喜用神方向、忌神提醒
   - 调候分析：季节调候需求
   - 大运流年：近期大运走势、关键流年提示
   - 综合建议：事业、财运、感情、健康方向（命理仅供参考）
3. 保持客观中肯，强调"命理分析仅供参考，人生在自己手中"
4. 总字数控制在 800-1200 字"""

ZIWEI_INTERPRET_PROMPT = """你是一位精通紫微斗数的命理专家。

你将收到一份紫微斗数命盘数据，包含：命宫、身宫、十二宫位、主星、辅星、四化等。

请生成一份紫微斗数命理分析报告，要求：
1. 使用流畅中文，术语附简要解释
2. 按以下结构：
   - 命宫总论：命宫主星格局、命格层次
   - 三方四正：命宫、财帛、事业、迁移的整体格局
   - 六亲宫位：父母、兄弟、夫妻、子女、交友
   - 财帛事业：财运与事业方向
   - 健康疾厄：体质与健康提醒
   - 大限流年：当前大限走势
   - 综合建议
3. 强调"命理仅供参考"
4. 总字数 600-1000 字"""

LIUYAO_INTERPRET_PROMPT = """你是一位精通六爻占卜的易学专家。

你将收到一份六爻卦象数据，包含：本卦、变卦、互卦、六亲、六神、世应、日辰等。

请生成一份六爻占卜分析报告，要求：
1. 使用流畅中文
2. 按以下结构：
   - 卦象总论：本卦卦义、变卦趋势
   - 用神分析：所占之事的用神及其旺衰
   - 六亲动爻：动爻变化及其吉凶
   - 世应关系：世应生克、彼此关系
   - 综合断语：所占之事的吉凶趋势与建议
3. 强调"占卜结果仅供参考，决策在自己"
4. 总字数 400-800 字"""

NAME_INTERPRET_PROMPT = """你是一位精通姓名学的专家，擅长五格剖象法与三才五行分析。

你将收到一份姓名学分析数据，包含：五格（天格、人格、地格、外格、总格）、三才、评分、建议。

请生成一份姓名学分析报告，要求：
1. 使用流畅中文
2. 按以下结构：
   - 姓名总论：整体评分与格局
   - 五格分析：各格数理吉凶
   - 三才配置：天人地三才五行关系
   - 性格倾向：姓名反映的性格特质
   - 事业财运：姓名对事业财运的影响
   - 健康提醒：三才配置对应的健康注意
   - 综合建议
3. 强调"姓名分析仅供参考"
4. 总字数 400-700 字"""

MARRIAGE_INTERPRET_PROMPT = """你是一位精通传统合婚的命理专家。

你将收到一份合婚分析数据，包含：双方八字、纳音匹配、日干关系、地支关系、五行互补、生肖匹配、综合评分。

请生成一份合婚分析报告，要求：
1. 使用流畅中文
2. 按以下结构：
   - 合婚总论：整体匹配度与缘分层次
   - 纳音匹配：年柱纳音五行关系
   - 日干关系：夫妻宫日干生克
   - 五行互补：双方五行是否互补
   - 生肖地支：生肖与地支合冲
   - 综合建议：相处之道与注意事项
3. 强调"合婚分析仅供参考，感情需双方经营"
4. 总字数 500-800 字"""

ORACLE_INTERPRET_PROMPT = """你是一位精通推背图与易经的预言解读专家。

你将收到一份推背图/周易卦象数据，包含：卦象、卦辞、上下卦、爻辞等。

请生成一份深度的卦象解读，要求：
1. 使用流畅中文，古文需附白话翻译
2. 按以下结构：
   - 卦象总论：本卦卦义与象征
   - 卦辞解读：卦辞原文与白话释义
   - 上下卦分析：上下卦体关系
   - 时机判断：当前所处时位
   - 行动建议：宜行之事与当避之事
   - 智慧启示：从卦象中可获得的智慧
3. 强调"卦象解读仅供参考，智者知机达变"
4. 总字数 500-800 字"""


# ============================================================================
# 结构化数据 → 文本上下文转换器
# ============================================================================

def _to_dict(obj: Any) -> Any:
    """将 dataclass/对象转为可序列化字典"""
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if hasattr(obj, "__dict__"):
        return {k: _to_dict(v) for k, v in vars(obj).items() if not k.startswith("_")}
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(x) for x in obj]
    return obj


def build_bazi_context(
    pillars: Dict[str, str],
    day_master: str = "",
    gender: str = "",
    wuxing: Optional[Dict] = None,
    shigan_map: Optional[Dict] = None,
    shensha: Optional[Dict] = None,
    geju: Optional[Dict] = None,
    yongshen: Optional[Dict] = None,
    tiaohou: Optional[Dict] = None,
    dayuns: Optional[List] = None,
    branch_relations: Optional[Dict] = None,
    extra: Optional[Dict] = None,
) -> str:
    """将八字结构化数据转为 LLM 可读的上下文文本"""
    lines = ["【八字排盘数据】"]

    # 基本信息
    lines.append(f"性别：{gender or '未指定'}")
    lines.append(f"日主：{day_master or '未知'}")
    lines.append(f"四柱：{pillars.get('year', '')} {pillars.get('month', '')} "
                 f"{pillars.get('day', '')} {pillars.get('hour', '')}")

    # 五行
    if wuxing:
        wx_str = "、".join(f"{k}{v}个" for k, v in wuxing.items())
        lines.append(f"五行分布：{wx_str}")

    # 十神
    if shigan_map:
        sg_str = "、".join(f"{k}={v}" for k, v in shigan_map.items())
        lines.append(f"十神（天干）：{sg_str}")

    # 神煞
    if shensha:
        lines.append("【神煞】")
        for pillar_name in ["year", "month", "day", "hour"]:
            pillar_shens = shensha.get(f"{pillar_name}_shens", {})
            if pillar_shens:
                pillar_label = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}[pillar_name]
                shen_str = "、".join(f"{name}({info.get('category', '')})"
                                     for name, info in pillar_shens.items())
                lines.append(f"  {pillar_label}：{shen_str}")

    # 格局
    if geju:
        lines.append("【格局】")
        lines.append(f"  格局名称：{geju.get('geju_name', '')}")
        lines.append(f"  格局类型：{geju.get('geju_type', '')}")
        lines.append(f"  格局描述：{geju.get('geju_desc', '')}")
        if geju.get("is_cong"):
            lines.append("  （从格）")

    # 喜用神
    if yongshen:
        lines.append("【喜用神】")
        lines.append(f"  日主旺衰：{yongshen.get('wang_shuai', '')}")
        lines.append(f"  喜用神：{', '.join(yongshen.get('yong_shen', []))}")
        lines.append(f"  忌神：{', '.join(yongshen.get('ji_shen', []))}")

    # 调候
    if tiaohou:
        lines.append("【调候】")
        lines.append(f"  季节：{tiaohou.get('season', '')}")
        lines.append(f"  是否需要调候：{'是' if tiaohou.get('required_tiaohou') else '否'}")
        if tiaohou.get('tiaohou_shens'):
            lines.append(f"  调候用神：{', '.join(tiaohou.get('tiaohou_shens', []))}")

    # 大运
    if dayuns:
        lines.append("【大运】")
        for i, dy in enumerate(dayuns[:6]):  # 前6步大运
            if isinstance(dy, dict):
                lines.append(f"  {dy.get('start_age', '?')}-{dy.get('end_age', '?')}岁："
                             f"{dy.get('ganzhi', '')}")
            else:
                lines.append(f"  大运{i+1}：{dy}")

    # 地支关系
    if branch_relations:
        lines.append("【地支关系】")
        for rel_name, rel_list in branch_relations.items():
            if rel_list:
                lines.append(f"  {rel_name}：{', '.join(rel_list)}")

    if extra:
        lines.append("【补充信息】")
        for k, v in extra.items():
            lines.append(f"  {k}：{v}")

    return "\n".join(lines)


def build_ziwei_context(chart_dict: Dict[str, Any]) -> str:
    """将紫微斗数命盘转为 LLM 上下文"""
    lines = ["【紫微斗数命盘数据】"]
    lines.append(f"性别：{chart_dict.get('gender', '')}")
    lines.append(f"农历：{chart_dict.get('lunar_month', '')}月{chart_dict.get('lunar_day', '')}日")
    lines.append(f"年柱：{chart_dict.get('year_gan', '')}{chart_dict.get('year_zhi', '')}")
    lines.append(f"时支：{chart_dict.get('hour_zhi', '')}")

    # 命宫
    ming_gong = chart_dict.get("ming_gong", {})
    if ming_gong:
        lines.append(f"命宫：{ming_gong.get('gong_name', '')}（{ming_gong.get('gong_zhi', '')}）")
        stars = ming_gong.get("stars", [])
        if stars:
            star_str = "、".join(s if isinstance(s, str) else s.get("name", "") for s in stars)
            lines.append(f"  主星：{star_str}")

    # 身宫
    shen_gong = chart_dict.get("shen_gong", {})
    if shen_gong:
        lines.append(f"身宫：{shen_gong.get('gong_name', '')}（{shen_gong.get('gong_zhi', '')}）")

    # 十二宫
    palaces = chart_dict.get("palaces", [])
    if palaces:
        lines.append("【十二宫位】")
        for p in palaces:
            if isinstance(p, dict):
                stars = p.get("stars", [])
                star_names = [s if isinstance(s, str) else s.get("name", "") for s in stars]
                lines.append(f"  {p.get('gong_name', '')}（{p.get('gong_zhi', '')}）："
                             f"{', '.join(star_names) if star_names else '空宫'}")

    # 四化
    sihua = chart_dict.get("sihua", {})
    if sihua:
        lines.append("【四化】")
        for k, v in sihua.items():
            lines.append(f"  {k}：{v}")

    return "\n".join(lines)


def build_liuyao_context(result_dict: Dict[str, Any]) -> str:
    """将六爻结果转为 LLM 上下文"""
    lines = ["【六爻卦象数据】"]
    lines.append(f"本卦：{result_dict.get('ben_gua_name', '')} "
                 f"{result_dict.get('ben_gua_symbol', '')}")
    if result_dict.get("bian_gua_name"):
        lines.append(f"变卦：{result_dict.get('bian_gua_name', '')} "
                     f"{result_dict.get('bian_gua_symbol', '')}")
    if result_dict.get("hu_gua_name"):
        lines.append(f"互卦：{result_dict.get('hu_gua_name', '')}")

    lines.append(f"上卦：{result_dict.get('shang_gua', '')}")
    lines.append(f"下卦：{result_dict.get('xia_gua', '')}")
    lines.append(f"卦宫：{result_dict.get('gua_gong', '')}")

    # 六亲
    liuqin = result_dict.get("liuqin", [])
    if liuqin:
        lines.append("【六亲配置】（从初爻到上爻）")
        for i, lq in enumerate(liuqin):
            lines.append(f"  {i+1}爻：{lq}")

    # 六神
    liushen = result_dict.get("liushen", [])
    if liushen:
        lines.append("【六神配置】")
        for i, ls in enumerate(liushen):
            lines.append(f"  {i+1}爻：{ls}")

    # 世应
    shi_yao = result_dict.get("shi_yao", "")
    ying_yao = result_dict.get("ying_yao", "")
    if shi_yao:
        lines.append(f"世爻：第{shi_yao}爻")
    if ying_yao:
        lines.append(f"应爻：第{ying_yao}爻")

    # 日辰
    day_ganzhi = result_dict.get("day_ganzhi", "")
    if day_ganzhi:
        lines.append(f"日辰：{day_ganzhi}")

    # 动爻
    dong_yao = result_dict.get("dong_yao", [])
    if dong_yao:
        lines.append(f"动爻：第{', '.join(str(y+1) for y in dong_yao)}爻")

    # 断辞
    duan_ci = result_dict.get("duan_ci", "")
    if duan_ci:
        lines.append(f"断辞：{duan_ci}")

    return "\n".join(lines)


def build_name_context(name_dict: Dict[str, Any]) -> str:
    """将姓名学结果转为 LLM 上下文"""
    lines = ["【姓名学分析数据】"]
    lines.append(f"姓名：{name_dict.get('surname', '')}{name_dict.get('given_name', '')}")
    lines.append(f"姓氏笔画：{name_dict.get('surname_strokes', '')}")

    given_strokes = name_dict.get("given_strokes", [])
    if given_strokes:
        lines.append(f"名字笔画：{', '.join(str(s) for s in given_strokes)}")

    # 五格
    wuge = name_dict.get("wuge", {})
    if wuge:
        lines.append("【五格数理】")
        lines.append(f"  天格：{wuge.get('tian', '')}")
        lines.append(f"  人格：{wuge.get('ren', '')}")
        lines.append(f"  地格：{wuge.get('di', '')}")
        lines.append(f"  外格：{wuge.get('wai', '')}")
        lines.append(f"  总格：{wuge.get('zong', '')}")

    # 三才
    sancai = name_dict.get("sancai", ())
    if sancai:
        lines.append(f"三才：{'、'.join(sancai)}")
    lines.append(f"三才吉凶：{name_dict.get('sancai_ji', '')}")
    if name_dict.get("sancai_desc"):
        lines.append(f"三才说明：{name_dict.get('sancai_desc', '')}")

    # 评分
    lines.append(f"总体评分：{name_dict.get('score', '')}")

    # 建议
    suggestions = name_dict.get("suggestions", [])
    if suggestions:
        lines.append("【建议】")
        for s in suggestions:
            lines.append(f"  - {s}")

    return "\n".join(lines)


def build_marriage_context(marriage_dict: Dict[str, Any]) -> str:
    """将合婚结果转为 LLM 上下文"""
    lines = ["【合婚分析数据】"]
    lines.append(f"甲方：{marriage_dict.get('name1', '')}")
    lines.append(f"乙方：{marriage_dict.get('name2', '')}")

    # 纳音
    if marriage_dict.get("nayin1"):
        lines.append(f"甲方纳音：{marriage_dict.get('nayin1', '')}")
    if marriage_dict.get("nayin2"):
        lines.append(f"乙方纳音：{marriage_dict.get('nayin2', '')}")
    lines.append(f"纳音匹配：{marriage_dict.get('nayin_match', '')} "
                 f"（评分：{marriage_dict.get('nayin_score', '')}）")

    # 日干
    if marriage_dict.get("day_gan1"):
        lines.append(f"甲方日干：{marriage_dict.get('day_gan1', '')}")
    if marriage_dict.get("day_gan2"):
        lines.append(f"乙方日干：{marriage_dict.get('day_gan2', '')}")
    lines.append(f"日干关系：{marriage_dict.get('day_gan_relation', '')} "
                 f"（评分：{marriage_dict.get('day_gan_score', '')}）")

    # 地支
    if marriage_dict.get("branch_relation"):
        lines.append(f"地支关系：{marriage_dict.get('branch_relation', '')} "
                     f"（评分：{marriage_dict.get('branch_score', '')}）")

    # 五行
    if marriage_dict.get("wuxing_match"):
        lines.append(f"五行互补：{marriage_dict.get('wuxing_match', '')} "
                     f"（评分：{marriage_dict.get('wuxing_score', '')}）")

    # 生肖
    if marriage_dict.get("shengxiao_match"):
        lines.append(f"生肖匹配：{marriage_dict.get('shengxiao_match', '')} "
                     f"（评分：{marriage_dict.get('shengxiao_score', '')}）")

    # 综合
    lines.append(f"综合评分：{marriage_dict.get('total_score', '')}")
    lines.append(f"综合评价：{marriage_dict.get('conclusion', '')}")

    return "\n".join(lines)


def build_oracle_context(oracle_dict: Dict[str, Any]) -> str:
    """将 Oracle 推背图结果转为 LLM 上下文"""
    lines = ["【推背图/周易卦象数据】"]
    lines.append(f"占卜模式：{oracle_dict.get('mode', '')}")
    lines.append(f"卦象：{oracle_dict.get('hexagram', '')}")
    lines.append(f"卦名：第{oracle_dict.get('hexagram_index', '')}卦")
    lines.append(f"上卦：{oracle_dict.get('upper_trigram', '')}")
    lines.append(f"下卦：{oracle_dict.get('lower_trigram', '')}")

    if oracle_dict.get("yao_lines"):
        lines.append("【爻象】")
        for i, yao in enumerate(oracle_dict.get("yao_lines", [])):
            lines.append(f"  {i+1}爻：{yao}")

    if oracle_dict.get("judgment"):
        lines.append(f"卦辞：{oracle_dict.get('judgment', '')}")
    if oracle_dict.get("image"):
        lines.append(f"象辞：{oracle_dict.get('image', '')}")
    if oracle_dict.get("commentary"):
        lines.append(f"注释：{oracle_dict.get('commentary', '')}")

    if oracle_dict.get("gan_zhi"):
        lines.append(f"干支：{oracle_dict.get('gan_zhi', '')}")
    if oracle_dict.get("wuxing"):
        lines.append(f"五行：{oracle_dict.get('wuxing', '')}")

    return "\n".join(lines)


# ============================================================================
# AI 解读生成函数
# ============================================================================

async def interpret_bazi(
    bazi_context: str,
    llm: Optional[BaseLLMAdapter] = None,
    use_rag: bool = False,
    question: str = "",
) -> str:
    """八字深度 AI 解读

    Args:
        bazi_context: 由 build_bazi_context() 生成的结构化上下文
        llm: LLM 适配器（默认使用全局实例）
        use_rag: 是否启用 RAG 知识增强
        question: 可选的具体问题（如"我的事业运如何？"）

    Returns:
        AI 生成的八字解读报告
    """
    if llm is None:
        llm = get_llm()

    messages = [ChatMessage(role="system", content=BAZI_INTERPRET_PROMPT)]

    if use_rag:
        rag_ctx = _build_rag_context(["八字", "格局", "用神", "神煞", "大运"])
        if rag_ctx:
            messages.append(ChatMessage(role="system", content=f"相关命理知识：\n{rag_ctx}"))

    user_content = f"请根据以下八字数据生成命理分析报告：\n\n{bazi_context}"
    if question:
        user_content += f"\n\n用户特别关注：{question}"
    messages.append(ChatMessage(role="user", content=user_content))

    response = await llm.chat(messages)
    return response.content


async def interpret_bazi_stream(
    bazi_context: str,
    llm: Optional[BaseLLMAdapter] = None,
    use_rag: bool = False,
    question: str = "",
) -> AsyncGenerator[str, None]:
    """八字深度 AI 解读（流式）"""
    if llm is None:
        llm = get_llm()

    messages = [ChatMessage(role="system", content=BAZI_INTERPRET_PROMPT)]

    if use_rag:
        rag_ctx = _build_rag_context(["八字", "格局", "用神"])
        if rag_ctx:
            messages.append(ChatMessage(role="system", content=f"相关命理知识：\n{rag_ctx}"))

    user_content = f"请根据以下八字数据生成命理分析报告：\n\n{bazi_context}"
    if question:
        user_content += f"\n\n用户特别关注：{question}"
    messages.append(ChatMessage(role="user", content=user_content))

    async for chunk in llm.chat_stream(messages):
        yield chunk


async def interpret_ziwei(
    ziwei_context: str,
    llm: Optional[BaseLLMAdapter] = None,
    question: str = "",
) -> str:
    """紫微斗数 AI 解读"""
    if llm is None:
        llm = get_llm()

    messages = [ChatMessage(role="system", content=ZIWEI_INTERPRET_PROMPT)]
    user_content = f"请根据以下紫微斗数命盘数据生成分析报告：\n\n{ziwei_context}"
    if question:
        user_content += f"\n\n用户特别关注：{question}"
    messages.append(ChatMessage(role="user", content=user_content))

    response = await llm.chat(messages)
    return response.content


async def interpret_liuyao(
    liuyao_context: str,
    question: str = "",
    llm: Optional[BaseLLMAdapter] = None,
) -> str:
    """六爻 AI 解读"""
    if llm is None:
        llm = get_llm()

    messages = [ChatMessage(role="system", content=LIUYAO_INTERPRET_PROMPT)]
    user_content = f"请根据以下六爻卦象数据生成占卜分析报告：\n\n{liuyao_context}"
    if question:
        user_content += f"\n\n所占之事：{question}"
    messages.append(ChatMessage(role="user", content=user_content))

    response = await llm.chat(messages)
    return response.content


async def interpret_name(
    name_context: str,
    llm: Optional[BaseLLMAdapter] = None,
) -> str:
    """姓名学 AI 解读"""
    if llm is None:
        llm = get_llm()

    messages = [ChatMessage(role="system", content=NAME_INTERPRET_PROMPT)]
    messages.append(ChatMessage(
        role="user",
        content=f"请根据以下姓名学数据生成分析报告：\n\n{name_context}",
    ))

    response = await llm.chat(messages)
    return response.content


async def interpret_marriage(
    marriage_context: str,
    llm: Optional[BaseLLMAdapter] = None,
) -> str:
    """合婚 AI 解读"""
    if llm is None:
        llm = get_llm()

    messages = [ChatMessage(role="system", content=MARRIAGE_INTERPRET_PROMPT)]
    messages.append(ChatMessage(
        role="user",
        content=f"请根据以下合婚数据生成分析报告：\n\n{marriage_context}",
    ))

    response = await llm.chat(messages)
    return response.content


async def interpret_oracle(
    oracle_context: str,
    question: str = "",
    llm: Optional[BaseLLMAdapter] = None,
) -> str:
    """Oracle 推背图 AI 深度解读"""
    if llm is None:
        llm = get_llm()

    messages = [ChatMessage(role="system", content=ORACLE_INTERPRET_PROMPT)]
    user_content = f"请根据以下卦象数据生成深度解读：\n\n{oracle_context}"
    if question:
        user_content += f"\n\n所占之事：{question}"
    messages.append(ChatMessage(role="user", content=user_content))

    response = await llm.chat(messages)
    return response.content


# ============================================================================
# 便捷函数：从引擎结果直接生成解读
# ============================================================================

async def interpret_bazi_from_analysis(
    analysis: Dict[str, Any],
    shensha_result: Any = None,
    comprehensive_result: Any = None,
    llm: Optional[BaseLLMAdapter] = None,
    use_rag: bool = False,
    question: str = "",
) -> str:
    """从 BaziAnalyzer.analysis 直接生成 AI 解读

    Args:
        analysis: BaziAnalyzer.analysis 字典
        shensha_result: ShenshaResult 对象（可选）
        comprehensive_result: ComprehensiveResult 对象（可选，含格局/喜用神/调候）
        llm: LLM 适配器
        use_rag: 是否启用 RAG
        question: 可选问题
    """
    shensha_dict = _to_dict(shensha_result) if shensha_result else None
    geju_dict = None
    yongshen_dict = None
    tiaohou_dict = None

    if comprehensive_result:
        comp_dict = _to_dict(comprehensive_result)
        geju_dict = comp_dict.get("geju")
        yongshen_dict = comp_dict.get("yongshen")
        tiaohou_dict = comp_dict.get("tiaohou")

    context = build_bazi_context(
        pillars=analysis.get("pillars", {}),
        day_master=analysis.get("day_master", ""),
        gender="male" if analysis.get("is_male", True) else "female",
        wuxing=analysis.get("wuxing"),
        shigan_map=analysis.get("shigan_map"),
        shensha=shensha_dict,
        geju=geju_dict,
        yongshen=yongshen_dict,
        tiaohou=tiaohou_dict,
        dayuns=analysis.get("dayuns"),
        branch_relations=analysis.get("branch_relations"),
    )

    return await interpret_bazi(context, llm=llm, use_rag=use_rag, question=question)


# ============================================================================
# 阶段二十四：多体系综合分析 AI 解读
# ============================================================================

SYSTEM_PROMPT_FOR_COMPREHENSIVE = (
    "你是一位精通中国传统命理的资深专家，精通八字命理、紫微斗数、奇门遁甲、"
    "六爻卦、流年断语、玄空风水、七政四余等多种术数体系。你将收到一份多体系"
    "综合分析结果，包含各体系分析结论、喜用神忌神交叉验证结果、共识运势评分"
    "和各分项研判。请生成专业、有深度、易懂的综合命理分析报告，要求：\n"
    "1. 开篇总论（100字以内）：结合多体系一致性，对命局层次做整体定性。\n"
    "2. 喜用神与忌神分析（150字以内）：汇总各体系共识与分歧，提出最具共识的"
    "喜用神方向与忌神提醒。\n"
    "3. 分项综合研判（200字以内）：事业、财运、感情、健康四方面简述。\n"
    "4. 关键流年提示（100字以内）：根据流年体系给出近期最重要的一两个提示。\n"
    "5. 综合建议与趋避（100字以内）：喜用神方位、行业方向等方向性建议。\n"
    "6. 全篇控制在600-800字，结尾注明\"以上仅供参考\"。"
)

SYSTEM_PROMPT_FOR_MOCK_COMPREHENSIVE = (
    "你是中国传统命理大师。请用简洁风格：1句话概括命局，"
    "列出喜用神忌神，简述事业财运感情健康四方面，给出2条建议，"
    "结尾注明\"以上仅供参考\"。"
)


def build_comprehensive_context(comp_dict: Dict[str, Any]) -> str:
    """从 ComprehensiveResult 字典构建结构化上下文字符串"""
    birth = comp_dict.get("birth_info", {})
    systems = comp_dict.get("systems", {})
    cross = comp_dict.get("cross_validation", {})
    consensus = comp_dict.get("consensus", {})
    report = comp_dict.get("comprehensive_report", "")

    gender_cn = "男" if birth.get("gender") == "male" else "女" if birth.get("gender") == "female" else birth.get("gender", "")

    lines = [
        "[基础信息]",
        f"  性别：{gender_cn}",
        f"  分析年份：{birth.get('target_year', 'N/A')}",
        "",
        "[各体系结论摘要]",
    ]

    for name, sys_data in systems.items():
        if isinstance(sys_data, dict):
            lines.append(f"  [{name}]")
            if sys_data.get("available") is False:
                lines.append(f"    [不可用] {sys_data.get('error', '未知错误')}")
            else:
                summary = sys_data.get("summary", "")
                data = sys_data.get("data", {})
                if summary:
                    lines.append(f"    摘要：{summary}")
                for key in ["yongshen", "喜用神", "ming_zhu", "命宫主星",
                            "geju_name", "格局", "score", "评分"]:
                    val = data.get(key) if isinstance(data, dict) else None
                    if val:
                        lines.append(f"    {key}：{val}")
            lines.append("")

    lines.extend([
        "[交叉验证结果]",
        f"  一致性得分：{cross.get('score', 'N/A')}（满分100）",
        f"  验证等级：{cross.get('level', 'N/A')}",
    ])
    agreed = cross.get("agreements", [])
    conflicts = cross.get("conflicts", [])
    if agreed:
        lines.append(f"  达成一致：{'、'.join(str(ag) for ag in agreed)}")
    if conflicts:
        lines.append(f"  存在分歧：{'、'.join(str(cf) for cf in conflicts)}")
    for p in cross.get("interpretations", []):
        lines.append(f"  解读：{p}")
    lines.append("")

    lines.extend([
        "[共识运势]",
        f"  综合等级：{consensus.get('overall', 'N/A')}",
        f"  综合评分：{consensus.get('score', 'N/A')}",
        f"  事业：{consensus.get('career', 'N/A')}",
        f"  财运：{consensus.get('wealth', 'N/A')}",
        f"  感情：{consensus.get('relationships', 'N/A')}",
        f"  健康：{consensus.get('health', 'N/A')}",
    ])
    for k, label in [("key_strengths", "核心优势"), ("key_risks", "核心风险"),
                      ("best_timing", "最佳时机"), ("weak_timing", "弱运时机")]:
        items = consensus.get(k, [])
        if items:
            lines.append(f"  {label}：{'、'.join(str(x) for x in items)}")
    lines.append("")

    if report:
        lines.extend(["", "[系统原始报告摘要]", report[:500]])

    return "\n".join(lines)


async def interpret_comprehensive(
    comp_dict: Dict[str, Any],
    llm: Optional[BaseLLMAdapter] = None,
    use_rag: bool = False,
    question: str = "",
) -> str:
    """多体系综合分析 AI 深度解读

    Args:
        comp_dict: ComprehensiveResult.to_dict() 字典
        llm: LLM 适配器（默认使用全局实例）
        use_rag: 是否启用 RAG 知识增强
        question: 可选的具体问题

    Returns:
        AI 生成的多体系综合解读报告
    """
    if llm is None:
        llm = get_llm()

    context = build_comprehensive_context(comp_dict)

    # Mock 模式使用简化提示词
    if "mock" in llm.model_name.lower():
        system_content = SYSTEM_PROMPT_FOR_MOCK_COMPREHENSIVE
    else:
        system_content = SYSTEM_PROMPT_FOR_COMPREHENSIVE

    messages = [ChatMessage(role="system", content=system_content)]

    if use_rag:
        rag_ctx = _build_rag_context(
            ["八字", "紫微斗数", "奇门遁甲", "喜用神", "忌神", "格局", "流年"]
        )
        if rag_ctx:
            messages.append(ChatMessage(
                role="system", content=f"相关命理知识：\n{rag_ctx}"
            ))

    user_content = f"请根据以下多体系综合分析数据生成报告：\n\n{context}"
    if question:
        user_content += f"\n\n用户特别关注：{question}"
    messages.append(ChatMessage(role="user", content=user_content))

    response = await llm.chat(messages)
    return response.content


async def interpret_comprehensive_stream(
    comp_dict: Dict[str, Any],
    llm: Optional[BaseLLMAdapter] = None,
    use_rag: bool = False,
    question: str = "",
) -> AsyncGenerator[str, None]:
    """多体系综合分析 AI 解读（流式）"""
    if llm is None:
        llm = get_llm()

    context = build_comprehensive_context(comp_dict)

    if "mock" in llm.model_name.lower():
        system_content = SYSTEM_PROMPT_FOR_MOCK_COMPREHENSIVE
    else:
        system_content = SYSTEM_PROMPT_FOR_COMPREHENSIVE

    messages = [ChatMessage(role="system", content=system_content)]

    if use_rag:
        rag_ctx = _build_rag_context(
            ["八字", "紫微斗数", "奇门", "喜用神", "忌神", "格局"]
        )
        if rag_ctx:
            messages.append(ChatMessage(
                role="system", content=f"相关命理知识：\n{rag_ctx}"
            ))

    user_content = f"请根据以下多体系综合分析数据生成报告：\n\n{context}"
    if question:
        user_content += f"\n\n用户特别关注：{question}"
    messages.append(ChatMessage(role="user", content=user_content))

    async for chunk in llm.chat_stream(messages):
        yield chunk


# ============================================================================
# 辅助
# ============================================================================

def _build_rag_context(keywords: List[str], top_k: int = 5) -> str:
    """构建 RAG 上下文（复用 llm_adapter 的逻辑）"""
    try:
        from .llm_adapter import _build_rag_context as _build
        from .vector_store import get_vector_store
        store = get_vector_store()
        return _build(store, keywords, top_k=top_k)
    except Exception:
        return ""


# ============================================================================
# v2.5: 上下文感知 + 个性化建议 + 对话记忆
# ============================================================================

# 对话记忆存储（简单内存实现，生产环境应换用 Redis/DB）
_conversation_memory: Dict[str, List[Dict[str, str]]] = {}

CONTEXT_AWARE_PROMPT = """你是一位精通命理的资深顾问，能够结合用户的历史问题和命盘全局信息，
提供上下文感知的深度解读。

分析时请注意：
1. 结合用户之前询问过的问题，理解其关注重点
2. 基于命盘全局信息（不仅是当前流年），给出连贯一致的建议
3. 如果用户之前问过类似问题，本次回答应深化或补充，而非简单重复
4. 保持回答的个性化，避免套话模板"""

PERSONALIZED_RECOMMENDATION_PROMPT = """你是一位命理规划师，善于根据命盘五行喜忌、当前运势和用户目标，
提供可操作的个性化建议。

请基于以下信息生成建议：
1. 五行喜忌：用户需要补什么五行、避什么五行
2. 当前运势：当前处于什么运势阶段
3. 用户目标：用户特别关心什么方面

建议应包含：
- 五行调补方案（颜色、方位、行业、数字等）
- 行动时机建议（最佳时间窗口）
- 注意事项（需要规避的风险）
- 每条建议应具体、可操作，避免空泛"""


def init_conversation(session_id: str) -> None:
    """初始化对话会话"""
    _conversation_memory[session_id] = []


def add_to_conversation(session_id: str, role: str, content: str) -> None:
    """添加消息到对话记忆"""
    if session_id not in _conversation_memory:
        _conversation_memory[session_id] = []
    _conversation_memory[session_id].append({
        "role": role,
        "content": content[:500],  # 截断长消息
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    })


def get_conversation_history(session_id: str, max_turns: int = 5) -> str:
    """获取对话历史摘要"""
    if session_id not in _conversation_memory:
        return ""

    history = _conversation_memory[session_id]
    recent = history[-max_turns * 2:]  # 最近 N 轮（每轮有 user + assistant）

    lines = ["【用户历史对话】"]
    for msg in recent:
        role_label = "用户" if msg["role"] == "user" else "顾问"
        lines.append(f"{role_label}：{msg['content'][:200]}")
    return "\n".join(lines)


def clear_conversation(session_id: str) -> None:
    """清除对话记忆"""
    _conversation_memory.pop(session_id, None)


async def interpret_bazi_contextual(
    bazi_context: str,
    session_id: str = "",
    user_goal: str = "",
    llm: Optional[BaseLLMAdapter] = None,
    question: str = "",
) -> str:
    """上下文感知的八字深度解读 v2.5

    Args:
        bazi_context: 八字结构化上下文
        session_id: 会话ID（用于追踪历史对话）
        user_goal: 用户目标（如"事业发展"、"感情婚姻"）
        llm: LLM 适配器
        question: 当前问题

    Returns:
        AI 生成的上下文感知解读
    """
    if llm is None:
        llm = get_llm()

    messages = [ChatMessage(role="system", content=BAZI_INTERPRET_PROMPT)]

    # 注入上下文感知提示
    messages.append(ChatMessage(role="system", content=CONTEXT_AWARE_PROMPT))

    # 注入对话历史
    if session_id:
        history = get_conversation_history(session_id)
        if history:
            messages.append(ChatMessage(role="system", content=history))

    # 注入用户目标
    if user_goal:
        messages.append(ChatMessage(
            role="system",
            content=f"用户当前关注目标：{user_goal}。请围绕此目标进行重点分析。",
        ))

    user_content = f"请根据以下八字数据生成命理分析报告：\n\n{bazi_context}"
    if question:
        user_content += f"\n\n用户当前问题：{question}"
    messages.append(ChatMessage(role="user", content=user_content))

    response = await llm.chat(messages)

    # 记录对话
    if session_id:
        add_to_conversation(session_id, "user", question or "请分析命盘")
        add_to_conversation(session_id, "assistant", response.content[:300])

    return response.content


def generate_personalized_recommendations(
    yongshen: List[str],
    jishen: List[str],
    current_fortune: str = "平",
    user_goal: str = "综合",
) -> List[Dict[str, str]]:
    """生成个性化建议 v2.5

    基于五行喜忌和当前运势，生成可操作的具体建议。

    Args:
        yongshen: 喜用神五行列表
        jishen: 忌神五行列表
        current_fortune: 当前运势等级
        user_goal: 用户目标

    Returns:
        建议列表，每条包含 category/title/detail/action
    """
    # 五行对应建议库
    WUXING_ADVICE = {
        "木": {
            "colors": ["绿色", "青色"],
            "directions": ["东方", "东南"],
            "industries": ["教育", "文化", "医疗", "园林", "出版"],
            "actions": ["种植绿植", "晨练", "阅读学习"],
            "numbers": [3, 8],
        },
        "火": {
            "colors": ["红色", "紫色", "橙色"],
            "directions": ["南方"],
            "industries": ["能源", "餐饮", "传媒", "互联网", "演艺"],
            "actions": ["增加社交", "创意活动", "适度运动"],
            "numbers": [2, 7],
        },
        "土": {
            "colors": ["黄色", "棕色", "咖啡色"],
            "directions": ["中央", "西南", "东北"],
            "industries": ["房地产", "建筑", "农业", "金融", "咨询"],
            "actions": ["稳定投资", "储蓄计划", "土地相关"],
            "numbers": [5, 0],
        },
        "金": {
            "colors": ["白色", "金色", "银色"],
            "directions": ["西方", "西北"],
            "industries": ["金融", "法律", "机械", "珠宝", "汽车"],
            "actions": ["理财规划", "技能提升", "金属饰品"],
            "numbers": [4, 9],
        },
        "水": {
            "colors": ["黑色", "蓝色", "灰色"],
            "directions": ["北方"],
            "industries": ["物流", "贸易", "旅游", "渔业", "咨询"],
            "actions": ["游泳", "旅行", "冥想", "静心"],
            "numbers": [1, 6],
        },
    }

    recommendations = []

    # 五行补益建议
    for wx in yongshen[:2]:
        advice = WUXING_ADVICE.get(wx)
        if advice:
            recommendations.append({
                "category": "五行调补",
                "title": f"补{wx}行运",
                "detail": f"宜用{', '.join(advice['colors'])}色系，"
                         f"关注{', '.join(advice['directions'][:2])}方向，"
                         f"适合{', '.join(advice['industries'][:2])}等行业",
                "action": f"日常可{advice['actions'][0]}",
            })

    # 忌神规避
    for wx in jishen[:1]:
        advice = WUXING_ADVICE.get(wx)
        if advice:
            recommendations.append({
                "category": "风险规避",
                "title": f"避{ wx }过旺",
                "detail": f"减少{', '.join(advice['colors'])}色系使用，"
                         f"慎选{', '.join(advice['industries'][:2])}等行业",
                "action": f"避免过度{advice['actions'][0] if advice['actions'] else ''}",
            })

    # 基于运势的建议
    if current_fortune in ("大吉", "吉"):
        recommendations.append({
            "category": "时机把握",
            "title": "运势向好，积极进取",
            "detail": "当前运势处于上升期，适合开拓新领域、启动新项目",
            "action": "把握未来3-6个月的黄金窗口期",
        })
    elif current_fortune in ("凶", "大凶"):
        recommendations.append({
            "category": "风险提示",
            "title": "运势低迷，以守为攻",
            "detail": "当前运势处于低谷期，建议保守行事，避免重大决策",
            "action": "宜静不宜动，修身养性，积蓄力量",
        })

    # 基于目标的建议
    goal_advice = {
        "事业": {"category": "事业发展", "title": "事业方向建议",
                 "detail": "结合五行喜忌选择适合的行业方向", "action": "制定职业发展规划"},
        "财运": {"category": "财富管理", "title": "财运管理建议",
                 "detail": "根据运势周期合理安排投资节奏", "action": "分散投资，稳健为主"},
        "感情": {"category": "感情经营", "title": "感情运势建议",
                 "detail": "把握感情运势周期，适时调整相处方式", "action": "多沟通，增进理解"},
        "健康": {"category": "健康养生", "title": "健康调理建议",
                 "detail": "根据五行偏颇调理身体，注意相应脏腑", "action": "规律作息，适度运动"},
    }

    if user_goal in goal_advice:
        recommendations.append(goal_advice[user_goal])

    return recommendations[:5]


async def chat_with_memory(
    bazi_context: str,
    question: str,
    session_id: str,
    llm: Optional[BaseLLMAdapter] = None,
) -> str:
    """带记忆的命理对话 v2.5

    支持多轮对话，AI 能记住之前的问答上下文。

    Args:
        bazi_context: 八字结构化上下文
        question: 当前问题
        session_id: 会话ID
        llm: LLM 适配器

    Returns:
        AI 回复
    """
    if llm is None:
        llm = get_llm()

    messages = [
        ChatMessage(role="system", content=BAZI_INTERPRET_PROMPT),
        ChatMessage(role="system", content="你是一位命理顾问，正在进行多轮对话。"
                    "请结合之前的对话历史，给出连贯、有针对性的回答。"
                    "如果用户切换话题，请自然过渡。"),
    ]

    # 注入命盘上下文
    messages.append(ChatMessage(
        role="system",
        content=f"当前用户的命盘信息：\n{bazi_context[:800]}",
    ))

    # 注入对话历史
    history = get_conversation_history(session_id, max_turns=3)
    if history:
        messages.append(ChatMessage(role="system", content=history))

    # 当前问题
    messages.append(ChatMessage(role="user", content=question))

    response = await llm.chat(messages)

    # 记录对话
    add_to_conversation(session_id, "user", question)
    add_to_conversation(session_id, "assistant", response.content[:300])

    return response.content


# ============================================================================
# 自测
# ============================================================================

async def _self_test():
    """自测"""
    print("=== AI Interpreter 自测 ===\n")

    llm = get_llm(backend="mock")
    print(f"适配器: {llm.model_name}\n")

    # 测试八字解读
    bazi_ctx = build_bazi_context(
        pillars={"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "癸巳"},
        day_master="辛金",
        gender="male",
        wuxing={"金": 2, "水": 2, "火": 3, "土": 1},
        shigan_map={"year_gan": "劫财", "month_gan": "伤官", "day_gan": "日主", "hour_gan": "食神"},
        geju={"geju_name": "伤官格", "geju_type": "伤官", "geju_desc": "月令伤官当令", "is_cong": False},
        yongshen={"wang_shuai": "衰", "yong_shen": ["土", "金"], "ji_shen": ["火", "木"]},
        tiaohou={"season": "夏", "required_tiaohou": True, "tiaohou_shens": ["壬", "癸"]},
        dayuns=[{"start_age": 6, "end_age": 15, "ganzhi": "癸未"}],
        branch_relations={"六合": ["午未"], "三合": []},
    )
    print("--- 八字上下文 ---")
    print(bazi_ctx[:300])

    report = await interpret_bazi(bazi_ctx, llm=llm)
    print("\n--- 八字解读（前300字）---")
    print(report[:300])

    # 测试 Oracle 解读
    oracle_ctx = build_oracle_context({
        "mode": "TUIBEITU",
        "hexagram": "䷀",
        "hexagram_index": 1,
        "upper_trigram": "乾",
        "lower_trigram": "乾",
        "judgment": "元亨利贞",
        "image": "天行健，君子以自强不息",
    })
    print("\n--- Oracle 上下文 ---")
    print(oracle_ctx[:200])

    oracle_report = await interpret_oracle(oracle_ctx, question="事业发展", llm=llm)
    print("\n--- Oracle 解读（前200字）---")
    print(oracle_report[:200])

    print("\n所有测试通过!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(_self_test())
