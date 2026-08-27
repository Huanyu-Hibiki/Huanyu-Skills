# PulseHub Recipes（平台攻略）

平台专属操作手册。每个 recipe 告诉 AI Agent 在单个平台上**具体**怎么干——去哪发现信号、怎么解析 URL、什么信号重要、风控规则是什么。

命令基准：recipe 内命令从 PulseHub 仓库根执行（`_shared/scripts/...`）。

## 为什么要有 Recipes

每个中文社媒平台都有自己的：
- URL 格式（短链、分享链、移动端 vs 桌面）
- 发现源（有的有 RSSHub 路由，有的要浏览器自动化）
- 信号词表（小红书的"求链接" vs 抖音的"怎么买"）
- 风控怪癖（小红书验证码、抖音 `msToken` 等）

Recipes 沉淀这些**平台特有知识**，让 skill 本体保持通用。

## Recipe 目录

| 平台 | Recipe | 状态 |
|----------|--------|--------|
| 哔哩哔哩 | [`bilibili.md`](bilibili.md) | ✅ 完成 |
| 小红书 | [`rednote.md`](rednote.md) | ✅ 参考模板 |
| 抖音 | [`douyin.md`](douyin.md) | ✅ 完成 |
| 微信公众号 | [`wechat-official.md`](wechat-official.md) | ✅ 完成 |
| 微信视频号 | `wechat-channels.md` | 🔴 待写（需扫码登录，URL 可解析内容有限） |
| 知乎 | [`zhihu.md`](zhihu.md) | ✅ 完成 |

**6 个平台已写 5 个。** 贡献新 recipe 时用 [`rednote.md`](rednote.md) 当规范模板。

## Recipe 结构

每个 recipe 遵循同一大纲：

```markdown
# <平台名>

## 平台画像
- 登录模型（cookie / OAuth / 公开）
- 限流
- 风控怪癖

## URL 模式
- 规范格式
- 短链域名
- 必需 token

## 发现源
- RSSHub 路由
- Chrome DevTools MCP 路径
- 搜索策略

## 信号词表
- 购买意向关键词
- 提问关键词
- 吐槽关键词

## 风控规则
- 每日请求上限
- 小号轮换要求
- 验证码 / 异常处理

## 示例 Workflow
- 话题搜索
- 竞品监控
- 自己评论监控
```

## 贡献一个 Recipe

1. 复制 `rednote.md` 为 `<你的平台>.md`
2. 逐节填入平台特有细节
3. 端到端实测至少 2 个示例 Workflow
4. 加进上面的目录表
5. 提 PR

Recipe 是你对 PulseHub **最有价值的贡献**——它编码了别处没写下来的、实战换来的运营知识。
