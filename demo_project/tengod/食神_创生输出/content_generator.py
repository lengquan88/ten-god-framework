#!/usr/bin/env python3
"""
content_generator.py — 内容生成器
食神主理创生，提供统一的内容生成接口与模板机制。
支持真实 LLM API 接入（OpenAI、Claude、本地模型）。
"""

from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Callable
from dataclasses import dataclass, field
import time
import uuid
import json
import os


class OutputFormat(Enum):
    """输出格式"""
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    CODE = "code"


class LLMProvider(Enum):
    """LLM 提供商"""
    MOCK = "mock"       # 模拟（默认）
    OPENAI = "openai"   # OpenAI API
    CLAUDE = "claude"   # Anthropic Claude
    LOCAL = "local"     # 本地模型（如 Ollama）
    CUSTOM = "custom"   # 自定义回调


@dataclass
class GenerationConfig:
    """生成配置"""
    format: OutputFormat = OutputFormat.TEXT
    max_length: int = 2000
    temperature: float = 0.7
    style: str = "default"
    language: str = "zh-CN"
    provider: LLMProvider = LLMProvider.MOCK
    model: str = ""  # 如 gpt-4, claude-3-opus
    api_key: str = ""  # 可从环境变量读取
    base_url: str = ""  # 自定义 API 地址
    session_id: str = ""  # 会话 ID（空字符串=不使用会话）
    timeout: float = 60.0  # 请求超时（秒）
    max_retries: int = 3  # 最大重试次数
    extra: Dict[str, Any] = field(default_factory=dict)


