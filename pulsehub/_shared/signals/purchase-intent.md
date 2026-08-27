# Purchase Intent Signal

The user is ready to buy, asking where/how to buy, or expressing desire to own a product.

## Score Impact

**high** — Strongest possible engagement signal. Comment within 30 minutes for maximum visibility.

## Variants by Category

### Generic (any category)

- 求链接 / 求链接啊 / 链接呢 / 链接一下
- 怎么买 / 哪里买 / 哪里能买 / 上哪买
- 多少钱 / 多少米 / 什么价位 / 价格多少
- 想要 / 想买 / 种草了 / 被种草
- 求同款 / 求型号 / 求牌子
- 怎么下单 / 怎么付款 / 怎么下单买
- 已下单 / 已入手 / 已购入 (positive signal — confirms market validation)
- 链接开了 / 链接没了 / 链接失效 (urgency — original link broke)
- 出 / 出一个 / 闲鱼出 (resale context, sometimes negative)

### Electronics / 3C

- 配置 / 参数 / 跑分 / 性价比
- 入手 / 冲了 / 等降价 / 等双十一
- 续航 / 屏幕 / 拍照 / 充电速度
- 实测 / 评测 / 对比 / 横评

### Beauty / Fashion

- 色号 / 试色 / 上嘴 / 上脸
- 适合 / 不适合 / 显白 / 显黑
- 链接 / 货号 / 哪里买便宜
- 学生党 / 平价 / 替代款

### Home / Lifestyle

- 团购 / 拼单 / 优惠 / 折扣
- 哪里订 / 怎么订 / 预约
- 链接发了 / 已拍

## Match Rules

- Case-insensitive matching
- Whole-word boundaries where applicable (避免误匹配子串)
- Trim whitespace before matching
- Combine with negation list — see False Positives below

## Suggested Comment Angle

When `purchase-intent` fires:

1. **Acknowledge the ask** — "看到你想要 XX，我用了 Y 个月..."
2. **Qualify the need** — ask about their use case / budget
3. **Mention 1-2 differentiators** — pick the ones that match their stated need
4. **Soft call to action** — "需要的话可以聊聊" or "我主页有详细对比"
5. **Do NOT** drop a bare affiliate link in the first comment — looks spammy

**Critical**: Adjust the angle based on `metadata.title` and `metadata.description`. Generic comments get reported as bot spam.

## False Positives

These look like purchase intent but aren't:

- "不想要" / "不想买" / "不种草" — explicit negation
- "求链接" appears in *commenter's own bio* — just their habit, not actual intent
- "多少钱" asked sarcastically — "这破玩意儿多少钱啊？" (complaint, not purchase)
- "怎么买" in a tutorial context — "教你怎么买到便宜机票" (creator post, not buyer)
- "想要" + emoji like 😂 / 🤣 — likely ironic

## Cultural Notes

- "出" / "出二手" is a **resale signal** — the user already owns it and is selling. Different angle: don't sell them again, ask why they're selling (intel opportunity).
- "等双十一" / "等 618" — buyer is **price-sensitive** and waiting. Don't pitch premium products.
- "学生党" — buyer has limited budget. Suggest value options.
- "种草" originally meant "to plant grass" — internet slang for "to be influenced to want something". Very high intent.

## Platform-Specific Notes

- **小红书**: Heaviest purchase-intent density. Comments are the main signal source.
- **抖音**: Purchase intent often in video itself (creator pitching). Check transcript.
- **B站**: Purchase intent mostly in 弹幕 (bullet comments) and 评论区.
- **知乎**: Long-form, intent is buried in question body. Less common but very high-value when found.
- **公众号**: Almost no purchase intent (articles are top-of-funnel, not bottom).
