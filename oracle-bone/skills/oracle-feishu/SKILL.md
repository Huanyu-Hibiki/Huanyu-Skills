---
name: oracle-feishu
description: 把 oracle-bone 的结构化数据同步到飞书多维表格做可视化与监测——五张表（作品总表/候选池/校准样本/热点与源健康/状态快照）从本地文件确定性推导，经用户自配的飞书 CLI 推送。**单向只读镜像**：本地文件是唯一事实源，绝不从飞书回写。前置 = 用户在 Agent 配好飞书 CLI + `.oracle-secrets.json` 写 feishu 块（不入 git）。触发词："同步飞书"/"飞书看板"/"推飞书"/"feishu sync"。
argument-hint: "[— tables: episodes,candidates,...] [— dry-run]"
allowed-tools: Bash(*), Read, Write, Glob
---

# /oracle-feishu — 飞书多维表格同步（只读镜像）

把链路里已经结构化的数据推到飞书多维表格，用飞书自带的视图/图表做可视化和监测。**定位铁律：飞书只是展示层**——本地文件（state / candidates.md / predictions / trends-history）是唯一事实源，本 skill 单向推送、按稳定 id 幂等 upsert、**绝不从飞书回写任何字段**（防双源冲突，协作契约 #7 精神）。

## 数据梳理（五张表，全部从本地文件推导）

