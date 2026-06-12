"""
spirit_engine — 神似评估器引擎包
=================================
跨项目可移植版本。脱离 Claw 目录结构独立运行。

组件:
  - Core: EnhancedSpiritTransformer, CrossDomainTestSuite
  - Incremental: SelectiveIncrementalLearner (P446)
  - Cognitive: ContainerCognitiveEngine (P447 CCE)
  - Ensemble: BranchEnsemble

依赖:
  pip install torch sentence-transformers numpy

用法:
  from spirit_engine import SpiritEngine
  engine = SpiritEngine()
  engine.evaluate("问题", ["回答1", "回答2"])
"""

__version__ = '1.0.0'
__all__ = [
    'SpiritEngine',
    'IncrementalLearner',
    'ContainerEngine',
    'BranchEnsemble',
]

import os, sys
import torch
import numpy as np
from sentence_transformers import SentenceTransformer

# ── Core ──
from .core import EnhancedSpiritTransformer, CrossDomainTestSuite

# ── P446 ──
from .incremental import SelectiveIncrementalLearner as IncrementalLearner

# ── P447 ──
from .cognitive import ContainerCognitiveEngine as ContainerEngine

# ── Ensemble ──
from .ensemble import BranchEnsemble


class SpiritEngine:
    """统一入口"""

    def __init__(self, model_path=None, device='cpu'):
        self.device = device
        self.encoder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.model = EnhancedSpiritTransformer(dim=384)
        if model_path:
            ckpt = torch.load(model_path, map_location=device)
            self.model.load_state_dict(ckpt['model'])
        self.model.set_qi('qi_main')
        self.model.eval()

    def evaluate(self, root_question, answers, qi='qi_main', explain=False):
        self.model.set_qi(qi)
        result = self.model.evaluate(answers, self.encoder, root_question)
        if explain:
            case = {'root_question': root_question, 'node_texts': answers}
            exp = self.model.explain(case, self.encoder, qi=qi)
            result['diagnosis'] = exp['diag']
            result['qi_scores'] = exp['qs']
        return result

    def summary(self):
        return {
            'engine': 'spirit_engine',
            'version': __version__,
            'model_params': sum(p.numel() for p in self.model.parameters()),
            'encoder': str(self.encoder.get_embedding_dimension()),
        }
