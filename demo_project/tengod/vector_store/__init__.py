"""
vector_store/ — 向量存储模块 v4.2.0
===========================================
道曰："积土成山，风雨兴焉。"

子模块：
  - sqlite_faiss.py  — SQLite + FAISS 向量存储
"""

from .sqlite_faiss import SQLiteFAISSVectorStore, VectorEntry

__all__ = ["SQLiteFAISSVectorStore", "VectorEntry"]