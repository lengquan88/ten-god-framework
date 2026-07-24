"""
test_tbce_unit.py — TBCE认知元组单元测试 v2.21.0
==================================================
测试覆盖：
- TBCECoordinates: 创建/转换/距离/梯度范数
- CognitiveUnit: 创建/序列化/更新坐标/距离计算
- GateState: 三态判断/阈值
- AutoCoordinateGenerator: 自动坐标生成
"""

import math
import pytest
import time

from tengod.tbce_unit import (
    TBCECoordinates,
    CognitiveUnit,
    GateState,
    AutoCoordinateGenerator,
)


# ============================================================================
# TBCECoordinates 测试
# ============================================================================

class TestTBCECoordinates:
    """TBCE六维坐标测试"""

    def test_create(self):
        """创建坐标"""
        c = TBCECoordinates(0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
        assert c.S == 0.5
        assert c.T == 0.6
        assert c.P == 0.7
        assert c.C == 0.8
        assert c.I == 0.9
        assert c.E == 1.0

    def test_to_list(self):
        """坐标转列表"""
        c = TBCECoordinates(0.1, 0.2, 0.3, 0.4, 0.5, 0.6)
        lst = c.to_list()
        assert lst == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        assert len(lst) == 6

    def test_to_dict(self):
        """坐标转字典"""
        c = TBCECoordinates(0.1, 0.2, 0.3, 0.4, 0.5, 0.6)
        d = c.to_dict()
        assert d == {'S': 0.1, 'T': 0.2, 'P': 0.3, 'C': 0.4, 'I': 0.5, 'E': 0.6}

    def test_from_list(self):
        """从列表创建坐标"""
        c = TBCECoordinates.from_list([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
        assert c.S == 0.1
        assert c.T == 0.2

    def test_from_list_invalid_length(self):
        """列表长度不对应抛出异常"""
        with pytest.raises(AssertionError):
            TBCECoordinates.from_list([0.1, 0.2, 0.3])

    def test_zero(self):
        """零坐标"""
        c = TBCECoordinates.zero()
        assert c.S == 0.0
        assert c.T == 0.0
        assert c.P == 0.0
        assert c.C == 0.0
        assert c.I == 0.0
        assert c.E == 0.0

    def test_default(self):
        """默认坐标"""
        c = TBCECoordinates.default()
        assert c.S == 0.5
        assert c.T == 0.5
        assert c.P == 0.5
        assert c.C == 0.5
        assert c.I == 0.5
        assert c.E == 0.5

    def test_distance_same_point(self):
        """同一点距离为0"""
        c1 = TBCECoordinates(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
        c2 = TBCECoordinates(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
        assert c1.distance(c2) == 0.0

    def test_distance_single_dim_diff(self):
        """单维度差异的距离"""
        c1 = TBCECoordinates(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        c2 = TBCECoordinates(1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        # S维度权重2.0，距离 = sqrt(2.0 * 1.0^2) = sqrt(2) ≈ 1.414
        d = c1.distance(c2)
        assert abs(d - math.sqrt(2.0)) < 1e-6

    def test_distance_all_dims(self):
        """所有维度差异的距离"""
        c1 = TBCECoordinates.zero()
        c2 = TBCECoordinates(1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
        # ds² = 2*1^2 + 2*1^2 + 1.5*1^2 + 1.5*1^2 + 1*1^2 + 1*1^2 = 9
        d = c1.distance(c2)
        assert abs(d - 3.0) < 1e-6

    def test_distance_custom_metric(self):
        """自定义度量张量"""
        c1 = TBCECoordinates(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        c2 = TBCECoordinates(1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        custom_metric = [
            [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        ]
        d = c1.distance(c2, custom_metric)
        assert abs(d - 1.0) < 1e-6

    def test_distance_negative_handled(self):
        """距离平方为负时返回0"""
        c1 = TBCECoordinates(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        c2 = TBCECoordinates(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        d = c1.distance(c2)
        assert d == 0.0

    def test_gradient_norm(self):
        """梯度范数"""
        coord = TBCECoordinates(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
        grad = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        norm = coord.gradient_norm(grad)
        # 默认度量张量 S=2.0, norm = sqrt(2.0 * 1^2) = sqrt(2)
        assert abs(norm - math.sqrt(2.0)) < 1e-6

    def test_gradient_norm_zero(self):
        """零梯度范数"""
        coord = TBCECoordinates.default()
        grad = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        norm = coord.gradient_norm(grad)
        assert norm == 0.0

    def test_edge_values(self):
        """边界值坐标"""
        c = TBCECoordinates(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert c.S == 0.0
        c = TBCECoordinates(1.0, 1.0, 1.0, 1.0, 1.0, 1.0)
        assert c.S == 1.0

    def test_large_time_value(self):
        """大时间值（T可以为∞）"""
        c = TBCECoordinates(0.5, 100.0, 0.5, 0.5, 0.5, 0.5)
        assert c.T == 100.0


# ============================================================================
# GateState 测试
# ============================================================================

class TestGateState:
    """门禁三态测试"""

    def test_open_above_threshold(self):
        """高于阈值 → 开"""
        assert GateState.from_threshold(0.8, 0.6, 0.3) == GateState.OPEN

    def test_pending_between_thresholds(self):
        """介于阈值之间 → 徘徊"""
        assert GateState.from_threshold(0.5, 0.6, 0.3) == GateState.PENDING

    def test_closed_below_threshold(self):
        """低于阈值 → 关"""
        assert GateState.from_threshold(0.2, 0.6, 0.3) == GateState.CLOSED

    def test_exact_boundary_open(self):
        """正好在开阈值 → 开"""
        assert GateState.from_threshold(0.6, 0.6, 0.3) == GateState.OPEN

    def test_exact_boundary_pending(self):
        """正好在徘徊阈值 → 徘徊"""
        assert GateState.from_threshold(0.3, 0.6, 0.3) == GateState.PENDING

    def test_is_passable(self):
        """只有开可通过"""
        assert GateState.is_passable(GateState.OPEN) is True
        assert GateState.is_passable(GateState.PENDING) is False
        assert GateState.is_passable(GateState.CLOSED) is False

    def test_requires_human(self):
        """只有徘徊需要人类确认"""
        assert GateState.requires_human(GateState.OPEN) is False
        assert GateState.requires_human(GateState.PENDING) is True
        assert GateState.requires_human(GateState.CLOSED) is False


# ============================================================================
# CognitiveUnit 测试
# ============================================================================

class TestCognitiveUnit:
    """认知单元测试"""

    @pytest.fixture
    def sample_unit(self):
        """创建示例认知单元"""
        return CognitiveUnit(
            unit_id="test.unit",
            name="测试单元",
            module_path="test.module",
            coordinates=TBCECoordinates(0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
            cognitive_layer=3,
            psi_operator="PersistenceDiagram",
            palace_id=1,
            tense="present",
            description="测试用认知单元",
        )

    def test_create_minimal(self):
        """最小字段创建"""
        unit = CognitiveUnit(
            unit_id="test.min",
            name="最小单元",
            module_path="test.min",
            coordinates=TBCECoordinates.default(),
            cognitive_layer=1,
            psi_operator="EmbeddingProvider",
        )
        assert unit.unit_id == "test.min"
        assert unit.gate_state == GateState.PENDING
        assert unit.palace_id is None

    def test_create_full(self, sample_unit):
        """完整字段创建"""
        assert sample_unit.unit_id == "test.unit"
        assert sample_unit.name == "测试单元"
        assert sample_unit.cognitive_layer == 3
        assert sample_unit.psi_operator == "PersistenceDiagram"
        assert sample_unit.palace_id == 1
        assert sample_unit.tense == "present"
        assert sample_unit.description == "测试用认知单元"

    def test_update_coordinates(self, sample_unit):
        """更新坐标"""
        new_coords = TBCECoordinates(0.1, 0.2, 0.3, 0.4, 0.5, 0.6)
        sample_unit.update_coordinates(new_coords)
        assert sample_unit.coordinates.S == 0.1
        assert sample_unit.verification_count == 1

    def test_update_coordinates_increments_count(self, sample_unit):
        """更新坐标增加验证次数"""
        count = sample_unit.verification_count
        sample_unit.update_coordinates(TBCECoordinates.default())
        assert sample_unit.verification_count == count + 1

    def test_calculate_distance(self, sample_unit):
        """计算与另一个单元的距离"""
        other = CognitiveUnit(
            unit_id="other.unit",
            name="其他单元",
            module_path="other.module",
            coordinates=TBCECoordinates.zero(),
            cognitive_layer=1,
            psi_operator="EmbeddingProvider",
        )
        dist = sample_unit.calculate_distance(other)
        assert dist > 0

    def test_calculate_distance_same_coords(self):
        """相同坐标距离为0"""
        u1 = CognitiveUnit(
            unit_id="u1", name="u1", module_path="u1",
            coordinates=TBCECoordinates.default(),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        u2 = CognitiveUnit(
            unit_id="u2", name="u2", module_path="u2",
            coordinates=TBCECoordinates.default(),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        assert u1.calculate_distance(u2) == 0.0

    def test_to_dict(self, sample_unit):
        """序列化为字典"""
        d = sample_unit.to_dict()
        assert d['unit_id'] == "test.unit"
        assert d['cognitive_layer'] == 3
        assert d['coordinates']['S'] == 0.5
        assert d['palace_id'] == 1
        assert d['tense'] == "present"

    def test_from_dict(self, sample_unit):
        """从字典反序列化"""
        d = sample_unit.to_dict()
        unit = CognitiveUnit.from_dict(d)
        assert unit.unit_id == sample_unit.unit_id
        assert unit.coordinates.S == sample_unit.coordinates.S
        assert unit.cognitive_layer == sample_unit.cognitive_layer

    def test_from_dict_null_palace(self):
        """反序列化无门禁宫的单元"""
        d = {
            'unit_id': 'test.no_palace',
            'name': '无宫',
            'module_path': 'test.no_palace',
            'coordinates': {'S': 0.5, 'T': 0.5, 'P': 0.5, 'C': 0.5, 'I': 0.5, 'E': 0.5},
            'cognitive_layer': 1,
            'psi_operator': 'EmbeddingProvider',
        }
        unit = CognitiveUnit.from_dict(d)
        assert unit.palace_id is None
        assert unit.tense == "present"

    def test_metadata_storage(self):
        """元数据存储"""
        unit = CognitiveUnit(
            unit_id="test.meta", name="元数据", module_path="test.meta",
            coordinates=TBCECoordinates.default(),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
            metadata={"custom_key": "custom_value", "count": 42},
        )
        assert unit.metadata["custom_key"] == "custom_value"
        assert unit.metadata["count"] == 42

    def test_discovered_at_and_updated_at(self):
        """时间戳"""
        t0 = time.time()
        unit = CognitiveUnit(
            unit_id="test.time", name="时间", module_path="test.time",
            coordinates=TBCECoordinates.default(),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        assert unit.discovered_at >= t0 - 1
        assert unit.updated_at >= t0 - 1

    def test_confidence_default(self):
        """默认置信度"""
        unit = CognitiveUnit(
            unit_id="test.conf", name="置信", module_path="test.conf",
            coordinates=TBCECoordinates.default(),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        assert unit.confidence == 0.5

    def test_gate_state_initial(self):
        """初始门禁状态"""
        unit = CognitiveUnit(
            unit_id="test.gate", name="门禁", module_path="test.gate",
            coordinates=TBCECoordinates.default(),
            cognitive_layer=1, psi_operator="EmbeddingProvider",
        )
        assert unit.gate_state == GateState.PENDING


# ============================================================================
# AutoCoordinateGenerator 测试
# ============================================================================

class TestAutoCoordinateGenerator:
    """自动坐标生成器测试"""

    @pytest.fixture
    def generator(self):
        return AutoCoordinateGenerator(seed=42)

    def test_generate_with_tests(self, generator):
        """有测试的模块 → 高S值"""
        coords = generator.generate_from_module_info(
            module_name="test_module",
            lines_of_code=300,
            dependency_count=8,
            is_core_module=True,
            has_tests=True,
            test_coverage=0.95,
        )
        assert coords.S > 0.7  # 高覆盖率 → 高可信度
        assert coords.S <= 1.0

    def test_generate_without_tests(self, generator):
        """无测试的模块 → 低S值"""
        coords = generator.generate_from_module_info(
            module_name="test_module",
            lines_of_code=300,
            dependency_count=8,
            is_core_module=False,
            has_tests=False,
            test_coverage=0.0,
        )
        assert coords.S < 0.4  # 无测试 → 低可信度

    def test_generate_core_module(self, generator):
        """核心模块 → 高T值"""
        coords = generator.generate_from_module_info(
            module_name="core_module",
            lines_of_code=300,
            dependency_count=8,
            is_core_module=True,
            has_tests=True,
            test_coverage=0.90,
        )
        assert coords.T > 0.7  # 核心模块 → 靠近现在

    def test_generate_low_dependency(self, generator):
        """低依赖 → 高P值"""
        coords = generator.generate_from_module_info(
            module_name="simple_module",
            lines_of_code=300,
            dependency_count=3,
            is_core_module=True,
            has_tests=True,
            test_coverage=0.90,
        )
        assert coords.P > 0.75  # 低依赖 → 投影清晰

    def test_generate_coordinates_in_range(self, generator):
        """所有坐标在[0,1]范围内"""
        coords = generator.generate_from_module_info(
            module_name="test", lines_of_code=500, dependency_count=15,
            is_core_module=True, has_tests=True, test_coverage=0.85,
        )
        assert 0 <= coords.S <= 1
        assert 0 <= coords.T <= 1
        assert 0 <= coords.P <= 1
        assert 0 <= coords.C <= 1
        assert 0 <= coords.I <= 1
        assert 0 <= coords.E <= 1

    def test_generate_reproducible(self):
        """相同种子+相同参数 → 相同结果"""
        g1 = AutoCoordinateGenerator(seed=42)
        g2 = AutoCoordinateGenerator(seed=42)
        c1 = g1.generate_from_module_info(
            "test", 300, 8, True, True, 0.90)
        c2 = g2.generate_from_module_info(
            "test", 300, 8, True, True, 0.90)
        assert c1.S == c2.S
        assert c1.T == c2.T
        assert c1.P == c2.P
        assert c1.C == c2.C
        assert c1.I == c2.I
        assert c1.E == c2.E

    def test_assign_layer_evaluation(self, generator):
        """评估类 → L8"""
        layer = generator.assign_cognitive_layer(100, False, True)
        assert layer == 8

    def test_assign_layer_metacognition(self, generator):
        """元认知类 → L6"""
        layer = generator.assign_cognitive_layer(100, True, False)
        assert layer == 6

    def test_assign_layer_large(self, generator):
        """大模块 → L4"""
        layer = generator.assign_cognitive_layer(1200, False, False)
        assert layer == 4

    def test_assign_layer_medium(self, generator):
        """中等模块 → L3"""
        layer = generator.assign_cognitive_layer(600, False, False)
        assert layer == 3

    def test_assign_layer_small(self, generator):
        """小模块 → L1"""
        layer = generator.assign_cognitive_layer(100, False, False)
        assert layer == 1

    def test_evaluation_overrides_metacognition(self, generator):
        """评估优先于元认知"""
        layer = generator.assign_cognitive_layer(100, True, True)
        assert layer == 8  # 评估优先

    def test_generate_edge_no_coverage(self, generator):
        """0%覆盖率 → 高E值（边缘探索）"""
        coords = generator.generate_from_module_info(
            "new", 200, 5, False, False, 0.0,
        )
        assert coords.E > 0.5  # 新模块 → 边缘探索度高

    def test_generate_edge_high_coverage(self, generator):
        """高覆盖率 → 低E值"""
        coords = generator.generate_from_module_info(
            "stable", 500, 10, True, True, 0.98,
        )
        assert coords.E < 0.5