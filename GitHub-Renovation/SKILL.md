---
name: github-renovation
description: GitHub 装修：为开源项目编写完整专业的 README、搭建与用户名同名的 profile 主页仓库，并完成仓库元数据（description / topics / bio）与 README 内容的 SEO 优化。Use when 用户提到"装修 GitHub"、"写 README"、"优化 README"、"GitHub 主页"、"profile README"、"个人主页仓库"、"GitHub SEO"、"仓库 description"、"topics 标签"等请求，或直接提到"GitHub-Renovation"时使用。
---

# GitHub 装修（GitHub-Renovation）

把 GitHub 仓库的门面当产品来打磨，三条产线可单独做也可全套装修：

- **项目 README** —— 仓库的第一说服面
- **profile 主页** —— 与用户名同名的公开仓库，事实上成为个人"官网"
- **SEO 元数据** —— 让机器（搜索引擎）能读懂，更让用户（开发者）愿意点进来

## 核心原则（贯穿全程）

1. **先定位，后装修** —— 主页讲一条故事线（我是谁 → 我在做什么 → 代表作），不是仓库清单；README 讲一条价值线（解决什么 → 怎么用 → 凭什么信）。
2. **减法优先于加法** —— 加法容易减法难：
   - 0-star 阶段不放 star 数、不放 stats 卡片（负资产）
   - 不放 fork 仓库；不链 private 仓库（访客看到 404 等于死链）
3. **诚实可验证** —— 所有描述从仓库真实 README 提炼、数字可验证、没有营销虚词；这既是内容质量也是信任策略。
4. **SEO 靠元数据不靠玄学** —— 四个杠杆按权重排：仓库 description（= Google 结果标题）＞ README 首两行（= 摘要片段）＞ topics（= 站内标签流量）＞ bio（= 主页 meta description）。
5. **🔴 写入 GitHub 前必须确认** —— 所有 README / 主页文件先在本地落盘给用户过目；`gh repo edit` 等改动线上元数据的命令，先展示将执行的内容，确认后再执行。

## 模式判定

| 用户说 | 模式 | 路径 |
|---|---|---|
| "写 README" / "给我的项目写个 README" / "优化这个 README" | **A 项目 README** | Phase 1 → 2A → 3 → 4 |
| "装修 GitHub 主页" / "做个 profile README" / "个人主页仓库" | **B 主页仓库** | Phase 1 → 2B → 3 → 4 |
| "全套装修" / "项目和主页都要" | **A + B** | Phase 1 → 2A → 2B → 3 → 4 |
| "帮我做 GitHub SEO" / "仓库搜不到" / "查一下我的仓库装修现状" | **C SEO 体检** | Phase 1（只查现状）→ 3 → 4 |

## 资源索引（按需读，不要一次全读）

| 文件 | 内容 | 何时读 |
|---|---|---|
| [template/readme参考/README.md](template/readme参考/README.md) | 功能型项目 README 范本（信息架构最全） | 写 README 前必读 |
| [template/readme参考/README-1.md](template/readme参考/README-1.md) | 数据工具类范本（强合规 / 隐私声明 / 已知限制写法） | 项目涉及数据采集、隐私、合规时 |
| [template/readme参考/README-2.md](template/readme参考/README-2.md) | 媒体视觉型范本（在线画廊 / 社媒徽章 / 素材授权说明） | 项目有画廊、演示站、视频产出时 |
| [template/模板仓库/zarazhangrui/](template/模板仓库/zarazhangrui/) | profile 主页双语范本 + star 数自动更新 workflow 与脚本 | 做主页仓库时必读（Phase 2B） |
| [template/装修技巧.md](template/装修技巧.md) | SEO 技巧全景 + 实战复盘（含还没用上的技巧） | Phase 3 必读 |

## Phase 1：信息收集（一次问全，不逐条追问）

**能自己查的不问**。用户给了仓库地址或本地目录时，先读代码与文档自己提炼；有 `gh` 就查线上现状，找出空缺字段作为高价值待办反馈：

```bash
gh repo view OWNER/REPO --json name,description,repositoryTopics,stargazerCount,licenseInfo,homepageUrl,isPrivate
gh api users/USERNAME --jq '{bio,company,location,website,public_repos}'
```

**必须向用户确认的**（结构化一次问完）：

