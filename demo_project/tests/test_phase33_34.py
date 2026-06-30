"""
test_phase33_34.py — Phase 3 MCP服务化与可视化测试 v2.33.0 → v2.34.0
========================================================================
测试覆盖：
  - mcp_gate_server.py: MCP工具定义、judge_unit、judge_all_gates、五行生克查询
  - mcp_cognitive_server.py: TBCE查询、Oracle投影、推测解码、测地线
  - dashboard.py: 仪表盘数据、十二神状态、TBCE雷达图、五行矩阵
  - report_generator.py: 报告生成、Markdown/JSON输出、元素分析
"""

import pytest
import os
import sys
import json
import math
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tengod.mcp_gate_server import (
    MCPGateServer, MCP_GATE_TOOLS,
    get_mcp_gate_server, reset_mcp_gate_server,
)
from tengod.mcp_cognitive_server import (
    MCPCognitiveServer, MCP_COGNITIVE_TOOLS, COGNITIVE_LAYERS,
    get_mcp_cognitive_server, reset_mcp_cognitive_server,
)
from tengod.dashboard import (
    DashboardData, DashboardGenerator,
    get_dashboard_generator, reset_dashboard_generator,
)
from tengod.report_generator import (
    GateReportSection, GateReport, ReportGenerator,
    get_report_generator, reset_report_generator,
)
from tengod.tbce_unit import GateState


# ============================================================================
# 测试夹具
# ============================================================================

@pytest.fixture(autouse=True)
def reset_all():
    reset_mcp_gate_server()
    reset_mcp_cognitive_server()
    reset_dashboard_generator()
    reset_report_generator()
    yield
    reset_mcp_gate_server()
    reset_mcp_cognitive_server()
    reset_dashboard_generator()
    reset_report_generator()


# ============================================================================
# 一、mcp_gate_server.py 测试
# ============================================================================

class TestMCPGateTools:
    """MCP工具定义测试"""

    def test_tools_list(self):
        """测试工具列表"""
        server = MCPGateServer()
        tools = server.get_tools()
        assert len(tools) == 8
        tool_names = {t["name"] for t in tools}
        assert "judge_unit" in tool_names
        assert "judge_all_gates" in tool_names
        assert "get_gate_status" in tool_names
        assert "get_element_cycle" in tool_names
        assert "get_twelve_gods_info" in tool_names
        assert "get_gate_health" in tool_names
        assert "get_verdict_history" in tool_names
        assert "get_blind_spots" in tool_names

    def test_tool_has_schema(self):
        """测试每个工具都有正确的input_schema"""
        server = MCPGateServer()
        for tool in server.get_tools():
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert "type" in tool["input_schema"]


class TestMCPGateJudgeUnit:
    """judge_unit 工具测试"""

    def test_judge_single_unit(self):
        """测试单个单元裁决"""
        server = MCPGateServer()
        result = server.execute_tool("judge_unit", {
            "unit_id": "test_001",
            "unit_name": "测试单元",
            "s_coord": 0.8, "t_coord": 0.5, "p_coord": 0.7,
            "c_coord": 0.6, "i_coord": 0.7, "e_coord": 0.3,
        })
        assert result["isError"] is False
        content = json.loads(result["content"][0]["text"])
        assert "verdicts" in content
        assert len(content["verdicts"]) == 12  # 全部十二神
        assert "all_passed" in content

    def test_judge_specific_gates(self):
        """测试指定门禁裁决"""
        server = MCPGateServer()
        result = server.execute_tool("judge_unit", {
            "unit_id": "test_002",
            "unit_name": "指定门禁测试",
            "gates": ["比肩", "食神", "正财"],
        })
        assert result["isError"] is False
        content = json.loads(result["content"][0]["text"])
        assert len(content["verdicts"]) == 3
        assert "比肩" in content["verdicts"]
        assert "食神" in content["verdicts"]
        assert "正财" in content["verdicts"]

    def test_judge_with_default_coords(self):
        """测试默认坐标裁决"""
        server = MCPGateServer()
        result = server.execute_tool("judge_unit", {
            "unit_id": "test_003",
            "unit_name": "默认坐标",
        })
        assert result["isError"] is False


