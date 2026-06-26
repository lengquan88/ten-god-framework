"""test_plugin_manager_supplement.py — 补充测试，覆盖 plugin_manager.py 未覆盖行。"""

import os
import sys
import tempfile
import pytest

from tengod.比肩_架构协同.plugin_manager import (
    PluginManager,
    Plugin,
    PluginSpec,
    PluginState,
    PluginHook,
    _create_sample_plugin,
)


# ── Plugin 基础测试 ──────────────────────────────────────────────────────

class TestPlugin:
    """测试 Plugin 类（覆盖 __init__ 和 call_hook）"""

    def test_plugin_init_defaults(self):
        """Plugin 初始化默认值"""
        spec = PluginSpec(name="test")
        p = Plugin(spec)
        assert p.state == PluginState.UNLOADED
        assert p.module is None
        assert p.instance is None
        assert p._hooks == {}
        assert p.loaded_at is None
        assert p.error is None

    def test_plugin_init_full_spec(self):
        """Plugin 初始化完整 spec"""
        spec = PluginSpec(
            name="full",
            version="2.0.0",
            description="desc",
            author="author",
            dependencies=["dep1"],
            entry_point="mod:cls",
            file_path="/tmp/x.py",
        )
        p = Plugin(spec)
        assert p.spec.name == "full"
        assert p.spec.version == "2.0.0"

    def test_call_hook_no_handlers(self):
        """call_hook 无处理器时返回 None"""
        p = Plugin(PluginSpec(name="t"))
        assert p.call_hook("nonexistent") is None

    def test_call_hook_with_handler(self):
        """call_hook 有处理器时正常调用"""
        p = Plugin(PluginSpec(name="t"))
        p._hooks["on_load"] = [lambda: 42]
        assert p.call_hook("on_load") == 42

    def test_call_hook_multiple_handlers_first_returns(self):
        """call_hook 多个处理器，第一个返回非 None 就返回"""
        p = Plugin(PluginSpec(name="t"))
        p._hooks["test"] = [lambda: "first", lambda: "second"]
        assert p.call_hook("test") == "first"

    def test_call_hook_handler_returns_none(self):
        """call_hook 处理器返回 None 时继续下一个"""
        p = Plugin(PluginSpec(name="t"))
        p._hooks["test"] = [lambda: None, lambda: 99]
        assert p.call_hook("test") == 99

    def test_call_hook_handler_exception(self):
        """call_hook 处理器抛异常时打印错误并继续"""
        p = Plugin(PluginSpec(name="t"))
        p._hooks["test"] = [lambda: 1 / 0]
        # 不应抛出异常，返回 None
        assert p.call_hook("test") is None

    def test_call_hook_with_args_kwargs(self):
        """call_hook 传递参数"""
        p = Plugin(PluginSpec(name="t"))
        p._hooks["test"] = [lambda a, b=0: a + b]
        assert p.call_hook("test", 10, b=20) == 30


# ── PluginManager 基础测试 ───────────────────────────────────────────────

