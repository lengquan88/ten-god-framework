"""
v2.16.1 测试配置 —— 标记预存失败为预期失败 (xfail)

这些测试失败均为预存问题，非本次改动引入：
- API 集成测试依赖外部服务/数据库初始化
- 部分功能模块尚未完整实现
- 异步测试需要特定运行环境

标记为 xfail 后，主测试套件报告为 "全部通过或明确预期失败"。
"""
import sys
import pytest

# ── v2.17.0: 保护 auth 模块不被 test_v22_api.py 的 MagicMock 污染 ──────────
# test_v22_api.py 在模块级执行 sys.modules['tengod.auth'] = MagicMock()，
# 在 pytest 收集阶段即污染全局状态。通过 pytest_configure 在污染前保存真实模块，
# 然后在每个测试前恢复。
_REAL_AUTH_MODULE = None
_REAL_API_SERVER_MODULE = None
_REAL_METRICS_MODULE = None

def pytest_configure(config):
    """在测试收集前保存真实模块引用（此时 test_v22_api.py 尚未导入）"""
    global _REAL_AUTH_MODULE, _REAL_API_SERVER_MODULE, _REAL_METRICS_MODULE
    try:
        import tengod.auth as _mod
        _REAL_AUTH_MODULE = _mod
    except Exception:
        pass
    try:
        import tengod.api_server as _mod
        _REAL_API_SERVER_MODULE = _mod
    except Exception:
        pass
    try:
        import tengod.metrics_collector as _mod
        _REAL_METRICS_MODULE = _mod
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _restore_auth_module(request):
    """每个测试前恢复被 test_v22_api.py 污染的模块"""
    if _REAL_AUTH_MODULE is not None:
        sys.modules["tengod.auth"] = _REAL_AUTH_MODULE
    if _REAL_API_SERVER_MODULE is not None:
        sys.modules["tengod.api_server"] = _REAL_API_SERVER_MODULE
    if _REAL_METRICS_MODULE is not None:
        sys.modules["tengod.metrics_collector"] = _REAL_METRICS_MODULE
    yield

# 预存失败测试列表（精确匹配 ClassName::method_name）
# 格式：{文件名: {ClassName::method_name, ...}}
# v2.18.0 阶段 6：清理死条目 + 移除已通过测试
KNOWN_FAILING_TESTS: dict[str, set[str]] = {
    # v2.17.0: test_api_integration.py / test_pwa.py 已修复
    # v2.18.0 阶段 1: test_ai_interpreter.py 34/34 通过
    # v2.18.0 阶段 2: test_phase20.py 36/36 通过
    # v2.18.0 阶段 3: test_v212_data_api.py + test_case_library.py 通过
    # v2.18.0 阶段 6: test_phase27.py (4 XPASS) + test_phase29.py (1 XPASS) 已通过，移除

    # v2.18.0 阶段 5: test_core.py + test_phase24.py + test_phase27_28.py + test_v21_security.py 全部通过

    # v2.18.0 阶段 4: test_phase30.py + test_phase28.py 前端 HTML 测试已修复（补全组件函数与可视化内容）
}


def pytest_collection_modifyitems(config, items):
    """自动为预存失败测试添加 xfail 标记（strict=False，不阻断 CI）"""
    # v2.17.0: 将 test_v22_api.py 移到最后执行，避免其模块级 MagicMock 污染其他测试
    # test_v22_api.py 在模块级执行 sys.modules['tengod.auth'] = MagicMock()，
    # 会破坏所有后续测试的 PasswordHasher 等导入。
    v22_items = []
    other_items = []
    for item in items:
        test_file = item.location[0].split("/")[-1] if "/" in item.location[0] else item.location[0]
        test_file = test_file.split("\\")[-1]
        if test_file == "test_v22_api.py":
            v22_items.append(item)
        else:
            other_items.append(item)
    items[:] = other_items + v22_items

    for item in items:
        test_file = item.location[0].split("/")[-1] if "/" in item.location[0] else item.location[0]
        test_file = test_file.split("\\")[-1]

        if test_file not in KNOWN_FAILING_TESTS:
            continue

        failing_set = KNOWN_FAILING_TESTS[test_file]
        if "*" in failing_set:
            item.add_marker(
                pytest.mark.xfail(
                    reason=f"预存失败——{test_file}（环境依赖/模块未完成）",
                    strict=False,
                )
            )
            continue

        node_id = item.nodeid
        test_name = item.name  # 精确测试函数名
        for pattern in failing_set:
            if "::" in pattern:
                cls_name, method = pattern.split("::", 1)
                if cls_name in node_id and test_name == method:
                    item.add_marker(
                        pytest.mark.xfail(
                            reason=f"预存失败——{pattern}（环境依赖/模块未完成）",
                            strict=False,
                        )
                    )
                    break
            else:
                # 模块级函数（无类名）
                if pattern in node_id:
                    item.add_marker(
                        pytest.mark.xfail(
                            reason=f"预存失败——{pattern}（环境依赖/模块未完成）",
                            strict=False,
                        )
                    )
                    break