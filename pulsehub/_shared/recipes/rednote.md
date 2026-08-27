# 小红书 (RedNote / Xiaohongshu) Recipe

> 所有其他 recipe 的参考模板。贡献新平台 recipe 时复制本文件结构。
> 命令基准：从 PulseHub 仓库根执行（`_shared/scripts/...`）。

## 平台画像

| 属性 | 值 |
|----------|-------|
| **登录模型** | Cookie（插件式）——无 OAuth |
| **公开访问** | 受限——多数页面需要 `xsec_token` URL 参数 |
| **限流** | 紧——单会话约 30 次页面浏览后出验证码 |
| **验证码类型** | 滑块验证 |
| **账号风险** | 高——只用小号，绝不用大号 |
| **最佳评论窗口** | 帖子发布后 0-30 分钟 |
| **桌面 vs 移动端** | 自动化优先桌面网页版 |

## URL 模式

### 规范 URL 格式

```
https://www.xiaohongshu.com/explore/{noteId}?xsec_token={token}
https://www.xiaohongshu.com/red_video/{noteId}?xsec_token={token}
https://www.xiaohongshu.com/discovery/item/{noteId}?xsec_token={token}
https://www.xiaohongshu.com/user/profile/{uid}?xsec_token={token}
```

**关键**：`xsec_token` 参数**必需**，没有它 URL 返回 403。这个 token 在用户分享帖子时生成——是小红书追踪深链引流的机制。

### 短链域名

- `xhslink.com/a/{base64slug}` —— 重定向到带 `xsec_token` 的规范 URL

### 作品 ID 格式

- 24 位十六进制串（MongoDB ObjectId 风格）
- 示例：`65f8e7ab000000000d00aabc`

### Token 提取

短链展开或解析分享 URL 后，从 query string 里取 `xsec_token`：

```typescript
const token = new URL(resolvedUrl).searchParams.get('xsec_token')
```

## 发现源

### 源 1：RSSHub（首选）✨

RSSHub 有多条小红书路由——无需登录，最安全。

| 模式 | RSSHub 路由 | 返回 |
|------|--------------|---------|
| `competitor_watch` | `/xiaohongshu/user/{uid}` | 用户最新笔记 |
| `topic_search` | `/xiaohongshu/search/notes?keyword={kw}` | 搜索结果 |
| `trending` | `/xiaohongshu/explore/{category}` | 分类热门 |

**用法**：

```bash
bash _shared/scripts/shell/rsshub-fetch.sh "/xiaohongshu/user/{uid}"
```

**注意**：
- 小红书改内部 API 时 RSSHub 路由可能失效
- 返回的元数据比登录态浏览少
- `xsec_token` 有时缺失 → 必须 fallback 到 Chrome MCP

### 源 2：Chrome DevTools MCP（需登录态）

RSSHub 不可用或需要更丰富数据时，用 Chrome MCP + 已登录的小号。

**准备**：
1. 打开 Chrome（非无痕模式）
2. 用专用小号登录
3. 关闭其他所有标签页
4. 连接 Chrome MCP server

**导航路径**：

| 意图 | URL |
|--------|-----|
| 话题搜索 | `https://www.xiaohongshu.com/search_result?keyword={kw}&source=web_explore_feed` |
| 用户主页 | `https://www.xiaohongshu.com/user/profile/{uid}` |
| 笔记详情 | `https://www.xiaohongshu.com/explore/{noteId}`（需要 xsec_token） |
| 热门 | `https://www.xiaohongshu.com/explore` |

**流程**：
1. `navigate` 到搜索 URL
2. `wait` 等 `networkidle`（3-5 秒）
3. `scroll` 下滑 3-5 次触发懒加载
4. `network_monitor` 抓 `/api/sns/web/v1/search/notes` 响应
5. 解析 JSON → `{noteId, xsec_token, title, ...}` 列表
6. 每个候选之间停 5-10 秒（防检测）再做下一个动作

### 源 3：搜索引擎关键词搜索

适合广度发现（不深挖）：

```bash
# firecrawl search
firecrawl search "site:xiaohongshu.com 无线耳机 求推荐"

# Bing（免费）
curl "https://www.bing.com/search?q=site%3Axiaohongshu.com+%E6%B1%82%E6%8E%A8%E8%8D%90"
```

信号密度低，但冷门话题有用。

## 信号词表

### 购买意向（高价值）🔥

- 求链接 / 求链接啊 / 链接呢
- 怎么买 / 哪里买 / 哪里能买
- 多少钱 / 价格 / 多少米
- 想要 / 想买 / 种草了
- 求同款 / 求型号
- 怎么下单 / 怎么付款

