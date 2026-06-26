#!/usr/bin/env python3
"""
test_v23_i18n.py — v2.3 国际化与移动端测试
覆盖：i18n 引擎、翻译功能、API 多语言、移动端轻量端点、分页
"""
import os
import sys
import json
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# ── v2.17.0: 将模块级 sys.modules 污染移到 autouse fixture 中 ──
# 原模块级代码 sys.modules['tengod.auth'] = MagicMock() 在 pytest 收集阶段
# 即污染全局状态，导致其他测试的 PasswordHasher.hash() 返回 MagicMock。
# 现在通过 fixture 设置 mock 并在测试结束后清理，不影响其他测试。

@pytest.fixture(autouse=True)
def _mock_tengod_modules_for_v23():
    """仅在本文件测试中 mock tengod.auth 和 metrics_collector，测试后恢复"""
    _orig_auth = sys.modules.get('tengod.auth')
    _orig_metrics = sys.modules.get('tengod.metrics_collector')

    mock_auth = MagicMock()
    mock_auth.authorize = MagicMock(return_value=None)
    mock_metrics = MagicMock()
    mock_metrics.metrics = MagicMock()

    sys.modules['tengod.auth'] = mock_auth
    sys.modules['tengod.metrics_collector'] = mock_metrics

    yield

    if _orig_auth is not None:
        sys.modules['tengod.auth'] = _orig_auth
    else:
        sys.modules.pop('tengod.auth', None)

    if _orig_metrics is not None:
        sys.modules['tengod.metrics_collector'] = _orig_metrics
    else:
        sys.modules.pop('tengod.metrics_collector', None)


# ════════════════════════════════════════
# 1. i18n 引擎基础测试
# ════════════════════════════════════════

class TestI18nEngine:
    """I18nEngine 核心功能"""

    def test_get_i18n_engine_singleton(self):
        from tengod.i18n import get_i18n_engine
        e1 = get_i18n_engine()
        e2 = get_i18n_engine()
        assert e1 is e2

    def test_default_lang_is_zh_cn(self):
        from tengod.i18n import get_i18n_engine, get_lang
        assert get_lang() == "zh-CN"
        assert get_i18n_engine().get_lang() == "zh-CN"

    def test_set_lang(self):
        from tengod.i18n import set_lang, get_lang, get_i18n_engine
        set_lang("en")
        assert get_lang() == "en"
        assert get_i18n_engine().get_lang() == "en"
        set_lang("zh-CN")  # 恢复

    def test_set_lang_invalid_fallback(self):
        from tengod.i18n import get_i18n_engine
        engine = get_i18n_engine()
        engine.set_lang("invalid-lang")
        assert engine.get_lang() == "zh-CN"

    def test_zh_cn_returns_original(self):
        from tengod.i18n import get_i18n_engine
        engine = get_i18n_engine()
        assert engine.translate("测试", "zh-CN") == "测试"

    def test_translate_to_english(self):
        from tengod.i18n import get_i18n_engine
        engine = get_i18n_engine()
        assert engine.translate("木", "en") == "Wood"
        assert engine.translate("甲", "en") == "Jia"

    def test_translate_to_taiwan(self):
        from tengod.i18n import get_i18n_engine
        engine = get_i18n_engine()
        assert engine.translate("丑", "zh-TW") == "醜"
        assert engine.translate("七杀", "zh-TW") == "七殺"

    def test_unknown_word_returns_original(self):
        from tengod.i18n import get_i18n_engine
        engine = get_i18n_engine()
        assert engine.translate("测试未知词", "en") == "测试未知词"

    def test_has_translation(self):
        from tengod.i18n import get_i18n_engine
        engine = get_i18n_engine()
        assert engine.has_translation("木", "en") is True
        assert engine.has_translation("不存在的词", "en") is False

    def test_add_custom_translation(self):
        from tengod.i18n import get_i18n_engine
        engine = get_i18n_engine()
        engine.add_custom("自定义词", {"en": "Custom Word"})
        assert engine.translate("自定义词", "en") == "Custom Word"

    def test_get_available_langs(self):
        from tengod.i18n import get_i18n_engine
        engine = get_i18n_engine()
        langs = engine.get_available_langs()
        assert len(langs) == 3
        assert [l["code"] for l in langs] == ["zh-CN", "zh-TW", "en"]


# ════════════════════════════════════════
# 2. 便捷函数测试
# ════════════════════════════════════════

