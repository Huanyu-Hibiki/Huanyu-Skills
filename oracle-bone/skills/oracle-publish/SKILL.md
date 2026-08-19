---
name: oracle-publish
description: 登记一篇内容已发布，把 URL/平台/发布时间写入对应预测文件 header 和 state。轻量动作——只更新元数据，**不动预测段任何字符**。含发布前合规 gate。触发词："已发布"/"I shipped"/"发布链接是 X"/"刚发完 [url]"/"publish registered"。
argument-hint: "<prediction-file-or-url> [— platform: <name>]"
allowed-tools: Bash(*), Read, Edit, Glob
---

# /oracle-publish — 发布登记

把发布元数据补到预测文件 header 与 state。**禁止改预测段**——hook 会拦。

`oracle-publish` 严格只用于「已实际发到平台且有真实 URL」。预测落盘 ≠ 发布，scheduled ≠ 发布，制作完 ≠ 发布。

## Overview

```
[用户：已发布 https://...]
  ↓
[Phase 0.5: 发布前合规 gate（oracle-compliance 快扫）]
  ↓
[Phase 1: 定位项目根 + 找到对应预测文件]
  ↓
[Phase 2: 解析 URL → 平台 + 问实际发布日（≠ 登记日）]
  ↓
[Phase 3: 更新 prediction header（仅 metadata 段）]
  ↓
[Phase 4: 更新 state（多平台表 + shoots 清队 + pending_retros 窗口表）]
  ↓
[Phase 5: 提醒（盲度警告 + 复盘日程 + 置顶评论触发）]
```

## Constants

- **AUTO_DETECT_PLATFORM = true** — URL 模式自动识别
- **VERIFY_BLIND = true** — 提醒用户从此刻起看到任何数据都破坏盲度声明诚信

## Workflow

### Phase 0.5: 发布前合规 gate

按 [oracle-compliance](../oracle-compliance/SKILL.md) 的清单快扫定稿 + 发布文案：
- 🔴 高危（竞品平台名口播 / 站外导流 / 敏感词）≥1 处 → 警告"发现 N 处高危限流风险，建议修改后再发布。仍要登记吗？"→ 用户确认才继续
- 🟡 中危 ≥3 处 → 轻量提示，不阻塞
- 通过 → 正常进 Phase 1

用户强制跳过 → state 标 `compliance_scan: skipped`（retro 发现低播放时优先检查是否限流）。

### Phase 1: 定位项目根 + 找预测文件

**项目根**：从当前目录向上找 `.oracle-state.json`；找不到 → 按已知项目根路径列表验证；都没有 → 一次定向搜索后询问用户（**不从 home 盲目 find**）。

**Step 1a: 链接自动解析（有 URL 时优先跑）**：

用户粘 1-N 条链接（可以一次给多平台多条）→ 跑：

```bash
python <skill包>/tools/link_resolver.py auto "<url1>" "<url2>" --project <项目根>
```

自动完成三件事：
1. **短链解析**：`v.douyin.com/x` / `b23.tv/x` / `xhslink.com/x` → 跟随重定向拿真实 URL
2. **平台识别 + 内容 ID 提取**：URL 模式解析（BV 号 / aweme_id / note_id…），B站走公开 API 最稳
3. **标题抓取 + 作品匹配**：HTML `<title>`/`og:title` 抓标题（清平台后缀）→ difflib 模糊匹配 shoots 队列 + 无 `Published at` 的 prediction → 输出确认表

```
🔗 链接解析 + 作品匹配

✅ [1] bilibili · ID=BV1ab2cd3ef4
     标题: 张三审合同的五个坑
     → 匹配: 004_合同审查的坑（prediction，score=0.58）⭐
⚠️ [2] wechat · ID=pending
     标题:（未取到——页面反爬或需客户端打开）

确认匹配请回编号+作品名；匹配错请纠正；标题缺失请补一句。
```

**纪律**：
- score ≥0.55 标 ⭐ 但**仍需用户确认**——匹配是建议不是决定（协作契约 #8）
- 标题抓取失败（反爬/需客户端）→ 平台和 ID 已有，标题问用户要一句即可，**不阻塞**
- 多条链接匹配到同一作品 → 正常（多平台分发），逐平台登记 per-platform 表
- link_resolver 全挂（无网络）→ 回退 Step 1b 手动流程

**Step 1b: 手动定位（无 URL / 解析失败时）**：

**找预测文件**（按优先级）：
1. 用户给了 prediction 路径 → 直接用
2. **link_resolver 已匹配**（Step 1a）→ 用匹配结果的 prediction_file
3. 只给 URL → 读 `in_progress_session.file`
4. `in_progress_session = null` → 检查 state 里最近 `scheduled`/多平台未补齐的作品记录，自动定位（**多平台补链接**：用户一次给多个链接 + 最近作品部分平台已登记 → 自动匹配未补齐的平台，不停下来问）
5. 都没有 → 列出 header 没填 `published_at` 的 prediction 让用户选

时间差 >14 天 → 提示"这个预测写于很久之前，确认是这篇？"

### Phase 2: 解析平台 + 实际发布日

**Platform ID**：link_resolver 解析的 content_id 直接用（BV号/note_id/aweme_id）；短链无法解析时标 pending，下次 retro 由 adapter 补。

| URL 模式 | 平台 |
|---|---|
| `youtube.com` `youtu.be` | youtube |
| `bilibili.com` `b23.tv` | bilibili |
| `douyin.com` `iesdouyin.com` `v.douyin.com` | douyin |
| `xiaohongshu.com` `xhslink.com` | xhs |
| `mp.weixin.qq.com` / `channels.weixin.qq.com` | wechat |
| `substack.com` / `medium.com` / `twitter.com` `x.com` | substack / medium / twitter |
| 其他 | unknown — 询问 |

