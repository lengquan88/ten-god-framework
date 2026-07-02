"""
local_embedding.py — 本地语义嵌入引擎 v3.1.0
===================================================
道曰："不出户，知天下；不窥牖，见天道。"

离线语义嵌入方案（零模型下载）：
  - sklearn TfidfVectorizer → 字符级 n-gram 稀疏向量
  - sklearn TruncatedSVD → 降维到目标维度（384/768）
  - 中文分词感知的 token_pattern

支持热切换：
  - 优先使用 SentenceTransformer（模型已缓存时）
  - 回退到 Tfidf+SVD（始终可用）
  - 也支持直接用 torch 的随机正交投影（性能最优，无语义）

用法：
    embedder = LocalEmbedder(dim=384)
    vec = embedder.encode("帮我算一下八字")  # → (384,) numpy
"""

from __future__ import annotations

import os
import math
import hashlib
from typing import Any, Callable, Dict, List, Optional

import numpy as np

# ── 优先：SentenceTransformer ─────────────────────────────────────
_HAS_SENTENCE_TRANSFORMER = False
_SENTENCE_MODEL = None

try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENTENCE_TRANSFORMER = True
except ImportError:
    pass

# 设置 HF 镜像（国内加速）
_HF_MIRROR = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_ENDPOINT", _HF_MIRROR)

# ── 核心：sklearn ──────────────────────────────────────────────────
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.pipeline import Pipeline


# ============================================================================
# 中文分词辅助
# ============================================================================

def _chinese_char_tokenizer(text: str) -> List[str]:
    """中文逐字分词 + 2-gram，对单个汉字做字符级 tokenization"""
    tokens = []
    # 逐字
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff' or '\u3400' <= ch <= '\u4dbf':
            tokens.append(ch)
        elif ch.strip():
            tokens.append(ch)
    # 2-gram（相邻汉字组合）
    for i in range(len(text) - 1):
        a, b = text[i], text[i + 1]
        if ('\u4e00' <= a <= '\u9fff' or '\u3400' <= a <= '\u4dbf') and \
           ('\u4e00' <= b <= '\u9fff' or '\u3400' <= b <= '\u4dbf'):
            tokens.append(a + b)
    return tokens if tokens else [text]


# ============================================================================
# 本地嵌入引擎
# ============================================================================

