# State Management（状态文件读写约定）

被所有子 skill 引用。`.oracle-state.json` 是各子 skill 共享上下文的**单一来源**——任何运行时状态、累计指标、轨道注册都从这里读、写回这里。

---

## 文件位置

```
<user-content-project>/.oracle-state.json
```

**全局唯一**（项目根下一份，不建每作品 state）。**绝不**放到全局 `~/.claude/` 或 oracle-bone skill 包自己的目录——一个用户可能维护多个内容项目，每个项目独立状态。

---

## 完整 schema（v1.0）

```jsonc
{
  "schema_version": "1.0",
  "skill_version": "0.1.0",
  "mode": "cold-start",                    // cold-start | calibration（由 calibration 样本数派生显示，此字段为 init 时初始判定）
  "content_form": "opinion-video",         // 默认视频，可扩展（long-essay / short-text / podcast / mixed）
  "project_root": "<用户配置的绝对路径>",
  "platforms": ["bilibili", "douyin"],     // init 配置的发布平台集
  "typical_duration_seconds": 240,
  "target_publish_cadence_days": 2,        // 1=日更 / 2=隔日 / 7=周更 / null=灵活

  // ── 内容规划（init Phase 3 产出，见 content-funnel-protocol.md）──
  "plan_type": "dual",                     // single | dual | triple
  "tracks": {
    "definitions": [
      {
        "id": "reach",                     // 轨道 id（候选池/prediction 引用此 id）
        "funnel_layer": "破圈",             // 破圈 | 认知 | 转化（单一轨时可为 null）
        "name": "<用户命名的轨道名>",
        "rubric_section": "rubric_notes.md#track-reach",
        "rubric_version": "v0",
        "review_skill": "oracle-who-for",  // 流量/共鸣轨默认；转化轨为 oracle-open-source
        "success_metrics": ["播放", "涨粉", "同频评论"],
        "retro_windows_days": [3],         // 转化轨默认 [3, 7, 30]
        "mix_ratio": 0.4
      }
      // dual/triple 时有 2-3 个定义；mix_ratio 之和 = 1.0
    ],
    "mix_ratio_note": "<占比与修订记录，compass-retro 建议修订时追加>"
  },

  // ── rubric 与对标 ──
  "rubric_form_mismatch": false,
  "benchmark_status": "none",              // none | imported | pending
  "benchmark_name": null,
  "benchmark_sample_count": 0,
  "baseline_plays": null,                  // 首个有实绩样本时回填；bucket 边界派生依据

  // ── 校准池（按轨道分桶）──
  "calibration_samples_by_track": { "reach": 0, "convert": 0 },
  "calibration_samples_total": 0,          // 派生缓存（含 cross 0.5 计数）
  "calibration_samples_at_last_bump": {},  // by track

  // ── 数据与工具配置 ──
  "data_collection": "manual",             // manual | adapter
  "pool_status": "none",                   // none | markdown | notion | sqlite
  "data_layer": "markdown",                // markdown | sqlite
  "hooks_installed": false,
  "enabled_trend_sources": ["manual-paste"],
  "enabled_perf_adapters": [],

  // ── 时间戳 ──
  "last_bump_at": {},
  "last_bump_self_audited": false,
  "last_published_at": null,
  "last_published_file": null,
  "last_retro_at": null,
  "last_trends_run_at": null,
  "last_trends_added_count": 0,

  // ── 队列与会话 ──
  "consecutive_directional_errors": {},    // by track: ["high","low",...]
  "pending_retros": [],                    // [{file, track, due_windows:[{days, due_at, done}]}]
  "shoots": [],                            // [{work_folder, prediction_file, track, shot_at, script_hash_at_shoot, script_diff_pct, script_consistency, v2_prediction_written}]
  "in_progress_session": null,             // {type:"prediction", file, track, started_at, rubric_version}

  "initialized_at": "2026-08-19T15:00:00+08:00"
}
```

---

## 字段写入责任表（防止"谁该写这个字段"歧义）

