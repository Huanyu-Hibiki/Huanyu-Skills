---
name: pulse-resolve
description: Normalize Chinese social media URLs. Resolves short links, extracts platform-native work IDs, preserves critical tokens like xsec_token. Use when user provides a messy URL or you need to deduplicate posts. 标准化URL、短链展开、提取作品ID、保留token。
---

# pulse-resolve · URL 标准化

把任意中文社媒 URL 规范化为统一的 `ResolvedLink` 结构。

本 skill 是 4 段流水线的**第 2 段**：接收原始 URL（短链/分享链/移动端链），产出可用于 enrich 和去重的标准化结构。

## 何时使用

- 拿到一个原始 URL，需要判断它属于**哪个平台**
- 需要**展开短链**（`b23.tv`、`v.douyin.com`、`xhslink.com`）
- 需要**提取作品 ID**（BV 号、笔记 ID 等）
- 需要**保留 token**（尤其是小红书的 `xsec_token`）
- 需要**去重**（同一篇帖子经不同短链分享）

触发词：**resolve, normalize, parse, expand, extract, 标准化, 解析, 展开, 提取**

## 何时不用

- 用户想**发现新内容** → 用 `pulse-discover`
- 用户想要某个 URL 的**元数据** → 用 `pulse-enrich`（内部会调 resolve）
- 用户想要**最终报告** → 用 `pulse-deliver`

## 工作流

### Step 1 · 接收原始 URL

URL 可能来自：

- 用户消息（单个 URL）
- `pulse-discover` 的输出（URL 列表）
- 文件（`--input urls.txt`）
- 标准输入（管道传入）

### Step 2 · 运行 pulse-resolve CLI

```bash
# 单个 URL — 在 _core/pulse-resolve/ 目录下执行（需要 pnpm + node_modules）
pnpm --filter pulse-resolve dev -- "https://xhslink.com/a/abc123"

# 从文件批量
pnpm --filter pulse-resolve dev -- --input urls.txt --output resolved.json

# 标准输入管道
echo "https://v.douyin.com/abc123/" | pnpm --filter pulse-resolve dev -- --stdin
```

**Fallback（CLI 跑不了时）**：缺 pnpm / node_modules / 超时 → 按「平台专属行为」表的 URL 模式**手工解析**（短链让用户在浏览器打开后把最终 URL 贴回来）。解析不出平台 → 输出 `platform: "unknown"`，**不要猜**。在结果里注明 `manual_parse`。

### Step 3 · 接收 ResolvedLink

输出是 `ResolvedLink` 对象的 JSON 数组：

```json
[
  {
    "platform": "rednote",
    "workId": "65f8e7ab000000000d00aabc",
    "url": "https://www.xiaohongshu.com/explore/65f8e7ab000000000d00aabc?xsec_token=ABxyz...",
    "originalLink": "https://xhslink.com/a/abc123",
    "token": { "xsec_token": "ABxyz..." },
    "resolvedAt": "2026-07-27T10:30:00.000Z"
  }
]
```

### Step 4 · 交接

把每个 `ResolvedLink` 交给 `pulse-enrich` 做元数据补全 + 评分。

## 平台专属行为

### B站（Bilibili）
- 接受：`bilibili.com/video/BVxxx`、`m.bilibili.com/video/BVxxx`、`b23.tv/xxx`（短链）
- ID 格式：`BV[0-9A-Z]+` 或 `av\d+`
- Token：无需
- 规范形：`https://www.bilibili.com/video/{BVid}`

### 抖音（Douyin）
- 接受：`douyin.com/video/{id}`、`douyin.com/note/{id}`（图文）、`douyin.com/?modal_id={id}`、`iesdouyin.com/share/video/{id}`、`v.douyin.com/xxx`（短链）
- ID 格式：纯数字串
- Token：无需
- 规范形：`https://www.douyin.com/video/{id}` 或 `https://www.douyin.com/note/{id}`

### 小红书（RedNote）⭐ 关键
- 接受：`xiaohongshu.com/explore/{noteId}`、`/red_video/{noteId}`、`/discovery/item/{noteId}`、`/user/profile/{uid}?xsec_token=xxx`、`xhslink.com/xxx`（短链）
- ID 格式：24 位十六进制
- **Token：`xsec_token` 必需**——没有它 URL 返回 403
- 规范形：`https://www.xiaohongshu.com/explore/{noteId}?xsec_token={token}`

