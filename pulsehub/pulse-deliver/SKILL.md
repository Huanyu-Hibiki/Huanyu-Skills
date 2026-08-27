---
name: pulse-deliver
description: Format engagement opportunities into a clickable Markdown report. Deduplicates against history, suggests comment angles, computes time windows. Use when you need a final actionable list. 输出可点击清单、去重、建议评论角度、计算时间窗口。
---

# pulse-deliver · 交付报告

把一批 `Opportunity` 对象渲染成用户**可以直接行动的可点击 Markdown 报告**。

本 skill 是 4 段流水线的**第 4 段**，也是最终输出——用户看到的就是它。

## 何时使用

- 手里有一个或多个 `Opportunity` 对象要展示给用户
- 用户说"**给我一份待评论清单**"
- 用户说"**今天有什么值得互动的**"
- `pulse-enrich` 跑完，需要呈现结果

触发词：**deliver, report, list, show, format, 输出, 报告, 清单, 列表**

## 何时不用

- 用户要**原始 JSON** → 直接打印 Opportunity 对象
- 用户想**发现更多** → 回 `pulse-discover`
- 用户想**重新评分** → 回 `pulse-enrich`

## 工作流

### Step 1 · 接收 Opportunities

输入：`Opportunity` 对象数组（`pulse-enrich` 的输出）。

### Step 2 · 去重

对照本地历史逐条检查：

```bash
# 状态库：~/.pulsehub/state/seen-urls.db (SQLite)
# 表结构：(platform, workId, firstSeenAt, lastShownAt)
```

跳过最近 7 天内已展示过的 URL（窗口可配置）。

保留的 URL 更新 `lastShownAt`。

**Fallback（DB 不可用时）**：SQLite DB 不存在 / 无法写 → 改用文本去重：扫描 `~/.pulsehub/reports/*.md` 历史报告里的 URL，按 (platform, workId) 手动比对。首次运行无历史 → 提示用户"本次未去重（首次运行）"，从本次开始积累报告作为去重依据。

### Step 3 · 计算时间窗口

对每个机会计算"最佳评论窗口"，依据：

- 元数据里的 `publishedAt`
- 平台互动曲线（发布后前 30 分钟内的评论曝光约 10 倍）
- 当前时间

输出：`bestWindowMin`（距发布时间的分钟数，如 30 = "发布后 30 分钟内最佳"）。

已过窗口 → 标记 "late"，但仍然列出。

### Step 4 · 建议评论角度

对每个机会生成一个**建议**（不是成品评论）：

```text
opportunity: {
  title: "想买个无线耳机求推荐",
  signals: { purchaseIntent: true }
}

suggestedAngle: "提你产品的降噪+续航。问对方预算来确认线索质量。
                 不要甩裸链接——让对方先追问。"
```

**关键**：建议只是角度，不是成品评论。用户必须用自己的口吻重写。

### Step 5 · 渲染 Markdown

按下面的模板渲染（**渲染由 AI 按模板直接完成，无独立 renderer 程序**）：

```markdown
# 待评论清单 — 2026-07-27

> 找到 12 个机会（高 3 / 中 6 / 低 3）。已去重，未展示 2 个最近 7 天看过的。

## 🔥 高价值（3）

### 1. 小红书：想买个无线耳机求推荐
- **URL**: [点击打开](https://www.xiaohongshu.com/explore/65f8e7ab...?xsec_token=ABxyz...)
- **作者**: @数码小白
- **发布时间**: 25 分钟前
- **信号**: 求购（"求推荐"）、问题（"预算 500 以内"）
- **评论角度**: 提降噪 + 续航，问预算，不直接甩链接
- **⏰ 时间窗口**: 还有 5 分钟（30 分钟内最佳）
- **评分理由**: 强购买意向，预算明确，时间新鲜

### 2. 抖音：xxx
- ...

## 🟡 中价值（6）
...

## 🔵 低价值（3）
...
```

### Step 6 · 输出

按场景选输出通道：

| 场景 | 输出到 |
|---------|-----------|
| 聊天 / 交互式 | 直接在对话里打印 Markdown |
| 批量 / 定时任务 | 写入 `~/.pulsehub/reports/YYYY-MM-DD-HH.md` |
| 用户指定文件 | 写到指定路径 |
| API / 程序化 | 返回 JSON Report 对象 |

## 示例

### 示例 1：聊天内报告

**用户**："今天有什么值得评论的？"

```
1. （假设 discover → resolve → enrich 已跑完）
2. pulse-deliver 收到 12 个 Opportunity
3. 去重：2 个最近 7 天已展示
4. 渲染 Markdown：10 个机会按评分分组
5. 打印到对话
```

### 示例 2：定时报告

**用户**："每天早上 9 点给我一份小红书待评论清单"

```
1. （cron / 调度器触发）
2. pulse-discover 以 topic_search 模式搜跟踪关键词
3. pulse-resolve 标准化所有 URL
4. pulse-enrich 补全 + 评分
5. pulse-deliver → 写入 ~/.pulsehub/reports/2026-07-27-09.md
6. （可选）webhook 通知用户
```

### 示例 3：过滤视图

**用户**："只看高价值的"

```
1. pulse-deliver 加过滤条件：score === 'high'
2. 只渲染 🔥 段
3. 跳过 🟡 和 🔵
```

## 输出格式硬约束

- **URL 必须可点击**——保留 `xsec_token` 和所有必要参数
- **Markdown 必须在标准查看器里正常渲染**——不用私有扩展
- **时间窗口必须显眼**——用 ⏰ emoji + 绝对时间
- **评论角度只能是建议**——绝不给成品评论
- **绝不输出可直接复制粘贴的自动评论**

## 重要说明

- **去重是本地的**——无云端、无同步，每个用户自己的历史
- **状态库只追加**——可以从历史重建报告
- **时间窗口是估算**——基于平台互动曲线，不是精确科学

## 不要做

- **绝不输出成品评论**——角度建议必须由用户用自己的口吻重写后才可用
- **不丢 URL 参数**——`xsec_token` 等参数丢了链接就废
- **不假装时间窗口**——已过窗口如实标 late，不伪造紧迫感

## 失败分支

| 触发条件 | 一线处理 | 仍失败兜底 |
|---------|---------|-----------|
| Opportunity 输入为空 | 回上游检查 enrich 是否产出 | 无机会 ≠ 报错——输出"今日无新机会"正常报告 |
| 写报告目录失败（`~/.pulsehub/reports/` 建不了） | 手工创建目录重试 | 降级为聊天内直接输出 Markdown，提示用户目录问题 |
| 时间窗口已过（全部 late） | 如实标 ⏰ 已过窗口 | 仍列出但排到低价值区，不假装还在窗口内 |

## 工具速查

| 工具 | 位置 | 用途 |
|------|----------|---------|
| Renderer | AI 按本文件 Step 5 模板直接渲染（无独立程序） | Markdown 渲染 |
| State DB | `~/.pulsehub/state/seen-urls.db` | 去重（不可用时见 Step 2 Fallback） |
| 报告模板 | 本文件 Step 5 内嵌模板 | 输出格式 |
