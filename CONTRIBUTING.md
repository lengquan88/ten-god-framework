# 贡献指南

感谢您对Claw项目的关注！我们欢迎所有形式的贡献，包括但不限于：

- 🐛 报告和修复bug
- ✨ 提出新功能
- 📖 改进文档
- 🧪 编写测试
- 💡 提供想法和建议
- 🌍 帮助翻译和本地化

## 📋 贡献流程

### 1. 准备工作

#### 环境设置

```bash
# Fork 仓库到您的GitHub账号
# 克隆您的Fork
git clone https://github.com/your-username/claw.git
cd claw

# 添加上游仓库
git remote add upstream https://github.com/original-org/claw.git

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 安装pre-commit钩子
pre-commit install
```

#### 代码规范

我们遵循以下代码规范：

- **PEP 8**: Python代码风格
- **Black**: 代码格式化
- **isort**: import排序
- **flake8**: 代码检查
- **pylint**: 高级代码检查
- **mypy**: 类型检查

配置文件已包含在项目中，请确保您的编辑器使用这些配置。

### 2. 创建分支

```bash
# 同步最新代码
git fetch upstream
git checkout main
git merge upstream/main

# 创建功能分支
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
# 或
git checkout -b docs/your-doc-update
```

**分支命名规范**：

- `feature/`: 新功能
- `fix/`: bug修复
- `docs/`: 文档更新
- `refactor/`: 代码重构
- `test/`: 测试相关
- `chore/`: 构建和工具

### 3. 进行开发

#### 开发原则

1. **保持简洁**: 每个PR只解决一个问题
2. **保持小规模**: 尽量保持PR小而专注
3. **保持一致**: 遵循现有的代码风格
4. **添加测试**: 新代码必须包含测试
5. **更新文档**: 如果有API变更，请更新文档

#### 代码质量

```bash
# 格式化代码
black src/ tests/

# 排序imports
isort src/ tests/

# 代码检查
flake8 src/ tests/

# 类型检查
mypy src/

# 运行测试
pytest

# 运行所有检查
pre-commit run --all-files
```

#### 提交规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type类型**：

- `feat`: 新功能
- `fix`: bug修复
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行的变动）
- `refactor`: 重构（既不是新增功能，也不是修改bug的代码变动）
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动
- `ci`: CI配置文件和脚本的变动

**示例**：

```
feat(agents): 添加研究助手智能体

实现了基于LangChain的研究助手智能体，支持：
- 文献检索
- 知识抽取
- 综述生成

Closes #123
```

### 4. 测试

#### 编写测试

```python
import pytest
from claw.agents.specialized import CodingAgent

def test_coding_agent_initialization():
    """测试编程助手智能体初始化"""
    agent = CodingAgent(name="coder", model="gpt-4")
    assert agent.name == "coder"
    assert agent.model == "gpt-4"

def test_coding_agent_run():
    """测试编程助手智能体执行"""
    agent = CodingAgent(name="coder", model="gpt-4")
    result = agent.run("编写一个快速排序算法")
    assert result is not None
    assert "快速排序" in result or "quicksort" in result.lower()
```

#### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/unit/test_agents/test_coding_agent.py

# 运行特定测试函数
pytest tests/unit/test_agents/test_coding_agent.py::test_coding_agent_initialization

# 生成覆盖率报告
pytest --cov=src --cov-report=html

# 并行运行测试
pytest -n auto
```

#### 测试要求

- 新功能必须有对应的单元测试
- 测试覆盖率不应降低
- 所有测试必须通过
- 集成测试验证功能完整性

### 5. 提交更改

```bash
# 查看更改
git status

# 添加更改的文件
git add path/to/changed/files

# 提交更改
git commit -m "feat(agents): 添加研究助手智能体"

# 推送到远程仓库
git push origin feature/your-feature-name
```

### 6. 创建Pull Request

#### PR模板

在创建PR时，请使用以下模板：

```markdown
## 📝 变更描述

简要描述这个PR做了什么以及为什么这么做。

## 🎯 变更类型

