#!/usr/bin/env python3
"""
劫财_攻防边界 — 安全防护/权限校验
劫财主理攻防，承担系统的安全边界与权限校验职责。
"""

from .guard import Guard, Permission, SecurityContext

__all__ = ["Guard", "Permission", "SecurityContext"]
__version__ = "1.0.0"
