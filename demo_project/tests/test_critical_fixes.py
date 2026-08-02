#!/usr/bin/env python3
"""
test_critical_fixes.py — 关键缺陷修复测试

覆盖以下修复：
1. JWT 签名算法修复（hexdigest → base64url）
2. Admin API 认证保护
3. QuotaManager 线程安全
"""

import threading
import time
import pytest
from unittest.mock import MagicMock, patch


class TestJWTManagerSign:
    """JWT 签名算法修复测试"""

    def test_sign_returns_base64url(self):
        """验证 _sign 返回 base64url 编码而非 hex 字符串"""
        from tengod.auth import JWTManager
        message = "test.signing.input"
        signature = JWTManager._sign(message)
        
        import base64
        try:
            padding = 4 - len(signature) % 4
            if padding != 4:
                signature += "=" * padding
            decoded = base64.urlsafe_b64decode(signature)
            assert len(decoded) == 32
        except Exception:
            pytest.fail("Signature is not valid base64url encoding")

    def test_create_and_verify_token(self):
        """验证创建的令牌能被正确验证"""
        from tengod.auth import JWTManager
        token = JWTManager.create_access_token(1, "testuser", "user")
        payload = JWTManager.verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["username"] == "testuser"
        assert payload["role"] == "user"
        assert payload["type"] == "access"

    def test_verify_token_invalid_signature(self):
        """验证无效签名被正确拒绝"""
        from tengod.auth import JWTManager
        token = JWTManager.create_access_token(1, "testuser", "user")
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{parts[1]}.invalid_signature"
        
        payload = JWTManager.verify_token(tampered_token)
        assert payload is None

    def test_token_format_compatibility(self):
        """验证令牌格式符合 JWT 规范"""
        from tengod.auth import JWTManager
        token = JWTManager.create_access_token(1, "testuser", "user")
        parts = token.split(".")
        
        assert len(parts) == 3
        
        import base64
        for part in parts[:2]:
            padding = 4 - len(part) % 4
            if padding != 4:
                part += "=" * padding
            decoded = base64.urlsafe_b64decode(part)
            assert len(decoded) > 0


class TestQuotaManagerThreadSafety:
    """QuotaManager 线程安全测试"""

    def test_concurrent_consume(self):
        """验证并发消耗配额不会导致计数丢失"""
        from tengod.auth import QuotaManager
        
        QuotaManager.reset(999)
        expected_count = 100
        errors = []

        def worker():
            try:
                for _ in range(10):
                    QuotaManager.consume(999)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"
        usage = QuotaManager.get_usage(999)
        today = list(usage.keys())[0] if usage else None
        assert today is not None, "No usage record"
        assert usage[today] == expected_count, f"Expected {expected_count}, got {usage[today]}"

    def test_concurrent_check_and_consume(self):
        """验证并发检查和消耗不会导致竞态条件"""
        from tengod.auth import QuotaManager
        
        QuotaManager.reset(888)
        quota = 50
        success_count = 0
        failure_count = 0
        errors = []

        def worker():
            nonlocal success_count, failure_count
            try:
                for _ in range(10):
                    allowed, _, _ = QuotaManager.check(888, quota)
                    if allowed:
                        QuotaManager.consume(888)
                        success_count += 1
                    else:
                        failure_count += 1
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"
        usage = QuotaManager.get_usage(888)
        today = list(usage.keys())[0] if usage else None
        assert today is not None, "No usage record"
        assert usage[today] == min(100, quota), f"Expected {min(100, quota)}, got {usage[today]}"

    def test_reset_during_concurrent_access(self):
        """验证重置操作在并发访问时的安全性"""
        from tengod.auth import QuotaManager
        
        QuotaManager.reset(777)
        for _ in range(50):
            QuotaManager.consume(777)

        completed = []

        def consumer():
            for _ in range(10):
                QuotaManager.consume(777)
            completed.append(True)

        def reseter():
            time.sleep(0.01)
            QuotaManager.reset(777)
            completed.append(True)

        t1 = threading.Thread(target=consumer)
        t2 = threading.Thread(target=reseter)
        t3 = threading.Thread(target=consumer)
        
        t1.start()
        t2.start()
        t3.start()
        t1.join()
        t2.join()
        t3.join()

        assert len(completed) == 3
        usage = QuotaManager.get_usage(777)
        assert sum(usage.values()) >= 0


