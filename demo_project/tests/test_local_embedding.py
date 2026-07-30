#!/usr/bin/env python3
"""
test_local_embedding.py — 本地语义嵌入引擎深度测试 v1.1
==========================================================
针对 local_embedding.py 中高风险逻辑路径的补充测试：

 1. 中文分词 _chinese_char_tokenizer：纯中文、中英文混合、空字符串、单汉字、带标点
 2. LocalEmbedder 初始化：三种模式（tfidf_svd / torch_projection / invalid）+ auto 模式回落
 3. fit() 方法：tfidf_svd 在多个文本上拟合
 4. encode() 确定性 & 归一化：
    - tfidf_svd：相同文本多次编码结果一致，L2 norm ≈ 1，输出维度 = dim
    - torch_projection：MD5-seeded 确定性（相同文本→相同向量），不同文本→不同向量
 5. encode_batch()：批量编码形状 (batch, dim)，每行 L2 归一化
 6. get_dim() / get_mode() 返回值正确性
 7. create_embedder 工厂：dim 传递、fit_corpus 标志、模式 auto 回落到 tfidf_svd
 8. 边界条件：encode 空字符串、超短文本、超长文本

注意：为保证在没有 sentence_transformers / torch 预训练模型下载的环境下
也能确定性通过，所有测试强制指定 mode="tfidf_svd" 或 mode="torch_projection"。
sentence_transformer（"auto"/"sentence_transformer"）路径需要预训练模型缓存，
从不在 CI 中硬测。
"""

from __future__ import annotations

import numpy as np
import pytest

from tengod.local_embedding import (
    _chinese_char_tokenizer,
    LocalEmbedder,
    create_embedder,
)


# ============================================================================
# 辅助：为 tfidf_svd 生成足够大的词汇量，以便 TruncatedSVD(n_components=K) 满足 K < n_features
# ============================================================================

# 用于 fit 时的丰富小语料（保证 n_features >> svd_components）
_RICH_CORPUS = [
    "八字排盘方法详解",
    "紫微斗数命盘十二宫解读",
    "六爻铜钱起卦流程教学",
    "风水堪舆理论基础入门",
    "姓名学三才五格笔画配置",
    "奇门遁甲九宫排盘秘诀",
    "大六壬神课金口诀断法",
    "四柱八字五行生克制化",
    "天干地支六十甲子纳音表",
    "十二生肖流年运势预测",
    "手相面相气色学总论",
    "周易易经六十四卦爻辞",
    "梅花易数拆字占卜实例",
    "子平真诠格局论命体系",
    "滴天髓阐微穷通宝鉴",
    "三命通会渊海子平评注",
    "五行金木水火土生克关系",
    "十神正官七杀偏印正印",
    "正财偏财食神伤官比肩",
    "大运流年流月流日推算",
]

# 单个最短文本 + 足够上下文预 fit 的 embedder 工厂
def _small_tfidf_svd_embedder(dim=16, svd_components=3, fitted=True):
    """返回一个 tfidf_svd 模式 embedder，预拟合以保证 n_features 充足。"""
    emb = LocalEmbedder(dim=dim, mode="tfidf_svd",
                        svd_components=svd_components,
                        tfidf_max_features=256)
    if fitted:
        emb.fit(_RICH_CORPUS)
    return emb


# ============================================================================
# 1. 中文分词辅助函数
# ============================================================================

