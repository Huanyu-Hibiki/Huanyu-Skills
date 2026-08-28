---
name: video-skill-optimize
description: 视频制作 Skill 迭代优化器。基于真实任务轨迹、用户纠正、失败、返工和成功模式，执行证据记录、模式聚合、有界候选修改、留出案例验证和人工采纳，持续优化 video-production-workflow 的全部 Skills。触发词：优化视频 skill、复盘制作流程、记录经验、skill 迭代、skillopt、这次协作哪里要改、把这个教训写进 skill。
---

# /video-skill-optimize

把 `video-production-workflow` 的 Markdown、脚本、模板和协议视为可训练状态，但不做无闸门的自我改写。完整协议见 `../../shared-references/skill-optimization.md`。

## 工作模式

| 模式 | 用途 | 是否修改生产 Skill |
|---|---|---|
| `record` | 从当前任务或对话记录一个具体信号 | 否 |
| `status` | 查看证据、候选和拒绝缓冲区 | 否 |
| `mine` | 按 Skill 和信号类型聚合重复模式 | 否 |
| `propose` | 聚合重复信号，暂存完整候选文件 | 否 |
| `gate` | 用留出案例比较基线与候选 | 否 |
| `adopt` | 用户明确确认后原子替换目标文件 | 是 |

## 1. 记录证据

只记录可复核的具体表现：用户明确纠正、工具/脚本失败、重复返工、边界误判、遗漏 QA、有效降级或显著节省步骤。不要把一般感想、模型猜测或整段对话原文写入账本。

```powershell
uv run --project "<合集根>" python "<合集根>/scripts/video-skill-optimize/optimize.py" record `
  --source dialogue --task-id EP009 --skill video-polish --kind user_correction `
  --summary "终稿必须由用户从剪映导出" `
  --expected "只准备预览并等待用户导出" `
  --observed "Agent 曾把预览误当最终交付" `
  --severity high
```

若信号包含密钥、Cookie、手机号、内部 URL 或未公开内容，先概括和脱敏。默认账本在合集根 `.skillopt-video/`，已从版本控制排除。

聚合可提案模式：

```powershell
uv run --project "<合集根>" python "<合集根>/scripts/video-skill-optimize/optimize.py" mine
```

## 2. 形成候选

满足任一条件才提出修改：同类信号出现至少 2 次；用户明确要求固化；或单次问题涉及 Raw 覆盖、错误最终交付、许可证、付费调用等高风险边界。优先修改最小责任文件，不把具体项目路径、人物和一次性 workaround 写入通用 Skill。

先复制目标文件并编辑候选副本，再登记：

```powershell
uv run --project "<合集根>" python "<合集根>/scripts/video-skill-optimize/optimize.py" propose `
  --target "skills/video-polish/SKILL.md" `
  --candidate "<候选完整文件>" `
  --summary "禁止把预览宣称为剪映最终导出" `
  --evidence EVID-... EVID-...
```

若只有一条低/中等级证据，但用户明确要求固化，加 `--explicit-user-request`；否则脚本会拒绝提案。

每个候选只解决一个可命名问题；默认最多改变 120 行。脚本保存基线哈希、候选全文和差异，不直接修改生产文件。

## 3. 留出验证

从 `../../templates/skill-optimization-eval.template.json` 复制验证文件。验证案例不能来自本候选引用的训练证据；至少包含 3 个案例，并覆盖一个正常路径、一个边界路径和一个邻近回归路径。

先让当前 Agent 分别按基线和候选执行或推演相同案例，把可检查结果填入 `baseline_pass`、`candidate_pass`。随后运行：

```powershell
uv run --project "<合集根>" python "<合集根>/scripts/video-skill-optimize/optimize.py" gate `
  --proposal PROP-... --evaluation "<留出验证.json>"
```

只有同时满足以下条件才通过：候选总分严格高于基线；没有基线通过而候选失败的回退；所有关键案例通过；候选结构有效；修改未超预算。失败候选保留在拒绝缓冲区，用于后续避免重复尝试。

## 4. 人工采纳

先向用户展示证据、目标文件、主要差异、基线/候选得分和残余风险。只有用户明确说“采纳/应用这个优化”后执行：

```powershell
uv run --project "<合集根>" python "<合集根>/scripts/video-skill-optimize/optimize.py" adopt `
  --proposal PROP-... --confirm "ADOPT:PROP-...:<候选哈希前12位>"
```

采纳前再次检查目标哈希；若基线后目标已变化则阻塞，必须重建候选。脚本先备份再原子替换。

## 禁止

- 不因单次偏好自动重写全局 Skill；
- 不把聊天全文、思维过程、工具参数/输出或秘密写入证据；
- 不使用参与生成候选的同一案例充当留出验证；
- 不为提高一个指标而删除 Raw 只读、许可证、审批或最终交付边界；
- 不自动采纳，即使 gate 通过；
- 不优化本优化器自身；其变更走普通人工审查。