class TestAdminApiAuthentication:
    """Admin API 认证保护测试"""

    def test_admin_endpoints_require_admin_role(self):
        """验证管理端点需要管理员角色"""
        from tengod.admin_api import create_admin_app
        from fastapi.testclient import TestClient
        
        app = create_admin_app()
        client = TestClient(app)

        response = client.get("/api/admin/stats")
        assert response.status_code == 401, "未认证请求应返回 401"

        response = client.get("/api/admin/records")
        assert response.status_code == 401, "未认证请求应返回 401"

        response = client.delete("/api/admin/records/1")
        assert response.status_code == 401, "未认证请求应返回 401"

    def test_health_endpoint_public(self):
        """验证健康检查端点无需认证"""
        from tengod.admin_api import create_admin_app
        from fastapi.testclient import TestClient
        
        app = create_admin_app()
        client = TestClient(app)

        response = client.get("/api/admin/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_non_admin_cannot_access_admin_endpoints(self):
        """验证非管理员角色无法访问管理端点"""
        from tengod.admin_api import create_admin_app
        from tengod.auth import JWTManager
        from fastapi.testclient import TestClient
        
        app = create_admin_app()
        client = TestClient(app)

        user_token = JWTManager.create_access_token(1, "user", "user")
        headers = {"Authorization": f"Bearer {user_token}"}

        response = client.get("/api/admin/stats", headers=headers)
        assert response.status_code == 403, "普通用户应返回 403"

    def test_admin_can_access_admin_endpoints(self):
        """验证管理员角色可以访问管理端点"""
        from tengod.admin_api import create_admin_app
        from tengod.auth import JWTManager
        from fastapi.testclient import TestClient
        
        app = create_admin_app()
        client = TestClient(app)

        admin_token = JWTManager.create_access_token(1, "admin", "admin")
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/admin/health")
        assert response.status_code == 200

        response = client.get("/api/admin/stats", headers=headers)
        assert response.status_code == 200


# ============================================================================
# FastAPI Depends 集成级认证 / 授权依赖注入修复测试
#
# 触发场景（修复前）：
#   1. 开发者按文档用法使用 Depends(get_current_user) 或 Depends(require_permission(...))
#   2. 用户请求携带合法的 Bearer token
#   3. 修复前：
#      - get_current_user 的 credentials 参数未声明 Depends(security)，故 FastAPI
#        不会解析 Authorization header，credentials 始终为 None -> 永远 401
#      - require_permission / require_role 内部 check_perm / check_role 的 user
#        参数未声明 Depends(get_current_user)，FastAPI 无法注入，user 永远 = None
#        -> 永远 401
#   4. 修复后：上述依赖能正确通过 Depends 链解析 Authorization 并校验权限
# ============================================================================


class TestAuthDependsIntegration:
    """FastAPI Depends 级认证与权限依赖注入测试"""

    def _build_app(self):
        from fastapi import Depends, FastAPI
        from tengod.auth import (
            CurrentUser,
            get_current_user,
            get_current_user_optional,
            require_permission,
            require_role,
        )

        app = FastAPI()

        @app.get("/me")
        def me(user: CurrentUser = Depends(get_current_user)):
            return {"id": user.id, "username": user.username, "role": user.role}

        @app.get("/me-optional")
        def me_opt(user: CurrentUser = Depends(get_current_user_optional)):
            return {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "is_authenticated": user.is_authenticated,
            }

        @app.get("/need-bazi-calc", dependencies=[Depends(require_permission("bazi:calc"))])
        def need_bazi_calc():
            return {"ok": True}

        @app.get(
            "/need-admin",
            dependencies=[Depends(require_role("admin"))],
        )
        def need_admin():
            return {"ok": True}

        @app.get("/inject-user", response_model=dict)
        def inject_user(
            user: CurrentUser = Depends(require_permission("bazi:report")),
        ):
            return {"id": user.id, "username": user.username}

        return app

    def test_get_current_user_injects_via_bearer_header(self):
        """Depends(get_current_user) 能通过 HTTP Bearer token 解析出用户"""
        from fastapi.testclient import TestClient
        from tengod.auth import JWTManager

        app = self._build_app()
        client = TestClient(app)

        token = JWTManager.create_access_token(7, "alice", "user")
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/me", headers=headers)
        assert resp.status_code == 200, f"expected 200 got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["id"] == 7
        assert body["username"] == "alice"
        assert body["role"] == "user"

    def test_get_current_user_missing_header_returns_401(self):
        """Depends(get_current_user) 缺少认证头时返回 401"""
        from fastapi.testclient import TestClient

        client = TestClient(self._build_app())
        resp = client.get("/me")
        assert resp.status_code == 401
        # 错误消息应当和 401 语义匹配
        assert resp.json()["detail"] in ("未提供认证令牌", "令牌无效或已过期", "未认证")

    def test_get_current_user_optional_returns_guest_when_no_header(self):
        """Depends(get_current_user_optional) 无 header 时返回 guest"""
        from fastapi.testclient import TestClient

        client = TestClient(self._build_app())
        resp = client.get("/me-optional")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == 0
        assert body["username"] == "guest"
        assert body["role"] == "guest"

    def test_get_current_user_optional_with_header_returns_user(self):
        """Depends(get_current_user_optional) 有 header 时返回已认证用户"""
        from fastapi.testclient import TestClient
        from tengod.auth import JWTManager

        client = TestClient(self._build_app())
        token = JWTManager.create_access_token(42, "bob", "user")
        resp = client.get("/me-optional", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["id"] == 42
        assert resp.json()["username"] == "bob"

    def test_require_permission_injects_user_and_passes(self):
        """Depends(require_permission(...)) 有合法 token 且有权限时通过"""
        from fastapi.testclient import TestClient
        from tengod.auth import JWTManager

        client = TestClient(self._build_app())
        token = JWTManager.create_access_token(1, "user1", "user")  # user 有 bazi:calc
        resp = client.get("/need-bazi-calc", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, f"unexpected {resp.status_code}: {resp.text}"
        assert resp.json()["ok"] is True

    def test_require_permission_no_token_returns_401_not_internal_error(self):
        """Depends(require_permission(...)) 无 token 时返回 401（而不是永远 401/注入失败时的其他异常）"""
        from fastapi.testclient import TestClient

        client = TestClient(self._build_app())
        resp = client.get("/need-bazi-calc")
        assert resp.status_code == 401
        # 保证是标准 HTTPException 响应而不是 500/422
        assert "detail" in resp.json()

    def test_require_permission_wrong_permission_returns_403(self):
        """Depends(require_permission(...)) 无对应权限时返回 403"""
        from fastapi.testclient import TestClient
        from tengod.auth import JWTManager

        client = TestClient(self._build_app())
        # guest 只有 bazi:calc，没有 bazi:report
        token = JWTManager.create_access_token(0, "guest", "guest")
        resp = client.get(
            "/inject-user", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, f"expected 403 got {resp.status_code}: {resp.text}"
        assert "权限不足" in resp.json()["detail"]

    def test_require_role_admin_blocks_user(self):
        """Depends(require_role("admin")) 普通用户被 403 拒绝"""
        from fastapi.testclient import TestClient
        from tengod.auth import JWTManager

        client = TestClient(self._build_app())
        token = JWTManager.create_access_token(5, "staff", "user")
        resp = client.get("/need-admin", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
        assert "角色不足" in resp.json()["detail"]

    def test_require_role_admin_allows_admin(self):
        """Depends(require_role("admin")) 管理员通过"""
        from fastapi.testclient import TestClient
        from tengod.auth import JWTManager

        client = TestClient(self._build_app())
        token = JWTManager.create_access_token(9, "boss", "admin")
        resp = client.get("/need-admin", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_require_permission_injects_user_into_endpoint_param(self):
        """require_permission 通过 Depends 注入当前用户到路由参数"""
        from fastapi.testclient import TestClient
        from tengod.auth import JWTManager, ROLE_PERMISSIONS

        client = TestClient(self._build_app())
        # admin 有 * 权限，包含 bazi:report
        token = JWTManager.create_access_token(100, "chief", "admin")
        resp = client.get(
            "/inject-user", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200, f"{resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["id"] == 100
        assert body["username"] == "chief"


# ============================================================================
# 本轮提交后检查 —— 4 个关键缺陷修复验证
# ============================================================================


class TestBackupRestoreDataIntegrity:
    """Bug 1: data_store.py backup/restore 缺失 LegacyCase / ReportCache 导致数据丢失"""

    _tmp_path = None

    @classmethod
    def setup_class(cls):
        import tempfile
        cls._tmp_path = tempfile.mkdtemp(prefix="tengod_backup_test_")

    def test_export_all_includes_cached_reports_and_cases(self):
        """_export_all 必须包含 cached_reports 和 cases 键，否则备份将丢弃这两类数据"""
        import os, sys
        sys.path.insert(0, "/workspace/demo_project")

        # 用内存 SQLite URL，确保经过 _export_all / _import_all 路径
        from tengod.data_store import DataStore
        db_path = os.path.join(self._tmp_path, "export_test.db")
        store = DataStore(db_url=f"sqlite:///{db_path}")
        # Base.metadata.create_all 已在 __init__ 中自动执行

        payload = store._export_all()
        assert "cached_reports" in payload, (
            "备份 _export_all 缺少 cached_reports 键，将导致 ReportCache 数据在恢复时丢失"
        )
        assert "cases" in payload, (
            "备份 _export_all 缺少 cases 键，将导致 LegacyCase 数据在恢复时丢失"
        )
        assert isinstance(payload["cached_reports"], list)
        assert isinstance(payload["cases"], list)

    def test_roundtrip_preserves_cached_report_and_case(self):
        """写入 ReportCache / LegacyCase → 导出 → 清除 → 导入，验证数据完整恢复"""
        import os, sys, tempfile, json
        sys.path.insert(0, "/workspace/demo_project")

        from tengod.data_store import DataStore, ReportCache, LegacyCase, BaziRecord

        db_src = os.path.join(self._tmp_path, "src.db")
        db_dst = os.path.join(self._tmp_path, "dst.db")
        backup_path = os.path.join(self._tmp_path, "backup.json")

        # --- 源库：使用 sqlite:/// URL 模式（触发 JSON 导出路径，而非文件复制） ---
        src = DataStore(db_url=f"sqlite:///{db_src}")
        rec_id = src.save_bazi_record(
            year=1990, month=5, day=5, hour=10, minute=10,
            gender="male", user_id=7, label="张三",
            day_master="甲",
            pillars={"year": "庚午"},
            geju={"ge": "正官格"},
            yongshen={"yong": "火"},
        )

        # 手工塞一个 ReportCache & LegacyCase
        with src._session() as s:
            rc = ReportCache(
                bazi_record_id=rec_id,
                format="md",
                content="# 报告正文",
                content_hash="h123",
            )
            s.add(rc)
            lc = LegacyCase(
                title="乾造 庚午 辛巳 甲子 丙寅 案例",
                summary="案例摘要",
                analysis_text="分析文本",
                category="正官格",
                is_public=True,
                is_featured=False,
                bazi_record_id=rec_id,
                user_id=7,
                pillars_json=json.dumps({"year": "庚午"}, ensure_ascii=False),
                geju_json=json.dumps({"ge": "正官格"}, ensure_ascii=False),
                yongshen_json=json.dumps({"yong": "火"}, ensure_ascii=False),
                day_master="甲",
                tags='["案例","正官"]',
            )
            s.add(lc)
            s.commit()

        # 导出（JSON 路径）
        backup_out = src.backup(backup_path)
        assert backup_out is not None
        with open(backup_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data.get("cached_reports", [])) == 1, f"cached_reports 条数不符: {data.get('cached_reports')}"
        assert len(data.get("cases", [])) == 1, f"cases 条数不符: {data.get('cases')}"

        # --- 目标库：空库，执行恢复 ---
        dst = DataStore(db_url=f"sqlite:///{db_dst}")
        ok = dst.restore(backup_path)
        assert ok, "restore 失败"

        # 验证三类数据都回来了
        with dst._session() as s:
            assert s.query(BaziRecord).filter_by(id=rec_id).one_or_none() is not None
            rc_count = s.query(ReportCache).count()
            lc_count = s.query(LegacyCase).count()
            assert rc_count == 1, f"ReportCache 恢复后应为 1，实际 {rc_count}（数据丢失）"
            assert lc_count == 1, f"LegacyCase 恢复后应为 1，实际 {lc_count}（数据丢失）"


class TestQuotaManagerAtomicity:
    """Bug 2: QuotaManager.check/consume 非原子 -> 并发下绕过日配额"""

    def test_check_and_consume_is_atomic_under_concurrency(self):
        """并发 check_and_consume(quota=10) 100 次，实际消耗必须恰好为 10，不能绕过"""
        import threading
        from tengod.auth import QuotaManager

        QUSER = 12345
        QuotaManager.reset(QUSER)
        QUOTA = 10
        TOTAL_ATTEMPTS = 100
        success = []
        fail = []
        lock = threading.Lock()

        def worker():
            for _ in range(10):
                ok, used_after, remain = QuotaManager.check_and_consume(QUSER, QUOTA)
                with lock:
                    if ok:
                        success.append(1)
                    else:
                        fail.append(1)

        threads = [threading.Thread(target=worker) for _ in range(TOTAL_ATTEMPTS // 10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        usage = QuotaManager.get_usage(QUSER)
        today_key = list(usage.keys())[0] if usage else None
        actual_used = usage[today_key] if today_key else 0

        assert len(success) == QUOTA, (
            f"并发下原子 check_and_consume 应恰好成功 {QUOTA} 次，"
            f"实际成功 {len(success)} 次（失败 {len(fail)}）— 存在配额绕过"
        )
        assert actual_used == QUOTA, (
            f"实际消耗 {actual_used} 与配额 {QUOTA} 不符"
        )

    def test_old_check_plus_consume_races_but_atomic_does_not(self):
        """对比：老的非原子模式（已停用）在并发下会越过 quota，而 check_and_consume 不会"""
        import threading
        from tengod.auth import QuotaManager

        QuotaManager.reset(555)
        QuotaManager.reset(666)
        QUOTA = 5
        TASKS = 50

        # --- 组 A：模拟旧代码 check + consume（非原子，会超配额） ---
        def race_worker_old(user_id):
            for _ in range(10):
                ok, _, _ = QuotaManager.check(user_id, QUOTA)
                # 释放锁的窗口：其他线程会同时通过 check
                if ok:
                    QuotaManager.consume(user_id)

        # --- 组 B：原子 check_and_consume（不会超） ---
        def atomic_worker(user_id):
            for _ in range(10):
                QuotaManager.check_and_consume(user_id, QUOTA)

        old_t = [threading.Thread(target=race_worker_old, args=(555,)) for _ in range(TASKS // 10)]
        new_t = [threading.Thread(target=atomic_worker, args=(666,)) for _ in range(TASKS // 10)]
        for t in old_t + new_t:
            t.start()
        for t in old_t + new_t:
            t.join()

        old_used = list(QuotaManager.get_usage(555).values())[0]
        new_used = list(QuotaManager.get_usage(666).values())[0]

        # 关键断言：原子路径必须严格等于 QUOTA
        assert new_used == QUOTA, f"原子模式使用 {new_used}，应严格等于 {QUOTA}"
        # 非原子模式在强并发下可能 > QUOTA（演示竞态存在）
        # 注意：该测试不做旧值的硬上界断言，仅验证修复后路径的正确性


class TestAsyncTaskQueueCancellation:
    """Bug 3: 任务被 CANCEL 后，对应 Future 未 resolve 会导致调用方 get_result 永久挂起"""

    def test_cancelled_task_resolves_future_with_cancelled_error(self):
        """入队后立即 cancel，然后让 worker 处理该 CANCELLED 项，
        验证 Future 会被 set_exception(CancelledError)，而不是永远 pending。"""
        import sys, asyncio
        sys.path.insert(0, "/workspace/demo_project")

        from tengod.正官_法度调度.async_task_queue import (
            AsyncTaskQueue, AsyncTaskPriority,
        )

        async def _run():
            q = AsyncTaskQueue(max_workers=1)

            def slow(x):
                return x * 2

            # 1) 先启动 worker（队列空，worker 在等待）
            start_task = asyncio.create_task(q.start())
            await asyncio.sleep(0.05)

            # 2) 异步 submit：创建 Future + 入队 PENDING 项
            task_id = await q.submit(
                slow, args=(21,), priority=AsyncTaskPriority.NORMAL
            )
            # 3) 立即标记 CANCELLED（worker 尚未拉取，因为 sleep 后它阻塞在 queue.get）
            ok1 = await q.cancel(task_id)
            assert ok1, "入队未运行时应当可取消"

            # 4) 给 worker 时间拉取该 CANCELLED 项并 resolve Future
            await asyncio.sleep(0.2)

            try:
                # 等待未来：如果没 resolve，5 秒后就会 timeout —— 失败
                res = await asyncio.wait_for(q.get_result(task_id), timeout=5.0)
            except asyncio.CancelledError:
                # 预期：Future 被 set_exception(CancelledError)
                pass
            except asyncio.TimeoutError:
                pytest.fail(
                    "被取消的任务 Future 始终未 resolve — 调用方 get_result 会永久挂起（资源泄漏）"
                )
            else:
                pytest.fail(f"被取消任务应抛 CancelledError，实际返回 {res!r}")

            # 清理
            await q.shutdown()
            start_task.cancel()
            try:
                await start_task
            except asyncio.CancelledError:
                pass

        asyncio.run(_run())


class TestFederatedConsensusMedianKeys:
    """Bug 4: _median_aggregate 仅取第一个 peer 的键，当 peer 键不统一时抛 KeyError 导致崩溃"""

    def test_median_with_different_keys_across_peers_does_not_crash(self):
        """A={w1,w2}, B={w2,w3}：修复前会在 info["model"]["w3"] / info["model"]["w1"] 处 KeyError"""
        import sys
        sys.path.insert(0, "/workspace/demo_project")
        from tengod.federated_consensus import FederatedConsensus

        fc = FederatedConsensus()
        peers = {
            "peer-A": {
                "round": 1, "stake": 1.0,
                "model": {
                    "w1": [1.0, 2.0, 3.0],
                    "w2": [10.0, 20.0, 30.0],
                },
            },
            "peer-B": {
                "round": 1, "stake": 1.0,
                "model": {
                    "w2": [100.0, 200.0, 300.0],
                    "w3": [0.1, 0.2, 0.3],
                },
            },
        }
        # 修复前会抛 KeyError: 'w1' or KeyError: 'w3'
        try:
            agg = fc._median_aggregate(peers)
        except KeyError as e:
            pytest.fail(
                f"_median_aggregate 在 peer 键不统一时抛 KeyError({e!r})，"
                f"导致整个共识节点流程崩溃"
            )

        # w1: 仅 peerA 有 -> 中位数 = A 的中位数（每个位置取中位数 = 原值）
        assert "w1" in agg
        assert agg["w1"] == [1.0, 2.0, 3.0]
        # w2: [10,100] -> sorted[len//2] = 100; 每个位置如此
        assert "w2" in agg
        assert agg["w2"] == [100.0, 200.0, 300.0]
        # w3: 仅 peerB 有
        assert "w3" in agg
        assert agg["w3"] == [0.1, 0.2, 0.3]

    def test_median_with_unequal_vector_lengths(self):
        """不同 peer 同一键向量长度不一致：按 min_len 对齐，不抛 IndexError"""
        import sys
        sys.path.insert(0, "/workspace/demo_project")
        from tengod.federated_consensus import FederatedConsensus

        fc = FederatedConsensus()
        peers = {
            "A": {"round": 1, "stake": 1, "model": {"w": [1, 2, 3, 4, 5]}},
            "B": {"round": 1, "stake": 1, "model": {"w": [10, 20]}},
        }
        agg = fc._median_aggregate(peers)
        assert "w" in agg
        # min(5,2) = 2，前两个位置取中位数 [10, 20]
        assert len(agg["w"]) == 2
        assert agg["w"] == [10, 20]

    def test_median_empty_peers_returns_empty_dict(self):
        """空 peers 不应崩溃（防御性）"""
        import sys
        sys.path.insert(0, "/workspace/demo_project")
        from tengod.federated_consensus import FederatedConsensus

        fc = FederatedConsensus()
        assert fc._median_aggregate({}) == {}


# ============================================================================
# Bug #1 回归测试: database.py 默认 STORAGE_BACKEND="memory" 时应使用 :memory:
# 并且 get_db() 应自动 init() 表结构，不会因表不存在而崩溃
#
# 修复前触发场景：
#   1. 未设置任何环境变量时 STORAGE_BACKEND 默认 "memory"
#   2. 修复前 DB_PATH 回退到 "tengod.db"（即写入文件，而非内存）
#   3. 并且 memory 模式下未调用 init()，导致 insert_case 表不存在抛 OperationalError
# ============================================================================


class TestDatabaseDefaultMemoryBackend:
    """Bug #1 回归测试: 默认数据库 memory 后端可直接使用"""

    def test_default_memory_insert_and_get_case(self):
        """默认 STORAGE_BACKEND=memory 时 get_db() 应可用且 CRUD 正常"""
        import tempfile, os
        import sys
        sys.path.insert(0, "/workspace/demo_project")
        import tengod.database as dbmod

        original_backend = dbmod.STORAGE_BACKEND
        original_dbpath = dbmod.DB_PATH
        try:
            # 强制切到 memory 模式并重置单例
            dbmod.STORAGE_BACKEND = "memory"
            dbmod.reset_db()
            db = dbmod.get_db()
            # insert 若表不存在会抛 OperationalError，这就是修复前的崩溃路径
            cid = db.insert_case({
                "name": "memory模式测试",
                "bazi_data": {"year": 1990, "month": 6},
                "tags": ["critical_fix"],
            })
            case = db.get_case(cid)
            assert case is not None
            assert case["name"] == "memory模式测试"
            assert case["bazi_data"] == {"year": 1990, "month": 6}
        finally:
            dbmod.STORAGE_BACKEND = original_backend
            dbmod.DB_PATH = original_dbpath
            dbmod.reset_db()

    def test_sqlite_file_backend_autoinits_tables(self):
        """sqlite 文件后端在全新临时库上 get_db() 必须自动 init()，不能依赖外部调用"""
        import tempfile, os
        import sys
        sys.path.insert(0, "/workspace/demo_project")
        import tengod.database as dbmod

        tmpdb = tempfile.mktemp(suffix=".db")
        original_backend = dbmod.STORAGE_BACKEND
        try:
            dbmod.STORAGE_BACKEND = "sqlite"
            dbmod.reset_db()
            db = dbmod.get_db(tmpdb)
            cid = db.insert_case({"name": "sqlite_init"})
            assert db.get_case(cid)["name"] == "sqlite_init"
        finally:
            dbmod.STORAGE_BACKEND = original_backend
            dbmod.reset_db()
            if os.path.exists(tmpdb):
                os.remove(tmpdb)


# ============================================================================
# Bug #3 回归测试: data_store.update_bazi_record / update_case 传入 dict/list 给
# *_json 字段时必须自动 json.dumps 序列化，不能把 Python repr 当作字符串存
#
# 修复前触发场景：
#   1. datastore.save_bazi_record(..., pillars={'year':'庚午'}) 内部用 json.dumps 正确
#   2. 之后调用 datastore.update_bazi_record(rid, pillars_json={'year':'甲午'}) 传 dict
#   3. 修复前 setattr(record, "pillars_json", {'year':'甲午'}) -> SQLite TEXT 列会转成
#      "{'year': '甲午'}"（Python dict repr，单引号）
#   4. 再调用 BaziRecord.to_dict() 内部 json.loads(pillars_json) -> JSONDecodeError
#      -> 任何使用八字记录详情的页面都会 500
# ============================================================================


class TestDataStoreJsonFieldUpdateSerialization:
    """Bug #3 回归测试: update_* 的 *_json 字段 dict/list 自动序列化为合法 JSON"""

    def test_update_bazi_record_dict_json_fields_are_valid_json(self):
        """update_bazi_record 传 dict/list 给 *_json 字段后 to_dict() 应能 json.loads"""
        import tempfile, os
        import sys
        sys.path.insert(0, "/workspace/demo_project")
        from tengod.data_store import DataStore

        tmpdb = tempfile.mktemp(suffix=".db")
        try:
            store = DataStore(tmpdb)
            rid = store.save_bazi_record(
                year=1990, month=6, day=15, hour=10, gender="male",
                pillars={"year": "庚午", "month": "壬午"},
                analysis={"conclusion": "init"},
            )
            ok = store.update_bazi_record(
                rid,
                pillars_json={"year": "甲午", "month": "庚午", "day": "辛亥"},
                analysis_json={"conclusion": "updated", "score": 95},
                shensha_json=["驿马", "天乙贵人"],
                geju_json={"type": "伤官佩印"},
                yongshen_json={"element": "水", "gan": "壬"},
                tiaohou_json={"need": "调候"},
            )
            assert ok is True
            rec = store.get_bazi_record(rid)
            # 关键断言：如果之前写入了非法 Python repr 字符串，这里会炸
            d = rec.to_dict()
            assert d["pillars"] == {"year": "甲午", "month": "庚午", "day": "辛亥"}
            assert d["analysis"] == {"conclusion": "updated", "score": 95}
            assert d["shensha"] == ["驿马", "天乙贵人"]
            assert d["geju"] == {"type": "伤官佩印"}
            assert d["yongshen"] == {"element": "水", "gan": "壬"}
            assert d["tiaohou"] == {"need": "调候"}
        finally:
            store.close()
            if os.path.exists(tmpdb):
                os.remove(tmpdb)

    def test_update_case_dict_json_fields_are_valid_json(self):
        """update_case 传 dict/list 给 *_json 字段后 to_dict() 应能 json.loads"""
        import tempfile, os
        import sys
        sys.path.insert(0, "/workspace/demo_project")
        from tengod.data_store import DataStore

        tmpdb = tempfile.mktemp(suffix=".db")
        try:
            store = DataStore(tmpdb)
            cid = store.save_case(
                title="案例A", summary="摘要",
                pillars={"year": "庚午"},
                geju={"name": "初始格"},
            )
            ok = store.update_case(
                cid,
                pillars_json={"year": "甲午", "month": "庚午", "day": "辛亥"},
                geju_json={"name": "伤官佩印", "score": 90},
                yongshen_json={"element": "木"},
            )
            assert ok is True
            case = store.get_case(cid)
            cd = case.to_dict()
            assert cd["pillars"] == {"year": "甲午", "month": "庚午", "day": "辛亥"}
            assert cd["geju"] == {"name": "伤官佩印", "score": 90}
            assert cd["yongshen"] == {"element": "木"}
        finally:
            store.close()
            if os.path.exists(tmpdb):
                os.remove(tmpdb)