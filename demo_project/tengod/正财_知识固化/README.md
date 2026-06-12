# 正财 · 知识固化

> 十神之一，主理固化、收纳与知识管理。
> 承担系统的数据存储与知识图谱职责。
> **v1.1.0 新增数据库持久化支持**

## 模块组成

| 文件 | 功能 |
|------|------|
| `knowledge_base.py` | 知识库，支持内存/SQLite/PostgreSQL/JSON 存储 |

## 快速开始

### 内存存储（默认）

```python
from tengod.正财_知识固化 import KnowledgeBase

kb = KnowledgeBase()

python = kb.add_node("Python", node_type="language")
django = kb.add_node("Django", node_type="framework")
kb.add_edge(python.id, django.id, "implements", weight=0.9)

print(kb.stats())
```

### SQLite 持久化

```python
from tengod.正财_知识固化 import KnowledgeBase, StorageBackend

kb = KnowledgeBase(backend=StorageBackend.SQLITE, db_path="my_knowledge.db")

# 添加数据（自动持久化）
node = kb.add_node("AI", node_type="concept")
kb.add_edge(node.id, "ml", "relates")

# 关闭连接
kb.close()
```

### JSON 文件持久化

```python
from tengod.正财_知识固化 import KnowledgeBase, StorageBackend

kb = KnowledgeBase(backend=StorageBackend.JSON, db_path="knowledge.json")

# 添加数据（自动保存到 JSON）
kb.add_node("项目A", node_type="project")

# 手动导出
data = kb.export()
```

### PostgreSQL 持久化

```python
from tengod.正财_知识固化 import KnowledgeBase, StorageBackend

kb = KnowledgeBase(
    backend=StorageBackend.POSTGRES,
    connection_string="postgresql://user:pass@localhost/db",
)

# 添加数据
kb.add_node("用户1", node_type="user")

kb.close()
```

## 核心特性

- **图结构**：节点 + 边的知识图谱
- **类型系统**：每个节点可标注类型
- **关系查询**：支持按关系类型筛选邻居
- **导出能力**：一键导出为 JSON 友好的字典
- **多种后端**：内存、SQLite、PostgreSQL、JSON 文件
- **自动持久化**：添加/删除操作自动保存

## 支持的存储后端

| 后端 | 说明 | 需要的依赖 |
|------|------|------------|
| `MEMORY` | 内存存储（默认） | 无 |
| `SQLITE` | SQLite 数据库 | `sqlite3`（内置） |
| `JSON` | JSON 文件 | 无 |
| `POSTGRES` | PostgreSQL | `psycopg2` |

## 版本

- v1.1.0 (2026-06-12) — 新增数据库持久化支持
- v1.0.0 (2026-06-12) — 基础版本