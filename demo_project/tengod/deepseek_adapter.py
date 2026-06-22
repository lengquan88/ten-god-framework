"""
Deepseek AI 适配器 v2.0
======================
中华文明数字永生体 · 智能分析能力扩展

功能：
- 接入 Deepseek Chat API 进行命理智能分析
- 支持流式响应
- 自动重试与错误处理
"""

import os
import json
from typing import Optional, AsyncIterator, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

try:
    import httpx
except ImportError:
    httpx = None


@dataclass
class DeepseekConfig:
    """Deepseek 配置"""
    api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: float = 60.0


@dataclass
class Message:
    """对话消息"""
    role: str  # system / user / assistant
    content: str


@dataclass
class DeepseekResponse:
    """Deepseek 响应"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    created_at: datetime = field(default_factory=datetime.now)


class DeepseekClient:
    """Deepseek API 客户端"""

    def __init__(self, config: Optional[DeepseekConfig] = None):
        self.config = config or DeepseekConfig()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=self.config.timeout
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def chat(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> DeepseekResponse:
        """
        发送对话请求

        Args:
            messages: 对话历史
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            DeepseekResponse: 响应对象
        """
        if httpx is None:
            raise ImportError("httpx is required: pip install httpx")

        # 构建消息列表
        chat_messages = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        chat_messages.extend([{"role": m.role, "content": m.content} for m in messages])

        # 请求体
        payload = {
            "model": self.config.model,
            "messages": chat_messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens
        }

        client = await self._get_client()

        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            return DeepseekResponse(
                content=data["choices"][0]["message"]["content"],
                model=data["model"],
                usage=data.get("usage", {}),
                finish_reason=data["choices"][0].get("finish_reason", "stop")
            )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Deepseek API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"Deepseek request failed: {e}")

    async def stream_chat(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        流式对话请求

        Yields:
            str: 响应文本片段
        """
        if httpx is None:
            raise ImportError("httpx is required: pip install httpx")

        chat_messages = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        chat_messages.extend([{"role": m.role, "content": m.content} for m in messages])

        payload = {
            "model": self.config.model,
            "messages": chat_messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True
        }

        client = await self._get_client()

        try:
            async with client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            content = chunk["choices"][0]["delta"].get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            raise RuntimeError(f"Deepseek stream error: {e}")


# ── 命理分析系统提示词 ────────────────────────────────────────────────────
BAZI_SYSTEM_PROMPT = """你是一位精通中国命理的专家，擅长八字命盘分析、紫微斗数、六爻预测等。

分析时请遵循以下原则：
1. 结合五行生克关系进行深入分析
2. 参考神煞对命局的影响
3. 结合大运流年进行趋势预测
4. 提供具体可行的改善建议

请用专业的命理术语进行分析，语言简洁有力。"""

QIMEN_SYSTEM_PROMPT = """你是一位精通奇门遁甲的专家，擅长奇门遁甲排盘与预测。

分析时请：
1. 准确解读九宫、八门、九星、八神的含义
2. 结合时家奇门判断吉凶
3. 提供具体的行动建议

请用简洁专业的语言进行分析。"""


# ── 便捷函数 ──────────────────────────────────────────────────────────────
_client: Optional[DeepseekClient] = None


def get_client() -> DeepseekClient:
    """获取全局 Deepseek 客户端"""
    global _client
    if _client is None:
        _client = DeepseekClient()
    return _client


async def analyze_bazi(bazi_data: Dict[str, Any], question: str) -> str:
    """
    使用 Deepseek 分析八字命盘

    Args:
        bazi_data: 八字数据
        question: 用户问题

    Returns:
        str: 分析结果
    """
    client = get_client()

    # 构建消息
    bazi_text = _format_bazi(bazi_data)
    messages = [
        Message(role="user", content=f"八字命盘数据：\n{bazi_text}\n\n我的问题：{question}")
    ]

    response = await client.chat(messages, system_prompt=BAZI_SYSTEM_PROMPT)
    return response.content


def _format_bazi(data: Dict[str, Any]) -> str:
    """格式化八字数据为文本"""
    lines = []
    if "pillars" in data:
        pillars = data["pillars"]
        lines.append(f"年柱：{pillars.get('year', '')}")
        lines.append(f"月柱：{pillars.get('month', '')}")
        lines.append(f"日柱：{pillars.get('day', '')}")
        lines.append(f"时柱：{pillars.get('hour', '')}")
    if "wuxing" in data:
        lines.append(f"五行：{data['wuxing']}")
    if "geju" in data:
        lines.append(f"格局：{data['geju']}")
    if "shensha" in data:
        lines.append(f"神煞：{data['shensha']}")
    return "\n".join(lines)


__all__ = [
    "DeepseekConfig",
    "DeepseekClient",
    "DeepseekResponse",
    "Message",
    "BAZI_SYSTEM_PROMPT",
    "QIMEN_SYSTEM_PROMPT",
    "get_client",
    "analyze_bazi",
]