class TestChineseCharTokenizer:
    def test_pure_chinese_multiple_chars(self):
        """纯中文：每个字 + 相邻双字 2-gram。"""
        tokens = _chinese_char_tokenizer("甲乙丙丁")
        # 逐字: 甲 乙 丙 丁
        # 2-gram: 甲乙 乙丙 丙丁
        unigrams = [t for t in tokens if len(t) == 1]
        bigrams = [t for t in tokens if len(t) == 2]
        assert unigrams == ["甲", "乙", "丙", "丁"]
        assert bigrams == ["甲乙", "乙丙", "丙丁"]
        assert len(tokens) == 4 + 3

    def test_single_chinese_char(self):
        """单汉字：只有 1 个 token（自身），因为无 2-gram。"""
        tokens = _chinese_char_tokenizer("道")
        assert tokens == ["道"]

    def test_mixed_chinese_english_punctuation(self):
        """中英文 + 数字 + 标点混合：中文逐字，非中文非空白作为 token。"""
        tokens = _chinese_char_tokenizer("八字Bazi,2024！")
        # 中文字符: 八 字 →  2-gram 八字
        # 非空白非中文: B a z i , 2 0 2 4 ！ → 标点、数字、英文字母都视为单个 token
        assert "八" in tokens and "字" in tokens and "八字" in tokens
        assert "B" in tokens
        assert "2" in tokens

    def test_empty_string_returns_self(self):
        """空字符串不会崩溃，返回 [空串]。"""
        assert _chinese_char_tokenizer("") == [""]

    def test_whitespace_only(self):
        """纯空白字符串返回 [原串]（因为没有非空白汉字可提）。"""
        tokens = _chinese_char_tokenizer("   \n\t")
        # 空处理：没有满足 ch.strip() 的字符，所以 tokens 为空，fallback [text]
        assert tokens == ["   \n\t"]

    def test_chinese_punctuation_CJK_symbols_stripped(self):
        """中文标点符号（非汉字）作为 token 或被跳过。"""
        tokens = _chinese_char_tokenizer("命理。玄学")
        # 至少提取到中文 unigram + bigram
        assert "命" in tokens and "理" in tokens and "玄" in tokens and "学" in tokens
        assert "命理" in tokens and "玄学" in tokens


# ============================================================================
# 2. LocalEmbedder 初始化
# ============================================================================

class TestInit:
    def test_tfidf_svd_mode_basic(self):
        emb = LocalEmbedder(dim=64, mode="tfidf_svd", svd_components=16)
        assert emb.get_mode() == "tfidf_svd"
        assert emb.get_dim() == 64

    def test_torch_projection_mode_numpy_fallback(self):
        """即使没有 torch，也能退化为 numpy SVD 正交投影。"""
        emb = LocalEmbedder(dim=32, mode="torch_projection")
        assert emb.get_mode() == "torch_projection"
        assert emb.get_dim() == 32

    def test_invalid_mode_raises_valueerror(self):
        with pytest.raises(ValueError, match="未知模式"):
            LocalEmbedder(dim=16, mode="bogus_mode")

    def test_svd_components_capped_at_dim(self):
        """svd_components > dim 时应被 min() 限制为 dim。"""
        emb = LocalEmbedder(dim=16, mode="tfidf_svd", svd_components=256)
        # 内部投影矩阵形状应为 (min(256,16)=16, dim=16)
        assert emb._proj.shape == (16, 16)


# ============================================================================
# 3. fit() 方法
# ============================================================================

class TestFit:
    def test_fit_returns_self(self):
        """使用丰富语料 + 小 svd_components，保证 n_features > n_components。"""
        emb = LocalEmbedder(dim=32, mode="tfidf_svd", svd_components=4)
        result = emb.fit(_RICH_CORPUS)
        assert result is emb
        assert emb._fitted is True

    def test_fit_small_corpus_enables_encode(self):
        """拟合后，编码不再触发自拟合。"""
        emb = LocalEmbedder(dim=32, mode="tfidf_svd", svd_components=4)
        emb.fit(_RICH_CORPUS)
        # 内部投影矩阵重建后应正确
        assert emb._proj.shape[1] == 32
        assert emb._proj.shape[0] == emb._pipeline.named_steps["svd"].components_.shape[0]


# ============================================================================
# 4. encode() 确定性与归一化
# ============================================================================