class TestMCPGateJudgeAllGates:
    """judge_all_gates 工具测试"""

    def test_judge_all_with_majority(self):
        """测试全部门禁裁决+多数投票"""
        server = MCPGateServer()
        result = server.execute_tool("judge_all_gates", {
            "unit_id": "test_all_001",
            "unit_name": "全部门禁测试",
            "s_coord": 0.9, "t_coord": 0.5, "p_coord": 0.8,
            "c_coord": 0.7, "i_coord": 0.8, "e_coord": 0.2,
        })
        assert result["isError"] is False
        content = json.loads(result["content"][0]["text"])
        assert "majority" in content
        assert "tai_ji_veto" in content
        assert "overall" in content
        assert "by_element" in content
        assert content["majority"]["total"] == 12

    def test_judge_all_high_quality(self):
        """测试高质量单元全部通过"""
        server = MCPGateServer()
        result = server.execute_tool("judge_all_gates", {
            "unit_id": "test_high",
            "unit_name": "高质量单元",
            "s_coord": 0.95, "t_coord": 0.3, "p_coord": 0.9,
            "c_coord": 0.85, "i_coord": 0.9, "e_coord": 0.1,
        })
        content = json.loads(result["content"][0]["text"])
        assert content["overall"] in ("open", "pending")


class TestMCPGateQuery:
    """查询类工具测试"""

    def test_get_gate_status(self):
        """测试查询门禁状态"""
        server = MCPGateServer()
        result = server.execute_tool("get_gate_status", {"god_name": "比肩"})
        assert result["isError"] is False
        content = json.loads(result["content"][0]["text"])
        assert content["god_name"] == "比肩"
        assert content["element"] == "木"

    def test_get_gate_status_invalid(self):
        """测试查询无效门禁"""
        server = MCPGateServer()
        result = server.execute_tool("get_gate_status", {"god_name": "不存在的门禁"})
        content = json.loads(result["content"][0]["text"])
        assert "error" in content

    def test_get_element_cycle(self):
        """测试五行生克查询"""
        server = MCPGateServer()
        result = server.execute_tool("get_element_cycle", {"element": "木"})
        content = json.loads(result["content"][0]["text"])
        assert content["element"] == "木"
        assert content["generates"] == "火"
        assert content["overcomes"] == "土"
        assert "full_cycle" in content

    def test_get_all_elements(self):
        """测试全部五行查询"""
        server = MCPGateServer()
        for elem in ["木", "火", "土", "金", "水"]:
            result = server.execute_tool("get_element_cycle", {"element": elem})
            content = json.loads(result["content"][0]["text"])
            assert content["element"] == elem

    def test_get_twelve_gods_info(self):
        """测试十二神元信息"""
        server = MCPGateServer()
        result = server.execute_tool("get_twelve_gods_info", {})
        content = json.loads(result["content"][0]["text"])
        assert content["total_gods"] == 12
        assert len(content["gods"]) == 12
        assert "element_cycles" in content
        assert "gate_types" in content

    def test_get_gate_health_no_data(self):
        """测试空数据健康度"""
        server = MCPGateServer()
        result = server.execute_tool("get_gate_health", {})
        content = json.loads(result["content"][0]["text"])
        assert content["status"] == "no_data"

    def test_get_gate_health_with_data(self):
        """测试有数据时的健康度"""
        server = MCPGateServer()
        server.execute_tool("judge_all_gates", {
            "unit_id": "h1", "unit_name": "健康测试",
            "s_coord": 0.9, "p_coord": 0.8, "c_coord": 0.7, "i_coord": 0.8,
        })
        result = server.execute_tool("get_gate_health", {})
        content = json.loads(result["content"][0]["text"])
        assert content["status"] != "no_data"
        assert "overall_pass_rate" in content
        assert "by_gate" in content
        assert "by_element" in content

    def test_get_verdict_history(self):
        """测试裁决历史"""
        server = MCPGateServer()
        server.execute_tool("judge_unit", {
            "unit_id": "h1", "unit_name": "历史测试",
            "gates": ["比肩", "食神"],
        })
        result = server.execute_tool("get_verdict_history", {
            "god_name": "比肩", "limit": 10,
        })
        content = json.loads(result["content"][0]["text"])
        assert content["god_name"] == "比肩"
        assert content["total"] >= 1

    def test_get_blind_spots(self):
        """测试盲点检测"""
        server = MCPGateServer()
        result = server.execute_tool("get_blind_spots", {})
        content = json.loads(result["content"][0]["text"])
        assert "never_judged" in content
        assert "low_performers" in content
        assert "recommendation" in content

    def test_server_info(self):
        """测试服务信息"""
        server = MCPGateServer()
        info = server.get_server_info()
        assert info["name"] == "tengod-twelve-gods-gate"
        assert info["version"] == "2.33.0"
        assert info["tool_count"] == 8

    def test_unknown_tool(self):
        """测试未知工具"""
        server = MCPGateServer()
        result = server.execute_tool("nonexistent_tool", {})
        assert result["isError"] is True


