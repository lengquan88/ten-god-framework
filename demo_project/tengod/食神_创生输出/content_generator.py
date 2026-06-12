#!/usr/bin/env python3
"""
content_generator.py — 内容生成器
食神主理创生，提供统一的内容生成接口与模板机制。
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import time
import uuid


class OutputFormat(Enum):
    """输出格式"""
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    CODE = "code"


@dataclass
class GenerationConfig:
    """生成配置"""
    format: OutputFormat = OutputFormat.TEXT
    max_length: int = 2000
    temperature: float = 0.7
    style: str = "default"
    language: str = "zh-CN"
    extra: Dict[str, Any] = field(default_factory=dict)


class ContentGenerator:
    """内容生成器 — 创生之泉

    统一的生成接口，支持多种格式、模板、缓存。
    """

    def __init__(self, name: str = "default"):
        self._name = name
        self._templates: Dict[str, str] = {}
        self._cache: Dict[str, str] = {}
        self._history: List[Dict[str, Any]] = []

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

        cache_key = f"{prompt}:{config.format.value}:{config.style}"
        if use_cache and cache_key in self._cache:
            content = self._cache[cache_key]
        else:
            # 模拟生成逻辑（实际可对接 LLM API）
            content = self._render(prompt, config)
            if use_cache:
                self._cache[cache_key] = content

        self._history.append({
            "id": str(uuid.uuid4())[:8],
            "prompt": prompt,
            "format": config.format.value,
            "timestamp": time.time(),
            "length": len(content),
        })
        return content

    def _render(self, prompt: str, config: GenerationConfig) -> str:
        """渲染内容"""
        if config.format == OutputFormat.MARKDOWN:
            return f"## {prompt}\n\n*由 {self._name} 生成*\n"
        elif config.format == OutputFormat.JSON:
            return f'{{"prompt": "{prompt}", "generator": "{self._name}"}}'
        elif config.format == OutputFormat.HTML:
            return f"<h1>{prompt}</h1><p>由 {self._name} 生成</p>"
        else:
            return f"{prompt} [by {self._name}]"

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取生成历史"""
        return self._history[-limit:]

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
