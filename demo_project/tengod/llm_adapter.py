#!/usr/bin/env python3
"""
llm_adapter.py — 偏印·桥接通变 · 大模型适配层 v1.0.0

多后端 LLM 适配器，支持 OpenAI / 兼容 API / 本地模型 / Mock。

核心能力：
  - 命理报告润色与白话解读
  - RAG 增强（向量检索 + 知识上下文注入）
  - 交互式命理问答
  - 流式输出（SSE）

用法：
  >>> from tengod.llm_adapter import get_llm, generate_report, chat
  >>> llm = get_llm()
  >>> report = generate_report(bazi_analyzer, llm)
  >>> answer = await chat("我的八字喜用神是什么？", bazi_context, llm)

环境变量：
  TENGOD_LLM_BACKEND    — openai / mock (默认: mock)
  TENGOD_LLM_MODEL      — 模型名称 (默认: gpt-4o-mini)
  TENGOD_LLM_API_KEY    — API Key
  TENGOD_LLM_API_BASE   — API Base URL
"""

from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

# ============================================================================
# 配置
# ============================================================================

LLM_BACKEND = os.environ.get("TENGOD_LLM_BACKEND", "mock")
LLM_MODEL = os.environ.get("TENGOD_LLM_MODEL", "gpt-4o-mini")
LLM_API_KEY = os.environ.get("TENGOD_LLM_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
LLM_API_BASE = os.environ.get("TENGOD_LLM_API_BASE", os.environ.get("OPENAI_API_BASE", ""))
LLM_MAX_TOKENS = int(os.environ.get("TENGOD_LLM_MAX_TOKENS", "2048"))
LLM_TEMPERATURE = float(os.environ.get("TENGOD_LLM_TEMPERATURE", "0.7"))


# ============================================================================
# 消息/响应类型
# ============================================================================

@dataclass
class ChatMessage:
    role: str  # system / user / assistant
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    elapsed_ms: float = 0.0


# ============================================================================
# 抽象适配器
# ============================================================================

class BaseLLMAdapter(ABC):
    """LLM 适配器基类"""

    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = LLM_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
    ) -> LLMResponse:
        """同步对话"""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[ChatMessage],
        temperature: float = LLM_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


# ============================================================================
# OpenAI 适配器
# ============================================================================

