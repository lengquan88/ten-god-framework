#!/usr/bin/env python3
"""
tengod.docs_generator — Stage 30 · 文档与开发者体验工具

为 tengod 项目提供：
  - APIDocsGenerator          API 端点文档扫描与 Markdown/OpenAPI 生成
  - DeveloperGuideGenerator   开发者指南（Getting Started / 插件 / i18n / 部署）
  - CommunityTools            知识库/FAQ/贡献指南/发布说明
  - SystemOverviewGenerator   ASCII 架构图 / 模块索引 / 特性矩阵 / 运行报告
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ============================================================================
# 1. APIDocsGenerator
# ============================================================================


class APIDocsGenerator:
    """扫描 admin_api.py + api_server.py 的端点，生成 API 文档。"""

    # 已知的 API 端点元数据（在无法 import FastAPI 或源文件时使用）
    _KNOWN_ADMIN_ENDPOINTS: List[Dict[str, Any]] = [
        {"path": "/api/admin/records", "methods": ["GET", "POST"], "tags": ["八字记录"],
         "desc": "分页获取或创建八字记录"},
        {"path": "/api/admin/records/{record_id}", "methods": ["GET", "PATCH", "DELETE"],
         "tags": ["八字记录"], "desc": "单条八字记录的读/更新/删除"},
        {"path": "/api/admin/cases", "methods": ["GET", "POST"], "tags": ["案例管理"],
         "desc": "案例列表/创建"},
        {"path": "/api/admin/cases/{case_id}", "methods": ["PATCH", "DELETE"],
         "tags": ["案例管理"], "desc": "案例更新/删除"},
        {"path": "/api/admin/users", "methods": ["GET"], "tags": ["用户管理"],
         "desc": "用户列表"},
        {"path": "/api/admin/users/{user_id}", "methods": ["GET", "PATCH"],
         "tags": ["用户管理"], "desc": "单个用户信息"},
        {"path": "/api/admin/analysis/trajectory", "methods": ["POST"],
         "tags": ["高级分析"], "desc": "命运轨迹推演"},
        {"path": "/api/admin/analysis/batch", "methods": ["POST"],
         "tags": ["高级分析"], "desc": "批量排盘分析"},
        {"path": "/api/admin/analysis/compare", "methods": ["POST"],
         "tags": ["高级分析"], "desc": "案例对比"},
        {"path": "/api/admin/stats", "methods": ["GET"], "tags": ["系统"],
         "desc": "系统统计信息"},
        {"path": "/api/admin/health", "methods": ["GET"], "tags": ["系统"],
         "desc": "健康检查"},
        {"path": "/api/admin/config", "methods": ["GET", "POST"], "tags": ["系统"],
         "desc": "配置读取/写入"},
    ]

    _KNOWN_PUBLIC_ENDPOINTS: List[Dict[str, Any]] = [
        {"path": "/api/health", "methods": ["GET"], "tags": ["系统"],
         "desc": "HTTP 健康检查"},
        {"path": "/api/stats", "methods": ["GET"], "tags": ["系统"],
         "desc": "系统指标（含向量存储）"},
        {"path": "/api/bazi/calc", "methods": ["POST"], "tags": ["八字排盘"],
         "desc": "计算四柱、大运、流年、五行等"},
        {"path": "/api/bazi/shensha", "methods": ["POST"], "tags": ["八字排盘"],
         "desc": "神煞推算"},
        {"path": "/api/bazi/geju", "methods": ["POST"], "tags": ["八字排盘"],
         "desc": "格局判断"},
        {"path": "/api/bazi/yongshen", "methods": ["POST"], "tags": ["八字排盘"],
         "desc": "喜用神分析"},
        {"path": "/api/bazi/tiaohou", "methods": ["POST"], "tags": ["八字排盘"],
         "desc": "调候分析"},
        {"path": "/api/bazi/full", "methods": ["POST"], "tags": ["八字排盘"],
         "desc": "综合八字分析"},
        {"path": "/api/bazi/report", "methods": ["POST"], "tags": ["八字排盘"],
         "desc": "命理报告生成（文本/Markdown/JSON/HTML）"},
        {"path": "/api/knowledge/search", "methods": ["POST"], "tags": ["知识查询"],
         "desc": "语义搜索（向量）"},
        {"path": "/api/knowledge/recommend", "methods": ["POST"], "tags": ["知识查询"],
         "desc": "节点关联推荐"},
        {"path": "/api/knowledge/wuxing/{element}", "methods": ["GET"], "tags": ["知识查询"],
         "desc": "五行查询"},
        {"path": "/api/knowledge/bagua/{trigram}", "methods": ["GET"], "tags": ["知识查询"],
         "desc": "八卦查询"},
        {"path": "/api/records", "methods": ["GET", "POST"], "tags": ["数据持久化"],
         "desc": "八字记录（登录用户隔离）"},
    ]

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

    # ── 1.1 扫描 ───────────────────────────────────────────────

    def generate_endpoint_docs(self) -> Dict[str, Any]:
        """扫描端点，返回结构化数据。"""
        endpoints: List[Dict[str, Any]] = []

        # 简单的源码扫描：提取 @app.xxx 装饰器下的路径
        try:
            import re

            def _scan_file(path: str) -> List[str]:
                if not os.path.exists(path):
                    return []
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
                paths: List[str] = []
                for m in re.finditer(
                    r'@app\.(?:get|post|put|patch|delete)\(\s*["\']([^"\']+)["\']',
                    text, re.IGNORECASE,
                ):
                    paths.append(m.group(1))
                # 兼容 FastAPI 常见的 add_api_route 风格
                for m in re.finditer(
                    r'(?:get|post|put|patch|delete)\(\s*["\']([^"\']+)["\']',
                    text, re.IGNORECASE,
                ):
                    path = m.group(1)
                    if path.startswith("/") and path not in paths:
                        paths.append(path)
                return paths

            tengod_dir = os.path.join(self.project_root, "tengod")
            admin_file = os.path.join(tengod_dir, "admin_api.py")
            server_file = os.path.join(tengod_dir, "api_server.py")
            scanned_admin = _scan_file(admin_file)
            scanned_public = _scan_file(server_file)
        except Exception:
            scanned_admin = []
            scanned_public = []

        # 合并已知与扫描结果
        known_paths_admin = {e["path"] for e in self._KNOWN_ADMIN_ENDPOINTS}
        for p in scanned_admin:
            if p not in known_paths_admin:
                endpoints.append({
                    "path": p, "methods": ["GET"], "tags": ["admin"],
                    "source": "scanned",
                    "desc": "扫描自 admin_api.py",
                })
        endpoints.extend({**e, "source": "known"} for e in self._KNOWN_ADMIN_ENDPOINTS)

        known_paths_public = {e["path"] for e in self._KNOWN_PUBLIC_ENDPOINTS}
        for p in scanned_public:
            if p not in known_paths_public:
                endpoints.append({
                    "path": p, "methods": ["GET"], "tags": ["public"],
                    "source": "scanned",
                    "desc": "扫描自 api_server.py",
                })
        endpoints.extend({**e, "source": "known"} for e in self._KNOWN_PUBLIC_ENDPOINTS)

        by_tag: Dict[str, int] = {}
        for e in endpoints:
            for tag in e.get("tags", []):
                by_tag[tag] = by_tag.get(tag, 0) + 1

        return {
            "total": len(endpoints),
            "by_tag": by_tag,
            "endpoints": endpoints,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── 1.2 模型文档 ─────────────────────────────────────────────

    def generate_model_docs(self) -> Dict[str, Any]:
        """列出关键数据模型的简单说明。"""
        models: List[Dict[str, Any]] = [
            {
                "name": "BaziInput",
                "fields": {
                    "year": "int, 1900-2100",
                    "month": "int, 1-12",
                    "day": "int, 1-31",
                    "hour": "int, 0-23",
                    "minute": "int, 0-59",
                    "gender": "'male' | 'female'",
                    "longitude": "float",
                    "latitude": "float",
                },
                "module": "tengod.api_server / tengod.admin_api",
            },
            {
                "name": "BaziRecord",
                "fields": {
                    "id": "int (主键)",
                    "year": "int",
                    "month": "int",
                    "day": "int",
                    "hour": "int",
                    "gender": "str",
                    "user_id": "Optional[int]",
                    "label": "str",
                    "day_master": "str",
                    "pillars": "dict",
                    "analysis": "dict",
                    "created_at": "datetime",
                },
                "module": "tengod.data_store",
            },
            {
                "name": "PluginMetadata",
                "fields": {
                    "id": "str (插件唯一 ID)",
                    "name": "str",
                    "version": "str",
                    "author": "str",
                    "description": "str",
                    "entry_point": "str",
                    "hooks": "List[str]",
                    "permissions": "List[str]",
                    "dependencies": "List[str]",
                    "is_active": "bool",
                    "is_builtin": "bool",
                },
                "module": "tengod.plugins",
            },
            {
                "name": "ReportQuery",
                "fields": {
                    "bazi": "BaziInput",
                    "format": "'text' | 'markdown' | 'json' | 'html'",
                    "include_shensha": "bool",
                    "include_geju": "bool",
                    "include_yongshen": "bool",
                },
                "module": "tengod.api_server",
            },
        ]
        return {
            "total_models": len(models),
            "models": models,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── 1.3 Markdown ───────────────────────────────────────────

    def generate_markdown(self) -> str:
        """生成完整的 Markdown 形式的 API 参考。"""
        endpoints_data = self.generate_endpoint_docs()
        models_data = self.generate_model_docs()

        lines: List[str] = []
        lines.append("# Tengod API Reference")
        lines.append("")
        lines.append(f"自动生成于 {endpoints_data['generated_at']}")
        lines.append(f"共 **{endpoints_data['total']}** 个端点，")
        lines.append(f"**{models_data['total_models']}** 个核心模型。")
        lines.append("")

        lines.append("## 端点分组统计")
        lines.append("")
        for tag, count in endpoints_data["by_tag"].items():
            lines.append(f"- **{tag}**: {count}")
        lines.append("")

        lines.append("## 端点参考")
        lines.append("")
        for ep in endpoints_data["endpoints"]:
            methods = ", ".join(ep.get("methods", []))
            tags = ", ".join(ep.get("tags", []))
            lines.append(f"### `{methods} {ep['path']}`")
            lines.append("")
            lines.append(f"- 分组: {tags}")
            lines.append(f"- 说明: {ep.get('desc', '')}")
            lines.append("")

        lines.append("## 数据模型")
        lines.append("")
        for m in models_data["models"]:
            lines.append(f"### {m['name']}")
            lines.append("")
            lines.append(f"- 模块: `{m['module']}`")
            lines.append("")
            lines.append("| Field | Type |")
            lines.append("| --- | --- |")
            for field_name, field_type in m["fields"].items():
                lines.append(f"| `{field_name}` | {field_type} |")
            lines.append("")

        return "\n".join(lines)

    # ── 1.4 OpenAPI / Swagger JSON ───────────────────────────

    def generate_openapi_spec(self, title: str = "Tengod API",
                              version: str = "1.0.0") -> Dict[str, Any]:
        """生成 OpenAPI 3.0 规范的 JSON 文档。"""
        endpoints_data = self.generate_endpoint_docs()

        paths: Dict[str, Any] = {}
        for ep in endpoints_data["endpoints"]:
            item: Dict[str, Any] = {}
            for method in ep.get("methods", []):
                item[method.lower()] = {
                    "summary": ep.get("desc", ""),
                    "tags": ep.get("tags", []),
                    "responses": {
                        "200": {"description": "成功响应"},
                        "400": {"description": "参数错误"},
                        "500": {"description": "服务端异常"},
                    },
                }
            paths[ep["path"]] = item

        return {
            "openapi": "3.0.3",
            "info": {
                "title": title,
                "version": version,
                "description": "Tengod 八字命理与知识系统 REST API",
                "contact": {"name": "Tengod Team"},
                "license": {"name": "MIT"},
            },
            "servers": [
                {"url": "http://localhost:8000", "description": "本地开发服务器"},
            ],
            "paths": paths,
            "components": {
                "schemas": {
                    "BaziInput": {
                        "type": "object",
                        "properties": {
                            "year": {"type": "integer"},
                            "month": {"type": "integer"},
                            "day": {"type": "integer"},
                            "hour": {"type": "integer"},
                            "gender": {"type": "string"},
                        },
                    },
                },
            },
            "generated_at": endpoints_data["generated_at"],
        }

    # ── 1.5 README 片段 ─────────────────────────────────────

    def generate_readme_snippet(self) -> str:
        """生成一个可嵌入到项目 README 的简短使用片段。"""
        total = self.generate_endpoint_docs()["total"]
        return (
            "## 使用 API\n\n"
            "```bash\n"
            "# 快速体验\n"
            "curl -X POST http://localhost:8000/api/bazi/calc \\\n"
            "  -H 'Content-Type: application/json' \\\n"
            "  -d '{\"year\":1990,\"month\":6,\"day\":15,"
            "\"hour\":10,\"gender\":\"male\"}'\n"
            "```\n\n"
            f"共 {total} 个端点，完整 API 参考见 `docs/api-reference.md`。\n"
        )


# ============================================================================
# 2. DeveloperGuideGenerator
# ============================================================================


class DeveloperGuideGenerator:
    """为开发者生成指引：环境搭建、插件开发、国际化、部署。"""

    def generate_getting_started(self) -> str:
        return (
            "# 起步指南 (Getting Started)\n\n"
            "## 1. 克隆项目\n"
            "```bash\n"
            "git clone https://github.com/tengod/tengod.git\n"
            "cd tengod\n"
            "```\n\n"
            "## 2. 安装依赖\n"
            "```bash\n"
            "python -m venv .venv\n"
            "source .venv/bin/activate  # Windows: .venv\\Scripts\\activate\n"
            "pip install -r requirements.txt\n"
            "```\n\n"
            "## 3. 运行快速测试\n"
            "```bash\n"
            "python -m tengod.bazi_calculator\n"
            "python -m pytest tests/ -q\n"
            "```\n\n"
            "## 4. 启动 API 服务器\n"
            "```bash\n"
            "python -m tengod.api_server --host 0.0.0.0 --port 8000\n"
            "# 访问 http://localhost:8000/docs 查看 Swagger UI\n"
            "```\n\n"
            "## 5. 常见命令\n"
            "- `python -m pytest tests/ -q`  运行测试\n"
            "- `python -m tengod.api_server` 启动 API\n"
            "- `python -m tengod.admin_api` 仅测试后台管理模块\n"
        )

    def generate_plugin_tutorial(self) -> str:
        return (
            "# 插件开发指南\n\n"
            "Tengod 的插件子系统基于 `tengod.plugins` 模块，"
            "支持钩子（hooks）、权限（permissions）与隔离运行。\n\n"
            "## 1. 插件元数据 (PluginMetadata)\n"
            "- `id`: 唯一标识符（推荐反向域名，如 `com.example.reporter`）\n"
            "- `hooks`: 插件响应的钩子集合（见下方 VALID_HOOKS）\n"
            "- `permissions`: 申请的权限声明（见 VALID_PERMISSIONS）\n\n"
            "## 2. 可用 Hooks\n"
            "- `bazi:post_calc`           八字排盘完成后触发\n"
            "- `report:post_gen`          报告生成完成后触发\n"
            "- `search:post_query`        语义搜索后触发\n"
            "- `analysis:post_trajectory` 轨迹分析完成后触发\n"
            "- `ui:custom_component`      UI 组件注入点\n\n"
            "## 3. 示例：最简插件\n"
            "```python\n"
            "from tengod.plugins import PluginMetadata, create_plugin_metadata, get_plugin_manager\n\n"
            "def my_plugin_fn(payload, context):\n"
            "    input_data = payload.get('input', {})\n"
            "    return {'enhanced': True, 'summary': f'hello {input_data}'}\n\n"
            "md = create_plugin_metadata(\n"
            "    id='com.example.demo',\n"
            "    name='Demo Plugin',\n"
            "    version='1.0.0',\n"
            "    author='you',\n"
            "    description='演示插件',\n"
            "    entry_point='module_name:my_plugin_fn',\n"
            "    hooks=['report:post_gen'],\n"
            "    permissions=['read:records'],\n"
            "    runtime_fn=my_plugin_fn,\n"
            ")\n\n"
            "pm = get_plugin_manager()\n"
            "pm.register(md)\n"
            "results = pm.trigger('report:post_gen', {'report': '内容'})\n"
            "for r in results:\n"
            "    print(r)\n"
            "```\n\n"
            "## 4. 验证插件\n"
            "- `PluginRegistry.validate_metadata(md)` 校验元数据\n"
            "- `PluginSandbox` 提供进程隔离运行（entry_point 形如 `code://...`）\n"
        )

    def generate_i18n_guide(self) -> str:
        return (
            "# 国际化 (i18n) 指南\n\n"
            "Tengod 提供多语言翻译的底层 `tengod.i18n` 模块。\n\n"
            "## 支持的语言\n"
            "- `zh-CN`  简体中文\n"
            "- `zh-TW`  繁体中文\n"
            "- `en`     English\n"
            "- `ja`     日本語\n"
            "- `ko`     한국어\n\n"
            "## 使用方式\n"
            "```python\n"
            "from tengod.i18n import get_translator, t\n\n"
            "tr = get_translator('en')\n"
            "print(tr('日主'))       # Day Master\n"
            "print(t('大运', 'ja'))  # 大運\n"
            "```\n\n"
            "## 添加新语言\n"
            "1. 在 `tengod/i18n/` 下添加 `xx.json`（`xx` 为语言代码）\n"
            "2. 以 `zh-CN.json` 为基准，填充各 key 的翻译\n"
            "3. 在 `tengod.i18n.SUPPORTED_LANGUAGES` 中注册新语言\n"
            "4. 运行测试验证：`python -m pytest tests/test_phase25.py`\n"
        )

    def generate_deployment_guide(self) -> str:
        return (
            "# 生产部署指南\n\n"
            "## 1. Docker 部署\n"
            "```bash\n"
            "docker build -t tengod:latest .\n"
            "docker run -d --name tengod -p 8000:8000 \\\n"
            "  -e TENGOD_DB_URL=/data/tengod.db \\\n"
            "  -v $(pwd)/data:/data tengod:latest\n"
            "```\n\n"
            "## 2. Docker Compose (推荐)\n"
            "```yaml\n"
            "version: '3.8'\n"
            "services:\n"
            "  redis:\n"
            "    image: redis:7-alpine\n"
            "    ports: ['6379:6379']\n"
            "  postgres:\n"
            "    image: postgres:16-alpine\n"
            "    environment:\n"
            "      POSTGRES_DB: tengod\n"
            "      POSTGRES_USER: tengod\n"
            "      POSTGRES_PASSWORD: secret\n"
            "    ports: ['5432:5432']\n"
            "  tengod:\n"
            "    image: tengod:latest\n"
            "    ports: ['8000:8000']\n"
            "    environment:\n"
            "      TENGOD_REDIS_URL: redis://redis:6379/0\n"
            "      TENGOD_DB_URL: postgresql://tengod:secret@postgres:5432/tengod\n"
            "```\n\n"
            "## 3. 生产环境关键变量\n"
            "- `TENGOD_DB_URL`             主数据库地址（SQLite/Postgres）\n"
            "- `TENGOD_REDIS_URL`          缓存/限流 Redis\n"
            "- `TENGOD_API_KEY`            对外 API 鉴权密钥\n"
            "- `TENGOD_WORKERS`            Gunicorn worker 数量\n\n"
            "## 4. 健康检查\n"
            "```bash\n"
            "curl http://localhost:8000/api/health\n"
            "curl http://localhost:8000/api/health/full\n"
            "```\n\n"
            "## 5. 性能与可靠性\n"
            "使用 `tengod.reliability` 模块：\n"
            "- `RateLimiter`  限流保护\n"
            "- `CircuitBreaker` 熔断器\n"
            "- `EnhancedHealthChecker` 综合健康检查\n"
        )


# ============================================================================
# 3. CommunityTools
# ============================================================================


class CommunityTools:
    """生成面向社区的文档。"""

    def generate_knowledge_base_article(self, topic: str, content: str) -> str:
        """格式化为知识库文章。"""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return (
            f"# {topic}\n\n"
            f"> 发布时间：{now}\n\n"
            f"{content.strip()}\n\n"
            "---\n"
            f"*本文由 Tengod CommunityTools 自动排版 · topic=`{topic}`*\n"
        )

    def generate_faq_entry(self, question: str, answer: str) -> str:
        """生成一条 FAQ。"""
        return f"**Q. {question}**\n\nA. {answer}\n"

    def generate_contributing_guide(self) -> str:
        return (
            "# 贡献指南 (Contributing)\n\n"
            "## 代码风格\n"
            "- 遵循 PEP 8，建议使用 `black` / `ruff`\n"
            "- 为新模块添加类型注解（type hints）\n\n"
            "## 分支与提交\n"
            "- 基于 `main` 创建新分支，例如 `feature/new-engine`\n"
            "- 提交信息简洁描述变更内容\n\n"
            "## 测试\n"
            "```bash\n"
            "python -m pytest tests/ -q\n"
            "```\n"
            "新增功能必须包含对应测试。\n\n"
            "## Pull Request 流程\n"
            "1. Fork 本仓库\n"
            "2. 在分支上提交变更\n"
            "3. 打开 PR，描述变更动机、影响范围与验证方式\n"
            "4. 通过 CI 后由维护者 review 合并\n"
        )

    def generate_release_notes(self, version: str, changes: List[str]) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        body = "\n".join(f"- {c}" for c in changes) if changes else "- (无变更)"
        return (
            f"# Release v{version}\n\n"
            f"> 发布日期: {now}\n\n"
            "## Highlights\n"
            f"{body}\n\n"
            "## 升级说明\n"
            f"```bash\n"
            f"git pull origin main\n"
            f"pip install -r requirements.txt\n"
            f"```\n"
        )


# ============================================================================
# 4. SystemOverviewGenerator
# ============================================================================


class SystemOverviewGenerator:
    """生成架构图、模块索引、特性矩阵与运行报告。"""

    STAGES_FEATURES: Dict[str, List[str]] = {
        "Stage 21 · 高级术数引擎": ["LiunianJudgmentEngine", "XuankongEngine (风水)",
                                    "QizhengEngine (七政四余)"],
        "Stage 22 · 数据与向量存储": ["DataStore (SQLite/Postgres)",
                                     "VectorStore (FAISS / Embeddings)",
                                     "CacheManager"],
        "Stage 23 · 插件系统": ["PluginRegistry", "PluginSandbox",
                               "PluginHookManager", "Built-in plugins"],
        "Stage 24 · 小程序/客户端": ["MiniappClient", "ShareCardGenerator",
                                   "Login/Token", "Search/Timeline"],
        "Stage 25 · 国际化": ["zh-CN / zh-TW / en / ja / ko", "Translator",
                             "Bazi 报告多语言"],
        "Stage 26 · 后台管理": ["AdminService (CRUD)", "Trajectory Analysis",
                              "Batch Analysis", "Case Compare"],
        "Stage 27 · 社交与协作": ["User lifecycle", "Follow/Post/Like/Comment",
                                "Collaboration Sessions"],
        "Stage 28 · 可视化": ["Bazi viz", "SVG rendering",
                             "Ziwei / Hexagram / Qimen charts"],
        "Stage 29 · 可靠性": ["RateLimiter", "CircuitBreaker",
                            "EnhancedHealthChecker", "PerformanceBenchmark"],
        "Stage 30 · 文档/体验": ["APIDocsGenerator", "DeveloperGuideGenerator",
                              "CommunityTools", "SystemOverviewGenerator"],
    }

    def generate_architecture_diagram_text(self) -> str:
        return (
            "Tengod 架构图 (ASCII)\n"
            "============================================================\n"
            "                                                              \n"
            "  +-----------------------+      +-----------------------+   \n"
            "  |   Web 控制台 / PWA    |      |  小程序 / Mobile App  |   \n"
            "  +-----------+-----------+      +-----------+-----------+   \n"
            "              |                                |               \n"
            "              +---------------+----------------+               \n"
            "                              |                                \n"
            "                  +-----------v------------+                   \n"
            "                  |   FastAPI (api_server) |                   \n"
            "                  |   + admin_api (back)   |                   \n"
            "                  +-----------+------------+                   \n"
            "                              |                                \n"
            "           +------------------+------------------+             \n"
            "           |                  |                  |             \n"
            "  +--------v-------+ +--------v--------+ +-------v--------+    \n"
            "  |  八字/神煞/格局 | |  向量知识图谱    | |  用户与案例    |    \n"
            "  |  大运/流年/喜用 | |  语义搜索/推荐   | |  多租户隔离    |    \n"
            "  +--------+-------+ +--------+--------+ +-------+--------+    \n"
            "           |                  |                  |             \n"
            "           +------------------+------------------+             \n"
            "                              |                                \n"
            "              +---------------v---------------+                \n"
            "              |  tengod.data_store            |                \n"
            "              |  (SQLite / Postgres)          |                \n"
            "              +---------------+---------------+                \n"
            "                              |                                \n"
            "              +---------------v---------------+                \n"
            "              |  Redis 缓存 / RateLimiter     |                \n"
            "              +-------------------------------+                \n"
            "                                                              \n"
            "  插件层 (Stage 23):    [PluginRegistry <-> HookManager]       \n"
            "  可靠性 (Stage 29):    [CircuitBreaker / HealthChecker]       \n"
            "  可视化 (Stage 28):    SVG + JSON Spec                        \n"
            "                                                              \n"
            "============================================================\n"
        )

    def generate_module_index(self) -> Dict[str, Any]:
        modules = [
            {"module": "tengod.bazi_calculator", "purpose": "八字排盘（四柱、大运、流年）"},
            {"module": "tengod.bazi_analyzer", "purpose": "八字分析器（综合分析结果）"},
            {"module": "tengod.shensha_engine", "purpose": "神煞推算引擎"},
            {"module": "tengod.geju_engine", "purpose": "格局/喜用神/调候分析"},
            {"module": "tengod.dayun_liunian", "purpose": "大运/流年推导"},
            {"module": "tengod.liunian_judgment", "purpose": "流年命理判断"},
            {"module": "tengod.fengshui.xuankong", "purpose": "玄空飞星（风水）"},
            {"module": "tengod.qizheng.engine", "purpose": "七政四余"},
            {"module": "tengod.divination_engine", "purpose": "爻/地支/天干基础运算"},
            {"module": "tengod.ziwei_engine", "purpose": "紫微斗数"},
            {"module": "tengod.liuyao_engine", "purpose": "六爻摇卦"},
            {"module": "tengod.qimen_engine", "purpose": "奇门遁甲"},
            {"module": "tengod.name_engine", "purpose": "姓名学"},
            {"module": "tengod.marriage_engine", "purpose": "合婚分析"},
            {"module": "tengod.vector_store", "purpose": "向量存储/语义搜索"},
            {"module": "tengod.vector_store_pg", "purpose": "Postgres 向量存储"},
            {"module": "tengod.data_store", "purpose": "SQLite/Postgres 数据模型"},
            {"module": "tengod.knowledge_graph", "purpose": "五行/八卦/天干/地支图谱"},
            {"module": "tengod.plugins", "purpose": "插件注册/沙盒/钩子"},
            {"module": "tengod.i18n", "purpose": "多语言翻译"},
            {"module": "tengod.miniapp", "purpose": "小程序客户端与分享卡"},
            {"module": "tengod.social", "purpose": "用户/发帖/关注/协作"},
            {"module": "tengod.visualization", "purpose": "SVG/JSON 可视化"},
            {"module": "tengod.advanced_analysis", "purpose": "轨迹/批量/案例对比"},
            {"module": "tengod.admin_api", "purpose": "后台管理 REST API"},
            {"module": "tengod.api_server", "purpose": "对外 FastAPI 服务器"},
            {"module": "tengod.reliability", "purpose": "限流/熔断/健康/性能基准"},
            {"module": "tengod.metrics_collector", "purpose": "运行指标采集"},
            {"module": "tengod.auth", "purpose": "JWT / 角色鉴权"},
            {"module": "tengod.llm_adapter", "purpose": "大模型对话/报告生成"},
            {"module": "tengod.report_generator", "purpose": "命理报告生成器"},
            {"module": "tengod.docs_generator", "purpose": "（本模块）自动化文档工具"},
        ]
        return {
            "total_modules": len(modules),
            "modules": modules,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def generate_feature_matrix(self) -> str:
        lines: List[str] = []
        lines.append("# Tengod 特性矩阵（Stages 21-30）")
        lines.append("")
        lines.append("| 阶段 | 特性 |")
        lines.append("| --- | --- |")
        for stage, features in self.STAGES_FEATURES.items():
            for i, f in enumerate(features):
                stage_display = stage if i == 0 else ""
                lines.append(f"| {stage_display} | {f} |")
        return "\n".join(lines)

    # ── 运行报告 ───────────────────────────────────────────

    def generate_running_report(self) -> Dict[str, Any]:
        """生成运行时摘要（尽力读取数据库状态，不依赖外部服务）。"""
        total_users = 0
        total_records = 0
        total_cases = 0
        db_status = "unknown"

        try:
            from tengod.data_store import DataStore
            store = DataStore()
            stats = getattr(store, "stats", lambda: {})()
            if isinstance(stats, dict):
                total_users = int(stats.get("total_users") or 0)
                total_records = int(stats.get("total_records") or 0)
                total_cases = int(stats.get("total_cases") or 0)
                db_status = "ok"
        except Exception:
            db_status = "unavailable"

        try:
            from tengod.metrics_collector import metrics as _m
            snap = getattr(_m, "get_snapshot", lambda: {})()
        except Exception:
            snap = {}

        return {
            "status": "running",
            "db": db_status,
            "users": total_users,
            "records": total_records,
            "cases": total_cases,
            "metrics": snap if isinstance(snap, dict) else {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ============================================================================
# 5. Helper functions
# ============================================================================


def ensure_markdown_dir(directory: Optional[str] = None) -> str:
    """创建 docs 目录并返回绝对路径。"""
    if directory is None:
        directory = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs",
        )
    directory = os.path.abspath(directory)
    os.makedirs(directory, exist_ok=True)
    return directory


def save_markdown(filename: str, content: str,
                  directory: Optional[str] = None) -> str:
    """将内容写入 docs 目录下的文件；返回最终路径。"""
    directory = ensure_markdown_dir(directory)
    if not filename.lower().endswith((".md", ".markdown")):
        filename = filename + ".md"
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


# ============================================================================
# 6. DocsManager singleton
# ============================================================================


@dataclass
class DocsManager:
    """聚合所有生成器的简单门面。"""

    api: APIDocsGenerator = field(default_factory=APIDocsGenerator)
    guide: DeveloperGuideGenerator = field(default_factory=DeveloperGuideGenerator)
    community: CommunityTools = field(default_factory=CommunityTools)
    overview: SystemOverviewGenerator = field(default_factory=SystemOverviewGenerator)

    def generate_all(self, out_dir: Optional[str] = None) -> Dict[str, str]:
        """批量生成所有文档并写入磁盘，返回 {filename: path}。"""
        out_dir = ensure_markdown_dir(out_dir)
        artifacts = {
            "api-reference.md": self.api.generate_markdown(),
            "getting-started.md": self.guide.generate_getting_started(),
            "plugin-tutorial.md": self.guide.generate_plugin_tutorial(),
            "i18n-guide.md": self.guide.generate_i18n_guide(),
            "deployment-guide.md": self.guide.generate_deployment_guide(),
            "contributing.md": self.community.generate_contributing_guide(),
            "release-notes.md": self.community.generate_release_notes(
                "1.0.0", ["项目初始化", "Stages 21-30 上线"]
            ),
            "architecture.md": self.overview.generate_architecture_diagram_text(),
            "feature-matrix.md": self.overview.generate_feature_matrix(),
            "modules.md": json.dumps(self.overview.generate_module_index(),
                                     indent=2, ensure_ascii=False, default=str),
            "running-report.json": json.dumps(self.overview.generate_running_report(),
                                              indent=2, ensure_ascii=False, default=str),
            "openapi.json": json.dumps(self.api.generate_openapi_spec(),
                                       indent=2, ensure_ascii=False, default=str),
            "README-snippet.md": self.api.generate_readme_snippet(),
        }
        written: Dict[str, str] = {}
        for name, content in artifacts.items():
            if name.endswith(".json"):
                path = os.path.join(out_dir, name)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(content if isinstance(content, str) else json.dumps(content))
            else:
                path = save_markdown(name, content, directory=out_dir)
            written[name] = path
        return written


_DOCS_MANAGER: Optional[DocsManager] = None
_DOCS_LOCK = threading.Lock()


def get_docs_manager() -> DocsManager:
    """线程安全的单例访问器。"""
    global _DOCS_MANAGER
    if _DOCS_MANAGER is None:
        with _DOCS_LOCK:
            if _DOCS_MANAGER is None:
                _DOCS_MANAGER = DocsManager()
    return _DOCS_MANAGER


# ============================================================================
# 7. Self-test
# ============================================================================


def _self_test() -> Dict[str, Any]:
    results: Dict[str, Any] = {}

    mgr = get_docs_manager()

    # APIDocsGenerator
    ep = mgr.api.generate_endpoint_docs()
    models = mgr.api.generate_model_docs()
    md = mgr.api.generate_markdown()
    openapi = mgr.api.generate_openapi_spec()
    snippet = mgr.api.generate_readme_snippet()
    results["api_endpoints"] = ep["total"]
    results["api_models"] = models["total_models"]
    results["api_markdown_len"] = len(md)
    results["api_openapi_paths"] = len(openapi.get("paths", {}))
    results["api_snippet_len"] = len(snippet)

    # DeveloperGuideGenerator
    results["guide_getting_started"] = len(mgr.guide.generate_getting_started())
    results["guide_plugin_tutorial"] = len(mgr.guide.generate_plugin_tutorial())
    results["guide_i18n_guide"] = len(mgr.guide.generate_i18n_guide())
    results["guide_deployment_guide"] = len(mgr.guide.generate_deployment_guide())

    # CommunityTools
    article = mgr.community.generate_knowledge_base_article("测试主题", "测试内容")
    faq = mgr.community.generate_faq_entry("这是问题吗？", "是的。")
    contrib = mgr.community.generate_contributing_guide()
    release = mgr.community.generate_release_notes("1.0.0", ["init"])
    results["community_article"] = len(article)
    results["community_faq"] = len(faq)
    results["community_contrib"] = len(contrib)
    results["community_release"] = len(release)

    # SystemOverviewGenerator
    arch = mgr.overview.generate_architecture_diagram_text()
    idx = mgr.overview.generate_module_index()
    fm = mgr.overview.generate_feature_matrix()
    rr = mgr.overview.generate_running_report()
    results["overview_arch"] = len(arch)
    results["overview_modules"] = idx["total_modules"]
    results["overview_feature_matrix"] = len(fm)
    results["overview_running_report_status"] = rr["status"]

    # helpers
    out_dir = ensure_markdown_dir()
    written = save_markdown("test-artifact.md", "# Test\n\nbody\n", directory=out_dir)
    results["helper_write_path"] = written
    results["helper_write_ok"] = os.path.exists(written)

    # write everything
    all_paths = mgr.generate_all(out_dir=out_dir)
    results["all_generated_files"] = list(all_paths.keys())
    results["all_generated_count"] = len(all_paths)

    return results


if __name__ == "__main__":
    import pprint
    pprint.pprint(_self_test())


__all__ = [
    "APIDocsGenerator",
    "DeveloperGuideGenerator",
    "CommunityTools",
    "SystemOverviewGenerator",
    "DocsManager",
    "ensure_markdown_dir",
    "save_markdown",
    "get_docs_manager",
]
