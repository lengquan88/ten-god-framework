"""
tests/test_shen_agents.py — 十神智能体模块测试
覆盖 ShenAgent 基类、12 个十神智能体、2 个综合智能体、工具函数。
"""

from __future__ import annotations

import pytest

from tengod.shen_agents import (
    ShenAgent,
    QishaAgent,
    ShangguanAgent,
    PianyinAgent,
    PiancaiAgent,
    YuanchenAgent,
    JiecaiAgent,
    TaijiAgent,
    ZhengyinAgent,
    ZhengguanAgent,
    ZhengcaiAgent,
    BijianAgent,
    ShishenAgent,
    SizhuAgent,
    LiunianAgent,
    ALL_SHEN_AGENTS,
    COMPREHENSIVE_AGENTS,
    ALL_AGENTS,
    get_agent,
    list_agents,
    analyze_with_agents,
    get_all_agent_tool_specs,
    agent_tool_dispatcher,
    SHIGAN_ANALYSIS,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_bazi_data():
    """基础八字数据 fixture"""
    return {
        "shigan_map": {
            "year_gan": "七杀",
            "month_gan": "正官",
            "day_gan": "比肩",
            "hour_gan": "食神",
        },
        "pillars": {
            "year": "甲子",
            "month": "丙寅",
            "day": "戊辰",
            "hour": "庚午",
        },
        "day_master": "戊",
    }


@pytest.fixture
def empty_bazi_data():
    """空八字数据 fixture"""
    return {}


# ============================================================================
# ShenAgent 基类测试
# ============================================================================


class TestShenAgentBase:
    """ShenAgent 基类测试"""

    def test_init_with_all_fields(self):
        agent = ShenAgent("测试", "测试标题", "这是一个测试描述", category="综合")
        assert agent.name == "测试"
        assert agent.title == "测试标题"
        assert agent.description == "这是一个测试描述"
        assert agent.category == "综合"

    def test_default_category_is_shen(self):
        agent = ShenAgent("测试", "标题", "描述")
        assert agent.category == "shen"

    def test_analyze_returns_dict_with_required_keys(self, sample_bazi_data):
        agent = ShenAgent("测试", "测试标题", "测试描述")
        result = agent.analyze(sample_bazi_data)
        assert isinstance(result, dict)
        assert result["agent"] == "测试"
        assert result["title"] == "测试标题"
        assert "analysis" in result
        assert result["confidence"] == 0.75

    def test_analyze_with_question(self, sample_bazi_data):
        agent = ShenAgent("测试", "标题", "描述")
        result = agent.analyze(sample_bazi_data, question="今年的运势如何？")
        assert result["agent"] == "测试"

    def test_default_analysis_format(self, sample_bazi_data):
        agent = ShenAgent("测试", "标题", "这是一个测试")
        analysis = agent._default_analysis(sample_bazi_data)
        assert "【测试·标题】" in analysis
        assert "这是一个测试" in analysis

    def test_to_tool_spec_format(self):
        agent = ShenAgent("测试", "测试标题", "测试描述")
        spec = agent.to_tool_spec()
        assert spec["type"] == "function"
        assert spec["function"]["name"] == "shen_测试"
        assert "测试标题" in spec["function"]["description"]
        assert "测试描述" in spec["function"]["description"]
        assert "parameters" in spec["function"]
        assert "bazi_data" in spec["function"]["parameters"]["properties"]
        assert "question" in spec["function"]["parameters"]["properties"]
        assert "bazi_data" in spec["function"]["parameters"]["required"]

    def test_to_tool_spec_with_category(self):
        agent = ShenAgent("测试", "标题", "描述", category="综合")
        spec = agent.to_tool_spec()
        assert spec["function"]["name"] == "shen_测试"


# ============================================================================
# SHIGAN_ANALYSIS 测试
# ============================================================================


class TestShiganAnalysis:
    """SHIGAN_ANALYSIS 映射测试"""

    EXPECTED_KEYS = ["正官", "七杀", "正财", "偏财", "正印", "偏印", "食神", "伤官", "比肩", "劫财"]

    def test_all_10_keys_present(self):
        for key in self.EXPECTED_KEYS:
            assert key in SHIGAN_ANALYSIS, f"缺少键: {key}"

    def test_all_values_are_non_empty_strings(self):
        for key in self.EXPECTED_KEYS:
            val = SHIGAN_ANALYSIS[key]
            assert isinstance(val, str), f"{key} 的值不是字符串"
            assert len(val) > 0, f"{key} 的值为空"


# ============================================================================
# 12 个 Shigan 智能体通用测试
# ============================================================================

SHIGAN_AGENT_CLASSES = [
    QishaAgent,
    ShangguanAgent,
    PianyinAgent,
    PiancaiAgent,
    YuanchenAgent,
    JiecaiAgent,
    TaijiAgent,
    ZhengyinAgent,
    ZhengguanAgent,
    ZhengcaiAgent,
    BijianAgent,
    ShishenAgent,
]


class TestAllShiganAgents:
    """所有十神智能体通用测试"""

    @pytest.mark.parametrize("agent_cls", SHIGAN_AGENT_CLASSES)
    def test_init_has_correct_name_title_description(self, agent_cls):
        agent = agent_cls()
        assert isinstance(agent.name, str) and len(agent.name) > 0
        assert isinstance(agent.title, str) and len(agent.title) > 0
        assert isinstance(agent.description, str) and len(agent.description) > 0
        assert agent.category == "shen"

    @pytest.mark.parametrize("agent_cls", SHIGAN_AGENT_CLASSES)
    def test_analyze_returns_dict_with_required_keys(self, agent_cls, sample_bazi_data):
        agent = agent_cls()
        result = agent.analyze(sample_bazi_data)
        assert isinstance(result, dict)
        assert "agent" in result
        assert "title" in result
        assert "confidence" in result
        assert isinstance(result["confidence"], float)

    @pytest.mark.parametrize("agent_cls", SHIGAN_AGENT_CLASSES)
    def test_analyze_returns_suggestions_list(self, agent_cls, sample_bazi_data):
        agent = agent_cls()
        result = agent.analyze(sample_bazi_data)
        assert "suggestions" in result
        assert isinstance(result["suggestions"], list)
        assert len(result["suggestions"]) > 0

    @pytest.mark.parametrize("agent_cls", SHIGAN_AGENT_CLASSES)
    def test_analyze_with_empty_bazi_data(self, agent_cls, empty_bazi_data):
        agent = agent_cls()
        result = agent.analyze(empty_bazi_data)
        assert isinstance(result, dict)
        assert "agent" in result

    @pytest.mark.parametrize("agent_cls", SHIGAN_AGENT_CLASSES)
    def test_analyze_with_custom_question(self, agent_cls, sample_bazi_data):
        agent = agent_cls()
        question = "我的财运如何？"
        result = agent.analyze(sample_bazi_data, question=question)
        assert isinstance(result, dict)
        assert "agent" in result


# ============================================================================
# QishaAgent 专项测试
# ============================================================================


class TestQishaAgent:
    """七杀·品质裁决 专项测试"""

    def test_analyze_with_shigan_map_containing_qisha(self):
        agent = QishaAgent()
        bazi_data = {
            "shigan_map": {
                "year_gan": "七杀",
                "month_gan": "正官",
                "day_gan": "比肩",
                "hour_gan": "食神",
            }
        }
        result = agent.analyze(bazi_data)
        assert result["verdict"] == "挑战型"
        assert "year柱" in result["qisha_locations"]
        assert result["agent"] == "七杀"

    def test_analyze_with_empty_shigan_map(self):
        agent = QishaAgent()
        result = agent.analyze({"shigan_map": {}})
        assert result["verdict"] == "稳健型"
        assert result["qisha_locations"] == []

    def test_qisha_locations_in_result(self):
        agent = QishaAgent()
        bazi_data = {
            "shigan_map": {
                "year_gan": "七杀",
                "month_gan": "七杀",
                "day_gan": "正官",
                "hour_gan": "七杀",
            }
        }
        result = agent.analyze(bazi_data)
        assert len(result["qisha_locations"]) == 3
        assert "year柱" in result["qisha_locations"]
        assert "month柱" in result["qisha_locations"]
        assert "hour柱" in result["qisha_locations"]

    def test_analyze_confidence(self, sample_bazi_data):
        agent = QishaAgent()
        result = agent.analyze(sample_bazi_data)
        assert result["confidence"] == 0.80


# ============================================================================
# YuanchenAgent 专项测试
# ============================================================================


class TestYuanchenAgent:
    """元辰·本源定位 专项测试"""

    def test_analyze_with_pillars(self):
        agent = YuanchenAgent()
        bazi_data = {
            "pillars": {
                "year": "甲子",
                "month": "丙寅",
                "day": "戊辰",
                "hour": "庚午",
            }
        }
        result = agent.analyze(bazi_data)
        assert "wuxing_distribution" in result
        assert "dominant_element" in result
        assert "weakest_element" in result
        assert isinstance(result["wuxing_distribution"], dict)
        # 甲=木, 丙=火, 戊=土, 庚=金 → 各1个
        assert result["wuxing_distribution"]["木"] == 1
        assert result["wuxing_distribution"]["火"] == 1
        assert result["wuxing_distribution"]["土"] == 1
        assert result["wuxing_distribution"]["金"] == 1
        assert result["wuxing_distribution"]["水"] == 0

    def test_dominant_and_weakest_elements(self):
        agent = YuanchenAgent()
        bazi_data = {
            "pillars": {
                "year": "甲子",
                "month": "乙丑",
                "day": "丙寅",
                "hour": "丁卯",
            }
        }
        # 甲=木, 乙=木, 丙=火, 丁=火 → 木2, 火2, 其他0
        result = agent.analyze(bazi_data)
        # 木和火都是2, max应该返回第一个出现的最大值
        assert result["wuxing_distribution"]["木"] == 2
        assert result["wuxing_distribution"]["火"] == 2

    def test_derive_traits_wood(self):
        agent = YuanchenAgent()
        assert "仁慈" in agent._derive_traits("木")

    def test_derive_traits_fire(self):
        agent = YuanchenAgent()
        assert "热情" in agent._derive_traits("火")

    def test_derive_traits_earth(self):
        agent = YuanchenAgent()
        assert "诚信" in agent._derive_traits("土")

    def test_derive_traits_metal(self):
        agent = YuanchenAgent()
        assert "果断" in agent._derive_traits("金")

    def test_derive_traits_water(self):
        agent = YuanchenAgent()
        assert "智慧" in agent._derive_traits("水")

    def test_derive_traits_unknown_element(self):
        agent = YuanchenAgent()
        assert agent._derive_traits("未知") == "综合型"

    def test_core_traits_in_result(self):
        agent = YuanchenAgent()
        bazi_data = {"pillars": {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚午"}}
        result = agent.analyze(bazi_data)
        assert "core_traits" in result
        assert isinstance(result["core_traits"], str)
        assert len(result["core_traits"]) > 0

    def test_confidence(self):
        agent = YuanchenAgent()
        result = agent.analyze({"pillars": {"year": "甲子"}})
        assert result["confidence"] == 0.85


# ============================================================================
# TaijiAgent 专项测试
# ============================================================================


class TestTaijiAgent:
    """太极·阴阳调和 专项测试"""

    def test_analyze_with_yang_dominant_pillars(self):
        agent = TaijiAgent()
        # 甲=阳, 丙=阳, 戊=阳, 庚=阳 → 全阳
        bazi_data = {
            "pillars": {
                "year": "甲子",
                "month": "丙寅",
                "day": "戊辰",
                "hour": "庚午",
            }
        }
        result = agent.analyze(bazi_data)
        assert result["yang_count"] == 4
        assert result["yin_count"] == 0
        assert result["balance_status"] == "阳盛"

    def test_analyze_with_yin_dominant_pillars(self):
        agent = TaijiAgent()
        # 乙=阴, 丁=阴, 己=阴, 辛=阴 → 全阴
        bazi_data = {
            "pillars": {
                "year": "乙丑",
                "month": "丁卯",
                "day": "己巳",
                "hour": "辛未",
            }
        }
        result = agent.analyze(bazi_data)
        assert result["yang_count"] == 0
        assert result["yin_count"] == 4
        assert result["balance_status"] == "阴盛"

    def test_analyze_with_balanced_pillars(self):
        agent = TaijiAgent()
        # 甲=阳, 乙=阴, 丙=阳, 丁=阴 → 2阳2阴, 平衡
        bazi_data = {
            "pillars": {
                "year": "甲子",
                "month": "乙丑",
                "day": "丙寅",
                "hour": "丁卯",
            }
        }
        result = agent.analyze(bazi_data)
        assert result["yang_count"] == 2
        assert result["yin_count"] == 2
        assert result["balance_status"] == "阴阳平衡"

    def test_analyze_with_diff_1_is_balanced(self):
        agent = TaijiAgent()
        # 甲=阳, 乙=阴, 丙=阳 → 2阳1阴, 差1, 仍为平衡
        bazi_data = {
            "pillars": {
                "year": "甲子",
                "month": "乙丑",
                "day": "丙寅",
            }
        }
        result = agent.analyze(bazi_data)
        assert result["balance_status"] == "阴阳平衡"

    def test_balanced_suggestions(self):
        agent = TaijiAgent()
        bazi_data = {"pillars": {"year": "甲子", "month": "乙丑", "day": "丙寅", "hour": "丁卯"}}
        result = agent.analyze(bazi_data)
        assert "阴阳平衡者" in result["suggestions"][0]

    def test_yang_sheng_suggestions(self):
        agent = TaijiAgent()
        bazi_data = {"pillars": {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚午"}}
        result = agent.analyze(bazi_data)
        assert "阳盛者" in result["suggestions"][0]

    def test_yin_sheng_suggestions(self):
        agent = TaijiAgent()
        bazi_data = {"pillars": {"year": "乙丑", "month": "丁卯", "day": "己巳", "hour": "辛未"}}
        result = agent.analyze(bazi_data)
        assert "阴盛者" in result["suggestions"][0]


# ============================================================================
# SizhuAgent 专项测试
# ============================================================================


class TestSizhuAgent:
    """四柱·五行综合诊断 专项测试"""

    def test_analyze_with_pillars_and_day_master(self):
        agent = SizhuAgent()
        bazi_data = {
            "pillars": {"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "庚午"},
            "day_master": "戊",
        }
        result = agent.analyze(bazi_data)
        assert result["agent"] == "四柱"
        assert result["day_master"] == "戊"
        assert result["pillars"] == bazi_data["pillars"]
        assert "日主戊" in result["analysis"]

    def test_category_is_comprehensive(self):
        agent = SizhuAgent()
        assert agent.category == "综合"

    def test_confidence(self):
        agent = SizhuAgent()
        result = agent.analyze({"pillars": {}, "day_master": ""})
        assert result["confidence"] == 0.85


# ============================================================================
# LiunianAgent 专项测试
# ============================================================================


class TestLiunianAgent:
    """流年·运势趋势预测 专项测试"""

    def test_analyze_basic(self):
        agent = LiunianAgent()
        result = agent.analyze({})
        assert result["agent"] == "流年"
        assert "analysis" in result
        assert "suggestions" in result
        assert len(result["suggestions"]) == 3

    def test_category_is_prediction(self):
        agent = LiunianAgent()
        assert agent.category == "预测"

    def test_confidence(self):
        agent = LiunianAgent()
        result = agent.analyze({})
        assert result["confidence"] == 0.75


# ============================================================================
# 智能体注册表测试
# ============================================================================


class TestAgentRegistries:
    """ALL_SHEN_AGENTS / COMPREHENSIVE_AGENTS / ALL_AGENTS 测试"""

    def test_12_shigan_agents_in_all_shen_agents(self):
        assert len(ALL_SHEN_AGENTS) == 12
        expected_names = {
            "七杀", "伤官", "偏印", "偏财", "元辰", "劫财",
            "太极", "正印", "正官", "正财", "比肩", "食神",
        }
        assert set(ALL_SHEN_AGENTS.keys()) == expected_names

    def test_2_comprehensive_agents(self):
        assert len(COMPREHENSIVE_AGENTS) == 2
        assert "四柱" in COMPREHENSIVE_AGENTS
        assert "流年" in COMPREHENSIVE_AGENTS

    def test_14_total_in_all_agents(self):
        assert len(ALL_AGENTS) == 14

    def test_all_are_shen_agent_instances(self):
        for agent in ALL_AGENTS.values():
            assert isinstance(agent, ShenAgent)

    def test_all_shigan_agents_are_shen_agent_instances(self):
        for agent in ALL_SHEN_AGENTS.values():
            assert isinstance(agent, ShenAgent)

    def test_all_comprehensive_agents_are_shen_agent_instances(self):
        for agent in COMPREHENSIVE_AGENTS.values():
            assert isinstance(agent, ShenAgent)


# ============================================================================
# get_agent() 测试
# ============================================================================


class TestGetAgent:
    """get_agent() 函数测试"""

    def test_valid_agent_name_returns_agent(self):
        agent = get_agent("七杀")
        assert agent is not None
        assert isinstance(agent, QishaAgent)

    def test_invalid_name_returns_none(self):
        assert get_agent("不存在的智能体") is None

    @pytest.mark.parametrize("name", [
        "七杀", "伤官", "偏印", "偏财", "元辰", "劫财",
        "太极", "正印", "正官", "正财", "比肩", "食神",
        "四柱", "流年",
    ])
    def test_each_of_14_agents_can_be_retrieved(self, name):
        agent = get_agent(name)
        assert agent is not None
        assert agent.name == name


# ============================================================================
# list_agents() 测试
# ============================================================================


class TestListAgents:
    """list_agents() 函数测试"""

    def test_returns_list_of_14_dicts(self):
        agents = list_agents()
        assert isinstance(agents, list)
        assert len(agents) == 14

    def test_each_dict_has_required_keys(self):
        agents = list_agents()
        for a in agents:
            assert "name" in a
            assert "title" in a
            assert "description" in a
            assert "category" in a

    def test_all_names_are_present(self):
        agents = list_agents()
        names = {a["name"] for a in agents}
        expected = {
            "七杀", "伤官", "偏印", "偏财", "元辰", "劫财",
            "太极", "正印", "正官", "正财", "比肩", "食神",
            "四柱", "流年",
        }
        assert names == expected


# ============================================================================
# analyze_with_agents() 测试
# ============================================================================


class TestAnalyzeWithAgents:
    """analyze_with_agents() 函数测试"""

    def test_with_specific_agent_names(self, sample_bazi_data):
        result = analyze_with_agents(sample_bazi_data, agent_names=["七杀", "正官"])
        assert result["count"] == 2
        assert len(result["agents"]) == 2
        agent_names_in_result = {r["agent"] for r in result["agents"]}
        assert agent_names_in_result == {"七杀", "正官"}

    def test_with_all_agents_default(self, sample_bazi_data):
        result = analyze_with_agents(sample_bazi_data)
        assert result["count"] == 12  # 默认使用 ALL_SHEN_AGENTS
        assert len(result["agents"]) == 12

    def test_with_invalid_agent_name_skipped(self, sample_bazi_data):
        result = analyze_with_agents(sample_bazi_data, agent_names=["七杀", "不存在"])
        assert result["count"] == 1

    def test_with_empty_agent_names_list(self, sample_bazi_data):
        # 空列表被视为 falsy，回退到默认全部十神智能体
        result = analyze_with_agents(sample_bazi_data, agent_names=[])
        assert result["count"] == 12
        assert len(result["agents"]) == 12

    def test_result_has_summary(self, sample_bazi_data):
        result = analyze_with_agents(sample_bazi_data, agent_names=["七杀"])
        assert "summary" in result
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_with_question_parameter(self, sample_bazi_data):
        result = analyze_with_agents(
            sample_bazi_data, agent_names=["七杀"], question="今年运势如何？"
        )
        assert result["count"] == 1


# ============================================================================
# get_all_agent_tool_specs() 测试
# ============================================================================


class TestGetAllAgentToolSpecs:
    """get_all_agent_tool_specs() 函数测试"""

    def test_returns_14_specs(self):
        specs = get_all_agent_tool_specs()
        assert len(specs) == 14

    def test_each_spec_has_type_function(self):
        specs = get_all_agent_tool_specs()
        for spec in specs:
            assert spec["type"] == "function"

    def test_each_spec_function_name_starts_with_shen(self):
        specs = get_all_agent_tool_specs()
        for spec in specs:
            name = spec["function"]["name"]
            assert name.startswith("shen_"), f"'{name}' 不以 shen_ 开头"

    def test_each_spec_has_parameters(self):
        specs = get_all_agent_tool_specs()
        for spec in specs:
            assert "parameters" in spec["function"]
            assert "bazi_data" in spec["function"]["parameters"]["properties"]


# ============================================================================
# agent_tool_dispatcher() 测试
# ============================================================================


class TestAgentToolDispatcher:
    """agent_tool_dispatcher() 函数测试"""

    def test_valid_agent_name_dispatches_correctly(self, sample_bazi_data):
        result = agent_tool_dispatcher("七杀", {"bazi_data": sample_bazi_data})
        assert result["tool"] == "shen_七杀"
        assert "result" in result
        assert result["result"]["agent"] == "七杀"

    def test_invalid_agent_name_returns_error_dict(self):
        result = agent_tool_dispatcher("不存在", {"bazi_data": {}})
        assert result["tool"] == "shen_不存在"
        assert "不存在" in result["result"]

    def test_params_passed_through_to_analyze(self, sample_bazi_data):
        result = agent_tool_dispatcher(
            "四柱",
            {
                "bazi_data": {
                    "pillars": {"year": "甲子"},
                    "day_master": "甲",
                },
                "question": "综合运势",
            },
        )
        assert result["tool"] == "shen_四柱"
        assert result["result"]["day_master"] == "甲"

    def test_empty_params_defaults(self):
        result = agent_tool_dispatcher("正官", {})
        assert result["tool"] == "shen_正官"
        assert "result" in result

    def test_all_14_agents_dispatch(self):
        for name in ALL_AGENTS:
            result = agent_tool_dispatcher(name, {"bazi_data": {}})
            assert result["tool"] == f"shen_{name}"
            assert "result" in result