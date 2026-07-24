"""
Tests for tengod.advanced_analysis — AdvancedAnalyzer module.

Covers:
  - compare_cases pipeline
  - batch_bazi pipeline
  - destiny_trajectory pipeline
  - All private helper methods
  - Edge cases: empty inputs, invalid data, extreme values
"""
import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from tengod.advanced_analysis import AdvancedAnalyzer, __version__


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_mock_record(record_id, year=1990, month=6, day=15, hour=10,
                      gender="male", analysis_json=None, geju_json=None):
    """Create a mock BaziRecord with the given fields."""
    record = MagicMock()
    record.id = record_id
    record.year = year
    record.month = month
    record.day = day
    record.hour = hour
    record.gender = gender
    record.analysis_json = analysis_json
    record.geju_json = geju_json
    return record


def _make_mock_store(records_by_id=None):
    """Create a mock DataStore that returns records from a dict."""
    store = MagicMock()
    if records_by_id is None:
        records_by_id = {}

    def _session_ctx():
        # _session() is used as a context manager returning a session
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=False)

        def query_side_effect(model):
            query_mock = MagicMock()
            query_mock.filter_by.return_value = query_mock

            def first_side_effect():
                # Extract the id from the filter_by call
                call_args = query_mock.filter_by.call_args
                if call_args:
                    record_id = call_args[1].get("id")
                    return records_by_id.get(record_id)
                return None

            query_mock.first = first_side_effect
            return query_mock

        session.query = query_side_effect
        return session

    store._session = _session_ctx
    return store


def _make_mock_bazi_analyzer(day_master="甲", wuxing=None, geju=None,
                             pillars=None, shigan=None):
    """Create a mock BaziAnalyzer instance."""
    if wuxing is None:
        wuxing = {"木": 3, "火": 1, "土": 1, "金": 1, "水": 2}
    if geju is None:
        geju = {"geju_name": "正官格"}
    if pillars is None:
        pillars = {
            "year": "甲子", "month": "乙丑", "day": "丙寅", "hour": "丁卯",
        }
    if shigan is None:
        shigan = {"比肩": 2, "食神": 1, "正财": 1}

    mock = MagicMock()
    mock.chart = MagicMock()
    mock.chart.pillars = pillars
    mock.analysis = {
        "day_master": day_master,
        "wuxing": wuxing,
        "geju": geju,
        "shigan": shigan,
    }
    return mock


# ---------------------------------------------------------------------------
# Test: __init__ / __version__
# ---------------------------------------------------------------------------

class TestInit:
    def test_default_store(self):
        with patch("tengod.advanced_analysis.get_data_store") as mock_get:
            analyzer = AdvancedAnalyzer()
            mock_get.assert_called_once()
            assert analyzer._store is mock_get.return_value

    def test_custom_store(self):
        store = MagicMock()
        analyzer = AdvancedAnalyzer(store=store)
        assert analyzer._store is store

    def test_version(self):
        assert __version__ == "1.0.0"


# ---------------------------------------------------------------------------
# Test: compare_cases (public pipeline)
# ---------------------------------------------------------------------------