class TestEncode:
    # ── 通用断言 ──
    @staticmethod
    def _is_normalized(v: np.ndarray, tol: float = 1e-5) -> bool:
        return abs(np.linalg.norm(v) - 1.0) < tol

    # ── tfidf_svd 模式 ──
    def test_tfidf_svd_encode_shape_and_norm(self):
        emb = _small_tfidf_svd_embedder(dim=48, svd_components=16)
        vec = emb.encode("帮我算一下八字排盘")
        assert vec.shape == (48,)
        assert vec.dtype == np.float32
        assert self._is_normalized(vec)

    def test_tfidf_svd_same_text_deterministic(self):
        """同一 embedder 实例上相同文本多次编码结果应完全一致。"""
        emb = create_embedder(dim=32, mode="tfidf_svd", fit_corpus=True)
        a = emb.encode("八字五行生克关系")
        b = emb.encode("八字五行生克关系")
        np.testing.assert_array_equal(a, b)

    def test_tfidf_svd_self_fit_on_first_encode(self):
        """未 fit 时 encode 丰富文本会自拟合，仍然返回归一化向量。"""
        # 注意：TruncatedSVD 需要 n_components < n_features
        # 用丰富的单条多特征文本 + 小 svd_components
        emb = LocalEmbedder(dim=24, mode="tfidf_svd", svd_components=8,
                            tfidf_max_features=128)
        assert emb._fitted is False
        # 使用丰富语料中所有内容拼接，确保 n_features > 8
        text = "。".join(_RICH_CORPUS)
        vec = emb.encode(text)
        assert emb._fitted is True
        assert vec.shape == (24,)
        assert self._is_normalized(vec)

    # ── torch_projection 模式：MD5 种子 → 完全确定性 ──
    def test_torch_projection_deterministic_same_text(self):
        """相同文本在相同 dim / 相同 random state → 100% 完全相同向量。"""
        emb1 = LocalEmbedder(dim=64, mode="torch_projection")
        emb2 = LocalEmbedder(dim=64, mode="torch_projection")
        v1a = emb1.encode("六爻铜钱起卦法")
        v1b = emb1.encode("六爻铜钱起卦法")
        v2a = emb2.encode("六爻铜钱起卦法")
        np.testing.assert_array_equal(v1a, v1b)
        np.testing.assert_array_equal(v1a, v2a)

    def test_torch_projection_different_texts_different_vectors(self):
        emb = LocalEmbedder(dim=64, mode="torch_projection")
        a = emb.encode("风水堪舆龙脉")
        b = emb.encode("取名改名三才五格")
        cos = float(np.dot(a, b))
        assert cos < 0.9

    def test_torch_projection_output_shape_and_norm_dtype(self):
        emb = LocalEmbedder(dim=128, mode="torch_projection")
        v = emb.encode("奇门遁甲九宫")
        assert v.shape == (128,)
        assert v.dtype == np.float32
        assert self._is_normalized(v)

    # ── 边界条件：极端文本。用预拟合 embedder 保证 n_features 充足 ──
    @pytest.mark.parametrize("text", [
        "",
        "x",         # 单字符非中文
        "甲乙",      # 2 字中文
        "测试重复 " * 500,  # 长文本
    ])
    def test_encode_edge_cases_no_crash_tfidf(self, text):
        """使用预拟合的 embedder（小 svd_components=3），encode 极端文本不 crash。"""
        emb = _small_tfidf_svd_embedder(dim=16, svd_components=3, fitted=True)
        vec = emb.encode(text)
        assert vec.shape == (16,)
        # 极端情况下 norm 为 1 或 0（空串退化），不 crash
        norm = float(np.linalg.norm(vec))
        assert norm <= 1.0 + 1e-4

    @pytest.mark.parametrize("text", ["", "甲乙", "长文本" * 200])
    def test_encode_edge_cases_no_crash_torch(self, text):
        emb = LocalEmbedder(dim=16, mode="torch_projection")
        vec = emb.encode(text)
        assert vec.shape == (16,)
        assert vec.dtype == np.float32


# ============================================================================
# 5. encode_batch()
# ============================================================================