### 微信公众号（WeChat Official）
- 接受：公众号文章 URL（`mp.weixin.qq.com/s/xxx`）
- ID 格式：文章 slug
- Token：无需（文章 URL 公开）
- 规范形：URL 原样

### 微信视频号（WeChat Channels）
- 接受：视频号 finder 主页 URL（需扫码登录）
- ID 格式：finder_id + video_id 组合
- Token：登录态 cookie（由 Chrome MCP 处理，不在 URL 里）
- 规范形：`https://channels.weixin.qq.com/web/video/<finder_id>/<video_id>`

### 知乎（Zhihu）
- 接受：`zhihu.com/question/{qid}/answer/{aid}`、`zhuanlan.zhihu.com/p/{pid}`
- ID 格式：问题/回答/专栏文章 ID
- Token：公开内容无需
- 规范形：URL 原样

## 示例

### 示例 1：单个短链

**用户**："这个链接是什么 https://xhslink.com/a/abc123"

```
1. 运行：pulse-resolve "https://xhslink.com/a/abc123"
2. CLI 跟随重定向 → https://www.xiaohongshu.com/explore/65f8e7ab...?xsec_token=ABxyz
3. 输出 ResolvedLink：platform=rednote, workId=65f8e7ab..., token.xsec_token=ABxyz
```

### 示例 2：批量解析 discover 输出

**用户**：（pulse-discover 返回 15 个 URL 之后）

```
1. 把 URL 存到 /tmp/candidates.txt
2. 运行：pulse-resolve --input /tmp/candidates.txt --output /tmp/resolved.json
3. 读 resolved.json → 12 个有效 ResolvedLink（3 个失败）
4. 交接给 pulse-enrich
```

### 示例 3：去重

**用户**："这 50 个 URL 里有没有重复的？"

```
1. 运行：pulse-resolve --input urls.txt --output resolved.json
2. 按 (platform, workId) 分组
3. 报告重复："URL #3 和 #17 是同一条抖音视频"
4. 可选：去重后再进入后续处理
```

## 实现说明

解析器**移植自 AiToEarn**（`apps/aitoearn-server/src/core/channels/platforms/<platform>/<platform>-work.provider.ts`），原代码 MIT 协议，解析逻辑版权归 AiToEarn 团队。

构建与贡献说明见 [`../_core/pulse-resolve/README.md`](../_core/pulse-resolve/)（相对本 skill 目录；仓库根基准下即 `_core/pulse-resolve/`）。

## 失败分支（必须按表处理）

| 触发条件 | 一线处理 | 仍失败兜底 |
|---------|---------|-----------|
| 短链展开超时 / 跳转链断 | 重试 1 次，间隔 5s | 请用户浏览器打开短链 → 贴最终 URL，手工按平台表解析 |
| URL 不匹配任何平台模式 | 输出 `platform: "unknown"` | 不猜平台；批量场景单独列出，交给用户判断 |
| RedNote 链接无 `xsec_token` | 标记 `token: missing` | **不要**伪造/复用其他帖的 token——下游 enrich 会 403，如实标记让用户回到帖子分享带 token 的链接 |
| CLI 报依赖错误（pnpm/modules 缺失） | 检查 `_core/pulse-resolve/` 是否已 install | 切手工解析模式（见 Step 2 Fallback），结果标 `manual_parse` |
| 批量输入部分失败 | 成功的照常输出 | 失败项逐条列原因，不因部分失败丢弃整批 |

## 不要做

- **不要丢 query 参数**——小红书的 `xsec_token`、B站的 `p` 分集参数丢了链接就废
- **不要猜平台**——`unknown` 就输出 unknown，下游会分流处理
- **不要静默丢弃失败 URL**——每个失败都要有原因
- **不要伪造 token**——403 的链接标记后交还用户，不是 AI 该修的

## 工具速查

| 工具 | 位置 | 用途 |
|------|----------|---------|
| `pulse-resolve` CLI | `_core/pulse-resolve/` | URL 标准化（不可用时见「失败分支」手工解析） |
