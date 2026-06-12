# 食神 · 创生输出

> 十神之一，主理创生、输出与表达。
> 承担系统的内容生成与格式化职责。
> **v1.1.0 新增真实 LLM API 支持**

## 模块组成

| 文件 | 功能 |
|------|------|
| `content_generator.py` | 统一的内容生成器，支持多格式、模板、缓存、真实 LLM API |

## 快速开始

### 模拟生成（默认）

```python
from tengod.食神_创生输出 import ContentGenerator, GenerationConfig, OutputFormat

gen = ContentGenerator(name="食神")

config = GenerationConfig(format=OutputFormat.MARKDOWN, style="formal")
result = gen.generate("项目进展报告", config)
print(result)
```

### 接入 OpenAI

```python
from tengod.食神_创生输出 import ContentGenerator, GenerationConfig, LLMProvider

gen = ContentGenerator(api_key="your-openai-api-key")

config = GenerationConfig(
    provider=LLMProvider.OPENAI,
    model="gpt-4",
    temperature=0.7,
    max_length=2000,
)

result = gen.generate("请写一段关于 AI 的介绍", config)
print(result)
```

### 接入 Claude

```python
from tengod.食神_创生输出 import ContentGenerator, GenerationConfig, LLMProvider

gen = ContentGenerator(api_key="your-anthropic-api-key")

config = GenerationConfig(
    provider=LLMProvider.CLAUDE,
    model="claude-3-opus-20240229",
)

result = gen.generate("请写一段关于 AI 的介绍", config)
print(result)
```

### 接入本地模型（Ollama）

```python
from tengod.食神_创生输出 import ContentGenerator, GenerationConfig, LLMProvider

gen = ContentGenerator()

config = GenerationConfig(
    provider=LLMProvider.LOCAL,
    model="llama2",
    base_url="http://localhost:11434",  # Ollama 默认地址
)

result = gen.generate("请写一段关于 AI 的介绍", config)
print(result)
```

### 自定义生成函数

```python
def my_generator(prompt: str, config: GenerationConfig) -> str:
    # 自定义逻辑
    return f"自定义处理: {prompt}"

gen = ContentGenerator()
gen.set_custom_generator(my_generator)

config = GenerationConfig(provider=LLMProvider.CUSTOM)
result = gen.generate("测试", config)
print(result)
```

## 核心特性

- **多格式输出**：支持文本、Markdown、JSON、HTML、代码
- **模板系统**：通过注册模板复用生成逻辑
- **缓存机制**：相同 prompt 自动复用结果
- **历史记录**：追踪所有生成请求
- **真实 LLM API**：支持 OpenAI、Claude、本地模型（Ollama）
- **自定义回调**：可注入任意生成逻辑

## 支持的 LLM 提供商

| 提供商 | 说明 | 需要的依赖 |
|--------|------|------------|
| `MOCK` | 模拟生成（默认） | 无 |
| `OPENAI` | OpenAI API | `openai` |
| `CLAUDE` | Anthropic Claude | `anthropic` |
| `LOCAL` | 本地模型（Ollama） | `requests` |
| `CUSTOM` | 自定义回调 | 无 |

## 版本

- v1.1.0 (2026-06-12) — 新增真实 LLM API 支持
- v1.0.0 (2026-06-12) — 基础版本