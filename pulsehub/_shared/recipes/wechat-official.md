# 微信公众号 (WeChat Official) Recipe

> 公众号文章的独特价值是**长尾**——发布一次，永久收录。6 个平台里互动密度最低，但 SEO 持久性最高。
> 命令基准：从 PulseHub 仓库根执行（`_shared/scripts/...`）。

## 平台画像

| 属性 | 值 |
|----------|-------|
| **登录模型** | 公开（文章 URL 无需 token）；作者侧用 `appId`/`appSecret` |
| **公开访问** | 高——`mp.weixin.qq.com/s/{slug}` 自由访问 |
| **限流** | 读宽松（约 100 次浏览才有摩擦） |
| **验证码类型** | `/cgi-bin/` 端点有图片验证（文章页少见） |
| **账号风险** | 读低；评论高（评论由作者预审） |
| **最佳评论窗口** | 0-48 小时（长尾；1 周后仍有 SEO 阅读） |
| **桌面 vs 移动端** | 都行；桌面抓取更容易 |
| **外部抓取** | 搜索引擎对公众号收录差——用搜狗微信（`weixin.sogou.com`） |

## URL 模式

### 规范 URL 格式

```
# 短 URL（分享中最常见）：
https://mp.weixin.qq.com/s/{slug}                    # slug 是不透明的类 base64 串

# 完整 URL（API/webhook 来的）：
https://mp.weixin.qq.com/s?__biz={base64}&mid={int}&idx={int}&sn={hex}&chksm=...
```

### 无独立短链域名

公众号文章没有 `b23.tv`、`v.douyin.com` 那样的独立短链域名。`mp.weixin.qq.com/s/{slug}` 本身就是短版。

### 作品 ID 格式

- `sn` 参数（32 位十六进制）是**最稳定的标识**
- `/s/{slug}` 里的 slug 也稳定但不透明（无解码规则）
- 其他参数（`__biz`、`mid`、`idx`）标识发布账号 + 位置

PulseHub 有 `sn` 用 `sn`，否则退回路径 slug。

### Token

读文章无需。**但**：
- 部分文章付费墙（付费阅读）
- 部分需关注公众号（关注后阅读）
- 境外 IP 可能见"该内容在你所在地区不可用"

## 发现源

### 源 1：RSSHub（主力）✨

微信不开放公开文章 API，RSSHub 走搜狗微信后端。

| 模式 | RSSHub 路由 | 返回 |
|------|--------------|---------|
| `competitor_watch` | `/wechat/mp/{cid}/{aid}` | 指定账号的文章 |
| `competitor_watch` | `/wechat/accounts/{category}` | 分类下的账号 |
| `topic_search` | （无路由——直接用搜狗） | — |
| `trending` | `/wechat/trending` | 热门文章 |

**解析 cid**（账号 ID，base64）：

```
1. 打开 https://weixin.sogou.com
2. 搜账号名
3. 打开账号页
4. 从 URL 提取：/gzh?openid={cid}&...
5. URL 解码 openid 参数
```

**用法**：

```bash
# 盯某账号的新文章
bash _shared/scripts/shell/rsshub-fetch.sh "/wechat/mp/{cid}/{aid}"
```

**注意**：搜狗微信反爬激进。RSSHub 路由可能失效或需要 cookie。设：

```
SOGOU_COOKIE_<cid>=your_cookie
```

### 源 2：搜狗微信直连

搜索驱动的发现：

```
https://weixin.sogou.com/weixin?type=2&query={keyword}
```

- `type=2` 搜文章（不是账号）
- 结果页可用 Chrome MCP 抓
- 返回：标题、摘要、账号名、文章 URL

**流程**：
1. `navigate` 到搜索 URL
2. `wait` 3-5 秒
3. 从页面 DOM 提取结果 URL
4. 每个 URL 都是 `mp.weixin.qq.com/s?...` 格式

### 源 3：微信内（App 内）

微信里：
- 订阅账号 → 文章进订阅号消息
- 读文章 → 复制 URL → 分享
- 数据最真实但**不可脚本化**（仅移动端）

PulseHub **不**自动化微信 App。用户手动转发感兴趣的 URL。

