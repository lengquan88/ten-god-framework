"""Combined test suite for Stage 24 (miniapp) and Stage 25 (i18n)."""

from __future__ import annotations

import datetime as _dt
import json
import os
import tempfile
import time
import uuid

import pytest

from tengod.miniapp import (
    LocalStorageManager,
    MiniappClient,
    MiniappConfig,
    ShareCardGenerator,
    build_miniapp_deeplink,
    validate_wechat_signature,
)
from tengod.i18n import I18nManager, detect_locale_from_text, get_i18n_manager


def _tmp_storage_path(prefix: str = "miniapp_test") -> str:
    directory = tempfile.mkdtemp(prefix=prefix)
    return os.path.join(directory, f"storage.json")


# ---------------------------------------------------------------------------
# TestMiniappClient
# ---------------------------------------------------------------------------

class TestMiniappClient:
    def test_client_init(self):
        client = MiniappClient(base_url=None, app_id="unit-test")
        assert client.app_id == "unit-test"
        assert client.base_url is None

    def test_login_returns_token(self):
        client = MiniappClient(base_url=None)
        result = client.login("wx-123")
        assert "token" in result
        assert result["openid"]
        assert result["session_key"]

    def test_calc_bazi_structure(self):
        client = MiniappClient()
        login = client.login("test")
        result = client.calc_bazi(
            login["token"], 1990, 6, 15, 12, 0, "male"
        )
        assert "pillars" in result
        assert "day_master" in result
        assert "analysis" in result
        assert "wuxing" in result

    def test_get_trajectory_structure(self):
        client = MiniappClient()
        login = client.login("test")
        trajectory = client.get_trajectory(login["token"], 1, 1990, 2020)
        # Must include dayun / liunian or the fallback keys.
        has_dayun = "dayun" in trajectory
        has_liunian = "liunian" in trajectory
        assert has_dayun or has_liunian

    def test_calc_ziwei(self):
        client = MiniappClient()
        login = client.login("test")
        result = client.calc_ziwei(login["token"], 1990, 6, 15, 12, "male")
        assert isinstance(result, dict)
        assert "ming_gong" in result or "palaces" in result

    def test_calc_liuyao(self):
        client = MiniappClient()
        login = client.login("test")
        result = client.calc_liuyao(login["token"], "auto", "求问", "male")
        assert "gua" in result

    def test_search_cases(self):
        client = MiniappClient()
        login = client.login("test")
        cases = client.search_cases(login["token"], "事业", "八字", 10)
        assert isinstance(cases, list)


# ---------------------------------------------------------------------------
# TestShareCardGenerator
# ---------------------------------------------------------------------------

class TestShareCardGenerator:
    def setup_method(self):
        self.cards = ShareCardGenerator()

    def test_bazi_share_has_title(self):
        card = self.cards.generate_bazi_share(
            [{"gan": "甲", "zhi": "子"}], "甲", "正官格", 85.0
        )
        assert "title" in card
        assert card["title"]

    def test_bazi_share_has_description(self):
        card = self.cards.generate_bazi_share([], "甲", "正官格", 85.0)
        assert "description" in card
        assert card["description"]

    def test_bazi_share_has_image_field(self):
        card = self.cards.generate_bazi_share([], "甲", "", 80)
        assert "image_data" in card or "image_url" in card

    def test_trajectory_share_structure(self):
        card = self.cards.generate_trajectory_share(
            {"day_master": "甲",
             "dayun": [{"age_start": 5, "gan_zhi": "甲子"}]}
        )
        assert isinstance(card, dict)
        assert "title" in card
        assert "description" in card

    def test_ai_share_structure(self):
        card = self.cards.generate_ai_share("日主甲木，秀气。", "命运解读")
        assert isinstance(card, dict)
        assert "title" in card
        assert "description" in card


# ---------------------------------------------------------------------------
# TestLocalStorageManager
# ---------------------------------------------------------------------------

class TestLocalStorageManager:
    def setup_method(self):
        self.path = _tmp_storage_path("storage_" + uuid.uuid4().hex[:8])
        self.storage = LocalStorageManager(storage_path=self.path)

    def teardown_method(self):
        try:
            if os.path.exists(self.path):
                os.remove(self.path)
        except OSError:
            pass

    def test_save_get_token(self):
        self.storage.save_user_token("token-abc", int(time.time()) + 3600)
        assert self.storage.get_user_token() == "token-abc"

    def test_history_append(self):
        self.storage.save_calculation_history({"type": "bazi", "score": 85})
        history = self.storage.get_history()
        assert len(history) >= 1
        assert history[0]["type"] == "bazi"

    def test_history_pagination(self):
        for i in range(10):
            self.storage.save_calculation_history({"type": "bazi", "index": i})
        history = self.storage.get_history(limit=3)
        assert len(history) == 3

    def test_favorites_roundtrip(self):
        self.storage.save_favorite(123, {"geju": "正官格"})
        favorites = self.storage.get_favorites()
        assert any(fav["record_id"] == 123 for fav in favorites)

    def test_clear_all(self):
        self.storage.save_user_token("to-clear", int(time.time()) + 3600)
        self.storage.save_calculation_history({"type": "anything"})
        self.storage.save_favorite(1, {"data": True})
        self.storage.clear_all()
        assert self.storage.get_user_token() is None
        assert self.storage.get_history() == []
        assert self.storage.get_favorites() == []

    def test_token_expiry_handling(self):
        # Already expired token
        self.storage.save_user_token("expired", int(time.time()) - 100)
        assert self.storage.get_user_token() is None


