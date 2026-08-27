---
name: pulse-discover
description: Find raw Signals (URLs) from Chinese social platforms. Use when user wants to discover comment opportunities, monitor competitors, track topics, or watch trending content. 发现评论机会、监控竞品、追话题、找热门、采集URL。
---

# pulse-discover · 发现帖子

从中文社媒平台找原始信号——那些**可能**代表互动机会的 URL。

本 skill 是 4 段流水线的**第 1 段**。它的输出（原始 URL）交给 `pulse-resolve` 处理。

## 何时使用

用户想：

- 在特定平台找评论机会
- 监控竞品的新帖
- 跨平台追踪关键词/话题
- 看自己赛道里什么在火
- 盯购买意向信号（求链接 / 怎么买 / 价格）

触发词：**discover, find, monitor, watch, track, trending, 发现, 监控, 追, 找, 采集**

## 何时不用

- 用户要**标准化某个具体 URL** → 直接用 `pulse-resolve`
- 用户要给已有 URL **补元数据** → 用 `pulse-enrich`
- 用户要**最终报告** → 用 `pulse-deliver`
- 用户要**自动发布或自动评论** → 拒绝并提示风控风险

## 工作流

### Step 1 · 确定发现模式

问用户（或从意图推断）选哪个模式：

| 模式 | 触发示例 | 要读的 recipe |
|------|----------------|----------------|
| `topic_search` | "找关于无线耳机的笔记" | `_shared/recipes/<平台>.md` → 「Example Workflows」里的话题搜索 Workflow |
| `competitor_watch` | "看看 @xxx 今天发了什么" | `_shared/recipes/<平台>.md` → 竞品监控 Workflow |
| `own_comments` | "看看谁评论了我的视频" | `_shared/recipes/<平台>.md` → 自己评论监控 Workflow（部分平台无此 Workflow → 走竞品监控的 URL 模式反向套用） |
| `trending` | "今天 B 站热门是什么" | `_shared/recipes/<平台>.md` → 热门/趋势 Workflow |

> 各平台的 Workflow 编号不同（小红书 A=话题搜索，B站 A=竞品监控）——**读文件按标题匹配**，不要按编号猜。

路径基准：`_shared/` 是 PulseHub 仓库根的共享资源目录（recipes / scripts / signals）。**recipe 文件缺失 → 降级为 RSSHub 路由猜测 + Chrome DevTools 直接打开平台搜索页，并告知用户该平台 recipe 缺失**。

### Step 2 · 选发现源

按平台 recipe，选一个或多个：

| 发现源 | 工具 | 什么时候用 |
|--------|------|-------------|
| RSSHub | `_shared/scripts/shell/rsshub-fetch.sh` | 公开订阅数据（无需登录） |
| **知乎 API** | `references/zhihu-search-api.md` | **知乎搜索首选**——官方 API，不反爬，自带内容摘要，无需登录态 |
| Chrome DevTools MCP | MCP server（直连） | 搜索结果页、需登录态的页面（**遇到登录墙/验证码立刻停下让用户处理，见 P1**） |
| 搜索引擎 | `jina-reader` / `firecrawl` | 通用网页搜索 |

**优先 RSSHub**——更安全（无账号风险）更快。
**知乎优先官方 API**——scraping 知乎网页会触发 40362 反爬限制。

### Step 3 · 执行发现

按 recipe 调对应工具。小红书话题搜索示例：

```bash
# 走 RSSHub（首选）— 从 PulseHub 仓库根执行
bash _shared/scripts/shell/rsshub-fetch.sh "/xiaohongshu/search/notes?keyword=无线耳机"

# 或走 Chrome DevTools MCP（RSSHub 路由不可用时）
# → 打开 https://www.xiaohongshu.com/search_result?keyword=无线耳机
# → 等网络空闲
# → 从页面 DOM 提取笔记 URL
```

### Step 4 · 输出原始 URL

输出原始 URL 列表。不标准化、不补元数据，只收集。