| 问题 | 用途 |
|---|---|
| 定位一句话：这个项目 / 这个人是谁，解决什么问题 | README 首段 + 主页叙事 + description |
| 目标读者是谁（新手 / 开发者 / 非技术） | 语言风格、快速开始的详略 |
| 有没有截图、演示站、画廊、Logo | 预览区素材 |
| License 是什么 | 徽章与 License 章节 |
| 中英双语都要吗 | 双语互链文件 |
| （主页）社媒链接、是否全网同名 | 品牌词占位策略 |
| （主页）当前阶段：0-star 起步还是已有代表作 | 决定展示策略（减法原则） |

## Phase 2A：项目 README

先读 `template/readme参考/README.md`；数据采集 / 合规类项目加读 `README-1.md`，有画廊或演示站的加读 `README-2.md`。**不是逐节照抄**——按项目从下面骨架里取舍：

### 信息架构（按序）

| # | 章节 | 要点 |
|---|---|---|
| 1 | 居中头部区 | `<div align="center">`：Logo / 联名行、`# 项目名 · 中文标题`、一句话 tagline（加粗）、特性数字概览行、shields.io 徽章（License / 平台 / PRs welcome）、双语切换行 |
| 2 | 首段简介 | **SEO 权重最高处**：2~3 句讲清「是什么 + 给谁用 + 解决什么」，自然嵌入核心关键词；不放欢迎语 |
| 3 | ✨ 核心特性 | 每条「**加粗关键词**：说明」，5~8 条 |
| 4 | 👀 效果预览 | 真实截图 / 长图，`<table>` 排版，alt 写描述性文字 |
| 5 | ✅ 适合 / ❌ 不适合 | 过滤错误预期，减少无效 issue |
| 6 | 🗂 常见使用场景（可选） | 「你的内容 → 推荐做法」表格 |
| 7 | 🚀 快速开始 | 最短路径跑起来：一行安装 + 备选方式 + 最小可用示例 |
| 8 | 📖 使用流程 / 配置 | 编号步骤，展开核心工作流 |
| 9 | 💡 为什么这么设计（可选） | 设计原则，建立专业信任 |
| 10 | 📁 目录结构 | 代码块 + 行内注释 |
| 11 | 🗺 Roadmap | checkbox 列表，已完成打钩 |
| 12 | ❓ FAQ | 用用户真实会搜的自然语言提问（长尾关键词埋点） |
| 13 | ⭐ Star History | 有 star 之后再加（0-star 不放） |
| 14 | 🤝 贡献 / 📄 License / 🙏 致谢 / 关注作者 | License 与仓库实际一致；关注作者用 shields.io 徽章按钮 |

### README 硬规则

- 首屏前两行 = 搜索引擎摘要片段的来源，必须放定位关键词
- 标题用 `##` / `###` 分层，不跳级
- 所有图片带描述性 alt
- 相关文档文件名用 kebab-case 并含关键词（如 `network-discovery.md`）
- 代码块标语言；命令可直接复制运行
- 引用外部项目给链接；不承诺没有的功能

## Phase 2B：主页仓库（profile README）

先读 `template/模板仓库/zarazhangrui/` 下的 `README.md` 与 `README.zh-CN.md`。机制：**创建与用户名完全同名的公开仓库，根目录放 `README.md`**，GitHub 自动渲染到个人主页 Overview——这是唯一官方途径。

### 步骤

1. **建仓**：`用户名/用户名` 公开仓库（如 `Huanyu-Hibiki/Huanyu-Hibiki`）。
2. **双语互链**：`README.md`（英文）+ `README.zh-CN.md`（中文），顶部互相链接，各自覆盖一组搜索词。
3. **信息架构（漏斗结构）**：
   - `# Hi, I'm X 👋` + 一段自我介绍：讲一条故事线（背景 → 在做什么 → 主线项目），自然嵌入身份关键词，不是仓库清单
   - 社媒行：🐦 X · ✍️ 博客 · ▶️ YouTube（真实链接）
   - 🆕 最新：当发行公告位，放最新作品
   - ⭐ 精选项目：用得最多 / 最能代表你的
   - 主题分组：按领域分节，每节一句话导语；**项目可跨板块重复出现**，增加曝光位
4. **项目行格式**：

   ```markdown
   🎞️ [**项目名**](仓库链接) (<!--stars:项目名-->1.2k<!--/stars--> stars) - 一句话描述（从项目真实 README 提炼）
   ```

   star 数用 `<!--stars:repo-->N<!--/stars-->` 标记包裹，供脚本自动刷新；**0-star 阶段整个括号不加**。