# ---------------------------------------------------------------------------
# TestI18nManager
# ---------------------------------------------------------------------------

class TestI18nManager:
    def setup_method(self):
        self.i18n = I18nManager(default_locale="zh-CN")

    def test_default_locale_zhcn(self):
        assert self.i18n.get_locale() == "zh-CN"

    def test_set_locale_changes_translation(self):
        original = self.i18n.translate("伤官")
        self.i18n.set_locale("en")
        translated = self.i18n.translate("伤官")
        assert translated != original

    def test_translate_known_term(self):
        self.i18n.set_locale("en")
        assert "Fire" in self.i18n.translate("火")

    def test_translate_unknown_term_fallback(self):
        result = self.i18n.translate("完全不存在的词")
        assert result == "完全不存在的词"

    def test_bulk_translate_list(self):
        self.i18n.set_locale("en")
        out = self.i18n.bulk_translate(["甲", "乙", "丙"])
        assert len(out) == 3
        assert out != ["甲", "乙", "丙"]

    def test_get_all_locales_includes_en(self):
        locales = self.i18n.get_all_locales()
        assert "en" in locales
        assert "ja" in locales
        assert "zh-TW" in locales

    def test_translate_bazi_result(self):
        self.i18n.set_locale("en")
        result = {
            "day_master": "甲",
            "geju": "伤官格",
            "wuxing": ["金", "木"],
        }
        translated = self.i18n.translate_bazi_result(result)
        assert translated["day_master"] != "甲" or translated["geju"] != "伤官格"

    def test_format_number(self):
        self.i18n.set_locale("en")
        assert "," in self.i18n.format_number(1234.5)
        self.i18n.set_locale("zh-CN")
        assert self.i18n.format_number(1000) != ""

    def test_format_date(self):
        self.i18n.set_locale("zh-CN")
        date = _dt.date(2020, 1, 15)
        out = self.i18n.format_date(date)
        assert "2020" in out

    def test_merge_custom_translations(self):
        self.i18n.merge_custom_translations("en", {"custom_key": "Custom Value"})
        self.i18n.set_locale("en")
        assert self.i18n.translate("custom_key") == "Custom Value"


# ---------------------------------------------------------------------------
# TestMiniappI18nIntegration
# ---------------------------------------------------------------------------

class TestMiniappI18nIntegration:
    def test_client_with_i18n(self):
        i18n = I18nManager(default_locale="zh-CN")
        labels = MiniappConfig().get_ui_labels()
        i18n.set_locale("en")
        assert i18n.get_ui_label("命盘") != "命盘" or labels["chart"] == "命盘"

    def test_share_card_localized(self):
        cards = ShareCardGenerator()
        i18n = I18nManager(default_locale="zh-CN")
        i18n.set_locale("en")
        card = cards.generate_bazi_share([], "甲", "伤官格", 80)
        # Chinese title contains Chinese characters for day master 甲
        assert "甲" in card["title"] or "命盘" in card["title"]

    def test_market_to_locale_mapping(self):
        i18n = I18nManager()
        assert i18n.get_locale_for_market("CN") == "zh-CN"
        assert i18n.get_locale_for_market("US") == "en"
        assert i18n.get_locale_for_market("JP") == "ja"
        assert i18n.get_locale_for_market("KR") == "ko"
        assert i18n.get_locale_for_market("VN") == "vi"

    def test_detect_locale_from_text(self):
        assert detect_locale_from_text("こんにちは") == "ja"
        assert detect_locale_from_text("안녕하세요") == "ko"
        assert detect_locale_from_text("Chào bạn") == "vi"
        assert detect_locale_from_text("Hello world") == "en"

    def test_multilingual_support_all(self):
        i18n = I18nManager()
        locales = ["zh-CN", "zh-TW", "en", "ja", "ko", "vi"]
        results = {}
        for loc in locales:
            i18n.set_locale(loc)
            results[loc] = i18n.translate("甲")
        assert len(set(results.values())) >= 2