```json
{
  "mode": "topic_search",
  "platform": "rednote",
  "query": "无线耳机",
  "candidates": [
    "https://www.xiaohongshu.com/explore/65f8e7ab...?xsec_token=ABxyz...",
    "https://xhslink.com/a/abc123",
    "https://www.xiaohongshu.com/discovery/item/65f9a1cd..."
  ],
  "discoveredAt": "2026-07-27T10:00:00Z"
}
```

**下一步**：把每个 URL 交给 `pulse-resolve`。

## 示例

### 示例 1：话题搜索

**用户**："找小红书上关于无线耳机的笔记，要能评论的那种"

```
1. 读 _shared/recipes/rednote.md 的话题搜索 Workflow（Workflow A: Topic Search）
2. 选源：RSSHub 路由 /xiaohongshu/search/notes
3. 运行：bash _shared/scripts/shell/rsshub-fetch.sh "/xiaohongshu/search/notes?keyword=无线耳机"
4. 收集 10-20 个候选 URL
5. 交接给 pulse-resolve
```

### 示例 2：竞品监控

**用户**："看看 @数码评测师 今天在 B 站发了什么"

```
1. 读 _shared/recipes/bilibili.md 的竞品监控 Workflow（Competitor Watch）
2. 需要 UP 主的 UID（通过搜索把用户名转 UID）
3. 运行：bash _shared/scripts/shell/rsshub-fetch.sh "/bilibili/user/dynamic/{uid}"
4. 从今天的动态里收集视频 URL
5. 交接给 pulse-resolve
```

### 示例 3：购买意向挖掘

**用户**："找找哪里有人在问无线耳机怎么买"

```
1. 这是带信号过滤的跨平台 topic_search
2. 对每个目标平台（小红书、抖音、B站、知乎）：
   a. 读 _shared/recipes/<平台>.md 的话题搜索 Workflow
   b. 搜关键词"无线耳机"
   c. 收集候选 URL
3. 全部 URL 交接给 pulse-resolve，再进 pulse-enrich（它负责检测购买意向）
```

## 重要规则

- **自我限流**：每平台每次会话最多 50 个 URL
- Chrome MCP 会话**用专用小号**
- RSSHub 和 Chrome MCP 都可用时**优先 RSSHub**
- **先读 recipe 再动手**——每个平台规则不同
- **绝不自动点击/滚动超出数据提取所需**的范围
- **多平台采集规则见 P6**——用户没指定单平台就默认跑全量，没跑完不进分析阶段

## Pitfalls

### P1. 遇到登录墙 / 验证码时停下来让用户处理（2026-08-05 用户强 correction）

**症状**：Chrome DevTools MCP 打开小红书搜索页 → 返回"登录后查看搜索结果"。AI 没有通知用户，而是自己切换到百度/Google/Bing 搜索引擎绕路 → 搜索引擎也跳验证码 → AI 又换工具…… 用户愤怒："你他妈就不能等一下啊，需要登录我登录，需要人机验证提示我验证不就行了？？？"

**正解**：🛑 遇到登录墙或人机验证，**立刻停下来告诉用户**："页面需要登录 / 需要过验证码，请在浏览器里处理一下"。等用户处理完再继续抓取。Chrome DevTools MCP 共享用户的 Chrome 登录态，用户手动登录后 session 就有了——这是正常流程，不是异常。

**原则**：登录和验证码是**用户该做的事**，不是 AI 该绕过的障碍。不要自作主张换工具链。

### P2. RSSHub 社交平台路由可能缺 Playwright 浏览器（2026-08-05 实证）

**症状**：RSSHub `/xiaohongshu/search/notes`、`/weibo/keyword` 等社交平台路由返回错误："browserType.launch: Executable doesn't exist"——RSSHub 服务账户（system profile）的 Playwright 浏览器路径不对。

