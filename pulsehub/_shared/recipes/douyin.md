# 抖音 (Douyin) Recipe

> 结构移植自 [`rednote.md`](rednote.md)。抖音的购买意向信号密度**最高**——但反爬也**最严**。
> 命令基准：从 PulseHub 仓库根执行（`_shared/scripts/...`）。

## 平台画像

| 属性 | 值 |
|----------|-------|
| **登录模型** | OAuth2 / 扫码（抖音 App）；RSSHub 支持有限 |
| **公开访问** | 低——多数内容需要签名 URL（`_signature`、`msToken`） |
| **限流** | 紧（单会话约 20 次浏览后出验证码） |
| **验证码类型** | 滑块 + 旋转图片 |
| **账号风险** | 高——必须小号，绝不用大号 |
| **最佳评论窗口** | 0-30 分钟（衰减极快） |
| **桌面 vs 移动端** | `m.douyin.com` 和 `www.douyin.com` 都可用 |
| **签名参数** | `_signature`、`msToken`、`a_bogus`——每小时变，难伪造 |

## URL 模式

### 规范 URL 格式

```
https://www.douyin.com/video/{id}                 # 视频
https://www.douyin.com/note/{id}                  # 图文
https://www.douyin.com/discover?modal_id={id}     # 弹窗视图
https://www.iesdouyin.com/share/video/{id}        # 旧版分享 URL
```

### 短链域名

- `v.douyin.com/{slug}/` —— 通用短链，302 到规范 URL

### 作品 ID 格式

- 纯数字串（通常 19 位），如 `7234567890123456789`
- 与 B站 BV/av 不同：无前缀，纯数字

### Token

URL 里无需。**但签名访问需要**：
- `_signature` query 参数（每次请求一个，约 1 小时过期）
- `msToken` cookie（每会话，约 30 分钟）
- `a_bogus` 参数（2024+ 的新反爬）

PulseHub **不**尝试伪造这些——依赖：
1. RSSHub（有自己的签名请求基础设施）
2. Chrome MCP（继承真实浏览器的 cookie + 签名）

## 发现源

### 源 1：RSSHub（覆盖有限）⚠️

抖音 RSSHub 路由比 B站**不可靠**——抖音主动封 RSSHub 的 IP 池。

| 模式 | RSSHub 路由 | 状态 | 返回 |
|------|--------------|--------|---------|
| `competitor_watch` | `/douyin/user/{id}` | ⚠️ 需 cookie | 用户视频 |
| `trending` | `/douyin/trending` | ✅ 免登录 | 热门视频（每小时） |
| `trending` | `/douyin/ranking` | ⚠️ 区域锁 | 排行榜 |
| `topic_search` | （不支持） | ❌ | — |

**Cookie 配置**：

`/douyin/user/{id}` 需要在 RSSHub 的 `.env` 里设：

```
DOUYIN_COOKIE_{id}=your_cookie_here
```

取 cookie：
1. Chrome 打开 → 小号登录 douyin.com
2. DevTools → Application → Cookies → `https://www.douyin.com`
3. 把 `sessionid`、`ttwid`、`msToken` 复制进 RSSHub env

**用法**：

```bash
# 热门（免登录）
bash _shared/scripts/shell/rsshub-fetch.sh "/douyin/trending"

# 用户视频（需 cookie）
bash _shared/scripts/shell/rsshub-fetch.sh "/douyin/user/{sec_uid}"
```

注：抖音用 `sec_uid`（base64，约 70 字符），不是数字 UID。从主页 URL 里找。

### 源 2：Chrome DevTools MCP（抖音主力）

鉴于 RSSHub 的抖音限制，Chrome MCP 是**主力**发现源。

| 意图 | URL |
|--------|-----|
| 搜视频 | `https://www.douyin.com/search/{keyword}?type=video` |
| 搜用户 | `https://www.douyin.com/search/{keyword}?type=user` |
| 用户主页 | `https://www.douyin.com/user/{sec_uid}` |
| 视频详情 | `https://www.douyin.com/video/{id}` |
| 创作者中心 | `https://creator.douyin.com/`（仅自己的数据） |

**流程**（登录小号）：
1. `navigate` 到搜索 URL
2. `wait` 等 `networkidle`（5-8 秒——抖音 JS 重）
3. `scroll` 2-3 次加载懒加载内容
4. `network_monitor` 抓 `/aweme/v1/web/general/search/single/` 响应
5. 解析 JSON → `{aweme_id, desc, author, statistics: {play_count, digg_count, ...}}`

### 源 3：搜索引擎

```bash
# firecrawl（Bing 后端，免登录）
firecrawl search "site:douyin.com 无线耳机"

# Bing 直连
curl "https://www.bing.com/search?q=site%3Adouyin.com+求推荐"
```

信号密度低——抖音内容被外部搜索引擎收录差。

## 信号词表

### 购买意向（高价值）🔥

抖音是全平台购买意向信号密度**最强**的。

- 求链接 / 求链接啊 / 链接呢
- 怎么买 / 哪里买 / 怎么下单
- 多少钱 / 多少米 / 什么价位
- 想要 / 想买 / 种草了
- 求同款 / 同款
- 已下单 / 已入手 / 已拍
- 怎么付款 / 怎么联系卖家

### 提问意向（中价值）🟡

- 求推荐 / 求安利
- 怎么选 / 选哪个
- 有用过的吗 / 谁买过
- 好用吗 / 值得吗

### 吐槽 ❌

- 太贵了 / 不值
- 翻车了 / 踩雷了
- 假货 / 高仿
- 售后差 / 客服差
- 退款 / 退货

