# SMOKE — 集成验收记录（任务 23）

- **日期**： 2026-08-28
- **环境**： Windows 10 / PowerShell 5.1 / uv 0.8.3 / Python 3.12.11（venv；计划预估时写的 3.13.5，实际 venv 为 3.12.11，全部脚本仅依赖标准库，95 项测试全绿，无功能影响）
- **仓库**： `C:\work\HuanyuCode\skill-master` @ `52feac9`（验收时 HEAD）
- **对照**： 设计文档验收标准①②③ + 计划任务 23 五项走查

## 结果总表

| 项 | 内容 | 真实输出摘要 | 结果 |
|---|---|---|---|
| A1 | 全量测试 `uv run pytest` | **95 passed in 3.13s**（test_inventory 26 / test_report 26 / test_scanner 43，退出码 0） | ✅ |
| A2 | 真实枚举对照（验收标准①） | inventory 枚举 opencode **56 个 skill** = `(Get-ChildItem C:\work\.opencode\skills -Directory).Count` = **56**，一致；claude-code/codex/trae/gemini/cursor 全部 `installed: false`；`duplicates: []`；`health_issues` 8 条（见下） | ✅ |
| A3 | 扫描器验收（验收标准②） | malicious-skill：**distinct rule_id 恰好 25**（INJ×5 / EXFIL×6 / DEST×4 / OBF×6 / PERM×4）、score=100>0；clean-skill：**findings=[]、score=0**；Python 断言全部通过 | ✅ |
| A4 | 端到端报告（验收标准③） | clean：`smoke-report.html`（9,621 B）生成，无 `{{` 残留、含 `<!DOCTYPE html>`、`<script` 计数 0、html/body/div/table 标签配对平衡，空 findings 表正常渲染（colspan=5 空行）；malicious：`smoke-report-mal.html`（22,312 B）同项全过且 severity 徽章出现（sev-critical×23 / sev-high×59 / sev-medium×29 / sev-low×11，含计数卡+徽章+行级） | ✅ |
| A5 | 路由 smoke（文档级走查） | 路由表 **25 条触发短语全量核对**（超出抽样 3×5=15 要求）：每条均逐字出现在对应子 skill frontmatter 且**不出现**在其他四个子 skill frontmatter（零串扰）；负例表抽 1 条走查通过（见下） | ✅ |
| A6 | 安装干跑 `.\install.ps1 -WhatIf` | 输出：源 `C:\work\HuanyuCode\skill-master` → junction `C:\Users\kabuto\.config\opencode\skills\skill-master`，与 agents.yaml 中 opencode 全局路径声明一致；该目录本机暂不存在，脚本注明“不存在则创建”；不实际执行 | ✅ |

**结论：A1-A6 共 6 项全部通过，无一失败。**

## A2 真实数据备查

health_issues（8 条，均为真实问题，抽查 2 条已人工复核）：

| skill | issue | 说明 |
|---|---|---|
| ali-abdaal-perspective | frontmatter_broken | frontmatter 围栏未闭合或 name/description 缺失/空 |
| bruce-schneier-perspective | missing_skill_md | 目录缺 SKILL.md |
| creem-preflight-review-workspace | missing_skill_md | 目录缺 SKILL.md |
| geifei-perspective | frontmatter_broken | 同上围栏问题 |
| nuwa-skill | name_mismatch | frontmatter name `huashu-nuwa` ≠ 目录名 `nuwa-skill` |
| peter-drucker-perspective | frontmatter_broken | 同上围栏问题 |
| shendu-yuedu | missing_skill_md | 目录缺 SKILL.md（人工复核：顶层确无，系分步合集目录）✓ |
| xinmeiti-huoke | missing_skill_md | 目录缺 SKILL.md（人工复核：顶层确无，系分步合集目录）✓ |

duplicates：`[]`（跨 Agent 无重名；本机仅 opencode 一家 installed）。

## A3 规则命中明细

25 个 distinct rule_id（score=100）：
INJ-001..005、EXFIL-001..006、DEST-001..004、OBF-001..006、PERM-001..004 —— 与 security-taxonomy 五大类及 scanner 声明的 25 条规则一一对应，无缺漏无超额。

## A4 验证明细

- 产物：`%TEMP%\opencode\smoke-report.html`（clean，空 findings 表）、`%TEMP%\opencode\smoke-report-mal.html`（malicious，含风险表）——均在临时目录，未入仓库
- 结构断言（两份均过）：`no_placeholder` / `has_doctype` / `script_count_0` / `balanced_html` / `balanced_body` / `balanced_div` / `balanced_table` 全 True
- 过程注记：首次断言用了臆造类名 `badge-*` 而失败一次，改按模板实际类名 `sev sev-*` 后通过——系验收脚本笔误，非产物缺陷

## A5 路由走查明细

- 正向：sm-manager / sm-security / sm-analyzer / sm-writer / sm-optimizer 各 5 条（全量 25 条）触发短语，"路由目标 = 短语所在子 skill frontmatter"逐条 PASS，且无一短语跨 skill 串扰
- 负例（抽 1）：`"优化这段 Python 代码"`——与 sm-optimizer 触发词共享关键词"优化"，但操作对象是 Python 代码而非含 SKILL.md 的 skill 目录；根 SKILL.md 负例表明确判"不路由"，与判别标准（操作对象是否为 skill 目录）一致 → PASS

## A6 干跑输出（UTF-8 修正后）

```
[WhatIf] 源仓库     ：C:\work\HuanyuCode\skill-master
[WhatIf] skill 目录 ：C:\Users\kabuto\.config\opencode\skills（不存在则创建）
[WhatIf] 将创建 junction：C:\Users\kabuto\.config\opencode\skills\skill-master -> C:\work\HuanyuCode\skill-master
[WhatIf] （junction 失败时降级为递归复制模式）
```

注：本机当前活跃目录为工作区级 `C:\work\.opencode\skills`（56 个 skill 所在）；全局目录 `.config\opencode\skills` 尚不存在，安装时将自动创建。如需装到工作区目录，可 `.\install.ps1 -Target C:\work\.opencode\skills`。