class TestCompareCases:
    """Tests for the compare_cases public method."""

    def test_compare_success(self):
        analysis_a = {
            "day_master": "甲", "wuxing": {"木": 3, "火": 1, "土": 1, "金": 1, "水": 2},
            "shigan": {"比肩": 2, "食神": 1, "正财": 1},
        }
        analysis_b = {
            "day_master": "丙", "wuxing": {"木": 1, "火": 3, "土": 1, "金": 1, "水": 2},
            "shigan": {"七杀": 2, "偏印": 1, "正官": 1},
        }

        record_a = _make_mock_record(1, analysis_json=json.dumps(analysis_a),
                                     geju_json=json.dumps({"geju_name": "正官格"}))
        record_b = _make_mock_record(2, analysis_json=json.dumps(analysis_b),
                                     geju_json=json.dumps({"geju_name": "食神格"}))
        store = _make_mock_store({1: record_a, 2: record_b})
        analyzer = AdvancedAnalyzer(store=store)

        result = analyzer.compare_cases(1, 2)

        assert "error" not in result
        assert result["record_a"]["id"] == 1
        assert result["record_b"]["id"] == 2
        assert result["record_a"]["day_master"] == "甲"
        assert result["record_b"]["day_master"] == "丙"
        assert result["record_a"]["geju"] == "正官格"
        assert result["record_b"]["geju"] == "食神格"
        assert "wuxing_compare" in result
        assert "shigan_compare" in result
        assert "similarity_score" in result
        assert "summary" in result
        assert isinstance(result["similarity_score"], float)
        assert 0 <= result["similarity_score"] <= 100

    def test_record_a_not_found(self):
        record_b = _make_mock_record(2, analysis_json=json.dumps({"day_master": "丙"}),
                                     geju_json=json.dumps({"geju_name": "食神格"}))
        store = _make_mock_store({2: record_b})
        analyzer = AdvancedAnalyzer(store=store)

        result = analyzer.compare_cases(999, 2)
        assert "error" in result
        assert "命例A" in result["error"]

    def test_record_b_not_found(self):
        record_a = _make_mock_record(1, analysis_json=json.dumps({"day_master": "甲"}),
                                     geju_json=json.dumps({"geju_name": "正官格"}))
        store = _make_mock_store({1: record_a})
        analyzer = AdvancedAnalyzer(store=store)

        result = analyzer.compare_cases(1, 999)
        assert "error" in result
        assert "命例B" in result["error"]

    def test_compare_same_geju(self):
        analysis_a = {"day_master": "甲", "wuxing": {"木": 3, "火": 1},
                      "shigan": {"比肩": 2}}
        analysis_b = {"day_master": "乙", "wuxing": {"木": 2, "火": 2},
                      "shigan": {"比肩": 1, "食神": 3}}
        record_a = _make_mock_record(1, analysis_json=json.dumps(analysis_a),
                                     geju_json=json.dumps({"geju_name": "正官格"}))
        record_b = _make_mock_record(2, analysis_json=json.dumps(analysis_b),
                                     geju_json=json.dumps({"geju_name": "正官格"}))
        store = _make_mock_store({1: record_a, 2: record_b})
        analyzer = AdvancedAnalyzer(store=store)

        result = analyzer.compare_cases(1, 2)
        assert result["geju_same"] is True

    def test_compare_same_day_master(self):
        analysis_a = {"day_master": "甲", "wuxing": {"木": 3},
                      "shigan": {"比肩": 2}}
        analysis_b = {"day_master": "甲", "wuxing": {"木": 2},
                      "shigan": {"比肩": 1}}
        record_a = _make_mock_record(1, analysis_json=json.dumps(analysis_a),
                                     geju_json=json.dumps({"geju_name": "正官格"}))
        record_b = _make_mock_record(2, analysis_json=json.dumps(analysis_b),
                                     geju_json=json.dumps({"geju_name": "食神格"}))
        store = _make_mock_store({1: record_a, 2: record_b})
        analyzer = AdvancedAnalyzer(store=store)

        result = analyzer.compare_cases(1, 2)
        assert result["day_master_same"] is True

    def test_compare_empty_analysis(self):
        record_a = _make_mock_record(1, analysis_json=None, geju_json=None)
        record_b = _make_mock_record(2, analysis_json=None, geju_json=None)
        store = _make_mock_store({1: record_a, 2: record_b})
        analyzer = AdvancedAnalyzer(store=store)

        result = analyzer.compare_cases(1, 2)
        assert "error" not in result
        assert result["day_master_same"] is False
        assert result["geju_same"] is False
        assert result["similarity_score"] == 0.0

    def test_compare_corrupted_analysis_json(self):
        analysis_a = {"day_master": "甲", "wuxing": {"木": 3}, "shigan": {}}
        record_a = _make_mock_record(1, analysis_json=json.dumps(analysis_a),
                                     geju_json=json.dumps({"geju_name": "正官格"}))
        record_b = _make_mock_record(2, analysis_json="not valid json{{{",
                                     geju_json="also bad{{{")
        store = _make_mock_store({1: record_a, 2: record_b})
        analyzer = AdvancedAnalyzer(store=store)

        result = analyzer.compare_cases(1, 2)
        assert "error" not in result
        # corrupted JSON → empty dicts → no day_master
        assert result["record_b"]["day_master"] == ""


# ---------------------------------------------------------------------------
# Test: _compare_wuxing
# ---------------------------------------------------------------------------