### 抖音特有标记

- **小黄车**：视频挂商品链接 = 强销售信号
- **橱窗**：UP 主有商品橱窗 = 商业化账号
- **直播间引流**："进直播间""链接在直播间" = 限时销售
- **抖音号**：`dy{数字}` 格式，不同于 sec_uid
- **3 分钟热度**：内容生命周期极短，< 1 小时评论价值最高

## 风控规则

### 硬性上限（Chrome MCP 会话）

| 上限 | 值 |
|-------|-------|
| 单会话最大浏览量 | 20（非常严） |
| 每天最多会话数 | 2 |
| 动作间最小延迟 | 8s |
| 单会话最长时长 | 20 分钟 |
| 验证码触发即停 | 是——暂停 24h |

### 账号轮换

- **绝不**用大号
- 2-3 个小号每周轮换
- 每个小号要像真人：
  - 头像 + 简介
  - 3-5 条正常视频（15 秒以上的个人内容）
  - 50+ 粉丝（真的或慢慢养的）
- 1 个月后退役该号，养新号

### 异常检测

看到以下情况停止：
- 滑块或旋转图片验证码
- "请输入手机号验证"
- 已登录却被重定向到登录页
- 正常查询搜索返回 0 结果
- HTTP 461 / 471（抖音反爬码）
- API 响应里出现 `verify_type` 字段

## 示例 Workflow

### Workflow A：热门发现（免登录）

**目标**：找赛道热门视频。

```
1. RSSHub: bash _shared/scripts/shell/rsshub-fetch.sh "/douyin/trending"
2. 按标题/简介过滤赛道关键词
3. 逐个：pulse-resolve → pulse-enrich
4. pulse-deliver → "热门机会"
```

### Workflow B：搜索驱动发现（Chrome MCP，需登录）

**目标**：找"无线耳机"相关、评论有购买意向的视频。

```
1. Chrome MCP navigate:
   https://www.douyin.com/search/无线耳机?type=video&sort_type=0&publish_time=0

2. 等待 + 滚动（5-8 秒，3 次滚动）

3. 抓 /aweme/v1/web/general/search/single/ 响应

4. 对每条视频：
   - 提取：aweme_id, desc, statistics.digg_count, statistics.comment_count
   - 过滤：digg_count > 1000（真互动信号）
   - pulse-resolve：用 aweme_id 拼 URL

5. 对过滤后的集合：
   - 逐个打开视频页
   - 抓 /aweme/v1/web/comment/list/ 响应
   - 扫评论里的购买意向关键词

6. pulse-deliver → top 机会报告
```

### Workflow C：竞品监控（需 cookie）

**目标**：监控竞品 "xxx" 的新视频。

```
1. 解析竞品 sec_uid：
   - Bing 搜 "xxx 抖音"
   - 或抓 douyin.com/search/xxx?type=user

2. RSSHub（已配 cookie 时）：
   bash _shared/scripts/shell/rsshub-fetch.sh "/douyin/user/{sec_uid}"

   或 Chrome MCP：
   - navigate https://www.douyin.com/user/{sec_uid}
   - wait networkidle
   - 抓 /aweme/v1/web/aweme/post/ 响应

3. 过滤最近 24h 的视频

4. pulse-resolve + pulse-enrich + pulse-deliver
```

## 常见 Pitfalls

### ❌ 不要丢 `_signature` 或 `msToken`

API 访问必需。它们绑定会话和 IP——跨机器/跨会话复制会失败。

PulseHub 的处理：
- 用 Chrome MCP（继承真实浏览器状态）
- 不在浏览器上下文之外解析 API 响应

### ❌ 不要混淆视频和图文

- `/video/{id}` = 标准视频
- `/note/{id}` = 图文（带文字的图片轮播）
- pulse-resolve 保留这个区分——不要抹掉

评论策略不同：
- 视频：评论视频本身
- 图文：评论单张图片（单次曝光互动更多）

### ❌ 不要忽略发布时间

抖音内容半衰期极短：
- 0-30 分钟：互动峰值窗口
- 30 分钟-2h：仍有价值
- 2-6h：衰减中
- 6h+：基本死了

enrich 必须含 `publishedAt`。deliver 用它算 `bestWindowMin`。

### ❌ 不要激进自动滚动

抖音把快速滚动当机器人。用：
- 每页 2-3 次滚动
- 滚动间隔 3-5 秒
- 盯"上拉加载更多"提示——单会话触发不超过 5 次

## 工具速查

| 工具 | 用途 |
|------|------|
| `rsshub-fetch.sh` | RSSHub（有限——只有 `/douyin/trending` 稳定） |
| Chrome DevTools MCP | 抖音主力工具（需登录小号） |
| `pulse-resolve` CLI | URL 标准化（处理 video/note 区分） |
| `yt-dlp` | 抖音元数据能用，但常被签名要求挡 |
| `whisper-transcribe` | 视频转录（yt-dlp 对抖音常失败——音频走 Chrome MCP 下载） |

## 与小红书对比

| 维度 | 小红书 | 抖音 |
|--------|--------|------|
| 购买意向密度 | 高 | **更高** |
| 评论价值衰减 | ~30 分钟 | **~30 分钟**（相同） |
| 反爬严格度 | 高 | **极高** |
| RSSHub 覆盖 | 好 | **差**（多数路由要 cookie） |
| Chrome MCP 可行性 | 好 | 好（但限额更严） |
| 适合 | 生活方式 / 美妆 / 穿搭 | 大众市场 / 快消 / 爆品 |