# ============================================================================
# 二、mcp_cognitive_server.py 测试
# ============================================================================

class TestMCPCognitiveTools:
    """认知查询工具定义测试"""

    def test_tools_list(self):
        """测试工具列表"""
        server = MCPCognitiveServer()
        tools = server.get_tools()
        assert len(tools) == 7
        tool_names = {t["name"] for t in tools}
        assert "query_tbce" in tool_names
        assert "query_oracle" in tool_names
        assert "query_speculation" in tool_names
        assert "query_cognitive_layer" in tool_names
        assert "search_units" in tool_names
        assert "get_cognitive_topology" in tool_names
        assert "compute_geodesic" in tool_names


class TestMCPCognitiveQueryTBCE:
    """TBCE查询测试"""

    def test_query_tbce(self):
        """测试TBCE坐标查询"""
        server = MCPCognitiveServer()
        result = server.execute_tool("query_tbce", {
            "s_coord": 0.8, "t_coord": 1.5, "p_coord": 0.7,
            "c_coord": 0.6, "i_coord": 0.7, "e_coord": 0.3,
        })
        content = json.loads(result["content"][0]["text"])
        assert "coordinates" in content
        assert "interpretation" in content
        assert "geometry" in content
        assert content["coordinates"]["S"] == 0.8

    def test_query_tbce_interpretation(self):
        """测试TBCE维度解释"""
        server = MCPCognitiveServer()
        result = server.execute_tool("query_tbce", {
            "s_coord": 0.9, "t_coord": 0.1, "p_coord": 0.2,
            "c_coord": 0.2, "i_coord": 0.2, "e_coord": 0.8,
        })
        content = json.loads(result["content"][0]["text"])
        interp = content["interpretation"]
        assert "S" in interp
        assert "T" in interp
        assert "P" in interp
        assert "C" in interp
        assert "I" in interp
        assert "E" in interp


class TestMCPCognitiveOracle:
    """Oracle投影测试"""

    def test_query_oracle_all(self):
        """测试三时态全投影"""
        server = MCPCognitiveServer()
        result = server.execute_tool("query_oracle", {
            "s_coord": 0.8, "t_coord": 0.5, "p_coord": 0.7,
            "c_coord": 0.6, "i_coord": 0.7, "e_coord": 0.3,
            "tense": "all",
        })
        content = json.loads(result["content"][0]["text"])
        assert "past" in content["projections"]
        assert "present" in content["projections"]
        assert "future" in content["projections"]

    def test_query_oracle_past(self):
        """测试过去投影"""
        server = MCPCognitiveServer()
        result = server.execute_tool("query_oracle", {
            "s_coord": 0.9, "tense": "past",
        })
        content = json.loads(result["content"][0]["text"])
        assert "past" in content["projections"]
        assert "present" not in content["projections"]

    def test_query_oracle_present(self):
        """测试现在投影"""
        server = MCPCognitiveServer()
        result = server.execute_tool("query_oracle", {
            "i_coord": 0.8, "c_coord": 0.8, "tense": "present",
        })
        content = json.loads(result["content"][0]["text"])
        assert "present" in content["projections"]
        assert content["projections"]["present"]["stability"] > 0.7

    def test_query_oracle_future(self):
        """测试未来投影"""
        server = MCPCognitiveServer()
        result = server.execute_tool("query_oracle", {
            "p_coord": 0.9, "e_coord": 0.1, "tense": "future",
        })
        content = json.loads(result["content"][0]["text"])
        assert "future" in content["projections"]
        assert content["projections"]["future"]["predictability"] > 0.7


class TestMCPCognitiveSpeculation:
    """推测解码测试"""

    def test_query_speculation(self):
        """测试推测解码查询"""
        server = MCPCognitiveServer()
        result = server.execute_tool("query_speculation", {
            "hit_count": 70, "total_count": 100, "confidence": 0.85,
        })
        content = json.loads(result["content"][0]["text"])
        assert content["hit_rate"] == 0.7
        assert "speedup_estimate" in content
        assert content["status"] == "good"

    def test_query_speculation_poor(self):
        """测试低命中率"""
        server = MCPCognitiveServer()
        result = server.execute_tool("query_speculation", {
            "hit_count": 20, "total_count": 100, "confidence": 0.3,
        })
        content = json.loads(result["content"][0]["text"])
        assert content["status"] == "poor"
        assert content["hit_rate"] == 0.2

    def test_query_speculation_optimal(self):
        """测试最优推测"""
        server = MCPCognitiveServer()
        result = server.execute_tool("query_speculation", {
            "hit_count": 95, "total_count": 100, "confidence": 0.95,
        })
        content = json.loads(result["content"][0]["text"])
        assert content["status"] == "optimal"


