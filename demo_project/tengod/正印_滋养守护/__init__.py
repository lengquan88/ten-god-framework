#!/usr/bin/env python3
"""
正印_滋养守护 — 配置管理/环境初始化
正印主理滋养，承担系统的配置管理与环境初始化职责。
"""

from .config_manager import ConfigManager, Config, ConfigSource

__all__ = ["ConfigManager", "Config", "ConfigSource"]
__version__ = "1.0.0"