class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI / 兼容 API 适配器"""

    def __init__(
        self,
        api_key: str = "",
        api_base: str = "",
        model: str = "gpt-4o-mini",
    ):
        self._api_key = api_key or LLM_API_KEY
        self._api_base = api_base or LLM_API_BASE
        self._model = model or LLM_MODEL
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            kwargs = {"api_key": self._api_key}
            if self._api_base:
                kwargs["base_url"] = self._api_base
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    @property
    def model_name(self) -> str:
        return self._model

    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = LLM_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
    ) -> LLMResponse:
        client = self._get_client()
        t0 = time.time()

        resp = await client.chat.completions.create(
            model=self._model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        elapsed = (time.time() - t0) * 1000
        choice = resp.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=resp.model,
            usage={
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
                "total_tokens": resp.usage.total_tokens if resp.usage else 0,
            },
            elapsed_ms=elapsed,
        )

    async def chat_stream(
        self,
        messages: List[ChatMessage],
        temperature: float = LLM_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        stream = await client.chat.completions.create(
            model=self._model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# ============================================================================
# Mock 适配器（无 API Key 时使用）
# ============================================================================

class MockAdapter(BaseLLMAdapter):
    """Mock 适配器 — 基于模板的本地生成，无需 API Key"""

    @property
    def model_name(self) -> str:
        return "mock/template-v1"

    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = LLM_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
    ) -> LLMResponse:
        t0 = time.time()
        content = self._generate(messages)
        elapsed = (time.time() - t0) * 1000
        return LLMResponse(
            content=content,
            model="mock/template-v1",
            usage={"prompt_tokens": 0, "completion_tokens": len(content), "total_tokens": len(content)},
            elapsed_ms=elapsed,
        )

    async def chat_stream(
        self,
        messages: List[ChatMessage],
        temperature: float = LLM_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
    ) -> AsyncGenerator[str, None]:
        content = self._generate(messages)
        # 模拟流式输出
        for i in range(0, len(content), 10):
            yield content[i:i+10]
            import asyncio
            await asyncio.sleep(0.05)

    def _generate(self, messages: List[ChatMessage]) -> str:
        """基于模板的本地生成"""
        user_msg = ""
        for m in messages:
            if m.role == "user":
                user_msg = m.content
                break

        # 检测是否包含八字数据（排除简短问句）
        has_bazi_data = (("八字" in user_msg or "四柱" in user_msg or "日主" in user_msg)
                         and len(user_msg) > 80)
        # 检测是否是问答
        is_question = ("？" in user_msg or "?" in user_msg or "问" in user_msg
                       or user_msg.startswith("什么") or user_msg.startswith("如何"))

        if is_question and not has_bazi_data:
            return self._generate_qa(user_msg)
        elif has_bazi_data:
            return self._generate_report_section(user_msg)
        else:
            return self._generate_general(user_msg)

    def _generate_report_section(self, context: str) -> str:
        """生成报告润色"""
        parts = context.split("\n")
        lines = ["【命理分析报告】\n"]

        # 提取关键信息
        for line in parts:
            line = line.strip()
            if "日主" in line:
                lines.append(f"根据八字排盘，{line}。")
            elif "五行" in line:
                lines.append(f"从五行分布来看，{line}。")
            elif "格局" in line:
                lines.append(f"格局判断：{line}。")
            elif "用神" in line:
                lines.append(f"喜用神分析：{line}。")
            elif "神煞" in line:
                lines.append(f"神煞方面：{line}。")

        if len(lines) == 1:
            lines.append("根据提供的八字信息，以下是命理分析：")
            lines.append("八字排盘显示命局结构完整，五行分布有其特点。")
            lines.append("建议结合具体大运流年进行深入分析。")

        lines.append("\n---")
        lines.append("*本报告由 Mock LLM 模板引擎生成，接入真实 LLM 可获得更详细的分析。*")
        return "\n".join(lines)

    def _generate_qa(self, question: str) -> str:
        """生成问答回复"""
        answers = {
            "喜用神": "喜用神是根据八字五行旺衰平衡确定的有利五行。日主过旺则需克泄耗，日主过弱则需生扶。具体需结合八字四柱和大运流年综合分析。",
            "五行": "五行（金木水火土）是中国传统哲学的核心概念，在命理学中代表不同的能量属性。五行之间存在相生相克的关系，是分析八字的基础。",
            "格局": "格局是八字命理中的核心概念，根据日主与月令的关系确定。常见格局有正官格、七杀格、正财格、偏财格、食神格、伤官格、正印格、偏印格等。",
            "大运": "大运是十年一变的运势周期，从月柱推导而出。大运的吉凶取决于大运干支与命局的关系，顺排逆排取决于性别和年干阴阳。",
            "神煞": "神煞是八字命理中辅助判断吉凶的星神，包括天乙贵人、天德、月德等吉神，以及劫煞、亡神等凶神。神煞需结合命局整体判断。",
        }

        for key, answer in answers.items():
            if key in question:
                return f"关于「{key}」：\n\n{answer}\n\n---\n*本回复由 Mock LLM 模板引擎生成。*"

        return f"关于您的问题：\n\n这是一个很好的命理问题。建议结合具体的八字四柱进行详细分析。您可以提供完整的出生时间（年/月/日/时），以便进行准确的命理推算。\n\n---\n*本回复由 Mock LLM 模板引擎生成。*"

    def _generate_general(self, context: str) -> str:
        return f"根据您提供的信息，以下是分析：\n\n{context[:500]}\n\n---\n*本回复由 Mock LLM 模板引擎生成。*"


# ============================================================================
# 工厂函数
# ============================================================================

_llm: Optional[BaseLLMAdapter] = None


def get_llm(
    backend: str = "",
    api_key: str = "",
    api_base: str = "",
    model: str = "",
) -> BaseLLMAdapter:
    """获取 LLM 适配器实例

    Args:
        backend: openai / mock
        api_key: API Key
        api_base: API Base URL
        model: 模型名称
    """
    global _llm
    if _llm is not None:
        return _llm

    backend = backend or LLM_BACKEND

    if backend == "openai":
        _llm = OpenAIAdapter(
            api_key=api_key or LLM_API_KEY,
            api_base=api_base or LLM_API_BASE,
            model=model or LLM_MODEL,
        )
    else:
        _llm = MockAdapter()

    return _llm


def reset_llm():
    """重置 LLM 实例"""
    global _llm
    _llm = None


# ============================================================================
# Prompt 模板
# ============================================================================

REPORT_SYSTEM_PROMPT = """你是一位精通中国传统命理学的专家，擅长八字排盘分析和命理报告撰写。

你的任务是根据提供的八字排盘数据，生成一份专业、易懂、有深度的命理分析报告。

报告要求：
1. 使用流畅自然的中文，避免过于机械的表达
2. 对专业术语提供简要解释，让初学者也能理解
3. 保持客观中肯，强调"命理分析仅供参考"
4. 按以下结构组织：基本信息 → 四柱解读 → 五行分析 → 十神分析 → 格局判断 → 喜用神分析 → 大运流年 → 综合建议
5. 每个部分控制在 2-3 句话，简洁有力"""

CHAT_SYSTEM_PROMPT = """你是一位和蔼可亲的命理顾问，精通八字命理、五行哲学、易经八卦。

你的回答风格：
1. 温和亲切，像朋友间的对话
2. 对专业概念提供通俗易懂的解释
3. 始终提醒"命理仅供参考，人生在自己手中"
4. 对于超出命理范围的问题，友善地表示无法回答
5. 回答控制在 200 字以内，简洁明了"""

RAG_SYSTEM_PROMPT = """你是一位精通中国传统命理学的专家。以下是相关知识库的内容，请结合这些知识回答用户的问题。

知识库内容：
{knowledge_context}

