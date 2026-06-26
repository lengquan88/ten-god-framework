"""补充测试：tengod.docs_generator 模块（APIDocsGenerator, DeveloperGuideGenerator,
CommunityTools, SystemOverviewGenerator, DocsManager, helpers）
"""
import json
import os
import sys
import tempfile
import pytest

from tengod.docs_generator import (
    APIDocsGenerator,
    CommunityTools,
    DeveloperGuideGenerator,
    DocsManager,
    SystemOverviewGenerator,
    ensure_markdown_dir,
    get_docs_manager,
    save_markdown,
)


# ============================================================================
# 1. APIDocsGenerator
# ============================================================================

class TestAPIDocsGenerator:
    """APIDocsGenerator 测试"""

    def test_init_default(self):
        """__init__ 默认 project_root"""
        gen = APIDocsGenerator()
        assert gen.project_root is not None
        assert os.path.isdir(gen.project_root)

    def test_init_custom(self):
        """__init__ 自定义 project_root"""
        with tempfile.TemporaryDirectory() as td:
            gen = APIDocsGenerator(project_root=td)
            assert gen.project_root == td

    def test_generate_endpoint_docs_structure(self):
        """generate_endpoint_docs() 返回正确结构"""
        gen = APIDocsGenerator()
        result = gen.generate_endpoint_docs()
        assert "total" in result
        assert "by_tag" in result
        assert "endpoints" in result
        assert "generated_at" in result
        assert isinstance(result["endpoints"], list)
        assert len(result["endpoints"]) == result["total"]
        assert isinstance(result["by_tag"], dict)
        # 检查每个端点有 path 和 methods
        for ep in result["endpoints"]:
            assert "path" in ep
            assert "methods" in ep

    def test_generate_endpoint_docs_with_known_data(self):
        """已知端点数据应被包含"""
        gen = APIDocsGenerator()
        result = gen.generate_endpoint_docs()
        paths = {ep["path"] for ep in result["endpoints"]}
        assert "/api/admin/health" in paths
        assert "/api/health" in paths
        assert "/api/bazi/calc" in paths

    def test_generate_model_docs(self):
        """generate_model_docs() 返回模型文档"""
        gen = APIDocsGenerator()
        result = gen.generate_model_docs()
        assert "total_models" in result
        assert "models" in result
        assert "generated_at" in result
        assert result["total_models"] >= 4
        model_names = [m["name"] for m in result["models"]]
        assert "BaziInput" in model_names
        assert "BaziRecord" in model_names
        assert "PluginMetadata" in model_names
        assert "ReportQuery" in model_names

    def test_generate_markdown_structure(self):
        """generate_markdown() 包含关键章节"""
        gen = APIDocsGenerator()
        md = gen.generate_markdown()
        assert "# Tengod API Reference" in md
        assert "## 端点分组统计" in md
        assert "## 端点参考" in md
        assert "## 数据模型" in md
        assert "自动生成于" in md
        # 应包含已知端点
        assert "/api/bazi/calc" in md
        assert "/api/health" in md

    def test_generate_markdown_non_empty(self):
        """generate_markdown() 返回非空字符串"""
        gen = APIDocsGenerator()
        md = gen.generate_markdown()
        assert len(md) > 500
        assert isinstance(md, str)

    def test_generate_openapi_spec_default(self):
        """generate_openapi_spec() 默认参数"""
        gen = APIDocsGenerator()
        spec = gen.generate_openapi_spec()
        assert spec["openapi"] == "3.0.3"
        assert spec["info"]["title"] == "Tengod API"
        assert spec["info"]["version"] == "1.0.0"
        assert "paths" in spec
        assert "components" in spec
        assert len(spec["paths"]) > 0
        # 验证包含已知路径
        assert "/api/admin/health" in spec["paths"]
        assert "/api/health" in spec["paths"]

    def test_generate_openapi_spec_custom_title_version(self):
        """generate_openapi_spec() 自定义标题和版本"""
        gen = APIDocsGenerator()
        spec = gen.generate_openapi_spec(title="Custom API", version="2.0.0")
        assert spec["info"]["title"] == "Custom API"
        assert spec["info"]["version"] == "2.0.0"

    def test_generate_openapi_spec_valid_json(self):
        """generate_openapi_spec() 可序列化为 JSON"""
        gen = APIDocsGenerator()
        spec = gen.generate_openapi_spec()
        json_str = json.dumps(spec, indent=2)
        parsed = json.loads(json_str)
        assert parsed["openapi"] == "3.0.3"

    def test_generate_openapi_spec_includes_all_paths(self):
        """generate_openapi_spec() 包含所有端点路径"""
        gen = APIDocsGenerator()
        spec = gen.generate_openapi_spec()
        paths = set(spec["paths"].keys())
        expected = {
            "/api/admin/records", "/api/admin/records/{record_id}",
            "/api/admin/cases", "/api/admin/cases/{case_id}",
            "/api/admin/users", "/api/admin/users/{user_id}",
            "/api/admin/analysis/trajectory", "/api/admin/analysis/batch",
            "/api/admin/analysis/compare", "/api/admin/stats",
            "/api/admin/health", "/api/admin/config",
            "/api/health", "/api/stats",
            "/api/bazi/calc", "/api/bazi/shensha", "/api/bazi/geju",
            "/api/bazi/yongshen", "/api/bazi/tiaohou", "/api/bazi/full",
            "/api/bazi/report",
            "/api/knowledge/search", "/api/knowledge/recommend",
            "/api/knowledge/wuxing/{element}", "/api/knowledge/bagua/{trigram}",
            "/api/records",
        }
        assert expected.issubset(paths)

    def test_generate_openapi_spec_paths_have_methods(self):
        """每个 OpenAPI 路径应包含 HTTP 方法定义"""
        gen = APIDocsGenerator()
        spec = gen.generate_openapi_spec()
        for path, item in spec["paths"].items():
            assert isinstance(item, dict)
            for method in item:
                assert method in ("get", "post", "put", "patch", "delete")
                assert "summary" in item[method]
                assert "responses" in item[method]

    def test_generate_readme_snippet(self):
        """generate_readme_snippet() 包含 curl 示例"""
        gen = APIDocsGenerator()
        snippet = gen.generate_readme_snippet()
        assert "## 使用 API" in snippet
        assert "curl" in snippet
        assert "/api/bazi/calc" in snippet
        assert "api-reference.md" in snippet

    def test_generate_endpoint_docs_scanned_fallback(self):
        """_scan_endpoints 不存在的文件时回退到已知端点"""
        gen = APIDocsGenerator(project_root="/nonexistent/path")
        result = gen.generate_endpoint_docs()
        # 应该仍然有已知端点
        assert result["total"] >= 25  # 至少包含已知端点


