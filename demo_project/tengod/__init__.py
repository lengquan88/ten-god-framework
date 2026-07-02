"""
TenGod — Chinese Fortune Telling System v4.1.0
===================================================
中华文明数字永生体 · 门禁认知系统 v4.1.0「集成贯通」

核心模块：
- 八字排盘 (bazi_calculator)      - 紫微斗数 (ziwei_engine)
- 六爻预测 (liuyao_engine)         - 奇门遁甲 (qimen_engine)
- 门禁认知引擎 (open_source_bridge)  - 六维投影门禁 (gate_torch)
- 语义嵌入 (local_embedding)        - 向量存储 (vector_store/sqlite_faiss)
- 经典语料库 (corpus/classics_corpus) - 知识图谱桥接 (kg_gate_bridge)
- 评估框架 (eval/)                  - 基准数据集 (eval/benchmark_dataset)
- 知识图谱融合 (knowledge_fusion)    - 国际化 (i18n)

版本: 4.1.0
"""

__version__ = "4.1.0"
__author__ = "TenGod Team"

from .core import get_core, create_app

__all__ = [
    "get_core",
    "create_app",
    "__version__",
]