**正解**：RSSHub 社交平台路由依赖 Playwright 浏览器。如果 RSSHub 以系统服务运行，需要给服务账户装 Playwright 浏览器，或改用 Chrome DevTools MCP（有用户登录态）作为 discovery source。RSSHub 的非社交路由（36氪、YouTube、B站等）不受影响。

### P3. Tavily 国内不稳定时用 Chrome DevTools 兜底（2026-08-05 实证）

**症状**：`web_search`（Tavily 后端）返回 `[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol`。代理 fake-ip 模式下尤其频繁。

**正解**：Tavily SSL 失败时，用 Chrome DevTools MCP 直接打开目标平台搜索页（如小红书 `/search_result?keyword=XXX`），用 `evaluate_script` 从 DOM 提取结果 URL。不要用百度/Google 搜索引擎中转——它们要么把结果藏在 JS 里（百度），要么跳验证码（Google）。

### P4. 逐条抓取时模拟人工节奏，避免反爬（2026-08-05 用户明确要求）

**症状**：连续快速打开 B站多个视频页 → 触发风控；小红书快速翻页 → 被限制。

**正解**：逐条抓正文时，**每条之间停 2-3 分钟**（用 `sleep 180`）。模拟人工浏览节奏。不要一次性连续打开 10+ 页面。用户原话："为了规避反爬，你不要一次性抓取特别多，抓取1条的时候停顿两三分钟再抓其他的内容，避免反爬，就是模拟人工真实浏览页面。"

**B站优先用 API**：`api.bilibili.com/x/web-interface/search/type` 返回完整标题/播放/弹幕/简介（见 `references/bilibili-search-api.md`），一次调用拿完搜索结果，不需要逐条点进去。只有需要单个视频的 `__INITIAL_STATE__` 详细 stat 时才逐条导航。

### P5. discover ≠ 分析+写稿——不要提前宣布完成（2026-08-05 用户两次强 correction）

**症状**：跑完 discover + resolve + enrich 后直接报告"核心任务完成"。用户愤怒："核心任务也没完成啊，你就说完成了？？现在只是获取数据，还没进行分析和写稿子呢。"

**正解**：discover → resolve → enrich 只是**数据采集层**。PulseHub 的完整链路是 `discover → resolve → enrich → 分析报告 → 写稿（按项目定制协议/档案定位）`。在 enrich 完成后，下一步是写分析报告（洞察/痛点/竞品/定位）和获客文案（档案声明的主平台形式），不是停下来说"完成"。只有用户明确说"这步够了"才能停。**不确定"核心任务"包含哪些子任务 → 先问用户确认范围，不要自己猜边界**。

### P6. 不许自作主张跳过平台（2026-08-05 用户强 correction）

**症状**：用户说"搜合同审查"。AI 跑了小红书+B站就直接跳到分析+写稿，跳过了知乎。用户愤怒："你又自作主张，还有知乎平台的呢？？你直接就分析了？？？？我也没说这个步骤完成了？"

**正解**：用户指定多平台采集时，**每个平台都必须跑完 discover → resolve → enrich**，才能进入分析阶段。跑完一个平台汇报一次，但不要在中间跳到下游步骤。用户没说"这步完成了"就不算完成。**宣布"核心任务完成"前，对照用户原始需求逐项核对**——没对齐就继续，别凭感觉收工。

## 工具速查

| 工具 | 位置 | 用途 |
|------|----------|---------|
| `rsshub-fetch.sh` | `_shared/scripts/shell/` | 抓 RSSHub 路由 |
| **知乎搜索 API** | `references/zhihu-search-api.md` | **知乎搜索首选**：官方 API，不反爬，自带摘要，5000 次/天免费 |
| **B站搜索 API** | `references/bilibili-search-api.md` | B站搜索首选：官方 API 拿干净元数据 |
| Chrome DevTools MCP | 外部 MCP server | 带登录态的浏览器自动化（遇登录墙停下见 P1） |
| `jina-reader` | 外部 API | 静态网页转 markdown |
| `firecrawl` | 外部 API | 通用网页提取 |