class TestPluginManager:
    """测试 PluginManager 核心功能"""

    def test_init_with_plugin_dir(self):
        """PluginManager 初始化时传入 plugin_dir 会添加搜索路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 确保目录存在
            pm = PluginManager(plugin_dir=tmpdir)
            assert tmpdir in pm._search_paths

    def test_init_without_plugin_dir(self):
        """PluginManager 无参初始化"""
        pm = PluginManager()
        assert pm._plugins == {}
        assert pm._search_paths == []
        assert pm._hooks == {}

    def test_add_search_path_valid(self):
        """add_search_path 添加有效目录"""
        pm = PluginManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            pm.add_search_path(tmpdir)
            assert tmpdir in pm._search_paths

    def test_add_search_path_invalid(self):
        """add_search_path 添加无效路径不生效"""
        pm = PluginManager()
        pm.add_search_path("/nonexistent_dir_xyz")
        assert "/nonexistent_dir_xyz" not in pm._search_paths

    def test_add_search_path_duplicate(self):
        """add_search_path 重复添加不重复"""
        pm = PluginManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            pm.add_search_path(tmpdir)
            pm.add_search_path(tmpdir)
            assert pm._search_paths.count(tmpdir) == 1

    def test_get_plugin_existing(self):
        """get_plugin 获取已注册插件"""
        pm = PluginManager()
        spec = PluginSpec(name="p1")
        pm.register_plugin(spec)
        p = pm.get_plugin("p1")
        assert p is not None
        assert p.spec.name == "p1"

    def test_get_plugin_nonexistent(self):
        """get_plugin 获取不存在的插件返回 None"""
        pm = PluginManager()
        assert pm.get_plugin("no_such") is None


# ── 注册与发现 ────────────────────────────────────────────────────────────

class TestRegistration:
    """测试插件注册与发现"""

    def test_register_plugin(self):
        """注册插件"""
        pm = PluginManager()
        spec = PluginSpec(name="reg_test")
        plugin = pm.register_plugin(spec)
        assert plugin.spec.name == "reg_test"
        assert plugin.state == PluginState.UNLOADED

    def test_register_duplicate_raises(self):
        """重复注册抛 ValueError"""
        pm = PluginManager()
        spec = PluginSpec(name="dup")
        pm.register_plugin(spec)
        with pytest.raises(ValueError, match="已注册"):
            pm.register_plugin(spec)

    def test_discover_empty(self):
        """discover 在空目录返回空列表"""
        pm = PluginManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            pm.add_search_path(tmpdir)
            assert pm.discover() == []

    def test_discover_with_plugin_files(self):
        """discover 发现插件文件"""
        pm = PluginManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建插件文件
            plugin_file = os.path.join(tmpdir, "my_plugin.py")
            with open(plugin_file, "w") as f:
                f.write(
                    'PLUGIN_SPEC = {"name": "discovered", "version": "1.0", '
                    '"description": "test", "author": "me", '
                    '"dependencies": [], "entry_point": ""}\n'
                )
            # 创建非插件文件（以 _ 开头，应被跳过）
            with open(os.path.join(tmpdir, "_private.py"), "w") as f:
                f.write("x = 1\n")
            # 创建非 py 文件
            with open(os.path.join(tmpdir, "notes.txt"), "w") as f:
                f.write("hello\n")

            pm.add_search_path(tmpdir)
            specs = pm.discover()
            assert len(specs) == 1
            assert specs[0].name == "discovered"

    def test_discover_invalid_dir_skipped(self):
        """discover 跳过无效目录"""
        pm = PluginManager()
        pm._search_paths.append("/nonexistent_dir_xyz")
        assert pm.discover() == []

    def test_discover_parse_error_skipped(self):
        """discover 解析错误时静默跳过"""
        pm = PluginManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建语法错误的文件
            with open(os.path.join(tmpdir, "bad.py"), "w") as f:
                f.write("this is not valid python @@@\n")
            pm.add_search_path(tmpdir)
            specs = pm.discover()
            assert specs == []

    def test_parse_plugin_file_no_spec(self):
        """_parse_plugin_file 文件无 PLUGIN_SPEC 返回 None"""
        pm = PluginManager()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x = 42\n")
            fpath = f.name
        try:
            assert pm._parse_plugin_file(fpath) is None
        finally:
            os.unlink(fpath)

    def test_parse_plugin_file_with_spec(self):
        """_parse_plugin_file 文件有 PLUGIN_SPEC 正确解析"""
        pm = PluginManager()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                'PLUGIN_SPEC = {"name": "parsed", "version": "2.0", '
                '"description": "d", "author": "a", '
                '"dependencies": ["x"], "entry_point": "ep"}\n'
            )
            fpath = f.name
        try:
            spec = pm._parse_plugin_file(fpath)
            assert spec is not None
            assert spec.name == "parsed"
            assert spec.version == "2.0"
            assert spec.file_path == fpath
        finally:
            os.unlink(fpath)

    def test_parse_plugin_file_partial_spec(self):
        """_parse_plugin_file 部分字段缺失使用默认值"""
        pm = PluginManager()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('PLUGIN_SPEC = {"name": "minimal"}\n')
            fpath = f.name
        try:
            spec = pm._parse_plugin_file(fpath)
            assert spec is not None
            assert spec.name == "minimal"
            assert spec.version == "1.0.0"
            assert spec.description == ""
            assert spec.author == ""
            assert spec.dependencies == []
            assert spec.entry_point == ""
        finally:
            os.unlink(fpath)


# ── 加载 / 激活 / 停用 / 卸载 ─────────────────────────────────────────────

class TestLoadActivate:
    """测试插件的加载、激活、停用和卸载"""

    @pytest.fixture
    def plugin_dir(self):
        """创建临时插件目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def _make_plugin_file(self, tmpdir, name, content):
        """创建插件文件"""
        fpath = os.path.join(tmpdir, f"{name}.py")
        with open(fpath, "w") as f:
            f.write(content)
        return fpath

    def test_load_plugin_basic(self, plugin_dir):
        """加载插件基本流程"""
        pm = PluginManager()
        self._make_plugin_file(
            plugin_dir,
            "basic",
            'PLUGIN_SPEC = {"name": "basic"}\n'
            'def hook_on_load():\n    return "loaded"\n',
        )
        pm.add_search_path(plugin_dir)
        spec = pm._parse_plugin_file(os.path.join(plugin_dir, "basic.py"))
        pm.register_plugin(spec)
        plugin = pm.load_plugin("basic")
        assert plugin.state == PluginState.LOADED
        assert plugin.loaded_at is not None
        assert plugin.module is not None

    def test_load_plugin_not_registered(self):
        """加载未注册插件抛 KeyError"""
        pm = PluginManager()
        with pytest.raises(KeyError, match="未注册"):
            pm.load_plugin("ghost")

    def test_load_plugin_already_loaded(self):
        """重复加载已加载插件直接返回"""
        pm = PluginManager()
        pm.register_plugin(PluginSpec(name="once"))
        p1 = pm.load_plugin("once")
        p2 = pm.load_plugin("once")
        assert p1 is p2

    def test_load_plugin_with_entry_point(self, plugin_dir):
        """加载有 entry_point 的插件，实例化入口类"""
        pm = PluginManager()
        self._make_plugin_file(
            plugin_dir,
            "ep",
            'PLUGIN_SPEC = {"name": "ep", "entry_point": "MyClass:ignored"}\n'
            "class MyClass:\n"
            "    def __init__(self):\n"
            "        self.x = 100\n",
        )
        pm.add_search_path(plugin_dir)
        spec = pm._parse_plugin_file(os.path.join(plugin_dir, "ep.py"))
        pm.register_plugin(spec)
        plugin = pm.load_plugin("ep")
        assert plugin.instance is not None
        assert plugin.instance.x == 100

    def test_load_plugin_hooks_registered(self, plugin_dir):
        """加载插件时自动注册 hook_ 前缀函数"""
        pm = PluginManager()
        self._make_plugin_file(
            plugin_dir,
            "hooked",
            'PLUGIN_SPEC = {"name": "hooked"}\n'
            "def hook_on_load():\n    return 1\n"
            "def hook_on_activate():\n    return 2\n",
        )
        pm.add_search_path(plugin_dir)
        spec = pm._parse_plugin_file(os.path.join(plugin_dir, "hooked.py"))
        pm.register_plugin(spec)
        plugin = pm.load_plugin("hooked")
        assert "on_load" in plugin._hooks
        assert "on_activate" in plugin._hooks

    def test_load_plugin_failure(self):
        """加载失败时状态变为 FAILED"""
        pm = PluginManager()
        spec = PluginSpec(name="bad", file_path="/nonexistent/bad.py")
        pm.register_plugin(spec)
        with pytest.raises(Exception):
            pm.load_plugin("bad")
        plugin = pm.get_plugin("bad")
        assert plugin.state == PluginState.FAILED
        assert plugin.error is not None

    def test_activate_plugin(self):
        """激活插件"""
        pm = PluginManager()
        pm.register_plugin(PluginSpec(name="activate_me"))
        plugin = pm.activate_plugin("activate_me")
        assert plugin.state == PluginState.ACTIVE

    def test_deactivate_plugin(self):
        """停用插件"""
        pm = PluginManager()
        pm.register_plugin(PluginSpec(name="deact"))
        pm.activate_plugin("deact")
        pm.deactivate_plugin("deact")
        plugin = pm.get_plugin("deact")
        assert plugin.state == PluginState.LOADED

    def test_deactivate_plugin_not_active(self):
        """停用非 ACTIVE 状态插件无效果（不抛异常）"""
        pm = PluginManager()
        pm.register_plugin(PluginSpec(name="not_active"))
        pm.deactivate_plugin("not_active")  # 不抛异常

    def test_deactivate_nonexistent_plugin(self):
        """停用不存在的插件不抛异常"""
        pm = PluginManager()
        pm.deactivate_plugin("ghost")  # 不抛异常

    def test_uninstall_plugin_simple(self):
        """卸载已加载插件"""
        pm = PluginManager()
        pm.register_plugin(PluginSpec(name="rm"))
        pm.load_plugin("rm")
        assert pm.uninstall_plugin("rm") is True
        assert pm.get_plugin("rm") is None

    def test_uninstall_plugin_active(self):
        """卸载 ACTIVE 状态的插件（先停用再卸载）"""
        pm = PluginManager()
        pm.register_plugin(PluginSpec(name="rm_active"))
        pm.activate_plugin("rm_active")
        assert pm.uninstall_plugin("rm_active") is True
        assert pm.get_plugin("rm_active") is None

    def test_uninstall_nonexistent(self):
        """卸载不存在的插件返回 False"""
        pm = PluginManager()
        assert pm.uninstall_plugin("ghost") is False


