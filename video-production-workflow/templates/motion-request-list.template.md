---
generated_by: video-plan
generated_at: <ISO 8601>
source: Rough/rough_cut_manifest.md + Rough/missing_materials.md
schema_version: 0.1
status: approved
---

# Motion / B-roll Request List

> 这是基于粗剪实际时间码的执行令。前期 `remotion_candidate_list.md` 只是候选，不能直接当作实现清单。

| 请求 ID | 对应镜号 / 时间 | A-roll 状态 | 覆盖模式 | 目的 | 内容 | 类型 | 时长 | 分辨率 / FPS | 透明通道 | 推荐引擎 | 数据 / 文案 | 优先级 | 状态 |
|---|---|---|---|---|---|---|---:|---|---|---|---|---|---|
| MOTION-001 | `<EP001-S08 / 02:05-02:35>` | `<OBS 保留>` | `<B-only>` | 解释 | `<产品能力对比>` | `<流程 / 数据 / UI / 关键词>` | 6 | `1920x1080@30` | 是 | Remotion | `<props/data>` | 高 | approved |

覆盖模式：`A-only` / `B-only` / `AB-live:<B-base-A-PiP / A-base-B-overlay / B-base-A-cutout / AB-split>`，沿用分镜表声明（见 `shared-references/motion-brief-standards.md` 第 6 节）。

## 实现计划要求

每个请求实现前必须说明：

- composition 名称；
- 目的、格式和时长；
- 覆盖模式与布局（透明 overlay / 全屏 insert 与放置区）；
- 时间线和布局（短动效按五相位交叠规划，见 `shared-references/motion-brief-standards.md`）；
- props 和数据来源；
- 技术库选择；
- 输出格式和命令；
- 风险、假设和 B-roll 装配时间。

## 已解决候选

| 候选 ID | 原因 | 解决方式 |
|---|---|---|
| `<candidate>` | 已由 OBS / Stock / Filmora 解决 | `<actual asset>` |
