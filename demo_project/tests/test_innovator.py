"""tests/test_innovator.py — 破界创新器 Innovator 模块综合测试"""

import json
import sys
import warnings
from unittest.mock import MagicMock, Mock, patch

import pytest

from tengod.伤官_破界创新.innovator import Idea, InnovationType, Innovator


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _mock_generation_config():
    """为 elaborate_idea / evaluate_with_llm 中的 'from 食神_创生输出 import GenerationConfig' 提供 mock 模块"""
    mock_cfg_module = Mock()
    mock_cfg = Mock()
    mock_cfg_module.GenerationConfig = Mock(return_value=mock_cfg)
    old = sys.modules.get("食神_创生输出")
    sys.modules["食神_创生输出"] = mock_cfg_module
    yield
    if old is not None:
        sys.modules["食神_创生输出"] = old
    else:
        sys.modules.pop("食神_创生输出", None)


@pytest.fixture
def innovator():
    """返回一个新的 Innovator 实例"""
    return Innovator()


@pytest.fixture
def sample_idea():
    """返回一个示例 Idea"""
    return Idea(
        id="test001",
        title="测试创意",
        description="这是一个测试创意",
        innovation_type=InnovationType.COMBINATION,
        feasibility=0.8,
        impact=0.9,
        tags=["测试", "创意"],
    )


@pytest.fixture
def mock_generator():
    """返回一个 Mock 内容生成器（食神）"""
    gen = Mock()
    gen.generate = Mock()
    return gen


@pytest.fixture
def mock_kb():
    """返回一个 Mock 知识库（正财）"""
    kb = Mock()
    node = Mock()
    node.id = "kb_node_001"
    node.name = "kb_node_name"
    node.node_type = "idea_combination"
    kb.add_node = Mock(return_value=node)
    return kb


@pytest.fixture
def populated_innovator(innovator):
    """返回一个已填充多个创意的 Innovator"""
    innovator.combine(["A", "B"])
    innovator.combine(["C", "D", "E"])
    innovator.transfer("生物学", "计算机科学")
    innovator.reverse("传统教育模式")
    return innovator


# ── InnovationType 枚举测试 ────────────────────────────────────


class TestInnovationType:
    """InnovationType 枚举测试"""

    def test_enum_values(self):
        """测试枚举值"""
        assert InnovationType.COMBINATION.value == "combination"
        assert InnovationType.TRANSFER.value == "transfer"
        assert InnovationType.REVERSE.value == "reverse"
        assert InnovationType.BREAKTHROUGH.value == "breakthrough"

    def test_enum_members_count(self):
        """测试枚举成员数量"""
        assert len(InnovationType) == 4

    def test_enum_member_names(self):
        """测试枚举成员名称"""
        names = {m.name for m in InnovationType}
        assert names == {"COMBINATION", "TRANSFER", "REVERSE", "BREAKTHROUGH"}


# ── Idea 数据类测试 ────────────────────────────────────────────


class TestIdea:
    """Idea 数据类测试"""

    def test_create_idea(self):
        """测试 Idea 创建"""
        idea = Idea(
            id="id001",
            title="创新方案",
            description="描述内容",
            innovation_type=InnovationType.TRANSFER,
            feasibility=0.7,
            impact=0.8,
        )
        assert idea.id == "id001"
        assert idea.title == "创新方案"
        assert idea.description == "描述内容"
        assert idea.innovation_type == InnovationType.TRANSFER
        assert idea.feasibility == 0.7
        assert idea.impact == 0.8

    def test_score_property(self):
        """测试 score 属性（feasibility*0.4 + impact*0.6）"""
        idea = Idea(
            id="id002",
            title="评分测试",
            description="测试评分",
            innovation_type=InnovationType.COMBINATION,
            feasibility=0.5,
            impact=1.0,
        )
        expected = 0.5 * 0.4 + 1.0 * 0.6  # 0.2 + 0.6 = 0.8
        assert idea.score == pytest.approx(expected)

    def test_score_zero(self):
        """测试 score 为零的情况"""
        idea = Idea(
            id="id003",
            title="零分",
            description="",
            innovation_type=InnovationType.REVERSE,
            feasibility=0.0,
            impact=0.0,
        )
        assert idea.score == 0.0

    def test_default_values(self):
        """测试默认值"""
        idea = Idea(
            id="id004",
            title="默认值测试",
            description="测试默认值",
            innovation_type=InnovationType.BREAKTHROUGH,
            feasibility=0.5,
            impact=0.5,
        )
        # created_at 应为 float
        assert isinstance(idea.created_at, float)
        assert idea.created_at > 0
        # tags 默认为空列表
        assert idea.tags == []

    def test_tags_custom(self):
        """测试自定义 tags"""
        idea = Idea(
            id="id005",
            title="标签测试",
            description="",
            innovation_type=InnovationType.COMBINATION,
            feasibility=0.5,
            impact=0.5,
            tags=["AI", "教育", "创新"],
        )
        assert idea.tags == ["AI", "教育", "创新"]
        assert len(idea.tags) == 3

    def test_score_high_feasibility_low_impact(self):
        """测试高可行性低影响"""
        idea = Idea(
            id="id006",
            title="",
            description="",
            innovation_type=InnovationType.COMBINATION,
            feasibility=1.0,
            impact=0.0,
        )
        assert idea.score == 0.4

    def test_score_low_feasibility_high_impact(self):
        """测试低可行性高影响"""
        idea = Idea(
            id="id007",
            title="",
            description="",
            innovation_type=InnovationType.COMBINATION,
            feasibility=0.0,
            impact=1.0,
        )
        assert idea.score == 0.6


