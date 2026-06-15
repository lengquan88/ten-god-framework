#!/usr/bin/env python3
"""
伤官_破界创新 — 因果推理/模型训练
伤官主理破界，承担系统的因果推理与创新算法职责。
"""

from .innovator import Innovator, Idea, InnovationType
from .oracle_engine import OracleEngine, OracleResult, OracleMode

__all__ = ["Innovator", "Idea", "InnovationType", "OracleEngine", "OracleResult", "OracleMode"]
__version__ = "1.5.0"
