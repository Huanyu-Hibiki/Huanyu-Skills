# skill-master 合集 设计文档

> 状态: 已批准（2026-08-28 头脑风暴定稿）
> 形态参考: `C:\work\huanyu-skills-project\template\cheat-on-content`（合集路由器架构）
> 内容参考: `C:\work\HuanyuCode\template`（writer / optimizer / security 三类）

## 目标

构建一个名为 **skill-master** 的 skill 合集，覆盖 skill 全生命周期：盘点本地各 Agent 已装 skill、安全审查外部 skill、深度分析开源 skill 并产出 HTML 报告、编写新 skill、迭代优化已有 skill。

## 用户场景

1. **盘点**：用户说"我装了哪些 skill" → 枚举 opencode/codex/claude code/trae 等全局 skill 目录，输出清单 + 重复对比 + 健康检查
2. **安全**：用户从 GitHub/skill Hub 下载了一个 skill，说"检查这个 skill 有没有后门" → 规则扫描 + LLM 复核 → 分级报告
3. **分析**：用户说"拆解这个开源 skill" → 读源码 → 功能/原理/架构分析 → 单文件 HTML 报告（内嵌安全风险章节）
4. **编写**：用户说"帮我写个 skill" → 需求访谈 → 选型 → 起草 → 自检 → 确认落盘
5. **优化**：用户说"优化这个 skill"/"触发不准" → 先审查诊断 → 出计划 → 确认后修改（常用于④的产物迭代）

## 技术方案

**混合形态合集**（cheat-on-content 模式）：LLM 擅长的流程编排/分析/写作 = markdown 子 skill；确定性操作（枚举/扫描/渲染）= Python 脚本；根 SKILL.md 做路由器。环境：Windows + PowerShell 5.1，Python 3.13.5 + uv 0.8.3（已验证可用），脚本仅依赖标准库。

```
C:\work\HuanyuCode\skill-master\
├── SKILL.md                      # 路由器：触发词 → 子 skill 路由表 + 总协议
├── skills/
│   ├── sm-manager/SKILL.md       # ① 本地 skill 盘点（只读）
│   ├── sm-security/SKILL.md      # ② 安全扫描
│   ├── sm-analyzer/SKILL.md      # ③ 开源 skill 分析 + HTML 报告
│   ├── sm-writer/SKILL.md        # ④ skill 编写
│   └── sm-optimizer/SKILL.md     # ⑤ skill 迭代优化
├── scripts/
│   ├── inventory.py              # 枚举各 Agent skill 目录 → JSON 清单
│   ├── scanner.py                # 安全规则引擎 → JSON findings
│   └── report.py                 # HTML 报告生成器（模板渲染）
├── shared-references/
│   ├── agents.yaml               # Agent 目录注册表（可配置+可探测）
│   ├── skill-anatomy.md          # skill 结构/原理知识（③④⑤共享）
│   └── security-taxonomy.md      # 风险分类学（吸收 SkillSpector 17 类思想）
├── templates/
│   └── report.html               # 单文件自包含 HTML 报告模板
├── references/                   # 从 template/ 吸收的精华
│   ├── writing/                  # ← write-a-skill（3阶段流程+结构校验清单）
│   ├── optimizing/               # ← skill-optimizer（审查清单）+ skill-creator（eval思想）
│   └── security/                 # ← SkillSpector（规则模式示例+分级思想）
├── tests/                        # pytest + fixtures
└── install.ps1                   # 安装到 opencode 全局目录（junction 链接）
```

**关键决策**：
- **agents.yaml 注册表**而非硬编码路径：内置各 Agent 已知默认路径模式（Windows 优先），探测不到标记 `not-installed`，用户可增删
- **子 skill 命名 `sm-*`** 前缀，避免与通用词抢触发
- **HTML 报告 = LLM 写 markdown 中间稿 + 脚本渲染**：分析与样式分离，各自可靠
- **安全 = 自建轻量规则库**（~25 条/5 类），吸收 SkillSpector 分类与分级思想，不搬其代码、不做其依赖
- **manager MVP 只读**：不做写删操作，安装/卸载/同步留给 v2

### 各子 skill 设计