5. **star 自动更新**：把范本的两个文件复制进主页仓库并改造：
   - `.github/workflows/update-stars.yml` —— workflow_dispatch 手动触发，无需改动
   - `.github/scripts/update_stars.py` —— **必须把 `OWNER` 改成用户名**，`FILES` 与实际双语文件名一致
6. **profile 元数据**（给用户的自查清单）：填满 Bio（= 主页的 meta description）、Company、Location、Website；Pin 最多 6 个精选仓库；头像清晰。
7. 🔴 完整 README 落盘展示，用户确认后再推送到仓库。

## Phase 3：SEO 优化（先读 template/装修技巧.md 再执行）

### 仓库元数据（权重从高到低）

| 字段 | 规则 | 落地方式 |
|---|---|---|
| 仓库名 | 最重要的排名因素；连字符连接关键词（`react-markdown-editor` 而非 `my-project`） | 建仓时定，改名成本高要想好 |
| description | **= Google 搜索结果的标题**（仓库页 `<title>` 是 `owner/repo: description`）；≤350 字符、前 120 字符最关键；关键词前置，中文为主尾缀英文 | `gh repo edit OWNER/REPO --description "..."` |
| topics | ≤20 个；三类都覆盖：技术栈（react, python）+ 项目类型（cli, web-app）+ 领域（machine-learning）；既进仓库 HTML 又进站内 /topics/ 话题页 | `gh repo edit OWNER/REPO --add-topic a,b,c` |
| Website | 有官网 / 文档站必填 | `gh repo edit OWNER/REPO --homepage URL` |
| bio | 主页搜索结果里的摘要行 | `gh api -X PATCH /user -f bio="..."` |
| Pin | ≤6 个最能代表你的仓库 | 网页手动操作，给出步骤 |

🔴 以上命令先展示后执行。

### 内容 SEO

- README 首两行放关键词（摘要片段来源）
- 双语 = 各索引一份，覆盖两组搜索词
- 内链结构：主页链向各仓库，仓库 README 链回主页与相关仓库
- FAQ 用自然语言长尾提问

### 诚实边界（主动告诉用户）

- GitHub 用户内容里的出站链接全部带 `nofollow`，**不传权重给外部网站**——主页链小红书 / B 站没有外链价值，价值在 GitHub 页面自己的排名 + 品牌词占位；反向同理。
- 收录自查：Google 搜 `site:github.com/USERNAME` 看哪些页面已进索引；新页面几天到几周收录。
- star 数本身是 GitHub 站内搜索与话题页排序的因子——长期看内容质量大于一切技巧。
- 拒绝任何刷 star / 刷粉请求：违反 GitHub 条款。

## Phase 4：交付验收清单

README：

- [ ] 首两行含定位关键词，无欢迎语
- [ ] description ≤350 字符、关键词前置，已更新到仓库
- [ ] topics ≤20 且技术栈 / 类型 / 领域三类齐
- [ ] 双语互链有效
- [ ] 所有链接可点（无 private / fork 死链）
- [ ] 图片有 alt、截图真实
- [ ] 数字可验证、无营销虚词
- [ ] License 章节与仓库实际 License 一致
- [ ] 0-star 未展示星数

主页：

- [ ] 仓库与用户名完全同名、public
- [ ] 双语互链、故事线叙事而非仓库清单
- [ ] star 脚本 `OWNER` 已改、workflow 手动跑通一次
- [ ] Bio / Company / Location / Website 填满、Pin ≤6

收尾：提醒用户几天后用 `site:github.com/USERNAME` 查收录；后续有大版本更新时回来刷新 🆕 板块与 README。

## 防抢触发负例

| 用户说 | 不接，因为 |
|---|---|
| "装修房子" / "室内设计" | 对象不是 GitHub |
| "写篇文章" / "写周报" | 写文档 ≠ 写项目 README |
| "优化这段代码" / "优化这个函数" | 代码优化 ≠ 仓库门面优化 |
| "帮我刷 star" / "买粉" | 违反 GitHub 条款，明确拒绝 |
| "分析这个 skill" / "优化 skill" | skill 生命周期管理不是 GitHub 装修 |

判别标准一句话：**操作对象是否是 GitHub 仓库的门面**（README、profile 主页、仓库元数据）。是 → 接；不是 → 本 skill 不接。