| # | 表 | 一行 = | 字段 | 数据源 | 可视化用途 |
|---|---|---|---|---|---|
| 1 | **episodes 作品总表** | 每期作品 | article_id / 标题 / 轨道 / rubric 版本 / composite / 预测 bucket / 中枢 / 实际播放 / 偏差倍数 / basis(v1/v2) / 状态(在途·已拍·已发·已复盘) / shot_at / published_at / URL / 平台 | predictions/*.md header + `## 复盘`、state.shoots、candidates entry | 预测 vs 实际散点、分轨漏斗、偏差趋势 |
| 2 | **candidates 候选池** | 每条候选 | candidate_id / 标题 / source / source_tier / track / tier / composite / 热度 / 时效 / read_status / 回流标记 / 入池时间 / rejected_reason | candidates.md + trends-history.jsonl | 选题漏斗（抓到→入池→起稿→发布）、分轨占比 vs mix_ratio |
| 3 | **calibration 校准样本** | 每次复盘 | article_id / 轨 / composite / 实际量级 / bucket 是否命中 / 偏差方向 / confidence / 复盘日期 / 一句关键教训 | 已复盘 predictions 的 `## 复盘` 段 | 校准曲线（composite vs 实绩）、bucket 命中率 |
| 4 | **trends 热点台账** | 每条抓过的热点 | date / 标题 / source / source_tier / 热度 / 是否入池 / 回流标记 / rejected 原因 | trends-history.jsonl | 热点频次、信源贡献度、E 层线索命中率 |
| 5 | **snapshots 状态快照** | 每次同步一天一条（append） | date / buffer 数 / 待复盘数 / 各轨样本数 / confidence / stage_constraint / 源健康摘要（trends 覆盖账本结论） | state + 当轮 trends 汇总 | 账号健康时间序列 |

字段缺失 → 推空值，**不猜不补**；skill 未跑过的产物（如没跑过 retro）→ 对应表推零行是正常状态。

## 前置（用户一次性配置，本 skill 不代配凭据）

1. **飞书 CLI**：用户在 Agent 环境自行配置可用的飞书命令行（官方 CLI / 自建脚本 / MCP 转命令行均可）——本 skill 只按下面的调用契约执行，不绑定具体实现
2. **`.oracle-secrets.json`**（项目根，已 gitignore）写 feishu 块：

```json
{
  "feishu": {
    "cli_cmd": "feishu bitable record upsert --app {app_token} --table {table_id} --records {file}",
    "app_token": "bascnXXXX",
    "tables": {
      "episodes": "tblXXXX", "candidates": "tblXXXX", "calibration": "tblXXXX",
      "trends": "tblXXXX", "snapshots": "tblXXXX"
    },
    "enabled_tables": ["episodes", "candidates", "snapshots"]
  }
}
```

- `cli_cmd` 是**命令模板**：`{app_token}` `{table_id}` `{file}` 三个占位符由本 skill 替换后经 Bash 执行；退出码 0 = 该表成功
- 表结构（字段名/类型）用户在飞书侧自建一次（按上表字段清单）；本 skill 只推行数据不建表——若用户 CLI 支持建表可自行用，与本 skill 无关
- 凭据绝不入 git、不进对话记录、不写 state

## Workflow

### Phase 0: 预检（四态）

| 检查 | 不过则 |
|---|---|
| state 存在 | 🔴 提示先 /oracle-init，退出 |
| `.oracle-secrets.json` feishu 块存在且 cli_cmd 有三占位符 | ❌ **blocked**：给上面配置模板让用户填（这是用户动作，不代配），退出 |
| CLI 可执行（跑 `cli_cmd` 去占位符的 `--help` 探测或直接首表试推） | ❌ blocked：报"CLI 不可用（命令/路径错误）"，退出 |
| 推送中 auth 失效 / 限流 | ❌ failed：如实报哪张表失败 + CLI 原始报错，**不静默跳过** |

### Phase 1: 推导行数据

按用户 `—tables` 参数（缺省 = enabled_tables）逐表推导：

- **episodes**：glob 各作品 `predictions/*.md` 读 header + `## 复盘`；state.shoots 补 shot_at 与状态；已发布读 publish 登记的 URL/平台
- **candidates**：解析 candidates.md 各 H3 entry（含 source_tier / 回流标记）；rejected 条目带原因
- **calibration**：只读含 `## 复盘` 段的 prediction 文件
- **trends**：读 `.oracle-cache/trends-history.jsonl`
- **snapshots**：当日一条（当日已有 → 覆盖该行，幂等）

行数据写入 `.oracle-cache/feishu-export/<table>.json`（JSON 数组）——`— dry-run` 到此为止：展示每表行数 + 首行样例，不调 CLI。

### Phase 2: 🔴 CHECKPOINT（数据出境门）

首次同步（或表结构变更后）：展示五表清单 + 各表行数 + 字段映射 + **数据出境提示**（内容数据将存到你配置的飞书应用/租户），等用户确认。之后常规同步按 `interaction_level` 执行（full-auto 可直接推——首次确认门不豁免）。

### Phase 3: 逐表推送 + 汇总

逐表替换占位符执行 `cli_cmd`，汇总按信封四态：

```
📤 飞书同步完成（3/5 表）
✅ episodes 12 行 / ✅ candidates 47 行 / ✅ snapshots 1 行
❌ calibration — CLI 报错：<原文>（auth 失效？）
⏭️ trends — 不在 enabled_tables
失败表修复后重跑 "同步飞书 — tables: calibration" 即可（幂等，不会重复插行）
```

## Key Rules

1. **单向镜像**——只推不拉，绝不从飞书回写本地
2. **幂等 upsert**——episodes/candidates/calibration 按稳定 id，snapshots 按日期覆盖
3. **凭据三不**——不入 git、不进对话、不写 state
4. **确定性推导**——行数据只从本地文件推导，缺失推空值不猜
5. **首次确认门**——数据出境确认不因 full-auto 档豁免

## Refusals

- 「从飞书把候选池拉回来合并」 → 拒绝。单向镜像；飞书侧的改动不回流（展示层标注/涂色随便用，不影响事实源）
- 「帮我配飞书应用的 app_secret」 → 用户动作。本 skill 只读 `.oracle-secrets.json`，不代配凭据
- 「把 predictions 正文也推上去」 → 越界。只推结构化字段；正文留在本地（数据最小化）

## Integration

- 上游：任意时刻可推；建议 publish / retro / trends 之后顺手同步一次（数据最新鲜）
- 下游：无（展示层终点）
- oracle-status 仍是本地快查入口；飞书侧适合横向图表与分享
