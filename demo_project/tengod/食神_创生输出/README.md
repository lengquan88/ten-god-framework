# 食神 · 创生输出

> 十神之一，主理创生、输出与表达。
> 承担系统的内容生成与格式化职责。

## 模块组成

| 文件 | 功能 |
|------|------|
| `content_generator.py` | 统一的内容生成器，支持多格式、模板、缓存 |

## 快速开始

```python
from tengod.食神_创生输出 import ContentGenerator, GenerationConfig, OutputFormat

gen = ContentGenerator(name="食神")

# 注册模板
gen.register_template("report", "# {title}\n\n{content}")

# 生成内容
config = GenerationConfig(format=OutputFormat.MARKDOWN, style="formal")
result = gen.generate("项目进展报告", config)
print(result)

# 查看历史
print(gen.get_history())
```

## 核心特性

- **多格式输出**：支持文本、Markdown、JSON、HTML
- **模板系统**：通过注册模板复用生成逻辑
- **缓存机制**：相同 prompt 自动复用结果
- **历史记录**：追踪所有生成请求
