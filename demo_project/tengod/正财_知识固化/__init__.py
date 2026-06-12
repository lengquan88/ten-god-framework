#!/usr/bin/env python3
"""
正财_知识固化 — 数据存储/知识图谱
正财主理固化，承担系统的数据存储与知识管理职责。
支持多种存储后端：内存、SQLite、PostgreSQL、JSON。
"""

from .knowledge_base import (
    KnowledgeBase,
    KnowledgeNode,
    KnowledgeEdge,
    StorageBackend,
)

__all__ = ["KnowledgeBase", "KnowledgeNode", "KnowledgeEdge", "StorageBackend"]
__version__ = "1.1.0"