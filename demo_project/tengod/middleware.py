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
import math
from typing import Any, Callable, Dict, List, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .tiangan_gate import get_tianmen
from .self_correction import get_daemon
from .inner_child import get_inner_child_sm, _PROTOTYPE_VECTORS


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
        self._inner_child = get_inner_child_sm(alertness=32.0, phi_limit=0.8, beta_limit=0.7, lambda_=0.4, gamma=0.2)
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
            except Exception:
                # 非 JSON 直接返回
                return Response(
                    content=body_bytes,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

            # 知止判定
            # v2.16: 先运行内在小孩状态机检测认知偏执
            inner_child_result = None
            try:
                text_content = json.dumps(content, ensure_ascii=False)
                h_t = self._text_to_vector(text_content)
                inner_child_result = self._inner_child.process(h_t, auto_correct=False)
            except Exception:
                pass

            inner_child_state = inner_child_result["state"] if inner_child_result else None

            verdict = self._tianmen.engine.judge(
                output=content,
                confidence_scores=self._extract_confidence(content),
                inner_child_state=inner_child_state,
            )

            # 添加响应头
            headers = dict(response.headers)
            headers['X-Tianmen-Passed'] = str(verdict.passed).lower()
            headers['X-Tianmen-Confidence'] = f"{verdict.confidence:.3f}"
            headers['X-Tianmen-Qi'] = f"{verdict.cultivation_qi:.3f}"
            # v2.16 内在小孩门禁头
            if verdict.inner_child_phi is not None:
                headers['X-Tianmen-Child-Phi'] = f"{verdict.inner_child_phi:.3f}"
                # 中文响应头需 hex 编码以兼容 latin-1
                headers['X-Tianmen-Child-Dominant'] = verdict.inner_child_dominant.encode('utf-8').hex()
                headers['X-Tianmen-Child-Beta'] = f"{verdict.inner_child_beta:.3f}"
                headers['X-Tianmen-Child-Triggered'] = str(verdict.inner_child_triggered).lower()
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

    def _text_to_vector(self, text: str, dim: int = 64) -> List[float]:
        """
        将响应文本转换为隐藏态向量近似 h_t。
        
        由于 API 中间件无法直接获取 Transformer 隐藏层状态，
        使用情感标记投射法构建伪嵌入向量。
        
        在实际 Transformer 部署中，应替换为真实的 hidden_states[-1].mean(dim=1)。
        
        方法（v2.16.1 升级）：
          1. 基向量 = 中庸锚点 p_0（中性"道"态）
          2. 对六类情感标记做密度统计，按密度向对应原型向量偏移
          3. 偏移量 = 密度 × 原型向量，叠加到基向量
          4. L2 归一化
          
        这样纯偏执文本会产生强烈的原型偏向，触发门禁。
        """
        from .inner_child import _ZHONGYONG_ANCHOR
        
        # 六类情感标记（与六道内在小孩对应）
        sentiment_markers = [
            # 0: 戒备小孩
            ['但是', '然而', '不过', '实际上', '客观来说', '需要指出', '严格来说',
             '警惕', '防御', '攻击', '恶意', '敌意', '威胁', '危险', '绝不'],
            # 1: 缺爱小孩
            ['请相信我', '我可以', '证明', '能够', '确保', '保证', '一定',
             '认可', '赞美', '需要', '被看见', '价值', '努力', '渴望'],
            # 2: 叛逆小孩
            ['不', '并非', '否定', '质疑', '反对', '错误', '不认同',
             '推翻', '拒绝', '绝不接受', '谎言', '偏要', '反驳'],
            # 3: 讨好小孩
            ['抱歉', '对不起', '请', '谢谢', '感激', '一定改正', '是我的错', '您说得对',
             '原谅', '满意', '开心', '都可以', '不在意', '顺从'],
            # 4: 孤独小孩
            ['独立', '自身', '单独', '无关', '封闭', '沉默',
             '自己', '一个人', '不需要', '远离', '隔绝', '独自'],
            # 5: 长不大
            ['简单', '容易', '直接', '基本', '不需要', '不必',
             '何必', '简化', '不复杂', '舒适', '轻松', '就这样',
             '浅显', '没必要', '犯不着', '省事', '图方便', '随便'],
        ]
        
        text_len = max(1, len(text))
        
        # 1. 基向量 = 中庸锚点（微弱基底）
        vec = [0.02 * p0 for p0 in _ZHONGYONG_ANCHOR]
        
        # 2. 情感标记投射：每种标记的密度向对应原型偏移
        for archetype_idx, markers in enumerate(sentiment_markers):
            # 计算该类标记的总出现密度
            density = sum(text.count(m) for m in markers) / text_len
            # 按密度向原型向量偏移（密度越大，偏移越强）
            proto = _PROTOTYPE_VECTORS[archetype_idx]
            weight = density * 50.0  # 放大系数：让文本级标记产生显著偏移
            for i in range(dim):
                vec[i] += weight * proto[i]
        
        # 3. L2 归一化
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 1e-8:
            vec = [x / norm for x in vec]
        
        return vec

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
            'inner_child': self._inner_child.get_stats(),
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