### 提问意向（中价值）🟡

- 求推荐 / 求安利
- 怎么选 / 哪个好
- 值得买吗 / 值不值
- 有用过的吗 / 有人试过吗
- 怎么用 / 怎么做

### 吐槽（跳过）❌

- 太贵了 / 不值
- 差评 / 翻车
- 退款 / 售后差
- 别买 / 别上当

### 热点标记（视语境）

- 爆款 / 上热门 / 热度爆棚
- 万赞 / 千评
- 病毒式 / 刷屏

## 风控规则

### 硬性上限

| 上限 | 值 |
|-------|-------|
| 单会话最大浏览量 | 30 |
| 每天最多会话数 | 3 |
| 动作间最小延迟 | 5s |
| 单会话最长时长 | 30 分钟 |
| 验证码触发即停 | 是——暂停 24h |

### 账号轮换

- **绝不**用大号
- 用专用小号，每周轮换
- 每个小号要像真人：头像、简介、5-10 条正常笔记
- 不在同一个 Chrome profile 上切号（用 `Browser Profiler`）

### 异常检测

看到以下任一情况立即停止：

- 滑块验证码
- "请输入手机号验证"提示
- 已登录却被重定向到登录页
- 查询正常但搜索结果为空
- HTTP 461 / 471（小红书反爬码）

## 示例 Workflow

### Workflow A：话题搜索（最常用）

**目标**：找"无线耳机"相关、强购买意向的最新帖子。

```
1.（先试 RSSHub）
   bash _shared/scripts/shell/rsshub-fetch.sh "/xiaohongshu/search/notes?keyword=无线耳机"

   ↓ RSSHub 返回有效结果（含 xsec_token）

2. 收集候选 URL

   ↓ RSSHub 失败或 token 缺失

2.（fallback 到 Chrome MCP）
   - navigate https://www.xiaohongshu.com/search_result?keyword=无线耳机
   - wait networkidle (5s)
   - scroll down 3 times
   - capture /api/sns/web/v1/search/notes response
   - extract noteId + xsec_token pairs

3. 对每个候选 URL：
   - pulse-resolve → ResolvedLink（确认 xsec_token 保留）
   - pulse-enrich → Opportunity（元数据 + 信号）
   - 评分：purchaseIntent=true 且 publishedAt < 60min → high

4. pulse-deliver → Markdown 报告
```

### Workflow B：竞品监控

**目标**：监控竞品 @xxx 的最新笔记。

```
1. 解析竞品 UID
   - 搜索引擎搜 "xxx 小红书"
   - 或浏览其主页从 URL 提取 UID

2.（试 RSSHub）
   bash _shared/scripts/shell/rsshub-fetch.sh "/xiaohongshu/user/{uid}"

3. 过滤最近 24h 发布的笔记

4. 对每条新笔记：
   - pulse-resolve
   - pulse-enrich（重点：可差异化的评论角度）

5. pulse-deliver → "竞品动态报告"
```

### Workflow C：自己评论监控

**目标**：看谁评论了（小号发出的）你的帖子。

```
1. 必须 Chrome MCP（RSSHub 不暴露这个）

2. navigate https://www.xiaohongshu.com/user/profile/{your_uid}

3. 对你最近的每条笔记：
   a. navigate 到笔记详情页
   b. wait 评论加载
   c. capture /api/sns/web/v1/comment/page response
   d. 解析评论

4. 过滤评论文本中的购买意向信号

5. pulse-deliver → "你的帖子——待回复"
```

## 常见 Pitfalls

### ❌ 不要丢 `xsec_token`

错：
```
https://www.xiaohongshu.com/explore/65f8e7ab...  ← 403
```

对：
```
https://www.xiaohongshu.com/explore/65f8e7ab...?xsec_token=ABxyz...  ← 可用
```

### ❌ 不要用无痕模式

无痕没有 cookie → 小红书把每个请求当"未知设备首访" → 5 次请求内出验证码。

### ❌ 不要滚动太快

`scroll` 间隔 < 1s 触发懒加载滥用检测。两次滚动之间至少等 2-3s。

### ❌ 不要把同一个 xsec_token 用到很多笔记上

每次分享生成唯一 token。如果很多 URL 上看到同一个 token，你看到的很可能是爬来的脏数据，不是真实用户分享。

## 工具速查

| 工具 | 用途 |
|------|------|
| `rsshub-fetch.sh` | RSSHub 路由抓取 |
| Chrome DevTools MCP | 登录态浏览 |
| `pulse-resolve` CLI | URL 标准化（保留 xsec_token） |
| `yt-dlp` | 小红书视频笔记元数据 |
| `whisper-transcribe` | 视频笔记转录 |
