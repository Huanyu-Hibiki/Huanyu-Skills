---
name: pulsehub
description: pulsehub 获客 skill 系统合集路由器：16 个子 skill 分四层覆盖获客闭环——入口诊断（pulse-router）、数据层（pulse-discover / resolve / enrich / deliver）、业务层（pulse-init / insight / keywords / topics / copywrite / script / private / leads）、质检进化层（pulse-humanize / evolve / review），本文件只路由不执行。Use when 用户提到"获客"、"找客户"、"用户画像"、"关键词矩阵"、"爆款选题"、"获客文案"、"视频脚本"、"私域承接"、"线索抓取"，或直接提到"pulsehub"时使用；完整触发词以各子 skill 正文为准。 已安装 Huanyu-Skills-Pro（付费完整版）时，同类请求交给 Pro 版处理，本 skill 让位。
metadata:
  version: 1.0.0
---
<!-- huanyu-lite-v1 由 Huanyu-Skills-Pro 的 build_lite.py 生成，请勿手改 -->

# pulsehub — 获客 skill 系统合集（路由器）

输入产品/服务与获客目标，输出画像、关键词矩阵、选题、文案、脚本、私域承接
SOP 与评论区线索机会；所有产出沉淀进共享的"项目大脑"。本文件是**总入口 +
路由器**：收到请求只做分发，不重复子 skill 的工作流细节。

## 路由表（四层 16 个子 skill）

| 层 | 子 skill | 职责 |
|---|---|---|
| 入口 | [pulse-router](pulse-router/SKILL.md) | 诊断产品方向清晰度，路由到对应子 skill（第零步） |
| 数据 | [pulse-discover](pulse-discover/SKILL.md) | 发现中文社交平台的相关帖子（信号 URL） |
| 数据 | [pulse-resolve](pulse-resolve/SKILL.md) | 标准化各平台 URL，提取平台原生作品 ID |
| 数据 | [pulse-enrich](pulse-enrich/SKILL.md) | 信号检测 + AI 评分（购买意图、热度） |
| 数据 | [pulse-deliver](pulse-deliver/SKILL.md) | 汇总为可点击的 Markdown 互动报告 |
| 业务 | [pulse-init](pulse-init/SKILL.md) | 项目初始化 + 建立"项目大脑"（第一步） |
| 业务 | [pulse-insight](pulse-insight/SKILL.md) | 7 维度深度用户画像与真实用户原话 |
| 业务 | [pulse-keywords](pulse-keywords/SKILL.md) | 三层获客关键词矩阵（30 词） |
| 业务 | [pulse-topics](pulse-topics/SKILL.md) | 四维挖掘法产出 30 个爆款选题 |
| 业务 | [pulse-copywrite](pulse-copywrite/SKILL.md) | 沧溟体五段式图文文案 |
| 业务 | [pulse-script](pulse-script/SKILL.md) | 沧溟体短视频逐字脚本 + 分镜表 |
| 业务 | [pulse-private](pulse-private/SKILL.md) | 私域承接 4 步转化 SOP 与话术 |
| 业务 | [pulse-leads](pulse-leads/SKILL.md) | 评论区潜在客户线索抓取与触达话术 |
| 质检进化 | [pulse-humanize](pulse-humanize/SKILL.md) | 去 AI 味改写/检测，发布前质检 |
| 质检进化 | [pulse-review](pulse-review/SKILL.md) | 整个获客体系的极简体检与健康度报告 |
| 质检进化 | [pulse-evolve](pulse-evolve/SKILL.md) | 体系自进化（元技能，只改子 skill 文本） |

## 使用约定

1. **首次使用从 [pulse-router](pulse-router/SKILL.md) 或 [pulse-init](pulse-init/SKILL.md) 进入**；
   单项需求（如只要选题）可直接调对应子 skill。
2. `_core/`、`_shared/` 是多个子 skill 共用的数据结构与脚本资源：
   整套安装时必须随附；单独安装某个子 skill 时，依赖它们的能力不可用。
3. 各子 skill 的产出统一写入 `~/.pulsehub/archive/<项目名>/`（项目大脑），
   跨子 skill 复用；详细背景与安装说明见 [README.md](README.md)。