class TestCompareWuxing:
    def test_basic_comparison(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        wa = {"木": 3, "火": 1, "土": 1, "金": 1, "水": 2}
        wb = {"木": 1, "火": 3, "土": 1, "金": 1, "水": 2}

        result = analyzer._compare_wuxing(wa, wb)

        assert result["a"] == wa
        assert result["b"] == wb
        assert result["dominant_a"] == "木"
        assert result["dominant_b"] == "火"
        assert result["diff"]["木"] == {"a": 3, "b": 1, "diff": 2}
        assert result["diff"]["火"] == {"a": 1, "b": 3, "diff": -2}

    def test_empty_wuxing(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._compare_wuxing({}, {})
        assert result["a"] == {}
        assert result["b"] == {}
        assert result["diff"] == {}
        assert result["dominant_a"] is None
        assert result["dominant_b"] is None

    def test_partial_wuxing(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        wa = {"木": 3, "火": 1}
        wb = {"金": 2, "水": 4}

        result = analyzer._compare_wuxing(wa, wb)

        assert result["diff"]["木"] == {"a": 3, "b": 0, "diff": 3}
        assert result["diff"]["金"] == {"a": 0, "b": 2, "diff": -2}
        assert result["dominant_a"] == "木"
        assert result["dominant_b"] == "水"


# ---------------------------------------------------------------------------
# Test: _compare_shigan
# ---------------------------------------------------------------------------

class TestCompareShigan:
    def test_basic_comparison(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        sa = {"比肩": 2, "食神": 1, "正财": 1}
        sb = {"七杀": 2, "偏印": 1, "正官": 1}

        result = analyzer._compare_shigan(sa, sb)

        assert result["比肩"] == {"a": 2, "b": 0}
        assert result["七杀"] == {"a": 0, "b": 2}
        assert result["食神"] == {"a": 1, "b": 0}

    def test_empty_shigan(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._compare_shigan({}, {})
        assert result == {}

    def test_overlapping_shigan(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        sa = {"比肩": 2, "食神": 1}
        sb = {"比肩": 1, "正财": 3}

        result = analyzer._compare_shigan(sa, sb)
        assert result["比肩"] == {"a": 2, "b": 1}
        assert result["食神"] == {"a": 1, "b": 0}
        assert result["正财"] == {"a": 0, "b": 3}


# ---------------------------------------------------------------------------
# Test: _calc_similarity
# ---------------------------------------------------------------------------

class TestCalcSimilarity:
    def test_identical(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        wa = {"木": 3, "火": 1, "土": 1, "金": 1, "水": 2}
        wb = {"木": 3, "火": 1, "土": 1, "金": 1, "水": 2}

        score = analyzer._calc_similarity(wa, wb, "甲", "甲", "正官格", "正官格")
        assert score == 100.0

    def test_different_geju_same_dm(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        wa = {"木": 3, "火": 1, "土": 1, "金": 1, "水": 2}
        wb = {"木": 3, "火": 1, "土": 1, "金": 1, "水": 2}

        score = analyzer._calc_similarity(wa, wb, "甲", "甲", "正官格", "食神格")
        # 30 (dm) + 30 (cosine=1.0) = 60
        assert score == 60.0

    def test_all_different_zero_wuxing(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        wa = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        wb = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}

        score = analyzer._calc_similarity(wa, wb, "甲", "丙", "正官格", "食神格")
        # dm diff + geju diff + zero norm → cosine=0
        assert score == 0.0

    def test_partial_wuxing(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        wa = {"木": 3}
        wb = {"木": 3}

        score = analyzer._calc_similarity(wa, wb, "甲", "甲", "正官格", "正官格")
        assert score == 100.0

    def test_extreme_opposite(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        wa = {"木": 5, "火": 0, "土": 0, "金": 0, "水": 0}
        wb = {"木": 0, "火": 0, "土": 0, "金": 5, "水": 0}

        score = analyzer._calc_similarity(wa, wb, "甲", "辛", "正官格", "七杀格")
        # dm diff, geju diff, cosine=0 → 0
        assert score == 0.0

    def test_caps_at_100(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        wa = {"木": 10, "火": 10, "土": 10, "金": 10, "水": 10}
        wb = {"木": 10, "火": 10, "土": 10, "金": 10, "水": 10}

        score = analyzer._calc_similarity(wa, wb, "甲", "甲", "正官格", "正官格")
        # 30 + 40 + 30 = 100, capped
        assert score == 100.0


# ---------------------------------------------------------------------------
# Test: _compare_summary
# ---------------------------------------------------------------------------

class TestCompareSummary:
    def test_high_similarity_same(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        summary = analyzer._compare_summary("甲", "甲", "正官格", "正官格", 85.0)
        assert "同为" in summary
        assert "相似度较高" in summary

    def test_medium_similarity(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        summary = analyzer._compare_summary("甲", "丙", "正官格", "食神格", 55.0)
        assert "分别为" in summary
        assert "相似度中等" in summary

    def test_low_similarity(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        summary = analyzer._compare_summary("甲", "丙", "正官格", "食神格", 20.0)
        assert "相似度较低" in summary

    def test_empty_dm_and_geju(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        summary = analyzer._compare_summary("", "", "", "", 10.0)
        assert "相似度较低" in summary
        assert summary.endswith("。")


# ---------------------------------------------------------------------------
# Test: batch_bazi (public pipeline)
# ---------------------------------------------------------------------------

class TestBatchBazi:
    def test_batch_success(self):
        mock_analyzer = _make_mock_bazi_analyzer()
        with patch("tengod.advanced_analysis.BaziAnalyzer", return_value=mock_analyzer):
            analyzer = AdvancedAnalyzer(store=MagicMock())
            inputs = [
                {"year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male"},
                {"year": 1985, "month": 3, "day": 20, "hour": 14, "gender": "female"},
            ]
            result = analyzer.batch_bazi(inputs)

        assert result["stats"]["total"] == 2
        assert result["stats"]["success"] == 2
        assert result["stats"]["failed"] == 0
        assert len(result["results"]) == 2
        for r in result["results"]:
            assert r["success"] is True
            assert r["day_master"] == "甲"
            assert r["geju"] == "正官格"

    def test_batch_partial_failure(self):
        good_analyzer = _make_mock_bazi_analyzer()
        def mock_bazi_side_effect(**kwargs):
            if kwargs["year"] == 9999:
                raise ValueError("Invalid year")
            return good_analyzer

        with patch("tengod.advanced_analysis.BaziAnalyzer",
                   side_effect=mock_bazi_side_effect):
            analyzer = AdvancedAnalyzer(store=MagicMock())
            inputs = [
                {"year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male"},
                {"year": 9999, "month": 1, "day": 1, "hour": 0, "gender": "male"},
            ]
            result = analyzer.batch_bazi(inputs)

        assert result["stats"]["total"] == 2
        assert result["stats"]["success"] == 1
        assert result["stats"]["failed"] == 1
        assert result["results"][0]["success"] is True
        assert result["results"][1]["success"] is False
        assert "error" in result["results"][1]

    def test_batch_empty_input(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer.batch_bazi([])
        assert result["stats"]["total"] == 0
        assert result["stats"]["success"] == 0
        assert result["results"] == []

    def test_batch_default_hour_minute(self):
        mock_analyzer = _make_mock_bazi_analyzer()
        with patch("tengod.advanced_analysis.BaziAnalyzer",
                   return_value=mock_analyzer) as mock_cls:
            analyzer = AdvancedAnalyzer(store=MagicMock())
            inputs = [{"year": 1990, "month": 6, "day": 15}]
            result = analyzer.batch_bazi(inputs)

        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["hour"] == 12
        assert call_kwargs["minute"] == 0
        assert result["stats"]["success"] == 1

    def test_batch_geju_string(self):
        """Test when geju is returned as a string, not a dict."""
        mock = _make_mock_bazi_analyzer()
        mock.analysis["geju"] = "正官格"  # plain string
        with patch("tengod.advanced_analysis.BaziAnalyzer", return_value=mock):
            analyzer = AdvancedAnalyzer(store=MagicMock())
            inputs = [{"year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male"}]
            result = analyzer.batch_bazi(inputs)
        assert result["results"][0]["geju"] == "正官格"

    def test_batch_geju_none(self):
        """Test when geju is not a dict and not a string."""
        mock = _make_mock_bazi_analyzer()
        mock.analysis["geju"] = None
        with patch("tengod.advanced_analysis.BaziAnalyzer", return_value=mock):
            analyzer = AdvancedAnalyzer(store=MagicMock())
            inputs = [{"year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male"}]
            result = analyzer.batch_bazi(inputs)
        assert result["results"][0]["geju"] is None

    def test_batch_stats_day_masters(self):
        mock1 = _make_mock_bazi_analyzer(day_master="甲", wuxing={"木": 3, "火": 1})
        mock2 = _make_mock_bazi_analyzer(day_master="丙", wuxing={"火": 3, "土": 1})
        mock3 = _make_mock_bazi_analyzer(day_master="甲", wuxing={"木": 2, "水": 2})

        call_count = [0]
        mocks = [mock1, mock2, mock3]
        def side_effect(**kwargs):
            m = mocks[call_count[0]]
            call_count[0] += 1
            return m

        with patch("tengod.advanced_analysis.BaziAnalyzer", side_effect=side_effect):
            analyzer = AdvancedAnalyzer(store=MagicMock())
            inputs = [
                {"year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male"},
                {"year": 1985, "month": 3, "day": 20, "hour": 14, "gender": "female"},
                {"year": 2000, "month": 1, "day": 1, "hour": 8, "gender": "male"},
            ]
            result = analyzer.batch_bazi(inputs)

        assert result["stats"]["day_masters"] == {"甲": 2, "丙": 1}
        assert result["stats"]["gejus"] == {"正官格": 3}
        assert result["stats"]["wuxing_totals"]["木"] == 5
        assert result["stats"]["wuxing_totals"]["火"] == 4


# ---------------------------------------------------------------------------
# Test: destiny_trajectory (public pipeline)
# ---------------------------------------------------------------------------

class TestDestinyTrajectory:
    def test_full_trajectory(self):
        mock_analyzer = _make_mock_bazi_analyzer(day_master="甲")
        with patch("tengod.advanced_analysis.BaziAnalyzer",
                   return_value=mock_analyzer):
            analyzer = AdvancedAnalyzer(store=MagicMock())
            result = analyzer.destiny_trajectory(
                year=1990, month=6, day=15, hour=10, gender="male",
                start_age=0, end_age=80,
            )

        assert "birth" in result
        assert result["birth"]["year"] == 1990
        assert result["day_master"] == "甲"
        assert "wuxing" in result
        assert "dayun" in result
        assert "liunian" in result
        assert "life_stages" in result
        assert "summary" in result
        assert len(result["dayun"]) > 0
        assert len(result["liunian"]) > 0

    def test_female_gender(self):
        mock_analyzer = _make_mock_bazi_analyzer(day_master="甲")
        with patch("tengod.advanced_analysis.BaziAnalyzer",
                   return_value=mock_analyzer) as mock_cls:
            analyzer = AdvancedAnalyzer(store=MagicMock())
            analyzer.destiny_trajectory(
                year=1990, month=6, day=15, hour=10, gender="female",
            )
        assert mock_cls.call_args[1]["is_male"] is False

    def test_custom_age_range(self):
        mock_analyzer = _make_mock_bazi_analyzer(day_master="甲")
        with patch("tengod.advanced_analysis.BaziAnalyzer",
                   return_value=mock_analyzer):
            analyzer = AdvancedAnalyzer(store=MagicMock())
            result = analyzer.destiny_trajectory(
                year=1990, month=6, day=15, hour=10, gender="male",
                start_age=30, end_age=50,
            )
        # dayun should start at or after 30
        assert all(du["age_start"] <= 50 for du in result["dayun"])
        # liunian should be within [30, 50]
        for ln in result["liunian"]:
            assert 30 <= ln["age"] <= 50

    def test_default_minute(self):
        mock_analyzer = _make_mock_bazi_analyzer(day_master="甲")
        with patch("tengod.advanced_analysis.BaziAnalyzer",
                   return_value=mock_analyzer) as mock_cls:
            analyzer = AdvancedAnalyzer(store=MagicMock())
            analyzer.destiny_trajectory(
                year=1990, month=6, day=15, hour=10, gender="male",
            )
        assert mock_cls.call_args[1]["minute"] == 0

    def test_trajectory_with_unknown_day_master(self):
        """Unknown day_master defaults to '土', so trajectory is still generated."""
        mock_analyzer = _make_mock_bazi_analyzer(day_master="未知")
        with patch("tengod.advanced_analysis.BaziAnalyzer",
                   return_value=mock_analyzer):
            analyzer = AdvancedAnalyzer(store=MagicMock())
            result = analyzer.destiny_trajectory(
                year=1990, month=6, day=15, hour=10, gender="male",
            )
        # "未知" → _get_dm_element returns "土" (default), so dayun is generated
        assert len(result["dayun"]) > 0
        assert "日主未知" in result["summary"]


# ---------------------------------------------------------------------------
# Test: _generate_dayun
# ---------------------------------------------------------------------------

class TestGenerateDayun:
    def test_yang_male_forward(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        wuxing = {"木": 3, "火": 1}
        result = analyzer._generate_dayun("甲", wuxing, 0, 80, "male")

        assert len(result) > 0
        # 甲木，阳男顺排 → 下一个是火
        assert result[0]["element"] == "火"
        assert result[0]["relation"] == "食神"
        assert result[0]["favorable"] is True
        assert result[0]["age_start"] == 5
        assert result[0]["age_end"] == 14

    def test_yin_female_forward(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._generate_dayun("乙", {}, 0, 80, "female")

        assert len(result) > 0
        # 乙木，阴女顺排 → 下一个是火
        assert result[0]["element"] == "火"

    def test_yang_female_reverse(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._generate_dayun("甲", {}, 0, 80, "female")

        assert len(result) > 0
        # 甲木，阳女逆排 → 上一个
        assert result[0]["element"] == "水"

    def test_yin_male_reverse(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._generate_dayun("乙", {}, 0, 80, "male")

        assert len(result) > 0
        # 乙木，阴男逆排 → 上一个
        assert result[0]["element"] == "水"

    def test_limited_age_range(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._generate_dayun("甲", {}, 0, 30, "male")

        # Should have dayun up to age 30
        assert len(result) >= 3
        for du in result:
            assert du["age_start"] <= 30

    def test_favorable_detection(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._generate_dayun("甲", {}, 0, 80, "male")

        favorable_relations = {"比肩", "正印", "偏印", "食神", "正财"}
        for du in result:
            if du["relation"] in favorable_relations:
                assert du["favorable"] is True
            else:
                assert du["favorable"] is False

    def test_unknown_day_master(self):
        """Unknown day_master defaults to '土' element, which is valid."""
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._generate_dayun("未知", {}, 0, 80, "male")
        # "未知" → _get_dm_element returns "土" (default), which is in wuxing_order
        # So dayun is generated using 土 as the starting element
        assert len(result) > 0
        assert result[0]["element"] in ["金", "木", "水", "火", "土"]

    def test_dm_element_not_in_wuxing_order(self):
        """Line 323: return [] when dm_element is not in wuxing_order."""
        analyzer = AdvancedAnalyzer(store=MagicMock())
        with patch.object(analyzer, "_get_dm_element", return_value="紫"):
            result = analyzer._generate_dayun("甲", {}, 0, 80, "male")
        assert result == []

    def test_dayun_structure(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._generate_dayun("丙", {}, 0, 80, "male")

        for du in result:
            assert "index" in du
            assert "age_start" in du
            assert "age_end" in du
            assert "gan_zhi" in du
            assert "element" in du
            assert "relation" in du
            assert "favorable" in du
            assert du["age_end"] == du["age_start"] + 9


# ---------------------------------------------------------------------------
# Test: _generate_liunian
# ---------------------------------------------------------------------------

class TestGenerateLiunian:
    def test_basic_liunian(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._generate_liunian(1990, 0, 10, "甲")

        assert len(result) == 11  # ages 0-10 inclusive
        for ln in result:
            assert "age" in ln
            assert "year" in ln
            assert "gan_zhi" in ln
            assert "element" in ln
            assert "relation" in ln
            assert ln["year"] == 1990 + ln["age"]

    def test_year_1984_is_jiazi(self):
        """1984 should be 甲子 year."""
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._generate_liunian(1984, 0, 0, "甲")
        assert result[0]["gan_zhi"] == "甲子"

    def test_liunian_relation(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._generate_liunian(1990, 0, 5, "甲")

        # All should have valid relations
        valid_relations = {"比肩", "食神", "偏财", "七杀", "正印", "偏印"}
        for ln in result:
            assert ln["relation"] in valid_relations

    def test_negative_start_age(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._generate_liunian(1990, -5, 5, "甲")
        # start_age clamped to 0
        assert result[0]["age"] == 0

    def test_end_age_capped_at_100(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._generate_liunian(1990, 0, 200, "甲")
        max_age = max(ln["age"] for ln in result)
        assert max_age <= 100

    def test_zero_range(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._generate_liunian(1990, 5, 5, "甲")
        assert len(result) == 1
        assert result[0]["age"] == 5


# ---------------------------------------------------------------------------
# Test: _analyze_life_stages
# ---------------------------------------------------------------------------

class TestAnalyzeLifeStages:
    def test_all_stages(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        dayun_list = [
            {"index": 1, "age_start": 5, "age_end": 14, "gan_zhi": "丙寅",
             "element": "火", "relation": "食神", "favorable": True},
            {"index": 2, "age_start": 15, "age_end": 24, "gan_zhi": "丁卯",
             "element": "火", "relation": "食神", "favorable": True},
            {"index": 3, "age_start": 25, "age_end": 34, "gan_zhi": "戊辰",
             "element": "土", "relation": "偏财", "favorable": True},
            {"index": 4, "age_start": 35, "age_end": 44, "gan_zhi": "己巳",
             "element": "土", "relation": "偏财", "favorable": True},
            {"index": 5, "age_start": 45, "age_end": 54, "gan_zhi": "庚午",
             "element": "金", "relation": "七杀", "favorable": False},
            {"index": 6, "age_start": 55, "age_end": 64, "gan_zhi": "辛未",
             "element": "金", "relation": "七杀", "favorable": False},
        ]

        result = analyzer._analyze_life_stages(dayun_list, "甲")

        assert len(result) == 6
        assert result[0]["stage"] == "少年运"
        assert result[1]["stage"] == "青年运"
        assert result[2]["stage"] == "壮年运"
        assert result[3]["stage"] == "壮年运"
        assert result[4]["stage"] == "中年运"
        assert result[5]["stage"] == "晚年运"

    def test_empty_dayun(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        result = analyzer._analyze_life_stages([], "甲")
        assert result == []

    def test_advice_content(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        dayun_list = [
            {"index": 1, "age_start": 5, "age_end": 14, "gan_zhi": "丙寅",
             "element": "火", "relation": "食神", "favorable": True},
            {"index": 2, "age_start": 15, "age_end": 24, "gan_zhi": "庚午",
             "element": "金", "relation": "七杀", "favorable": False},
        ]

        result = analyzer._analyze_life_stages(dayun_list, "甲")
        assert "进取" in result[0]["advice"]
        assert "谨慎" in result[1]["advice"]

    def test_stage_boundaries(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        # Boundary cases: 14→少年, 15→青年, 24→青年, 25→壮年, 39→壮年, 40→中年, 54→中年, 55→晚年
        test_cases = [
            (14, "少年运"),
            (15, "青年运"),
            (24, "青年运"),
            (25, "壮年运"),
            (39, "壮年运"),
            (40, "中年运"),
            (54, "中年运"),
            (55, "晚年运"),
        ]
        for age_start, expected_stage in test_cases:
            dayun = [{"index": 1, "age_start": age_start, "age_end": age_start + 9,
                      "gan_zhi": "甲子", "element": "木", "relation": "比肩",
                      "favorable": True}]
            result = analyzer._analyze_life_stages(dayun, "甲")
            assert result[0]["stage"] == expected_stage, \
                f"age_start={age_start}: expected {expected_stage}, got {result[0]['stage']}"


# ---------------------------------------------------------------------------
# Test: _stage_advice
# ---------------------------------------------------------------------------

class TestStageAdvice:
    def test_favorable_advice(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        advice = analyzer._stage_advice("食神", True)
        assert "进取" in advice
        assert "食神" in advice

    def test_unfavorable_advice(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        advice = analyzer._stage_advice("七杀", False)
        assert "谨慎" in advice
        assert "七杀" in advice


# ---------------------------------------------------------------------------
# Test: _trajectory_summary
# ---------------------------------------------------------------------------

class TestTrajectorySummary:
    def test_mostly_favorable(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        dayun_list = [
            {"favorable": True}, {"favorable": True}, {"favorable": True},
            {"favorable": False}, {"favorable": False},
        ]
        stages = [{"stage": "少年运"}]
        summary = analyzer._trajectory_summary("甲", dayun_list, stages)
        assert "整体运势顺遂" in summary

    def test_balanced(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        dayun_list = [
            {"favorable": True}, {"favorable": False},
            {"favorable": True}, {"favorable": False},
        ]
        stages = []
        summary = analyzer._trajectory_summary("甲", dayun_list, stages)
        assert "顺逆参半" in summary

    def test_mostly_unfavorable(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        dayun_list = [
            {"favorable": False}, {"favorable": False}, {"favorable": False},
            {"favorable": True},
        ]
        stages = []
        summary = analyzer._trajectory_summary("甲", dayun_list, stages)
        assert "整体运势偏逆" in summary

    def test_empty_dayun(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        summary = analyzer._trajectory_summary("甲", [], [])
        assert summary == "无法推演命运轨迹"

    def test_all_favorable(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        dayun_list = [{"favorable": True}] * 10
        summary = analyzer._trajectory_summary("甲", dayun_list, [])
        assert "整体运势顺遂" in summary
        assert "10步大运" in summary
        assert "10步为有利运" in summary


# ---------------------------------------------------------------------------
# Test: _get_dm_element
# ---------------------------------------------------------------------------

class TestGetDmElement:
    def test_all_gan(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        expected = {
            "甲": "木", "乙": "木",
            "丙": "火", "丁": "火",
            "戊": "土", "己": "土",
            "庚": "金", "辛": "金",
            "壬": "水", "癸": "水",
        }
        for gan, elem in expected.items():
            assert analyzer._get_dm_element(gan) == elem

    def test_unknown_gan_defaults_to_tu(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        assert analyzer._get_dm_element("未知") == "土"
        assert analyzer._get_dm_element("") == "土"
        assert analyzer._get_dm_element("X") == "土"


# ---------------------------------------------------------------------------
# Test: _wuxing_relation
# ---------------------------------------------------------------------------

class TestWuxingRelation:
    def test_same_element_is_bijian(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        for elem in ["木", "火", "土", "金", "水"]:
            assert analyzer._wuxing_relation(elem, elem) == "比肩"

    def test_known_relations(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        # 木生火 → 食神
        assert analyzer._wuxing_relation("木", "火") == "食神"
        # 木克土 → 偏财
        assert analyzer._wuxing_relation("木", "土") == "偏财"
        # 金克木 → 七杀
        assert analyzer._wuxing_relation("木", "金") == "七杀"
        # 水生木 → 正印
        assert analyzer._wuxing_relation("木", "水") == "正印"

    def test_unknown_relation_defaults_to_pianyin(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        # A relation not in the mapping (e.g., 木→木 already handled as 比肩)
        # But if we pass elements not in the mapping...
        assert analyzer._wuxing_relation("X", "Y") == "偏印"


# ---------------------------------------------------------------------------
# Test: _get_record
# ---------------------------------------------------------------------------

class TestGetRecord:
    def test_existing_record(self):
        record = _make_mock_record(1)
        store = _make_mock_store({1: record})
        analyzer = AdvancedAnalyzer(store=store)

        result = analyzer._get_record(1)
        assert result is record

    def test_missing_record(self):
        store = _make_mock_store({})
        analyzer = AdvancedAnalyzer(store=store)

        result = analyzer._get_record(999)
        assert result is None


# ---------------------------------------------------------------------------
# Test: _get_analysis
# ---------------------------------------------------------------------------

class TestGetAnalysis:
    def test_valid_json(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        record = _make_mock_record(1, analysis_json=json.dumps({"day_master": "甲", "wuxing": {"木": 3}}))
        result = analyzer._get_analysis(record)
        assert result == {"day_master": "甲", "wuxing": {"木": 3}}

    def test_none_json(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        record = _make_mock_record(1, analysis_json=None)
        result = analyzer._get_analysis(record)
        assert result == {}

    def test_corrupted_json(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        record = _make_mock_record(1, analysis_json="not valid json")
        result = analyzer._get_analysis(record)
        assert result == {}


# ---------------------------------------------------------------------------
# Test: _get_geju_name
# ---------------------------------------------------------------------------

class TestGetGejuName:
    def test_dict_geju(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        record = _make_mock_record(1, geju_json=json.dumps({"geju_name": "正官格", "score": 85}))
        result = analyzer._get_geju_name(record)
        assert result == "正官格"

    def test_string_geju(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        record = _make_mock_record(1, geju_json=json.dumps("食神格"))
        result = analyzer._get_geju_name(record)
        assert result == "食神格"

    def test_none_geju(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        record = _make_mock_record(1, geju_json=None)
        result = analyzer._get_geju_name(record)
        assert result == ""

    def test_corrupted_geju_json(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        record = _make_mock_record(1, geju_json="not valid json")
        result = analyzer._get_geju_name(record)
        assert result == ""

    def test_dict_without_geju_name_key(self):
        analyzer = AdvancedAnalyzer(store=MagicMock())
        record = _make_mock_record(1, geju_json=json.dumps({"other_key": "value"}))
        result = analyzer._get_geju_name(record)
        assert result == ""


# ---------------------------------------------------------------------------
# Test: Edge cases & integration-like scenarios
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_compare_same_record(self):
        """Compare a record with itself → 100% similarity."""
        analysis = {"day_master": "甲", "wuxing": {"木": 3, "火": 1, "土": 1, "金": 1, "水": 2},
                    "shigan": {"比肩": 2, "食神": 1, "正财": 1}}
        record = _make_mock_record(1, analysis_json=json.dumps(analysis),
                                   geju_json=json.dumps({"geju_name": "正官格"}))
        store = _make_mock_store({1: record})
        analyzer = AdvancedAnalyzer(store=store)

        result = analyzer.compare_cases(1, 1)
        assert result["similarity_score"] == 100.0
        assert result["geju_same"] is True
        assert result["day_master_same"] is True

    def test_large_batch(self):
        """Test batch with many inputs."""
        mock_analyzer = _make_mock_bazi_analyzer()
        with patch("tengod.advanced_analysis.BaziAnalyzer",
                   return_value=mock_analyzer):
            analyzer = AdvancedAnalyzer(store=MagicMock())
            inputs = [{"year": 1990 + i, "month": 6, "day": 15, "hour": 10,
                       "gender": "male"} for i in range(50)]
            result = analyzer.batch_bazi(inputs)

        assert result["stats"]["total"] == 50
        assert result["stats"]["success"] == 50
        assert result["stats"]["failed"] == 0

    def test_trajectory_zero_age_range(self):
        """Test trajectory with start_age == end_age."""
        mock_analyzer = _make_mock_bazi_analyzer(day_master="甲")
        with patch("tengod.advanced_analysis.BaziAnalyzer",
                   return_value=mock_analyzer):
            analyzer = AdvancedAnalyzer(store=MagicMock())
            result = analyzer.destiny_trajectory(
                year=1990, month=6, day=15, hour=10, gender="male",
                start_age=30, end_age=30,
            )
        # dayun starts at 5, increments by 10; with end_age=30, we get dayun up to 30
        # liunian: only age 30
        assert len(result["liunian"]) == 1
        assert result["liunian"][0]["age"] == 30

    def test_batch_all_failures(self):
        """All batch inputs cause exceptions."""
        def raise_error(**kwargs):
            raise RuntimeError("Simulated failure")

        with patch("tengod.advanced_analysis.BaziAnalyzer",
                   side_effect=raise_error):
            analyzer = AdvancedAnalyzer(store=MagicMock())
            inputs = [
                {"year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male"},
                {"year": 1985, "month": 3, "day": 20, "hour": 14, "gender": "female"},
            ]
            result = analyzer.batch_bazi(inputs)

        assert result["stats"]["total"] == 2
        assert result["stats"]["success"] == 0
        assert result["stats"]["failed"] == 2
        for r in result["results"]:
            assert r["success"] is False
            assert "Simulated failure" in r["error"]

    def test_extreme_wuxing_values(self):
        """Test wuxing comparison with very large values."""
        analyzer = AdvancedAnalyzer(store=MagicMock())
        wa = {"木": 9999, "火": 0, "土": 0, "金": 0, "水": 0}
        wb = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 9999}

        result = analyzer._compare_wuxing(wa, wb)
        assert result["diff"]["木"]["diff"] == 9999
        assert result["diff"]["水"]["diff"] == -9999

    def test_similarity_with_extreme_values(self):
        """Similarity should handle large wuxing values without overflow."""
        analyzer = AdvancedAnalyzer(store=MagicMock())
        wa = {"木": 1000000, "火": 0, "土": 0, "金": 0, "水": 0}
        wb = {"木": 1000000, "火": 0, "土": 0, "金": 0, "水": 0}

        score = analyzer._calc_similarity(wa, wb, "甲", "甲", "正官格", "正官格")
        assert score == 100.0


# ---------------------------------------------------------------------------
# Test: __all__ export
# ---------------------------------------------------------------------------

def test_module_all():
    from tengod import advanced_analysis
    assert "AdvancedAnalyzer" in advanced_analysis.__all__