## 信号词表

### 购买意向（低密度）🔵

公众号文章本身很少有购买意向（漏斗顶部内容）。看：

- 评论（最有价值，但预审）
- 文末引导（"关注公众号回复 X 获取 Y"）

关键词：
- 关注后回复
- 长按识别
- 加微信 / 加 v
- 进群
- 课程 / 训练营
- 限时优惠

### 提问意向（中）🟡

- 怎么做 / 如何
- 是什么 / 区别
- 为什么
- 求教 / 求指教

### 吐槽 ❌

- 标题党
- 没营养
- 软文 / 广告
- 拉黑

## 风控规则

### 硬性上限

| 上限 | 值 |
|-------|-------|
| 单会话最大文章浏览量 | 50 |
| 每天最多会话数 | 5 |
| 浏览间最小延迟 | 5s |
| 单会话最长时长 | 30 分钟 |
| 验证码停止 | 暂停 12h |

### 公众号特殊注意

1. **评论预审**：所有评论由账号作者预审。你的评论可能永远不公开。别把高价值角度浪费在这里。
2. **封号风险**：跨多篇文章评论同一链接像 spam。微信追踪跨账号行为。
3. **IP 信誉**：数据中心 IP 的评论被静默丢弃。用住宅 IP。
4. **只读安全**：纯读文章完全安全——无摩擦。

## 示例 Workflow

### Workflow A：竞品文章监控

```
1. 解析竞品账号 cid（走搜狗微信）
2. RSSHub: bash _shared/scripts/shell/rsshub-fetch.sh "/wechat/mp/{cid}/{aid}"
3. 过滤最近 7 天文章（公众号长尾）
4. 逐个：pulse-resolve + pulse-enrich（firecrawl 抓正文）
5. pulse-deliver → "竞品内容报告"
```

### Workflow B：行业关键词搜索

```
1. Chrome MCP navigate: https://weixin.sogou.com/weixin?type=2&query=无线耳机
2. 等待 + 提取结果 URL
3. 逐个：pulse-resolve（公众号 Resolver 处理 /s/{slug} 格式）
4. pulse-enrich 走 firecrawl（抓正文）
5. LLM 扫品类趋势（不是购买意向）
6. pulse-deliver → "行业内容摘要"
```

### Workflow C：SEO 调研（只读）

内容规划用：

```
1. 选关键词（如"无线耳机选购"）
2. 搜狗微信拿 top 10 文章
3. 逐个：firecrawl 抓正文
4. 分析：
   - 共同结构（开头/对比/结论）
   - 平均长度
   - 提到的产品
5. 输出：自己写文章的内容 brief
```

## 常见 Pitfalls

### ❌ 不要指望评论被看见

公众号评论预审。就算评论很好，作者也可能不放行。把公众号互动当**品牌建设**，不是直接转化。

### ❌ 不要信搜狗微信的搜索量

搜狗夸大搜索量和点击量。数据只做定性用，不做定量用。

### ❌ 不要假设 URL 永久

微信会下架文章（如违规）。URL 可能一周后 404。重要的文章正文要存下来。

### ❌ 不要忽略 `__biz` 参数

同一账号的文章共享 `__biz`。追踪账号时存下它的 `__biz`，用于按来源过滤文章。

## 为什么互动价值低

公众号本质是**漏斗顶部**内容：

- 读者在**学习**模式，不是购买模式
- 文章长（2000-10000 字）→ 决策疲劳
- 无可见社交证明（无点赞数、评论数展示）
- 作者控制预审，评论 ROI 低

**建议**：公众号用于**调研**（读文章），不用于**互动**（评论）。"评论机会"流水线应把公众号 URL 降权。

## 工具速查

| 工具 | 用途 |
|------|------|
| `rsshub-fetch.sh` | RSSHub 公众号路由（需搜狗 cookie） |
| Chrome DevTools MCP | 搜狗微信搜索抓取 |
| `pulse-resolve` CLI | URL 标准化（sn 提取） |
| `firecrawl` | 文章正文提取（公众号 HTML 乱） |
| `whisper-transcribe` | （用不上——文章是文字） |
