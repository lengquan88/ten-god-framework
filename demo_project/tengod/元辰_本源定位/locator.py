#!/usr/bin/env python3
"""
元辰_本源定位 — 项目根目录/核心定位
元辰主理本源，承担项目的根目录定位与核心入口职责。
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import os
import sys


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
            if os.path.isdir(full) and not item.startswith(('.', '_')):
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


__all__ = ["YuanChenLocator", "ProjectRoot"]
__version__ = "1.0.0"