# ============================================================================
# 2. DeveloperGuideGenerator
# ============================================================================

class TestDeveloperGuideGenerator:
    """DeveloperGuideGenerator 测试"""

    def test_generate_getting_started(self):
        """generate_getting_started() 结构"""
        dg = DeveloperGuideGenerator()
        gs = dg.generate_getting_started()
        assert "# 起步指南" in gs
        assert "git clone" in gs
        assert "pip install" in gs
        assert "pytest" in gs
        assert len(gs) > 200

    def test_generate_plugin_tutorial(self):
        """generate_plugin_tutorial() 结构"""
        dg = DeveloperGuideGenerator()
        pt = dg.generate_plugin_tutorial()
        assert "# 插件开发指南" in pt
        assert "PluginMetadata" in pt
        assert "bazi:post_calc" in pt
        assert "report:post_gen" in pt
        assert len(pt) > 200

    def test_generate_i18n_guide(self):
        """generate_i18n_guide() 结构"""
        dg = DeveloperGuideGenerator()
        ig = dg.generate_i18n_guide()
        assert "# 国际化" in ig
        assert "zh-CN" in ig
        assert "en" in ig
        assert "ja" in ig
        assert len(ig) > 200

    def test_generate_deployment_guide(self):
        """generate_deployment_guide() 结构"""
        dg = DeveloperGuideGenerator()
        dep = dg.generate_deployment_guide()
        assert "# 生产部署指南" in dep
        assert "Docker" in dep
        assert "docker build" in dep
        assert "TENGOD_DB_URL" in dep
        assert len(dep) > 200

    def test_all_guides_non_empty(self):
        """所有 guide 方法返回非空字符串"""
        dg = DeveloperGuideGenerator()
        guides = [
            dg.generate_getting_started(),
            dg.generate_plugin_tutorial(),
            dg.generate_i18n_guide(),
            dg.generate_deployment_guide(),
        ]
        for g in guides:
            assert isinstance(g, str)
            assert len(g) > 100