class TestMCPCognitiveLayer:
    """认知层查询测试"""

    def test_query_all_layers(self):
        """测试查询所有认知层"""
        server = MCPCognitiveServer()
        result = server.execute_tool("query_cognitive_layer", {"layer": 0})
        content = json.loads(result["content"][0]["text"])
        assert content["total_layers"] == 8

    def test_query_specific_layer(self):
        """测试查询特定认知层"""
        server = MCPCognitiveServer()
        for layer in range(1, 9):
            result = server.execute_tool("query_cognitive_layer", {"layer": layer})
            content = json.loads(result["content"][0]["text"])
            assert content["layer"] == layer
            assert "name" in content
            assert "psi" in content

    def test_query_invalid_layer(self):
        """测试查询无效认知层"""
        server = MCPCognitiveServer()
        result = server.execute_tool("query_cognitive_layer", {"layer": 99})
        content = json.loads(result["content"][0]["text"])
        assert "error" in content


class TestMCPCognitiveSearch:
    """搜索测试"""

    def test_search_units(self):
        """测试搜索认知单元"""
        server = MCPCognitiveServer()
        result = server.execute_tool("search_units", {
            "s_min": 0.0, "s_max": 1.0, "limit": 5,
        })
        content = json.loads(result["content"][0]["text"])
        assert "filters" in content
        assert "units" in content
        assert content["total_found"] >= 0

    def test_search_with_layer_filter(self):
        """测试认知层过滤搜索"""
        server = MCPCognitiveServer()
        result = server.execute_tool("search_units", {
            "cognitive_layer": 3, "limit": 5,
        })
        content = json.loads(result["content"][0]["text"])
        assert content["filters"]["cognitive_layer"] == 3


class TestMCPCognitiveTopology:
    """认知拓扑测试"""

    def test_get_cognitive_topology(self):
        """测试认知拓扑"""
        server = MCPCognitiveServer()
        result = server.execute_tool("get_cognitive_topology", {})
        content = json.loads(result["content"][0]["text"])
        assert "layer_distribution" in content
        assert "psi_heatmap" in content
        assert "topology_description" in content


class TestMCPCognitiveGeodesic:
    """测地线距离测试"""

    def test_compute_geodesic(self):
        """测试测地线计算"""
        server = MCPCognitiveServer()
        result = server.execute_tool("compute_geodesic", {
            "s1": 0.5, "t1": 0.5, "p1": 0.5, "c1": 0.5, "i1": 0.5, "e1": 0.5,
            "s2": 0.8, "t2": 0.8, "p2": 0.8, "c2": 0.8, "i2": 0.8, "e2": 0.8,
        })
        content = json.loads(result["content"][0]["text"])
        assert "euclidean_distance" in content
        assert "geodesic_distance" in content
        assert "per_dimension" in content
        assert len(content["per_dimension"]) == 6
        assert "interpretation" in content

    def test_compute_geodesic_same_point(self):
        """测试同点测地线"""
        server = MCPCognitiveServer()
        result = server.execute_tool("compute_geodesic", {
            "s1": 0.5, "t1": 0.5, "p1": 0.5, "c1": 0.5, "i1": 0.5, "e1": 0.5,
            "s2": 0.5, "t2": 0.5, "p2": 0.5, "c2": 0.5, "i2": 0.5, "e2": 0.5,
        })
        content = json.loads(result["content"][0]["text"])
        assert content["euclidean_distance"] == 0.0

    def test_compute_geodesic_timelike(self):
        """测试类时间隔"""
        server = MCPCognitiveServer()
        # S差大，T差小 → 类时
        result = server.execute_tool("compute_geodesic", {
            "s1": 0.9, "t1": 0.5, "p1": 0.5, "c1": 0.5, "i1": 0.5, "e1": 0.5,
            "s2": 0.1, "t2": 0.5, "p2": 0.5, "c2": 0.5, "i2": 0.5, "e2": 0.5,
        })
        content = json.loads(result["content"][0]["text"])
        assert "is_timelike" in content
        assert "is_spacelike" in content


