"""
corpus/ — 命理经典语料库模块 v4.2.0
===========================================
道曰："执古之道，以御今之有。"

子模块：
  - classics_corpus.py  — 命理经典文献结构化数据
  - importer.py         — 语料库→向量存储灌入管道
"""

from .classics_corpus import ClassicsCorpus
from .importer import CorpusImporter

__all__ = ["ClassicsCorpus", "CorpusImporter"]