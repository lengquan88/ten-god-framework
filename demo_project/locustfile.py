"""locustfile.py — TenGod 八字术数平台 API 压力测试 v3.0

用法:
    pip install locust
    # 启动目标服务器（另一个终端）：
    cd demo_project && python -m tengod.api_server
    # 运行压测（Web UI）：
    locust -f locustfile.py --host=http://localhost:8000
    # 或 headless 模式：
    locust -f locustfile.py --host=http://localhost:8000 \
        --users=100 --spawn-rate=10 --run-time=60s --headless

基线指标（2026-06-17, TestClient 本地测试, 50次平均）:
    GET  /api/health              3ms   P95=3.5ms   QPS=331  (系统端点)
    GET  /api/health/full        110ms   P95=111ms   QPS=9    (完整健康检查)
    GET  /metrics                104ms   P95=105ms   QPS=10   (Prometheus指标)
    GET  /api/stats                3ms   P95=3.6ms   QPS=320  (API统计)
    POST /api/bazi/calc            5ms   P95=5.3ms   QPS=206  (八字排盘)
    POST /api/bazi/full            6ms   P95=6.4ms   QPS=181  (八字全量分析)
    POST /api/bazi/shensha         4ms   P95=5.0ms   QPS=230  (神煞推算)
    POST /api/bazi/geju            4ms   P95=4.9ms   QPS=241  (格局分析)
    GET  /api/graph/search         4ms   P95=4.2ms   QPS=279  (图谱搜索)
    GET  /api/graph/stats          3ms   P95=3.5ms   QPS=311  (图谱统计)
    GET  /api/knowledge/wuxing/金   3ms   P95=3.9ms   QPS=299  (五行查询)
"""
import random
import uuid

from locust import HttpUser, task, between, events


class TengodGuestUser(HttpUser):
    """模拟游客用户（未登录，配额10次/天）"""
    wait_time = between(1, 3)
    weight = 3  # 游客占 60%

    # ============ 系统端点（公开，无配额限制）============

    @task(5)
    def health_check(self):
        """健康检查（高频）"""
        self.client.get("/api/health")

    @task(3)
    def health_full(self):
        """完整健康检查"""
        self.client.get("/api/health/full")

    @task(2)
    def metrics(self):
        """Prometheus 指标"""
        self.client.get("/metrics")

    @task(2)
    def api_stats(self):
        """API 统计"""
        self.client.get("/api/stats")

    # ============ 八字计算（需配额）============

    @task(3)
    def bazi_calc(self):
        """八字排盘（核心业务）"""
        self.client.post("/api/bazi/calc", json={
            "year": random.randint(1950, 2010),
            "month": random.randint(1, 12),
            "day": random.randint(1, 28),
            "hour": random.randint(0, 23),
            "gender": random.choice(["male", "female"]),
        })

    # ============ 知识图谱（需配额）============

    @task(2)
    def graph_search(self):
        """知识图谱搜索"""
        keywords = ["金", "木", "水", "火", "土", "甲", "乙", "丙", "丁", "戊"]
        self.client.get("/api/graph/search", params={
            "keyword": random.choice(keywords),
            "limit": 10,
        })

    @task(1)
    def graph_stats(self):
        """图谱统计"""
        self.client.get("/api/graph/stats")