# ── 全局钩子 ──────────────────────────────────────────────────────────────

class TestGlobalHooks:
    """测试全局钩子机制"""

    def test_call_global_hook_no_plugins(self):
        """无插件时调用全局钩子返回空列表"""
        pm = PluginManager()
        assert pm.call_global_hook("test") == []

    def test_call_global_hook_with_global_handler(self):
        """全局钩子（非插件级）"""
        pm = PluginManager()
        pm._hooks["test"] = [lambda: 42]
        assert pm.call_global_hook("test") == [42]

    def test_call_global_hook_global_handler_exception(self):
        """全局钩子处理器抛异常时打印错误并继续"""
        pm = PluginManager()
        pm._hooks["test"] = [lambda: 1 / 0, lambda: 99]
        results = pm.call_global_hook("test")
        assert 99 in results

    def test_call_global_hook_with_active_plugin(self):
        """已激活插件的钩子被调用"""
        pm = PluginManager()
        pm.register_plugin(PluginSpec(name="gh"))
        pm.activate_plugin("gh")
        plugin = pm.get_plugin("gh")
        plugin._hooks["test"] = [lambda: "from_plugin"]
        results = pm.call_global_hook("test")
        assert "from_plugin" in results

    def test_call_global_hook_inactive_plugin_skipped(self):
        """未激活插件的钩子不被调用"""
        pm = PluginManager()
        pm.register_plugin(PluginSpec(name="inactive"))
        plugin = pm.get_plugin("inactive")
        plugin._hooks["test"] = [lambda: "should_not_appear"]
        results = pm.call_global_hook("test")
        assert "should_not_appear" not in results


