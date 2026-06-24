"""
tianmen_middleware.py — 天眼全局中间件 v2.15.0
====================================================
道曰："天门开阖，能为雌乎？"

所有 API 请求输出，自动经过天眼门禁审核。
不阻断正常响应，只对低置信度高熵输出，加上 X-Tianmen 头，触发回头看。
"""

from __future__ import annotations
import time
import json
from typing import Any, Callable, Dict, List, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Scope, Receive, Send

from .tiangan_gate import get_tianmen, ZhizhiVerdict
from .self_correction import get_daemon


# ============================================================================
# 配置
# ============================================================================

# 哪些端点不需要门禁
EXCLUDE_PATHS = {
    '/',
    '/health',
    '/health/live',
    '/health/full',
    '/docs',
    '/openapi.json',
    '/redoc',
    '/api/v2/gate/',  # 门禁监控端点自身免检
}

# 哪些端点必须门禁
MANDATORY_GATE = {
    '/api/v2/',
    '/api/bazi/',
    '/api/ziwei/',
    '/api/qimen/',
    '/api/liuyao/',
}


# ============================================================================
# 天眼中间件
# ============================================================================

class TianmenMiddleware(BaseHTTPMiddleware):
    """
    天眼门禁全局中间件。

    Features:
      1. 所有 API 请求输出自动经过知止判定
      2. 添加 X-Tianmen 头记录判定结果
      3. 统计门禁数据
      4. 低置信度自动触发自修正
    """

    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[List[str]] = None,
        mandatory_gate: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self._exclude_paths = set(exclude_paths) if exclude_paths else EXCLUDE_PATHS
        self._mandatory_gate = set(mandatory_gate) if mandatory_gate else MANDATORY_GATE
        self._tianmen = get_tianmen()
        self._daemon = get_daemon()
        self._total_requests = 0
        self._blocked_requests = 0
        self._corrected_requests = 0
        # 回写全局单例（FastAPI add_middleware 实例化后可通过 get_middleware() 获取）
        global _tianmen_middleware
        _tianmen_middleware = self

    def should_gate(self, path: str) -> bool:
        """判断是否需要门禁"""
        # 先检查排除列表（前缀匹配）
        for exclude in self._exclude_paths:
            if path == exclude:
                return False
            # 前缀匹配：排除路径以 / 结尾表示目录前缀（排除 '/' 根路径）
            if exclude != '/' and exclude.endswith('/') and path.startswith(exclude):
                return False
        for prefix in self._mandatory_gate:
            if path.startswith(prefix):
                return True
        # 默认所有 /api 都过门禁
        return path.startswith('/api')

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        path = request.url.path
        self._total_requests += 1

        # 跳过不需要门禁的路径
        if not self.should_gate(path):
            return await call_next(request)

        start_time = time.time()

        # 先获取原始响应
        response = await call_next(request)

        # 尝试获取响应体（流式响应跳过）
        content_type = response.headers.get('content-type', '') or response.media_type or ''
        if 'text/' in content_type or 'application/json' in content_type:
            # 读取 body
            body_bytes = b''
            async for chunk in response.body_iterator:
                body_bytes += chunk

            # 解析内容
            try:
                content = json.loads(body_bytes)
            except:
                # 非 JSON 直接返回
                return Response(
                    content=body_bytes,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

            # 知止判定
            verdict = self._tianmen.engine.judge(
                output=content,
                confidence_scores=self._extract_confidence(content),
            )

            # 添加响应头
            headers = dict(response.headers)
            headers['X-Tianmen-Passed'] = str(verdict.passed).lower()
            headers['X-Tianmen-Confidence'] = f"{verdict.confidence:.3f}"
            headers['X-Tianmen-Qi'] = f"{verdict.cultivation_qi:.3f}"
            if not verdict.passed:
                # 响应头只允许 ASCII/latin-1，中文原因只能转 ASCII 或省略
                # 保留原因信息，转 latin-1 安全编码
                safe_reason = verdict.retreat_reason.encode('utf-8').hex()
                headers['X-Tianmen-Reason'] = safe_reason
                self._blocked_requests += 1

            # 低置信度触发自修正
            if verdict.should_retreat:
                corrected, report = self._daemon.correct({
                    'output': content,
                    'confidence': verdict.confidence,
                    'uncertainty': verdict.entropies.get('output', 0.5),
                }, enable_gate=True)
                if report.success:
                    self._corrected_requests += 1
                    content = corrected
                    body_bytes = json.dumps(content).encode()

            # 返回包装后的响应
            # 移除 Content-Length（body 可能被修改），让服务器用 chunked 编码
            headers.pop('content-length', None)
            return Response(
                content=body_bytes,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type,
            )

        # 流式，不加处理
        return response

    def _extract_confidence(self, content: Any) -> Dict[str, float]:
        """从输出提取置信度分数"""
        scores: Dict[str, float] = {}
        if isinstance(content, dict):
            if 'confidence' in content:
                scores['output'] = float(content.get('confidence', 0.5))
            if 'score' in content:
                scores['score'] = float(content.get('score', 0.5))
            if 'overall' in content:
                scores['overall'] = float(content['overall']['confidence'] if isinstance(content['overall'], dict) else content['overall'])
        if not scores:
            scores['overall'] = 0.5
        return scores

    def get_stats(self) -> Dict[str, Any]:
        """获取中间件统计"""
        return {
            'total_requests': self._total_requests,
            'blocked_requests': self._blocked_requests,
            'corrected_requests': self._corrected_requests,
            'block_rate': round(
                self._blocked_requests / max(1, self._total_requests), 3
            ),
            'correction_rate': round(
                self._corrected_requests / max(1, self._blocked_requests), 3
            ) if self._blocked_requests > 0 else 0.0,
            'tianmen': self._tianmen.get_stats(),
            'correction': self._daemon.get_stats(),
        }


# ============================================================================
# 全局单例
# ============================================================================

_tianmen_middleware: Optional[TianmenMiddleware] = None


def get_middleware(
    exclude_paths: Optional[List[str]] = None,
    mandatory_gate: Optional[List[str]] = None,
) -> TianmenMiddleware:
    global _tianmen_middleware
    if _tianmen_middleware is None:
        _tianmen_middleware = TianmenMiddleware(
            None,  # type: ignore
            exclude_paths,
            mandatory_gate,
        )
    return _tianmen_middleware


__all__ = [
    "TianmenMiddleware",
    "get_middleware",
]
