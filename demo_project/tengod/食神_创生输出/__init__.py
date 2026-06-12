#!/usr/bin/env python3
"""
食神_创生输出 — 内容生成/LLM调用
食神主理创生，承担系统的内容输出与生成职责。
"""

from .content_generator import (
    ContentGenerator,
    OutputFormat,
    GenerationConfig,
)

__all__ = [
    "ContentGenerator",
    "OutputFormat",
    "GenerationConfig",
]
__version__ = "1.0.0"
