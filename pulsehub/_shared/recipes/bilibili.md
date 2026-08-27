# 哔哩哔哩 (Bilibili) Recipe

> 结构移植自 [`rednote.md`](rednote.md)。B站是中文大平台里最宽容的。
> 命令基准：从 PulseHub 仓库根执行（`_shared/scripts/...`）。

## 平台画像

| 属性 | 值 |
|----------|-------|
| **登录模型** | AiToEarn 走 OAuth2；RSSHub / Chrome MCP **公开可读** |
| **公开访问** | 高——多数页面不登录也能读 |
| **限流** | 宽松（限流前约 100 请求/分钟） |
| **验证码类型** | 滑块——只读场景很少触发 |
| **账号风险** | 低——互动仍建议小号；纯只读调研可用大号 |
| **最佳评论窗口** | 0-6 小时（比小红书长，B站用户浏览节奏慢） |
| **桌面 vs 移动端** | 优先桌面网页版（`www.bilibili.com`）；移动站数据少 |
| **Cookie 有效期** | 登录态功能约 30 天 |

## URL 模式

### 规范 URL 格式

```
https://www.bilibili.com/video/{BVid}                    # 桌面
https://m.bilibili.com/video/{BVid}                      # 移动
https://www.bilibili.com/video/av{avid}                  # 旧版（自动重定向到 BV）
https://www.bilibili.com/bangumi/play/{epid}             # 番剧（路径不同，暂不支持）
```

### 短链域名

- `b23.tv/{slug}` —— 通用短链（HTTP 302 重定向到规范 URL）

### 作品 ID 格式

- **BV**（现行）：`BV` + 10 位 `[0-9A-Za-z]`，如 `BV1xx411c7mD`
- **av**（旧版）：`av` + 数字 ID，如 `av987654` —— 自动重定向到对应 BV
- **ep**（番剧）：`ep` + 数字——内容类型不同，暂不解析

### Token

无需。B站视频 URL 完全公开。

## 发现源

### 源 1：RSSHub（首选）✨

B站是中文平台里 **RSSHub 覆盖最全**的。

| 模式 | RSSHub 路由 | 返回 |
|------|--------------|---------|
| `competitor_watch` | `/bilibili/user/dynamic/{uid}` | UP 的近期动态（视频+帖子+转发） |
| `competitor_watch` | `/bilibili/user/video/{uid}` | 仅 UP 投稿视频（信号更干净） |
| `topic_search` | （无直连路由——用 Chrome MCP） | — |
| `trending` | `/bilibili/popular/all` | 全站热门（每小时更新） |
| `trending` | `/bilibili/ranking/0/3/1` | 全站排行榜（每日） |
| `trending` | `/bilibili/part/ranking/{tid}/3/1` | 分区排行榜 |
| `follow_feed` | `/bilibili/user/topic/{uid}/{topic_id}` | UP 的特定合集/话题 |

**用户名转 UID**：

```
# 方案 A：RSSHub 搜索
bash _shared/scripts/shell/rsshub-fetch.sh "/bilibili/search/keyword/{keyword}"

# 方案 B：从 B站搜索页抓
# https://search.bilibili.com/upuser?keyword={username}
```

**用法示例**：

```bash
# 监控某个 UP 的新视频
bash _shared/scripts/shell/rsshub-fetch.sh "/bilibili/user/video/208259"

# 拉今日热门
bash _shared/scripts/shell/rsshub-fetch.sh "/bilibili/popular/all"
```

### 源 2：Chrome DevTools MCP

RSSHub 不可用或需要更丰富数据时：

| 意图 | URL |
|--------|-----|
| 搜视频 | `https://search.bilibili.com/all?keyword={kw}` |
| 搜 UP | `https://search.bilibili.com/upuser?keyword={kw}` |
| UP 主页 | `https://space.bilibili.com/{uid}/video` |
| 视频页 | `https://www.bilibili.com/video/{BVid}` |
| 热门 | `https://www.bilibili.com/v/popular/all` |

**流程**（登录小号）：
1. `navigate` 到搜索 URL
2. `wait` 等 `networkidle`（2-3 秒）
3. `network_monitor` 抓 `/x/web-interface/wbi/search/type` 响应
4. 解析 JSON → `{bvid, title, author, play, like, ...}`

### 源 3：搜索引擎

```bash
# firecrawl
firecrawl search "site:bilibili.com 无线耳机 测评"

# Bing
curl "https://www.bing.com/search?q=site%3Abilibili.com+测评"
```

信号密度低于 RSSHub，冷门发现有用途。

## 信号词表

### 购买意向（高价值）🔥

