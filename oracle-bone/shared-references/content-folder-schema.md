# Content Folder Schema（作品目录标准结构）

> **被 oracle-seed 引用**。oracle-seed 输出 draft 前必须按此 schema 初始化作品目录，避免后续产物散落到错误位置。
>
> **强制约束**：每期作品的所有产物（draft / prediction / brief / cover prompt / 发布文案等）必须落到对应子目录，禁止散落到项目根。

---

## 路径约定

作品目录直接放在**项目根**下，用编号 + 标题命名：

```
<NNN>_<工作标题>/              # NNN = 三位递增编号（001, 002, ...），文件夹名用工作标题
├── scripts/                   # 内容脚本（oracle-seed Phase 4 输出；简介/置顶评论 append 到定稿末尾）
├── predictions/               # 盲预测文件（oracle-predict 输出，oracle-retro 追加复盘段）
├── audience-brief.md          # 受众档案（oracle-who-for 输出——流量/共鸣类轨道）
├── open-source-audit.md       # 自我开源审查档案（oracle-open-source 输出——转化类轨道）
├── prompt/                    # 统一 prompt 管理
│   ├── cover/                 # 封面 prompt（oracle-cover 输出）
│   │   ├── _base.md           # 主体内容（构图/风格/文案），跨平台共用
│   │   └── prompt-<平台>.md    # _base + 平台比例派生（如 prompt-bilibili.md / prompt-douyin.md）
│   ├── _README.md             # prompt 管理规范
│   └── [video|audio|animation]/  # 可选扩展位：AI 视频/音频/动画 prompt
├── derivatives/               # 衍生内容（oracle-derivative 输出：图文/短文/切片稿）
└── [制作管线目录]              # 可选：用户自己的制作产物（见下方"制作管线边界"）
```

### 编号约定

- `<NNN>` 从 state 的已登记作品数派生（001 起，递增）
- 同一项目内编号**不复用**——即使某期废弃，编号跳过（追溯性优先）
- 废弃作品目录不删，改名为 `<NNN>_<标题>_abandoned/` 留档

## 命名约定

### 文件夹名（作品标题）
- 用**工作标题**（oracle-seed 讨论确定的角度），不要等最终标题再命名
- oracle-title-pick 选定最终标题后允许改文件夹名追溯发布版标题（Windows 注意：文件夹名避开冒号等非法字符；rename 被进程锁住时用 copy+delete fallback，见 `references/platform-notes.md`）
- 例：`003_从龟壳到算法/`（工作版）→ `003_古人占卜我预测/`（发布版）

### 文件名
- `<YYYY-MM-DD>_<id>_<short-title>.md` —— scripts/ 和 predictions/ 一致（见 blind-prediction-protocol.md 的文件名约定）
- `prompt-<平台>.md` —— prompt/cover/ 等子目录

### ID 稳定性
- 作品 ID 用 candidate id（12 位 hash），与 script/prediction 文件名一致
- 重命名文件夹不影响追溯（git history + 内部文件 ID 关联）

## 与 oracle-bone 各阶段产物的对应

| 阶段产物 | 输出路径 |
|---|---|
| 脚本 draft | `scripts/<date>_<id>_<short>.md` |
| 改稿 v2 | `scripts/<date>_<id>_<short>_who-for-v2.md`（或 `_open-source-v2.md`）|
| 受众档案 | `audience-brief.md`（作品目录根，流量/共鸣轨） |
| 开源审查 | `open-source-audit.md`（作品目录根，转化轨） |
| 预测 v1 | `predictions/<date>_<id>_<short>.md` |
| 预测 v2/v3 | 同文件 append `## 预测 vN` 段 |
| 复盘 | 同文件 append `## 复盘` 段（多窗口轨道分 T+Nd 小节） |
| 封面 prompt | `prompt/cover/_base.md` + `prompt-<平台>.md` |
| 发布文案 | `scripts/<定稿>.md` 末尾 `## 发布文案` 段（**不建独立文件**） |
| 置顶评论 | `scripts/<定稿>.md` 末尾 `## 置顶评论` 段 |
| 衍生内容 | `derivatives/<形式>_<短名>.md` |

## 制作管线边界

oracle-bone **只管链路产物**：`scripts/` `predictions/` `prompt/` `derivatives/` + 两份 review 档案。

制作管线产物（录制素材 / 剪辑工程 / 成片 / 字幕 / 封面图）**不归 oracle-bone 管**，但建议放在同一作品目录下的用户自选子目录（如 `production/` 或 Raw/Rough/Final 等），保持"一期一个文件夹"的完整性。具体结构由用户的制作工具链决定，skill 不做约束、不写入、不移动。

**oracle-title-pick 改名时的连带**：`mv` 作品目录 + `mv` scripts/ 定稿 + 同步 prediction header 的 Title/Script Path 字段——但**不碰**制作管线子目录的内容（只随文件夹整体移动）。

## 与全局文件的关系

部分全局文件**不放在作品目录**，而是放在项目根（oracle-init 时建）：

| 全局文件 | 位置 |
|---|---|
| `.oracle-state.json` | 项目根（全局唯一） |
| `user-profile.md` / `content-plan.md` / `audience-profiles.md` | 项目根（init 产出，跨期共享） |
| `rubric_notes.md` | 项目根（按轨道分节） |
| `script_patterns.md` | 项目根（按轨道分节） |
| `candidates.md` | 项目根（oracle-trends / oracle-seed 累积） |
| `benchmark.md` | 项目根（oracle-learn-from 产出） |

这些是跨期的元数据，每期作品共享。**作品目录只放本期作品的产物**。

## oracle-seed 初始化步骤

oracle-seed 在确定选题后，**立即**初始化作品目录：

```powershell
# 工作标题 + 编号作为文件夹名（用户确认后）
$base = "<项目根>/<NNN>_<工作标题>"

# 标准子目录（一次性全建）
$dirs = @(
    "$base/scripts",
    "$base/predictions",
    "$base/prompt/cover",
    "$base/derivatives"
)

foreach ($d in $dirs) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
```

后续所有产物按本 schema 落到对应子目录。

## 演进原则

- 本 schema 是**当前约定**，不是绝对真理
- 新增工具/新阶段产物时，扩展 `prompt/` 或新增顶层子目录
- 旧期作品目录结构差异**不改**（retro 时如发现某期漏建目录，单独补即可）
- schema 修订走 git commit + 在 changelog 段记录