# ── Innovator 基础方法测试 ─────────────────────────────────────


class TestInnovatorBasic:
    """Innovator 基础方法测试"""

    def test_init_empty(self, innovator):
        """测试初始化后 ideas 为空"""
        assert innovator._ideas == []

    # ── combine ──

    def test_combine_basic(self, innovator):
        """测试基本组合创新"""
        idea = innovator.combine(["AI", "教育"])
        assert idea.innovation_type == InnovationType.COMBINATION
        assert "组合" in idea.title
        assert "AI" in idea.title
        assert "教育" in idea.title
        assert idea.feasibility == 0.7
        assert idea.impact == 0.7
        assert idea.tags == ["AI", "教育"]
        assert len(innovator._ideas) == 1

    def test_combine_multiple_items(self, innovator):
        """测试多项组合"""
        idea = innovator.combine(["A", "B", "C", "D"])
        assert idea.tags == ["A", "B", "C", "D"]
        assert "A × B × C × D" in idea.title

    def test_combine_with_description(self, innovator):
        """测试带自定义描述的组合"""
        idea = innovator.combine(["X", "Y"], description="自定义组合描述")
        assert idea.description == "自定义组合描述"

    def test_combine_without_description(self, innovator):
        """测试不带描述的默认描述生成"""
        idea = innovator.combine(["X", "Y"])
        assert "X 与 Y" in idea.description

    def test_combine_single_item(self, innovator):
        """测试单个元素组合"""
        idea = innovator.combine(["独立元素"])
        assert idea.tags == ["独立元素"]
        assert "独立元素" in idea.title

    def test_combine_empty_items(self, innovator):
        """测试空列表组合"""
        idea = innovator.combine([])
        assert idea.innovation_type == InnovationType.COMBINATION
        assert idea.tags == []

    def test_combine_special_characters(self, innovator):
        """测试特殊字符组合"""
        idea = innovator.combine(["测试@#$", "数据%^&"])
        assert idea.tags == ["测试@#$", "数据%^&"]

    # ── transfer ──

    def test_transfer_basic(self, innovator):
        """测试基本迁移创新"""
        idea = innovator.transfer("生物学", "计算机科学")
        assert idea.innovation_type == InnovationType.TRANSFER
        assert "迁移" in idea.title
        assert "生物学" in idea.title
        assert "计算机科学" in idea.title
        assert idea.feasibility == 0.6
        assert idea.impact == 0.8
        assert idea.tags == ["生物学", "计算机科学"]
        assert len(innovator._ideas) == 1

    def test_transfer_with_description(self, innovator):
        """测试带自定义描述的迁移"""
        idea = innovator.transfer("物理", "化学", description="自定义描述")
        assert idea.description == "自定义描述"

    def test_transfer_without_description(self, innovator):
        """测试默认描述生成"""
        idea = innovator.transfer("源", "目标")
        assert "源" in idea.description
        assert "目标" in idea.description

    # ── reverse ──

    def test_reverse_basic(self, innovator):
        """测试基本逆向创新"""
        idea = innovator.reverse("传统教育模式")
        assert idea.innovation_type == InnovationType.REVERSE
        assert "逆向" in idea.title
        assert "传统教育模式" in idea.title
        assert idea.feasibility == 0.5
        assert idea.impact == 0.9
        assert idea.tags == ["逆向"]
        assert len(innovator._ideas) == 1

    def test_reverse_with_description(self, innovator):
        """测试带自定义描述的逆向"""
        idea = innovator.reverse("旧模式", description="自定义描述")
        assert idea.description == "自定义描述"

    def test_reverse_without_description(self, innovator):
        """测试默认描述生成"""
        idea = innovator.reverse("某模式")
        assert "某模式" in idea.description
        assert "反向" in idea.description

    # ── top_ideas ──

    def test_top_ideas_default(self, populated_innovator):
        """测试默认 n=5 的 top_ideas"""
        top = populated_innovator.top_ideas()
        assert len(top) <= 5
        # 验证排序：得分高的在前
        for i in range(len(top) - 1):
            assert top[i].score >= top[i + 1].score

    def test_top_ideas_custom_n(self, populated_innovator):
        """测试自定义 n"""
        top = populated_innovator.top_ideas(n=2)
        assert len(top) == 2

    def test_top_ideas_n_larger_than_list(self, populated_innovator):
        """测试 n 大于列表长度"""
        top = populated_innovator.top_ideas(n=100)
        assert len(top) == len(populated_innovator._ideas)

    def test_top_ideas_empty(self, innovator):
        """测试空列表的 top_ideas"""
        top = innovator.top_ideas()
        assert top == []

    def test_top_ideas_n_zero(self, innovator):
        """测试 n=0"""
        innovator.combine(["A", "B"])
        top = innovator.top_ideas(n=0)
        assert top == []

    # ── list_by_type ──

    def test_list_by_type_combination(self, populated_innovator):
        """测试按 COMBINATION 类型筛选"""
        result = populated_innovator.list_by_type(InnovationType.COMBINATION)
        assert len(result) == 2
        for idea in result:
            assert idea.innovation_type == InnovationType.COMBINATION

    def test_list_by_type_transfer(self, populated_innovator):
        """测试按 TRANSFER 类型筛选"""
        result = populated_innovator.list_by_type(InnovationType.TRANSFER)
        assert len(result) == 1

    def test_list_by_type_reverse(self, populated_innovator):
        """测试按 REVERSE 类型筛选"""
        result = populated_innovator.list_by_type(InnovationType.REVERSE)
        assert len(result) == 1

    def test_list_by_type_empty(self, innovator):
        """测试空列表筛选"""
        result = innovator.list_by_type(InnovationType.COMBINATION)
        assert result == []

    def test_list_by_type_no_match(self, populated_innovator):
        """测试无匹配类型"""
        result = populated_innovator.list_by_type(InnovationType.BREAKTHROUGH)
        assert result == []

    # ── report ──

    def test_report_empty(self, innovator):
        """测试空状态报告"""
        report = innovator.report()
        assert report["total"] == 0
        assert report["version"] == "1.4.0"
        for itype in InnovationType:
            assert report["by_type"][itype.value] == 0
        assert report["top_ideas"] == []

    def test_report_structure(self, populated_innovator):
        """测试报告结构"""
        report = populated_innovator.report()
        assert "total" in report
        assert "by_type" in report
        assert "top_ideas" in report
        assert "version" in report
        assert report["total"] == 4

    def test_report_by_type_counts(self, populated_innovator):
        """测试按类型统计"""
        report = populated_innovator.report()
        assert report["by_type"]["combination"] == 2
        assert report["by_type"]["transfer"] == 1
        assert report["by_type"]["reverse"] == 1
        assert report["by_type"]["breakthrough"] == 0

    def test_report_top_ideas_format(self, populated_innovator):
        """测试 top_ideas 格式"""
        report = populated_innovator.report()
        for idea_dict in report["top_ideas"]:
            assert "id" in idea_dict
            assert "title" in idea_dict
            assert "score" in idea_dict
            assert "type" in idea_dict
            assert isinstance(idea_dict["score"], float)


