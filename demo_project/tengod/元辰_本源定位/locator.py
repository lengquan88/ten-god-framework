#!/usr/bin/env python3
"""
元辰_本源定位 — 项目根目录/核心定位
元辰主理本源，承担项目的根目录定位与核心入口职责。
"""

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProjectRoot:
    """项目根目录定位"""

    path: str
    name: str
    description: str = ""
    submodules: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)


class YuanChenLocator:
    """元辰定位器 — 本源之锚

    定位项目根目录，扫描核心文件，提供全局入口。
    """

    def __init__(self, root_path: Optional[str] = None):
        self._root = root_path or os.getcwd()
        self._project: Optional[ProjectRoot] = None

    def locate(self) -> ProjectRoot:
        """定位项目根目录"""
        # 查找标志性文件
        markers = ["README.md", "package.json", "requirements.txt", "Makefile", ".git"]
        found_markers = []
        for marker in markers:
            if os.path.exists(os.path.join(self._root, marker)):
                found_markers.append(marker)

        # 查找子模块
        submodules = []
        for item in os.listdir(self._root):
            full = os.path.join(self._root, item)
            if os.path.isdir(full) and not item.startswith((".", "_")):
                submodules.append(item)

        self._project = ProjectRoot(
            path=self._root,
            name=os.path.basename(self._root),
            description="项目根目录",
            submodules=submodules,
            config_files=found_markers,
        )
        return self._project

    def get_core_paths(self) -> Dict[str, str]:
        """获取核心路径"""
        if not self._project:
            self.locate()
        return {
            "root": self._project.path,
            "name": self._project.name,
            "tengod": os.path.join(self._project.path, "demo_project", "tengod"),
            "tests": os.path.join(self._project.path, "demo_project", "tests"),
            "docs": os.path.join(self._project.path, "docs"),
            "prd": os.path.join(self._project.path, "PRD"),
        }

    def add_to_path(self) -> None:
        """将核心路径添加到 sys.path"""
        paths = self.get_core_paths()
        for name, path in paths.items():
            if os.path.exists(path) and path not in sys.path:
                sys.path.insert(0, path)

    def summary(self) -> Dict[str, Any]:
        """生成摘要"""
        if not self._project:
            self.locate()
        return {
            "path": self._project.path,
            "name": self._project.name,
            "submodules_count": len(self._project.submodules),
            "config_files": self._project.config_files,
            "submodules": self._project.submodules[:10],
        }

    def scan_files(
        self, max_depth: int = 3, include_hidden: bool = False
    ) -> List[Dict[str, Any]]:
        """深度扫描项目文件树，返回结构化文件信息列表。

        每项包含：{path, name, ext, size, is_dir, depth}
        """
        if not self._project:
            self.locate()
        result: List[Dict[str, Any]] = []
        root = self._project.path

        def _walk(current: str, depth: int) -> None:
            if depth > max_depth:
                return
            try:
                for entry in os.listdir(current):
                    if not include_hidden and entry.startswith("."):
                        continue
                    full = os.path.join(current, entry)
                    is_dir = os.path.isdir(full)
                    _, ext = os.path.splitext(entry)
                    size = 0
                    try:
                        if not is_dir:
                            size = os.path.getsize(full)
                    except OSError:
                        pass
                    result.append(
                        {
                            "path": full,
                            "name": entry,
                            "ext": ext.lower(),
                            "size": size,
                            "is_dir": is_dir,
                            "depth": depth,
                        }
                    )
                    if is_dir:
                        _walk(full, depth + 1)
            except PermissionError:
                pass

        _walk(root, 0)
        return result

    def scan_to_knowledge(self, kb) -> Dict[str, int]:
        """扫描项目目录并自动生成知识图谱节点。

        将项目结构（目录、Python模块、配置文件）写入知识库：
        - 目录 → node_type="directory"
        - .py文件 → node_type="module"
        - 配置文件 → node_type="config_file"

        返回 {"directories": N, "modules": N, "config_files": N, "edges": N}
        """
        files = self.scan_files(max_depth=4)
        stats = {"directories": 0, "modules": 0, "config_files": 0, "edges": 0}

        # 阶段1：创建所有文件和目录节点
        parent_map: Dict[str, str] = {}  # path -> node_id
        for f in files:
            node_id = None
            props = {"path": f["path"], "size": f["size"]}
            if f["is_dir"]:
                node = kb.add_node(
                    name=f"[目录]{f['name']}",
                    node_type="directory",
                    properties=props,
                )
                node_id = node.id
                parent_map[f["path"]] = node_id
                stats["directories"] += 1
            elif f["ext"] == ".py":
                node = kb.add_node(
                    name=f"[模块]{f['name']}",
                    node_type="module",
                    properties=props,
                )
                node_id = node.id
                stats["modules"] += 1
            elif f["ext"] in (
                ".json",
                ".yaml",
                ".yml",
                ".toml",
                ".ini",
                ".cfg",
                ".env",
                ".txt",
            ):
                node = kb.add_node(
                    name=f"[配置]{f['name']}",
                    node_type="config_file",
                    properties=props,
                )
                node_id = node.id
                stats["config_files"] += 1

            if node_id:
                parent_map[f["path"]] = node_id

        # 阶段2：创建父子关系边
        for f in files:
            child_id = parent_map.get(f["path"])
            if not child_id:
                continue
            parent_dir = os.path.dirname(f["path"])
            parent_id = parent_map.get(parent_dir)
            if parent_id and parent_id != child_id:
                kb.add_edge(parent_id, child_id, "contains")
                stats["edges"] += 1

        # 阶段3：创建项目根节点
        root_node = kb.add_node(
            name=f"[项目]{self._project.name}",
            node_type="project",
            properties={
                "path": self._project.path,
                "submodules": self._project.submodules[:20],
                "config_files": self._project.config_files,
                "scanned_at": time.time(),
            },
        )
        # 连接根到一级子目录
        for f in files:
            if f["depth"] == 1 and f["is_dir"]:
                child_id = parent_map.get(f["path"])
                if child_id:
                    kb.add_edge(root_node.id, child_id, "contains")
                    stats["edges"] += 1

        return stats


__all__ = ["YuanChenLocator", "ProjectRoot"]
__version__ = "1.0.0"
