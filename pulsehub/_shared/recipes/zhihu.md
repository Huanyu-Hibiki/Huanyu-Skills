# 知乎 (Zhihu) Recipe

> 知乎是中文平台里**问题质量最高**的——长、细、有研究深度。量比小红书/抖音少，但单个机会价值 10 倍。
> 命令基准：从 PulseHub 仓库根执行（`_shared/scripts/...`）。

## 平台画像

| 属性 | 值 |
|----------|-------|
| **登录模型** | 公开可读（受限）；全功能需登录 |
| **公开访问** | 中——多数回答不登录可读；部分需登录 |
| **限流** | 中等（单会话约 40 次浏览后出验证码） |
| **验证码类型** | 滑块 + 图片旋转 |
| **账号风险** | 中——建议小号；只读用大号安全 |
| **最佳回答窗口** | 0-7 天（长尾；前 24h 对排名关键） |
| **最佳评论窗口** | 回答下 0-6 小时；问题下 0-24h |
| **桌面 vs 移动端** | 优先桌面（`www.zhihu.com`） |
| **签名** | `x-zse-96` header（反爬，每月变化） |

## URL 模式

### 规范 URL 格式

```
https://www.zhihu.com/question/{qid}/answer/{aid}    # 具体回答
https://www.zhihu.com/question/{qid}                 # 问题页（列回答）
https://zhuanlan.zhihu.com/p/{pid}                   # 专栏文章
https://www.zhihu.com/pin/{pinId}                    # 想法——pulse-resolve 暂不支持
```

### 短链域名

- `link.zhihu.com/?target={url-encoded}` —— 站外链接包装（不是文章 URL）
- 知乎内容没有独立短链域名

### 作品 ID 格式

知乎用**纯数字 ID**（长整数）。pulse-resolve 加前缀区分类型：
- `a-{aid}` 回答
- `q-{qid}` 问题页
- `p-{pid}` 专栏文章

### Token

URL 里无需。**但**：
- API 访问需要 `x-zse-96` header（每月变，难伪造）
- `dnt` header 影响返回数据
- 部分内容"登录后查看"

PulseHub 的 API 调用走 Chrome MCP（继承真实浏览器签名）。

## 发现源

### 源 1：RSSHub（覆盖优秀）✨

知乎 RSSHub 路由维护良好、稳定。

| 模式 | RSSHub 路由 | 返回 |
|------|--------------|---------|
| `trending` | `/zhihu/hotlist` | 热榜（top 50 热门问题） |
| `trending` | `/zhihu/daily` | 知乎日报 |
| `topic_search` | `/zhihu/topic/{tid}` | 话题热门回答 |
| `competitor_watch` | `/zhihu/people/answers/{uid}` | 用户回答 |
| `competitor_watch` | `/zhihu/zhuanlan/people/{uid}` | 用户专栏文章 |
| `competitor_watch` | `/zhihu/pin/{uid}` | 用户想法 |

**主页 URL 转 UID**：

```
https://www.zhihu.com/people/{slug}    →   slug 是文本（如 "zhou-yuan-9"）
                                             用搜索找数字 UID
```

**用法**：

```bash
# 拉今日热榜
bash _shared/scripts/shell/rsshub-fetch.sh "/zhihu/hotlist"

# 盯某用户的新回答
bash _shared/scripts/shell/rsshub-fetch.sh "/zhihu/people/answers/{uid}"
```

### 源 2：Chrome DevTools MCP

搜索与富数据：

| 意图 | URL |
|--------|-----|
| 搜索 | `https://www.zhihu.com/search?type=content&q={keyword}` |
| 问题 | `https://www.zhihu.com/question/{qid}` |
| 回答 | `https://www.zhihu.com/question/{qid}/answer/{aid}` |
| 话题 | `https://www.zhihu.com/topic/{tid}` |
| 热榜 | `https://www.zhihu.com/hot` |

**流程**：
1. `navigate` 到搜索 URL（登录小号）
2. `wait` 等 `networkidle`（3-5 秒）
3. `network_monitor` 抓 `/api/v4/search_v3?t=general&q=...` 响应
4. 解析 JSON → `{id, type, object: {title, content, author, voteup_count, comment_count}}`

### 源 3：搜索引擎

```bash
# Bing（免费）
curl "https://www.bing.com/search?q=site%3Azhihu.com+%E6%B1%82%E6%8E%A8%E8%8D%90"

# firecrawl
firecrawl search "site:zhihu.com 无线耳机 推荐"
```

知乎被外部搜索引擎**收录好于**小红书/抖音，跨平台发现有用。

## 信号词表

### 购买意向（高质量、低频率）🔥

知乎的购买意向信号比小红书**更深但更稀**。

- 求推荐 / 求建议
- 怎么选 / 哪个好
- 有用过的吗 / 谁买过
- XX 值得买吗 / XX 是不是智商税
- 求对比 / 横评
- XXX 和 YYY 怎么选
- 预算 XXX 有什么推荐

### 提问意向（知乎密度最高）🟡

知乎本来就是问答平台——几乎每个 URL 都是一个问题。

- 怎么做 / 如何
- 是什么 / 区别
- 为什么
- 求教 / 求指教
- 求教程 / 求攻略
- 如何评价

### 吐槽 ❌

- 智商税 / 割韭菜
- 不值 / 太贵
- 售后差
- 假货
- 别买 / 避雷

### 知乎特有标记

- **谢邀**：标准开头，不是信号
- **匿名用户**：匿名回答权威权重低
- **高赞回答**：voteup_count > 1000——在这里互动的权威 ROI 最高
- **专栏**：zhuanlan.zhihu.com——更长、更打磨的内容
- **想法**：短内容，类推特——互动价值低
- **盐选会员**：部分内容付费墙
- **赞同 vs 反对 vs 评论**：赞同是主信号（顶）

