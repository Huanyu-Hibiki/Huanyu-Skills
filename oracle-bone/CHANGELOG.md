# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — v0.1.0 全量构建（2026-08-19）
- 骨架：主 SKILL.md（总协议 + 26 子 skill 路由表 + 三原则 + 轨道机制 + 协作契约）+ README + install/uninstall + LICENSE + .gitignore
- shared-references 12 份核心协议 + migrations/registry.md（schema 1.0）
- 26 个子 skill 全量（主链 7 / 选题打磨 8 / review 质检 5 / 支撑 6）
- starter-rubrics 5 份（opinion-video 已拟合参考版 / zero 等权 / conversion-video 泛化版 / 长文短文扩展位）
- templates 14 份（含三份档案模板 user-profile / content-plan / audience-profiles）
- hooks 三件套（prediction-immutability / session-start / meta-logging）
- tools/score-curve.py + adapters 四类（trend-sources 6 源 / perf-data / candidate-pool / script-extraction）
- references 5 份种子（做号定位提炼 / dbskill 精华 / 漏斗理论 / 转化轨手册 / 平台坑备查）+ examples

### Added — 数据分析基础设施（2026-08-19，第二批）
- **tools/data_normalizer.py**：四平台数据统一归一器（字段别名映射 / "1.2万"多值解析 / 跳出率口径标注 3s vs 2s / 零值过滤 / 标题清理）——actual_data 从此只有一种 schema（根治 bump P5 schema 漂移坑）
- **tools/snapshot_store.py**：SQLite 采集快照库（runs + snapshots 时序模型，latest vs prev diff 出播放增量/新作/互动率变化）
- **tools/dashboard.py**：分析引擎——五维增量指标提取 + quantile 分位阈值 + 规则建议（高互动低播放→复刻/衍生；高播放低互动→互动触发器/who-for；增长最快旧作→apprentice 拆解）+ A/B 粗分类
- **adapters/perf-data/auto-collect/**：Playwright 一键采集（四平台 .py 采集器：监听后台 API 响应 + DOM 兜底双源合并 / 复用本机浏览器 Profile / 授权保守检查 / 断点续跑 / --auth-only 首次授权 / --debug 校准模式）。**设计模式参考 data-scientist-community（AGPL-3.0，作者赵逍遥），clean-room 重写**——完整管线 collect → normalize → snapshot → dashboard
- 接线：oracle-retro Path B 改三级数据源（auto-collect → 手动导出归一 → manual paste）；oracle-compass-retro Phase 1/2 自动拉快照库 + quantile 建议联动 Phase 3/6
- 单测：归一器（万单位/逗号/口径/零值/标题话题清理）+ 快照 diff（增量/新作）+ 分位建议 + A/B 粗分——全部通过

### Added — 视频号采集（2026-08-19，第三批）
- `platforms/wechat.py`：视频号助手采集器（channels.weixin.qq.com）——宽容解析 + DOM 兜底；**候选端点态**，首跑 `--debug` 按 urls.log 校准 ENDPOINTS（README 有四步流程）
- collect.py：注册 wechat 平台 + `--debug` 新增全量响应 URL 日志（`<platform>-urls.log`）——端点校准的工作流基建
- data_normalizer：视频号字段别名（推荐量→收藏量）+ 平台探测关键词（视频号/wechat/channels/微信）
- oracle-publish：URL 识别表补 `channels.weixin.qq.com → wechat`
- 已覆盖平台：抖音 / 小红书 / B站 / 快手 / **视频号**（5 平台）

### Added — 发布链接自动解析（2026-08-19，第四批）
- **tools/link_resolver.py**：发布链接三合一——短链重定向解析（v.douyin.com/b23.tv/xhslink.com）→ 平台识别 + 内容 ID 提取（BV号/aweme_id/note_id）→ 标题抓取（B站走公开 view API 最稳；其他抓 og:title/`<title>` + 平台后缀清理）→ difflib 模糊匹配 shoots 队列 + 未发布 prediction（含"解析标题是完整版 vs 作品名短版"的包含关系加分）
- **oracle-publish Phase 1 重构**：Step 1a 链接自动解析（用户粘 N 条链接 → 确认表"链接→平台→标题→匹配作品(score)"→ 确认即登记）；Step 1b 手动流程保留为降级路径；Platform ID 直接复用解析的 content_id
- 纪律：score≥0.55 标 ⭐ 仍需用户确认；标题抓取失败不阻塞（平台+ID 已有）；无网络回退手动
- 测试：平台检测 8 例 / ID 提取 / 标题清理 / 模糊匹配（含 B站真网解析）全部通过

### 实机校准完成 — 四平台数据全通（2026-08-19，第五批）
- **授权修复**：`--auth-only` 循环不再 unauthorized 即退出——浏览器保持打开等本人扫码，authorized 自动继续（用户实机纠错）
- **B站校准**：卡片 = `.article-card`，BV+标题挂 `<a href>` 链接（不在主文本流）；headless 会被风控给空壳页 → 采集默认 headed
- **抖音校准**：列表在响应顶层 `items[]`；`metrics{}` 直带五维增量指标（cover_click_rate/bounce_rate_2s/completion_rate_5s/completion_rate/avg_view_second）+ view_count/like/favorite/subscribe——**五维闸门数据源就位**
- **小红书校准**：笔记管理页 = `/new/note-manager`（非发布页）；列表 API `note/user/posted`；**框架级修复：监听先于导航挂载**（首屏 API 在页面加载时发出，晚挂整段错过）
- **视频号校准**：post_list 状态码 **201 是正常业务响应**（framework 收 200+201）；objectId 带 `export/` 前缀取尾段；进入页面需点"内容管理→视频"触发 SPA 路由（新增平台 `post_navigate` 钩子）
- **反垃圾修复**：DOM 兜底行作品 ID 必须匹配真实 ID 形态（纯数字≥6/BV号/十六进制）——"时长冒充 ID"垃圾行不再污染合并
- **实测结果**：B站 8 条 + 抖音 8 条（含五维）+ 小红书 9 条 + 视频号 7 条 = **32 条入快照库**，dashboard quantile 建议正常输出