- 求同款 / 求型号 / 求牌子
- 怎么买 / 哪里买 / 链接
- 多少钱 / 什么价位
- 想要 / 想买 / 种草了
- 等降价 / 等双十一 / 等 618
- 性价比 / 配置 / 参数

### 提问意向（中价值）🟡

- 求推荐 / 求建议
- 怎么选 / 哪个好
- 值得买吗 / 值不值
- 能出个对比吗 / 能测一下吗
- UP 主能讲讲 xxx 吗

### 吐槽 ❌

- 太贵了 / 不值
- 翻车了 / 踩雷
- 广告 / 软文 / 恰饭
- 别买 / 避雷

### B站特有标记

- **弹幕**：短小、即时、强情绪。盯"求链接""买买买""等等党"。PulseHub 目前从视频页抓，不走弹幕 API。
- **三连**：点赞+投币+收藏，B站特有的强力认可信号，高价值内容指标。
- **充电**：B站打赏机制。"求充电"类弹幕是社区参与信号。
- **分区**：`tid` 数值。科技=95，数码=207，知识=36。重要过滤维度。

## 风控规则

### 硬性上限（登录态 Chrome MCP）

| 上限 | 值 |
|-------|-------|
| 单会话最大浏览量 | 80（远高于小红书） |
| 每天最多会话数 | 5 |
| 动作间最小延迟 | 3s |
| 单会话最长时长 | 60 分钟 |
| 验证码触发即停 | 是——暂停 4h（比小红书轻） |

### 账号轮换

- B站对自动化**最宽容**——纯只读调研可用大号
- 实际评论仍用小号（B站会标记日评论 50+ 的账号）
- 养号：新号先看+赞一周再评论

### 异常检测

看到以下情况停止：
- "请进行人机验证"提示
- 正常查询搜索结果突然为空
- HTTP 412（B站反爬码）
- 评论静默发送失败

## 示例 Workflow

### Workflow A：竞品监控（最常用）

**目标**：监控竞品 UP "xxx" 的新视频。

```
1. 解析 UP UID：
   - search.bilibili.com/upuser?keyword=xxx
   - 或从主页 URL 拿：space.bilibili.com/{uid}

2. RSSHub 拉取：
   bash _shared/scripts/shell/rsshub-fetch.sh "/bilibili/user/video/{uid}"

3. 过滤最近 24h 的视频（用 <pubDate>）

4. 对每个视频：
   - pulse-resolve → ResolvedLink
   - pulse-enrich（yt-dlp --dump-json 拿元数据）
   - LLM 信号检测（标题+简介）

5. pulse-deliver → Markdown 报告
```

### Workflow B：分区热门

**目标**：找过去 24h 的科技热门视频。

```
1. 选分区：数码 = tid 207
2. RSSHub: /bilibili/part/ranking/207/3/1
3. 拿 top 20 视频
4. 逐个：pulse-resolve + pulse-enrich
5. 过滤标题中的购买意向信号
6. pulse-deliver → "数码热门中的评论机会"
```

### Workflow C：搜索驱动发现

**目标**：找"无线耳机测评"高互动视频。

```
1. Chrome MCP 搜索：
   navigate https://search.bilibili.com/all?keyword=无线耳机测评&order=click

2. 按播放量排序（高→低）

3. 对每条结果：
   - pulse-resolve BV URL
   - pulse-enrich（yt-dlp 拿 play_count, like_count, comment_count）
   - 评分：play > 10k 且 comment_count > 50 → high
```

## 常见 Pitfalls

### ❌ 不要混淆 BV 和 av ID

- `BV1xx411c7mD` ≠ `av123456`
- B站两个都认，av 自动重定向到 BV
- pulse-resolve 都能处理，但下游工具（yt-dlp）偏好 BV

### ❌ 不要忽略分区

- 数码区的观众 ≠ 跳宅舞区的观众
- enrich 输出里始终给视频打 `tid` 标签
- 发现时按 tid 过滤

### ❌ 不要只信弹幕数

- 高弹幕 ≠ 高购买意向
- 弹幕在梗/段子内容上高、在商业内容上低
- 用评论区 + 赞播比做更好的信号

## 工具速查

| 工具 | 用途 |
|------|------|
| `rsshub-fetch.sh` | RSSHub 路由抓取（B站覆盖最好） |
| Chrome DevTools MCP | 登录态浏览、搜索抓取 |
| `pulse-resolve` CLI | BV/av URL 标准化 |
| `yt-dlp` | B站元数据 + 音轨下载（完美支持） |
| `whisper-transcribe` | B站视频转录 |
