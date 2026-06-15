#!/usr/bin/env python3
"""
食神_创生输出 — 内容生成/LLM调用
食神主理创生，承担系统的内容输出与生成职责。
支持真实 LLM API 接入（OpenAI、Claude、本地模型）。
"""

from .content_generator import (
    ContentGenerator,
    GenerationConfig,
    LLMProvider,
    OutputFormat,
)

__all__ = [
    "ContentGenerator",
    "OutputFormat",
    "GenerationConfig",
    "LLMProvider",
]
__version__ = "1.1.0"