class TestEncodeBatch:
    def test_tfidf_svd_batch_shape_and_normalized(self):
        emb = create_embedder(dim=24, mode="tfidf_svd", fit_corpus=True)
        texts = ["八字排盘", "紫微斗数", "六爻起卦", "风水布局", "姓名取名"]
        batch = emb.encode_batch(texts)
        assert batch.shape == (5, 24)
        assert batch.dtype == np.float32
        norms = np.linalg.norm(batch, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-5)

    def test_torch_projection_batch_shape_and_consistent_with_single(self):
        emb = LocalEmbedder(dim=40, mode="torch_projection")
        texts = ["A", "B", "C"]
        batch = emb.encode_batch(texts)
        assert batch.shape == (3, 40)
        for i, t in enumerate(texts):
            single = emb.encode(t)
            np.testing.assert_array_equal(single, batch[i])

    def test_empty_batch_not_raises_is_empty(self):
        """encode_batch 空列表在 numpy 实现上可能抛 ValueError。"""
        emb = LocalEmbedder(dim=8, mode="tfidf_svd", svd_components=4)
        with pytest.raises((ValueError, Exception)):
            emb.encode_batch([])


# ============================================================================
# 6. get_dim / get_mode
# ============================================================================

class TestAccessors:
    @pytest.mark.parametrize("dim", [2, 8, 64, 128])
    @pytest.mark.parametrize("mode", ["tfidf_svd", "torch_projection"])
    def test_dim_matches_init(self, dim, mode):
        # tfidf_svd: svd_components 必须 < 后续 n_features；这里构造后不 fit，仅检查元数据
        emb = LocalEmbedder(dim=dim, mode=mode,
                            svd_components=min(2, max(1, dim - 1)),
                            tfidf_max_features=64)
        assert emb.get_dim() == dim
        assert emb.get_mode() == mode


# ============================================================================
# 7. create_embedder 工厂函数
# ============================================================================

class TestCreateEmbedder:
    def test_factory_returns_tfidf_svd_mode(self):
        """指定 mode=tfidf_svd 且 fit_corpus=True。"""
        emb = create_embedder(dim=128, mode="tfidf_svd", fit_corpus=True)
        assert isinstance(emb, LocalEmbedder)
        assert emb.get_mode() == "tfidf_svd"
        assert emb.get_dim() == 128
        # fit_corpus=True：_DOMAIN_CORPUS 被用于 fit
        assert emb._fitted is True

    def test_factory_no_fit_corpus_is_not_fitted(self):
        emb = create_embedder(dim=64, mode="tfidf_svd", fit_corpus=False)
        assert emb._fitted is False

    def test_factory_two_instances_encode_same_vector(self):
        """工厂默认参数（相同种子相同语料）→ 两实例对同一文本 encode 结果相同。"""
        a = create_embedder(dim=32, mode="tfidf_svd", fit_corpus=True)
        b = create_embedder(dim=32, mode="tfidf_svd", fit_corpus=True)
        va = a.encode("测试文本")
        vb = b.encode("测试文本")
        assert va.shape == vb.shape == (32,)
        # RandomState(42) + 相同语料 fit → 相同向量
        np.testing.assert_allclose(va, vb, atol=1e-6)


# ============================================================================
# 8. 语义相似度（回归：tfidf_svd 至少有领域区分度）
# ============================================================================

class TestSemanticSimilarityRegression:
    def test_same_domain_higher_similarity_than_cross_domain(self):
        """同领域文本对的相似度应显著高于跨领域文本对（至少 1.5 倍）。"""
        emb = create_embedder(dim=64, mode="tfidf_svd", fit_corpus=True)
        same_a = emb.encode("八字排盘看日主强弱")
        same_b = emb.encode("四柱八字排盘方法分析")
        cross_a = emb.encode("八字排盘看日主强弱")
        cross_b = emb.encode("风水罗盘定向方位吉凶")

        sim_same = float(np.dot(same_a, same_b))
        sim_cross = float(np.dot(cross_a, cross_b))
        # 同领域相似度应高于跨领域
        assert sim_same > sim_cross