**实际发布日（硬规则）**：登记 `published_at` 前**必须问**"实际是哪天点的发布？"——**绝不默认登记日**。发布日错一天，retro 窗口全错。
- 用户消息已明确说"X 日发布" → 各平台默认同 X，**不逐平台再问**（除非 URL 文本里有明显冲突 → 一句话确认一次）
- 分日发布 → 逐平台问
- 回答含糊（"前两天"）→ 追问具体日期
- 平台信息里能看到实际时间戳 → 交叉核验

### Phase 3: 更新 prediction header

**只动文件最顶部 metadata 块**（第一个 `##` 之前），用 Edit 不用 Write。已有字段 → 警告"已登记过"，询问是否覆盖（绝不静默覆盖）：

```markdown
**Published at**: 2026-05-04T14:32:00+08:00
**Platform**: douyin
**URL**: https://v.douyin.com/abc123
**Work Folder**: <NNN>_<标题>/
**Platform ID**: <平台内容 ID（BV号/note_id/video_id 等，短链无法解析时标 pending）>
**Track**: <从 in_progress_session.track 继承>
```

作品目录不存在 → 警告"跳过了 oracle-shoot？"，询问跳过登记直接发（自动建目录 + 标 `ad_hoc_publish: true`，并至少复制 script 摘要到 `scripts/script.lost.md` 让 retro 有东西可读）或先补 shoot。

hook 行为预期：只动 metadata 段应放行。hook 误拦 → 报 bug，**不绕过 hook**。

### Phase 4: 更新 state

```json
{
  "in_progress_session": null,
  "last_published_at": "<最晚平台时间>",
  "last_published_file": "<NNN>_<标题>/predictions/<...>.md",
  "pending_retros": [
    {
      "file": "<NNN>_<标题>/predictions/<...>.md",
      "track": "<轨道 id>",
      "published_at_per_platform": { "douyin": "<ISO>", "bilibili": "<ISO>" },
      "due_windows": [
        { "days": 3, "due_at": "<ISO>", "done": false },
        { "days": 7, "due_at": "<ISO>", "done": false },
        { "days": 30, "due_at": "<ISO>", "done": false }
      ]
    }
  ],
  "shoots": [/* 移除对应项 */]
}
```

**关键规则**：
1. `due_windows` 按该轨 `retro_windows_days` 生成（流量轨 [3]，转化轨 [3,7,30]）——oracle-status 按 due_at 显示"今天该复盘哪些"
2. `last_published_at` 用**最晚平台**时间（与"最新发布"语义一致）
3. **每发一个平台就调一次 oracle-publish**——retro 窗口从各平台独立起算，不要攒到全发完
4. **shoots 清队是硬步骤**——读 shoots，移除 work_folder 匹配项；没找到 → 警告"队列里没有这条。是直接发布没经过 shoot 吗？"（不阻塞）。跳过 publish 登记 → shoots 堆积 → buffer 虚高 → 用户看到错误数字（最伤信任的失败模式之一）

### Phase 5: 提醒 + 下一步

```
✅ 登记完成：<NNN>_<标题>/predictions/<...>.md
   - Published at: <实际发布日> / Platform: douyin / URL: ...

📦 Buffer：N 篇（颜色 + 含义）[颜色变化 → 行动建议]

⚠️  从此刻起，你看到任何关于这条作品的数据都会破坏盲度声明的诚信。
    不小心看到 → 告诉我，我在文件里追加 integrity warning。

📌 发布后 5 分钟内：跑 /oracle-pinned-comment 生成置顶评论（趁算法推第一批观众前撑起评论氛围）
📅 计划复盘：<按该轨窗口列出 T+3d / T+7d / T+30d 日期>
   到时间说："复盘 <NNN>_<标题>"
[每 2 期已复盘作品后] /oracle-compass-retro 罗盘复盘到期
```

## Key Rules

1. **不动预测段**——即使修复笔误也不在 publish 时改
2. **不抓数据**——登记动作，数据回收是 oracle-retro 的活
3. **实际发布日 ≠ 登记日**——必须问
4. **重复登记需明示**——绝不静默覆盖
5. **shoots 清队不跳**——buffer 准确性依赖它

## Refusals

- 「我顺手把预测段也改一下」 → 拒绝。走 `_redo.md` 路径
- 「URL 等会补，先记时间」 → 允许（URL 可后补；published_at + platform 必填）
- 「跳过 metadata 更新，直接清 in_progress_session」 → 拒绝。元数据是复盘关键上下文

## 已知坑（实战教训压缩版）

| 坑 | 正解 |
|---|---|
| 发布后没跑 publish → state 滞后 → retro 校验失败 | publish 是必跑步骤；retro 检测到滞后可走 publish 补登记 |
| 多平台只用一个 last_published_at → 其他平台窗口算错 | per-platform 表 + 每平台独立调 publish |
| 登记日冒充发布日 → retro 窗口整体顺延 | 问实际发布日，绝不默认今天 |
| shoots 残留 → buffer 虚高 → 错误建议 | 每次 publish 必清队；oracle-shoot 也有交叉校验，两边防 |

## Integration

- 上游：oracle-shoot（shoots 队列来源）
- 下游：oracle-pinned-comment（发布后即时）→ oracle-retro（窗口到期，按 due_windows）→ 每 2 期 oracle-compass-retro
- oracle-status 用 pending_retros 算"今天该复盘哪些"；平台字段路由 retro 的 perf adapter
