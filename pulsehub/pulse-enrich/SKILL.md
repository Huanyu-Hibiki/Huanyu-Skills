---
name: pulse-enrich
description: Add metadata and AI-scored engagement value to resolved URLs. Detects purchase-intent signals, transcribes video content, ranks opportunities. Use after pulse-resolve. 补充元信息、检测求购信号、AI打分、转录视频、排序机会。
---

# pulse-enrich · 信号补全与评分

把一个 `ResolvedLink` 变成带评分的 `Opportunity`：

1. 抓取元数据（标题、描述、作者、标签、时长）
2. 转录视频内容（如适用）
3. 检测互动信号（购买意向、提问、吐槽）
4. 给出评分（高 / 中 / 低）+ 评分理由

本 skill 是 4 段流水线的**第 3 段**：接收 `pulse-resolve` 的输出，产出可直接进报告的 `Opportunity` 对象。

## 何时使用

- 手里有一个 `ResolvedLink`，想知道**内容讲什么**
- 想检测**购买意向信号**（求链接 / 怎么买 / 价格）
- 想按互动价值**给 URL 排序**
- 需要**视频转录文本**做内容级分析

触发词：**enrich, analyze, score, rank, transcribe, detect, 分析, 打分, 排序, 转录, 检测**

## 何时不用

- 用户只要**标准化 URL** → 停在 `pulse-resolve`
- 用户要**最终报告** → 用 `pulse-deliver`（需要时会内部调 enrich）
- 用户想**发现新 URL** → 用 `pulse-discover`

## 工作流

### Step 1 · 接收 ResolvedLink

```json
{
  "platform": "rednote",
  "workId": "65f8e7ab...",
  "url": "https://www.xiaohongshu.com/explore/65f8e7ab...?xsec_token=...",
  "originalLink": "https://xhslink.com/a/abc123"
}
```

### Step 2 · 抓取元数据

按平台和内容类型选工具：

| 内容类型 | 工具 | 返回什么 |
|--------------|------|-----------------|
| 视频（任意平台） | `yt-dlp` | 标题、描述、标签、时长、封面、发布日期 |
| 小红书图文 | Chrome DevTools MCP | 标题、描述、标签（从页面 DOM） |
| 微信公众号文章 | `firecrawl` / `jina-reader` | 标题、正文、作者 |
| 知乎回答/文章 | `firecrawl` / `jina-reader` | 标题、正文、作者 |

**视频一律先跑 yt-dlp**：

```bash
python _shared/scripts/python/ytdlp-fetch/fetch.py --url "<resolved_url>" --output json
```

**B站/小红书等平台优先用平台内部 API 拿元数据**（见 Pitfalls P1/P2），减少逐页导航次数 = 降低反爬风险。

### Step 3 · 转录视频内容（可选）

内容是视频、且需要检测口播内容里的信号时：

```bash
# Step 3a: 只下载音轨
yt-dlp -x --audio-format mp3 --audio-quality 5 -o "/tmp/audio.mp3" "<url>"

# Step 3b: 转录
python _shared/scripts/python/whisper-transcribe/transcribe.py --input "/tmp/audio.mp3" --model base
```

**Whisper 用 `base` 求快、`small` 求准**，没有 GPU 别用更大模型。

**Fallback（工具链失败时）**：yt-dlp 拿不到元数据 → 改用 Chrome DevTools 打开页面读 `__INITIAL_STATE__`/DOM（见 P3）；Whisper 不可用 → 跳过转录，只用标题+描述做信号检测，并在结果里标 `no_transcript`；两个都失败 → 只输出 ResolvedLink + 已知信息，评分降为 `low` 并注明原因，**不要编造元数据**。

### Step 4 · 检测信号

把标题 + 描述 +（可选）转录文本交给 LLM，用信号检测 prompt 判读。

信号库（定义见 `_shared/signals/`——purchase-intent / question-intent / complaint 三类）：

| 信号 | 关键词示例 | 评分影响 |
|--------|-----------------|--------------|
| 购买意向 | 求链接, 怎么买, 价格, 多少钱, 链接, 哪里买 | ⬆️ 高 |
| 提问 | 求推荐, 怎么做, 能不能, 请问, 怎么 | ⬆️ 中 |
| 吐槽 | 太贵了, 不推荐, 差评, 退款, 售后 | ⬇️ 负面（跳过） |
| 热点 | 热门, 上热搜, 爆款, 病毒式 | 视语境 |