class TengodAuthedUser(HttpUser):
    """模拟认证用户（已登录，配额100次/天）"""
    wait_time = between(0.5, 2)
    weight = 2  # 认证用户占 40%

    def on_start(self):
        """注册并登录获取 token"""
        username = f"locust_{uuid.uuid4().hex[:8]}"
        password = "LocustTest123"

        # 注册
        self.client.post("/api/auth/register", json={
            "username": username,
            "password": password,
            "email": f"{username}@locust.test",
        })

        # 登录
        resp = self.client.post("/api/auth/login", json={
            "username": username,
            "password": password,
        })
        if resp.status_code == 200:
            data = resp.json()
            self.token = data.get("access_token", "")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = ""
            self.headers = {}

    # ============ 八字全量分析（认证用户）============

    @task(5)
    def bazi_full(self):
        """八字全量分析（排盘+神煞+格局+喜用神+调候）"""
        self.client.post("/api/bazi/full", json={
            "year": random.randint(1950, 2010),
            "month": random.randint(1, 12),
            "day": random.randint(1, 28),
            "hour": random.randint(0, 23),
            "gender": random.choice(["male", "female"]),
        }, headers=self.headers)

    @task(3)
    def bazi_shensha(self):
        """神煞推算"""
        self.client.post("/api/bazi/shensha", json={
            "year": random.randint(1950, 2010),
            "month": random.randint(1, 12),
            "day": random.randint(1, 28),
            "hour": random.randint(0, 23),
            "gender": "male",
        }, headers=self.headers)

    @task(3)
    def bazi_geju(self):
        """格局分析"""
        self.client.post("/api/bazi/geju", json={
            "year": random.randint(1950, 2010),
            "month": random.randint(1, 12),
            "day": random.randint(1, 28),
            "hour": random.randint(0, 23),
            "gender": "male",
        }, headers=self.headers)

    # ============ 知识查询（认证用户）============

    @task(2)
    def knowledge_wuxing(self):
        """五行知识查询"""
        elements = ["金", "木", "水", "火", "土"]
        self.client.get(f"/api/knowledge/wuxing/{random.choice(elements)}",
                       headers=self.headers)

    @task(2)
    def graph_path(self):
        """图谱路径查询"""
        self.client.get("/api/graph/path", params={
            "source": "elem_金",
            "target": "elem_水",
        }, headers=self.headers)

    @task(1)
    def graph_neighbors(self):
        """图谱邻居查询"""
        self.client.get("/api/graph/neighbors/elem_金", headers=self.headers)

    # ============ 记录管理（认证用户）============

    @task(1)
    def save_record(self):
        """保存八字记录"""
        self.client.post("/api/records", json={
            "year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male",
        }, params={"label": f"locust_{random.randint(1, 10000)}"},
           headers=self.headers)

    @task(1)
    def list_records(self):
        """查询自己的记录"""
        self.client.get("/api/records", headers=self.headers)

    # ============ 高级术数（认证用户）============

    @task(1)
    def ziwei_calc(self):
        """紫微斗数"""
        self.client.post("/api/ziwei/calc", json={
            "year": random.randint(1950, 2010),
            "month": random.randint(1, 12),
            "day": random.randint(1, 28),
            "hour": random.randint(0, 23),
            "gender": "male",
        }, headers=self.headers)

    @task(1)
    def liuyao_shake(self):
        """六爻摇卦"""
        self.client.post("/api/liuyao/shake", json={
            "question": "测试问题",
        }, headers=self.headers)


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("=" * 60)
    print("  TenGod 八字术数平台 v3.0 压力测试启动")
    print(f"  目标: {environment.host}")
    print(f"  用户数: {environment.runner.target_user_count if environment.runner else 'N/A'}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("=" * 60)
    print("  压力测试完成")
    if hasattr(environment, "stats"):
        stats = environment.stats
        print(f"  总请求数: {stats.total.num_requests}")
        print(f"  失败数: {stats.total.num_failures}")
        if stats.total.num_requests > 0:
            fail_rate = stats.total.num_failures / stats.total.num_requests * 100
            print(f"  失败率: {fail_rate:.2f}%")
        print(f"  平均响应时间: {stats.total.avg_response_time:.2f}ms")
        print(f"  P50: {stats.total.get_response_time_percentile(0.5):.2f}ms")
        print(f"  P95: {stats.total.get_response_time_percentile(0.95):.2f}ms")
        print(f"  P99: {stats.total.get_response_time_percentile(0.99):.2f}ms")
        print(f"  QPS: {stats.total.total_rps:.2f}")
        print()
        print("  各端点详情:")
        for entry in stats.entries.values():
            print(f"    {entry.method:6s} {entry.name:40s} "
                  f"reqs={entry.num_requests:6d} "
                  f"avg={entry.avg_response_time:8.2f}ms "
                  f"p95={entry.get_response_time_percentile(0.95):8.2f}ms "
                  f"fail={entry.num_failures}")
    print("=" * 60)