# ── set_generator 测试 ─────────────────────────────────────────


class TestSetGenerator:
    """set_generator 测试"""

    def test_set_generator(self, innovator, mock_generator):
        """测试设置生成器"""
        innovator.set_generator(mock_generator)
        assert innovator._generator is mock_generator

    def test_overwrite_generator(self, innovator, mock_generator):
        """测试覆盖生成器"""
        gen1 = Mock()
        innovator.set_generator(gen1)
        assert innovator._generator is gen1
        innovator.set_generator(mock_generator)
        assert innovator._generator is mock_generator


# ── generate_with_llm 测试 ────────────────────────────────────


class TestGenerateWithLLM:
    """generate_with_llm 测试"""

    def test_generate_valid_json(self, innovator, mock_generator):
        """测试 Mock 返回有效 JSON"""
        innovator.set_generator(mock_generator)
        mock_generator.generate.return_value = json.dumps(
            {
                "title": "AI融合方案",
                "description": "利用AI技术融合传统教育",
                "innovation_type": "组合",
                "feasibility": 0.85,
                "impact": 0.9,
            },
            ensure_ascii=False,
        )

        idea = innovator.generate_with_llm("AI+教育")
        assert idea is not None
        assert idea.title == "AI融合方案"
        assert idea.innovation_type == InnovationType.COMBINATION
        assert idea.feasibility == 0.85
        assert idea.impact == 0.9
        assert len(innovator._ideas) == 1

    def test_generate_valid_json_with_braces(self, innovator, mock_generator):
        """测试 JSON 中包含额外文本（带大括号的）"""
        innovator.set_generator(mock_generator)
        mock_generator.generate.return_value = (
            '一些前缀文本 {"title": "新方案", "description": "描述", '
            '"innovation_type": "突破", "feasibility": 0.7, "impact": 0.8} 后缀'
        )

        idea = innovator.generate_with_llm("测试")
        assert idea is not None
        assert idea.title == "新方案"
        assert idea.innovation_type == InnovationType.BREAKTHROUGH

    def test_generate_invalid_json_fallback(self, innovator, mock_generator):
        """测试返回无效 JSON 时的 fallback"""
        innovator.set_generator(mock_generator)
        mock_generator.generate.return_value = "这不是JSON"

        idea = innovator.generate_with_llm("测试prompt")
        assert idea is not None
        assert idea.title == "LLM生成"
        assert idea.innovation_type == InnovationType.COMBINATION
        assert idea.feasibility == 0.5
        assert idea.impact == 0.5
        assert len(innovator._ideas) == 1

    def test_generate_exception_fallback(self, innovator, mock_generator):
        """测试生成器抛出异常时的 fallback"""
        innovator.set_generator(mock_generator)
        mock_generator.generate.side_effect = RuntimeError("生成失败")

        idea = innovator.generate_with_llm("任何prompt")
        assert idea is not None
        assert idea.title == "LLM生成"
        assert idea.innovation_type == InnovationType.COMBINATION

    def test_generate_without_generator(self, innovator):
        """测试未设置生成器时的警告"""
        with pytest.warns(UserWarning, match="generator 未注入"):
            idea = innovator.generate_with_llm("测试")
        assert idea is None

    def test_generate_with_none_generator(self, innovator):
        """测试生成器为 None"""
        innovator._generator = None
        with pytest.warns(UserWarning, match="generator 未注入"):
            idea = innovator.generate_with_llm("测试")
        assert idea is None

    def test_generate_all_innovation_types(self, innovator, mock_generator):
        """测试所有创新类型的映射"""
        innovator.set_generator(mock_generator)
        type_map = {
            "组合": InnovationType.COMBINATION,
            "迁移": InnovationType.TRANSFER,
            "逆向": InnovationType.REVERSE,
            "突破": InnovationType.BREAKTHROUGH,
        }

        for cn_type, expected_enum in type_map.items():
            mock_generator.generate.return_value = json.dumps(
                {
                    "title": "测试",
                    "description": "测试",
                    "innovation_type": cn_type,
                    "feasibility": 0.5,
                    "impact": 0.5,
                },
                ensure_ascii=False,
            )
            idea = innovator.generate_with_llm("测试")
            assert idea.innovation_type == expected_enum

    def test_generate_unknown_type_defaults(self, innovator, mock_generator):
        """测试未知创新类型默认为 COMBINATION"""
        innovator.set_generator(mock_generator)
        mock_generator.generate.return_value = json.dumps(
            {
                "title": "测试",
                "description": "测试",
                "innovation_type": "未知类型",
                "feasibility": 0.5,
                "impact": 0.5,
            },
            ensure_ascii=False,
        )
        idea = innovator.generate_with_llm("测试")
        assert idea.innovation_type == InnovationType.COMBINATION

    def test_generate_missing_fields_defaults(self, innovator, mock_generator):
        """测试缺失字段使用默认值"""
        innovator.set_generator(mock_generator)
        mock_generator.generate.return_value = json.dumps({"title": "仅标题"})

        idea = innovator.generate_with_llm("测试")
        assert idea.description == ""
        assert idea.feasibility == 0.5
        assert idea.impact == 0.5

    def test_generate_with_style(self, innovator, mock_generator):
        """测试 style 参数传递"""
        innovator.set_generator(mock_generator)
        mock_generator.generate.return_value = json.dumps(
            {
                "title": "测试",
                "description": "测试",
                "innovation_type": "组合",
                "feasibility": 0.5,
                "impact": 0.5,
            },
            ensure_ascii=False,
        )
        innovator.generate_with_llm("测试", style="analytical")
        mock_generator.generate.assert_called_once()
        call_kwargs = mock_generator.generate.call_args[1]
        assert call_kwargs.get("style") == "analytical"


