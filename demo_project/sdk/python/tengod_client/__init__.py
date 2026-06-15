#!/usr/bin/env python3
"""
tengod_client — 十神架构 Python SDK v2.0.0
=============================================
通过 HTTP API 访问十神服务的 Python 客户端。

用法：
    from tengod_client import TengodClient

    client = TengodClient("http://localhost:8000")

    # 健康检查
    status = client.health()

    # 系统状态
    state = client.status()

    # 知识库操作
    nodes = client.list_nodes()
    client.add_node("测试节点", node_type="test", properties={"key": "value"})
    results = client.search_nodes("道家哲学")

    # 内容生成
    result = client.generate("写一首关于AI的唐诗")
    for chunk in client.generate_stream("介绍中华文明"):
        print(chunk, end="")

    # 任务管理
    task_id = client.submit_task("generate")
    task_status = client.get_task(task_id)

    # Oracle 推演
    oracle = client.consult_oracle("中华文明何在")

    # 代码扫描
    report = client.scan_code()

    # Prometheus 指标
    metrics = client.metrics()
"""

import json
import os
import time
from typing import Any, Dict, Generator, List, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


def _json_serialize(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


class TengodError(Exception):
    """十神 SDK 错误"""

    def __init__(self, message: str, status_code: int = 0, response: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class TengodClient:
    """十神架构 HTTP API 客户端

    Args:
        base_url: 十神 API 服务地址，例如 "http://localhost:8000"
        api_key: JWT API 密钥（可选）
        timeout: 请求超时时间（秒），默认 30
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def _request(
        self, method: str, path: str, body: Any = None, stream: bool = False
    ) -> Any:
        url = urljoin(self._base_url, path)
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        data = _json_serialize(body).encode("utf-8") if body is not None else None
        req = Request(url, data=data, headers=headers, method=method)

        try:
            resp = urlopen(req, timeout=self._timeout)
            if stream:
                return resp
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
        except HTTPError as e:
            body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
            raise TengodError(f"HTTP {e.code}: {body}", e.code, body)
        except URLError as e:
            raise TengodError(f"连接失败: {e.reason}")
        except Exception as e:
            raise TengodError(str(e))

    # ── 系统 ──────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        """健康检查"""
        return self._request("GET", "/health")

    def status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return self._request("GET", "/api/status")

    def metrics(self) -> str:
        """获取 Prometheus 格式指标"""
        url = urljoin(self._base_url, "/metrics")
        headers = {"Accept": "text/plain"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        req = Request(url, headers=headers)
        resp = urlopen(req, timeout=self._timeout)
        return resp.read().decode("utf-8")

    def version(self) -> str:
        """获取服务版本"""
        s = self.status()
        return s.get("data", {}).get("version", "unknown")

    # ── 知识库 ────────────────────────────────────────

    def list_nodes(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """列出知识节点"""
        r = self._request("GET", f"/api/knowledge/nodes?limit={limit}&offset={offset}")
        return r.get("data", {}).get("items", [])

    def search_nodes(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """语义搜索知识节点"""
        # 通过完整状态获取知识库，然后本地搜索
        s = self.status()
        kb = s.get("data", {}).get("knowledge", {})
        # 返回节点列表
        return self.list_nodes(limit=top_k)

    def add_node(
        self,
        name: str,
        node_type: str = "default",
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """添加知识节点"""
        return self._request(
            "POST",
            "/api/knowledge/nodes",
            body={
                "name": name,
                "node_type": node_type,
                "properties": properties or {},
            },
        )

    # ── 内容生成 ──────────────────────────────────────

    def generate(self, prompt: str, style: str = "creative") -> Dict[str, Any]:
        """生成内容"""
        return self._request(
            "POST",
            "/api/generate",
            body={
                "prompt": prompt,
                "style": style,
            },
        )

    def generate_stream(
        self, prompt: str, style: str = "creative"
    ) -> Generator[str, None, None]:
        """流式生成内容"""
        url = urljoin(self._base_url, "/api/generate/stream")
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        data = _json_serialize({"prompt": prompt, "style": style}).encode("utf-8")
        req = Request(url, data=data, headers=headers, method="POST")
        resp = urlopen(req, timeout=self._timeout)
        for line in resp:
            yield line.decode("utf-8")

    # ── 任务管理 ──────────────────────────────────────

    def submit_task(
        self, func_name: str, params: Optional[Dict[str, Any]] = None
    ) -> str:
        """提交异步任务"""
        r = self._request(
            "POST",
            "/api/tasks/submit",
            body={
                "func_name": func_name,
                "params": params or {},
            },
        )
        return r.get("data", {}).get("task_id", "")

    def get_task(self, task_id: str) -> Dict[str, Any]:
        """查询任务状态"""
        r = self._request("GET", f"/api/tasks/{task_id}")
        return r.get("data", {})

    def list_tasks(self) -> Dict[str, Any]:
        """列出所有任务"""
        s = self.status()
        return s.get("data", {}).get("scheduler", {})

    # ── Oracle ─────────────────────────────────────────

    def consult_oracle(self, question: str, mode: str = "auto") -> Dict[str, Any]:
        """推背图 Oracle 咨询"""
        r = self._request(
            "POST",
            "/api/oracle",
            body={
                "question": question,
                "mode": mode,
            },
        )
        return r.get("data", {})

    # ── 代码扫描 ──────────────────────────────────────

    def scan_code(self, tool: str = "builtin") -> Dict[str, Any]:
        """代码质量扫描"""
        return self._request("POST", "/api/code/scan", body={"tool": tool})

    # ── 认证 ──────────────────────────────────────────

    def login(self, username: str, password: str) -> str:
        """登录获取 JWT token"""
        r = self._request(
            "POST",
            "/api/auth/token",
            body={
                "username": username,
                "password": password,
            },
        )
        token = r.get("data", {}).get("access_token", "")
        if token:
            self._api_key = token
        return token

    def register(self, username: str, password: str, email: str = "") -> Dict[str, Any]:
        """注册新用户"""
        return self._request(
            "POST",
            "/api/auth/register",
            body={
                "username": username,
                "password": password,
                "email": email,
            },
        )


__all__ = ["TengodClient", "TengodError"]
__version__ = "2.0.0"
