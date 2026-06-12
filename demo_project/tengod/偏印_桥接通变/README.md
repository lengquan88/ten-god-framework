# 偏印 · 桥接通变

> 十神之一，主理桥接、变通与协议适配。
> 承担系统的协议转换与外部对接职责。

## 模块组成

| 文件 | 功能 |
|------|------|
| `adapter.py` | 适配器与协议转换器，支持 JSON/命名风格等常见转换 |

## 快速开始

```python
from tengod.偏印_桥接通变 import (
    Adapter,
    BridgeRegistry,
    DictToJsonConverter,
    CamelToSnakeConverter,
)

# 创建注册中心
registry = BridgeRegistry()
registry.register_converter("json", DictToJsonConverter())
registry.register_converter("camel_snake", CamelToSnakeConverter())

# 创建适配器
json_adapter = Adapter("json_bridge", registry.get_converter("json"))
registry.register_adapter(json_adapter)

# 转换
data = {"name": "test", "value": 123}
json_str = json_adapter.convert(data, direction="to")
print(json_str)

back = json_adapter.convert(json_str, direction="from")

# 命名风格转换
cs_adapter = Adapter("cs_bridge", registry.get_converter("camel_snake"))
snake = cs_adapter.convert({"userName": "alice", "userAge": 30}, direction="from")
print(snake)  # {"user_name": "alice", "user_age": 30}
```

## 核心特性

- **抽象协议接口**：基于 ABC 的可扩展转换器
- **内置转换器**：JSON、驼峰/蛇形命名
- **适配器封装**：每个适配器独立追踪调用与错误
- **注册中心**：统一管理所有转换资源
