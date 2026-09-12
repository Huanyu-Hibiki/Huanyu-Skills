<div align="center">

# xianyu-skill · 闲鱼卖货 AI 助手

**把你的 AI 技能包 / 资料包挂上闲鱼卖钱——AI 帮你拆竞品、写文案、做商品图，一条龙**

拆解爆款（它为什么卖得好）→ 写商品文案（标题+描述+自动排雷违规词）→ 生成详情图（封面+轮播图，直接上传）

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/Huanyu-Hibiki/Huanyu-Skills/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-3%20·%20卖货闭环-059669)](#-目录)
[![Agents](https://img.shields.io/badge/Claude%20Code%20·%20OpenCode%20·%20Codex%20·%20Cursor-supported-8b5cf6)](#-安装)

</div>

---

> 📦 本系统是 [Huanyu-Skills 合集](../)的一员。

输入：你做好的一个东西（比如一个 AI 技能包、一份教程资料）。输出：**能直接挂上闲鱼去卖的三件套**——竞品拆解报告、商品标题和描述、可直接上传的商品图。AI 只负责拆解、写作和排版，**卖多少钱、承诺什么，始终由你拍板**。

## 🧭 工作流

```
#3 拆解爆款 → #2 写文案 → #1 出详情图 → 挂上闲鱼
（可选）     （3版标题你挑） （3版风格你挑）
```

三步共享同一份"商品档案"，拆爆款学到的招数，自动用到文案和图上。每一步都可以单独用。

## 📋 目录

| # | Skill | 干什么 | 触发短语 |
|---|---|---|---|
| 1 | `xy-detail-images` 详情图 | 生成闲鱼封面图 + 竖版详情图（PNG 直接上传） | "生成详情图" / "做商品图" / "封面图" |
| 2 | `xy-listing-copy` 商品文案 | 3 版标题 + 商品描述，发布前自动查违规词 | "写商品描述" / "闲鱼文案" / "商品标题" |
| 3 | `xy-hot-analysis` 爆款拆解 | 分析同类爆款为什么卖得好，给你 5 条能抄的招 | "分析爆款" / "拆解这个竞品" |

## 📦 安装（写给完全没接触过 AI 工具的你）

整个安装分 2 步：**① 装好 AI 编程助手 → ② 放好本 Skill 文件夹**。跟着做就行，每步都有说明。

### 第 0 步：先弄清楚两个概念

| 名词 | 是什么 | 例子 |
|---|---|---|
| **AI Agent（编程助手）** | 能帮你操作电脑、读写文件的 AI 助手软件，本 Skill 的"大脑" | Claude Code、OpenCode、Codex CLI、Cursor |
| **Skill（技能）** | 教会 Agent 做某类工作的说明书文件夹，放到指定位置 Agent 就会自动使用 | 本项目 `xianyu-skill` |

> 你至少需要安装并登录其中一个 Agent，才能使用本 Skill。Agent 一般按模型用量向官方付费，与本 Skill 无关（本 Skill 免费、开源）。

### 第 1 步：把本 Skill 放到 Agent 能读到的位置

**方式一：从 GitHub 获取（需要安装 [Git](https://git-scm.com/downloads)）**

```bash
git clone https://github.com/Huanyu-Hibiki/Huanyu-Skills.git
```

**方式二：直接下载文件夹**，跳过 Git。

然后把它复制到你 Agent 的 skills 目录（任选其一位即可）：

| Agent | skills 目录（`<用户名>` 换成你的） |
|---|---|
| Claude Code | `C:\Users\<用户名>\.claude\skills\`（macOS/Linux：`~/.claude/skills/`） |
| OpenCode | 项目或全局 `.opencode/skills/` |
| Cursor / Codex | 项目内任意目录，用 `AGENTS.md` 指向它 |

复制后最终路径应类似：

```text
C:\Users\<用户名>\.claude\skills\xianyu-skill\
├── SKILL.md              ← Agent 读的入口说明书
├── 01-detail-images\     ← 子 skill：生成详情图
├── 02-listing-copy\      ← 子 skill：写商品文案
├── 03-hot-analysis\      ← 子 skill：拆解爆款
└── ...
```

> 本 Skill **不需要编程基础、不需要 API key**——它是纯 AI 工作流，放好文件夹就能用。

### 常见问题（FAQ）

| 问题 | 解决 |
|---|---|
| Agent 没识别到 skill | 确认路径下有 `SKILL.md` 文件，重启 Agent 会话 |
| 出图那一步卡住（截图工具没装） | 对 Agent 说"按 fallback 降级"，它会给你 HTML 文件 + 手动截图教程（浏览器打开，按尺寸截图即可），不影响使用 |
| 生成的图里字体不对 / 是方框 | 网络字体没加载出来，检查电脑联网后让 Agent 重新截图 |
| 想放在项目目录而非全局 | 可以，只要 Agent 能索引到该目录即可 |

## 🚀 第一次使用

在你的 Agent 里直接说：

```text
我做了个PPT复刻skill想在闲鱼卖，帮我把上架要准备的东西都弄好
```

AI 会接管整条链：先问你几个问题（卖多少钱、怎么发货、有什么卖点）→ 建立商品档案 →（可选）拆解同赛道爆款 → 给你 3 版标题挑 → 写好描述并自动查一遍违规词 → 出 3 版封面风格给你挑 → 最后生成全套可上传的图片。

**人 × AI 分工**：人负责拍板（选标题、选风格、定价格）和提供真实信息（真实销量、真实背书，没有就不写）；AI 负责拆解、写作、排版、查违规词。

## 💬 日常用法

```text
生成详情图                                    → #1（封面 + 轮播图 PNG）
写商品描述 / 闲鱼文案                          → #2（3版标题 + 正文 + 合规自检）
拆解这个竞品（附上竞品截图或店铺文件夹）         → #3（拆解报告 + 5条行动建议）
帮我把上架都弄好                               → 三步串行（推荐首次用这个）
```

> 💡 拆解竞品的小技巧：在闲鱼 App 里找到卖同类商品的店铺，把**商品图一张张截图** + **文字描述复制**，放到一个文件夹里发给 AI（本项目 `template/店铺参考/` 就是标准格式的示范）。AI 会算出它的"想要率"、逐张拆封面、逐段拆文案。

## ✅ 适合 / ❌ 不适合

**✅ 适合**：做了 AI 技能包 / 教程资料想挂闲鱼卖的人；上架过但没人问、不会写文案不会做图的人；想在挂之前先搞懂"别人家为什么卖得好"的人。

**❌ 不适合**：想卖外挂、代刷、翻墙等违规商品——AI 会直接拒绝帮你写；想要"一键铺货几百个商品"的搬运党——本系统的合规检查恰好是来拦这个的。

## 📄 License

MIT

---

## 👤 关于作者 · 呼风唤雨的焕羽

我是**呼风唤雨的焕羽**，**工程合规 AI 创业者**——工程管理专业出身，从央企经营部走出来，现在经营一人公司（OPC），用 AI Agent 重做工程本行（合同审查 / 招投标合规 / 资质管理），全过程 [Build in Public](https://github.com/Huanyu-Hibiki)。本 skill 的完整手把手教程与实战演示，都在我的视频里：

<p>
  <a href="https://v.douyin.com/eBJ-mM7PvIg"><img alt="在抖音关注作者「呼风唤雨的焕羽」" src="https://img.shields.io/badge/%E6%8A%96%E9%9F%B3-%E5%85%B3%E6%B3%A8%E6%88%91-000000?style=for-the-badge&logo=tiktok&logoColor=white"></a>
  <a href="https://space.bilibili.com/338267911"><img alt="在哔哩哔哩关注作者「呼风唤雨的焕羽」" src="https://img.shields.io/badge/%E5%93%94%E5%93%A9%E5%93%94%E5%93%A9-%E5%85%B3%E6%B3%A8%E6%88%91-FB7299?style=for-the-badge&logo=bilibili&logoColor=white"></a>
  <a href="https://www.xiaohongshu.com/user/profile/677c7be200000000140313f7"><img alt="在小红书关注作者「呼风唤雨的焕羽」" src="https://img.shields.io/badge/%E5%B0%8F%E7%BA%A2%E4%B9%A6-%E5%85%B3%E6%B3%A8%E6%88%91-FF2442?style=for-the-badge&logo=xiaohongshu&logoColor=white"></a>
</p>

<div align="center">

🔍 **四个平台全同名，搜索「呼风唤雨的焕羽」看视频教程**

<img src="../assets/gzh-qrcode.png" width="520" alt="微信搜一搜：呼风唤雨的焕羽">

<sub>微信扫一扫 / 搜一搜「**呼风唤雨的焕羽**」关注公众号，第一时间获取 skill 更新与 AI 实战干货</sub>

</div>