class TestMCPCognitiveServerInfo:
    """服务信息测试"""

    def test_server_info(self):
        """测试服务信息"""
        server = MCPCognitiveServer()
        info = server.get_server_info()
        assert info["name"] == "tengod-cognitive-query"
        assert info["version"] == "2.33.0"
        assert info["tool_count"] == 7

    def test_unknown_tool(self):
        """测试未知工具"""
        server = MCPCognitiveServer()
        result = server.execute_tool("nonexistent", {})
        assert result["isError"] is True


# ============================================================================
# 三、dashboard.py 测试
# ============================================================================

class TestDashboardData:
    """仪表盘数据测试"""

    def test_dashboard_data_creation(self):
        """测试仪表盘数据创建"""
        data = DashboardData()
        d = data.to_dict()
        assert "timestamp" in d
        assert "health_overview" in d
        assert "twelve_gods_status" in d
        assert "tbce_radar" in d
        assert "element_matrix" in d
        assert "gate_trends" in d
        assert "seven_theories" in d
        assert "chaos_sea" in d
        assert "alerts" in d


class TestDashboardGenerator:
    """仪表盘生成器测试"""

    def test_empty_generate(self):
        """测试空数据生成"""
        gen = DashboardGenerator()
        data = gen.generate()
        d = data.to_dict()
        assert d["health_overview"]["status"] == "no_data"

    def test_with_gate_results(self):
        """测试有门禁数据时生成"""
        gen = DashboardGenerator()
        for god in ["比肩", "劫财", "食神", "伤官", "正财", "偏财",
                     "正官", "七杀", "正印", "偏印", "太极", "元辰"]:
            gen.record_gate_result(
                god_name=god,
                element="木" if god in ("比肩", "劫财") else "火",
                passed=True if god != "劫财" else False,
                score=0.8 if god != "劫财" else 0.3,
                boost=0.05,
            )

        data = gen.generate()
        d = data.to_dict()

        # 健康总览
        assert d["health_overview"]["status"] != "no_data"
        assert d["health_overview"]["total_judgments"] == 12

        # 十二神状态
        assert len(d["twelve_gods_status"]) == 12
        for god_status in d["twelve_gods_status"]:
            assert "name" in god_status
            assert "element" in god_status
            assert "state" in god_status
            assert "pass_rate" in god_status

    def test_health_overview_healthy(self):
        """测试健康状态"""
        gen = DashboardGenerator()
        for i in range(50):
            gen.record_gate_result("比肩", "木", True, 0.9)
        data = gen.generate()
        assert data.health_overview["status"] in ("healthy", "degraded")

    def test_health_overview_critical(self):
        """测试严重状态"""
        gen = DashboardGenerator()
        for i in range(50):
            gen.record_gate_result("比肩", "木", False, 0.2)
        data = gen.generate()
        assert data.health_overview["status"] == "critical"

    def test_tbce_radar(self):
        """测试TBCE雷达图"""
        gen = DashboardGenerator()
        gen.record_unit_snapshot("u1", [0.5, 0.5, 0.5, 0.5, 0.5, 0.5], 1, "Embedding")
        gen.record_unit_snapshot("u2", [0.8, 0.3, 0.7, 0.6, 0.7, 0.2], 3, "Tortuosity")
        data = gen.generate()
        radar = data.tbce_radar
        assert "labels" in radar
        assert len(radar["labels"]) == 6
        assert "datasets" in radar
        assert len(radar["datasets"]) > 0

    def test_element_matrix(self):
        """测试五行矩阵"""
        gen = DashboardGenerator()
        gen.record_gate_result("比肩", "木", True, 0.9)
        gen.record_gate_result("食神", "火", True, 0.8)
        data = gen.generate()
        matrix = data.element_matrix
        assert "elements" in matrix
        assert len(matrix["elements"]) == 6
        assert "matrix" in matrix
        assert len(matrix["matrix"]) == 6  # 6x6矩阵
        for row in matrix["matrix"]:
            assert len(row) == 6

    def test_gate_trends(self):
        """测试门禁趋势"""
        gen = DashboardGenerator()
        for i in range(30):
            gen.record_gate_result("比肩", "木", i % 3 != 0, 0.5 + (i % 3) * 0.2)
        data = gen.generate()
        trends = data.gate_trends
        if trends["datasets"]:
            assert "labels" in trends
            assert "datasets" in trends

    def test_alerts_detection(self):
        """测试告警检测"""
        gen = DashboardGenerator()
        for i in range(20):
            gen.record_gate_result("比肩", "木", False, 0.1)
        data = gen.generate()
        assert len(data.alerts) > 0
        assert data.alerts[0]["level"] in ("critical", "warning")

    def test_no_alerts(self):
        """测试无告警"""
        gen = DashboardGenerator()
        for i in range(20):
            gen.record_gate_result("比肩", "木", True, 0.9)
        data = gen.generate()
        assert len(data.alerts) == 0