# ── elaborate_idea 测试 ────────────────────────────────────────


class TestElaborateIdea:
    """elaborate_idea 测试"""

    def test_elaborate_valid_idea(self, innovator, mock_generator):
        """测试对有效创意的扩展"""
        idea = innovator.combine(["AI", "医疗"])
        innovator.set_generator(mock_generator)
        mock_generator.generate.return_value = "详细方案：步骤1、步骤2、步骤3"

        result = innovator.elaborate_idea(idea.id, style="detailed")

        assert result == "详细方案：步骤1、步骤2、步骤3"
        mock_generator.generate.assert_called_once()

    def test_elaborate_invalid_idea(self, innovator, mock_generator):
        """测试对不存在的创意扩展"""
        innovator.set_generator(mock_generator)
        result = innovator.elaborate_idea("nonexistent_id")
        assert result is None

    def test_elaborate_without_generator(self, innovator):
        """测试未设置生成器"""
        idea = innovator.combine(["A", "B"])
        with pytest.warns(UserWarning, match="generator 未注入"):
            result = innovator.elaborate_idea(idea.id)
        assert result is None

    def test_elaborate_exception_handling(self, innovator, mock_generator):
        """测试生成器抛出异常"""
        idea = innovator.combine(["A", "B"])
        innovator.set_generator(mock_generator)
        mock_generator.generate.side_effect = ValueError("模拟错误")

        result = innovator.elaborate_idea(idea.id)

        assert result is not None
        assert "方案扩展失败" in result
        assert "模拟错误" in result


