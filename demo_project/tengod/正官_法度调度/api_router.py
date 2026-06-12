#!/usr/bin/env python3
"""
api_router.py — 简易 API 路由器
正官主理法度，提供统一的接口调度机制。
"""

from typing import Callable, Dict, List, Any
from functools import wraps


class APIRouter:
    """API 路由器 — 法度之表

    支持 GET/POST/PUT/DELETE 等 HTTP 方法的注册与分发。
    """

    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        self._routes: Dict[str, Dict[str, Callable]] = {}
        self._middleware: List[Callable] = []

    def route(self, path: str, method: str = "GET") -> Callable:
        """装饰器：注册路由"""
        def decorator(func: Callable) -> Callable:
            full_path = f"{self.prefix}{path}"
            if full_path not in self._routes:
                self._routes[full_path] = {}
            self._routes[full_path][method.upper()] = func

            @wraps(func)
            def wrapper(*args, **kwargs):
                # 执行中间件
                for mw in self._middleware:
                    mw(*args, **kwargs)
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def get(self, path: str) -> Callable:
        return self.route(path, "GET")

    def post(self, path: str) -> Callable:
        return self.route(path, "POST")

    def put(self, path: str) -> Callable:
        return self.route(path, "PUT")

    def delete(self, path: str) -> Callable:
        return self.route(path, "DELETE")

    def add_middleware(self, func: Callable) -> None:
        """添加中间件"""
        self._middleware.append(func)

    def dispatch(self, path: str, method: str = "GET", *args, **kwargs) -> Any:
        """分发请求"""
        full_path = f"{self.prefix}{path}"
        routes = self._routes.get(full_path, {})
        handler = routes.get(method.upper())
        if not handler:
            raise ValueError(f"Route not found: {method} {full_path}")
        return handler(*args, **kwargs)

    def list_routes(self) -> List[Dict[str, str]]:
        """列出所有路由"""
        result = []
        for path, methods in self._routes.items():
            for method in methods:
                result.append({"method": method, "path": path})
        return result


# 快捷装饰器
_default_router = APIRouter()


def route(path: str, method: str = "GET") -> Callable:
    """快捷路由注册"""
    return _default_router.route(path, method)


def get(path: str) -> Callable:
    return _default_router.get(path)


def post(path: str) -> Callable:
    return _default_router.post(path)
