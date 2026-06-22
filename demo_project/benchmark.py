#!/usr/bin/env python3
"""
benchmark.py — TenGod API 基线性能基准测试

使用 FastAPI TestClient 直接测试，无需启动 HTTP 服务器。
建立各端点的基线响应时间指标，供 locust 压测参考。

用法:
    cd demo_project && python benchmark.py
"""
import os
import sys
import time
import statistics
import uuid

# 确保不启用 API Key 鉴权
os.environ.pop("TENGOD_API_KEY", None)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from tengod.api_server import app, _request_counts
from tengod.auth import QuotaManager

client = TestClient(app)

# 测试参数
WARMUP_RUNS = 5
BENCHMARK_RUNS = 50


def reset_state():
    """重置配额和限流状态"""
    QuotaManager._usage.clear()
    _request_counts.clear()


def bench(name, func, runs=BENCHMARK_RUNS):
    """运行基准测试，返回统计信息"""
    # 预热
    for _ in range(WARMUP_RUNS):
        reset_state()
        try:
            func()
        except Exception:
            pass

    # 正式测试
    times = []
    errors = 0
    for _ in range(runs):
        reset_state()
        start = time.perf_counter()
        try:
            r = func()
            if r.status_code >= 400:
                errors += 1
        except Exception:
            errors += 1
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)

    times.sort()
    avg = statistics.mean(times)
    p50 = statistics.median(times)
    p95 = times[int(len(times) * 0.95)] if len(times) > 1 else times[0]
    p99 = times[int(len(times) * 0.99)] if len(times) > 1 else times[0]
    qps = 1000 / avg if avg > 0 else 0

    status = "OK" if errors == 0 else f"ERR({errors})"
    print(f"  {name:45s} avg={avg:8.2f}ms  p50={p50:8.2f}ms  "
          f"p95={p95:8.2f}ms  p99={p99:8.2f}ms  qps={qps:7.1f}  [{status}]")
    return {"name": name, "avg": avg, "p50": p50, "p95": p95, "p99": p99, "qps": qps, "errors": errors}


def register_and_login():
    """注册并登录，返回 token"""
    username = f"bench_{uuid.uuid4().hex[:8]}"
    client.post("/api/auth/register", json={
        "username": username, "password": "Bench123456",
        "email": f"{username}@bench.test",
    })
    r = client.post("/api/auth/login", json={
        "username": username, "password": "Bench123456",
    })
    data = r.json()
    return data.get("access_token", "")


def main():
    print("=" * 80)
    print("  TenGod API 基线性能基准测试")
    print(f"  预热: {WARMUP_RUNS} 次 | 测试: {BENCHMARK_RUNS} 次 | Python {sys.version.split()[0]}")
    print("=" * 80)

    results = []

    # ── 系统端点 ──
    print("\n【系统端点】")
    results.append(bench("GET  /api/health", lambda: client.get("/api/health")))
    results.append(bench("GET  /api/health/full", lambda: client.get("/api/health/full")))
    results.append(bench("GET  /metrics", lambda: client.get("/metrics")))
    results.append(bench("GET  /api/stats", lambda: client.get("/api/stats")))

    # ── 八字计算（游客）──
    print("\n【八字排盘（游客）】")
    bazi_input = {"year": 1990, "month": 6, "day": 15, "hour": 10, "gender": "male"}
    results.append(bench("POST /api/bazi/calc", lambda: client.post("/api/bazi/calc", json=bazi_input)))

    # ── 知识图谱（游客）──
    print("\n【知识图谱（游客）】")
    results.append(bench("GET  /api/graph/stats", lambda: client.get("/api/graph/stats")))
    results.append(bench("GET  /api/graph/search?keyword=金",
                         lambda: client.get("/api/graph/search", params={"keyword": "金", "limit": 10})))
    results.append(bench("GET  /api/graph/node/elem_金",
                         lambda: client.get("/api/graph/node/elem_金")))

    # ── 认证用户端点 ──
    print("\n【认证用户端点】")
    token_holder = {"token": ""}

    def setup_token():
        if not token_holder["token"]:
            token_holder["token"] = register_and_login()
        return {"Authorization": f"Bearer {token_holder['token']}"}

    def bazi_full():
        h = setup_token()
        return client.post("/api/bazi/full", json=bazi_input, headers=h)

    def bazi_shensha():
        h = setup_token()
        return client.post("/api/bazi/shensha", json=bazi_input, headers=h)

    def bazi_geju():
        h = setup_token()
        return client.post("/api/bazi/geju", json=bazi_input, headers=h)

    def bazi_yongshen():
        h = setup_token()
        return client.post("/api/bazi/yongshen", json=bazi_input, headers=h)

    def knowledge_wuxing():
        h = setup_token()
        return client.get("/api/knowledge/wuxing/金", headers=h)

    def graph_path():
        h = setup_token()
        return client.get("/api/graph/path", params={"source": "elem_金", "target": "elem_水"}, headers=h)

    results.append(bench("POST /api/bazi/full", bazi_full))
    results.append(bench("POST /api/bazi/shensha", bazi_shensha))
    results.append(bench("POST /api/bazi/geju", bazi_geju))
    results.append(bench("POST /api/bazi/yongshen", bazi_yongshen))
    results.append(bench("GET  /api/knowledge/wuxing/金", knowledge_wuxing))
    results.append(bench("GET  /api/graph/path", graph_path))

    # ── 汇总 ──
    print("\n" + "=" * 80)
    print("  基线指标汇总")
    print("=" * 80)
    print(f"  {'端点':45s} {'平均(ms)':>10s} {'P95(ms)':>10s} {'QPS':>10s}")
    print("  " + "-" * 78)
    for r in results:
        print(f"  {r['name']:45s} {r['avg']:10.2f} {r['p95']:10.2f} {r['qps']:10.1f}")
    print("=" * 80)

    # 性能等级评估
    print("\n性能等级评估:")
    fast = [r for r in results if r["avg"] < 50]
    medium = [r for r in results if 50 <= r["avg"] < 200]
    slow = [r for r in results if r["avg"] >= 200]
    print(f"  快速 (<50ms):  {len(fast)}/{len(results)} 端点")
    print(f"  中等 (50-200ms): {len(medium)}/{len(results)} 端点")
    print(f"  较慢 (>200ms): {len(slow)}/{len(results)} 端点")
    if slow:
        print("  需优化端点:")
        for r in slow:
            print(f"    - {r['name']} ({r['avg']:.1f}ms)")


if __name__ == "__main__":
    main()