| 字段 | 唯一写入者 | 何时写 |
|---|---|---|
| `plan_type` / `tracks.definitions` / `mix_ratio` | oracle-init（创建）/ 用户拍板后的 compass-retro 建议修订 | init Phase 3 落盘；修订须用户确认后同步 |
| `tracks.definitions[].rubric_version` | oracle-init（初值 v0）/ oracle-bump（按轨升版） | bump 落地时 |
| `calibration_samples_by_track` | oracle-retro | 每次该轨复盘成功落盘 +1（cross 各 +0.5） |
| `pending_retros` | oracle-publish（push，含窗口到期表）/ oracle-retro（勾掉完成窗口） | publish 时 push；retro 完成全部窗口后 remove |
| `shoots` | oracle-shoot（push）/ oracle-publish（remove） | 拍摄登记 / 发布登记 |
| `consecutive_directional_errors` | oracle-retro（push）/ oracle-bump（清空，按轨） | retro 判定偏差方向时；bump 落地时 |
| `in_progress_session` | oracle-predict（创建）/ oracle-publish（清除） | predict 写完文件时；publish 登记时 |
| `baseline_plays` | oracle-init（有历史则中位数）/ oracle-retro（首个实绩回填） | — |
| `last_bump_at` | oracle-bump（按轨记录） | bump 落地时 |
| `stage_constraint`（optional，`{value, basis, updated_at}`） | oracle-init（Phase 4.5 初判）/ compass-retro（Phase 3 回写，连续两次同向或用户拍板才切换） | init 时；每 2 期罗盘复盘时。旧 state 缺此字段按 `none` 兜底，不触发 migrate。判定表见主 SKILL.md「stage_constraint」段 |

**绝不允许**多个 skill 写同一字段——会导致状态语义破碎。如果未来需要新字段，先想好"谁是唯一写者"。

**prediction 文件是 track 的 source of truth**：`predictions/*.md` header 的 `Track` 字段为准；state 的分桶计数是聚合缓存。两者不一致时以 prediction 文件为准（oracle-retro 写入时同步校准）。

---

## 读写协议

### 读（任何 skill）

```python
# 伪代码
import json, os

state_path = os.path.join(project_root, ".oracle-state.json")
if not os.path.exists(state_path):
    # 不存在 = 用户没初始化，路由到 /oracle-init
    raise NeedsInitError()

with open(state_path) as f:
    state = json.load(f)

# 检查 schema_version 兼容
LATEST_SCHEMA = "1.0"  # see migrations/registry.md
if state.get("schema_version") != LATEST_SCHEMA:
    log_warning(f"schema 版本不匹配：state={state.get('schema_version')}, 期望={LATEST_SCHEMA}。建议跑 /oracle-migrate")
```

**关键纪律**：
- 读完不立刻关心字段缺失——用 `state.get(field, default)` 容错。新版 skill 引入新字段时旧 state file 会缺该字段，应优雅默认而非崩溃
- **绝不**在内存里 mutate state 后忘记写回——下游 skill 读到的是磁盘版
- **操作前先读全局验证已有事实**——用户说"X 已落盘"不等于没落盘，先 stat/read 验证再行动（协作契约 #7）

### 写（任何 skill）

```python
# 伪代码 — read-modify-write 模式
state = read_state()
state["calibration_samples_by_track"]["reach"] += 1
state["last_retro_at"] = now_iso()
write_state(state)

def write_state(state):
    state_path = os.path.join(project_root, ".oracle-state.json")
    tmp_path = state_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, state_path)  # atomic rename
```

**关键纪律**：
- **原子写**：写到 .tmp → rename。避免半写损坏的 state file
- **永远 indent=2**：人类可读，便于用户手改 + git diff
- **ensure_ascii=False**：保留中文字符不转 \uXXXX
- **写完再继续后续操作**：避免下游 skill 读到旧值

### 并发模型

预期场景：**单用户 + 单会话**。不做锁。如果两个会话并行操作同一个项目（罕见且不推荐）：可能出现写覆盖。未来需要时可加文件锁；当前不加，避免引入复杂度。

---

## state file 损坏 / 不一致的处理

