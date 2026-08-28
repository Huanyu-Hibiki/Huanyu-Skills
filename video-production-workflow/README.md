# 视频制作管线 / Video Production Workflow

> 把“写完稿之后怎么做成片”变成有阶段、有交接、有审核闸门的制作系统。

## 它解决什么问题

常见的视频制作问题不是缺一个工具，而是工具之间没有清晰的交接：

- 分镜表没有告诉剪辑师哪些画面是 A-roll、哪些是 B-roll；
- 转录字幕、校对字幕和精剪 SRT 混在一起，时间码逐步失真；
- 剪映草稿、下载素材、Remotion 工程和最终成片散落在不同目录；
- B-roll 只是按关键词找素材，没有先判断这句话是否值得插画面；
- 动效工具直接参与整片剪辑，导致时间线、字幕和素材责任混乱。

这套合集把流程固定为：

```text
终稿
  → 分镜与素材路由
  → A-roll 转录粗剪
  → 字幕校对
  → 剪映 Draft
  → 外部素材获取
  → 剪映精剪并输出 SRT
  → B-roll 机会分析
  → B-roll 生成
  → B-roll 装配与成片 QA
```

## 第一次使用

先初始化唯一 Python 环境：

```powershell
cd "<合集根目录>"
uv venv .venv --python 3.11
uv sync
```

合集根目录 = 包含 `SKILL.md` 和 `scripts/` 的目录（部署位置因机器而异）。本机密钥放 `.env`（已被 git 忽略，参考 `.env.example` 配置）；**通过复制文件夹分发本合集时，先删除 `.env`**——里面是本机 API key。

在视频项目目录或制作管线目录中调用：

```text
初始化视频制作管线
```

或：

```text
/video-init <视频项目根>\EP00X_视频标题
```

初始化会检查项目路径，创建标准目录、`.video-workflow-state.json`、`WORKFLOW.md` 和 `STATUS.md`，不会覆盖已有文件。

## 日常用法

```text
规划这篇视频的分镜
粗剪 Raw 里的这些视频
根据原稿校对字幕
创建剪映草稿
按 asset_request_list 下载素材
分析精剪 SRT 哪些地方值得做 B-roll
为 B-roll-003 生成 Remotion 动效
把这些 B-roll 放到对应口播位置并输出预览
视频状态
记录这次协作的问题并优化视频 skill
```

## 重要区分

| 项目 | 负责什么 | 不负责什么 |
|---|---|---|
| `video-rough-cut` | 转录、按文稿和词级时间码剪辑、FFmpeg 合成、最终自检 | 不替用户决定每条 B-roll 的审美方案 |
| `video-caption-correct` | 校对 ASR、识别口误、生成删除建议 | 不替代剪映内部最终精剪 |
| `video-jianying-draft` | 生成剪映原生 Draft | 不负责内容策划和 B-roll 机会判断 |
| `b-roll-finder` | 判断哪里值得插 B-roll、定义视觉命题和素材路由 | 不替用户做最终审美选择 |
| `b-roll-generate` | 调度真实素材、拼贴路线、Remotion、HyperFrames | 不编辑整条主视频 |
| `video-polish` | 装配 B-roll、音效、音乐和字幕，输出成片 | 不静默删除用户已经确认的素材 |
| `video-skill-optimize` | 从任务和对话记录证据，生成并验证有界 Skill 候选 | 不自动采纳，不用训练案例冒充留出验证 |

## 文件位置

完整规范见 [SKILL.md](SKILL.md)。项目内文件结构见 [shared-references/video-folder-schema.md](shared-references/video-folder-schema.md)，阶段交接见 [shared-references/handoff-contracts.md](shared-references/handoff-contracts.md)。

## 能力来源

本合集把内容规划、粗剪、字幕、剪映、素材获取、B-roll 引擎和验证式 Skill 优化统一编排为当前子 Skill。历史来源只保留在迁移记录中，运行时不依赖备份目录。