class ContentGenerator:
    """内容生成器 — 创生之泉

    统一的生成接口，支持多种格式、模板、缓存、真实 LLM API。
    """

    def __init__(self, name: str = "default", api_key: Optional[str] = None):
        self._name = name
        self._cache: Dict[str, str] = {}
        self._history: List[Dict[str, Any]] = []
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._custom_generator: Optional[Callable] = None
        # 会话管理：session_id -> [{"role": "user"/"assistant", "content": str}, ...]
        self._sessions: Dict[str, List[Dict[str, str]]] = {}
        # Token 消耗统计：provider -> 总 token 数
        self._token_counts: Dict[str, int] = {}
        # -------- Prompt 模板库（v1.5.0）--------
        self._templates = {
            "creative_writing": (
                "你是一位才华横溢的创意写作专家。请根据以下主题创作内容：\n"
                "主题：{topic}\n"
                "风格：{style}\n"
                "字数：约 {length} 字\n"
                "请用 {language} 输出。"
            ),
            "technical_explanation": (
                "你是一位专业的技术作家。请解释以下概念：\n"
                "概念：{concept}\n"
                "目标读者：{audience}\n"
                "深度：{depth}\n"
                "请用 {language} 详细说明，包含背景、原理和应用场景。"
            ),
            "analysis_report": (
                "你是一位专业的行业分析师。请对以下内容进行深入分析：\n"
                "主题：{topic}\n"
                "分析维度：{dimensions}\n"
                "请用 {language} 输出分析报告，包含：\n"
                "1. 背景概述\n2. 现状分析\n3. 趋势预测\n4. 建议与结论"
            ),
            "code_explanation": (
                "你是一位资深软件工程师。请解释以下代码的核心逻辑：\n"
                "语言：{language}\n"
                "代码：\n{code}\n"
                "请用中文说明：\n1. 整体架构\n2. 关键函数\n3. 数据流\n4. 潜在改进点"
            ),
            "innovation_idea": (
                "你是一位破界创新专家。请针对以下挑战提出创新性解决方案：\n"
                "挑战：{challenge}\n"
                "约束条件：{constraints}\n"
                "请用 {language} 提出3个创新方案，每个方案包含：\n"
                "名称、核心思路、预期效果、实施难度（1-5分）"
            ),
            "knowledge_summary": (
                "请用 {language} 总结以下内容的核心要点（150字以内）：\n"
                "内容：{content}\n"
                "格式：\n- 要点1\n- 要点2\n- 要点3"
            ),
            "qa_answer": (
                "你是一位知识渊博的导师。请回答以下问题：\n"
                "问题：{question}\n"
                "背景：{context}\n"
                "请用 {language} 详细回答，确保答案准确、清晰、有帮助。"
            ),
        }

    def set_api_key(self, key: str) -> None:
        """设置 API Key"""
        self._api_key = key

    def set_custom_generator(self, func: Callable[[str, GenerationConfig], str]) -> None:
        """设置自定义生成函数"""
        self._custom_generator = func

    def register_template(self, name: str, template: str) -> None:
        """注册模板"""
        self._templates[name] = template

    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        use_cache: bool = True,
    ) -> str:
        """生成内容（生产级：会话管理 + 重试 + 超时）"""
        if config is None:
            config = GenerationConfig()

        # ---------- 会话管理 ----------
        session_id = config.session_id
        messages: List[Dict[str, str]] = []
        if session_id:
            messages = self._sessions.get(session_id, [])
            messages.append({"role": "user", "content": prompt})
        else:
            messages = [{"role": "user", "content": prompt}]

        cache_key = f"{prompt}:{config.format.value}:{config.style}:{config.provider.value}"
        if use_cache and cache_key in self._cache:
            content = self._cache[cache_key]
        else:
            # 根据会话模式传入消息列表
            content = self._generate_with_provider(prompt, config, messages=messages)
            if use_cache:
                self._cache[cache_key] = content

        # 更新会话历史
        if session_id:
            messages.append({"role": "assistant", "content": content})
            self._sessions[session_id] = messages[-50:]  # 保留最近50轮

        # 粗估 Token 消耗（按字符数 ÷ 2 估算中文）
        est_tokens = len(content) // 2 + len(prompt) // 2
        prov = config.provider.value
        self._token_counts[prov] = self._token_counts.get(prov, 0) + est_tokens

        self._history.append({
            "id": str(uuid.uuid4())[:8],
            "prompt": prompt,
            "format": config.format.value,
            "provider": config.provider.value,
            "session_id": session_id,
            "timestamp": time.time(),
            "length": len(content),
            "est_tokens": est_tokens,
        })
        return content

    def _generate_with_provider(
        self,
        prompt: str,
        config: GenerationConfig,
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """根据提供商生成内容"""
        if config.provider == LLMProvider.MOCK:
            return self._render_mock(prompt, config)
        elif config.provider == LLMProvider.OPENAI:
            return self._call_openai(prompt, config, messages=messages)
        elif config.provider == LLMProvider.CLAUDE:
            return self._call_claude(prompt, config, messages=messages)
        elif config.provider == LLMProvider.LOCAL:
            return self._call_local(prompt, config)
        elif config.provider == LLMProvider.CUSTOM and self._custom_generator:
            return self._custom_generator(prompt, config)
        else:
            return self._render_mock(prompt, config)

    def _call_with_retry(
        self,
        func: Callable[[], str],
        max_retries: int,
        provider_name: str,
    ) -> str:
        """通用重试包装（指数退避）"""
        import random
        last_error = ""
        for attempt in range(max_retries + 1):
            try:
                return func()
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(wait)
        return f"[Error({provider_name}): 重试{max_retries+1}次后仍失败] {last_error}"

    def _render_mock(self, prompt: str, config: GenerationConfig) -> str:
        """模拟渲染"""
        if config.format == OutputFormat.MARKDOWN:
            return f"## {prompt}\n\n*由 {self._name} 生成（模拟）*\n"
        elif config.format == OutputFormat.JSON:
            return json.dumps({
                "prompt": prompt,
                "generator": self._name,
                "provider": "mock",
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }, ensure_ascii=False)
        elif config.format == OutputFormat.HTML:
            return f"<h1>{prompt}</h1><p>由 {self._name} 生成</p>"
        elif config.format == OutputFormat.CODE:
            return f"# {prompt}\n# 由 {self._name} 生成\npass"
        else:
            return f"{prompt} [by {self._name} (mock)]"

    def _call_openai(self, prompt: str, config: GenerationConfig,
                     messages: Optional[List[Dict[str, str]]] = None) -> str:
        """调用 OpenAI API（超时控制 + 重试 + 会话消息）"""
        def _do():
            import openai
            client = openai.OpenAI(
                api_key=self._api_key or config.api_key,
                base_url=config.base_url if config.base_url else None,
                timeout=config.timeout,
            )
            # 有会话历史时用 messages 格式，否则降级为单条 prompt
            if messages and len(messages) > 1:
                msgs = messages
            else:
                msgs = [{"role": "user", "content": prompt}]
            response = client.chat.completions.create(
                model=config.model or "gpt-3.5-turbo",
                messages=msgs,
                max_tokens=config.max_length,
                temperature=config.temperature,
            )
            return response.choices[0].message.content or ""
        return self._call_with_retry(_do, config.max_retries, "OpenAI")

    def _call_claude(self, prompt: str, config: GenerationConfig,
                     messages: Optional[List[Dict[str, str]]] = None) -> str:
        """调用 Claude API（超时控制 + 重试 + 会话消息）"""
        def _do():
            import anthropic
            client = anthropic.Anthropic(api_key=self._api_key or config.api_key, timeout=config.timeout)
            if messages and len(messages) > 1:
                msgs = messages
            else:
                msgs = [{"role": "user", "content": prompt}]
            response = client.messages.create(
                model=config.model or "claude-3-haiku-20240307",
                max_tokens=config.max_length,
                messages=msgs,
            )
            return response.content[0].text
        return self._call_with_retry(_do, config.max_retries, "Claude")

    def _call_local(self, prompt: str, config: GenerationConfig) -> str:
        """调用本地模型（Ollama 等）+ 超时 + 重试"""
        def _do():
            import requests
            base_url = config.base_url or "http://localhost:11434"
            response = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": config.model or "llama2",
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=config.timeout,
            )
            return response.json().get("response", "")
        return self._call_with_retry(_do, config.max_retries, "Local/Ollama")

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取生成历史"""
        return self._history[-limit:]

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """统计信息（含 Token 消耗估算）"""
        provider_count: Dict[str, int] = {}
        for h in self._history:
            p = h.get("provider", "mock")
            provider_count[p] = provider_count.get(p, 0) + 1
        return {
            "name": self._name,
            "total_generations": len(self._history),
            "cache_size": len(self._cache),
            "sessions": len(self._sessions),
            "by_provider": provider_count,
            "est_tokens_by_provider": self._token_counts,
            "total_est_tokens": sum(self._token_counts.values()),
        }

    # -------- 会话管理 --------

    def get_session(self, session_id: str) -> List[Dict[str, str]]:
        """获取指定会话的历史消息"""
        return self._sessions.get(session_id, [])

    def list_sessions(self) -> List[str]:
        """列出所有活跃会话 ID"""
        return list(self._sessions.keys())

    def clear_session(self, session_id: str) -> bool:
        """清空指定会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def clear_all_sessions(self) -> int:
        """清空所有会话"""
        count = len(self._sessions)
        self._sessions.clear()
        return count

    # -------- 流式生成 --------

    def generate_stream(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        token_delay: float = 0.02,
    ) -> Iterator[str]:
        """流式生成内容，逐 Token 返回。

        Args:
            prompt: 提示词
            config: 生成配置
            token_delay: 每个 token 的模拟延迟（仅 MOCK 模式生效）

        Yields:
            逐次返回生成的片段文本（可能是字、词或句）

        Usage:
            >>> gen = ContentGenerator()
            >>> for token in gen.generate_stream("你好"):
            >>>     print(token, end="", flush=True)
        """
        if config is None:
            config = GenerationConfig()

        start_time = time.time()
        full_content_parts: List[str] = []

        if config.provider == LLMProvider.MOCK:
            iterator = self._stream_mock(prompt, config, token_delay)
        elif config.provider == LLMProvider.OPENAI:
            iterator = self._stream_openai(prompt, config)
        elif config.provider == LLMProvider.CLAUDE:
            iterator = self._stream_claude(prompt, config)
        elif config.provider == LLMProvider.LOCAL:
            iterator = self._stream_local(prompt, config)
        else:
            iterator = self._stream_mock(prompt, config, token_delay)

        for chunk in iterator:
            full_content_parts.append(chunk)
            yield chunk

        full_content = "".join(full_content_parts)
        self._history.append({
            "id": str(uuid.uuid4())[:8],
            "prompt": prompt,
            "format": config.format.value,
            "provider": config.provider.value,
            "stream": True,
            "timestamp": start_time,
            "duration": round(time.time() - start_time, 3),
            "length": len(full_content),
        })

    def _stream_mock(self, prompt: str, config: GenerationConfig, token_delay: float) -> Iterator[str]:
        """MOCK 模式：逐字输出模拟内容"""
        text = self._render_mock(prompt, config)
        # 按字符或词切分
        tokens: List[str] = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ord(ch) > 127:  # 中文单字
                tokens.append(ch)
                i += 1
            else:  # 英文按词/标点聚合
                buf = ch
                i += 1
                while i < len(text) and ord(text[i]) <= 127 and not text[i].isspace():
                    buf += text[i]
                    i += 1
                tokens.append(buf)

        for tok in tokens:
            time.sleep(token_delay)
            yield tok

    def _stream_openai(self, prompt: str, config: GenerationConfig) -> Iterator[str]:
        """OpenAI 流式调用"""
        try:
            import openai
            client = openai.OpenAI(
                api_key=self._api_key or config.api_key,
                base_url=config.base_url if config.base_url else None,
            )
            stream = client.chat.completions.create(
                model=config.model or "gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=config.max_length,
                temperature=config.temperature,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield delta
        except ImportError:
            yield f"[Error: openai 未安装，回退 MOCK]\n"
            for tok in self._stream_mock(prompt, config, 0):
                yield tok
        except Exception as e:
            yield f"[Error: {str(e)}] "
            for tok in self._stream_mock(prompt, config, 0):
                yield tok

    def _stream_claude(self, prompt: str, config: GenerationConfig) -> Iterator[str]:
        """Claude 流式调用"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self._api_key or config.api_key)
            with client.messages.stream(
                model=config.model or "claude-3-haiku-20240307",
                max_tokens=config.max_length,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except ImportError:
            yield f"[Error: anthropic 未安装，回退 MOCK]\n"
            for tok in self._stream_mock(prompt, config, 0):
                yield tok
        except Exception as e:
            yield f"[Error: {str(e)}] "
            for tok in self._stream_mock(prompt, config, 0):
                yield tok

    def _stream_local(self, prompt: str, config: GenerationConfig) -> Iterator[str]:
        """本地 Ollama 流式调用"""
        try:
            import requests
            base_url = config.base_url or "http://localhost:11434"
            resp = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": config.model or "llama2",
                    "prompt": prompt,
                    "stream": True,
                },
                stream=True,
                timeout=120,
            )
            for line in resp.iter_lines(decode_unicode=True):
                if line:
                    try:
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        if chunk:
                            yield chunk
                    except json.JSONDecodeError:
                        continue
        except ImportError:
            yield f"[Error: requests 未安装，回退 MOCK]\n"
            for tok in self._stream_mock(prompt, config, 0):
                yield tok
        except Exception as e:
            yield f"[Error: {str(e)}] "
            for tok in self._stream_mock(prompt, config, 0):
                yield tok

    def generate_collect(self, prompt: str, config: Optional[GenerationConfig] = None) -> str:
        """调用流式生成但一次性返回完整内容（方便统一接口）"""
        return "".join(self.generate_stream(prompt, config))

    # -------- Prompt 模板库（v1.5.0）--------
    def list_templates(self) -> List[str]:
        """列出所有可用模板名称"""
        return list(self._templates.keys())

    def render_template(
        self,
        name: str,
        **kwargs,
    ) -> str:
        """渲染指定模板，填充变量。
        
        示例：gen.render_template("creative_writing", topic="中华文明", style="古典", length=500, language="中文")
        """
        if name not in self._templates:
            raise ValueError(f"未知模板：{name}，可用：{self.list_templates()}")
        template = self._templates[name]
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"模板 {name} 缺少参数：{e}")

    def generate_from_template(
        self,
        template_name: str,
        config: Optional[GenerationConfig] = None,
        **template_vars,
    ) -> str:
        """使用模板渲染并生成内容（一步到位）。
        
        示例：gen.generate_from_template("creative_writing", topic="中华文明", style="古典")
        """
        prompt = self.render_template(template_name, **template_vars)
        return self.generate(prompt, config)

    def add_template(self, name: str, template: str) -> None:
        """添加或覆盖自定义模板"""
        self._templates[name] = template

    def remove_template(self, name: str) -> bool:
        """移除模板（仅自定义模板）"""
        if name in self._templates:
            del self._templates[name]
            return True
        return False


__all__ = ["ContentGenerator", "OutputFormat", "GenerationConfig", "LLMProvider"]
__version__ = "1.5.0"