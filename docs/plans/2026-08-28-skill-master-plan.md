# skill-master 合集 实施计划

## 总览

按设计文档的依赖序（manager → security → analyzer → writer → optimizer）全量交付 skill-master 合集。策略：**共享层先行**（agents.yaml / skill-anatomy / security-taxonomy 三个知识底座），**脚本走 TDD**（fixtures 先行，pytest 全覆盖），**SKILL.md 最后写**（每个子 skill 在其依赖的脚本和 references 就绪后编写，根路由器收尾）。所有 Python 脚本仅依赖标准库，运行环境 Windows + PowerShell 5.1 + Python 3.13.5 + uv 0.8.3。

## 前置准备

- [x] 设计文档已批准（2026-08-28 头脑风暴定稿）
- [ ] 开发环境复核：`uv --version` 确认 0.8.3 可用、`python --version` 确认 3.13.5
- [ ] 确认 `C:\work\HuanyuCode\skill-master\` 为实施根目录（当前仅有 docs/）
- [ ] 任务 1 建立 pytest 空基线

## 任务列表

### 任务 1: 项目骨架 + pytest 基线 (~3 min)
- **描述**： 创建完整目录树 + `pyproject.toml`（uv 管理，`[dependency-groups] dev = ["pytest"]`）+ 空 conftest，确认空跑通过
- **文件**：
  - 创建 `pyproject.toml`、`tests/conftest.py`、`.gitignore`
  - 创建目录：`scripts/`、`skills/{sm-manager,sm-security,sm-analyzer,sm-writer,sm-optimizer}/`、`shared-references/`、`templates/`、`references/{writing,optimizing,security}/`、`tests/fixtures/`
- **测试**： 无（基线建立）
- **验证**： `uv run pytest` 退出码 0（0 项收集）
- **依赖**： 无

### 任务 2: agents.yaml 注册表 (~4 min)
- **描述**： 内置 opencode / claude-code / codex / trae / gemini 等已知默认全局 skill 目录模式（Windows 优先写法，支持 `~` 与 `%USERPROFILE%` 展开）。每项 = `name + paths[] + enabled`，文件头注释说明用户可增删。实施时用 `ls` 探测本机真实目录校准默认值
- **文件**： 创建 `shared-references/agents.yaml`
- **测试**： 无（数据文件，解析行为由任务 6 测试覆盖）
- **验证**： 条目覆盖 ≥5 个 Agent；每个 Agent ≥1 个候选路径
- **依赖**： 任务 1

### 任务 3: skill-anatomy.md 知识底座 (~5 min)
- **描述**： skill 结构/原理知识，供 ③④⑤ 共享：目录结构规范、frontmatter 字段（name/description/allowed-tools）、description ≤1024 字符约束、渐进式披露、SKILL.md ≤200 行 + 下沉 references/ 规则、触发词写法
- **文件**： 创建 `shared-references/skill-anatomy.md`
- **测试**： 无
- **验证**： 覆盖健康检查（任务 7）所用全部判据；sm-writer/sm-optimizer 可直接引用
- **依赖**： 任务 1

### 任务 4: security-taxonomy.md 风险分类学 (~5 min)
- **描述**： 5 类风险（提示注入/数据外泄/破坏命令/混淆隐藏/过度权限）+ 规则 id 命名段（INJ/EXFIL/DEST/OBF/Perm）+ severity 四级定义（critical/high/medium/low）+ 每条规则必带误报说明的字段规范；附 SkillSpector 17 类思想映射表（只吸收思想）
- **文件**： 创建 `shared-references/security-taxonomy.md`
- **测试**： 无
- **验证**： 类别与设计文档一致；任务 10 的规则表按此文档逐条生成
- **依赖**： 任务 1

### 任务 5: fixtures — 假 Agent 目录树 (~4 min)
- **描述**： 造 `fake-opencode/`（2 个健康 skill）、`fake-claude/`（1 健康 + 1 缺 SKILL.md + 1 frontmatter 残缺 + 1 desc>1024 字符）、跨 Agent 重名 skill（duplicates 样本）；附 `fixtures/README.md` 说明预期结果
- **文件**： 创建 `tests/fixtures/agents-tree/**`、`tests/fixtures/README.md`
- **测试**： 无（本身是测试资产）
- **验证**： 目录树与 README 预期一一对应
- **依赖**： 任务 1

### 任务 6: inventory.py — 枚举 (~5 min)
- **描述**： TDD。先写测试：agents.yaml 解析、`installed` 探测标记、skills 列表（name/path/description/size_kb/desc_len）、`--agent` 过滤、stdout 纯 JSON、失败退出码非 0。**注意：标准库无 yaml** —— 实现固定 schema 的迷你 YAML 子集解析器（仅支持本文件用到的键结构），不引第三方依赖
- **文件**： 创建 `scripts/inventory.py`、`tests/test_inventory.py`
- **测试**： `test_inventory.py` 枚举部分，用任务 5 fixtures
- **验证**： `uv run pytest tests/test_inventory.py` 绿；CLI `--agents tests/fixtures/agents-tree.yaml` 输出合法 JSON
- **依赖**： 任务 2, 5

### 任务 7: inventory.py — 健康检查 + 重复检测 (~4 min)
- **描述**： TDD。补充 `has_skill_md` / `frontmatter_ok` / `health_issues[]`（missing_skill_md、frontmatter 残缺、desc 超 1024、命名不一致）/ `duplicates[]` 字段实现与测试
- **文件**： 修改 `scripts/inventory.py`、`tests/test_inventory.py`
- **测试**： 坏样本全部命中对应 health_issue；重名 skill 出现在 duplicates
- **验证**： `uv run pytest tests/test_inventory.py` 绿（新增用例 ≥4）
- **依赖**： 任务 6

### 任务 8: sm-manager SKILL.md (~4 min)
- **描述**： 子 skill ①。frontmatter（name: sm-manager，description 含触发词：盘点skill/我装了哪些skill/skill清单/skill健康检查）+ 工作流：读 agents.yaml → 运行 inventory.py → LLM 解读 JSON（清单/重复对比/健康）→ 输出建议。只读约束（安装/卸载属 v2，明确拒绝）
- **文件**： 创建 `skills/sm-manager/SKILL.md`
- **测试**： 无（skill 层 smoke 在任务 23）
- **验证**： ≤200 行；触发词与任务 21 路由表一致；含"写操作拒绝"段
- **依赖**： 任务 7

### 任务 9: fixtures — 恶意 skill 样本 (~5 min)
- **描述**： 造 `malicious-skill/`：每条规则一个触发文件（"ignore previous instructions"、`curl -X POST $API_KEY`、`rm -rf`/注册表写、`eval(base64...)`/零宽字符/`.开头`隐藏文件、allowed-tools 高危通配）+ `clean-skill/`（干净样本防误报）；README 附 规则id → 文件 映射表
- **文件**： 创建 `tests/fixtures/malicious-skill/**`、`tests/fixtures/clean-skill/**`，更新 `tests/fixtures/README.md`
- **测试**： 无（测试资产）
- **验证**： 映射表覆盖 security-taxonomy 全部 5 类
- **依赖**： 任务 4（可与 6/7/8 并行）

### 任务 10: scanner.py — 规则引擎 (~5 min)
- **描述**： TDD。先写测试：malicious-skill 每样本命中正确 rule_id + severity；clean-skill 零 critical。实现 RULES 表（~25 条：id/severity/正则或文件名模式/explanation/false_positive_note，按 security-taxonomy 逐条生成）+ 文件遍历 + findings JSON
- **文件**： 创建 `scripts/scanner.py`、`tests/test_scanner.py`
- **测试**： 恶意样本全命中、干净样本零 critical 误报
- **验证**： `uv run pytest tests/test_scanner.py` 绿
- **依赖**： 任务 4, 9

### 任务 11: scanner.py — 评分 + 截断 + CLI (~4 min)
- **描述**： TDD。score 计算（severity 加权 → 0-100）、`--max-files 500` 与 50MB 截断警告（truncated 标记）、单文件模式、`--json`、失败退出码
- **文件**： 修改 `scripts/scanner.py`、`tests/test_scanner.py`
- **测试**： 评分函数边界（空/全critical/全low）；截断警告触发
- **验证**： pytest 绿；`uv run python scripts/scanner.py tests/fixtures/malicious-skill --json` 输出含 score 的合法 JSON
- **依赖**： 任务 10

### 任务 12: sm-security SKILL.md (~4 min)
- **描述**： 子 skill ②。工作流：定位本地路径 → scanner.py → LLM 复核 critical/high（对照 false_positive_note 降误报，标注"疑似误报"）→ 分级报告（0-100 分 + severity 标签 + 建议）。不承诺 100% 检出
- **文件**： 创建 `skills/sm-security/SKILL.md`
- **验证**： ≤200 行；含误报复核环节；错误处理（目标不存在/超大目标）
- **依赖**： 任务 11, 18 可后补（写作时可先引用 taxonomy）

### 任务 13: templates/report.html (~4 min)
- **描述**： 单文件自包含 HTML 模板：内联 CSS、零外部资源；占位符 `{{TITLE}}/{{SCORE}}/{{OVERVIEW}}/{{SECTIONS}}/{{FINDINGS_TABLE}}/{{GENERATED_AT}}`；含概览卡片、章节导航、安全风险表格（severity 色阶）样式
- **文件**： 创建 `templates/report.html`
- **验证**： 双击可开（渲染占位内容）；grep 确认无外链 `<script src>`/`<link href>`；占位符清单写入文件头注释
- **依赖**： 任务 1（可与 9-12 并行）

### 任务 14: report.py — 渲染器 (~5 min)
- **描述**： TDD golden file 测试：固定 analysis.md + findings.json → 渲染 → 与 golden 对比（时间戳等动态字段剥离后比较）。实现：markdown 子集 → HTML（stdlib，标题/列表/代码块/段落转义）、findings 表格注入、分数色阶、模板占位符替换
- **文件**： 创建 `scripts/report.py`、`tests/test_report.py`、`tests/golden/report.html`（由首次运行生成后人工确认固化）
- **测试**： golden 对比一致；markdown 转义安全（XSS 防护：`html.escape`）
- **验证**： pytest 绿；输出 HTML 双击可开
- **依赖**： 任务 13

### 任务 15: sm-analyzer SKILL.md (~4 min)
- **描述**： 子 skill ③。工作流：读源码 → LLM 写 analysis.md 中间稿（六章节：功能定位/架构/工作流拆解/设计模式/亮点短板/可借鉴点）→ scanner.py findings → report.py 渲染 → 交付 HTML + 中间稿留档。错误处理：渲染失败时中间稿已落盘可救
- **文件**： 创建 `skills/sm-analyzer/SKILL.md`
- **验证**： ≤200 行；六章节与设计数据模型一致；输入=本地路径（在线下载明确范围外）
- **依赖**： 任务 14, 3

### 任务 16: references/writing/ 吸收 (~3 min)
- **描述**： 从 `template/writer/write-a-skill` 吸收：3 阶段流程（需求收集→起草→用户复核）、SKILL.md 模板、结构校验清单 → 整合为两份文档，注明来源（MIT, Matt Pocock derived）
- **文件**： 创建 `references/writing/workflow.md`、`references/writing/structure-checklist.md`
- **验证**： sm-writer 可直接引用；含来源声明
- **依赖**： 任务 1（可与 9-14 并行）

### 任务 17: references/optimizing/ 吸收 (~4 min)
- **描述**： 从 skill-optimizer 吸收审查清单（触发语义/工作流可靠性/异常处理/输出契约/结构分层/敏感信息/粒度等），从 skill-creator 吸收 eval 思想（触发准确性评估）
- **文件**： 创建 `references/optimizing/review-checklist.md`、`references/optimizing/eval-notes.md`
- **验证**： 清单覆盖设计文档四诊断维度（触发语义/工作流/资源组织/安全边界）
- **依赖**： 任务 1（可与 9-14 并行）

### 任务 18: references/security/ 吸收 (~4 min)
- **描述**： 从 SkillSpector 吸收思想（不搬 Apache 代码）：规则模式示例（每类 2-3 个正则范例 + 上下文取证方式）、severity 定级标准
- **文件**： 创建 `references/security/pattern-examples.md`、`references/security/severity-guide.md`
- **验证**： 与 security-taxonomy.md 一致无冲突；无代码拷贝（仅思想表述）
- **依赖**： 任务 4（可与 13-17 并行）

### 任务 19: sm-writer SKILL.md (~5 min)
- **描述**： 子 skill ④。工作流：需求访谈（**一次一问**）→ 3 方案选型（对照 skill-anatomy 规范）→ 起草（引用 references/writing/workflow）→ 结构自检（structure-checklist 逐项过）→ 用户确认 → 落盘（写入用户指定目录，落盘前必须确认）
- **文件**： 创建 `skills/sm-writer/SKILL.md`
- **验证**： ≤200 行；"一次一问"与"确认后落盘"约束醒目；自检清单完整引用
- **依赖**： 任务 3, 16

### 任务 20: sm-optimizer SKILL.md (~5 min)
- **描述**： 子 skill ⑤。工作流：**先审查后动手**——读目标 → 按清单诊断（references/optimizing/review-checklist 四维度）→ 分优先级计划 → 用户确认 → 修改 → 校验输出 before/after 说明
- **文件**： 创建 `skills/sm-optimizer/SKILL.md`
- **验证**： ≤200 行；"未确认前不改文件"约束醒目；before/after 输出契约明确
- **依赖**： 任务 3, 17

### 任务 21: 根 SKILL.md 路由器 (~4 min)
- **描述**： 参照 cheat-on-content 模式：frontmatter（name: skill-master，description 含 5 类场景触发词概览）+ 路由表（触发词 → sm-*，含前置条件列）+ 总协议三条（脚本做确定性事/LLM 做判断事/危险操作必须确认）+ 各子 skill 触发词与其 frontmatter 逐一核对
- **文件**： 创建 `SKILL.md`（项目根）
- **验证**： ≤200 行；路由表覆盖 5 子 skill 全部触发词且与各 frontmatter 一致；含负例说明（防抢触发）
- **依赖**： 任务 8, 12, 15, 19, 20

### 任务 22: install.ps1 (~3 min)
- **描述**： PowerShell 5.1 安装脚本：检测 opencode 全局 skill 目录 → `New-Item -ItemType Junction` 链接 skill-master → 已存在时提示跳过；支持 `-Remove` 卸载、`-WhatIf` 干跑；junction 失败降级为复制模式
- **文件**： 创建 `install.ps1`
- **验证**： PowerShell 语法解析通过；`-WhatIf` 干跑输出正确目标路径
- **依赖**： 任务 21

### 任务 23: 集成验收 + smoke (~5 min)
- **描述**： 按设计文档验收标准全量回归：① 全量 pytest ② inventory 对照手工 `Get-ChildItem` 枚举真实 opencode 目录一致 ③ scanner 对全部恶意样本命中 + 干净样本零 critical ④ report HTML 双击可开 ⑤ 5 个子 skill 各 3 条触发词 + 1 条负例走查路由表
- **文件**： 可选创建 `tests/SMOKE.md` 记录结果
- **验证**： 设计文档三条验收标准全过；结果记录在案
- **依赖**： 全部任务

## 并行机会

- **任务 2、3、4** 三个知识文档互不依赖，可并行
- **任务 5、9** 两个 fixtures 互不依赖，可与文档任务并行
- **任务 13、16、17、18** 在骨架就绪后可与 manager/security 线（6-12）并行
- **任务 16、17、18** 彼此并行（不同 references 目录）

## 风险 & 缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 标准库无 YAML 解析器 | 高 | 中 | inventory.py 内置固定 schema 迷你解析器（~60 行），不引第三方依赖 |
| Agent 默认路径不准 | 中 | 低 | agents.yaml 可配置 + 探测不到标 `not-installed`（非错误）|
| scanner 正则误报 | 中 | 中 | 每条规则带 false_positive_note + sm-security 的 LLM 复核环节 + clean fixtures 防回归 |
| golden file 含动态内容 | 低 | 低 | 渲染时动态字段（时间戳）剥离后再对比 |
| 模板占位符与渲染器不匹配 | 中 | 中 | 任务 13 先冻结占位符清单（文件头注释），任务 14 依赖 13 |
| install.ps1 junction 权限不足 | 低 | 中 | 降级为复制模式并明确提示差异 |
| 迷你 YAML 解析器遇到用户自定义复杂结构 | 中 | 低 | agents.yaml 头注释声明受支持的 schema 子集；解析失败输出明确错误 JSON |

## 测试策略

| 层级 | 内容 | 覆盖目标 |
|------|------|----------|
| 单元测试（pytest） | inventory 枚举/健康/重复、scanner 规则/评分/截断、report 渲染 | 3 个脚本 100% 分支 |
| Golden file | report.py 输出对比 | 渲染确定性 |
| Fixtures 回归 | 恶意样本全命中 + 干净样本零 critical | 每次改动即验证 |
| Skill 层 smoke（手动） | 5 子 skill × 3 触发词 + 1 负例 | 路由准确、不抢触发 |
| 验收 | 对照设计文档三条标准 | 最终交付门槛 |

---

**计划统计**： 23 个任务，预估总时长 ~90 分钟，关键路径 = 任务 1 → 2/5 → 6 → 7 → 8 →（security 线）10 → 11 → 12 →（analyzer 线）13 → 14 → 15 →（writer/optimizer）19/20 → 21 → 22 → 23。
