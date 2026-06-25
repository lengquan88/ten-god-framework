"""
Tests for tengod.mcp_server — MCPServer class and create_mcp_server factory.
"""
import pytest
from tengod.mcp_server import MCPServer, create_mcp_server


# ── Helper ──────────────────────────────────────────────────────────────────

def _get_tool_by_name(tools, name):
    """Return the tool dict with the given name, or None."""
    for t in tools:
        if t["name"] == name:
            return t
    return None


# ── Init ────────────────────────────────────────────────────────────────────

class TestMCPServerInit:
    def test_init_defaults(self):
        srv = MCPServer()
        assert srv.host == "0.0.0.0"
        assert srv.port == 8765
        assert srv.is_running() is False

    def test_init_custom_host_port(self):
        srv = MCPServer(host="127.0.0.1", port=9999)
        assert srv.host == "127.0.0.1"
        assert srv.port == 9999
        assert srv.is_running() is False


# ── get_tools() ─────────────────────────────────────────────────────────────

class TestGetTools:
    def test_returns_four_tools(self):
        srv = MCPServer()
        tools = srv.get_tools()
        assert len(tools) == 4

    def test_tool_names(self):
        srv = MCPServer()
        names = {t["name"] for t in srv.get_tools()}
        assert names == {"calculate_bazi", "get_palace_info", "get_star_info", "analyze_combination"}

    def test_calculate_bazi_schema(self):
        srv = MCPServer()
        tool = _get_tool_by_name(srv.get_tools(), "calculate_bazi")
        assert tool is not None
        assert tool["description"] == "Calculate Bazi (Eight Characters) fortune"
        schema = tool["input_schema"]
        assert schema["type"] == "object"
        assert "year" in schema["properties"]
        assert schema["properties"]["year"]["type"] == "integer"
        assert schema["properties"]["month"]["type"] == "integer"
        assert schema["properties"]["day"]["type"] == "integer"
        assert schema["properties"]["hour"]["type"] == "integer"
        assert schema["properties"]["minute"]["type"] == "integer"
        assert schema["properties"]["gender"]["type"] == "integer"
        assert schema["properties"]["solar_calendar"]["type"] == "boolean"
        assert set(schema["required"]) == {"year", "month", "day", "hour", "gender"}

    def test_get_palace_info_schema(self):
        srv = MCPServer()
        tool = _get_tool_by_name(srv.get_tools(), "get_palace_info")
        assert tool is not None
        schema = tool["input_schema"]
        assert schema["type"] == "object"
        assert schema["properties"]["palace_id"]["type"] == "integer"
        assert schema["required"] == ["palace_id"]

    def test_get_star_info_schema(self):
        srv = MCPServer()
        tool = _get_tool_by_name(srv.get_tools(), "get_star_info")
        assert tool is not None
        schema = tool["input_schema"]
        assert schema["type"] == "object"
        assert schema["properties"]["star_id"]["type"] == "integer"
        assert schema["required"] == ["star_id"]

    def test_analyze_combination_schema(self):
        srv = MCPServer()
        tool = _get_tool_by_name(srv.get_tools(), "analyze_combination")
        assert tool is not None
        schema = tool["input_schema"]
        assert schema["type"] == "object"
        assert schema["properties"]["star_ids"]["type"] == "array"
        assert schema["properties"]["star_ids"]["items"]["type"] == "integer"
        assert schema["properties"]["analysis_type"]["type"] == "string"
        assert schema["properties"]["analysis_type"]["enum"] == ["compatibility", "interaction", "strength"]
        assert schema["required"] == ["star_ids"]


# ── execute_tool() ──────────────────────────────────────────────────────────

class TestExecuteTool:
    @pytest.mark.asyncio
    async def test_calculate_bazi_valid(self):
        srv = MCPServer()
        result = await srv.execute_tool("calculate_bazi", {
            "year": 2000, "month": 1, "day": 15, "hour": 8, "gender": 1
        })
        assert result["success"] is True
        assert result["data"]["year_pillar"] == "甲子"
        assert result["data"]["month_pillar"] == "乙丑"
        assert result["data"]["day_pillar"] == "丙寅"
        assert result["data"]["hour_pillar"] == "丁卯"
        assert result["data"]["gender"] == 1

    @pytest.mark.asyncio
    async def test_get_palace_info(self):
        srv = MCPServer()
        result = await srv.execute_tool("get_palace_info", {"palace_id": 5})
        assert result["success"] is True
        assert result["data"]["palace_id"] == 5
        assert result["data"]["palace_name"] == "宫位5"

    @pytest.mark.asyncio
    async def test_get_star_info(self):
        srv = MCPServer()
        result = await srv.execute_tool("get_star_info", {"star_id": 42})
        assert result["success"] is True
        assert result["data"]["star_id"] == 42
        assert result["data"]["star_name"] == "星耀42"

    @pytest.mark.asyncio
    async def test_analyze_combination_with_analysis_type(self):
        srv = MCPServer()
        result = await srv.execute_tool("analyze_combination", {
            "star_ids": [1, 2, 3],
            "analysis_type": "interaction",
        })
        assert result["success"] is True
        assert result["data"]["star_ids"] == [1, 2, 3]
        assert result["data"]["analysis_type"] == "interaction"

    @pytest.mark.asyncio
    async def test_analyze_combination_defaults(self):
        srv = MCPServer()
        result = await srv.execute_tool("analyze_combination", {
            "star_ids": [7],
        })
        assert result["success"] is True
        assert result["data"]["star_ids"] == [7]
        assert result["data"]["analysis_type"] == "compatibility"

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        srv = MCPServer()
        result = await srv.execute_tool("nonexistent_tool", {"a": 1})
        assert "error" in result
        assert "Unknown tool" in result["error"]


# ── Lifecycle ───────────────────────────────────────────────────────────────

class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start(self):
        srv = MCPServer()
        assert srv.is_running() is False
        await srv.start()
        assert srv.is_running() is True

    @pytest.mark.asyncio
    async def test_stop(self):
        srv = MCPServer()
        await srv.start()
        assert srv.is_running() is True
        await srv.stop()
        assert srv.is_running() is False

    @pytest.mark.asyncio
    async def test_is_running_reflects_state(self):
        srv = MCPServer()
        assert srv.is_running() is False
        await srv.start()
        assert srv.is_running() is True
        await srv.stop()
        assert srv.is_running() is False
        await srv.start()
        assert srv.is_running() is True


# ── Factory ─────────────────────────────────────────────────────────────────

class TestCreateMCPServer:
    def test_defaults(self):
        srv = create_mcp_server()
        assert isinstance(srv, MCPServer)
        assert srv.host == "0.0.0.0"
        assert srv.port == 8765

    def test_custom_args(self):
        srv = create_mcp_server(host="10.0.0.1", port=5555)
        assert isinstance(srv, MCPServer)
        assert srv.host == "10.0.0.1"
        assert srv.port == 5555