| # | 子 skill | 触发词 | 核心工作流 | 输出 |
|---|---------|--------|-----------|------|
| ① | sm-manager | 盘点skill/我装了哪些skill/skill清单/skill健康检查 | 读 agents.yaml → inventory.py → LLM 解读 | 各 Agent 清单、跨 Agent 重复对比、健康检查（缺 SKILL.md/frontmatter 残缺/description 超 1024 字符/命名不一致） |
| ② | sm-security | 检查这个skill安全吗/扫描skill/有没有后门 | 定位路径 → scanner.py → LLM 复核高危项（降误报）→ 分级报告 | 0-100 风险分 + severity 标签 + 建议 |
| ③ | sm-analyzer | 分析这个skill/拆解这个开源skill/它怎么工作的 | 读源码 → LLM 写中间稿（功能定位/架构/工作流/设计模式/亮点短板/可借鉴点）→ scanner.py findings → report.py 渲染 | 单文件 HTML：概览卡片/功能与原理/架构图/安全风险（内嵌②）/可借鉴点/总评分 |
| ④ | sm-writer | 帮我写个skill/新做一个skill | 需求访谈（一次一问）→ 3 方案选型 → 起草（按 skill-anatomy 规范）→ 结构自检 → 用户确认 → 落盘 | 新 skill 目录 |
| ⑤ | sm-optimizer | 优化这个skill/skill触发不准/改skill | **先审查后动手**：读目标 → 按清单诊断（触发语义/工作流/资源组织/安全边界）→ 分优先级计划 → 确认后修改 → 校验 | 优化后的 skill + before/after 说明 |

**安全规则库 v1（~25 条，5 类）**：提示注入（忽略之前指令类模式）、数据外泄（curl POST+env、可疑域名）、破坏命令（rm -rf/格式化/注册表写）、混淆隐藏（base64 长串/eval/零宽字符/.开头隐藏文件）、过度权限（allowed-tools 高危通配）。每条规则 = id + severity + 模式 + 解释 + 误报说明。

**共性约束**：每个 SKILL.md ≤200 行（超出下沉 references/）；脚本做确定性事、LLM 做判断事、危险操作必须确认。

## 数据模型

**inventory.json**（inventory.py 输出）：
```json
{
  "agents": [{"name": "opencode", "path": "...", "installed": true,
    "skills": [{"name": "...", "path": "...", "description": "...",
      "size_kb": 12.3, "has_skill_md": true, "frontmatter_ok": true, "desc_len": 210}]}],
  "duplicates": [{"name": "...", "locations": ["...", "..."]}],
  "health_issues": [{"skill": "...", "issue": "missing_skill_md", "detail": "..."}]
}
```

**findings.json**（scanner.py 输出）：
```json
{
  "score": 34,
  "findings": [{"rule_id": "EXFIL-001", "severity": "critical",
    "file": "scripts/x.py", "line": 42, "evidence": "curl -X POST $ENV..."},
                {"explanation": "环境变量外传到外部域名"}]
}
```

**analysis.md**（sm-analyzer 中间稿）：结构化 markdown，章节 = 功能定位 / 架构 / 工作流拆解 / 设计模式 / 亮点与短板 / 可借鉴点。

## 接口设计

```
inventory.py --agents shared-references/agents.yaml [--agent opencode] [--json]
  → stdout JSON（见上），退出码非 0 = 失败并输出错误 JSON

scanner.py <skill目录或文件> [--json] [--max-files 500]
  → stdout JSON（见上）

report.py --draft analysis.md --findings findings.json --out report.html
  → 单文件自包含 HTML（内联 CSS，无外部资源）
```

约定：脚本 stdout 只输出机器可读结果，人话解读交给子 skill 的 LLM。

## 错误处理

| 失败模式 | 应对 |
|---|---|
| Agent 目录不存在 | 标记 `installed:false`，正常继续（非错误） |
| SKILL.md 缺失/frontmatter 坏 | 健康检查记录 issue，不中断枚举 |
| 扫描目标超大 | 超 500 文件/50MB 截断并警告 |
| report.py 渲染失败 | markdown 中间稿已落盘，人工可救 |
| 扫描误报 | LLM 复核环节标注"疑似误报"，规则表附误报说明 |

## 测试策略

- **脚本层（pytest）**：`tests/fixtures/` 造 ①假 Agent 目录树（含健康问题样本）②恶意 skill 样本（每条规则一个触发样例 + 干净样例防误报）③报告 golden file 对比
- **skill 层（手动 smoke）**：每个子 skill 3 条触发词实测 + 1 条负例（防抢触发）
- **验收标准**：inventory 枚举与手工 `Get-ChildItem` 一致；scanner 对全部恶意样本命中、对干净样本零 critical 误报；HTML 双击可开

## 开发顺序（依赖序，全量交付）

manager → security → analyzer → writer → optimizer，每完成一个跑该层测试再进下一个。

## 明确不在 v1 范围

- skill 安装/卸载/跨 Agent 同步/启停（manager v2）
- 在线下载 skill（analyzer 输入 = 本地路径，用户自行 clone）
- 直接依赖或调用 SkillSpector CLI
- 处理用户已装的其他 skill 合集的边界问题（不吸收、不卸载已有 skill）
