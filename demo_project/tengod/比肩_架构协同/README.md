# 比肩 · 架构协同

> 十神之一，主理协同、架构与组件注册。
> 承担系统级组件的统一管理与依赖解析职责。

## 模块组成

| 文件 | 功能 |
|------|------|
| `registry.py` | 全局组件注册中心，支持单例、依赖解析、别名 |

## 快速开始

```python
from tengod.比肩_架构协同 import component, get_registry

@component("logger", aliases=["log", "logging"])
class Logger:
    def info(self, msg):
        print(f"[INFO] {msg}")

# 获取组件
logger = get_registry().get("logger")
logger.info("Hello")

# 通过别名获取
logger = get_registry().get("log")

# 列出所有组件
print(get_registry().list_all())
```

## 核心特性

- **单例模式**：全局唯一注册中心
- **装饰器注册**：通过 `@component` 一行注册
- **别名机制**：一个组件可有多个名称
- **依赖解析**：基于类型注解自动注入依赖
