# AGENTS.md — PulseHub 获客 skill 集 · Agent 入口

> agent（opencode 等）启动时读本文件获得路由。人也可以当目录用。

## 这是什么

PulseHub 是一套完整的获客 skill 系统：从项目初始化到线索转化，16 个 skill 分 4 层，共享一个"项目大脑"（`~/.pulsehub/archive/<项目名>/`，随使用积累上下文）。

## 快速路由

用户说什么 → 调哪个 skill：

| 用户意图 | skill |
|---|---|
| "想做获客 / 找客户"（还没建档） | `pulse-router`（先诊断方向清晰度） |
| "初始化 / 新建项目" | `pulse-init` |
| "用户画像 / 我的客户是谁" | `pulse-insight` |
| "关键词矩阵 / 获客关键词" | `pulse-keywords` |
| "选题 / 不知道发什么" | `pulse-topics` |
| "写文案 / 小红书文案" | `pulse-copywrite` |
| "视频脚本 / 口播稿" | `pulse-script` |
| "私域承接 / 成交话术" | `pulse-private` |
| "抓线索 / 评论区获客" | `pulse-leads` |
| "去 AI 味 / 改自然点" | `pulse-humanize` |
| "复盘 / 体系体检" | `pulse-review` |
| "优化获客 skill / 体系升级" | `pulse-evolve` |
| "找帖子 / 监控竞品 / 追热点" | `pulse-discover` → `pulse-resolve` → `pulse-enrich` → `pulse-deliver`（4 段数据流水线，按序链式调用） |

**首次使用**：先跑 `pulse-router`（或直接 `pulse-init`）建立项目大脑，之后所有 skill 都读它。

**主平台收口**：内容主平台在 `pulse-init` Round 3 用 ABCD 确定并写入档案「主平台」字段；copywrite/topics/script/humanize 等下游 skill 一律读该字段，不各自问用户。

## 共享上下文（项目大脑）

- 位置：`~/.pulsehub/archive/<项目名>/`，6 个文件（项目档案 / 人群语料库 / 爆款素材库 / 话术资产 / 数据反馈 / 个人风格）
- 模板源：仓库 `_archive/` 目录
- 每个业务 skill 启动时先读需要的文件，产出后写回并更新《项目档案.md》的累积产出索引
- 设计详见 `_archive/README.md`

## 硬规则（全库通用，违反 = 事故）

1. **登录墙 / 验证码 → 停下让用户处理**，不自作主张换工具链（pulse-discover P1）
2. **逐页抓取每条间隔 2-3 分钟**模拟人工，优先平台 API 批量拿数据（pulse-enrich P1）
3. **永不自动爬取评论区**——半自动模式默认，自动化需用户明确授权 + 严格限流（pulse-leads）
4. **绝不编造用户原话 / 案例数据**——语料库没有就标 `[待补充]`（所有内容 skill）
5. **多平台采集不自行截断**——所有平台跑完才进分析（pulse-discover P6）
6. **项目定制协议优先于默认结构**——档案「定位协议」字段登记的约束文件说了算

## 目录结构

```
pulsehub/
├── pulse-router/ ... pulse-review/   # 16 个 skill（各含 SKILL.md）
├── _archive/     # 项目大脑模板（6 个文件）
├── _shared/      # 共享资源：recipes（平台攻略）/ scripts（脚本）/ signals（信号定义）
└── _core/        # pulse-resolve CLI 源码（需要 pnpm 环境；不可用时按 SKILL.md 的 Fallback 手工解析）
```
