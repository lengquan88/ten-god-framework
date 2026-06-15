#!/usr/bin/env python3
"""test_auth.py — 认证测试 (七杀·品质裁决)"""

from src.auth_service import authenticate, check_permission


def test_authenticate_valid():
    assert authenticate("admin") == True


def test_authenticate_invalid():
    assert authenticate("hacker") == False


def test_permission_admin():
    assert check_permission("admin", "delete") == True


def test_permission_viewer():
    assert check_permission("viewer", "write") == False


if __name__ == "__main__":
    test_authenticate_valid()
    test_authenticate_invalid()
    test_permission_admin()
    test_permission_viewer()
    print("All tests passed!")