- [ ] Bug修复
- [ ] 新功能
- [ ] 代码重构
- [ ] 文档更新
- [ ] 性能优化
- [ ] 其他

## ✅ 检查清单

- [ ] 代码遵循项目的代码规范
- [ ] 添加了相应的测试
- [ ] 所有测试通过
- [ ] 更新了相关文档
- [ ] 提交信息清晰规范
- [ ] 没有引入新的警告或错误

## 🔗 相关Issue

Closes #(issue number)

## 📸 截图或演示

如果适用，添加截图或演示链接。

## 🧪 测试

描述如何测试这些更改：

```bash
# 测试命令
pytest tests/unit/test_agents/test_research_agent.py
```

## 💬 其他说明

任何其他需要审查者注意的事项。
```

#### PR审查流程

1. **自动检查**: CI/CD会自动运行所有测试
2. **人工审查**: 维护者会审查代码
3. **修改建议**: 可能需要根据反馈进行修改
4. **合并**: 审查通过后，代码会被合并到主分支

## 📚 文档贡献

### 文档类型

- **用户文档**: 面向终端用户的使用指南
- **开发者文档**: 面向开发者的技术文档
- **API文档**: 代码接口说明
- **教程**: 逐步教程和示例
- **FAQ**: 常见问题解答

### 文档格式

- 使用Markdown格式
- 包含代码示例
- 添加图表和截图（如需要）
- 保持简洁清晰

### 文档位置

```
docs/
├── user/              # 用户文档
├── developer/         # 开发者文档
├── api/               # API文档
└── tutorials/         # 教程
```

## 🐛 Bug报告

### 报告模板

在报告bug时，请使用以下模板：

```markdown
## 🐛 Bug描述

简要描述bug的情况。

## 📋 复现步骤

1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## 🎯 期望行为

清晰简洁地描述您期望发生什么。

## 📸 实际行为

清晰简洁地描述实际发生了什么。

## 🖼️ 截图

如果适用，添加截图以帮助解释问题。

## 💻 环境

- OS: [e.g. Windows 10, macOS 11.5]
- Python版本: [e.g. 3.10]
- Claw版本: [e.g. 1.0.0]

## 📄 日志

如果适用，添加相关的日志输出。

## 📝 补充信息

添加任何其他关于问题的信息。
```

## ✨ 功能请求

### 请求模板

```markdown
## 🎯 功能描述

简要描述您希望添加的功能。

## 🎨 功能描述

详细描述这个功能如何工作，用户界面如何，等等。

## 💡 使用场景

描述这个功能的使用场景和好处。

## 🔄 替代方案

描述您考虑过的替代解决方案。

## 📚 参考资料

添加任何链接、截图或其他参考资料。
```

## 🌍 国际化

### 支持语言

- 中文（简体）
- 英文
- 更多语言欢迎贡献

### 如何贡献翻译

1. 找到需要翻译的文档
2. 在 `docs/i18n/<lang>/` 下创建对应文件
3. 翻译文档内容
4. 提交PR

## 📋 代码审查标准

### 审查要点

1. **代码质量**: 代码是否清晰、可读、易维护
2. **测试覆盖**: 是否有足够的测试
3. **性能影响**: 是否会影响性能
4. **安全性**: 是否有安全隐患
5. **文档完整性**: 是否更新了相关文档

### 审查反馈

- 提供建设性的反馈
- 解释为什么需要修改
- 给出具体的修改建议
- 保持礼貌和专业

## 🏆 贡献者

我们非常感谢所有的贡献者！查看 [CONTRIBUTORS.md](CONTRIBUTORS.md) 了解完整的贡献者列表。

## 📞 获取帮助

如果您在贡献过程中遇到任何问题：

1. 查看 [文档](docs/)
2. 搜索 [Issues](https://github.com/your-org/claw/issues)
3. 创建新的Issue提问
4. 加入我们的 [社区](https://github.com/your-org/claw/discussions)

## 📜 行为准则

我们承诺为每个人提供欢迎和友好的环境。请阅读我们的完整行为准则 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## 🙏 感谢

再次感谢您的贡献！每一个贡献都让Claw变得更好。

---

**Happy Coding! 🚀**