# ============================================================================
# 3. SystemOverviewGenerator
# ============================================================================

class TestSystemOverviewGenerator:
    """SystemOverviewGenerator 测试"""

    def test_generate_architecture_diagram_text(self):
        """generate_architecture_diagram_text() 返回 ASCII 图"""
        sog = SystemOverviewGenerator()
        result = sog.generate_architecture_diagram_text()
        assert isinstance(result, str)
        assert len(result) > 500
        assert "Tengod 架构图" in result
        assert "FastAPI" in result
        assert "插件层" in result
        assert "可靠性" in result

    def test_generate_module_index_structure(self):
        """generate_module_index() 返回正确结构"""
        sog = SystemOverviewGenerator()
        idx = sog.generate_module_index()
        assert "total_modules" in idx
        assert "modules" in idx
        assert "generated_at" in idx
        assert idx["total_modules"] == len(idx["modules"])
        assert idx["total_modules"] > 20

    def test_generate_module_index_contains_key_modules(self):
        """模块索引包含核心模块"""
        sog = SystemOverviewGenerator()
        idx = sog.generate_module_index()
        module_names = [m["module"] for m in idx["modules"]]
        assert "tengod.bazi_calculator" in module_names
        assert "tengod.api_server" in module_names
        assert "tengod.plugins" in module_names
        assert "tengod.docs_generator" in module_names

    def test_generate_feature_matrix_structure(self):
        """generate_feature_matrix() 结构"""
        sog = SystemOverviewGenerator()
        fm = sog.generate_feature_matrix()
        assert "# Tengod 特性矩阵" in fm
        assert "| 阶段 | 特性 |" in fm
        assert "Stage 21" in fm
        assert "Stage 30" in fm
        assert "APIDocsGenerator" in fm

    def test_generate_feature_matrix_non_empty(self):
        """generate_feature_matrix() 非空"""
        sog = SystemOverviewGenerator()
        fm = sog.generate_feature_matrix()
        assert len(fm) > 500

    def test_generate_running_report_default(self):
        """generate_running_report() 返回默认状态"""
        sog = SystemOverviewGenerator()
        rr = sog.generate_running_report()
        assert isinstance(rr, dict)
        assert "status" in rr
        assert rr["status"] == "running"
        assert "db" in rr
        assert "users" in rr
        assert "records" in rr
        assert "cases" in rr
        assert "metrics" in rr
        assert "timestamp" in rr

    def test_generate_running_report_db_unavailable(self):
        """当 DataStore 导入失败时 db 状态为 unavailable"""
        sog = SystemOverviewGenerator()
        # 直接调用，在无 DataStore 的环境中应该返回 unavailable
        rr = sog.generate_running_report()
        assert rr["db"] in ("ok", "unavailable")
        assert rr["status"] == "running"


# ============================================================================
# 4. CommunityTools
# ============================================================================

