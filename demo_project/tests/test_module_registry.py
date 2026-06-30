"""
test_module_registry.py — 模块注册表测试 v2.21.0
===================================================
测试覆盖：
- register_all_modules: 全局注册
- 模块注册表完整性
- 门禁统计
- 推测解码在完整注册表上的表现
"""

import pytest

from tengod.tbce_unit import TBCECoordinates
from tengod.object_space import (
    ObjectSpaceManager,
    reset_object_space,
    get_object_space,
)
from tengod.module_registry import (
    TENGOD_MODULES,
    register_all_modules,
    print_registry_summary,
    demo_speculative_decoding,
)


class TestModuleRegistry:
    """模块注册表测试"""

    @pytest.fixture(autouse=True)
    def reset_global_state(self):
        """每个测试前后重置全局状态"""
        reset_object_space()
        yield
        reset_object_space()

    def test_register_all_modules(self):
        """注册所有模块"""
        results = register_all_modules()
        assert len(results) > 0
        assert len(results) == len(TENGOD_MODULES)

    def test_module_count(self):
        """模块数量 >= 92"""
        assert len(TENGOD_MODULES) >= 92

    def test_all_modules_have_required_fields(self):
        """所有模块都有必需字段"""
        required = ["name", "module_path", "lines_of_code", "dependency_count",
                     "is_core_module", "has_tests", "test_coverage", "psi_operator"]
        for mod in TENGOD_MODULES:
            for field in required:
                assert field in mod, f"Module {mod.get('name')} missing {field}"

    def test_register_and_verify(self):
        """注册后可以验证"""
        space = get_object_space()
        results = register_all_modules(space)

        # 至少有一些模块通过门禁
        open_count = sum(1 for v in results.values() if v == "open")
        assert open_count > 0

    def test_register_without_judge(self):
        """不裁决的注册"""
        space = get_object_space()
        results = register_all_modules(space, auto_judge=False)
        assert len(results) == len(TENGOD_MODULES)

    def test_sniff_on_full_registry(self):
        """全量注册表上的推测解码"""
        space = get_object_space()
        register_all_modules(space)

        target = TBCECoordinates(S=0.9, T=0.8, P=0.7, C=0.6, I=0.5, E=0.3)
        result = space.sniff(target, top_k=5)

        assert len(result.verified_results) > 0
        assert result.speedup_ratio >= 1.0

    def test_nearest_neighbors_on_full_registry(self):
        """全量注册表上的最近邻"""
        space = get_object_space()
        register_all_modules(space)

        # 找到第一个注册的单元
        first_unit = space.list_all()[0]
        nn = space.nearest_neighbors(first_unit.unit_id, k=3)

        assert len(nn) > 0
        # 最近邻不包含自己
        assert all(n[0].unit_id != first_unit.unit_id for n in nn)

    def test_layer_distribution(self):
        """认知层分布"""
        space = get_object_space()
        register_all_modules(space)

        dist = space.get_layer_distribution()
        assert dist, "认知层分布不应为空"
        # 至少有一个层
        assert len(dist) >= 1

    def test_coordinate_distribution(self):
        """坐标分布"""
        space = get_object_space()
        register_all_modules(space)

        dist = space.get_coordinate_distribution()
        assert 'S' in dist
        assert 'T' in dist
        assert all(0 <= dist[d]['mean'] <= 1 for d in ['S', 'P', 'C', 'I', 'E'])

    def test_gate_distribution(self):
        """门禁状态分布"""
        space = get_object_space()
        register_all_modules(space)

        stats = space.get_ontology_stats()
        # 部分模块可能被本体论裁决拒绝（门禁关），所以实际注册数量可能小于总数
        assert stats['total_units'] <= len(TENGOD_MODULES)
        # 裁决总数（含被拒的）= 开+徘徊+关
        judged_total = (stats['gate_stats']['open'] + stats['gate_stats']['pending'] + stats['gate_stats']['closed'])
        assert judged_total == len(TENGOD_MODULES), f"Expected {len(TENGOD_MODULES)} judged, got {judged_total}"

    def test_serialize_full_registry(self):
        """全量注册表的序列化"""
        space = get_object_space()
        register_all_modules(space)

        d = space.to_dict()
        assert d['version'] == '2.21.0'
        # 部分模块可能被本体论裁决拒绝
        assert len(d['units']) <= len(TENGOD_MODULES)
        assert 'ontology_stats' in d
        assert 'coordinate_distribution' in d
        assert 'layer_distribution' in d

    def test_demo_speculative_decoding(self):
        """演示推测解码（不抛异常）"""
        register_all_modules()
        # 演示不应抛异常
        try:
            demo_speculative_decoding()
        except Exception as e:
            pytest.fail(f"demo_speculative_decoding raised: {e}")

    def test_print_registry_summary(self):
        """打印注册表摘要（不抛异常）"""
        register_all_modules()
        try:
            print_registry_summary()
        except Exception as e:
            pytest.fail(f"print_registry_summary raised: {e}")

    def test_palace_distribution(self):
        """门禁宫分布"""
        space = get_object_space()
        register_all_modules(space)

        # 获取所有分配了门禁宫的单元
        palace_units = []
        for unit in space.list_all():
            if unit.palace_id is not None:
                palace_units.append(unit)

        # 至少有一些单元分配了门禁宫
        assert len(palace_units) > 0

    def test_consensus_layer_distribution(self):
        """共识网络层分布"""
        space = get_object_space()
        register_all_modules(space)

        consensus_units = []
        for unit in space.list_all():
            if unit.consensus_layer is not None:
                consensus_units.append(unit)

        # 至少有一些单元在共识网络中
        assert len(consensus_units) > 0

    def test_tense_distribution(self):
        """时态分布"""
        space = get_object_space()
        register_all_modules(space)

        past = space.list_by_tense("past")
        present = space.list_by_tense("present")
        future = space.list_by_tense("future")

        # 大部分应该是在present态
        assert len(present) > 0

    def test_psi_operator_distribution(self):
        """Ψ算子分布"""
        space = get_object_space()
        register_all_modules(space)

        psi_operators = set()
        for unit in space.list_all():
            psi_operators.add(unit.psi_operator)

        # 至少有两种不同的Ψ算子
        assert len(psi_operators) >= 2

    def test_core_modules(self):
        """核心模块标记"""
        core_count = sum(1 for m in TENGOD_MODULES if m.get('is_core_module'))
        assert core_count == len(TENGOD_MODULES)  # 所有模块都是核心模块