# ── evaluate_with_llm 测试 ─────────────────────────────────────


class TestEvaluateWithLLM:
    """evaluate_with_llm 测试"""

    def test_evaluate_valid_idea(self, innovator, mock_generator):
        """测试评估有效创意"""
        idea = innovator.combine(["区块链", "供应链"])
        innovator.set_generator(mock_generator)
        mock_generator.generate.return_value = json.dumps(
            {
                "innovation": 0.8,
                "feasibility": 0.6,
                "risk": 0.4,
                "impact": 0.9,
                "suggestions": "建议增加试点",
            },
            ensure_ascii=False,
        )

        result = innovator.evaluate_with_llm(idea.id)

        assert result is not None
        assert result["innovation"] == 0.8
        assert result["feasibility"] == 0.6
        assert result["risk"] == 0.4
        assert result["impact"] == 0.9
        assert result["suggestions"] == "建议增加试点"

    def test_evaluate_invalid_idea(self, innovator, mock_generator):
        """测试评估不存在的创意"""
        innovator.set_generator(mock_generator)
        result = innovator.evaluate_with_llm("bad_id")
        assert result is None

    def test_evaluate_without_generator(self, innovator):
        """测试未设置生成器"""
        idea = innovator.combine(["A", "B"])
        with pytest.warns(UserWarning, match="generator 未注入"):
            result = innovator.evaluate_with_llm(idea.id)
        assert result is None

    def test_evaluate_json_with_extra_text(self, innovator, mock_generator):
        """测试 JSON 包含额外文本"""
        idea = innovator.combine(["测试"])
        innovator.set_generator(mock_generator)
        mock_generator.generate.return_value = (
            '评估结果：{"innovation": 0.7, "feasibility": 0.5, '
            '"risk": 0.3, "impact": 0.8, "suggestions": "good"}'
        )

        result = innovator.evaluate_with_llm(idea.id)

        assert result is not None
        assert result["innovation"] == 0.7

    def test_evaluate_exception_fallback(self, innovator, mock_generator):
        """测试异常时的 fallback 评估"""
        idea = innovator.combine(["A", "B"])
        innovator.set_generator(mock_generator)
        mock_generator.generate.side_effect = Exception("评估异常")

        result = innovator.evaluate_with_llm(idea.id)

        assert result is not None
        assert result["suggestions"] == "评估失败"
        assert result["innovation"] == idea.score

    def test_evaluate_clean_json_direct_parse(self, innovator, mock_generator):
        """测试纯 JSON 不包含 innovation 键时直接解析（走 else 分支）"""
        idea = innovator.combine(["测试"])
        innovator.set_generator(mock_generator)
        # JSON 不含 "innovation" 键，正则匹配不到，走 else 分支直接 json.loads
        mock_generator.generate.return_value = (
            '{"feasibility": 0.55, "risk": 0.35, "impact": 0.85, "suggestions": "ok"}'
        )

        result = innovator.evaluate_with_llm(idea.id)

        assert result is not None
        assert result["impact"] == 0.85


