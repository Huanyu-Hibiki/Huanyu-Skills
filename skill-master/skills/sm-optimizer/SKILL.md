---
name: sm-optimizer
description: 诊断并迭代优化已存在的 skill——机器健康检查 + 四维语义诊断（触发语义/工作流/资源组织/安全边界），产出分优先级优化计划，经用户确认后单变量实施、before/after 验证。Use when 用户提到"优化这个skill"、"skill触发不准"、"改skill"、"skill不触发"、"迭代skill"时使用。
---

# sm-optimizer — 已有 skill 迭代优化（先审查后动手）

对**已存在**的 skill 走"诊断 → 计划 → 确认 → 修改 → 验证"。铁律贯穿全程：
**先审查，后动手**——未获用户确认前，不修改目标 skill 的任何文件。

知识资产（判据与细节都在这些文件里，本文件不重复；路径相对仓库根，
即本 skill 目录向上两级）：

- `references/optimizing/review-checklist.md` — 四维诊断清单 + 诊断输出格式
- `references/optimizing/eval-notes.md` — 触发测试集构造 + before/after 记录法
- `shared-references/skill-anatomy.md` — 结构判据权威（下文以 § 编号引用）
- `scripts/inventory.py` — 机器四项健康检查

## 工作流

1. [ ] **定范围**：确认目标 skill 已存在——不存在的归 sm-writer 新写。
   - 用户指定了方向（如"只改 description"、"skill 触发不准"）→ 只做该
     维度深查；其余维度发现的问题列入"额外建议"，不偷偷扩大改动面
   - 只说"优化这个skill" → 全量四维诊断

2. [ ] **机器检查**（PowerShell，仓库根执行）：目标 skill 在
   `shared-references/agents.yaml` 注册范围内时直接用；不在时写临时
   注册表指向其所在目录（放系统临时目录，用后删除），命令相同：

   ```powershell
   python scripts/inventory.py --agents shared-references/agents.yaml --json
   ```

   解读 `health_issues` 四项（判据 skill-anatomy §3）：`missing_skill_md` /
   `frontmatter_broken` / `desc_too_long` / `name_mismatch`。退出码非 0
   时向用户展示 error JSON 并停止。机器查的是结构层，语义层进步骤 ③。

3. [ ] **语义诊断**：读 review-checklist.md，四维逐项检查（触发语义 /
   工作流可靠性 / 资源组织 / 安全边界）。其中：
   - 维度一（触发语义）按 eval-notes §一 构造 3 正例 + 1 负例逐一走查
   - 发现疑似安全问题（明文密钥、危险操作裸奔、权限全开）：只记录
     类型与位置，不回显完整值，转介 sm-security（见"边界"）

   产出按影响排序的问题列表，格式用 review-checklist 的诊断输出表：
   **维度 / 严重度 / 位置 / 问题与建议**。

4. [ ] **优化计划**：按高 / 中 / 低分优先级（排序规则同 review-checklist
   严重度定义）。每项写清三件事：**改什么、为什么、预期影响**——
   写不出预期影响的项不做。

5. [ ] **等待用户确认**：展示问题列表 + 优化计划，停在这里等确认。
   - 未确认前禁止修改目标 skill 的任何文件，包括"顺手的小改"
   - 用户否定或缩小范围 → 回步骤 ① 重定范围，重新出计划

6. [ ] **实施（单变量）**：一次只改一个变量，改完一项立即验证，
   通过后再进入下一项。
   - 改 description 前**先冻结触发测试集**（eval-notes §一）——改完
     后才有判断好坏的基准
   - 触发没有实际失败案例、只是"感觉不放心" → 不动（eval-notes §三）

7. [ ] **验证与记录**：逐项按 eval-notes §二 的表格做 before/after 记录
   （日期 / 改动点 / 预期影响 / 验证话术 / 结果）。
   - 3 正例全触发 + 负例不触发 = 通过 → keep
   - 结果差 → **回滚优先**：恢复上一个 keep 版本，不在坏版本上叠加
   - 连续两轮收益微小 → 停手（见好就收）

## 硬约束

- **诊断 ≠ 修改**：输出问题列表后先给分优先级的计划，等确认再动手
- **确认前零改动**：未获用户明确确认，不改目标 skill 的任何文件
- **单变量原则**：一次只改一个变量，否则结果好坏无法归因
- **回滚优先于叠加**：验证失败恢复上一个 keep 版本，而不是继续打补丁

## 边界

- **新写 skill 归 sm-writer**：本 skill 只处理已存在的 skill
- **安全深查归 sm-security**：诊断中发现疑似安全问题，本 skill 只在
  报告中记录类型与位置并转介，不展开修复、不回显敏感值