# ============================================================================
# 四、report_generator.py 测试
# ============================================================================

class TestGateReportSection:
    """报告章节测试"""

    def test_section_creation(self):
        """测试章节创建"""
        section = GateReportSection(
            title="测试章节",
            level=1,
            content="测试内容",
            data={"key": "value"},
        )
        d = section.to_dict()
        assert d["title"] == "测试章节"
        assert d["level"] == 1
        assert d["content"] == "测试内容"
        assert d["data"]["key"] == "value"

    def test_section_with_subsections(self):
        """测试带子章节的章节"""
        parent = GateReportSection(title="父章节", level=1, content="父内容")
        child = GateReportSection(title="子章节", level=2, content="子内容")
        parent.subsections.append(child)

        d = parent.to_dict()
        assert len(d["subsections"]) == 1
        assert d["subsections"][0]["title"] == "子章节"


class TestGateReport:
    """报告模型测试"""

    def test_report_creation(self):
        """测试报告创建"""
        report = GateReport(
            report_id="test_001",
            title="测试报告",
        )
        d = report.to_dict()
        assert d["report_id"] == "test_001"
        assert d["title"] == "测试报告"
        assert d["version"] == "2.34.0"


class TestReportGenerator:
    """报告生成器测试"""

    def test_generate_empty_report(self):
        """测试空报告生成"""
        gen = ReportGenerator()
        report = gen.generate_report(
            title="空报告",
            gate_verdicts=None,
            include_seven_theories=False,
            include_chaos_sea=False,
            include_element_analysis=False,
        )
        assert report.report_id.startswith("report_")
        assert report.title == "空报告"
        assert len(report.sections) == 0

    def test_generate_with_verdicts(self):
        """测试带裁决的报告"""
        gen = ReportGenerator()
        verdicts = {
            "比肩": {"state": GateState.OPEN, "score": 0.9, "element": "木",
                     "element_boost": 0.05, "reason": "架构健康"},
            "劫财": {"state": GateState.OPEN, "score": 0.85, "element": "木",
                     "element_boost": 0.03, "reason": "边界安全"},
            "食神": {"state": GateState.OPEN, "score": 0.8, "element": "火",
                     "element_boost": 0.05, "reason": "创新质量高"},
            "伤官": {"state": GateState.PENDING, "score": 0.55, "element": "火",
                     "element_boost": 0.0, "reason": "破界风险待评估"},
            "正财": {"state": GateState.OPEN, "score": 0.9, "element": "土",
                     "element_boost": 0.05, "reason": "知识可靠"},
            "偏财": {"state": GateState.OPEN, "score": 0.85, "element": "土",
                     "element_boost": 0.03, "reason": "演化健康"},
            "正官": {"state": GateState.OPEN, "score": 0.9, "element": "金",
                     "element_boost": 0.05, "reason": "调度合规"},
            "七杀": {"state": GateState.OPEN, "score": 0.8, "element": "金",
                     "element_boost": 0.02, "reason": "品质达标"},
            "正印": {"state": GateState.OPEN, "score": 0.85, "element": "水",
                     "element_boost": 0.04, "reason": "配置健康"},
            "偏印": {"state": GateState.OPEN, "score": 0.8, "element": "水",
                     "element_boost": 0.03, "reason": "桥接安全"},
            "太极": {"state": GateState.OPEN, "score": 0.9, "element": "太极",
                     "element_boost": 0.0, "reason": "阴阳平衡"},
            "元辰": {"state": GateState.OPEN, "score": 0.85, "element": "太极",
                     "element_boost": 0.0, "reason": "本源定位准确"},
        }

        report = gen.generate_report(
            title="综合评估报告",
            gate_verdicts=verdicts,
            include_seven_theories=False,
            include_chaos_sea=False,
        )

        assert report.report_id.startswith("report_")
        assert len(report.sections) >= 3  # 裁决+五行+建议
        assert report.summary != ""
        assert len(report.recommendations) > 0

    def test_generate_with_closed_gates(self):
        """测试包含关闭门禁的报告"""
        gen = ReportGenerator()
        verdicts = {
            "比肩": {"state": GateState.CLOSED, "score": 0.2, "element": "木",
                     "element_boost": 0.0, "reason": "架构严重损坏"},
            "劫财": {"state": GateState.CLOSED, "score": 0.15, "element": "木",
                     "element_boost": 0.0, "reason": "边界崩溃"},
            "食神": {"state": GateState.OPEN, "score": 0.9, "element": "火",
                     "element_boost": 0.0, "reason": "创新正常"},
        }

        report = gen.generate_report(
            title="异常报告",
            gate_verdicts=verdicts,
            include_seven_theories=False,
            include_chaos_sea=False,
        )

        # 应该有五行失衡建议
        assert any("木行" in r for r in report.recommendations)
        assert "系统存在严重问题" in report.summary

    def test_to_markdown(self):
        """测试Markdown输出"""
        gen = ReportGenerator()
        verdicts = {
            "比肩": {"state": GateState.OPEN, "score": 0.9, "element": "木",
                     "element_boost": 0.05, "reason": "健康"},
        }
        report = gen.generate_report(
            title="Markdown测试",
            gate_verdicts=verdicts,
            include_seven_theories=False,
            include_chaos_sea=False,
        )
        md = gen.to_markdown(report)
        assert "# Markdown测试" in md
        assert "报告ID" in md
        assert "执行摘要" in md
        assert "十二神门禁裁决" in md

    def test_to_json(self):
        """测试JSON输出"""
        gen = ReportGenerator()
        verdicts = {
            "比肩": {"state": GateState.OPEN, "score": 0.9, "element": "木",
                     "element_boost": 0.05, "reason": "健康"},
        }
        report = gen.generate_report(
            title="JSON测试",
            gate_verdicts=verdicts,
            include_seven_theories=False,
            include_chaos_sea=False,
        )
        json_str = gen.to_json(report)
        parsed = json.loads(json_str)
        assert parsed["title"] == "JSON测试"
        assert "sections" in parsed

    def test_get_report(self):
        """测试按ID获取报告"""
        gen = ReportGenerator()
        report = gen.generate_report(title="测试", gate_verdicts=None,
                                     include_seven_theories=False,
                                     include_chaos_sea=False,
                                     include_element_analysis=False)
        result = gen.get_report(report.report_id)
        assert result is not None
        assert result["title"] == "测试"

    def test_get_nonexistent_report(self):
        """测试不存在的报告"""
        gen = ReportGenerator()
        result = gen.get_report("nonexistent")
        assert result is None

    def test_get_recent_reports(self):
        """测试获取最近报告"""
        gen = ReportGenerator()
        for i in range(5):
            gen.generate_report(title=f"报告{i}", gate_verdicts=None,
                               include_seven_theories=False,
                               include_chaos_sea=False,
                               include_element_analysis=False)
        recent = gen.get_recent_reports(limit=3)
        assert len(recent) == 3

    def test_element_analysis(self):
        """测试五行分析"""
        gen = ReportGenerator()
        verdicts = {
            "比肩": {"state": GateState.OPEN, "score": 0.9, "element": "木",
                     "element_boost": 0.05, "reason": "健康"},
            "劫财": {"state": GateState.OPEN, "score": 0.85, "element": "木",
                     "element_boost": 0.03, "reason": "安全"},
            "食神": {"state": GateState.OPEN, "score": 0.8, "element": "火",
                     "element_boost": 0.05, "reason": "高质量"},
            "正财": {"state": GateState.OPEN, "score": 0.9, "element": "土",
                     "element_boost": 0.05, "reason": "可靠"},
            "正官": {"state": GateState.OPEN, "score": 0.9, "element": "金",
                     "element_boost": 0.05, "reason": "合规"},
            "正印": {"state": GateState.OPEN, "score": 0.85, "element": "水",
                     "element_boost": 0.04, "reason": "健康"},
        }
        report = gen.generate_report(
            title="元素分析",
            gate_verdicts=verdicts,
            include_seven_theories=False,
            include_chaos_sea=False,
        )
        # 应该有元素分析章节
        has_element = any("五行" in s.title for s in report.sections)
        assert has_element