class TestI18nHelpers:
    """便捷函数：translate_bazi、translate_wuxing、translate_shier"""

    def test_translate_bazi_pillars(self):
        from tengod.i18n import translate_bazi
        pillars = {"year": "甲子", "month": "丙寅"}
        result = translate_bazi(pillars, lang="en")
        assert "Jia" in result["year"]
        assert "Zi" in result["year"]
        assert "Bing" in result["month"]

    def test_translate_wuxing_counts(self):
        from tengod.i18n import translate_wuxing
        data = {"木": 3, "火": 2}
        result = translate_wuxing(data, lang="en")
        assert "Wood" in result
        assert result["Wood"] == 3
        assert "Fire" in result

    def test_translate_wuxing_strength(self):
        from tengod.i18n import translate_wuxing
        data = {"木": {"status": "旺", "strength": 100}}
        result = translate_wuxing(data, lang="en")
        assert "Wood" in result
        assert result["Wood"]["status"] == "Prosperous"
        assert result["Wood"]["strength"] == 100

    def test_translate_shier_single_char(self):
        from tengod.i18n import translate_shier
        result = translate_shier("子", lang="en")
        assert "Zi Hour" in result

    def test_translate_shier_full(self):
        from tengod.i18n import translate_shier
        result = translate_shier("子时", lang="en")
        assert "Zi Hour" in result

    def test_t_function(self):
        from tengod.i18n import t, set_lang
        set_lang("en")
        assert t("木") == "Wood"
        set_lang("zh-CN")

    def test_translate_dict(self):
        from tengod.i18n import get_i18n_engine
        engine = get_i18n_engine()
        data = {"element": "木", "status": "旺"}
        result = engine.translate_dict(data, lang="en")
        assert result["element"] == "Wood"
        assert result["status"] == "Prosperous"

    def test_translate_list_in_dict(self):
        from tengod.i18n import get_i18n_engine
        engine = get_i18n_engine()
        data = {"elements": ["木", "火"]}
        result = engine.translate_dict(data, lang="en")
        assert "Wood" in result["elements"]
        assert "Fire" in result["elements"]


# ════════════════════════════════════════
# 3. 翻译表完整性
# ════════════════════════════════════════

class TestTranslationCoverage:
    """翻译表覆盖率检查"""

    def test_tiangan_all_present(self):
        from tengod.i18n import TRANSLATIONS
        tiangan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        for g in tiangan:
            assert g in TRANSLATIONS, f"天干 {g} 未翻译"
            assert "en" in TRANSLATIONS[g]

    def test_dizhi_all_present(self):
        from tengod.i18n import TRANSLATIONS
        dizhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        for z in dizhi:
            assert z in TRANSLATIONS, f"地支 {z} 未翻译"

    def test_wuxing_all_present(self):
        from tengod.i18n import TRANSLATIONS
        wuxing = ["木", "火", "土", "金", "水"]
        for w in wuxing:
            assert w in TRANSLATIONS, f"五行 {w} 未翻译"

    def test_jieqi_all_present(self):
        from tengod.i18n import TRANSLATIONS
        jieqi = ["立春", "雨水", "惊蛰", "春分", "清明", "谷雨",
                 "立夏", "小满", "芒种", "夏至", "小暑", "大暑",
                 "立秋", "处暑", "白露", "秋分", "寒露", "霜降",
                 "立冬", "小雪", "大雪", "冬至", "小寒", "大寒"]
        for j in jieqi:
            assert j in TRANSLATIONS, f"节气 {j} 未翻译"

    def test_shishen_all_present(self):
        from tengod.i18n import TRANSLATIONS
        shishen = ["比肩", "劫财", "食神", "伤官", "偏财", "正财",
                   "七杀", "正官", "偏印", "正印"]
        for s in shishen:
            assert s in TRANSLATIONS, f"十神 {s} 未翻译"


# ════════════════════════════════════════
# 4. API 端点测试
# ════════════════════════════════════════