请基于以上知识库内容，结合你的专业知识，回答用户的问题。"""


# ============================================================================
# 高级功能
# ============================================================================

async def generate_report(
    bazi_context: str,
    llm: Optional[BaseLLMAdapter] = None,
    use_rag: bool = False,
) -> str:
    """生成命理报告（润色 + 白话解读）

    Args:
        bazi_context: 八字分析上下文（来自 BaziReportGenerator）
        llm: LLM 适配器实例
        use_rag: 是否启用 RAG 增强

    Returns:
        润色后的报告文本
    """
    if llm is None:
        llm = get_llm()

    messages = [ChatMessage(role="system", content=REPORT_SYSTEM_PROMPT)]

    # RAG 增强
    if use_rag:
        try:
            from tengod.vector_store import get_vector_store
            store = get_vector_store()
            # 提取关键词
            keywords = [w for w in ["日主", "五行", "格局", "用神", "大运", "神煞", "调候"]
                       if w in bazi_context]
            if not keywords:
                keywords = ["五行", "阴阳"]
            rag_context = _build_rag_context(store, keywords)
            if rag_context:
                messages.append(ChatMessage(
                    role="system",
                    content=f"相关命理知识：\n{rag_context}",
                ))
        except Exception:
            pass

    messages.append(ChatMessage(
        role="user",
        content=f"请根据以下八字排盘数据生成一份命理分析报告：\n\n{bazi_context}",
    ))

    response = await llm.chat(messages)
    return response.content


async def chat(
    question: str,
    bazi_context: Optional[str] = None,
    llm: Optional[BaseLLMAdapter] = None,
    use_rag: bool = True,
) -> str:
    """交互式命理问答

    Args:
        question: 用户问题
        bazi_context: 八字上下文（可选）
        llm: LLM 适配器实例
        use_rag: 是否启用 RAG 增强

    Returns:
        LLM 回答
    """
    if llm is None:
        llm = get_llm()

    messages = [ChatMessage(role="system", content=CHAT_SYSTEM_PROMPT)]

    # RAG 增强
    if use_rag:
        try:
            from tengod.vector_store import get_vector_store
            store = get_vector_store()
            rag_context = _build_rag_context(store, [question])
            if rag_context:
                messages.append(ChatMessage(
                    role="system",
                    content=f"相关命理知识：\n{rag_context}",
                ))
        except Exception:
            pass

    # 八字上下文
    if bazi_context:
        messages.append(ChatMessage(
            role="system",
            content=f"当前用户的八字信息：\n{bazi_context}",
        ))

    messages.append(ChatMessage(role="user", content=question))
    response = await llm.chat(messages)
    return response.content


async def chat_stream(
    question: str,
    bazi_context: Optional[str] = None,
    llm: Optional[BaseLLMAdapter] = None,
    use_rag: bool = True,
) -> AsyncGenerator[str, None]:
    """流式命理问答"""
    if llm is None:
        llm = get_llm()

    messages = [ChatMessage(role="system", content=CHAT_SYSTEM_PROMPT)]

    if use_rag:
        try:
            from tengod.vector_store import get_vector_store
            store = get_vector_store()
            rag_context = _build_rag_context(store, [question])
            if rag_context:
                messages.append(ChatMessage(
                    role="system",
                    content=f"相关命理知识：\n{rag_context}",
                ))
        except Exception:
            pass

    if bazi_context:
        messages.append(ChatMessage(
            role="system",
            content=f"当前用户的八字信息：\n{bazi_context}",
        ))

    messages.append(ChatMessage(role="user", content=question))
    async for chunk in llm.chat_stream(messages):
        yield chunk


def _build_rag_context(store, queries: List[str], top_k: int = 5) -> str:
    """构建 RAG 上下文"""
    all_results = []
    seen = set()
    for q in queries:
        try:
            result = store.search(q, top_k=top_k)
            for r in result.results:
                key = r.get("name", "")
                if key not in seen:
                    seen.add(key)
                    text = r.get("text", "")
                    if text:
                        all_results.append(f"- {key}: {text[:200]}")
        except Exception:
            pass
    if all_results:
        return "\n".join(all_results[:10])
    return ""


# ============================================================================
# 自测
# ============================================================================

async def _self_test():
    """自测"""
    print("=== LLM Adapter 自测 ===\n")

    # Mock 适配器
    llm = get_llm(backend="mock")
    print(f"适配器: {llm.model_name}")

    # 报告生成
    bazi_data = """
八字：庚午 壬午 辛亥 癸巳
日主：辛金
五行：金2 木0 水2 火3 土1
格局：伤官格
用神：土、金
神煞：天乙贵人(年)、桃花(日)、驿马(月)
大运：6-15岁 癸未"""
    report = await generate_report(bazi_data, llm)
    print(f"\n--- 报告生成 ---")
    print(report[:400])

    # 问答
    qa = await chat("我的八字喜用神是什么？", bazi_data, llm)
    print(f"\n--- 问答 ---")
    print(qa[:400])

    # 流式
    print(f"\n--- 流式输出 ---")
    async for chunk in chat_stream("五行是什么？", llm=llm):
        print(chunk, end="", flush=True)
    print()

    print(f"\n所有测试通过!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(_self_test())