# ============================================================================
# 五、集成测试
# ============================================================================

class TestPhase3Integration:
    """Phase 3 集成测试"""

    def test_mcp_to_dashboard_integration(self):
        """MCP门禁 → 仪表盘集成"""
        gate_server = MCPGateServer()
        dash_gen = DashboardGenerator()

        # 执行门禁裁决
        result = gate_server.execute_tool("judge_all_gates", {
            "unit_id": "int_001", "unit_name": "集成测试",
            "s_coord": 0.9, "p_coord": 0.8, "c_coord": 0.7, "i_coord": 0.8,
        })
        content = json.loads(result["content"][0]["text"])

        # 导入仪表盘
        for name, verdict in content["verdicts"].items():
            dash_gen.record_gate_result(
                god_name=name,
                element=verdict.get("element", "未知"),
                passed=verdict.get("state") == GateState.OPEN,
                score=verdict.get("score", 0.5),
                boost=verdict.get("element_boost", 0.0),
            )

        dashboard = dash_gen.generate()
        assert dashboard.health_overview["status"] != "no_data"
        assert dashboard.health_overview["total_judgments"] == 12

    def test_mcp_to_report_integration(self):
        """MCP门禁 → 报告集成"""
        gate_server = MCPGateServer()
        report_gen = ReportGenerator()

        result = gate_server.execute_tool("judge_all_gates", {
            "unit_id": "int_002", "unit_name": "报告集成",
            "s_coord": 0.85, "p_coord": 0.75, "c_coord": 0.65, "i_coord": 0.75,
        })
        content = json.loads(result["content"][0]["text"])

        report = report_gen.generate_report(
            title="集成测试报告",
            gate_verdicts=content["verdicts"],
            include_seven_theories=False,
            include_chaos_sea=False,
        )

        assert report.report_id.startswith("report_")
        assert len(report.sections) >= 3
        assert report.summary != ""

    def test_full_phase3_pipeline(self):
        """Phase 3 全管道集成"""
        gate_server = MCPGateServer()
        cog_server = MCPCognitiveServer()
        dash_gen = DashboardGenerator()
        report_gen = ReportGenerator()

        # 1. 认知查询
        tbce_result = cog_server.execute_tool("query_tbce", {
            "s_coord": 0.9, "t_coord": 0.3, "p_coord": 0.8,
            "c_coord": 0.7, "i_coord": 0.8, "e_coord": 0.2,
        })
        tbce = json.loads(tbce_result["content"][0]["text"])
        assert "coordinates" in tbce

        # 2. Oracle投影
        oracle_result = cog_server.execute_tool("query_oracle", {
            "s_coord": 0.9, "p_coord": 0.8, "e_coord": 0.2, "tense": "all",
        })
        oracle = json.loads(oracle_result["content"][0]["text"])
        assert "past" in oracle["projections"]

        # 3. 门禁裁决
        gate_result = gate_server.execute_tool("judge_all_gates", {
            "unit_id": "full_001", "unit_name": "全管道测试",
            "s_coord": 0.9, "p_coord": 0.8, "c_coord": 0.7, "i_coord": 0.8,
        })
        gate_data = json.loads(gate_result["content"][0]["text"])

        # 4. 仪表盘
        for name, verdict in gate_data["verdicts"].items():
            dash_gen.record_gate_result(
                god_name=name,
                element=verdict.get("element", "未知"),
                passed=verdict.get("state") == GateState.OPEN,
                score=verdict.get("score", 0.5),
                boost=verdict.get("element_boost", 0.0),
            )
        dashboard = dash_gen.generate()
        assert dashboard.health_overview["total_judgments"] == 12

        # 5. 报告
        report = report_gen.generate_report(
            title="全管道报告",
            gate_verdicts=gate_data["verdicts"],
            include_seven_theories=False,
            include_chaos_sea=False,
        )

        md = report_gen.to_markdown(report)
        assert "全管道报告" in md
        assert "执行摘要" in md

        json_str = report_gen.to_json(report)
        parsed = json.loads(json_str)
        assert parsed["title"] == "全管道报告"

        # 6. 门禁健康度
        health_result = gate_server.execute_tool("get_gate_health", {})
        health = json.loads(health_result["content"][0]["text"])
        assert health["status"] != "no_data"

        # 7. 测地线
        geo_result = cog_server.execute_tool("compute_geodesic", {
            "s1": 0.5, "t1": 0.5, "p1": 0.5, "c1": 0.5, "i1": 0.5, "e1": 0.5,
            "s2": 0.9, "t2": 0.3, "p2": 0.8, "c2": 0.7, "i2": 0.8, "e2": 0.2,
        })
        geo = json.loads(geo_result["content"][0]["text"])
        assert geo["euclidean_distance"] > 0