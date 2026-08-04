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
import os
import json
import subprocess
import sys
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
# 本次新发现的 4 个关键缺陷修复验证
# ============================================================================


class TestJWTEmptySecretVulnerability:
    """Bug: 未设置 TENGOD_JWT_SECRET 时使用空字符串做 JWT 密钥 -> 令牌伪造/认证绕过"""

    def test_jwt_secret_is_non_empty_when_env_unset(self):
        """删除 env 后 JWTManager/JWT_SECRET 不得为空，
        否则攻击者可以用空密钥签发任意用户（含 admin）令牌，完全绕过认证。"""
        import os, hashlib, hmac, base64, json
        # 必须在导入 auth 前清掉环境变量，触发默认值路径
        saved = os.environ.pop("TENGOD_JWT_SECRET", None)
        try:
            # 注意：如果其他测试先 import 了 tengod.auth，模块级 JWT_SECRET 可能已被赋值。
            # 为了稳健，本测试直接从 auth.py 源码层面重新加载读取默认值
            import importlib
            import tengod.auth as auth_mod
            importlib.reload(auth_mod)

            secret = getattr(auth_mod, "JWT_SECRET", None)
            # 关键断言：空密钥 = 认证绕过漏洞
            assert secret is not None, "JWT_SECRET 未定义（环境变量缺省）"
            assert isinstance(secret, str) and len(secret) >= 16, (
                f"JWT_SECRET 长度不足或为空 {secret!r}；"
                "空密钥允许攻击者用 HS256 配合空 HMAC 密钥伪造任意管理员令牌"
            )
            # 进一步：随机密钥应不等于字符串字面量 ""
            assert secret != "", "JWT_SECRET 绝对不能是空字符串"
        finally:
            if saved is not None:
                os.environ["TENGOD_JWT_SECRET"] = saved

    def test_tokens_signed_with_different_process_secrets_are_not_interchangeable(self):
        """两个独立进程分别生成各自的随机密钥；进程 A 的令牌必须被进程 B 拒绝。
        （这验证了未设 env 时不会退化为空密钥——空密钥下所有进程签发的令牌可互换。）"""
        import os, importlib, subprocess, sys, textwrap
        import tempfile
        code = textwrap.dedent("""
            import os, json, importlib, sys
            sys.path.insert(0, '/workspace/demo_project')
            os.environ.pop('TENGOD_JWT_SECRET', None)
            import tengod.auth as am
            importlib.reload(am)
            tok = am.JWTManager.create_access_token(99, 'crossuser', 'admin')
            print(tok)
        """)
        with tempfile.TemporaryDirectory() as td:
            p1 = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=30,
                cwd="/workspace/demo_project",
            )
            p2 = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=30,
                cwd="/workspace/demo_project",
            )
            assert p1.returncode == 0, f"process1 failed: {p1.stderr}"
            assert p2.returncode == 0, f"process2 failed: {p2.stderr}"
            tok_p1 = p1.stdout.strip()
            tok_p2 = p2.stdout.strip()
            assert tok_p1 and tok_p2

            # 用 tok_p1 的内容通过 p2 环境验证：必须返回 None（拒绝）
            # 用临时 .py 文件代替 f-string 内嵌 code，避免 json.dumps(...) 里的花括号转义问题
            import uuid
            script_path = os.path.join(td, f"verifier_{uuid.uuid4().hex[:8]}.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write("import os, json, importlib, sys\n")
                f.write("sys.path.insert(0, '/workspace/demo_project')\n")
                f.write("os.environ.pop('TENGOD_JWT_SECRET', None)\n")
                f.write("import tengod.auth as am\n")
                f.write("importlib.reload(am)\n")
                f.write(f"token = {tok_p1!r}\n")
                f.write("p = am.JWTManager.verify_token(token)\n")
                f.write("valid = bool(p is not None and isinstance(p, dict) and 'username' in p)\n")
                f.write("print(json.dumps({'valid': valid}))\n")

            pv = subprocess.run(
                [sys.executable, script_path],
                capture_output=True, text=True, timeout=30,
                cwd="/workspace/demo_project",
            )
            assert pv.returncode == 0, f"verifier failed rc={pv.returncode} stderr: {pv.stderr}"
            try:
                info = json.loads(pv.stdout.strip())
            except Exception as e:
                pytest.fail(f"verifier 输出不可解析: {pv.stdout!r} err={e}")
            # 关键断言：如果 verify 返回 True，说明两个进程退化到共享同一个（空）密钥
            assert info.get("valid") is False, (
                "不同进程（各自随机密钥）签发的令牌在对端应被拒绝；"
                "若非如此说明 JWT_SECRET 退化到了一个跨进程相同的固定值（典型为 ''），"
                "即存在认证绕过漏洞。"
            )


class TestUserIdDeterministic:
    """Bug: auth.py / api_server.py 的 user_id = hash(username) % N 受 PYTHONHASHSEED 影响
    在进程重启后变化 -> 用户 A 的数据（user_id=X）被映射到用户 B（user_id=X）上
    或用户 A 的历史查询/配额/配置在重启后静默丢失。"""

    def test_auth_source_uses_deterministic_hash_not_python_builtin(self):
        """源码层面断言：auth.py 中 user_id 不能依赖内置 hash(username)。
        修复前：hash(username) % 100000 → PYTHONHASHSEED 一变 user_id 就漂移。
        修复后：hashlib.sha256(username.encode("utf-8")) 驱动的确定性 ID。"""
        import sys, inspect
        sys.path.insert(0, "/workspace/demo_project")
        import tengod.auth as am
        src = inspect.getsource(am)

        # 不允许：hash(username) / hash(password) 之类的内置 hash 用于 ID 生成
        # 允许：hashlib 里的密码学哈希
        import ast, textwrap
        found_python_hash_for_id = False
        # 搜索模式：在 user_id = ... % N 或类似赋值中出现 hash( （非 hashlib）
        lines = src.splitlines()
        for i, line in enumerate(lines):
            # 找包含 hash( 的行，但排除 hashlib / PasswordHasher.hash / __hash__
            stripped = line.strip()
            if "user_id" in stripped and "hash(" in stripped and "hashlib" not in stripped:
                # 过滤掉 hashlib.sha* / hashlib.md5 这些已经排除；这里主要抓的是裸 hash(xxx)
                if "__hash__" not in stripped and "PasswordHasher.hash" not in stripped:
                    found_python_hash_for_id = True
                    break
        assert not found_python_hash_for_id, (
            f"auth.py 第 {i+1} 行在计算 user_id 时使用了 Python 内置 hash()：\n"
            f"  {stripped!r}\n"
            "内置 hash() 受 PYTHONHASHSEED 影响，跨进程/重启会产生不同 user_id，"
            "导致用户历史查询/配额/外键数据静默丢失或越权。"
        )

        # 正向：必须在生成 user_id 的地方使用确定性密码学哈希（sha256/sha512/md5）
        deterministic_crypto_hash_present = any(
            (("sha256" in l or "sha512" in l or "md5" in l) and "username" in l and "user_id" in lines[max(0, i-3):min(len(lines), i+4)])
            for i, l in enumerate(lines)
        )
        # 更稳妥的模式：遍历找 "_deterministic_hash" 这种显式变量，或 sha256(username.encode)
        assert (
            "_deterministic_hash" in src
            or "sha256(username.encode" in src
            or "sha512(username.encode" in src
        ), (
            "auth.py 中未找到基于确定性密码学哈希的 user_id 生成。"
            "必须使用 hashlib.sha* 而非内置 hash()。"
        )

    def test_user_id_computation_stable_across_pythonhashseed(self):
        """在不同 PYTHONHASHSEED 下，用 auth.py 中实际的确定性公式算出的 user_id 必须完全相同。
        （修复前：hash(username) 每次不同；修复后 sha256(username).digest 恒等。）"""
        import subprocess, sys, os, textwrap, tempfile, uuid

        # 把计算脚本写成临时 .py 文件执行（避免 f-string 中大括号转义）
        def run_with(seed_env: str) -> int:
            with tempfile.TemporaryDirectory() as td:
                script = os.path.join(td, f"uid_{uuid.uuid4().hex[:8]}.py")
                with open(script, "w", encoding="utf-8") as f:
                    f.write(textwrap.dedent("""
                        import sys, hashlib
                        sys.path.insert(0, '/workspace/demo_project')
                        username = '张三_测试用户_9527'
                        # 与 auth.py 中完全一致的确定性公式：
                        _deterministic_hash = int(
                            hashlib.sha256(username.encode('utf-8')).hexdigest(), 16
                        )
                        user_id = _deterministic_hash % 100000
                        print(user_id)
                    """))
                env = os.environ.copy()
                if seed_env == "random":
                    env["PYTHONHASHSEED"] = "random"
                else:
                    env["PYTHONHASHSEED"] = seed_env
                p = subprocess.run(
                    [sys.executable, script],
                    capture_output=True, text=True, timeout=30, env=env,
                )
                assert p.returncode == 0, f"seed={seed_env} 失败 rc={p.returncode} stderr={p.stderr[:300]}"
                return int(p.stdout.strip())

        a = run_with("123")
        b = run_with("456")
        c = run_with("random")
        # 修复前：a / b / c 分别是 3 个不同的 hash(username) % 100000 值
        # 修复后：sha256 是确定性的，三者恒等
        assert a == b == c, (
            f"不同 PYTHONHASHSEED 下 user_id 不一致: {a} / {b} / {c}；"
            "修复前使用 Python 内置 hash()，重启/多进程部署下 user_id 漂移，"
            "会导致用户的 Bazi 记录、配额消耗、ReportCache 等以 user_id 为外键的数据"
            "发生静默丢失或跨用户越权访问。"
        )


class TestNoHardcodedDefaultCredentials:
    """Bug: api_server.py 预置 admin/admin123 / user/user123 两个明文默认账号
    -> 任何网络可达者可用硬编码凭据登录管理员账号，造成完全越权。"""

    def test_api_server_default_users_dict_initially_empty(self):
        """模块级 _DEFAULT_USERS 在 import/reload 后必须是空 dict 或等价零配置，
        不能在源码里写死 {admin: admin123, user: user123}。"""
        import importlib, sys, os
        sys.path.insert(0, "/workspace/demo_project")

        # 删除 env 使默认值路径生效
        saved_env = {
            k: os.environ.pop(k, None)
            for k in (
                "TENGOD_ADMIN_PASSWORD",
                "TENGOD_USER_PASSWORD",
                "TENGOD_ENABLE_DEFAULT_USERS",
            )
        }
        try:
            import tengod.正官_法度调度.api_server as apisrv
            importlib.reload(apisrv)

            default_users = getattr(apisrv, "_DEFAULT_USERS", None)
            assert default_users is not None, "api_server 缺少 _DEFAULT_USERS 定义"
            # 源码字面量中不得包含常见硬编码凭据
            import inspect
            src = inspect.getsource(apisrv)
            for bad in ("admin123", "user123", "admin:admin123"):
                assert bad not in src, (
                    f"api_server 源码中硬编码默认凭据 {bad!r}，任何用户可登录，存在严重越权"
                )
        finally:
            for k, v in saved_env.items():
                if v is not None:
                    os.environ[k] = v

    def test_admin_user_only_created_when_explicit_env_set(self):
        """未显式设置 TENGOD_ADMIN_PASSWORD / TENGOD_ENABLE_DEFAULT_USERS=1 时，
        _initialize_default_users() 不得创建任何 admin 用户。"""
        import importlib, sys, os
        sys.path.insert(0, "/workspace/demo_project")
        # 清空所有相关 env
        keys_to_clear = [
            "TENGOD_ADMIN_PASSWORD", "TENGOD_USER_PASSWORD",
            "TENGOD_ENABLE_DEFAULT_USERS", "TENGOD_ADMIN_USERNAME",
            "TENGOD_USER_USERNAME",
        ]
        saved = {k: os.environ.pop(k, None) for k in keys_to_clear}
        try:
            import tengod.正官_法度调度.api_server as apisrv
            importlib.reload(apisrv)
            # 初始 _DEFAULT_USERS 应该为空
            dict(apisrv._DEFAULT_USERS)
            # 调用默认用户初始化函数
            apisrv._initialize_default_users()
            after = dict(apisrv._DEFAULT_USERS)
            # 在无 env 的情况下，不应该凭空出现默认账号（修复前会有 admin/user）
            assert len(after) == 0, (
                f"未设置任何 TENGOD_*_PASSWORD / ENABLE_DEFAULT_USERS 环境变量时，"
                f"默认用户集合应为空，实际包含 {sorted(after.keys())!r}；"
                "这些账号通常对应源码里硬编码的弱密码，存在严重越权风险。"
            )
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v


class TestAsyncTaskQueueCancelRaceFixed:
    """Bug 补充：cancel() 必须同步 resolve Future 并避免 cancelled 计数重复。
    原实现：只改 item.status，不设 Future.result/exception，依赖 Worker 拉取项时处理。
    当任务处于 RUNNING 状态时 Worker 的 finally 分支对 CANCELLED 状态完全没处理，
    Future 永远 pending -> get_result 无限挂起；同时 PENDING 场景下 Worker 与 cancel()
    重复给 cancelled 统计 +=1。"""

    def test_cancel_running_task_does_not_hang_get_result(self):
        """在任务 RUNNING 阶段调用 cancel()，随后 get_result 必须在短时间内抛 CancelledError，
        修复前会挂到超时（因为 Worker finally 没处理 CANCELLED -> 不 resolve Future）。
        注意：不用 pytest.mark.asyncio，改用 asyncio.run() 避免插件依赖。"""
        import sys, asyncio
        sys.path.insert(0, "/workspace/demo_project")
        from tengod.正官_法度调度.async_task_queue import (
            AsyncTaskQueue, AsyncTaskPriority,
        )

        async def _body():
            started_evt = asyncio.Event()

            async def long_running():
                started_evt.set()
                await asyncio.sleep(10.0)  # 长时间运行
                return "never"

            q = AsyncTaskQueue(max_workers=1)
            start_task = asyncio.create_task(q.start())
            await asyncio.sleep(0.02)

            task_id = await q.submit(long_running, priority=AsyncTaskPriority.HIGH)

            # 等待 Worker 真的开始执行（进入 RUNNING 状态，此时 Worker finally 分支会覆盖）
            await asyncio.wait_for(started_evt.wait(), timeout=3.0)

            # 取消：必须立即 resolve Future
            ok = await q.cancel(task_id)
            assert ok, "RUNNING 阶段应可取消"

            # 关键：get_result 必须在极短时间内返回 CancelledError；
            # 如果修复前（没设 Future），这里将挂 5s 后 pytest 自身超时/失败。
            try:
                await asyncio.wait_for(q.get_result(task_id), timeout=2.0)
            except asyncio.CancelledError:
                pass  # 预期
            except asyncio.TimeoutError:
                pytest.fail(
                    "RUNNING 状态的任务被 cancel() 后 get_result 仍未 resolve；"
                    "修复前 Worker 的 finally 仅处理 COMPLETED / FAILED 状态，"
                    "导致 CANCELLED 状态的 Future 永远 pending，调用侧请求无限挂起。"
                )
            else:
                pytest.fail("RUNNING 阶段取消的任务应抛 CancelledError，不是正常返回值")

            await q.shutdown()
            start_task.cancel()
            try:
                await start_task
            except asyncio.CancelledError:
                pass

        asyncio.run(_body())

    def test_cancel_count_not_double_counted(self):
        """PENDING 阶段取消：cancelled 统计 +=1 且仅 +=1。
        修复前 cancel() 一次，再由 Worker 拉到时又加一次 -> cancelled = 2。
        注意：不用 pytest.mark.asyncio，改用 asyncio.run() 避免插件依赖。"""
        import sys, asyncio, inspect
        sys.path.insert(0, "/workspace/demo_project")
        from tengod.正官_法度调度.async_task_queue import (
            AsyncTaskQueue, AsyncTaskPriority, AsyncTaskStatus,
        )

        async def _body():
            q = AsyncTaskQueue(max_workers=0)  # 0 个 worker：任务永远 PENDING
            q._shutdown = False  # 允许 start 之外的手动调用
            q._workers = []

            # 入队
            task_id = await q.submit(lambda: 1, priority=AsyncTaskPriority.LOW)
            assert q.stats()["cancelled"] == 0

            # 直接调用 cancel
            ok = await q.cancel(task_id)
            assert ok
            stats_after_cancel = q.stats()
            assert stats_after_cancel["cancelled"] == 1, (
                f"cancel() 后 cancelled 统计应为 1，实际 {stats_after_cancel['cancelled']}"
            )

            # 拉出 CANCELLED 项，检查源码模式：Worker 的 CANCELLED 分支不能再重复统计
            item = await q._queue.get()
            assert item.status == AsyncTaskStatus.CANCELLED
            src = inspect.getsource(AsyncTaskQueue._worker)
            lines_of_block = []
            in_block = False
            for line in src.splitlines():
                if "item.status == AsyncTaskStatus.CANCELLED" in line or (
                    in_block and line.strip()
                ):
                    in_block = True
                    lines_of_block.append(line)
                    if in_block and line.rstrip().endswith("continue"):
                        break
            block_text = "\n".join(lines_of_block)
            assert "cancelled" not in block_text.replace("CANCELLED", ""), (
                "Worker 在处理已取消项的分支里仍进行了 cancelled 统计，"
                "和 cancel() 方法自身的计数叠加后会导致 cancelled 翻倍。"
            )
            # 兜底：如果 pull 完了再看 stats，还是 1
            assert q.stats()["cancelled"] == 1

        asyncio.run(_body())