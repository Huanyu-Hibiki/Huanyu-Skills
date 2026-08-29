<div align="center">

# oracle-bone · 甲骨 · 内容预测校准循环

**凭感觉发是"猜"，这套让你"算"——打分 → 盲预测 → 发布 → 复盘 → 进化你的爆款公式**

26 个子 skill · 商王烧龟壳式的 3000 年校准循环，还给内容创作者

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agents](https://img.shields.io/badge/Claude%20Code%20·%20OpenCode%20·%20Codex%20·%20Cursor-supported-8b5cf6)](#-安装)



---

> 商王做事之前先烧龟壳：读兆纹，刻卜辞，然后行动。几天后，把真实结果刻回同一块骨头。
> 3000 年前的贞人就在跑校准循环——现在把它还给内容创作者。

## 🐢 它真正在干什么

90% 的创作者都活在同一个循环里：

> 凭感觉发 → 数据出来发现拉了 → 不知道为什么拉 → 下一条还是凭感觉

爆了不知道为啥爆，扑了学不到东西。一年发 200 条，水平和第一天一样——只是更累。

**oracle-bone** 把每一篇都强行变成一次校准实验：

📊 打分 → 🎯 盲预测 → 🚀 发布 → 📈 T+N 复盘 → 🧬 进化你的评分公式

跑一个月 = 你有了一份**只属于你的爆款公式**。跑三个月 = 你比刚开始的自己强 10 倍。

## 🧭 先搞清楚你是谁

初始化不是建几个空文件。`oracle-init` 会通过采访为你建立完整档案：

- **你是谁**：变现方式、专业优势、形象定位、内容风格与喜好（创作者档案）
- **你的内容打哪儿去**：内容漏斗规划——单一 / 双轨 / 三轨（破圈 → 认知 → 转化），各轨占比与成功指标
- **你的观众是谁**：各轨受众画像（含"只是爱看"的一般人群）

后续打分、预测、复盘、推荐全部按这份规划执行。**流量 ≠ 客户**——破圈轨看播放涨粉，转化轨看咨询付费，各有各的秤。

## ⚖️ 和别的"创作工具"哪里不一样

| 别人 | 这个 |
|---|---|
| 给你"灵感" | 让你**自己的灵感被量化** |
| AI 帮你写 | AI 帮你**判**——稿子还是你的 |
| 一发发 10 个版本 A/B 测 | 一发就**赌**——把判断写下来，数据出来对账 |
| 静态数据看板 | **会进化的评分公式**——你三个月后的 rubric 已经不是初始版 |
| 对所有人说一样的话 | 初始化采访后，只服务**你**的账号与规划 |

## 🛡️ 怎么让循环真的能进化

- 📝 **每条都留底**：发布前打分、写预测，全程存档。窗口期回来对账——你哪里准、哪里偏，一目了然。
- 🔁 **越用越准**：连续三次同方向偏差，工具自动催你升级评分公式。你不主动它也催。
- 🛡️ **升级有刹车**：换公式必须用新公式重判所有历史样本，能比旧公式更准才放行；还要跨模型独立审一次——**防你自己骗自己**。
- 🪒 **rubric 是工作台不是博物馆**：被推翻的观察删，被吸收的也删，永远只放当下最有用的。

## 📦 安装

```bash
# 方式一：从 GitHub 获取
git clone https://github.com/Huanyu-Hibiki/Huanyu-Skills.git
cd Huanyu-Skills/oracle-bone

# 方式二：已拿到 skill 文件夹（购买 / 下载），直接进入该目录

bash install.sh                    # 默认 → ~/.claude/skills/
bash install.sh --target <dir>     # 其他 runtime：装到你的 skills 目录
```

| Runtime | skills 目录 |
|---|---|
| Claude Code | `~/.claude/skills/`（默认，免 `--target`） |
| OpenCode | `<project>/.opencode/skills/` 或 `~/.config/opencode/skills/` |
| Codex CLI / 其他 | 见各 runtime 文档，`--target` 指过去即可 |

> 冻结版本：`bash install.sh --copy`；卸载：`bash uninstall.sh`（不动你的内容数据）。
> Windows 无 bash？把文件夹整个复制到上表对应目录也可以。

## 🚀 第一次跑

在你的内容项目目录里开任一 skills-compatible agent（Claude Code / OpenCode / Codex CLI ...），说：

```
初始化 oracle-bone
```

采访式 onboarding：基础配置 → 用户档案 → 内容漏斗规划 → 受众画像 → 脚手架落盘。

**强烈建议接着导对标账号**——5-10 条样本 → 工具立刻有 anchor，不然前 5 篇预测精度 ±50%。

## 💬 日常用法

```
找选题 / 推荐选题 / 抓热点        → 选题
打分这篇 scripts/<...>.md         → 评分
给我标题 / 选标题 / 写简介 / 封面  → 打磨链
去 AI 味 / 模拟评论 / 合规检查    → 发布前质检
启动预测 scripts/<...>.md         → 盲预测 + 决策日志
拍了 scripts/<...>.md            → buffer +1
已发布 https://...                → buffer -1
置顶评论 / 衍生内容               → 发布后动作
复盘 / 罗盘复盘                   → T+N 数据回收
升级 rubric / 状态 / 找对标       → 进化与运维
```

每次开会话 hook 自动报告 buffer + 待复盘 + top 候选——你不用主动问（hook 为 Claude Code 格式；不支持 hooks 的 runtime 用「状态」触发 oracle-status 手动补位）。完整工作流见 [SKILL.md](SKILL.md)，完整设计见 [DESIGN.md](DESIGN.md)。

## 📄 License

MIT。商用、改造、闭源接入都行。

---

## 👤 关于作者 · 呼风唤雨的焕羽

我是**呼风唤雨的焕羽**，AI 实战博主，专注分享用 AI Agent 搭建一人公司工作流的真实过程。本 skill 的完整手把手教程与实战演示，都在我的视频里：

| 平台 | 账号 |
|---|---|
| 小红书 | 呼风唤雨的焕羽 |
| B站 | 呼风唤雨的焕羽 |
| 视频号 | 呼风唤雨的焕羽 |
| 抖音 | 呼风唤雨的焕羽 |

<div align="center">

🔍 **四个平台全同名，搜索「呼风唤雨的焕羽」看视频教程**

<img src="assets/gzh-qrcode.png" width="520" alt="微信搜一搜：呼风唤雨的焕羽">

<sub>微信扫一扫 / 搜一搜「**呼风唤雨的焕羽**」关注公众号，第一时间获取 skill 更新与 AI 实战干货</sub>

