---
name: sm-analyzer
description: 通读本地的开源 skill 源码，拆解其功能、架构、工作流与设计模式，附静态安全扫描，产出自包含 HTML 分析报告。Use when 用户提到"分析这个skill"、"拆解这个开源skill"、"它怎么工作的"、"skill原理"、"这个skill写得怎么样"时使用。
---

# sm-analyzer — 开源 skill 分析（子 skill ③）

对用户指定的本地 skill 目录做深度分析：先写六章节中间稿 analysis.md，
再跑 scanner.py 安全扫描，最后用 report.py 渲染成单文件 HTML 报告。

遵循三原则（shared-references/skill-anatomy.md §6.2）：扫描与渲染等
确定性操作交给脚本，解读与评价等语义判断留给 LLM，产物落盘前先与
用户确认去向。

## 工作流

1. [ ] **确认输入**：被分析 skill 必须是**本地目录**（用户已 clone/下载）。
   - 用 `Test-Path` 核对路径；不存在时向用户展示报错并请其核对，不猜路径
   - 用户给 GitHub 仓库链接时：**在线下载不在本 skill 范围内**，请用户先
     自行下载到本地，再提供目录路径
   - 同时确认产物输出位置：默认被分析 skill 同目录，用户指定处优先；
     三件产物（analysis.md / findings.json / HTML）都写到这里

2. [ ] **通读源码**：
   - `SKILL.md` 必读——frontmatter、工作流、引用结构
   - `references/`、`scripts/`、`assets/` 按存在逐个通读；其余文件浏览用途
   - 超大目标（文件数 >500，或后续扫描报 truncated）时，先向用户说明
     **抽样策略**（入口文件与脚本全读、references 抽样、其余跳过），
     确认后再继续

3. [ ] **写中间稿 analysis.md 并落盘**（后续步骤都以它为源，先写盘再走）：
   - 首行一个 H1：`# <skill名> 分析报告`——report.py 把第一个 H1 抽作
     报告标题并从正文移除，**全文勿出现第二个 H1**
   - 六章节固定结构，每章一个 `##`，顺序不可变：
     - `## 功能定位` — 做什么、给谁用、什么场景触发
     - `## 架构` — 目录结构、各文件分工、渐进披露的组织方式
     - `## 工作流拆解` — 入口文件描述的执行步骤，脚本/LLM/用户各管哪段
     - `## 设计模式` — description 写法、触发词、步骤清单化、引用下沉等手法
     - `## 亮点与短板` — 结构规范性逐条对照 shared-references/skill-anatomy.md：
       目录结构（§1）、frontmatter（§2）、SKILL.md ≤200 行（§4.1）、
       description 与触发词写法（§5）、反模式（§4.3）
     - `## 可借鉴点` — 具体到文件与写法（如"SKILL.md 的 Use when 句式"），
       不写空泛表扬
   - 只用渲染器支持的 markdown 子集：`###`/`####` 标题、段落、有序/无序
     列表、围栏代码块、`行内code`、**粗体**；表格、链接等其余语法按纯
     文本输出，尽量不用

4. [ ] **安全扫描**（PowerShell，从 skill-master 仓库根执行）：

   ```powershell
   python scripts/scanner.py "<被分析skill路径>" --json | Out-File -Encoding utf8 findings.json
   ```

   - stdout 恒为单一 JSON：`{"score","findings":[...],"truncated"}`
   - 必须用 `Out-File -Encoding utf8` 落盘：PowerShell 5.1 的 `>` 重定向
     写 UTF-16，report.py 按 utf-8 读会失败
   - `truncated: true`（目标超 500 文件被截断）时，回中间稿补注一句
     （放"亮点与短板"章末）：安全扫描被截断，结果只覆盖前 500 个文件
   - 退出码非 0 时向用户展示 error JSON 并**只停止本环节**——中间稿已在
     步骤③落盘，不丢；是否继续渲染由用户决定

5. [ ] **渲染 HTML 报告**：

   ```powershell
   python scripts/report.py --draft analysis.md --findings findings.json --out "<skill名>-analysis-<YYYY-MM-DD>.html"
   ```

   - 文件名含 skill 名与日期；可选 `--timestamp "YYYY-MM-DD HH:MM"` 固定
     报告生成时间（默认取当前时间）
   - 成功时 stdout 打印输出路径；产物为自包含 HTML（内联 CSS，零外部资源）
   - 退出码非 0 时不写输出文件：向用户展示 stderr 报错，**跳过渲染环节**，
     把已落盘的 analysis.md 直接交给用户并说明渲染失败原因

6. [ ] **交付**：给用户 HTML 路径 + 一段话总结（功能一句话、结构规范性
   结论、安全分与关键 findings、最值得借鉴的 1-2 点）。analysis.md 与
   findings.json 留档不删——渲染失败时 analysis.md 就是可交付的救场稿。

## 错误处理

| 场景 | 处理 |
|---|---|
| 被分析路径不存在 | 展示报错，请用户核对路径或先自行下载；不猜路径、不搜盘 |
| scanner.py 失败（非 0 退出） | 展示 error JSON，停止安全扫描环节；中间稿保留，后续环节待用户决定 |
| report.py 失败（非 0 退出） | 展示 stderr 报错，不写输出；analysis.md 直接交付并说明失败原因 |

三个环节各自独立降级：任一脚本失败只停对应环节，**已落盘的中间稿永不丢**。

## 边界

- **安全深度分工**：本 skill 呈现 scanner 的总分与规则命中即止；逐条
  误报复核、修复建议等深度安全审查属 sm-security，需要时明确转介
- 对被分析 skill 的评价保持**客观**：亮点与短板都指向可验证的事实
  （行数、目录结构、具体写法），不堆形容词
- 只新增分析产物，**不修改被分析 skill 的任何源文件**