class TestI18nAPI:
    """i18n API 端点"""

    @pytest.mark.asyncio
    async def test_languages_endpoint(self, mock_auth):
        from tengod.api_server import v2_i18n_languages, Request
        mock_request = MagicMock(spec=Request)
        result = await v2_i18n_languages(mock_request)
        assert "languages" in result
        assert len(result["languages"]) == 3
        assert result["default"] == "zh-CN"

    @pytest.mark.asyncio
    async def test_translate_endpoint(self, mock_auth):
        from tengod.api_server import v2_i18n_translate, Request
        mock_request = MagicMock(spec=Request)

        async def mock_json():
            return {"texts": ["木", "火"], "lang": "en"}

        mock_request.json = mock_json
        result = await v2_i18n_translate(mock_request)
        assert result["lang"] == "en"
        assert result["translations"]["木"] == "Wood"
        assert result["translations"]["火"] == "Fire"

    @pytest.mark.asyncio
    async def test_knowledge_list_pagination(self, mock_auth):
        from tengod.api_server import v2_knowledge_list, Request
        from tengod.knowledge_fusion import get_fusion_engine, init_base_knowledge
        engine = get_fusion_engine()
        init_base_knowledge(engine)

        mock_request = MagicMock(spec=Request)
        result = await v2_knowledge_list(page=1, page_size=10, category=None,
                                         lang="zh-CN", request=mock_request)
        assert "items" in result
        assert "total" in result
        assert "page" in result
        assert result["page"] == 1
        assert result["page_size"] == 10
        assert result["total"] > 0

    @pytest.mark.asyncio
    async def test_knowledge_list_category_filter(self, mock_auth):
        from tengod.api_server import v2_knowledge_list, Request
        from tengod.knowledge_fusion import get_fusion_engine, init_base_knowledge
        engine = get_fusion_engine()
        init_base_knowledge(engine)

        mock_request = MagicMock(spec=Request)
        result = await v2_knowledge_list(page=1, page_size=20, category="element",
                                         lang="zh-CN", request=mock_request)
        assert result["total"] == 5  # 木火土金水

    @pytest.mark.asyncio
    async def test_knowledge_list_with_lang(self, mock_auth):
        from tengod.api_server import v2_knowledge_list, Request
        from tengod.knowledge_fusion import get_fusion_engine, init_base_knowledge
        engine = get_fusion_engine()
        init_base_knowledge(engine)

        mock_request = MagicMock(spec=Request)
        result = await v2_knowledge_list(page=1, page_size=5, category="element",
                                         lang="en", request=mock_request)
        names = [item["name"] for item in result["items"]]
        assert "Wood" in names


# ════════════════════════════════════════
# 5. 移动端轻量端点测试
# ════════════════════════════════════════

class TestMobileBaziQuick:
    """移动端轻量八字端点 /api/v2/mobile/bazi/quick"""

    @pytest.mark.asyncio
    async def test_quick_bazi_basic(self, mock_auth):
        """基础排盘：返回精简字段 p/d/w/t"""
        from tengod.api_server import v2_mobile_bazi_quick, Request
        mock_request = MagicMock(spec=Request)
        result = await v2_mobile_bazi_quick(
            request=mock_request, year=1990, month=6, day=15, hour=10,
        )
        assert "p" in result       # pillars
        assert "d" in result       # day_master
        assert "w" in result       # wuxing_count
        assert "t" in result       # total_score
        # 四柱齐全
        assert "year" in result["p"]
        assert "month" in result["p"]
        assert "day" in result["p"]
        assert "hour" in result["p"]

    @pytest.mark.asyncio
    async def test_quick_bazi_wuxing_count(self, mock_auth):
        """五行计数：五个元素且值为整数"""
        from tengod.api_server import v2_mobile_bazi_quick, Request
        mock_request = MagicMock(spec=Request)
        result = await v2_mobile_bazi_quick(
            request=mock_request, year=1990, month=6, day=15, hour=10,
        )
        assert len(result["w"]) == 5
        for val in result["w"].values():
            assert isinstance(val, int)

    @pytest.mark.asyncio
    async def test_quick_bazi_with_lang_en(self, mock_auth):
        """英文翻译：五行 key 应为英文"""
        from tengod.api_server import v2_mobile_bazi_quick, Request
        mock_request = MagicMock(spec=Request)
        result = await v2_mobile_bazi_quick(
            request=mock_request, year=1990, month=6, day=15, hour=10,
            lang="en",
        )
        assert "Wood" in result["w"] or "Fire" in result["w"]

    @pytest.mark.asyncio
    async def test_quick_bazi_female(self, mock_auth):
        """女性排盘：gender 参数生效"""
        from tengod.api_server import v2_mobile_bazi_quick, Request
        mock_request = MagicMock(spec=Request)
        result = await v2_mobile_bazi_quick(
            request=mock_request, year=1990, month=6, day=15, hour=10,
            gender="female",
        )
        assert "p" in result
        assert result["p"]["year"]  # 有年柱

    @pytest.mark.asyncio
    async def test_quick_bazi_custom_location(self, mock_auth):
        """自定义经纬度：不报错并返回结果"""
        from tengod.api_server import v2_mobile_bazi_quick, Request
        mock_request = MagicMock(spec=Request)
        result = await v2_mobile_bazi_quick(
            request=mock_request, year=1990, month=6, day=15, hour=10,
            longitude=121.5, latitude=31.2,
        )
        assert "p" in result


@pytest.fixture
def mock_auth():
    yield