# ── idea_to_knowledge 测试 ─────────────────────────────────────


class TestIdeaToKnowledge:
    """idea_to_knowledge 测试"""

    def test_valid_idea_to_kb(self, innovator, mock_kb):
        """测试将有效创意存入知识库"""
        idea = innovator.combine(["AI", "金融"])
        result = innovator.idea_to_knowledge(idea.id, mock_kb)

        assert result is not None
        assert result["id"] == "kb_node_001"
        assert result["name"] == "kb_node_name"
        assert result["node_type"] == "idea_combination"

        mock_kb.add_node.assert_called_once()
        call_kwargs = mock_kb.add_node.call_args[1]
        assert call_kwargs["name"] == f"[创意]{idea.title}"
        assert call_kwargs["node_type"] == f"idea_{idea.innovation_type.value}"
        assert "tags" in call_kwargs["properties"]
        assert call_kwargs["properties"]["innovation_type"] == "combination"

    def test_invalid_idea_to_kb(self, innovator, mock_kb):
        """测试将不存在的创意存入知识库"""
        result = innovator.idea_to_knowledge("bad_id", mock_kb)
        assert result is None
        mock_kb.add_node.assert_not_called()


# ── pipeline 测试 ──────────────────────────────────────────────


class TestPipeline:
    """pipeline 测试"""

    def test_pipeline_without_llm(self, innovator):
        """测试不使用 LLM 的 pipeline"""
        result = innovator.pipeline(["A", "B", "C"], use_llm=False)
        assert result["idea_id"] is not None
        assert "组合" in result["title"]
        assert "steps" in result
        assert len(innovator._ideas) == 1

    def test_pipeline_with_llm(self, innovator, mock_generator):
        """测试使用 LLM 的 pipeline"""
        innovator.set_generator(mock_generator)
        mock_generator.generate.return_value = json.dumps(
            {
                "title": "LLM方案",
                "description": "LLM生成的方案",
                "innovation_type": "组合",
                "feasibility": 0.8,
                "impact": 0.7,
            },
            ensure_ascii=False,
        )

        result = innovator.pipeline(["A", "B", "C"], use_llm=True)

        assert result["idea_id"] is not None
        assert "LLM方案" in result["title"]

    def test_pipeline_with_llm_and_kb(self, innovator, mock_generator, mock_kb):
        """测试完整 pipeline（LLM + KB）"""
        innovator.set_generator(mock_generator)
        mock_generator.generate.return_value = json.dumps(
            {
                "title": "完整方案",
                "description": "完整描述",
                "innovation_type": "组合",
                "feasibility": 0.9,
                "impact": 0.8,
            },
            ensure_ascii=False,
        )

        result = innovator.pipeline(
            ["A", "B"], use_llm=True, save_to_kb=mock_kb
        )

        assert result["idea_id"] is not None
        assert result["knowledge_saved"] is True

    def test_pipeline_without_llm_with_kb(self, innovator, mock_kb):
        """测试不用 LLM 但存入 KB"""
        result = innovator.pipeline(
            ["A", "B"], use_llm=False, save_to_kb=mock_kb
        )
        assert result["idea_id"] is not None
        assert result["knowledge_saved"] is True

    def test_pipeline_llm_returns_none(self, innovator):
        """测试当 use_llm=True 但无 generator 时，回退到 combine"""
        # use_llm=True 但没设置 generator，hasattr 检查为 False，回退到 combine
        result = innovator.pipeline(["A", "B"], use_llm=True)
        assert result["idea_id"] is not None
        assert "组合" in result["title"]

    def test_pipeline_llm_returns_none_with_generator(self, innovator, mock_generator):
        """测试 pipeline 中 generate_with_llm 返回 None 时的失败处理"""
        innovator.set_generator(mock_generator)
        mock_generator.generate.return_value = None

        # Mock generate_with_llm 返回 None，触发 idea is None 分支
        with patch.object(innovator, "generate_with_llm", return_value=None):
            result = innovator.pipeline(["A", "B"], use_llm=True)

        assert result["status"] == "failed"
        assert result["reason"] == "创意生成失败"

    def test_pipeline_default_use_llm(self, innovator):
        """测试默认 use_llm=True（无 generator 则 fallback 到 combine）"""
        # 没有 generator，所以 use_llm=True 但 hasattr 判断为 False，走 combine 分支
        result = innovator.pipeline(["A", "B"])
        assert result["idea_id"] is not None
        assert "组合" in result["title"]