class LocalEmbedder:
    """本地语义嵌入引擎

    三种模式（按优先级）：
      1. sentence_transformer — 模型已缓存时使用
      2. tfidf_svd — TF-IDF + TruncatedSVD（始终可用）
      3. torch_projection — 随机正交投影（最快，无语义）
    """

    def __init__(
        self,
        dim: int = 384,
        mode: str = "auto",
        model_name: str = "all-MiniLM-L6-v2",
        svd_components: int = 256,
        tfidf_max_features: int = 8192,
    ):
        self.dim = dim
        self.mode = mode
        self._fitted = False

        # 确定实际模式
        if mode == "auto":
            if _HAS_SENTENCE_TRANSFORMER and self._try_load_model(model_name):
                self._actual_mode = "sentence_transformer"
            else:
                self._actual_mode = "tfidf_svd"
        else:
            self._actual_mode = mode

        if self._actual_mode == "sentence_transformer":
            self._model: Any = _SENTENCE_MODEL
            self.dim = self._model.get_embedding_dimension()
        elif self._actual_mode == "tfidf_svd":
            self._pipeline = Pipeline([
                ("tfidf", TfidfVectorizer(
                    tokenizer=_chinese_char_tokenizer,
                    lowercase=False,
                    max_features=tfidf_max_features,
                )),
                ("svd", TruncatedSVD(
                    n_components=min(svd_components, dim),
                    random_state=42,
                )),
            ])
            # 二次投影到目标维度（svd_components → dim）
            self._proj = np.random.RandomState(42).randn(min(svd_components, dim), dim).astype(np.float32)
            self._proj = self._proj / np.linalg.norm(self._proj, axis=1, keepdims=True)
        elif self._actual_mode == "torch_projection":
            self._init_torch_projection()
        else:
            raise ValueError(f"未知模式: {self._actual_mode}")

    def _try_load_model(self, model_name: str) -> bool:
        """尝试加载 SentenceTransformer 模型

        优先级：
          1. 本地缓存加载（local_files_only=True）
          2. 镜像下载（hf-mirror.com）
        """
        global _SENTENCE_MODEL
        if _SENTENCE_MODEL is not None:
            return True
        try:
            _SENTENCE_MODEL = SentenceTransformer(model_name, local_files_only=True)
            return True
        except Exception:
            try:
                _SENTENCE_MODEL = SentenceTransformer(model_name)
                return True
            except Exception:
                return False

    def _init_torch_projection(self) -> None:
        """初始化 torch 随机正交投影"""
        try:
            import torch
            self._torch_proj = torch.nn.Linear(self.dim, self.dim, bias=False)
            torch.nn.init.orthogonal_(self._torch_proj.weight)
            self._use_torch = True
        except ImportError:
            rng = np.random.RandomState(42)
            W = rng.randn(self.dim, self.dim).astype(np.float32)
            U, _, Vt = np.linalg.svd(W, full_matrices=False)
            self._proj_np = (U @ Vt).astype(np.float32)
            self._use_torch = False

    def fit(self, texts: List[str]) -> "LocalEmbedder":
        """在语料上拟合 TF-IDF + SVD

        Args:
            texts: 训练文本列表

        Returns:
            self
        """
        if self._actual_mode == "tfidf_svd":
            sparse = self._pipeline.named_steps["tfidf"].fit_transform(texts)
            svd = self._pipeline.named_steps["svd"]
            svd.fit(sparse)
            # 实际降维后的维度
            actual_svd_dim = svd.components_.shape[0]
            # 重建投影矩阵（二次投影到目标维度）
            rng = np.random.RandomState(42)
            self._proj = rng.randn(actual_svd_dim, self.dim).astype(np.float32)
            self._proj = self._proj / np.linalg.norm(self._proj, axis=1, keepdims=True)
            self._fitted = True
        return self

    def encode(self, text: str) -> np.ndarray:
        """文本 → 语义嵌入向量

        Args:
            text: 输入文本

        Returns:
            (dim,) numpy 向量
        """
        if self._actual_mode == "sentence_transformer":
            return self._model.encode(text, normalize_embeddings=True)

        elif self._actual_mode == "tfidf_svd":
            if not self._fitted:
                # 用单文本自拟合（适用于在线场景）
                self.fit([text])
            vec = self._pipeline.transform([text])[0]  # (svd_components,)
            # 投影到目标维度
            emb = vec @ self._proj  # (dim,)
            # L2 归一化
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            return emb.astype(np.float32)

        elif self._actual_mode == "torch_projection":
            # 确定性 hash → seed → 随机向量 → 正交投影
            seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            rng = np.random.RandomState(seed)
            raw = rng.randn(self.dim).astype(np.float32)
            if self._use_torch:
                import torch
                x = torch.from_numpy(raw)
                out = self._torch_proj(x).detach().cpu().numpy()
            else:
                out = raw @ self._proj_np.T
            norm = np.linalg.norm(out)
            if norm > 0:
                out = out / norm
            return out.astype(np.float32)

        else:
            raise ValueError(f"未知模式: {self._actual_mode}")

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """批量编码

        Args:
            texts: 文本列表

        Returns:
            (batch, dim) numpy 数组
        """
        if self._actual_mode == "sentence_transformer":
            return self._model.encode(texts, normalize_embeddings=True)
        else:
            return np.stack([self.encode(t) for t in texts])

    def get_dim(self) -> int:
        """获取嵌入维度"""
        return self.dim

    def get_mode(self) -> str:
        """获取当前模式"""
        return self._actual_mode


# ============================================================================
# 预训练语料（用于 TF-IDF 拟合）
# ============================================================================

