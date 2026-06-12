#!/usr/bin/env python3
"""
content_generator.py — 内容生成器
食神主理创生，提供统一的内容生成接口与模板机制。
支持真实 LLM API 接入（OpenAI、Claude、本地模型）。
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Callable
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
    extra: Dict[str, Any] = field(default_factory=dict)


class ContentGenerator:
    """内容生成器 — 创生之泉

    统一的生成接口，支持多种格式、模板、缓存、真实 LLM API。
    """

    def __init__(self, name: str = "default", api_key: Optional[str] = None):
        self._name = name
        self._templates: Dict[str, str] = {}
        self._cache: Dict[str, str] = {}
        self._history: List[Dict[str, Any]] = []
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._custom_generator: Optional[Callable] = None

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
        """生成内容"""
        if config is None:
            config = GenerationConfig()

        cache_key = f"{prompt}:{config.format.value}:{config.style}:{config.provider.value}"
        if use_cache and cache_key in self._cache:
            content = self._cache[cache_key]
        else:
            content = self._generate_with_provider(prompt, config)
            if use_cache:
                self._cache[cache_key] = content

        self._history.append({
            "id": str(uuid.uuid4())[:8],
            "prompt": prompt,
            "format": config.format.value,
            "provider": config.provider.value,
            "timestamp": time.time(),
            "length": len(content),
        })
        return content

    def _generate_with_provider(self, prompt: str, config: GenerationConfig) -> str:
        """根据提供商生成内容"""
        if config.provider == LLMProvider.MOCK:
            return self._render_mock(prompt, config)
        elif config.provider == LLMProvider.OPENAI:
            return self._call_openai(prompt, config)
        elif config.provider == LLMProvider.CLAUDE:
            return self._call_claude(prompt, config)
        elif config.provider == LLMProvider.LOCAL:
            return self._call_local(prompt, config)
        elif config.provider == LLMProvider.CUSTOM and self._custom_generator:
            return self._custom_generator(prompt, config)
        else:
            return self._render_mock(prompt, config)

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

    def _call_openai(self, prompt: str, config: GenerationConfig) -> str:
        """调用 OpenAI API"""
        try:
            import openai
            client = openai.OpenAI(
                api_key=self._api_key or config.api_key,
                base_url=config.base_url if config.base_url else None,
            )
            response = client.chat.completions.create(
                model=config.model or "gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=config.max_length,
                temperature=config.temperature,
            )
            return response.choices[0].message.content
        except ImportError:
            return f"[Error: openai 未安装] {prompt}"
        except Exception as e:
            return f"[Error: {str(e)}] {prompt}"

    def _call_claude(self, prompt: str, config: GenerationConfig) -> str:
        """调用 Claude API"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self._api_key or config.api_key)
            response = client.messages.create(
                model=config.model or "claude-3-haiku-20240307",
                max_tokens=config.max_length,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except ImportError:
            return f"[Error: anthropic 未安装] {prompt}"
        except Exception as e:
            return f"[Error: {str(e)}] {prompt}"

    def _call_local(self, prompt: str, config: GenerationConfig) -> str:
        """调用本地模型（Ollama 等）"""
        try:
            import requests
            base_url = config.base_url or "http://localhost:11434"
            response = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": config.model or "llama2",
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=60,
            )
            return response.json().get("response", "")
        except ImportError:
            return f"[Error: requests 未安装] {prompt}"
        except Exception as e:
            return f"[Error: {str(e)}] {prompt}"

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取生成历史"""
        return self._history[-limit:]

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """统计信息"""
        provider_count: Dict[str, int] = {}
        for h in self._history:
            p = h.get("provider", "mock")
            provider_count[p] = provider_count.get(p, 0) + 1
        return {
            "name": self._name,
            "total_generations": len(self._history),
            "cache_size": len(self._cache),
            "by_provider": provider_count,
        }


__all__ = ["ContentGenerator", "OutputFormat", "GenerationConfig", "LLMProvider"]
__version__ = "1.1.0"