## 风控规则

### 硬性上限

| 上限 | 值 |
|-------|-------|
| 单会话最大浏览量 | 40 |
| 每天最多会话数 | 4 |
| 浏览间最小延迟 | 5s |
| 单会话最长时长 | 40 分钟 |
| 验证码停止 | 暂停 12h |

### 账号轮换

- 知乎比小红书宽容，但也在追踪自动化
- **写回答**（非仅评论）要用养好的号：
  - 至少 1 个月账龄
  - 10+ 条有正赞的回答
  - 真实资料（头像、简介、兴趣）
- **只评论**的话小号即可

### 异常检测

看到以下情况停止：
- "请验证手机号"提示
- "系统检测到您的账号异常"消息
- 搜索出验证码（登录用户少见）
- 正常查询搜索结果为空
- 公开回答返回 HTTP 401 / 403

## 示例 Workflow

### Workflow A：热榜监控（推荐）

**目标**：捕捉你赛道的热门问题。

```
1. RSSHub: bash _shared/scripts/shell/rsshub-fetch.sh "/zhihu/hotlist"
   → 返回 top 50 热门问题

2. 按关键词过滤（如"无线耳机""推荐"）
   → 通常每天 2-5 条命中

3. 对每条命中：
   - pulse-resolve → ResolvedLink
   - 检查：已有高赞回答？（越多越难排上去）
   - 决策：写新回答（价值最高）还是在现有回答下评论？

4. 若写新回答：
   - pulse-enrich 走 firecrawl（抓问题正文 + top 3 回答）
   - LLM 分析：现有回答缺什么？
   - 建议角度："现有回答都讲 X，补 Y 视角。"

5. pulse-deliver → "知乎热榜机会"
```

### Workflow B：竞品回答监控

**目标**：监控竞品的回答找互动机会。

```
1. 解析竞品 UID（搜索）

2. RSSHub: /zhihu/people/answers/{uid}

3. 对每条新回答：
   - pulse-resolve
   - 检查：comment_count > 10？
   - 是 → 打开回答，扫评论里的提问意向关键词
   - 用有用的补充去评论（不与原回答竞争）

4. pulse-deliver → "竞品互动机会"
```

### Workflow C：关键词驱动问题搜索

**目标**：找赛道里还没人答的问题。

```
1. Chrome MCP navigate: https://www.zhihu.com/search?type=content&q=无线耳机+推荐

2. 过滤结果：
   - type=answer（已有回答——评论机会）
   - type=question（未答——写新回答）
   - 按最新排序

3. 对未答问题：
   - 检查：已有几个回答？< 5 = 绿地
   - 检查：关注数？> 100 = 高价值
   - 检查：问题年龄？< 24h = 最佳窗口

4. pulse-deliver → "知乎绿地问题"
```

## 评论策略差异

知乎和小红书/抖音有本质区别：

| 维度 | 小红书/抖音 | 知乎 |
|--------|------------|------|
| 互动类型 | 评论 | **写回答**（新写）或评论 |
| 回答长度 | 50-150 字 | 500-3000 字 |
| 权威 ROI | 低（评论被淹没） | **很高**（高赞回答常年挂榜） |
| 写作耗时 | 2 分钟 | 30-60 分钟 |
| 单次互动价值 | 1x | **20-50x** |

**战略含义**：知乎优先**写新回答**而不是评论。用 PulseHub 找绿地问题，然后写有分量的回答。

## 常见 Pitfalls

### ❌ 不要写低投入回答

知乎算法惩罚：
- < 200 字的回答
- 无格式（无加粗、无列表）
- 无图
- 只甩外链

写 500+ 字、带结构化格式。

### ❌ 不要跨问题复制粘贴同一回答

知乎检测重复内容。每条回答必须唯一。用 PulseHub 的信号检测为每个问题写**针对性**回答。

### ❌ 不要忽略关注数

10 关注 + 50 回答的问题**不如** 500 关注 + 2 回答的值钱。两个指标都要看。

### ❌ 不要评论"感谢分享"或"学到了"

知乎明令禁止低价值评论。会被删且可能标记账号。

### ❌ 不要只信 voteup_count

有些回答的赞是机器人或营销号刷的。检查：
- 评论：真互动还是垃圾？
- 作者历史：有没有其他优质内容？
- 日期：多年前的赞未必反映当前质量

## 为什么知乎量少但重要

尽管 PulseHub 从知乎产出的 URL 比小红书/抖音少：

| 原因 | 影响 |
|--------|--------|
| **长尾 SEO** | 一条好回答能带 5 年以上流量 |
| **高意向** | 知乎用户在研究模式——离购买更近 |
| **权威建设** | 高赞回答把你立成专家 |
| **跨平台放大** | 知乎回答被截图进小红书/抖音/公众号内容 |
| **搜索排名** | 百度对知乎收录权重高——回答排高价值查询 |

**建议**：把知乎当**优质渠道**。不冲量，冲质。每周一条好回答胜过每天 10 条平庸回答。

## 工具速查

| 工具 | 用途 |
|------|------|
| `rsshub-fetch.sh` | 知乎 RSSHub（热榜/话题/用户） |
| Chrome DevTools MCP | 搜索 + 登录态浏览 |
| `pulse-resolve` CLI | URL 标准化（a-/q-/p- 前缀） |
| `firecrawl` | 回答正文提取（知乎 HTML 复杂） |
| `whisper-transcribe` | 文字回答用不上；知乎视频回答（少见）可用 |
| 调用方 LLM | **关键**——分析现有回答找内容缺口 |
