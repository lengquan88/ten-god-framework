# 正印 · 滋养守护

> 十神之一，主理滋养、守护与初始化。
> 承担系统的配置管理与环境初始化职责。

## 模块组成

| 文件 | 功能 |
|------|------|
| `config_manager.py` | 配置管理器，支持默认值/环境变量/文件/手动覆盖 |

## 快速开始

```python
import os
from tengod.正印_滋养守护 import ConfigManager

cm = ConfigManager(env_prefix="TENGOD_")

# 设置默认值
cm.set_default("max_workers", 4, "最大并发数")
cm.set_default("timeout", 30, "超时秒数")

# 从环境变量加载（自动识别 TENGOD_ 前缀）
os.environ["TENGOD_DEBUG"] = "true"
cm.load_from_env("debug")

# 从文件加载
cm.load_from_file("config.json")

# 手动覆盖
cm.set("max_workers", 8)

# 获取
print(cm.get("max_workers"))  # 8
print(cm.get("debug"))        # True (从环境变量)

# 查看所有
print(cm.list_with_source())
```

## 核心特性

- **多源支持**：默认值、环境变量、JSON 文件、手动覆盖
- **优先级管理**：override > file > env > default
- **自动类型转换**：环境变量自动识别 bool/int/float/JSON
- **来源追踪**：每个配置可追溯到具体来源
