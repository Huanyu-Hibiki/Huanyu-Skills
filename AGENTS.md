# Project Agent Guidelines (Antigravity)

本文件是当前项目的核心治理文件。Google Antigravity 在当前工作区执行任务时会自动加载本文件及相关规则，以保证代码编写与协作的高质量、高一致性。

---

## 1. 核心工程哲学 (ETHOS)

1. **完整性很便宜 (Boil the Lake)**
   - AI 时代完整实现的边际成本趋近于零。当完整实现只比捷径多几分钟时，每一次都做完整的事。
   - 测试是最便宜的湖，绝不拖延到后续 PR。
   - 完整性优先不是添加未请求的功能，而是完整实现用户目标、完整验证结果、完整清理本次修改的副作用。

2. **先搜索再构建 (Search Before Building)**
   - 在编写涉及不熟悉模式、基础设施或运行时已有内置方案的代码之前，先搜索是否已有现成工具、库或规范。
   - 避免从零重复造轮子。

3. **用户说了算 (User Sovereignty)**
   - AI 提供方案建议与分析，用户做最终决策。这是覆盖一切规则的最高规则。
   - 当你有强烈推荐但与用户显性偏好冲突时：展示推荐、解释理由、说明盲区，然后尊重并执行用户的选择，绝不擅自越权。

---

## 2. 核心开发工作流

收到任何开发任务时，遵循标准工程生命周期推进：

```
用户需求
   ↓
brainstorming → 设计探索 → 澄清问题 → 方案对比 → 设计文档 (docs/designs/) → 用户批准
   ↓
AI 复杂度评估（边界 / 技术栈 / 改动范围 / 隐藏假设 / 确定性）
   ↓                                       ↓
全部简单                                 任一复杂
   ↓                                       ↓
writing-plans                          grill-me → 需求校准与压力测试
   ↓                                       ↓
   ↓ ←—————————————————————————————————————┘
   ↓
writing-plans → 任务拆解 (tracer-bullet 垂直切片) → 计划文档 (docs/plans/) → 用户确认
   ↓
execute-plans → 逐个任务执行:
  1. TDD: 先写失败测试 (红灯)
  2. 实现: 最小正确代码让测试通过 (绿灯)
  3. 审查: spec-compliance 审查 → code-quality 审查
   ↓
finishing-a-branch → 最终验证 (verification-before-completion) → 提交规范 → 交付分支
```

### 三条推进路径
- **超大工程**（单会话无法承载、方案迷雾重）：使用 `wayfinder` 绘制决策地图（GitHub Issues 承载），逐票解决，路径清晰后进入常规流程。
- **复杂任务**（跨模块、技术不熟悉、包含隐藏假设）：`brainstorming` → `grill-me` (压力测试) → `writing-plans` → `execute-plans` → `finishing-a-branch`。
- **简单任务**（需求单一、技术确定）：`brainstorming` → `writing-plans` → `execute-plans` → `finishing-a-branch`。

---

## 3. 强制纪律守则

### 代码编写前：
- **禁止直接动笔**：新功能、组件或行为变更前必须完成设计探索并获批。
- **显式识别假设**：不确定时先提问，不静默选择实现路径。
- **搜索先行**：涉及未熟悉依赖或运行时能力时，必须检索现有生态。

### 代码编写中：
- **TDD 红绿循环**：严格先写失败测试，再写最小实现使其转绿。80%+ 测试覆盖率是底线。
- **手术式修改 (Karpathy 准则)**：每一行代码变动都能追溯到用户需求。严禁随手重构、格式化或清理无关死代码。
- **禁止破坏配置**：禁止通过放宽 linter/formatter 或滥用 `any` / `@ts-ignore` 掩盖问题。

### 代码编写后：
- **证据先于声明**：声称完成前，必须实际运行测试或验证命令并核验输出 (`verification-before-completion`)。
- **双阶段审查**：严格执行 Spec 合规审查与代码质量审查。
- **安全红线**：禁止硬编码 API Key、密码与敏感 Token；边界输入强制校验；SQL 强制参数化。

---

## 4. 智能体角色与委派体系 (Agent Roles)

在 Antigravity 中，你可以根据任务需要利用 `invoke_subagent` 或 Slash Commands 派发专注的子智能体：

| 角色 (Role) | 职责定位 | 权限建议 | 触发场景 |
| :--- | :--- | :--- | :--- |
| **`architect`** | 架构与方案设计，深入权衡利弊 | 只读分析 | 复杂架构设计、重构方案探索、技术选型 |
| **`planner`** | 将设计文档拆解为 tracer-bullet 垂直切片实施任务 | 只读分析业务代码，可写计划 | 编写实施计划 (`writing-plans`) |
| **`implementer`** | 专注执行单个切片任务，遵循 TDD 红绿循环 | 完整读写与执行 | 任务执行 (`execute-plans`) |
| **`reviewer`** | 综合代码审查（质量、安全、可维护性） | 只读分析 | PR 评审、功能提交后审查 |
| **`spec-reviewer`** | 对照设计文档检查实现是否完整忠实 | 只读分析 | execute-plans 第一阶段审查 |
| **`quality-reviewer`** | 六维代码质量深度审查 (正确/安全/维护/性能/测试/规范) | 只读分析 | execute-plans 第二阶段审查 |
| **`quality-auditor`** | 运行 lint/build/test 工具并生成 0-100 加权评分报告 | 读 + 命令执行 | 质量审计 (`code-quality-audit`) |
| **`debugger`** | 系统化四阶段根因排查（铁律：不找到根因不修复） | 完整读写与执行 | 排查异常、修复 Bug (`systematic-debugging`) |
| **`security-auditor`** | OWASP 级安全审计与漏洞排查 | 读写分析与修复 | 涉及认证、支付、API、用户输入模块 |
| **`git-governance-reviewer`** | Git 仓库治理、分支流与 Commit 规范核验 | 只读 Git 命令 | 提交、切分支、发布与 Hotfix 审查 |

---

## 5. 项目技能库索引 (`.agents/skills/`)

本项目已配备完备的 Antigravity 渐进式技能库，主要类别包括：
- **流程编排**：`brainstorming`, `grill-me`, `writing-plans`, `execute-plans`, `finishing-a-branch`, `wayfinder`
- **工程纪律**：`tdd-workflow`, `verification-before-completion`, `search-first`, `karpathy-guidelines`
- **审查与审计**：`code-review`, `code-quality-audit`, `security-review`, `db-review`, `python-review`
- **修复与调试**：`systematic-debugging`, `build-fix`, `python-build`, `refactor-clean`
- **Git 治理**：`git-check`, `branch-guide`, `commit-guide`, `release-check`, `hotfix-check`, `github-repo-governance`
- **架构模式**：`backend-patterns`, `frontend-patterns`, `postgres-patterns`, `api-design`, `docker-patterns`, `mcp-builder`

---

## 6. 模块化规则索引 (`.agents/rules/`)

更多细分维度的编码与安全规范请参阅：
- `karpathy.md`：抑制 LLM 常见失误的极简主义编码准则
- `common.md`：通用代码风格、小文件组织与错误处理契约
- `workflow.md`：端到端工作流与状态推进规则
- `security.md`：密钥管理、能力层防线与安全防护
- `architecture.md`：系统分层、依赖方向与接口契约