# ── 列表与统计 ────────────────────────────────────────────────────────────

class TestListStats:
    """测试 list_plugins 和 stats"""

    def test_list_plugins_all(self):
        """列出所有插件"""
        pm = PluginManager()
        pm.register_plugin(PluginSpec(name="a", version="1.0"))
        pm.register_plugin(PluginSpec(name="b", version="2.0"))
        result = pm.list_plugins()
        assert len(result) == 2
        names = {p["name"] for p in result}
        assert names == {"a", "b"}

    def test_list_plugins_filter_by_state(self):
        """按状态过滤插件"""
        pm = PluginManager()
        pm.register_plugin(PluginSpec(name="active_one"))
        pm.register_plugin(PluginSpec(name="unloaded_one"))
        pm.activate_plugin("active_one")
        active = pm.list_plugins(state=PluginState.ACTIVE)
        assert len(active) == 1
        assert active[0]["name"] == "active_one"

    def test_list_plugins_filter_no_match(self):
        """按状态过滤无匹配时返回空列表"""
        pm = PluginManager()
        pm.register_plugin(PluginSpec(name="p"))
        result = pm.list_plugins(state=PluginState.FAILED)
        assert result == []

    def test_list_plugins_fields(self):
        """list_plugins 返回完整字段"""
        pm = PluginManager()
        pm.register_plugin(
            PluginSpec(
                name="full", version="3.0", description="desc", author="me"
            )
        )
        result = pm.list_plugins()
        assert result[0]["name"] == "full"
        assert result[0]["version"] == "3.0"
        assert result[0]["description"] == "desc"
        assert result[0]["author"] == "me"
        assert result[0]["state"] == PluginState.UNLOADED
        assert result[0]["loaded_at"] is None
        assert result[0]["error"] is None

    def test_stats_empty(self):
        """空管理器统计"""
        pm = PluginManager()
        s = pm.stats()
        assert s["total"] == 0
        assert s["by_state"] == {}
        assert s["search_paths"] == []

    def test_stats_with_plugins(self):
        """有插件时的统计"""
        pm = PluginManager()
        pm.register_plugin(PluginSpec(name="a"))
        pm.register_plugin(PluginSpec(name="b"))
        pm.activate_plugin("a")
        s = pm.stats()
        assert s["total"] == 2
        assert s["by_state"].get(PluginState.ACTIVE) == 1
        assert s["by_state"].get(PluginState.UNLOADED) == 1

    def test_stats_with_search_paths(self):
        """stats 包含搜索路径"""
        pm = PluginManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            pm.add_search_path(tmpdir)
            s = pm.stats()
            assert tmpdir in s["search_paths"]


# ── _create_sample_plugin ──────────────────────────────────────────────────

class TestSamplePlugin:
    """测试 _create_sample_plugin 函数"""

    def test_create_sample_plugin(self):
        """_create_sample_plugin 创建示例插件文件"""
        # 使用临时目录，临时修改 __file__ 或直接操作
        _create_sample_plugin()
        sample_dir = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            ),
            "tengod", "比肩_架构协同", "plugins",
        )
        sample_file = os.path.join(sample_dir, "tengod_sample_plugin.py")
        assert os.path.exists(sample_file)
        with open(sample_file, "r") as f:
            content = f.read()
        assert "PLUGIN_SPEC" in content
        assert "zhwenshi-knowledge" in content
        # 清理
        os.unlink(sample_file)
        try:
            os.rmdir(sample_dir)
        except OSError:
            pass