LLM prompt 模板：

```text
You are an engagement opportunity analyst. Given the following content,
detect which signals are present and assign an engagement score.

Title: {title}
Description: {description}
Transcript (if any): {transcript}
Existing comments sample: {comments}

Return JSON:
{
  "purchaseIntent": boolean,
  "questionIntent": boolean,
  "complaint": boolean,
  "matchedKeywords": ["求链接", "..."],
  "score": "high" | "medium" | "low",
  "scoreReason": "..."
}
```

### Step 5 · 输出 Opportunity

```json
{
  "link": { /* ResolvedLink */ },
  "metadata": {
    "title": "想买个无线耳机求推荐",
    "description": "预算 500 以内...",
    "author": "用户xxx",
    "publishedAt": "2026-07-27T09:00:00Z",
    "tags": ["无线耳机", "推荐"]
  },
  "signals": {
    "purchaseIntent": true,
    "questionIntent": true,
    "complaint": false,
    "matchedKeywords": ["求推荐", "买"]
  },
  "score": "high",
  "scoreReason": "强购买意向。作者正在主动求无线耳机推荐。评论窗口：发布后 0-60 分钟。",
  "enrichedAt": "2026-07-27T10:35:00Z"
}
```

## 示例

### 示例 1：快速评分（不转录）

**用户**："这 5 个 URL 哪个最值得评论？"

```
对每个 URL：
1. pulse-resolve → ResolvedLink
2. yt-dlp --dump-json → 元数据（跳过转录求快）
3. LLM 信号检测（标题 + 描述）
4. 输出 Opportunity

按评分排序（高 → 中 → 低），返回前 2 个
```

### 示例 2：深度分析（带转录）

**用户**："这个抖音视频里有没有提到我们的产品？"

```
1. pulse-resolve 解析抖音 URL
2. yt-dlp 下载音轨
3. whisper 转录
4. LLM 扫转录文本找产品提及
5. 报告："02:15 提到，上下文：..."
```

### 示例 3：批量过滤

**用户**："把这 30 个候选里高价值的筛出来"

```
1. pulse-resolve 全部 30 个 URL
2. 逐个：yt-dlp 元数据 + LLM 信号检测
3. 过滤 score == "high"
4. 过滤结果交给 pulse-deliver
```

## 性能与成本（每个 URL）

| 操作 | 耗时 | 成本 |
|-----------|------|------|
| 仅元数据（yt-dlp） | ~2s | 免费 |
| 转录（Whisper base, CPU） | ~30s/分钟音频 | 免费 |
| 关键词检测（内置） | ~10ms | 免费 |
| LLM 信号检测 | ~3s | **用调用方 Agent 自己的模型**（无额外费用） |

- **LLM 信号检测由调用方 AI Agent 用自己的模型完成**——PulseHub 只生成 prompt
- **不需要口播分析就跳过转录**

## 不要做

- **不编造元数据**——工具链全失败 → 评分降 `low` 并注明原因，不虚构标题/统计
- **能 API 拿的不逐页导航**——逐页导航是高风险动作，只在需要抓评论区内容时用（见 P1）
- **不连续快速抓取**——逐页之间 `sleep 180` 模拟人工；🛑 遇验证码/风控提示立即停
- **不抓用户隐私字段**——只取内容与互动数据

## 工具速查

| 工具 | 位置 | 用途 |
|------|----------|---------|
| `yt-dlp`（Python） | 外部依赖 | 视频元数据 + 音轨下载 |
| `whisper-transcribe` | `_shared/scripts/python/whisper-transcribe/` | 音频转文字 |
| `ytdlp-fetch` | `_shared/scripts/python/ytdlp-fetch/` | 视频元数据抓取辅助 |
| `firecrawl` | 外部 API | 非视频网页转 markdown |
| `jina-reader` | 外部 API | firecrawl 的免费替代 |
| 关键词信号检测 | 本文件 Step 4 表格 + `_shared/signals/*.md` | 关键词判读（AI 直接按表格判读，或用本地 Python 跑，无需额外安装） |
| **调用方 AI Agent 本体** | （你） | 用信号检测 prompt 调自己的 LLM——不需要单独的 API key |

