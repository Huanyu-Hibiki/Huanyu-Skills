---
name: sm-manager
description: 盘点本机各 AI Agent（opencode/claude-code/codex 等）已安装的 skill，输出清单、跨 Agent 重复对比与健康检查结论。只读，不安装、不卸载、不修改任何 skill。Use when 用户提到"盘点skill"、"我装了哪些skill"、"skill清单"、"skill健康检查"、"skill重复"时使用。
---

# sm-manager — 本地 skill 盘点（只读）

枚举 `shared-references/agents.yaml` 注册的各 Agent skill 目录，解读
`scripts/inventory.py` 输出的 JSON，产出清单、重复对比与健康结论。

遵循三原则（shared-references/skill-anatomy.md §6.2）：脚本做确定性事
（枚举与健康检查交给 inventory.py）、LLM 做判断事（解读与建议）、危险操作
必须确认——本 skill 只读，本身无危险操作。

## 工作流

1. [ ] **定位注册表**：优先用 skill-master 仓库内的
   `shared-references/agents.yaml`（本 skill 目录向上两级即仓库根）；
   用户指定了其他注册表就用用户的路径；两者都没有时询问用户，不猜路径。
   - 注册表归用户编辑：可增删 Agent 条目、追加候选路径、置
     `enabled: false` 跳过某个 Agent（本 skill 不代改，见"只读约束"）
   - 路径一律正斜杠写法，支持 `~/...` 与 `%USERPROFILE%/...` 前缀，
     脚本解析时自动展开为绝对路径

2. [ ] **运行盘点脚本**（PowerShell，从仓库根执行）：

   ```powershell
   python scripts/inventory.py --agents shared-references/agents.yaml --json
   ```

   - stdout 恒为单一 JSON 对象；退出码非 0 时向用户原样展示 error JSON
     并**停止**——不重试、不猜测、不绕过脚本自行枚举
   - 只盘点单个 Agent 时追加 `--agent <name>`

3. [ ] **解读 JSON 三块**（只解读，不重新枚举目录）：
   - **agents** — 各 Agent 的 skill 清单。`installed: false` 仅表示该路径
     探测不到（Agent 未安装或目录未建立），**不是错误**，照实说明即可
   - **duplicates** — 同名 skill 出现在多个 Agent。逐条列出位置，提醒用户
     关注是否版本漂移：同名不同步，更新时容易漏改一处
   - **health_issues** — 四类问题，判据与修法见 skill-anatomy.md §3：
     - `missing_skill_md`：目录缺 SKILL.md，Agent 加载不到，等于没装
     - `frontmatter_broken`：围栏未闭合或缺 name/description 键，路由信号不可用
     - `desc_too_long`：description 超 1024 字符，靠后的触发词会被截掉
     - `name_mismatch`：frontmatter name 与目录名不一致，重复计数、更新易错对象

4. [ ] **输出汇总与建议**：一张总表（Agent × 已装 skill 数 × 问题数）、
   重复列表、按影响排序的问题与修复建议。建议只说"该做什么"，
   不代用户动手改。

## 只读约束（硬性）

- 本 skill **不执行任何写、删、安装、卸载、同步、启停操作**，不改任何文件
  ——包括 agents.yaml：用户想调整盘点范围时，指引用户自行编辑注册表
- 用户要求安装、卸载、同步、启停 skill 时，**明确拒绝**并说明：这些操作
  属 skill-master v2 范围，当前版本只盘点、不改动

## 边界

- 目录很大（几百个 skill）时输出汇总统计与问题项，不逐条罗列全部 skill；
  用户明确要完整清单时再全量列出
- 一切数字与结论以脚本 JSON 为准，不自行解析 SKILL.md 或重复实现检查逻辑
