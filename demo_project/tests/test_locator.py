"""YuanChenLocator 与 ProjectRoot 模块的全面测试。"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

from tengod.元辰_本源定位.locator import ProjectRoot, YuanChenLocator


# ════════════════════════════════════════════════════════════════════
# ProjectRoot dataclass 测试
# ════════════════════════════════════════════════════════════════════

class TestProjectRoot:
    """测试 ProjectRoot 数据类。"""

    def test_create_with_all_fields(self):
        """创建包含所有字段的 ProjectRoot。"""
        pr = ProjectRoot(
            path="/tmp/test",
            name="test",
            description="测试项目",
            submodules=["a", "b"],
            config_files=["README.md", ".git"],
        )
        assert pr.path == "/tmp/test"
        assert pr.name == "test"
        assert pr.description == "测试项目"
        assert pr.submodules == ["a", "b"]
        assert pr.config_files == ["README.md", ".git"]

    def test_create_with_defaults(self):
        """创建仅含必填字段的 ProjectRoot，验证默认值。"""
        pr = ProjectRoot(path="/tmp/test", name="test")
        assert pr.description == ""
        assert pr.submodules == []
        assert pr.config_files == []

    def test_submodules_default_is_independent(self):
        """验证默认 submodules 列表是独立实例。"""
        pr1 = ProjectRoot(path="/tmp/a", name="a")
        pr2 = ProjectRoot(path="/tmp/b", name="b")
        pr1.submodules.append("x")
        assert pr2.submodules == []

    def test_config_files_default_is_independent(self):
        """验证默认 config_files 列表是独立实例。"""
        pr1 = ProjectRoot(path="/tmp/a", name="a")
        pr2 = ProjectRoot(path="/tmp/b", name="b")
        pr1.config_files.append("x")
        assert pr2.config_files == []

    def test_is_dataclass(self):
        """验证 ProjectRoot 是 dataclass 类型。"""
        from dataclasses import is_dataclass
        assert is_dataclass(ProjectRoot)


# ════════════════════════════════════════════════════════════════════
# YuanChenLocator 测试
# ════════════════════════════════════════════════════════════════════

class TestYuanChenLocatorInit:
    """测试 YuanChenLocator.__init__。"""

    def test_init_with_explicit_path(self):
        """使用显式路径初始化。"""
        locator = YuanChenLocator(root_path="/tmp")
        assert locator._root == "/tmp"
        assert locator._project is None

    def test_init_with_default_cwd(self):
        """使用默认路径（当前工作目录）初始化。"""
        locator = YuanChenLocator()
        assert locator._root == os.getcwd()
        assert locator._project is None

    def test_init_with_none_path(self):
        """传入 None 应使用当前工作目录。"""
        locator = YuanChenLocator(root_path=None)
        assert locator._root == os.getcwd()


class TestYuanChenLocatorLocate:
    """测试 locate() 方法。"""

    def test_locate_returns_project_root(self, tmp_path):
        """locate() 返回 ProjectRoot 实例。"""
        # 在临时目录中创建标志文件
        (tmp_path / "README.md").write_text("# test")
        (tmp_path / ".git").mkdir()
        locator = YuanChenLocator(root_path=str(tmp_path))
        result = locator.locate()
        assert isinstance(result, ProjectRoot)
        assert result.path == str(tmp_path)
        assert result.name == tmp_path.name

    def test_locate_finds_markers(self, tmp_path):
        """locate() 发现标志文件。"""
        (tmp_path / "README.md").write_text("# test")
        (tmp_path / ".git").mkdir()
        (tmp_path / "requirements.txt").write_text("pytest")
        locator = YuanChenLocator(root_path=str(tmp_path))
        result = locator.locate()
        assert "README.md" in result.config_files
        assert ".git" in result.config_files
        assert "requirements.txt" in result.config_files

    def test_locate_no_markers(self, tmp_path):
        """目录中没有标志文件时 config_files 为空。"""
        locator = YuanChenLocator(root_path=str(tmp_path))
        result = locator.locate()
        assert result.config_files == []

    def test_locate_finds_submodules(self, tmp_path):
        """locate() 发现子模块（非点号开头的目录）。"""
        (tmp_path / "README.md").write_text("# test")
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "docs").mkdir()
        locator = YuanChenLocator(root_path=str(tmp_path))
        result = locator.locate()
        assert "src" in result.submodules
        assert "tests" in result.submodules
        assert "docs" in result.submodules

    def test_locate_skips_dot_dirs(self, tmp_path):
        """locate() 跳过以点号开头的目录。"""
        (tmp_path / "README.md").write_text("# test")
        (tmp_path / "src").mkdir()
        (tmp_path / ".git").mkdir()
        (tmp_path / ".venv").mkdir()
        (tmp_path / "_private").mkdir()  # 下划线开头也跳过
        locator = YuanChenLocator(root_path=str(tmp_path))
        result = locator.locate()
        assert "src" in result.submodules
        assert ".git" not in result.submodules
        assert ".venv" not in result.submodules
        assert "_private" not in result.submodules

    def test_locate_stores_project(self, tmp_path):
        """locate() 将结果存储到 self._project。"""
        (tmp_path / "README.md").write_text("# test")
        locator = YuanChenLocator(root_path=str(tmp_path))
        locator.locate()
        assert locator._project is not None
        assert locator._project.name == tmp_path.name


class TestYuanChenLocatorGetCorePaths:
    """测试 get_core_paths() 方法。"""

    def test_get_core_paths_structure(self, tmp_path):
        """get_core_paths() 返回正确的字典结构。"""
        (tmp_path / "README.md").write_text("test")
        locator = YuanChenLocator(root_path=str(tmp_path))
        paths = locator.get_core_paths()
        assert "root" in paths
        assert "name" in paths
        assert "tengod" in paths
        assert "tests" in paths
        assert "docs" in paths
        assert "prd" in paths
        assert paths["root"] == str(tmp_path)
        assert paths["name"] == tmp_path.name

    def test_get_core_paths_calls_locate(self, tmp_path):
        """get_core_paths() 如果尚未调用 locate() 会自动调用。"""
        (tmp_path / "README.md").write_text("# test")
        locator = YuanChenLocator(root_path=str(tmp_path))
        assert locator._project is None
        paths = locator.get_core_paths()
        assert locator._project is not None
        assert paths["root"] == str(tmp_path)

    def test_get_core_paths_does_not_re_locate(self, tmp_path):
        """如果已经 locate() 过，get_core_paths() 不重复执行。"""
        (tmp_path / "README.md").write_text("# test")
        locator = YuanChenLocator(root_path=str(tmp_path))
        first = locator.locate()
        paths = locator.get_core_paths()
        assert locator._project is first


class TestYuanChenLocatorAddToPath:
    """测试 add_to_path() 方法。"""

    def test_add_to_path_adds_entries(self, tmp_path):
        """add_to_path() 将存在的路径添加到 sys.path。"""
        (tmp_path / "README.md").write_text("# test")
        locator = YuanChenLocator(root_path=str(tmp_path))
        original_len = len(sys.path)
        locator.add_to_path()
        # 根路径应该被添加（因为存在）
        assert str(tmp_path) in sys.path

    def test_add_to_path_no_duplicates(self, tmp_path):
        """重复调用 add_to_path() 不会重复添加。"""
        (tmp_path / "README.md").write_text("# test")
        locator = YuanChenLocator(root_path=str(tmp_path))
        locator.add_to_path()
        count = sys.path.count(str(tmp_path))
        locator.add_to_path()
        assert sys.path.count(str(tmp_path)) == count


class TestYuanChenLocatorSummary:
    """测试 summary() 方法。"""

    def test_summary_structure(self, tmp_path):
        """summary() 返回正确的字典结构。"""
        (tmp_path / "README.md").write_text("# test")
        (tmp_path / "src").mkdir()
        locator = YuanChenLocator(root_path=str(tmp_path))
        s = locator.summary()
        assert s["path"] == str(tmp_path)
        assert s["name"] == tmp_path.name
        assert s["submodules_count"] == 1
        assert "README.md" in s["config_files"]
        assert "src" in s["submodules"]

    def test_summary_calls_locate_if_needed(self, tmp_path):
        """summary() 如果未 locate 会自动调用。"""
        (tmp_path / "README.md").write_text("# test")
        locator = YuanChenLocator(root_path=str(tmp_path))
        assert locator._project is None
        s = locator.summary()
        assert locator._project is not None
        assert s["path"] == str(tmp_path)


class TestYuanChenLocatorScanFiles:
    """测试 scan_files() 方法。"""

    def test_scan_files_default_depth(self, tmp_path):
        """scan_files() 使用默认深度扫描。"""
        (tmp_path / "README.md").write_text("hello")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print(1)")
        locator = YuanChenLocator(root_path=str(tmp_path))
        files = locator.scan_files()
        assert isinstance(files, list)
        assert len(files) > 0
        # 检查文件结构
        paths = [f["name"] for f in files]
        assert "README.md" in paths
        assert "src" in paths

    def test_scan_files_calls_locate_if_needed(self, tmp_path):
        """scan_files() 如果未 locate 会自动调用。"""
        (tmp_path / "README.md").write_text("hello")
        locator = YuanChenLocator(root_path=str(tmp_path))
        assert locator._project is None
        locator.scan_files()
        assert locator._project is not None

    def test_scan_files_field_structure(self, tmp_path):
        """scan_files() 返回的每项包含正确的字段。"""
        (tmp_path / "README.md").write_text("hello")
        locator = YuanChenLocator(root_path=str(tmp_path))
        files = locator.scan_files(max_depth=1)
        for f in files:
            assert "path" in f
            assert "name" in f
            assert "ext" in f
            assert "size" in f
            assert "is_dir" in f
            assert "depth" in f

    def test_scan_files_depth_0(self, tmp_path):
        """scan_files(max_depth=0) 只扫描根目录。"""
        (tmp_path / "README.md").write_text("hello")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print(1)")
        locator = YuanChenLocator(root_path=str(tmp_path))
        files = locator.scan_files(max_depth=0)
        for f in files:
            assert f["depth"] == 0

    def test_scan_files_depth_1(self, tmp_path):
        """scan_files(max_depth=1) 扫描到深度 1。"""
        (tmp_path / "README.md").write_text("hello")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print(1)")
        (tmp_path / "src" / "sub").mkdir()
        (tmp_path / "src" / "sub" / "deep.py").write_text("pass")
        locator = YuanChenLocator(root_path=str(tmp_path))
        files = locator.scan_files(max_depth=1)
        depths = set(f["depth"] for f in files)
        assert 0 in depths
        assert 1 in depths
        assert 2 not in depths

    def test_scan_files_custom_depth(self, tmp_path):
        """scan_files() 使用自定义深度。"""
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "b").mkdir()
        (tmp_path / "a" / "b" / "c").mkdir()
        (tmp_path / "a" / "b" / "c" / "d").mkdir()
        locator = YuanChenLocator(root_path=str(tmp_path))
        files = locator.scan_files(max_depth=2)
        depths = set(f["depth"] for f in files)
        assert max(depths) <= 2

    def test_scan_files_skips_hidden_by_default(self, tmp_path):
        """scan_files() 默认跳过隐藏文件/目录。"""
        (tmp_path / "README.md").write_text("hello")
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".hidden" / "secret.txt").write_text("secret")
        (tmp_path / ".gitignore").write_text("*.pyc")
        locator = YuanChenLocator(root_path=str(tmp_path))
        files = locator.scan_files()
        names = [f["name"] for f in files]
        assert ".hidden" not in names
        assert ".gitignore" not in names

    def test_scan_files_include_hidden(self, tmp_path):
        """scan_files(include_hidden=True) 包含隐藏文件/目录。"""
        (tmp_path / "README.md").write_text("hello")
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".hidden" / "secret.txt").write_text("secret")
        (tmp_path / ".gitignore").write_text("*.pyc")
        locator = YuanChenLocator(root_path=str(tmp_path))
        files = locator.scan_files(include_hidden=True)
        names = [f["name"] for f in files]
        assert ".hidden" in names
        assert ".gitignore" in names

    def test_scan_files_size(self, tmp_path):
        """scan_files() 正确报告文件大小。"""
        (tmp_path / "data.txt").write_text("hello world")
        locator = YuanChenLocator(root_path=str(tmp_path))
        files = locator.scan_files()
        for f in files:
            if f["name"] == "data.txt":
                assert f["size"] == 11
                assert f["ext"] == ".txt"
                assert not f["is_dir"]

    def test_scan_files_ext_lowercase(self, tmp_path):
        """scan_files() 返回的扩展名为小写。"""
        (tmp_path / "README.MD").write_text("test")
        locator = YuanChenLocator(root_path=str(tmp_path))
        files = locator.scan_files()
        for f in files:
            if f["name"] == "README.MD":
                assert f["ext"] == ".md"

    def test_scan_files_permission_error_handled(self, tmp_path):
        """scan_files() 在 PermissionError 时不崩溃。"""
        (tmp_path / "README.md").write_text("test")
        (tmp_path / "locked").mkdir()
        locator = YuanChenLocator(root_path=str(tmp_path))
        # 先调用 locate() 以避免 mock 影响 locate 内部的 os.listdir
        locator.locate()
        # 现在 mock os.listdir 只在 _walk 阶段生效
        real_listdir = os.listdir
        call_count = [0]

        def mock_listdir(path):
            call_count[0] += 1
            # 第一次调用是 _walk 对根目录的 listdir，让它失败
            if call_count[0] == 1:
                raise PermissionError
            return real_listdir(path)

        with patch("os.listdir", side_effect=mock_listdir):
            files = locator.scan_files()
            # PermissionError 被捕获，结果为空
            assert files == []

    def test_scan_files_subdir_permission_error(self, tmp_path):
        """scan_files() 在子目录 PermissionError 时继续扫描。"""
        (tmp_path / "README.md").write_text("test")
        (tmp_path / "ok_dir").mkdir()
        (tmp_path / "locked").mkdir()
        real_listdir = os.listdir

        def mock_listdir(path):
            if path.endswith("locked"):
                raise PermissionError
            return real_listdir(path)

        locator = YuanChenLocator(root_path=str(tmp_path))
        with patch("os.listdir", side_effect=mock_listdir):
            files = locator.scan_files()
        names = [f["name"] for f in files]
        # 根目录下的项应该可见，locked 子目录中的项不可见
        assert "README.md" in names
        assert "ok_dir" in names


class TestYuanChenLocatorScanToKnowledge:
    """测试 scan_to_knowledge() 方法。"""

    @staticmethod
    def _make_mock_kb():
        """创建带 add_node / add_edge 的模拟知识库。"""
        kb = Mock()
        node_counter = [0]

        def add_node(name, node_type, properties=None):
            node_counter[0] += 1
            node = Mock()
            node.id = f"node_{node_counter[0]}"
            node.name = name
            return node

        kb.add_node = Mock(side_effect=add_node)
        kb.add_edge = Mock()

        return kb

    def test_scan_to_knowledge_returns_stats(self, tmp_path):
        """scan_to_knowledge() 返回正确的统计字典。"""
        (tmp_path / "README.md").write_text("test")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print(1)")
        (tmp_path / "config.json").write_text("{}")
        locator = YuanChenLocator(root_path=str(tmp_path))
        kb = self._make_mock_kb()
        stats = locator.scan_to_knowledge(kb)
        assert "directories" in stats
        assert "modules" in stats
        assert "config_files" in stats
        assert "edges" in stats

    def test_scan_to_knowledge_creates_directory_nodes(self, tmp_path):
        """scan_to_knowledge() 为目录创建节点。"""
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        locator = YuanChenLocator(root_path=str(tmp_path))
        kb = self._make_mock_kb()
        stats = locator.scan_to_knowledge(kb)
        assert stats["directories"] >= 2  # src, tests

    def test_scan_to_knowledge_creates_module_nodes(self, tmp_path):
        """scan_to_knowledge() 为 .py 文件创建模块节点。"""
        (tmp_path / "main.py").write_text("pass")
        (tmp_path / "utils.py").write_text("pass")
        locator = YuanChenLocator(root_path=str(tmp_path))
        kb = self._make_mock_kb()
        stats = locator.scan_to_knowledge(kb)
        assert stats["modules"] >= 2

    def test_scan_to_knowledge_creates_config_nodes(self, tmp_path):
        """scan_to_knowledge() 为配置文件创建配置节点。"""
        (tmp_path / "config.json").write_text("{}")
        (tmp_path / "settings.yaml").write_text("key: val")
        (tmp_path / "pyproject.toml").write_text("[tool]")
        (tmp_path / "app.ini").write_text("[app]")
        locator = YuanChenLocator(root_path=str(tmp_path))
        kb = self._make_mock_kb()
        stats = locator.scan_to_knowledge(kb)
        assert stats["config_files"] >= 4

    def test_scan_to_knowledge_creates_edges(self, tmp_path):
        """scan_to_knowledge() 创建父子关系边。"""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print(1)")
        locator = YuanChenLocator(root_path=str(tmp_path))
        kb = self._make_mock_kb()
        stats = locator.scan_to_knowledge(kb)
        assert stats["edges"] > 0

    def test_scan_to_knowledge_creates_root_node(self, tmp_path):
        """scan_to_knowledge() 创建项目根节点。"""
        (tmp_path / "src").mkdir()
        locator = YuanChenLocator(root_path=str(tmp_path))
        kb = self._make_mock_kb()
        locator.scan_to_knowledge(kb)
        # 检查 add_node 被调用来创建项目根节点
        project_calls = [
            call for call in kb.add_node.call_args_list
            if call[1].get("node_type") == "project"
        ]
        assert len(project_calls) == 1

    def test_scan_to_knowledge_node_types(self, tmp_path):
        """scan_to_knowledge() 使用正确的 node_type。"""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("pass")
        (tmp_path / "config.json").write_text("{}")
        locator = YuanChenLocator(root_path=str(tmp_path))
        kb = self._make_mock_kb()
        locator.scan_to_knowledge(kb)
        node_types = [
            call[1]["node_type"]
            for call in kb.add_node.call_args_list
            if "node_type" in call[1]
        ]
        assert "directory" in node_types
        assert "module" in node_types
        assert "config_file" in node_types
        assert "project" in node_types

    def test_scan_to_knowledge_connects_root_to_depth1_dirs(self, tmp_path):
        """scan_to_knowledge() 将根节点连接到深度 1 的子目录。"""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "sub_pkg").mkdir()
        (tmp_path / "src" / "sub_pkg" / "mod.py").write_text("pass")
        locator = YuanChenLocator(root_path=str(tmp_path))
        kb = self._make_mock_kb()
        stats = locator.scan_to_knowledge(kb)
        # 验证根节点到 depth=1 子目录的连接边存在
        assert stats["edges"] > 0

    def test_scan_to_knowledge_ignores_unknown_files(self, tmp_path):
        """scan_to_knowledge() 忽略非 Python、非配置文件的未知文件。"""
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        (tmp_path / "data.bin").write_bytes(b"\x00\x01")
        locator = YuanChenLocator(root_path=str(tmp_path))
        kb = self._make_mock_kb()
        stats = locator.scan_to_knowledge(kb)
        # png 和 bin 文件不应创建节点(除了目录节点)
        assert stats["modules"] == 0
        assert stats["config_files"] == 0


# ════════════════════════════════════════════════════════════════════
# 边界情况测试
# ════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """测试边界情况。"""

    def test_empty_directory(self, tmp_path):
        """空目录的处理。"""
        locator = YuanChenLocator(root_path=str(tmp_path))
        result = locator.locate()
        assert result.path == str(tmp_path)
        assert result.submodules == []
        assert result.config_files == []

    def test_empty_directory_scan(self, tmp_path):
        """空目录的 scan_files()。"""
        locator = YuanChenLocator(root_path=str(tmp_path))
        files = locator.scan_files()
        assert files == []

    def test_non_existent_path(self):
        """不存在的路径：locate() 会抛出 FileNotFoundError（os.listdir 失败）。"""
        locator = YuanChenLocator(root_path="/nonexistent/path/12345")
        with pytest.raises(FileNotFoundError):
            locator.locate()

    def test_scan_files_with_non_existent_path(self):
        """不存在的路径：scan_files() 不崩溃（os.listdir 会抛 FileNotFoundError）。"""
        locator = YuanChenLocator(root_path="/nonexistent/path/12345")
        with pytest.raises(FileNotFoundError):
            locator.scan_files()

    def test_scan_files_existing_project(self):
        """对真实项目路径执行 scan_files()。"""
        # 使用 demo_project 根目录
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        locator = YuanChenLocator(root_path=project_root)
        files = locator.scan_files(max_depth=1)
        assert len(files) > 0
        names = [f["name"] for f in files]
        # 验证一些已知文件
        assert "Makefile" in names or "requirements.txt" in names or "README.md" in names

    def test_scan_files_depth_default_3(self, tmp_path):
        """验证默认深度为 3。"""
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "b").mkdir()
        (tmp_path / "a" / "b" / "c").mkdir()
        (tmp_path / "a" / "b" / "c" / "d").mkdir()
        (tmp_path / "a" / "b" / "c" / "d" / "e").mkdir()
        locator = YuanChenLocator(root_path=str(tmp_path))
        files = locator.scan_files()  # 默认 max_depth=3
        depths = set(f["depth"] for f in files)
        assert max(depths) <= 3

    def test_summary_submodules_truncation(self, tmp_path):
        """summary() 的 submodules 截断到 10 个。"""
        (tmp_path / "README.md").write_text("test")
        for i in range(15):
            (tmp_path / f"mod_{i}").mkdir()
        locator = YuanChenLocator(root_path=str(tmp_path))
        s = locator.summary()
        assert len(s["submodules"]) <= 10
        assert s["submodules_count"] == 15

    def test_scan_files_oserror_on_getsize(self, tmp_path):
        """scan_files() 在 os.path.getsize 抛出 OSError 时不会崩溃。"""
        (tmp_path / "README.md").write_text("test")
        locator = YuanChenLocator(root_path=str(tmp_path))
        with patch("os.path.getsize", side_effect=OSError):
            files = locator.scan_files()
            for f in files:
                if not f["is_dir"]:
                    assert f["size"] == 0

    def test_get_core_paths_paths_existence(self, tmp_path):
        """get_core_paths() 返回的路径格式正确。"""
        (tmp_path / "README.md").write_text("test")
        locator = YuanChenLocator(root_path=str(tmp_path))
        paths = locator.get_core_paths()
        root = str(tmp_path)
        assert paths["tengod"] == os.path.join(root, "demo_project", "tengod")
        assert paths["tests"] == os.path.join(root, "demo_project", "tests")
        assert paths["docs"] == os.path.join(root, "docs")
        assert paths["prd"] == os.path.join(root, "PRD")