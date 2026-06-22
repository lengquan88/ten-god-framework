"""
TenGod - Chinese Fortune Telling System
A comprehensive Chinese metaphysics calculation and analysis system
"""
__version__ = "1.5.0"
__author__ = "TenGod Team"

from .core import get_core, create_app

__all__ = ["get_core", "create_app", "__version__"]
