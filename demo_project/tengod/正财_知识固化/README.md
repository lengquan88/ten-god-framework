# 正财 · 知识固化

> 十神之一，主理固化、收纳与知识管理。
> 承担系统的数据存储与知识图谱职责。

## 模块组成

| 文件 | 功能 |
|------|------|
| `knowledge_base.py` | 轻量级知识库，支持节点/关系/邻居查询 |

## 快速开始

```python
from tengod.正财_知识固化 import KnowledgeBase

kb = KnowledgeBase()

# 添加节点
python = kb.add_node("Python", node_type="language")
django = kb.add_node("Django", node_type="framework")
fastapi = kb.add_node("FastAPI", node_type="framework")

# 添加关系
kb.add_edge(python.id, django.id, "implements", weight=0.9)
kb.add_edge(python.id, fastapi.id, "implements", weight=0.95)

# 查询邻居
for neighbor in kb.neighbors(python.id, "implements"):
    print(f"{neighbor.name} (权重通过关系)")

# 统计
print(kb.stats())
```

## 核心特性

- **图结构**：节点 + 边的知识图谱
- **类型系统**：每个节点可标注类型
- **关系查询**：支持按关系类型筛选邻居
- **导出能力**：一键导出为 JSON 友好的字典