| 症状 | 处理 |
|---|---|
| 文件不存在 | 提示"未初始化，请跑 /oracle-init"，**不**自动创建 |
| JSON 解析失败 | 提示"state file 损坏"，建议手动修复或备份 + 重新 init |
| schema_version 不识别 | 提示版本号 + 建议跑 [/oracle-migrate](../skills/oracle-migrate/SKILL.md)。SessionStart hook 会自动检测并提示 |
| `pending_retros` 含已删除的文件 | oracle-status 检测时安静移除，不报错 |
| `in_progress_session` 文件已不存在 | oracle-status 检测到 → 询问用户是否清理 |
| 分桶计数与 predictions/ 实际复盘数不一致 | oracle-status 报告差异。临时手改 state 即可；持续不一致是 bug，应加入 oracle-migrate 的 reconciliation step |
| mix_ratio 之和 ≠ 1.0 | oracle-status 报警，等用户拍板修正 |

---

## 与 git 的关系

`.oracle-state.json` **应该**被纳入 git：
- ✅ 它是项目配置 + 累计指标的快照
- ✅ git history 提供状态演化的完整轨迹
- ✅ 多设备同步靠 git push/pull
- ❌ **不**含敏感信息（cookie / API key 应放 `.env` 或 `.oracle-secrets.json`，单独 gitignore）

`.oracle-cache/` 目录**不应该**被纳入 git：
- 含 `usage.jsonl`（meta-logging 钩子的本地日志）
- 含 `trends-history.jsonl`（trend 抓取的去重缓存）
- 这些是设备本地状态，跨设备同步无意义

`/oracle-init` 应自动在用户项目根追加（不覆盖）`.gitignore`：

```
.oracle-cache/
.oracle-secrets.json
```

---

## 用户手改 state file 的边界

允许手改的字段：
- `enabled_trend_sources`（数组，决定 oracle-trends 用哪些源）
- `data_collection`（切换 manual ↔ adapter）

**不**建议手改的字段（会破坏不变量）：
- `calibration_samples_by_track` / `pending_retros` / `consecutive_directional_errors`（应通过 retro 流程更新）
- `tracks.definitions[].rubric_version`（应通过 bump 流程更新）
- `in_progress_session`（应通过 predict/publish 流程更新）
- `tracks.definitions` / `mix_ratio`（应通过"用户拍板的规划修订"更新，compass-retro 只提建议）

如用户确实想重置：建议**删除整个 .oracle-state.json + 重跑 /oracle-init**——这比手改单字段安全。

---

## Confidence label 派生表（**单一真值**）

被 oracle-predict / oracle-status / oracle-recommend / SessionStart hook 等共同使用。从**该轨道** `calibration_samples` 派生，所有 skill 用同一逻辑：

| `calibration_samples`（该轨） | confidence emoji + 标签 | 数值含义 | 用户该如何用 |
|---|---|---|---|
| 0 | 🔴 极低 | "占星级别，纯纪律训练" | 不要基于 composite 决定要不要发；写 prediction 是为了**采集数据**，不是为了**做决策** |
| 1-2 | 🟠 低 | "中枢 ±50%，方向感优于绝对数字" | 信"A 比 B 流量好"的方向，不信具体数字 |
| 3-5 | 🟡 偏低 | "中枢 ±40%，可作为参考之一" | bucket 排序可用，中枢点估计仍是猜测 |
| 6-10 | 🟢 中 | "中枢 ±25%，可参与决策" | 可作为"要不要发"的依据之一 |
| 11-20 | 🟢 较高 | "中枢 ±15%，rubric 形态稳定" | 可信中枢估计 |
| 21+ | 🔵 高 | "中枢 ±10%，可数据驱动 bump" | 进入数据驱动阶段 — bump 用回归而非直觉 |

> 上表的 ±X% 是**经验值**（源自参考项目的真实校准曲线），不是数学严格保证。新人账号的真实 ±X% 要等自己跑出 score-curve 才能验证。

**不要用这个表来 gating 任何功能**——所有 skill 在所有 calibration_samples 下都跑相同流程，只是输出里**显示**当前 confidence 等级。这是设计的核心原则。