# ── 边界与集成测试 ──────────────────────────────────────────────


class TestEdgeCases:
    """边界与集成测试"""

    def test_multiple_operations_order(self, innovator):
        """测试多次操作后数据一致性"""
        innovator.combine(["A", "B"])
        innovator.transfer("X", "Y")
        innovator.reverse("Z")
        innovator.combine(["C", "D"])

        assert len(innovator._ideas) == 4
        assert len(innovator.list_by_type(InnovationType.COMBINATION)) == 2
        assert len(innovator.list_by_type(InnovationType.TRANSFER)) == 1
        assert len(innovator.list_by_type(InnovationType.REVERSE)) == 1

    def test_top_ideas_ordering(self, innovator):
        """测试 top_ideas 严格按分数排序"""
        # 手动创建不同分数的 Idea（通过 combine/transfer/reverse）
        # combine: 0.7*0.4 + 0.7*0.6 = 0.7
        # transfer: 0.6*0.4 + 0.8*0.6 = 0.72
        # reverse: 0.5*0.4 + 0.9*0.6 = 0.74
        innovator.combine(["A", "B"])  # score 0.7
        innovator.transfer("X", "Y")  # score 0.72
        innovator.reverse("Z")  # score 0.74

        top = innovator.top_ideas()
        # 最高分应该是 reverse (0.74)
        assert top[0].innovation_type == InnovationType.REVERSE
        assert top[1].innovation_type == InnovationType.TRANSFER
        assert top[2].innovation_type == InnovationType.COMBINATION

    def test_idea_id_uniqueness(self, innovator):
        """测试每个创意 ID 唯一"""
        ids = set()
        for _ in range(20):
            idea = innovator.combine(["X"])
            ids.add(idea.id)
        assert len(ids) == 20

    def test_combine_with_unicode(self, innovator):
        """测试中文和特殊 Unicode 字符"""
        idea = innovator.combine(["中文字符", "日本語", "🚀✨"])
        assert idea.innovation_type == InnovationType.COMBINATION
        assert "中文字符" in idea.title
        assert "日本語" in idea.title
        assert "🚀✨" in idea.title

    def test_report_after_llm_generation(self, innovator, mock_generator):
        """测试 LLM 生成后报告包含新创意"""
        innovator.set_generator(mock_generator)
        mock_generator.generate.return_value = json.dumps(
            {
                "title": "LLM创意",
                "description": "LLM描述",
                "innovation_type": "突破",
                "feasibility": 0.9,
                "impact": 0.95,
            },
            ensure_ascii=False,
        )
        innovator.generate_with_llm("测试")
        report = innovator.report()
        assert report["total"] == 1
        assert report["by_type"]["breakthrough"] == 1

    def test_generate_with_llm_clean_json(self, innovator, mock_generator):
        """测试纯 JSON 返回值（无额外文本）"""
        innovator.set_generator(mock_generator)
        mock_generator.generate.return_value = (
            '{"title": "纯JSON方案", "description": "描述", '
            '"innovation_type": "迁移", "feasibility": 0.6, "impact": 0.7}'
        )
        idea = innovator.generate_with_llm("测试")
        assert idea.title == "纯JSON方案"
        assert idea.innovation_type == InnovationType.TRANSFER