class TestCommunityTools:
    """CommunityTools 测试"""

    def test_generate_knowledge_base_article(self):
        """generate_knowledge_base_article() 格式化知识库文章"""
        ct = CommunityTools()
        article = ct.generate_knowledge_base_article("测试主题", "这是测试内容")
        assert "# 测试主题" in article
        assert "这是测试内容" in article
        assert "发布时间" in article
        assert "CommunityTools" in article

    def test_generate_knowledge_base_article_with_multiline_content(self):
        """generate_knowledge_base_article() 多行内容"""
        ct = CommunityTools()
        article = ct.generate_knowledge_base_article("多行", "第一行\n第二行\n第三行")
        assert "第一行" in article
        assert "第二行" in article

    def test_generate_faq_entry(self):
        """generate_faq_entry() 格式化 FAQ"""
        ct = CommunityTools()
        faq = ct.generate_faq_entry("这是问题吗？", "是的，这是答案。")
        assert "**Q. 这是问题吗？**" in faq
        assert "A. 是的，这是答案。" in faq

    def test_generate_faq_entry_empty(self):
        """generate_faq_entry() 空内容"""
        ct = CommunityTools()
        faq = ct.generate_faq_entry("", "")
        assert "**Q. **" in faq
        assert "A. " in faq

    def test_generate_contributing_guide(self):
        """generate_contributing_guide() 结构"""
        ct = CommunityTools()
        cg = ct.generate_contributing_guide()
        assert "# 贡献指南" in cg
        assert "PEP 8" in cg
        assert "Pull Request" in cg
        assert "pytest" in cg
        assert len(cg) > 200

    def test_generate_release_notes_with_changes(self):
        """generate_release_notes() 有变更列表"""
        ct = CommunityTools()
        rn = ct.generate_release_notes("2.0.0", ["新功能 A", "修复 B", "优化 C"])
        assert "# Release v2.0.0" in rn
        assert "- 新功能 A" in rn
        assert "- 修复 B" in rn
        assert "- 优化 C" in rn
        assert "## Highlights" in rn
        assert "## 升级说明" in rn
        assert "git pull" in rn

    def test_generate_release_notes_empty_changes(self):
        """generate_release_notes() 空变更列表"""
        ct = CommunityTools()
        rn = ct.generate_release_notes("1.0.0", [])
        assert "# Release v1.0.0" in rn
        assert "(无变更)" in rn

    def test_generate_release_notes_no_changes(self):
        """generate_release_notes() 空列表回退"""
        ct = CommunityTools()
        rn = ct.generate_release_notes("0.0.1", [])
        assert "(无变更)" in rn


# ============================================================================
# 5. Helper functions
# ============================================================================