## Pitfalls

### P1. 批量抓取帖子时必须模拟人工节奏，停顿 2-3 分钟/条（2026-08-05 用户硬规则）

**问题是什么**（用户原话："为了规避反爬，你不要一次性抓取特别多，抓取1条的时候停顿两三分钟再抓其他的内容，避免反爬，就是模拟人工真实浏览页面"）：

- ❌ 逐条导航到帖子页 → `evaluate_script` 提取内容 → 立刻导航下一条 → 连续抓 10 条（整个序列 < 2 分钟）
- ❌ B站/小红书/抖音的反爬系统检测到"短时间内连续访问 N 个帖子页" → 触发风控（限流 / 封号 / 验证码弹窗）
- ❌ 用户要的是数据，AI 的"快"直接导致**账号风险**

**正解**（模拟人工真实浏览）：
```text
0. 🛑 触发验证码/风控提示 → 立即停止逐页抓取，告知用户，等处理后再继续
1. 每抓 1 条帖子内容后，停顿 2-3 分钟（`sleep 180`）再抓下一条
2. 抓取过程中用 evaluate_script 做"像人一样"的动作：
   - 页面加载后等 2-3 秒再提取（模拟阅读）
   - 偶尔 scroll 一下（模拟浏览）
   - 不要用 for 循环连续 navigate（这是机器行为）
3. 批量 enrich 时先告诉用户预计耗时（如 "10 条 × 3min/条 ≈ 30 分钟"），让用户知道节奏
4. 优先用平台 API（如 B站 search API）一次性拿元数据，**减少逐页导航次数**——API 调用 1 次 = 拿 20 条 metadata，比逐页导航 20 次安全得多
5. **优先级**：能用 API 拿到的数据（标题/描述/播放/点赞/评论数）就不要逐页导航；逐页导航只在需要抓评论区内容时才做
```

**关键区分**：
- **平台搜索 API**（B站 `/x/web-interface/search/type`）= 1 次 API 调用拿 N 条结果 metadata = **低风险**
- **逐页导航**（navigate → evaluate_script 提取内容）= N 次页面访问 = **高风险**，必须限速

**实操模式**（2026-08-05 验证通过）：
```
Step 1: 搜索 → 用平台 API 一次拿 20 条 metadata（标题/描述/统计/标签）→ 低风险，快速
Step 2: 对 Top N 条做逐页 enrich → 每条之间 sleep 180s → 模拟人工
Step 3: signal 检测 + 打分用本地 Python（execute_code），不需要访问网络
```

### P2. B站搜索页 DOM 提取 title 会拿到脏数据（2026-08-05 实证）

**问题是什么**：
- ❌ B站搜索结果页的 `.bili-video-card__info--tit` 等 selector 返回的 textContent 是 "稍后再看51561126:23"（稍后再看 + 播放量 + 时长拼在一起），不是真正的标题
- ❌ 用 DOM selector 提取标题 = 不可靠

**正解**：用 B站内部搜索 API（`/x/web-interface/search/type`），返回干净 JSON：
```javascript
// 在 Chrome DevTools evaluate_script 里跑
const resp = await fetch('https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=' + encodeURIComponent(query) + '&page=1', { credentials: 'include' });
const data = await resp.json();
const results = data.data.result.map(v => ({
  bv: v.bvid,
  title: v.title.replace(/<[^>]+>/g, ''),  // 去掉 em 标签
  author: v.author,
  play: v.play,
  reply: v.reply,
  tag: v.tag,
  description: v.description
}));
```

**通用原则**：社交平台的搜索结果提取，**优先用平台 API** 而非 DOM scraping。API 返回结构化数据，DOM 返回脏数据。

### P3. 视频详情页用 window.__INITIAL_STATE__ 拿元数据（2026-08-05 实证）

B站视频页 `window.__INITIAL_STATE__.videoData` 含完整元数据（title/desc/owner/stat{view,danmaku,reply,favorite,coin,like}），比 DOM selector 可靠。小红书帖子页 `#detail-desc` 可拿描述。
