"""Comprehensive tests for tengod.miniapp module."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest

from tengod.miniapp import (
    LocalStorageManager,
    MiniappClient,
    MiniappConfig,
    ShareCardGenerator,
    build_miniapp_deeplink,
    validate_wechat_signature,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def storage():
    """Fixture that provides a LocalStorageManager backed by a temp file."""
    path = tempfile.mktemp(suffix=".json")
    mgr = LocalStorageManager(storage_path=path)
    yield mgr
    try:
        os.remove(path)
    except OSError:
        pass


# ===========================================================================
# MiniappClient
# ===========================================================================


class TestMiniappClientInit:
    """Tests for MiniappClient.__init__."""

    def test_init_with_defaults(self):
        client = MiniappClient()
        assert client.base_url is None
        assert client.app_id == "tengod-miniapp"
        assert client.app_secret == ""
        assert client.timeout == 10.0
        assert client._session == {}

    def test_init_with_custom_params(self):
        client = MiniappClient(
            base_url="https://api.example.com",
            app_id="my-app",
            app_secret="my-secret",
            timeout=5.0,
        )
        assert client.base_url == "https://api.example.com"
        assert client.app_id == "my-app"
        assert client.app_secret == "my-secret"
        assert client.timeout == 5.0


class TestMiniappClientLogin:
    """Tests for MiniappClient.login."""

    def test_login_local_mode_returns_openid_session_key_token(self):
        client = MiniappClient(base_url=None, app_id="test-app", app_secret="secret")
        result = client.login("wx-code-123", provider="wechat")
        assert "openid" in result
        assert "session_key" in result
        assert "token" in result
        assert result["provider"] == "wechat"
        assert "logged_at" in result
        # Verify session was saved internally
        assert client._session["openid"] == result["openid"]
        assert client._session["token"] == result["token"]

    def test_login_remote_mode_mocks_request(self):
        client = MiniappClient(base_url="https://api.example.com", app_id="test")
        with patch.object(client, "_request", return_value={
            "openid": "remote-openid",
            "session_key": "remote-key",
            "token": "remote-token",
            "provider": "wechat",
        }) as mock_req:
            result = client.login("code-456", provider="alipay")
            mock_req.assert_called_once_with(
                "POST", "/api/miniapp/login",
                {"code": "code-456", "provider": "alipay"},
            )
            assert result["openid"] == "remote-openid"


class TestMiniappClientGetUserProfile:
    """Tests for MiniappClient.get_user_profile."""

    def test_get_user_profile_local_mode(self):
        client = MiniappClient(base_url=None)
        result = client.get_user_profile("my-token")
        assert result["token"] == "my-token"
        assert result["nickname"] == "tengod_user"
        assert result["locale"] == "zh-CN"
        assert "created_at" in result
        assert result["preferences"]["theme"] == "light"

    def test_get_user_profile_remote_mode(self):
        client = MiniappClient(base_url="https://api.example.com")
        with patch.object(client, "_request", return_value={
            "token": "tok", "nickname": "remote_user", "locale": "en",
        }) as mock_req:
            result = client.get_user_profile("tok")
            mock_req.assert_called_once_with(
                "GET", "/api/user/profile", {"token": "tok"},
            )
            assert result["nickname"] == "remote_user"


class TestMiniappClientCalcBazi:
    """Tests for MiniappClient.calc_bazi."""

    def test_calc_bazi_local_mode_mocks_bazi_analyzer(self):
        client = MiniappClient(base_url=None)
        mock_pillar = MagicMock()
        mock_pillar.gan = "甲"
        mock_pillar.zhi = "子"
        mock_chart = MagicMock()
        mock_chart.pillars = [mock_pillar, mock_pillar, mock_pillar, mock_pillar]
        mock_analyzer = MagicMock()
        mock_analyzer.chart = mock_chart
        mock_analyzer.analysis = {
            "day_master": "甲木",
            "geju": {"geju_name": "正官格"},
            "wuxing": {"金": 30, "木": 40},
        }

        with patch("tengod.bazi_analyzer.BaziAnalyzer", return_value=mock_analyzer):
            result = client.calc_bazi("token", 1990, 6, 15, 12, 0, "male")
            assert "record_id" in result
            assert result["day_master"] == "甲木"
            assert result["geju"] == "正官格"
            assert "wuxing" in result
            assert len(result["pillars"]) == 4
            assert result["pillars"][0]["gan"] == "甲"
            assert result["pillars"][0]["zhi"] == "子"

    def test_calc_bazi_local_mode_analysis_without_geju_name(self):
        """When geju is not a dict, it should be stringified."""
        client = MiniappClient(base_url=None)
        mock_analyzer = MagicMock()
        mock_analyzer.chart = None
        mock_analyzer.analysis = {
            "day_master": "乙木",
            "geju": "伤官格",
            "wuxing": {},
        }

        with patch("tengod.bazi_analyzer.BaziAnalyzer", return_value=mock_analyzer):
            result = client.calc_bazi("token", 2000, 1, 1, 6, 0, "female")
            assert result["geju"] == "伤官格"

    def test_calc_bazi_local_mode_exception(self):
        client = MiniappClient(base_url=None)
        with patch("tengod.bazi_analyzer.BaziAnalyzer", side_effect=RuntimeError("Boom")):
            result = client.calc_bazi("token", 1990, 6, 15, 12, 0, "male")
            assert result["record_id"] == 0
            assert result["pillars"] == []
            assert result["day_master"] == ""
            assert result["geju"] == ""
            assert result["wuxing"] == {}
            assert "error" in result["analysis"]
            assert "Boom" in result["analysis"]["error"]

    def test_calc_bazi_remote_mode(self):
        client = MiniappClient(base_url="https://api.example.com")
        with patch.object(client, "_request", return_value={
            "record_id": 999, "day_master": "丙火", "geju": "正印格",
        }) as mock_req:
            result = client.calc_bazi("token", 1990, 6, 15, 12, 0, "male")
            mock_req.assert_called_once()
            assert result["record_id"] == 999


class TestMiniappClientGetTrajectory:
    """Tests for MiniappClient.get_trajectory."""

    def test_get_trajectory_local_mode(self):
        client = MiniappClient(base_url=None)
        mock_engine = MagicMock()
        mock_engine.destiny_trajectory.return_value = {
            "dayun": [{"age_start": 5, "gan_zhi": "甲子"}],
            "liunian": [],
        }
        with patch("tengod.advanced_analysis.AdvancedAnalyzer", return_value=mock_engine):
            result = client.get_trajectory("token", 1, 1990, 2020)
            assert "dayun" in result
            assert result["token"] == "token"
            assert result["record_id"] == 1
            assert result["start_year"] == 1990
            assert result["end_year"] == 2020

    def test_get_trajectory_remote_mode(self):
        client = MiniappClient(base_url="https://api.example.com")
        with patch.object(client, "_request", return_value={
            "dayun": [{"age_start": 10}], "liunian": [{"year": 2000}],
        }) as mock_req:
            result = client.get_trajectory("token", 2, 1990, 2020)
            mock_req.assert_called_once()
            assert result["dayun"][0]["age_start"] == 10


class TestMiniappClientCalcZiwei:
    """Tests for MiniappClient.calc_ziwei."""

    def test_calc_ziwei_local_mode(self):
        client = MiniappClient(base_url=None)
        mock_chart = MagicMock()
        mock_data = {
            "year_ganzhi": "庚午",
            "ming_gong": "寅",
            "palace_1": {"gan": "甲", "zhi": "子"},
        }
        with patch("tengod.ziwei_engine.calc_ziwei", return_value=mock_chart):
            with patch("tengod.ziwei_engine.ziwei_to_dict", return_value=mock_data):
                result = client.calc_ziwei("token", 1990, 6, 15, 12, "male")
                assert "palaces" in result
                assert result["year_ganzhi"] == "庚午"
                assert result["ming_gong"] == "寅"
                assert result["token"] == "token"

    def test_calc_ziwei_remote_mode(self):
        client = MiniappClient(base_url="https://api.example.com")
        with patch.object(client, "_request", return_value={
            "palaces": {}, "year_ganzhi": "庚午", "ming_gong": "寅",
        }) as mock_req:
            result = client.calc_ziwei("token", 1990, 6, 15, 12, "male")
            mock_req.assert_called_once()
            assert result["year_ganzhi"] == "庚午"


class TestMiniappClientCalcLiuyao:
    """Tests for MiniappClient.calc_liuyao."""

    def test_calc_liuyao_local_mode(self):
        client = MiniappClient(base_url=None)
        mock_result = MagicMock()
        mock_result.ben_gua = "坤为地"
        with patch("tengod.liuyao_engine.shake_and_calc", return_value=mock_result):
            result = client.calc_liuyao("token", "auto", "问财运", "male")
            assert result["method"] == "auto"
            assert result["question"] == "问财运"
            assert result["gua"] == "坤为地"
            assert len(result["lines"]) == 6
            assert result["token"] == "token"

    def test_calc_liuyao_local_mode_gua_name_fallback(self):
        """When ben_gua is empty, fall back to gua_name."""
        client = MiniappClient(base_url=None)
        mock_result = MagicMock()
        mock_result.ben_gua = ""
        mock_result.gua_name = "震为雷"
        with patch("tengod.liuyao_engine.shake_and_calc", return_value=mock_result):
            result = client.calc_liuyao("token", "manual", "问", "female")
            assert result["gua"] == "震为雷"

    def test_calc_liuyao_remote_mode(self):
        client = MiniappClient(base_url="https://api.example.com")
        with patch.object(client, "_request", return_value={
            "gua": "离为火", "lines": [],
        }) as mock_req:
            result = client.calc_liuyao("token", "auto", "问", "male")
            mock_req.assert_called_once()
            assert result["gua"] == "离为火"


class TestMiniappClientCalcQimen:
    """Tests for MiniappClient.calc_qimen."""

    def test_calc_qimen_local_mode(self):
        client = MiniappClient(base_url=None)
        mock_palace = MagicMock()
        mock_palace.gan = "戊"
        mock_palace.zhi = "子"
        mock_chart = MagicMock()
        mock_chart.palaces = [mock_palace] * 8
        with patch("tengod.qimen_engine.calc_qimen", return_value=mock_chart):
            result = client.calc_qimen("token", "问事", 2024, 1, 15, 10)
            assert result["question"] == "问事"
            assert "palaces" in result
            assert result["token"] == "token"
            assert "1" in result["palaces"]

    def test_calc_qimen_remote_mode(self):
        client = MiniappClient(base_url="https://api.example.com")
        with patch.object(client, "_request", return_value={
            "question": "问事", "palaces": {},
        }) as mock_req:
            result = client.calc_qimen("token", "问事", 2024, 1, 15, 10)
            mock_req.assert_called_once()
            assert result["question"] == "问事"


class TestMiniappClientSearchCases:
    """Tests for MiniappClient.search_cases."""

    def test_search_cases_local_mode(self):
        client = MiniappClient(base_url=None)
        cases = client.search_cases("token", "事业", "八字", 20)
        assert isinstance(cases, list)
        assert len(cases) <= 5  # local mode caps at 5
        assert cases[0]["id"] == 1000
        assert "事业" in cases[0]["title"]

    def test_search_cases_local_mode_limit_smaller_than_5(self):
        client = MiniappClient(base_url=None)
        cases = client.search_cases("token", "keyword", limit=2)
        assert len(cases) == 2

    def test_search_cases_remote_mode(self):
        client = MiniappClient(base_url="https://api.example.com")
        with patch.object(client, "_request", return_value={
            "cases": [{"id": 1, "title": "Test Case"}],
        }) as mock_req:
            cases = client.search_cases("token", "事业", "八字", 10)
            mock_req.assert_called_once()
            assert cases[0]["id"] == 1

    def test_search_cases_remote_returns_non_dict(self):
        client = MiniappClient(base_url="https://api.example.com")
        with patch.object(client, "_request", return_value="not a dict"):
            cases = client.search_cases("token", "事业")
            assert cases == []


class TestMiniappClientGetReport:
    """Tests for MiniappClient.get_report."""

    def test_get_report_local_mode(self):
        client = MiniappClient(base_url=None)
        report = client.get_report("token", 42, format="text")
        assert "命盘报告 #42" in report
        assert "格式: text" in report

    def test_get_report_remote_mode_dict_with_report_key(self):
        client = MiniappClient(base_url="https://api.example.com")
        with patch.object(client, "_request", return_value={
            "report": "远程报告内容",
        }) as mock_req:
            report = client.get_report("token", 42)
            mock_req.assert_called_once()
            assert report == "远程报告内容"

    def test_get_report_remote_mode_dict_without_report_key(self):
        client = MiniappClient(base_url="https://api.example.com")
        with patch.object(client, "_request", return_value={
            "data": "some data",
        }) as mock_req:
            report = client.get_report("token", 42)
            assert "data" in report

    def test_get_report_remote_mode_non_dict(self):
        client = MiniappClient(base_url="https://api.example.com")
        with patch.object(client, "_request", return_value="plain text report"):
            report = client.get_report("token", 42)
            assert report == "plain text report"


class TestMiniappClientGetShareImage:
    """Tests for MiniappClient.get_share_image."""

    def test_get_share_image_returns_base64_data_uri(self):
        client = MiniappClient()
        result = client.get_share_image("token", 123)
        assert result.startswith("data:image/png;base64,")
        # Decode and verify content
        encoded = result[len("data:image/png;base64,"):]
        decoded = json.loads(base64.b64decode(encoded).decode("utf-8"))
        assert decoded["record_id"] == 123
        assert decoded["token"] == "token"


class TestMiniappClientRequest:
    """Tests for MiniappClient._request."""

    def test_request_get_success(self):
        client = MiniappClient(base_url="https://api.example.com")
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status.return_value = None
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response
        with patch.dict("sys.modules", {"requests": mock_requests}):
            result = client._request("GET", "/api/test", {"key": "val"})
            mock_requests.get.assert_called_once_with(
                "https://api.example.com/api/test",
                params={"key": "val"},
                timeout=10.0,
            )
            assert result == {"status": "ok"}

    def test_request_post_success(self):
        client = MiniappClient(base_url="https://api.example.com", timeout=5.0)
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "done"}
        mock_response.raise_for_status.return_value = None
        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response
        with patch.dict("sys.modules", {"requests": mock_requests}):
            result = client._request("POST", "/api/action", {"data": 1})
            mock_requests.post.assert_called_once_with(
                "https://api.example.com/api/action",
                json={"data": 1},
                timeout=5.0,
            )
            assert result == {"result": "done"}

    def test_request_with_retry_fails_twice_then_succeeds(self):
        client = MiniappClient(base_url="https://api.example.com")
        fail_response = MagicMock()
        fail_response.json.return_value = {"finally": "ok"}
        fail_response.raise_for_status.return_value = None

        call_count = [0]

        def mock_get(url, params, timeout):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise ConnectionError("fail")
            return fail_response

        mock_requests = MagicMock()
        mock_requests.get.side_effect = mock_get
        with patch.dict("sys.modules", {"requests": mock_requests}):
            with patch("tengod.miniapp.time.sleep", return_value=None) as mock_sleep:
                result = client._request("GET", "/api/test")
                assert result == {"finally": "ok"}
                assert call_count[0] == 3
                assert mock_sleep.call_count == 2

    def test_request_all_retries_exhausted(self):
        client = MiniappClient(base_url="https://api.example.com")
        mock_requests = MagicMock()
        mock_requests.get.side_effect = ConnectionError("network error")
        with patch.dict("sys.modules", {"requests": mock_requests}):
            with patch("tengod.miniapp.time.sleep", return_value=None):
                result = client._request("GET", "/api/test")
                assert "error" in result
                assert "network error" in result["error"]
                assert result["url"] == "https://api.example.com/api/test"

    def test_request_json_decode_error_returns_raw_text(self):
        """When response.json() raises ValueError, returns raw text."""
        client = MiniappClient(base_url="https://api.example.com")
        mock_response = MagicMock()
        mock_response.text = "plain text response"
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("bad json")
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response
        with patch.dict("sys.modules", {"requests": mock_requests}):
            result = client._request("GET", "/api/test")
            assert result == {"raw": "plain text response"}


# ===========================================================================
# ShareCardGenerator
# ===========================================================================


class TestShareCardGeneratorTranslate:
    """Tests for ShareCardGenerator._t."""

    def test_t_with_i18n_available(self):
        cards = ShareCardGenerator()
        mock_t = MagicMock(return_value="translated")
        with patch("tengod.i18n.t", mock_t):
            result = cards._t("命盘", "zh-CN")
            mock_t.assert_called_once_with("命盘", "zh-CN")
            assert result == "translated"

    def test_t_with_i18n_unavailable(self):
        cards = ShareCardGenerator()
        with patch("tengod.i18n.t", side_effect=ImportError):
            result = cards._t("命盘", "zh-CN")
            assert result == "命盘"


class TestShareCardGeneratorBazi:
    """Tests for ShareCardGenerator.generate_bazi_share."""

    def test_generate_bazi_share_with_dict_pillars(self):
        cards = ShareCardGenerator()
        pillars = [
            {"gan": "甲", "zhi": "子"},
            {"gan": "乙", "zhi": "丑"},
            {"gan": "丙", "zhi": "寅"},
            {"gan": "丁", "zhi": "卯"},
        ]
        result = cards.generate_bazi_share(pillars, "甲木", "正官格", 82.5)
        assert "title" in result
        assert "甲木" in result["title"]
        assert "description" in result
        assert "82.5" in result["description"]
        assert "image_data" in result
        assert result["day_master"] == "甲木"
        assert result["geju"] == "正官格"
        assert result["score"] == 82.5

    def test_generate_bazi_share_with_stem_branch_keys(self):
        """Pillars using 'stem'/'branch' keys instead of 'gan'/'zhi'."""
        cards = ShareCardGenerator()
        pillars = [
            {"stem": "甲", "branch": "子"},
            {"stem": "乙", "branch": "丑"},
            {"stem": "丙", "branch": "寅"},
            {"stem": "丁", "branch": "卯"},
        ]
        result = cards.generate_bazi_share(pillars, "甲木", "正官格", 80.0)
        assert "甲子" in result["description"] or "甲子" in result.get("pillar_text", "")

    def test_generate_bazi_share_with_non_dict_pillars(self):
        cards = ShareCardGenerator()
        result = cards.generate_bazi_share("some string pillars", "甲木", "正官格", 80.0)
        assert "description" in result
        assert "some string pillars" in result["description"]

    def test_generate_bazi_share_with_empty_day_master(self):
        cards = ShareCardGenerator()
        result = cards.generate_bazi_share([], "", "正官格", 80.0)
        assert "命盘分析" in result["title"]

    def test_generate_bazi_share_with_non_numeric_score(self):
        cards = ShareCardGenerator()
        result = cards.generate_bazi_share([], "甲木", "正官格", "N/A")
        assert "description" in result
        assert result["score"] == "N/A"


class TestShareCardGeneratorTrajectory:
    """Tests for ShareCardGenerator.generate_trajectory_share."""

    def test_generate_trajectory_share_with_dict(self):
        cards = ShareCardGenerator()
        summary = {
            "day_master": "甲木",
            "dayun": [
                {"age_start": 5, "gan_zhi": "甲子"},
                {"age_start": 15, "gan_zhi": "乙丑"},
                {"age_start": 25, "gan_zhi": "丙寅"},
            ],
        }
        result = cards.generate_trajectory_share(summary)
        assert "甲木" in result["title"]
        assert "description" in result
        assert result["path"] == "/pages/share/trajectory"

    def test_generate_trajectory_share_with_non_dict(self):
        cards = ShareCardGenerator()
        result = cards.generate_trajectory_share("plain text summary")
        assert "命运轨迹" in result["title"]
        assert "plain text summary" in result["description"]


class TestShareCardGeneratorAI:
    """Tests for ShareCardGenerator.generate_ai_share."""

    def test_generate_ai_share_with_full_text(self):
        cards = ShareCardGenerator()
        result = cards.generate_ai_share(
            "日主甲木，生于春月，木气旺盛，宜行火运以泄秀气。",
            "命运解读",
        )
        assert result["title"] == "命运解读"
        assert "日主甲木" in result["description"]
        assert result["path"] == "/pages/share/ai"

    def test_generate_ai_share_with_empty_text(self):
        cards = ShareCardGenerator()
        result = cards.generate_ai_share("", "AI解读")
        assert "查看完整解读" in result["description"]

    def test_generate_ai_share_with_empty_first_line(self):
        cards = ShareCardGenerator()
        result = cards.generate_ai_share("some text", "")
        assert result["title"] == "AI 解读"


# ===========================================================================
# LocalStorageManager
# ===========================================================================


class TestLocalStorageManagerInit:
    """Tests for LocalStorageManager.__init__."""

    def test_init_with_default_path(self):
        mgr = LocalStorageManager()
        assert mgr.storage_path.endswith(".miniapp_storage.json")

    def test_init_with_custom_path(self, storage):
        assert storage.storage_path.endswith(".json")


class TestLocalStorageManagerEnsure:
    """Tests for LocalStorageManager._ensure."""

    def test_ensure_creates_file_with_defaults(self):
        path = tempfile.mktemp(suffix=".json")
        try:
            mgr = LocalStorageManager(storage_path=path)
            assert os.path.exists(path)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["token"] is None
            assert data["token_expires_at"] == 0
            assert data["history"] == []
            assert data["favorites"] == {}
        finally:
            try:
                os.remove(path)
            except OSError:
                pass


class TestLocalStorageManagerRead:
    """Tests for LocalStorageManager._read."""

    def test_read_with_existing_file(self, storage):
        storage.save_user_token("test-token", int(time.time()) + 3600)
        data = storage._read()
        assert data["token"] == "test-token"

    def test_read_with_corrupted_file(self, storage):
        # Write corrupted JSON
        with open(storage.storage_path, "w", encoding="utf-8") as f:
            f.write("not valid json {{{")
        data = storage._read()
        assert data["token"] is None
        assert data["history"] == []
        assert data["favorites"] == {}


class TestLocalStorageManagerToken:
    """Tests for token save/get."""

    def test_save_user_token_and_get_user_token(self, storage):
        future = int(time.time()) + 7200
        storage.save_user_token("my-token", future)
        assert storage.get_user_token() == "my-token"

    def test_get_user_token_with_expired_token(self, storage):
        past = int(time.time()) - 1000
        storage.save_user_token("expired-token", past)
        assert storage.get_user_token() is None

    def test_get_user_token_with_no_token(self, storage):
        assert storage.get_user_token() is None


class TestLocalStorageManagerHistory:
    """Tests for save_calculation_history and get_history."""

    def test_save_calculation_history_adds_item(self, storage):
        storage.save_calculation_history({"type": "bazi", "score": 85})
        history = storage.get_history()
        assert len(history) >= 1
        assert history[0]["type"] == "bazi"

    def test_get_history_returns_most_recent_first(self, storage):
        storage.save_calculation_history({"type": "first", "index": 0})
        time.sleep(0.01)
        storage.save_calculation_history({"type": "second", "index": 1})
        history = storage.get_history()
        assert history[0]["type"] == "second"
        assert history[1]["type"] == "first"

    def test_get_history_respects_default_limit(self, storage):
        for i in range(30):
            storage.save_calculation_history({"type": "item", "index": i})
        history = storage.get_history()
        assert len(history) == 20  # default limit

    def test_get_history_with_custom_limit(self, storage):
        for i in range(10):
            storage.save_calculation_history({"type": "item", "index": i})
        history = storage.get_history(limit=5)
        assert len(history) == 5

    def test_history_bounded_to_200_items(self, storage):
        for i in range(250):
            storage.save_calculation_history({"type": "item", "index": i})
        data = storage._read()
        assert len(data["history"]) == 200


class TestLocalStorageManagerFavorites:
    """Tests for save_favorite and get_favorites."""

    def test_save_favorite_adds_item(self, storage):
        storage.save_favorite(42, {"geju": "正官格", "score": 90})
        favs = storage.get_favorites()
        assert len(favs) == 1
        assert favs[0]["record_id"] == 42

    def test_get_favorites_returns_list(self, storage):
        favs = storage.get_favorites()
        assert isinstance(favs, list)
        assert favs == []


class TestLocalStorageManagerClearAll:
    """Tests for clear_all."""

    def test_clear_all_resets_to_defaults(self, storage):
        storage.save_user_token("to-clear", int(time.time()) + 3600)
        storage.save_calculation_history({"type": "test"})
        storage.save_favorite(1, {"data": True})
        storage.clear_all()
        assert storage.get_user_token() is None
        assert storage.get_history() == []
        assert storage.get_favorites() == []


# ===========================================================================
# MiniappConfig
# ===========================================================================


class TestMiniappConfig:
    """Tests for MiniappConfig."""

    def test_theme_config_light(self):
        config = MiniappConfig()
        theme = config.theme_config("light")
        assert theme["primary"] == "#C9A96E"
        assert theme["background"] == "#FBF7EF"
        assert theme["text"] == "#2A2118"
        assert theme["accent"] == "#8B5E3C"

    def test_theme_config_dark(self):
        config = MiniappConfig()
        theme = config.theme_config("dark")
        assert theme["primary"] == "#E8C88E"
        assert theme["background"] == "#1E1A16"
        assert theme["text"] == "#F3E9D7"
        assert theme["accent"] == "#C49A6C"

    def test_theme_config_invalid_name_defaults_to_light(self):
        config = MiniappConfig()
        theme = config.theme_config("nonexistent")
        assert theme["primary"] == "#C9A96E"
        assert theme["background"] == "#FBF7EF"

    def test_feature_flags_returns_all_features(self):
        config = MiniappConfig()
        flags = config.feature_flags()
        assert flags["bazi"] is True
        assert flags["ziwei"] is True
        assert flags["liuyao"] is True
        assert flags["qimen"] is True
        assert flags["trajectory"] is True
        assert flags["report"] is True
        assert flags["share"] is True
        assert flags["ai_interpretation"] is True
        assert flags["case_search"] is True

    def test_get_ui_labels_returns_all_labels(self):
        config = MiniappConfig()
        labels = config.get_ui_labels()
        assert labels["chart"] == "命盘"
        assert labels["arrange"] == "排盘"
        assert labels["analyze"] == "分析"
        assert labels["report"] == "报告"
        assert labels["dayun"] == "大运"
        assert labels["liunian"] == "流年"
        assert labels["day_zhu"] == "日柱"
        assert labels["day_master"] == "日主"
        assert labels["year_zhu"] == "年柱"
        assert labels["month_zhu"] == "月柱"
        assert labels["hour_zhu"] == "时柱"
        assert labels["gender_male"] == "男"
        assert labels["gender_female"] == "女"
        assert labels["wuxing"] == "五行"
        assert labels["shishen"] == "十神"
        assert labels["geju"] == "格局"
        assert labels["shengxiao"] == "生肖"
        assert labels["login"] == "登录"
        assert labels["share"] == "分享"


# ===========================================================================
# Helpers
# ===========================================================================


class TestValidateWechatSignature:
    """Tests for validate_wechat_signature."""

    def test_valid_signature(self):
        token = "test-token"
        timestamp = "1234567890"
        nonce = "abc123"
        items = sorted([token, timestamp, nonce])
        expected = hashlib.sha1("".join(items).encode("utf-8")).hexdigest()
        assert validate_wechat_signature(timestamp, nonce, expected, token) is True

    def test_invalid_signature(self):
        assert validate_wechat_signature(
            "1234567890", "abc123", "wrong-signature", "test-token"
        ) is False

    def test_with_empty_params(self):
        assert validate_wechat_signature("", "nonce", "sig", "token") is False
        assert validate_wechat_signature("ts", "", "sig", "token") is False
        assert validate_wechat_signature("ts", "nonce", "", "token") is False
        assert validate_wechat_signature("ts", "nonce", "sig", "") is False


class TestBuildMiniappDeeplink:
    """Tests for build_miniapp_deeplink."""

    def test_with_no_params(self):
        result = build_miniapp_deeplink("pages/index/index")
        assert result == "pages/index/index"

    def test_with_params(self):
        result = build_miniapp_deeplink("pages/detail/detail", {"id": "123", "type": "bazi"})
        assert "id=123" in result
        assert "type=bazi" in result
        assert result.startswith("pages/detail/detail?")

    def test_with_none_values_filtered(self):
        result = build_miniapp_deeplink("pages/home/home", {"a": "1", "b": None, "c": "3"})
        assert "a=1" in result
        assert "c=3" in result
        assert "b=" not in result

    def test_with_empty_dict(self):
        result = build_miniapp_deeplink("pages/index/index", {})
        assert result == "pages/index/index"