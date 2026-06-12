# 元辰 · 本源定位

> 十神扩展之一，主理本源、定位与根目录。
> 承担项目的根目录定位与核心入口职责。

## 模块组成

| 文件 | 功能 |
|------|------|
| `locator.py` | 项目根目录定位器，扫描核心文件，提供全局入口 |

## 快速开始

```python
from tengod.元辰_本源定位 import YuanChenLocator

locator = YuanChenLocator("/path/to/project")
project = locator.locate()

print(f"项目名: {project.name}")
print(f"子模块: {project.submodules}")
print(f"配置文件: {project.config_files}")

# 获取核心路径
paths = locator.get_core_paths()
print(paths)

# 自动添加到 sys.path
locator.add_to_path()
```

## 核心特性

- **自动定位**：通过标志性文件（README.md、package.json 等）定位项目根
- **子模块扫描**：自动发现项目子目录
- **路径注入**：一键将核心路径添加到 sys.path
- **摘要报告**：生成项目结构摘要