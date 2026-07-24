"""Tests for tengod.report_generator module."""

from unittest.mock import MagicMock, patch

import pytest

from tengod.report_generator import (
    BaziReportGenerator,
    ComprehensiveReportGenerator,
    WUXING_ADVICE,
    WUXING_COLORS,
    WUXING_EMOJI,
    SHIGAN_ADVICE,
    SHIGAN_DESC,
    generate_html_report,
    generate_report,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_analyzer():
    """Create a mock BaziAnalyzer with all needed attributes."""
    a = MagicMock()
    a.year = 1990
    a.month = 6
    a.day = 15
    a.hour = 12
    a.minute = 30
    a.is_male = True
    a.longitude = 116.4
    a.chart = MagicMock()
    a.chart.true_hour = 12
    a.chart.true_minute = 45
    a.analysis = {
        'day_master': '甲',
        'pillars': {
            'year': '庚午',
            'month': '壬午',
            'day': '甲子',
            'hour': '己巳',
        },
        'shigan_map': {
            'year_gan': '七杀',
            'month_gan': '偏印',
            'hour_gan': '正财',
        },
        'wuxing': {'木': 2, '火': 2, '土': 1, '金': 1, '水': 2},
        'wuxing_score': {'木': 30, '火': 20, '土': 10, '金': 15, '水': 25},
        'shigan_count': {
            '正官': 1, '七杀': 1, '正印': 0, '偏印': 1,
            '正财': 1, '偏财': 0, '食神': 0, '伤官': 0,
            '比肩': 1, '劫财': 0,
        },
        'dayuns': [
            {'age': 10, 'start_year': 2000, 'pillar': '癸未'},
            {'age': 20, 'start_year': 2010, 'pillar': '甲申'},
        ],
        'liunians': [
            {'year': 2024, 'pillar': '甲辰', 'gan_shigan': '比肩'},
            {'year': 2025, 'pillar': '乙巳', 'gan_shigan': '劫财'},
        ],
        'conclusion': '命主甲木生于午月，火旺木焚，需水调候。',
    }
    return a


# ============================================================================
# Constants
# ============================================================================


class TestConstants:
    """Tests for module-level constants."""

    def test_wuxing_colors_all_elements(self):
        """WUXING_COLORS has all 5 elements."""
        assert set(WUXING_COLORS.keys()) == {"木", "火", "土", "金", "水"}
        for v in WUXING_COLORS.values():
            assert v.startswith("#")

    def test_wuxing_emoji_all_elements(self):
        """WUXING_EMOJI has all 5 elements."""
        assert set(WUXING_EMOJI.keys()) == {"木", "火", "土", "金", "水"}

    def test_shigan_desc_all_ten(self):
        """SHIGAN_DESC has all 10 十神."""
        expected = {"比肩", "劫财", "食神", "伤官", "正财", "偏财",
                    "正官", "七杀", "正印", "偏印"}
        assert set(SHIGAN_DESC.keys()) == expected
        for v in SHIGAN_DESC.values():
            assert isinstance(v, str) and len(v) > 0

    def test_shigan_advice_all_ten(self):
        """SHIGAN_ADVICE has all 10 十神."""
        expected = {"比肩", "劫财", "食神", "伤官", "正财", "偏财",
                    "正官", "七杀", "正印", "偏印"}
        assert set(SHIGAN_ADVICE.keys()) == expected
        for v in SHIGAN_ADVICE.values():
            assert isinstance(v, str) and len(v) > 0

    def test_wuxing_advice_all_elements(self):
        """WUXING_ADVICE has all 5 elements."""
        assert set(WUXING_ADVICE.keys()) == {"木", "火", "土", "金", "水"}
        for v in WUXING_ADVICE.values():
            assert isinstance(v, str) and len(v) > 0


# ============================================================================
# BaziReportGenerator __init__
# ============================================================================


class TestBaziReportGeneratorInit:
    """Tests for BaziReportGenerator.__init__."""

    def test_init_with_analyzer(self, mock_analyzer):
        """Init with analyzer extracts basic info."""
        gen = BaziReportGenerator(mock_analyzer)
        assert gen._year == 1990
        assert gen._month == 6
        assert gen._day == 15
        assert gen._hour == 12
        assert gen._minute == 30
        assert gen._is_male is True
        assert gen._longitude == 116.4
        assert gen._chart is mock_analyzer.chart
        assert gen._analysis is mock_analyzer.analysis

    def test_init_without_analyzer(self):
        """Init without analyzer leaves internal state as None."""
        gen = BaziReportGenerator()
        assert gen._analyzer is None
        assert gen._shensha is None
        assert gen._geju is None
        assert gen._yongshen is None
        assert gen._tiaohou is None
        assert gen._vector_store is None

    def test_init_with_lang_parameter(self, mock_analyzer):
        """Init with lang parameter stores correctly."""
        gen = BaziReportGenerator(mock_analyzer, lang="en")
        assert gen._lang == "en"

    def test_t_with_i18n_available(self, mock_analyzer):
        """_t translates when i18n is available."""
        gen = BaziReportGenerator(mock_analyzer)
        mock_t_func = MagicMock(return_value="translated text")
        with patch.dict("sys.modules", {"tengod.i18n": MagicMock(t=mock_t_func)}):
            result = gen._t("original text")
            assert result == "translated text"
            mock_t_func.assert_called_once_with("original text", "zh-CN")

    def test_t_with_i18n_unavailable(self, mock_analyzer):
        """_t returns original text when i18n import fails."""
        gen = BaziReportGenerator(mock_analyzer)
        with patch.dict("sys.modules", {"tengod.i18n": None}):
            from importlib import import_module
            try:
                import_module("tengod.i18n")
            except ImportError:
                pass
            result = gen._t("some text")
            assert result == "some text"


# ============================================================================
# Setters
# ============================================================================


class TestSetters:
    """Tests for setter methods."""

    def test_set_analyzer(self, mock_analyzer):
        """set_analyzer extracts basic info."""
        gen = BaziReportGenerator()
        gen.set_analyzer(mock_analyzer)
        assert gen._year == 1990
        assert gen._month == 6
        assert gen._day == 15
        assert gen._hour == 12
        assert gen._minute == 30

    def test_set_shensha(self, mock_analyzer):
        gen = BaziReportGenerator(mock_analyzer)
        shensha = MagicMock()
        gen.set_shensha(shensha)
        assert gen._shensha is shensha

    def test_set_geju(self, mock_analyzer):
        gen = BaziReportGenerator(mock_analyzer)
        geju = MagicMock()
        gen.set_geju(geju)
        assert gen._geju is geju

    def test_set_yongshen(self, mock_analyzer):
        gen = BaziReportGenerator(mock_analyzer)
        yongshen = MagicMock()
        gen.set_yongshen(yongshen)
        assert gen._yongshen is yongshen

    def test_set_tiaohou(self, mock_analyzer):
        gen = BaziReportGenerator(mock_analyzer)
        tiaohou = MagicMock()
        gen.set_tiaohou(tiaohou)
        assert gen._tiaohou is tiaohou

    def test_set_vector_store(self, mock_analyzer):
        gen = BaziReportGenerator(mock_analyzer)
        store = MagicMock()
        gen.set_vector_store(store)
        assert gen._vector_store is store


# ============================================================================
# text_report()
# ============================================================================


class TestTextReport:
    """Tests for text_report method."""

    def test_basic_text_report(self, mock_analyzer):
        """Basic text report generation returns a non-empty string."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.text_report()
        assert isinstance(report, str)
        assert len(report) > 0

    def test_header_present(self, mock_analyzer):
        """Verify header section is present in text report."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.text_report()
        assert "八字命理综合分析报告" in report

    def test_basic_info_present(self, mock_analyzer):
        """Verify basic info section is present in text report."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.text_report()
        assert "基本信息" in report
        assert "1990" in report
        assert "男命" in report

    def test_pillars_present(self, mock_analyzer):
        """Verify pillars section is present in text report."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.text_report()
        assert "四柱分析" in report
        assert "庚午" in report
        assert "壬午" in report
        assert "甲子" in report
        assert "己巳" in report

    def test_wuxing_present(self, mock_analyzer):
        """Verify wuxing section is present in text report."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.text_report()
        assert "五行分析" in report

    def test_shigan_present(self, mock_analyzer):
        """Verify shigan section is present in text report."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.text_report()
        assert "十神分析" in report

    def test_footer_present(self, mock_analyzer):
        """Verify footer section is present in text report."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.text_report()
        assert "报告生成时间" in report

    def test_text_report_with_shensha(self, mock_analyzer):
        """Text report with shensha data."""
        gen = BaziReportGenerator(mock_analyzer)
        shensha = MagicMock()
        shensha.all_shensha = {
            "天乙贵人": {"cat": "吉神", "desc": "贵人相助"},
            "羊刃": {"cat": "凶", "desc": "刚烈冲动"},
        }
        gen.set_shensha(shensha)
        report = gen.text_report()
        assert "神煞分析" in report
        assert "天乙贵人" in report

    def test_text_report_with_geju(self, mock_analyzer):
        """Text report with geju data."""
        gen = BaziReportGenerator(mock_analyzer)
        geju = MagicMock()
        geju.geju_name = "正官格"
        geju.geju_type = "正格"
        geju.score = 85.0
        geju.geju_desc = "正官得令，格局清纯"
        geju.is_cong = False
        geju.is_huaqi = False
        geju.shiyongshen = ["正官", "正印"]
        geju.jishen = ["伤官"]
        gen.set_geju(geju)
        report = gen.text_report()
        assert "格局分析" in report
        assert "正官格" in report

    def test_text_report_with_yongshen(self, mock_analyzer):
        """Text report with yongshen data."""
        gen = BaziReportGenerator(mock_analyzer)
        yongshen = MagicMock()
        yongshen.wang_shuai = "身弱"
        yongshen.wang_shuai_level = 35.0
        yongshen.yong_shen = ["水", "木"]
        yongshen.ji_shen = ["土", "金"]
        yongshen.yongshen_desc = "身弱需印比帮身"
        gen.set_yongshen(yongshen)
        report = gen.text_report()
        assert "喜用神与调候" in report
        assert "身弱" in report

    def test_text_report_with_tiaohou(self, mock_analyzer):
        """Text report with tiaohou data."""
        gen = BaziReportGenerator(mock_analyzer)
        tiaohou = MagicMock()
        tiaohou.required_tiaohou = True
        tiaohou.season = "夏季"
        tiaohou.tiaohou_shens = ["水"]
        tiaohou.desc = "夏季火旺，需水调候"
        gen.set_tiaohou(tiaohou)
        report = gen.text_report()
        assert "调候" in report

    def test_text_report_with_all_data(self, mock_analyzer):
        """Text report with all optional data combined."""
        gen = BaziReportGenerator(mock_analyzer)

        shensha = MagicMock()
        shensha.all_shensha = {
            "天乙贵人": {"cat": "吉神", "desc": "贵人相助"},
        }
        gen.set_shensha(shensha)

        geju = MagicMock()
        geju.geju_name = "正官格"
        geju.geju_type = "正格"
        geju.score = 80.0
        geju.geju_desc = "正官得令"
        geju.is_cong = False
        geju.is_huaqi = False
        geju.shiyongshen = ["正官"]
        geju.jishen = []
        gen.set_geju(geju)

        yongshen = MagicMock()
        yongshen.wang_shuai = "身旺"
        yongshen.wang_shuai_level = 70.0
        yongshen.yong_shen = ["火", "土"]
        yongshen.ji_shen = ["水"]
        yongshen.yongshen_desc = "身旺需克泄耗"
        gen.set_yongshen(yongshen)

        tiaohou = MagicMock()
        tiaohou.required_tiaohou = True
        tiaohou.season = "夏季"
        tiaohou.tiaohou_shens = ["水"]
        tiaohou.desc = "夏季调候"
        gen.set_tiaohou(tiaohou)

        report = gen.text_report()
        assert "神煞分析" in report
        assert "格局分析" in report
        assert "喜用神与调候" in report
        assert "调候" in report


# ============================================================================
# markdown_report()
# ============================================================================


class TestMarkdownReport:
    """Tests for markdown_report method."""

    def test_basic_markdown_report(self, mock_analyzer):
        """Basic markdown report generation."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.markdown_report()
        assert isinstance(report, str)
        assert len(report) > 0

    def test_sections_present(self, mock_analyzer):
        """Verify markdown sections are present."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.markdown_report()
        assert "# " in report
        assert "基本信息" in report
        assert "四柱分析" in report
        assert "五行分析" in report
        assert "十神分析" in report

    def test_with_shensha(self, mock_analyzer):
        """Markdown report with shensha data."""
        gen = BaziReportGenerator(mock_analyzer)
        shensha = MagicMock()
        shensha.all_shensha = {
            "天乙贵人": {"cat": "吉神", "desc": "贵人相助"},
        }
        gen.set_shensha(shensha)
        report = gen.markdown_report()
        assert "神煞分析" in report

    def test_with_geju(self, mock_analyzer):
        """Markdown report with geju data."""
        gen = BaziReportGenerator(mock_analyzer)
        geju = MagicMock()
        geju.geju_name = "正官格"
        geju.geju_type = "正格"
        geju.score = 90.0
        geju.geju_desc = "正官得令"
        geju.is_cong = False
        geju.is_huaqi = False
        geju.shiyongshen = ["正官"]
        geju.jishen = []
        gen.set_geju(geju)
        report = gen.markdown_report()
        assert "格局分析" in report
        assert "正官格" in report

    def test_with_yongshen(self, mock_analyzer):
        """Markdown report with yongshen data."""
        gen = BaziReportGenerator(mock_analyzer)
        yongshen = MagicMock()
        yongshen.wang_shuai = "身弱"
        yongshen.wang_shuai_level = 30.0
        yongshen.yong_shen = ["水", "木"]
        yongshen.ji_shen = ["土"]
        yongshen.yongshen_desc = "身弱帮身"
        gen.set_yongshen(yongshen)
        report = gen.markdown_report()
        assert "喜用神与调候" in report


# ============================================================================
# json_report()
# ============================================================================


class TestJsonReport:
    """Tests for json_report method."""

    def test_basic_json_structure(self, mock_analyzer):
        """Basic JSON report has expected top-level keys."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.json_report()
        assert isinstance(report, dict)
        assert "meta" in report
        assert "basic" in report
        assert "wuxing" in report
        assert "shigan" in report
        assert "shensha" in report
        assert "geju" in report
        assert "yongshen" in report
        assert "tiaohou" in report
        assert "dayun" in report
        assert "liunian" in report
        assert "conclusion" in report

    def test_json_with_shensha(self, mock_analyzer):
        """JSON report with shensha data."""
        gen = BaziReportGenerator(mock_analyzer)
        shensha = MagicMock()
        shensha.json_report.return_value = {"shensha_data": "test"}
        gen.set_shensha(shensha)
        report = gen.json_report()
        assert report["shensha"] == {"shensha_data": "test"}

    def test_json_with_geju(self, mock_analyzer):
        """JSON report with geju data."""
        gen = BaziReportGenerator(mock_analyzer)
        geju = MagicMock()
        geju.geju_name = "正官格"
        geju.geju_type = "正格"
        geju.geju_desc = "desc"
        geju.score = 85.0
        geju.is_cong = False
        geju.is_huaqi = False
        gen.set_geju(geju)
        report = gen.json_report()
        assert report["geju"] is not None
        assert report["geju"]["name"] == "正官格"

    def test_json_with_yongshen(self, mock_analyzer):
        """JSON report with yongshen data."""
        gen = BaziReportGenerator(mock_analyzer)
        yongshen = MagicMock()
        yongshen.wang_shuai = "身弱"
        yongshen.yong_shen = ["水"]
        yongshen.ji_shen = ["土"]
        yongshen.yongshen_desc = "desc"
        gen.set_yongshen(yongshen)
        report = gen.json_report()
        assert report["yongshen"] is not None
        assert report["yongshen"]["wang_shuai"] == "身弱"

    def test_json_with_tiaohou(self, mock_analyzer):
        """JSON report with tiaohou data."""
        gen = BaziReportGenerator(mock_analyzer)
        tiaohou = MagicMock()
        tiaohou.required_tiaohou = True
        tiaohou.tiaohou_shens = ["水"]
        tiaohou.season = "夏季"
        tiaohou.desc = "desc"
        gen.set_tiaohou(tiaohou)
        report = gen.json_report()
        assert report["tiaohou"] is not None
        assert report["tiaohou"]["required"] is True

    def test_json_all_top_level_keys(self, mock_analyzer):
        """Verify all top-level keys are present in JSON report."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.json_report()
        expected_keys = {"meta", "basic", "wuxing", "shigan", "shensha",
                         "geju", "yongshen", "tiaohou", "dayun", "liunian",
                         "conclusion"}
        assert set(report.keys()) == expected_keys


# ============================================================================
# html_report()
# ============================================================================


class TestHtmlReport:
    """Tests for html_report method."""

    def test_basic_html_report(self, mock_analyzer):
        """Basic HTML report generation."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.html_report()
        assert isinstance(report, str)
        assert len(report) > 0

    def test_contains_html_structure(self, mock_analyzer):
        """HTML report contains HTML template structure."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.html_report()
        assert "<!DOCTYPE html>" in report
        assert "<html" in report
        assert "<head>" in report
        assert "<body>" in report
        assert "</html>" in report

    def test_contains_title(self, mock_analyzer):
        """HTML report contains title."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.html_report()
        assert "<title>" in report
        assert "1990" in report

    def test_contains_version(self, mock_analyzer):
        """HTML report contains version info."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.html_report()
        assert "引擎版本" in report

    def test_contains_body(self, mock_analyzer):
        """HTML report contains body content from markdown."""
        gen = BaziReportGenerator(mock_analyzer)
        report = gen.html_report()
        assert "八字命理综合分析报告" in report


# ============================================================================
# _safe_get
# ============================================================================


class TestSafeGet:
    """Tests for _safe_get method."""

    def test_dict_with_key(self, mock_analyzer):
        """Dict with key returns value."""
        gen = BaziReportGenerator(mock_analyzer)
        d = {"key": "value"}
        assert gen._safe_get(d, "key") == "value"

    def test_dict_without_key_returns_default(self, mock_analyzer):
        """Dict without key returns default."""
        gen = BaziReportGenerator(mock_analyzer)
        d = {"a": 1}
        assert gen._safe_get(d, "missing", "default") == "default"

    def test_non_dict_with_attribute(self, mock_analyzer):
        """Non-dict object with attribute returns attribute value."""
        gen = BaziReportGenerator(mock_analyzer)

        class SimpleObj:
            pass
        obj = SimpleObj()
        obj.name = "test_name"
        result = gen._safe_get(obj, "name", "fallback")
        assert result == "test_name"

    def test_non_dict_without_attribute_returns_default(self, mock_analyzer):
        """Non-dict object without attribute returns default."""
        gen = BaziReportGenerator(mock_analyzer)
        obj = MagicMock(spec=[])  # no attributes
        result = gen._safe_get(obj, "nonexistent", "fallback")
        assert result == "fallback"


# ============================================================================
# Sub-sections (tested via text_report)
# ============================================================================


class TestHeaderText:
    """Tests for _header_text via text_report."""

    def test_header_contains_formatted_header(self, mock_analyzer):
        """_header_text returns formatted header."""
        gen = BaziReportGenerator(mock_analyzer)
        header = gen._header_text()
        assert isinstance(header, list)
        assert len(header) == 4
        assert any("八字命理综合分析报告" in line for line in header)


class TestBasicInfoText:
    """Tests for _basic_info_text via text_report."""

    def test_basic_info_with_male(self, mock_analyzer):
        """_basic_info_text with male gender."""
        mock_analyzer.is_male = True
        gen = BaziReportGenerator(mock_analyzer)
        info = gen._basic_info_text()
        text = "\n".join(info)
        assert "男命" in text

    def test_basic_info_with_female(self, mock_analyzer):
        """_basic_info_text with female gender."""
        mock_analyzer.is_male = False
        gen = BaziReportGenerator(mock_analyzer)
        info = gen._basic_info_text()
        text = "\n".join(info)
        assert "女命" in text


class TestPillarsText:
    """Tests for _pillars_text via text_report."""

    def test_pillars_with_four_pillars(self, mock_analyzer):
        """_pillars_text with four pillars."""
        gen = BaziReportGenerator(mock_analyzer)
        pillars = gen._pillars_text()
        text = "\n".join(pillars)
        assert "庚午" in text
        assert "壬午" in text
        assert "甲子" in text
        assert "己巳" in text


class TestWuxingText:
    """Tests for _wuxing_text via text_report."""

    def test_wuxing_with_distribution(self, mock_analyzer):
        """_wuxing_text with wuxing distribution."""
        gen = BaziReportGenerator(mock_analyzer)
        text_lines = gen._wuxing_text()
        text = "\n".join(text_lines)
        assert "五行分析" in text
        assert "最旺五行" in text

    def test_wuxing_with_missing(self, mock_analyzer):
        """_wuxing_text with missing wuxing."""
        mock_analyzer.analysis['wuxing'] = {'木': 0, '火': 2, '土': 1, '金': 1, '水': 2}
        gen = BaziReportGenerator(mock_analyzer)
        text_lines = gen._wuxing_text()
        text = "\n".join(text_lines)
        assert "缺失五行" in text


class TestShiganText:
    """Tests for _shigan_text via text_report."""

    def test_shigan_with_counts(self, mock_analyzer):
        """_shigan_text with shigan counts."""
        gen = BaziReportGenerator(mock_analyzer)
        lines = gen._shigan_text()
        text = "\n".join(lines)
        assert "十神分析" in text
        assert "善神" in text
        assert "凶神" in text


class TestShenshaText:
    """Tests for _shensha_text via text_report."""

    def test_shensha_without_data(self, mock_analyzer):
        """_shensha_text without shensha data."""
        gen = BaziReportGenerator(mock_analyzer)
        lines = gen._shensha_text()
        text = "\n".join(lines)
        assert "未加载神煞数据" in text

    def test_shensha_with_data(self, mock_analyzer):
        """_shensha_text with shensha data."""
        gen = BaziReportGenerator(mock_analyzer)
        shensha = MagicMock()
        shensha.all_shensha = {
            "天乙贵人": {"cat": "吉神", "desc": "贵人相助"},
            "羊刃": {"cat": "凶", "desc": "刚烈"},
        }
        gen.set_shensha(shensha)
        lines = gen._shensha_text()
        text = "\n".join(lines)
        assert "天乙贵人" in text
        assert "吉神" in text


class TestGejuText:
    """Tests for _geju_text via text_report."""

    def test_geju_without_data(self, mock_analyzer):
        """_geju_text without geju data."""
        gen = BaziReportGenerator(mock_analyzer)
        lines = gen._geju_text()
        text = "\n".join(lines)
        assert "未加载格局数据" in text

    def test_geju_with_data(self, mock_analyzer):
        """_geju_text with geju data."""
        gen = BaziReportGenerator(mock_analyzer)
        geju = MagicMock()
        geju.geju_name = "正官格"
        geju.geju_type = "正格"
        geju.score = 85.0
        geju.geju_desc = "正官得令"
        geju.is_cong = False
        geju.is_huaqi = False
        geju.shiyongshen = ["正官", "正印"]
        geju.jishen = ["伤官"]
        gen.set_geju(geju)
        lines = gen._geju_text()
        text = "\n".join(lines)
        assert "正官格" in text
        assert "格局纯度" in text

    def test_geju_with_cong_ge(self, mock_analyzer):
        """_geju_text with cong ge (从格)."""
        gen = BaziReportGenerator(mock_analyzer)
        geju = MagicMock()
        geju.geju_name = "从财格"
        geju.geju_type = "从格"
        geju.score = 90.0
        geju.geju_desc = "从财"
        geju.is_cong = True
        geju.is_huaqi = False
        geju.shiyongshen = ["财"]
        geju.jishen = []
        gen.set_geju(geju)
        lines = gen._geju_text()
        text = "\n".join(lines)
        assert "从格" in text

    def test_geju_with_huaqi_ge(self, mock_analyzer):
        """_geju_text with huaqi ge (化气格)."""
        gen = BaziReportGenerator(mock_analyzer)
        geju = MagicMock()
        geju.geju_name = "化气格"
        geju.geju_type = "化格"
        geju.score = 88.0
        geju.geju_desc = "化气"
        geju.is_cong = False
        geju.is_huaqi = True
        geju.shiyongshen = []
        geju.jishen = []
        gen.set_geju(geju)
        lines = gen._geju_text()
        text = "\n".join(lines)
        assert "化气格" in text


class TestYongshenText:
    """Tests for _yongshen_text via text_report."""

    def test_yongshen_without_data(self, mock_analyzer):
        """_yongshen_text without yongshen/tiaohou data."""
        gen = BaziReportGenerator(mock_analyzer)
        lines = gen._yongshen_text()
        text = "\n".join(lines)
        assert "未加载喜用神数据" in text

    def test_yongshen_with_yongshen_data(self, mock_analyzer):
        """_yongshen_text with yongshen data."""
        gen = BaziReportGenerator(mock_analyzer)
        yongshen = MagicMock()
        yongshen.wang_shuai = "身弱"
        yongshen.wang_shuai_level = 35.0
        yongshen.yong_shen = ["水", "木"]
        yongshen.ji_shen = ["土", "金"]
        yongshen.yongshen_desc = "身弱需印比帮身"
        gen.set_yongshen(yongshen)
        lines = gen._yongshen_text()
        text = "\n".join(lines)
        assert "身弱" in text
        assert "用神" in text
        assert "忌神" in text

    def test_yongshen_with_tiaohou_data(self, mock_analyzer):
        """_yongshen_text with tiaohou data."""
        gen = BaziReportGenerator(mock_analyzer)
        tiaohou = MagicMock()
        tiaohou.required_tiaohou = True
        tiaohou.season = "夏季"
        tiaohou.tiaohou_shens = ["水"]
        tiaohou.desc = "夏季火旺，需水调候"
        gen.set_tiaohou(tiaohou)
        lines = gen._yongshen_text()
        text = "\n".join(lines)
        assert "调候" in text
        assert "夏季" in text


class TestDayunText:
    """Tests for _dayun_text via text_report."""

    def test_dayun_with_dayuns(self, mock_analyzer):
        """_dayun_text with dayuns."""
        gen = BaziReportGenerator(mock_analyzer)
        lines = gen._dayun_text()
        text = "\n".join(lines)
        assert "大运分析" in text
        assert "癸未" in text
        assert "甲申" in text


class TestLiunianText:
    """Tests for _liunian_text via text_report."""

    def test_liunian_with_liunians(self, mock_analyzer):
        """_liunian_text with liunians."""
        gen = BaziReportGenerator(mock_analyzer)
        lines = gen._liunian_text()
        text = "\n".join(lines)
        assert "近期流年" in text
        assert "2024" in text
        assert "2025" in text
        assert "比肩" in text


class TestAdviceText:
    """Tests for _advice_text via text_report."""

    def test_advice_with_wuxing_and_yongshen(self, mock_analyzer):
        """_advice_text with wuxing and yongshen."""
        gen = BaziReportGenerator(mock_analyzer)
        yongshen = MagicMock()
        yongshen.yong_shen = ["水", "木"]
        yongshen.ji_shen = ["土", "金"]
        yongshen.wang_shuai = "身弱"
        yongshen.wang_shuai_level = 35.0
        yongshen.yongshen_desc = "身弱帮身"
        gen.set_yongshen(yongshen)
        lines = gen._advice_text()
        text = "\n".join(lines)
        assert "综合建议" in text
        assert "宜补充" in text

    def test_advice_with_missing_wuxing(self, mock_analyzer):
        """_advice_text with missing wuxing."""
        mock_analyzer.analysis['wuxing'] = {'木': 0, '火': 2, '土': 1, '金': 1, '水': 2}
        gen = BaziReportGenerator(mock_analyzer)
        lines = gen._advice_text()
        text = "\n".join(lines)
        assert "补缺建议" in text


class TestFooterText:
    """Tests for _footer_text via text_report."""

    def test_footer_contains_timestamp(self, mock_analyzer):
        """_footer_text contains timestamp."""
        gen = BaziReportGenerator(mock_analyzer)
        footer = gen._footer_text()
        text = "\n".join(footer)
        assert "报告生成时间" in text


# ============================================================================
# ComprehensiveReportGenerator
# ============================================================================


@pytest.fixture
def comp_dict():
    """Create a comprehensive report dict."""
    return {
        "birth_info": {"gender": "male", "target_year": "2024"},
        "systems": {
            "八字": {"available": True, "summary": "八字分析摘要"},
            "紫微斗数": {"available": True, "summary": "紫微分析摘要"},
            "占星": {"available": False, "error": "模块未加载"},
        },
        "cross_validation": {
            "score": 75,
            "level": "较高",
            "agreements": ["八字", "紫微斗数"],
            "conflicts": ["占星"],
            "interpretations": ["八字与紫微斗数一致"],
        },
        "consensus": {
            "overall": "中上",
            "score": 72,
            "career": "良好",
            "wealth": "中等",
            "relationships": "良好",
            "health": "一般",
            "key_strengths": ["事业稳定", "财运亨通"],
            "key_risks": ["健康注意"],
            "best_timing": ["春季", "秋季"],
        },
        "comprehensive_report": "综合分析报告内容",
    }


class TestComprehensiveReportGenerator:
    """Tests for ComprehensiveReportGenerator."""

    def test_init_with_comp_dict(self, comp_dict):
        """Init with comp_dict stores all attributes."""
        gen = ComprehensiveReportGenerator(comp_dict)
        assert gen._d is comp_dict
        assert gen._birth == comp_dict["birth_info"]
        assert gen._systems == comp_dict["systems"]
        assert gen._cross == comp_dict["cross_validation"]
        assert gen._consensus == comp_dict["consensus"]
        assert gen._raw_report == comp_dict["comprehensive_report"]

    def test_text_report_with_consensus(self, comp_dict):
        """Text report with consensus and cross_validation."""
        gen = ComprehensiveReportGenerator(comp_dict)
        report = gen.text_report()
        assert "多体系综合命理分析报告" in report
        assert "共识运势" in report
        assert "交叉验证" in report

    def test_text_report_with_systems(self, comp_dict):
        """Text report with systems data."""
        gen = ComprehensiveReportGenerator(comp_dict)
        report = gen.text_report()
        assert "各体系分析结果" in report
        assert "八字" in report
        assert "紫微斗数" in report

    def test_text_report_with_unavailable_systems(self, comp_dict):
        """Text report with unavailable systems."""
        gen = ComprehensiveReportGenerator(comp_dict)
        report = gen.text_report()
        assert "占星" in report
        assert "不可用" in report or "模块未加载" in report

    def test_text_report_with_raw_report(self, comp_dict):
        """Text report with raw_report."""
        gen = ComprehensiveReportGenerator(comp_dict)
        report = gen.text_report()
        assert "综合分析" in report
        assert "综合分析报告内容" in report

    def test_markdown_report_sections(self, comp_dict):
        """Markdown report has expected sections."""
        gen = ComprehensiveReportGenerator(comp_dict)
        report = gen.markdown_report()
        assert "# " in report
        assert "共识运势" in report
        assert "交叉验证" in report
        assert "各体系分析结果" in report

    def test_json_report_structure(self, comp_dict):
        """JSON report has expected structure."""
        gen = ComprehensiveReportGenerator(comp_dict)
        report = gen.json_report()
        assert "birth_info" in report
        assert "consensus" in report
        assert "cross_validation" in report
        assert "systems" in report
        assert "raw_report" in report
        assert "summary" in report

    def test_html_report_generation(self, comp_dict):
        """HTML report generation."""
        gen = ComprehensiveReportGenerator(comp_dict)
        report = gen.html_report()
        assert isinstance(report, str)
        assert "<!DOCTYPE html>" in report
        assert "<html" in report

    def test_level_bar_0(self, comp_dict):
        gen = ComprehensiveReportGenerator(comp_dict)
        assert gen._level_bar(0) == "☆☆☆☆☆"

    def test_level_bar_20(self, comp_dict):
        gen = ComprehensiveReportGenerator(comp_dict)
        assert gen._level_bar(20) == "★☆☆☆☆"

    def test_level_bar_40(self, comp_dict):
        gen = ComprehensiveReportGenerator(comp_dict)
        assert gen._level_bar(40) == "★★☆☆☆"

    def test_level_bar_60(self, comp_dict):
        gen = ComprehensiveReportGenerator(comp_dict)
        assert gen._level_bar(60) == "★★★☆☆"

    def test_level_bar_80(self, comp_dict):
        gen = ComprehensiveReportGenerator(comp_dict)
        assert gen._level_bar(80) == "★★★★☆"

    def test_level_bar_100(self, comp_dict):
        gen = ComprehensiveReportGenerator(comp_dict)
        assert gen._level_bar(100) == "★★★★★"

    def test_level_bar_boundary(self, comp_dict):
        """Test boundary values for level_bar."""
        gen = ComprehensiveReportGenerator(comp_dict)
        assert gen._level_bar(9) == "☆☆☆☆☆"
        assert gen._level_bar(11) == "★☆☆☆☆"
        assert gen._level_bar(29) == "★☆☆☆☆"
        assert gen._level_bar(31) == "★★☆☆☆"
        assert gen._level_bar(49) == "★★☆☆☆"
        assert gen._level_bar(51) == "★★★☆☆"
        assert gen._level_bar(69) == "★★★☆☆"
        assert gen._level_bar(71) == "★★★★☆"
        assert gen._level_bar(89) == "★★★★☆"
        assert gen._level_bar(91) == "★★★★★"


# ============================================================================
# generate_report()
# ============================================================================


class TestGenerateReport:
    """Tests for generate_report convenience function."""

    def test_basic_call(self, mock_analyzer):
        """Basic call with analyzer."""
        report = generate_report(mock_analyzer)
        assert isinstance(report, str)
        assert "八字命理综合分析报告" in report

    def test_with_all_optional_results(self, mock_analyzer):
        """With all optional results."""
        shensha = MagicMock()
        shensha.all_shensha = {"天乙贵人": {"cat": "吉神", "desc": "贵人"}}

        geju = MagicMock()
        geju.geju_name = "正官格"
        geju.geju_type = "正格"
        geju.score = 85.0
        geju.geju_desc = "desc"
        geju.is_cong = False
        geju.is_huaqi = False
        geju.shiyongshen = ["正官"]
        geju.jishen = []

        yongshen = MagicMock()
        yongshen.wang_shuai = "身弱"
        yongshen.wang_shuai_level = 35.0
        yongshen.yong_shen = ["水"]
        yongshen.ji_shen = ["土"]
        yongshen.yongshen_desc = "desc"

        tiaohou = MagicMock()
        tiaohou.required_tiaohou = True
        tiaohou.season = "夏季"
        tiaohou.tiaohou_shens = ["水"]
        tiaohou.desc = "desc"

        report = generate_report(
            mock_analyzer,
            shensha_result=shensha,
            geju_result=geju,
            yongshen_result=yongshen,
            tiaohou_result=tiaohou,
        )
        assert isinstance(report, str)
        assert "神煞分析" in report
        assert "格局分析" in report

    def test_with_lang_parameter(self, mock_analyzer):
        """With lang parameter."""
        report = generate_report(mock_analyzer, lang="en")
        assert isinstance(report, str)


# ============================================================================
# generate_html_report()
# ============================================================================


class TestGenerateHtmlReport:
    """Tests for generate_html_report convenience function."""

    def test_basic_call(self, mock_analyzer):
        """Basic call with analyzer."""
        report = generate_html_report(mock_analyzer)
        assert isinstance(report, str)
        assert "<!DOCTYPE html>" in report

    def test_with_all_optional_results(self, mock_analyzer):
        """With all optional results."""
        shensha = MagicMock()
        shensha.all_shensha = {"天乙贵人": {"cat": "吉神", "desc": "贵人"}}

        geju = MagicMock()
        geju.geju_name = "正官格"
        geju.geju_type = "正格"
        geju.score = 85.0
        geju.geju_desc = "desc"
        geju.is_cong = False
        geju.is_huaqi = False
        geju.shiyongshen = ["正官"]
        geju.jishen = []

        yongshen = MagicMock()
        yongshen.wang_shuai = "身弱"
        yongshen.wang_shuai_level = 35.0
        yongshen.yong_shen = ["水"]
        yongshen.ji_shen = ["土"]
        yongshen.yongshen_desc = "desc"

        tiaohou = MagicMock()
        tiaohou.required_tiaohou = True
        tiaohou.season = "夏季"
        tiaohou.tiaohou_shens = ["水"]
        tiaohou.desc = "desc"

        report = generate_html_report(
            mock_analyzer,
            shensha_result=shensha,
            geju_result=geju,
            yongshen_result=yongshen,
            tiaohou_result=tiaohou,
        )
        assert isinstance(report, str)
        assert "<!DOCTYPE html>" in report