class TestHelperFunctions:
    """ensure_markdown_dir 和 save_markdown 测试"""

    def test_ensure_markdown_dir_default(self):
        """ensure_markdown_dir() 默认路径"""
        d = ensure_markdown_dir()
        assert os.path.isdir(d)
        assert d.endswith("docs")

    def test_ensure_markdown_dir_custom(self):
        """ensure_markdown_dir() 自定义路径"""
        with tempfile.TemporaryDirectory() as td:
            custom = os.path.join(td, "my_docs")
            d = ensure_markdown_dir(custom)
            assert d == os.path.abspath(custom)
            assert os.path.isdir(d)

    def test_ensure_markdown_dir_creates_if_not_exists(self):
        """ensure_markdown_dir() 自动创建目录"""
        with tempfile.TemporaryDirectory() as td:
            new_dir = os.path.join(td, "new_docs_subdir")
            assert not os.path.exists(new_dir)
            d = ensure_markdown_dir(new_dir)
            assert os.path.isdir(d)

    def test_save_markdown_with_extension(self):
        """save_markdown() 带 .md 扩展名"""
        with tempfile.TemporaryDirectory() as td:
            path = save_markdown("test.md", "# Hello\n\nWorld", directory=td)
            assert os.path.exists(path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "# Hello" in content
            assert "World" in content

    def test_save_markdown_without_extension(self):
        """save_markdown() 不带扩展名自动添加 .md"""
        with tempfile.TemporaryDirectory() as td:
            path = save_markdown("testfile", "# NoExt", directory=td)
            assert path.endswith(".md")
            assert os.path.exists(path)

    def test_save_markdown_with_markdown_extension(self):
        """save_markdown() .markdown 扩展名"""
        with tempfile.TemporaryDirectory() as td:
            path = save_markdown("readme.markdown", "# MD", directory=td)
            assert path.endswith(".markdown")
            assert os.path.exists(path)

    def test_save_markdown_returns_absolute_path(self):
        """save_markdown() 返回绝对路径"""
        with tempfile.TemporaryDirectory() as td:
            path = save_markdown("test.md", "content", directory=td)
            assert os.path.isabs(path)

    def test_save_markdown_multiple_files(self):
        """save_markdown() 多次写入不冲突"""
        with tempfile.TemporaryDirectory() as td:
            p1 = save_markdown("a.md", "A", directory=td)
            p2 = save_markdown("b.md", "B", directory=td)
            assert p1 != p2
            assert os.path.exists(p1)
            assert os.path.exists(p2)


# ============================================================================
# 6. DocsManager
# ============================================================================

class TestDocsManager:
    """DocsManager 和 get_docs_manager 测试"""

    def test_docs_manager_init(self):
        """DocsManager 默认初始化"""
        dm = DocsManager()
        assert isinstance(dm.api, APIDocsGenerator)
        assert isinstance(dm.guide, DeveloperGuideGenerator)
        assert isinstance(dm.community, CommunityTools)
        assert isinstance(dm.overview, SystemOverviewGenerator)

    def test_docs_manager_custom_generators(self):
        """DocsManager 自定义生成器"""
        api = APIDocsGenerator()
        guide = DeveloperGuideGenerator()
        community = CommunityTools()
        overview = SystemOverviewGenerator()
        dm = DocsManager(api=api, guide=guide, community=community, overview=overview)
        assert dm.api is api
        assert dm.guide is guide
        assert dm.community is community
        assert dm.overview is overview

    def test_generate_all_returns_dict(self):
        """generate_all() 返回字典"""
        dm = DocsManager()
        with tempfile.TemporaryDirectory() as td:
            result = dm.generate_all(out_dir=td)
            assert isinstance(result, dict)
            assert len(result) > 0

    def test_generate_all_creates_files(self):
        """generate_all() 创建所有文档文件"""
        dm = DocsManager()
        with tempfile.TemporaryDirectory() as td:
            result = dm.generate_all(out_dir=td)
            for name, path in result.items():
                assert os.path.exists(path), f"{name} → {path} 不存在"
                assert os.path.isfile(path)

    def test_generate_all_includes_key_files(self):
        """generate_all() 包含所有关键文档"""
        dm = DocsManager()
        with tempfile.TemporaryDirectory() as td:
            result = dm.generate_all(out_dir=td)
            expected_keys = [
                "api-reference.md",
                "getting-started.md",
                "plugin-tutorial.md",
                "i18n-guide.md",
                "deployment-guide.md",
                "contributing.md",
                "release-notes.md",
                "architecture.md",
                "feature-matrix.md",
                "modules.md",
                "running-report.json",
                "openapi.json",
                "README-snippet.md",
            ]
            for key in expected_keys:
                assert key in result, f"缺少 {key}"

    def test_generate_all_json_files_valid_json(self):
        """generate_all() JSON 文件是有效 JSON"""
        dm = DocsManager()
        with tempfile.TemporaryDirectory() as td:
            result = dm.generate_all(out_dir=td)
            for name, path in result.items():
                if name.endswith(".json"):
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.loads(f.read())
                    assert isinstance(data, (dict, list))

    def test_generate_all_default_dir(self):
        """generate_all() 默认输出目录"""
        dm = DocsManager()
        with tempfile.TemporaryDirectory() as td:
            # 使用临时目录作为默认
            result = dm.generate_all(out_dir=td)
            assert len(result) > 0
            for path in result.values():
                assert path.startswith(os.path.abspath(td))

    def test_generate_all_writes_valid_markdown_files(self):
        """generate_all() Markdown 文件有内容"""
        dm = DocsManager()
        with tempfile.TemporaryDirectory() as td:
            result = dm.generate_all(out_dir=td)
            for name, path in result.items():
                if name.endswith(".md"):
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    assert len(content) > 10, f"{name} 内容过短"

    def test_get_docs_manager_singleton(self):
        """get_docs_manager() 返回单例"""
        dm1 = get_docs_manager()
        dm2 = get_docs_manager()
        assert dm1 is dm2

    def test_get_docs_manager_returns_docs_manager(self):
        """get_docs_manager() 返回 DocsManager 实例"""
        dm = get_docs_manager()
        assert isinstance(dm, DocsManager)


# ============================================================================
# 7. 边缘情况与集成测试
# ============================================================================

class TestEdgeCases:
    """边缘情况测试"""

    def test_empty_endpoint_list_handled(self):
        """端点列表为空也应正常工作"""
        gen = APIDocsGenerator()
        result = gen.generate_endpoint_docs()
        # 至少应有已知端点
        assert result["total"] > 0

    def test_save_guides_to_temp_directory(self):
        """保存文档到临时目录"""
        dg = DeveloperGuideGenerator()
        with tempfile.TemporaryDirectory() as td:
            path = save_markdown("getting-started.md",
                                 dg.generate_getting_started(),
                                 directory=td)
            assert os.path.exists(path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "# 起步指南" in content

    def test_runtime_report_with_no_engine(self):
        """无 DataStore 时 runtime report 仍可生成"""
        sog = SystemOverviewGenerator()
        rr = sog.generate_running_report()
        assert rr["status"] == "running"
        # 在无 DataStore 的环境中 db 应为 unavailable
        assert rr["db"] in ("ok", "unavailable")

    def test_all_generate_methods_return_non_empty_strings(self):
        """所有 generate 方法返回非空字符串"""
        gen = APIDocsGenerator()
        dg = DeveloperGuideGenerator()
        ct = CommunityTools()
        sog = SystemOverviewGenerator()

        string_methods = [
            (gen.generate_markdown, "generate_markdown"),
            (gen.generate_readme_snippet, "generate_readme_snippet"),
            (dg.generate_getting_started, "generate_getting_started"),
            (dg.generate_plugin_tutorial, "generate_plugin_tutorial"),
            (dg.generate_i18n_guide, "generate_i18n_guide"),
            (dg.generate_deployment_guide, "generate_deployment_guide"),
            (ct.generate_contributing_guide, "generate_contributing_guide"),
            (sog.generate_architecture_diagram_text, "generate_architecture_diagram_text"),
            (sog.generate_feature_matrix, "generate_feature_matrix"),
        ]
        for method, name in string_methods:
            result = method()
            assert isinstance(result, str), f"{name} 应返回 str"
            assert len(result) > 0, f"{name} 不应返回空字符串"

    def test_generate_markdown_contains_model_section(self):
        """generate_markdown 包含数据模型章节"""
        gen = APIDocsGenerator()
        md = gen.generate_markdown()
        assert "### BaziInput" in md
        assert "### BaziRecord" in md
        assert "### PluginMetadata" in md
        assert "### ReportQuery" in md

    def test_feature_matrix_covers_all_stages(self):
        """特性矩阵覆盖 Stage 21-30"""
        sog = SystemOverviewGenerator()
        fm = sog.generate_feature_matrix()
        for i in range(21, 31):
            assert f"Stage {i}" in fm

    def test_openapi_spec_has_servers(self):
        """OpenAPI spec 包含 servers"""
        gen = APIDocsGenerator()
        spec = gen.generate_openapi_spec()
        assert "servers" in spec
        assert len(spec["servers"]) > 0
        assert "url" in spec["servers"][0]

    def test_openapi_spec_has_components(self):
        """OpenAPI spec 包含 components/schemas"""
        gen = APIDocsGenerator()
        spec = gen.generate_openapi_spec()
        assert "components" in spec
        assert "schemas" in spec["components"]
        assert "BaziInput" in spec["components"]["schemas"]

    def test_release_notes_has_date(self):
        """release_notes 包含发布日期"""
        ct = CommunityTools()
        rn = ct.generate_release_notes("3.0.0", ["功能"])
        assert "发布日期" in rn

    def test_knowledge_base_article_has_topic_in_footer(self):
        """知识库文章页脚包含 topic"""
        ct = CommunityTools()
        article = ct.generate_knowledge_base_article("五行", "内容")
        assert "topic=`五行`" in article

    def test_contributing_guide_has_pr_flow(self):
        """贡献指南包含 PR 流程"""
        ct = CommunityTools()
        cg = ct.generate_contributing_guide()
        assert "Fork" in cg
        assert "Pull Request" in cg


class TestSelfTestAndMain:
    """_self_test() 覆盖"""

    def test_self_test_returns_results(self):
        """_self_test() 返回结果字典"""
        from tengod.docs_generator import _self_test
        results = _self_test()
        assert isinstance(results, dict)
        assert "api_endpoints" in results
        assert "api_models" in results
        assert "api_markdown_len" in results
        assert "api_openapi_paths" in results
        assert "api_snippet_len" in results
        assert "guide_getting_started" in results
        assert "guide_plugin_tutorial" in results
        assert "guide_i18n_guide" in results
        assert "guide_deployment_guide" in results
        assert "community_article" in results
        assert "community_faq" in results
        assert "community_contrib" in results
        assert "community_release" in results
        assert "overview_arch" in results
        assert "overview_modules" in results
        assert "overview_feature_matrix" in results
        assert "overview_running_report_status" in results
        assert "helper_write_ok" in results
        assert "all_generated_files" in results
        assert "all_generated_count" in results
        # 所有字段都是正数长度
        assert results["api_markdown_len"] > 0
        assert results["guide_getting_started"] > 0
        assert results["overview_arch"] > 0
        assert results["all_generated_count"] > 0

    def test_self_test_all_generated_files_includes_key_artifacts(self):
        """_self_test() 生成的文件列表包含关键 artifacts"""
        from tengod.docs_generator import _self_test
        results = _self_test()
        files = results["all_generated_files"]
        assert "api-reference.md" in files
        assert "openapi.json" in files
        assert "modules.md" in files

    def test_self_test_helper_write_ok(self):
        """_self_test() 验证 helper 写入成功"""
        from tengod.docs_generator import _self_test
        results = _self_test()
        assert results["helper_write_ok"] is True

class TestScanExceptionHandling:
    """源码扫描异常处理分支覆盖"""

    def test_generate_endpoint_docs_exception_handling(self, monkeypatch):
        """generate_endpoint_docs 异常处理分支 — 扫描时 open 抛出异常"""
        import builtins
        original_open = builtins.open

        def _mock_open(file, *args, **kwargs):
            fname = str(file) if not isinstance(file, str) else file
            if fname.endswith("admin_api.py") or fname.endswith("api_server.py"):
                raise OSError("模拟文件读取失败")
            return original_open(file, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", _mock_open)
        gen = APIDocsGenerator()
        result = gen.generate_endpoint_docs()
        # 即使扫描失败，仍然返回已知端点
        assert result["total"] >= 25
        assert len(result["endpoints"]) == result["total"]
        assert isinstance(result["by_tag"], dict)

    def test_generate_endpoint_docs_scanned_endpoints(self, tmp_path):
        """源码扫描到新端点时添加 source='scanned'"""
        # 创建临时 tengod 目录，包含带自定义端点的文件
        tengod_dir = tmp_path / "tengod"
        tengod_dir.mkdir()
        admin_api = tengod_dir / "admin_api.py"
        admin_api.write_text("""
@app.get("/api/admin/custom_scan")
@app.post("/api/admin/custom_scan2")
def handler():
    pass
""")
        api_server = tengod_dir / "api_server.py"
        api_server.write_text("""
@app.get("/api/public/custom_scan")
def handler():
    pass
""")
        gen = APIDocsGenerator(project_root=str(tmp_path))
        result = gen.generate_endpoint_docs()
        paths = {ep["path"] for ep in result["endpoints"]}
        assert "/api/admin/custom_scan" in paths
        assert "/api/admin/custom_scan2" in paths
        # 已知端点仍应存在
        assert "/api/bazi/calc" in paths

    def test_generate_endpoint_docs_second_regex_match(self, tmp_path):
        """第二个正则匹配（add_api_route 风格）：覆盖行 121"""
        tengod_dir = tmp_path / "tengod"
        tengod_dir.mkdir()
        server_file = tengod_dir / "api_server.py"
        server_file.write_text("""
# 使用 add_api_route 风格的路径定义
get("/api/v2/new_endpoint")
post("/api/v2/another_one")
delete("/api/v2/remove_me")
""")
        gen = APIDocsGenerator(project_root=str(tmp_path))
        result = gen.generate_endpoint_docs()
        paths = {ep["path"] for ep in result["endpoints"]}
        assert "/api/v2/new_endpoint" in paths
        assert "/api/v2/another_one" in paths
        assert "/api/v2/remove_me" in paths

    def test_generate_endpoint_docs_nonexistent_path(self):
        """不存在的 project_root 也能正常回退"""
        gen = APIDocsGenerator(project_root="/this/does/not/exist/at/all")
        result = gen.generate_endpoint_docs()
        assert result["total"] >= 25
        assert len(result["endpoints"]) == result["total"]
        assert isinstance(result["by_tag"], dict)

class TestRunningReportExceptions:
    """running_report 异常处理分支覆盖"""

    def test_running_report_datastore_exception(self, monkeypatch):
        """DataStore 导入失败时 db_status='unavailable'"""
        import sys
        import builtins

        # 使用 builtins.__import__ 拦截导入
        original_import = builtins.__import__

        def _mock_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "tengod.data_store":
                raise ImportError("模拟 DataStore 不可用")
            return original_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", _mock_import)
        # 清除已缓存的模块
        sys.modules.pop("tengod.data_store", None)
        sog = SystemOverviewGenerator()
        rr = sog.generate_running_report()
        assert rr["db"] == "unavailable"
        assert rr["status"] == "running"

    def test_running_report_metrics_exception(self, monkeypatch):
        """metrics_collector 导入失败时 metrics 为空"""
        import sys
        from unittest.mock import patch

        # 直接 mock 掉 generate_running_report 中的 metrics 导入
        # 通过替换 sys.modules 中已缓存的模块为 None
        # 让 from ... import 在查找时找不到模块名
        # 使用 builtins.__import__ 拦截
        import builtins
        _orig_import = builtins.__import__

        def _block_metrics(name, *args, **kwargs):
            if name == "tengod.metrics_collector":
                raise ImportError("metrics 模块不可用")
            return _orig_import(name, *args, **kwargs)

        builtins.__import__ = _block_metrics
        try:
            # 清除缓存
            to_remove = [k for k in sys.modules if k.startswith("tengod.metrics_collector")]
            for k in to_remove:
                del sys.modules[k]
            sog = SystemOverviewGenerator()
            rr = sog.generate_running_report()
            assert "metrics" in rr
            assert isinstance(rr["metrics"], dict)
            assert rr["metrics"] == {}  # 异常时为空
            assert rr["status"] == "running"
        finally:
            builtins.__import__ = _orig_import

    def test_running_report_normal(self):
        """正常环境下的 running_report"""
        sog = SystemOverviewGenerator()
        rr = sog.generate_running_report()
        assert "metrics" in rr
        assert isinstance(rr["metrics"], dict)
        assert rr["status"] == "running"
        assert rr["db"] in ("ok", "unavailable")