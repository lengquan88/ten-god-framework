"""locustfile.py — 十神架构 HTTP API 压力测试 v2.1.0

用法:
    pip install locust
    # 启动目标服务器（另一个终端）：
    python -m tengod.正官_法度调度.api_server
    # 运行压测：
    locust -f locustfile.py --host=http://localhost:8000 --users=100 --spawn-rate=10
    # 或 headless 模式：
    locust -f locustfile.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=60s --headless
"""
import random
import json

from locust import HttpUser, task, between, events


class TengodUser(HttpUser):
    """模拟十神 API 用户行为"""
    wait_time = between(1, 3)

    def on_start(self):
        """用户初始化 — 登录获取 token"""
        try:
            resp = self.client.post("/api/auth/token", json={
                "username": "admin",
                "password": "admin123",
            })
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("data", {}).get("access_token", "")
                self.headers = {"Authorization": f"Bearer {self.token}"}
            else:
                self.token = ""
                self.headers = {}
        except Exception:
            self.token = ""
            self.headers = {}

    # ============ 系统端点 ============

    @task(5)
    def health_check(self):
        """健康检查（高频）"""
        self.client.get("/health")

    @task(3)
    def status_check(self):
        """状态查询"""
        self.client.get("/api/status")

    @task(2)
    def metrics_check(self):
        """指标查询"""
        self.client.get("/metrics")

    @task(1)
    def root_check(self):
        self.client.get("/")

    # ============ 知识库操作 ============

    @task(3)
    def list_knowledge(self):
        self.client.get("/api/knowledge/nodes", headers=self.headers)

    @task(2)
    def search_knowledge(self):
        queries = ["儒家", "道家", "法家", "AI", "天地", "阴阳", "五行", "八卦"]
        self.client.post("/api/knowledge/search", json={
            "query": random.choice(queries),
        }, headers=self.headers)

    @task(1)
    def add_knowledge(self):
        self.client.post("/api/knowledge/nodes", json={
            "name": f"压测节点_{random.randint(1, 10000)}",
            "node_type": "stress_test",
            "properties": {"value": random.random()},
        }, headers=self.headers)

    # ============ 生成操作 ============

    @task(2)
    def generate_content(self):
        prompts = ["你好", "写一首诗", "解释阴阳", "什么是AI", "论语简介"]
        self.client.post("/api/generate", json={
            "prompt": random.choice(prompts),
            "format": "text",
            "provider": "mock",
        }, headers=self.headers)

    @task(1)
    def generate_stream(self):
        self.client.post("/api/generate/stream", json={
            "prompt": "流式测试",
            "format": "text",
            "provider": "mock",
        }, headers=self.headers)

    # ============ Oracle ============

    @task(2)
    def consult_oracle(self):
        questions = ["今日运势", "项目方向", "技术选型", "团队协作", "研究方向"]
        self.client.post("/api/oracle", json={
            "question": random.choice(questions),
            "mode": "auto",
        }, headers=self.headers)

    # ============ 共识操作 ============

    @task(1)
    def consensus_state(self):
        self.client.get("/api/consensus/state", headers=self.headers)

    @task(1)
    def consensus_propose(self):
        self.client.post("/api/consensus/propose", json={
            "key": f"stress_{random.randint(1, 1000)}",
            "value": str(random.random()),
        }, headers=self.headers)

    # ============ 任务操作 ============

    @task(1)
    def task_submit(self):
        self.client.post("/api/tasks/submit", json={
            "func_args": {"x": random.randint(1, 100)},
        }, headers=self.headers)

    @task(1)
    def task_list(self):
        self.client.get("/api/tasks", headers=self.headers)

    # ============ 配置操作 ============

    @task(1)
    def config_get(self):
        self.client.get("/api/config", headers=self.headers)

    @task(1)
    def config_set(self):
        self.client.post("/api/config", json={
            "key": f"stress_test_{random.randint(1, 100)}",
            "value": str(random.random()),
        }, headers=self.headers)

    # ============ 组件列表 ============

    @task(1)
    def component_list(self):
        self.client.get("/api/components", headers=self.headers)


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("=" * 60)
    print("  十神架构 v2.1.0 压力测试启动")
    print(f"  目标: {environment.host}")
    print(f"  用户数: {environment.runner.target_user_count if environment.runner else 'N/A'}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("=" * 60)
    print("  压力测试完成")
    if hasattr(environment, 'stats'):
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
    print("=" * 60)