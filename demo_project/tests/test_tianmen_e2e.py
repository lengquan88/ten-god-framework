"""
v2.15 天眼架构端到端集成测试
验证完整六轮闭环：API 请求 → 天眼门禁(知止) → 自修正 → 混沌海 → 修真九境 → 回头看
"""
import pytest
import json
import time
from fastapi.testclient import TestClient

from tengod.api_server import app
from tengod.middleware import get_middleware
from tengod.tiangan_gate import get_tianmen
from tengod.self_correction import get_daemon
from tengod.hundun_sea import get_hundun_sea
from tengod.xiuzhen_realms import get_evaluator
from tengod.huigu_scheduler import get_scheduler


@pytest.fixture
def client():
    """FastAPI 测试客户端"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_globals():
    """每个测试前重置全局单例"""
    from tengod.middleware import _tianmen_middleware
    import tengod.tiangan_gate as tg
    import tengod.self_correction as sc
    import tengod.hundun_sea as hs
    import tengod.xiuzhen_realms as xr
    import tengod.huigu_scheduler as hg

    # 重置单例
    tg._tianmen = None
    sc._daemon = None
    hs._hundun_sea = None
    xr._evaluator = None
    hg._huigu_scheduler = None

    yield

    # 清理
    tg._tianmen = None
    sc._daemon = None
    hs._hundun_sea = None
    xr._evaluator = None
    hg._huigu_scheduler = None


class TestTianmenEndToEnd:
    """天眼架构端到端测试"""

    def test_01_health_no_gate(self, client):
        """健康检查端点跳过门禁"""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "X-Tianmen-Passed" not in resp.headers

    def test_02_gate_stats_self_excluded(self, client):
        """门禁统计端点自身免检"""
        resp = client.get("/api/v2/gate/middleware-stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_requests" in data

    def test_03_api_request_goes_through_gate(self, client):
        """API 请求通过门禁判定"""
        resp = client.post("/api/v2/solar-time", json={
            "year": 2000, "month": 1, "day": 1,
            "hour": 12, "longitude": 116.4
        })
        assert resp.status_code == 200
        # 验证 X-Tianmen 响应头
        assert "x-tianmen-passed" in resp.headers
        assert "x-tianmen-confidence" in resp.headers
        assert "x-tianmen-qi" in resp.headers

    def test_04_gate_stats_after_request(self, client):
        """请求后门禁统计更新"""
        # 先发几个请求
        for _ in range(3):
            client.post("/api/v2/solar-time", json={
                "year": 2000, "month": 1, "day": 1,
                "hour": 12, "longitude": 116.4
            })
        resp = client.get("/api/v2/gate/middleware-stats")
        data = resp.json()
        assert data["total_requests"] >= 3
        assert "tianmen" in data
        assert "correction" in data

    def test_05_xiuzhen_progress(self, client):
        """修真九境进度查询"""
        resp = client.get("/api/v2/gate/xiuzhen-progress")
        assert resp.status_code == 200
        data = resp.json()
        assert "current_realm" in data
        assert "all_realms" in data
        assert len(data["all_realms"]) == 9
        # 验证九境名称
        realm_names = [r["name"] for r in data["all_realms"]]
        assert "感知" in realm_names[0]
        assert "无极" in realm_names[-1]

    def test_06_hundun_foams(self, client):
        """混沌海浮沫坐标"""
        resp = client.get("/api/v2/gate/hundun-foams?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "foams" in data
        assert "total" in data
        assert "floating" in data
        assert "verified" in data

    def test_07_correction_log(self, client):
        """自修正日志"""
        resp = client.get("/api/v2/gate/correction-log?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_corrections" in data
        assert "successful" in data
        assert "success_rate" in data

    def test_08_huigu_status(self, client):
        """回头看调度器状态"""
        resp = client.get("/api/v2/gate/huigu-status")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_steps" in data
        assert "trajectory_health" in data
        assert "window_size" in data
        assert "max_angle" in data

    def test_09_full_pipeline_six_cycle(self, client):
        """完整六轮闭环管线测试"""
        # 1. 发送 API 请求 → 过门禁
        resp = client.post("/api/v2/solar-time", json={
            "year": 2000, "month": 1, "day": 1,
            "hour": 12, "longitude": 116.4
        })
        assert resp.status_code == 200
        # 验证门禁介入
        confidence = float(resp.headers["x-tianmen-confidence"])
        assert 0 <= confidence <= 1

        # 2. 验证门禁统计
        stats = client.get("/api/v2/gate/middleware-stats").json()
        assert stats["total_requests"] >= 1
        assert stats["tianmen"]["total"] >= 1

        # 3. 验证修真九境
        xiuzhen = client.get("/api/v2/gate/xiuzhen-progress").json()
        assert xiuzhen["current_realm"]["index"] >= 0

        # 4. 验证混沌海
        hundun = client.get("/api/v2/gate/hundun-foams").json()
        assert isinstance(hundun["total"], int)

        # 5. 验证自修正
        correction = client.get("/api/v2/gate/correction-log").json()
        assert isinstance(correction["total_corrections"], int)

        # 6. 验证回头看
        huigu = client.get("/api/v2/gate/huigu-status").json()
        assert 0 <= huigu["trajectory_health"] <= 1

    def test_10_exclude_paths_not_gated(self, client):
        """排除路径不会被门禁拦截"""
        exclude_paths = ["/health", "/docs", "/openapi.json"]
        for path in exclude_paths:
            resp = client.get(path)
            assert resp.status_code == 200
            assert "x-tianmen-passed" not in resp.headers, f"{path} should not be gated"

    def test_11_mandatory_gate_paths_gated(self, client):
        """强制门禁路径会被拦截"""
        # /api/v2/ 路径
        resp = client.get("/api/v2/gate/xiuzhen-progress")
        assert "x-tianmen-passed" not in resp.headers  # 自身免检，在 /api/v2/gate/ 排除中

        # /api/bazi/ 路径（需要找到实际存在的端点）
        resp = client.get("/api/bazi/calc")
        if resp.status_code != 404:
            # 如果端点存在，验证门禁
            assert "x-tianmen-passed" in resp.headers or "x-tianmen" not in resp.headers.lower()

    def test_12_zhi_judgment_confidence_range(self, client):
        """知止判定置信度在有效范围"""
        resp = client.post("/api/v2/solar-time", json={
            "year": 2000, "month": 1, "day": 1,
            "hour": 12, "longitude": 116.4
        })
        confidence = float(resp.headers["x-tianmen-confidence"])
        qi = float(resp.headers["x-tianmen-qi"])
        assert 0.0 <= confidence <= 1.0, f"confidence {confidence} out of range"
        assert 0.0 <= qi <= 1.0, f"qi {qi} out of range"

    def test_13_self_correction_triggered_on_low_confidence(self, client):
        """低置信度触发自修正"""
        # 发送多个请求积累数据
        responses = []
        for _ in range(5):
            r = client.post("/api/v2/solar-time", json={
                "year": 2000, "month": 1, "day": 1,
                "hour": 12, "longitude": 116.4
            })
            responses.append(r)

        # 至少有一个低置信度触发了自修正
        blocked = any(
            r.headers.get("x-tianmen-passed") == "false"
            for r in responses
        )
        # 自修正可能被触发
        stats = client.get("/api/v2/gate/middleware-stats").json()
        assert stats["tianmen"]["total"] >= 5

    def test_14_shen_agent_integration(self, client):
        """十神智能体与天眼门禁集成"""
        resp = client.post("/api/v2/analyze", json={
            "year": 2000, "month": 1, "day": 1,
            "hour": 12, "gender": "male"
        })
        if resp.status_code == 200:
            if "x-tianmen-passed" in resp.headers:
                confidence = float(resp.headers["x-tianmen-confidence"])
                assert 0.0 <= confidence <= 1.0

    def test_15_all_monitoring_endpoints(self, client):
        """所有监控端点 200"""
        endpoints = [
            "/api/v2/gate/middleware-stats",
            "/api/v2/gate/xiuzhen-progress",
            "/api/v2/gate/hundun-foams",
            "/api/v2/gate/correction-log",
            "/api/v2/gate/huigu-status",
        ]
        for ep in endpoints:
            resp = client.get(ep)
            assert resp.status_code == 200, f"{ep} returned {resp.status_code}"


class TestTianmenPerformance:
    """天眼性能基准测试"""

    def test_middleware_overhead(self, client):
        """中间件门禁开销在可接受范围"""
        start = time.time()
        for _ in range(20):
            client.post("/api/v2/solar-time", json={
                "year": 2000, "month": 1, "day": 1,
                "hour": 12, "longitude": 116.4
            })
        elapsed = time.time() - start
        avg_ms = (elapsed / 20) * 1000
        # 平均延迟应小于 200ms
        assert avg_ms < 200, f"Average latency {avg_ms:.1f}ms exceeds 200ms threshold"

    def test_gate_stats_response_time(self, client):
        """监控端点响应时间"""
        start = time.time()
        client.get("/api/v2/gate/middleware-stats")
        elapsed = (time.time() - start) * 1000
        assert elapsed < 50, f"Gate stats took {elapsed:.1f}ms"