# 命理领域的预训练文本，让 TF-IDF 学到领域语义
_DOMAIN_CORPUS = [
    # 八字
    "八字排盘 年柱 月柱 日柱 时柱 天干 地支 六十甲子 五行 生克 十神 正官 七杀 正印 偏印 正财 偏财 食神 伤官 比肩 劫财",
    "大运 流年 起运 排大运 顺排 逆排 阳年 阴年 节气 命宫 胎元 身宫 用神 忌神 喜神 格局 调候",
    "日主 身强 身弱 从格 化格 专旺 从强 从弱 从财 从杀 从儿 假从 真从 通关 调候 扶抑",
    # 紫微斗数
    "紫微斗数 命宫 兄弟宫 夫妻宫 子女宫 财帛宫 疾厄宫 迁移宫 交友宫 官禄宫 田宅宫 福德宫 父母宫",
    "紫微星 天机星 太阳星 武曲星 天同星 廉贞星 天府星 太阴星 贪狼星 巨门星 天相星 天梁星 七杀星 破军星",
    "四化 化禄 化权 化科 化忌 三方四正 对宫 夹宫 借星 空宫 桃花星 驿马 科甲 魁钺 昌曲 左右",
    # 六爻
    "六爻 起卦 摇卦 铜钱 本卦 变卦 互卦 错卦 综卦 世爻 应爻 动爻 静爻 伏神 飞神 月建 日辰",
    "六亲 父母 兄弟 妻财 官鬼 子孙 六兽 青龙 朱雀 勾陈 腾蛇 白虎 玄武 用神 元神 忌神 仇神",
    # 风水
    "风水 堪舆 峦头 理气 龙 穴 砂 水 向 玄空 飞星 九宫 三元九运 八宅 命卦 罗盘 二十四山",
    "玄空飞星 山星 向星 运星 旺山旺向 上山下水 双星会向 双星会坐 城门诀 七星打劫 父母三般卦",
    # 姓名学
    "姓名学 五格 天格 人格 地格 外格 总格 三才 数理 笔画 五行 金木水火土 字义 音韵 81数理 吉凶",
    "取名 改名 五行补救 八字取名 生肖取名 三才配置 五格数理 字音 字形 字义 寓意 忌用字",
    # 通用认知
    "门禁 裁决 认知 坐忘 注意力 稀疏化 六维 投影 测地线 黎曼 流形 坐标 可信度 时间 投影保真度 图层 交织 边缘",
    "混沌海 推背图 Oracle 预言 自修正 固化 归档 成像 多模态 融合 质量门禁 推测解码 节奏 魂",
    "五行生克 木生火 火生土 土生金 金生水 水生木 木克土 土克水 水克火 火克金 金克木",
    "九宫格 坎一 坤二 震三 巽四 中五 乾六 兑七 艮八 离九",
]


def create_embedder(
    dim: int = 384,
    mode: str = "auto",
    fit_corpus: bool = True,
) -> LocalEmbedder:
    """工厂函数：创建配置好的嵌入器

    Args:
        dim: 嵌入维度
        mode: "auto" | "sentence_transformer" | "tfidf_svd" | "torch_projection"
        fit_corpus: 是否用领域语料预拟合

    Returns:
        LocalEmbedder 实例
    """
    embedder = LocalEmbedder(dim=dim, mode=mode)

    if fit_corpus and embedder.get_mode() == "tfidf_svd":
        embedder.fit(_DOMAIN_CORPUS)

    return embedder


# ============================================================================
# 自检
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  本地语义嵌入引擎 v3.1.0")
    print("=" * 60)

    embedder = create_embedder(dim=384)
    print(f"\n  模式: {embedder.get_mode()}")
    print(f"  维度: {embedder.get_dim()}")

    # 测试单文本编码
    texts = [
        "帮我算一下八字",
        "紫微斗数怎么看命盘",
        "六爻起卦方法",
        "风水布局",
        "取名改名",
    ]
    print(f"\n  测试文本 ({len(texts)} 条):")
    for t in texts:
        vec = embedder.encode(t)
        print(f"    {t:20s} → ({vec.shape[0]},) norm={np.linalg.norm(vec):.3f}")

    # 测试语义相似度（余弦）
    print("\n  语义相似度测试:")
    pairs = [
        ("帮我算八字", "八字排盘方法"),
        ("帮我算八字", "风水布局"),
        ("紫微斗数", "紫微命盘"),
        ("紫微斗数", "六爻占卜"),
    ]
    for a, b in pairs:
        va = embedder.encode(a)
        vb = embedder.encode(b)
        sim = float(np.dot(va, vb))
        print(f"    '{a}' ↔ '{b}': {sim:.3f}")

    # 批量编码
    batch = embedder.encode_batch(texts)
    print(f"\n  批量编码: {batch.shape}")

    print("\n" + "=" * 60)
    print("  自检完成")
    print("=" * 60)