# 成片导出：Remotion / B-roll 成片 → 可编辑剪映草稿

> 方法论改编自开源项目 [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft)（Apache-2.0，`references/jianying-export.md`），已按本合集 `jianying.py` CLI 体系改写。Mac 剪映 11.2 实测口径来自原项目。

**用途**：`video-polish` 交付成片后，用户还想在剪映里继续改字幕内容/字号/颜色、给镜头变速/重排、调整或替换 SFX/BGM 时，把成品反导出为**可编辑的剪映原生草稿**。

**触发**：成片交付后默认询问一次「是否需要同时生成剪映工程文件（可改字幕、变速、换音频）」；用户明确点名「导出剪映工程」时直接执行。

**边界**：镜头内部动效（逐帧程序渲染的运镜/粒子/编排）超出剪映的素材+关键帧模型，只能烘焙进底片。

## 1. 分层原则：什么可编辑、什么烘焙

| 层 | 剪映里的形态 | 可编辑度 |
|---|---|---|
| 镜头内动效（运镜/粒子/逐元素编排） | 烘焙进底片 | 仅整段变速/调色 |
| 镜头边界 | 底片按镜头切段（同一文件不同 source/target 区间） | 变速/重排/删减 |
| 屏幕字幕/口播字幕 | 剪映原生文本轨 | 内容/字号/颜色全开 |
| SFX / BGM | 剪映音频轨（带各自音量） | 全开 |
| 用户点名的独立元素（logo/计数） | 可选：画中画图层 | 位置/大小/透明度 |

品牌动效时刻（标题贴位、logo lockup 等定制编排的文字）默认烘焙——拆成剪映文本会丢掉调校过的入场动画；用户明确要求可编辑时才拆，并说明代价。

## 2. plate 底片渲染（无字幕、无 SFX、无 BGM 的干净底片）

给 Remotion 工程加一个 `plate` inputProp 做网关（不必层层传 prop）：

```tsx
// 字幕/覆盖层组件顶部
import { getInputProps } from 'remotion';
const { plate } = getInputProps() as { plate?: boolean };
if (plate) return null;

// Root 里音频统一 gating
{!plate && <Audio src={staticFile('audio/bgm.mp3')} volume={0.72} />}
```

```bash
npx remotion render src/index.ts <CompId> ../out/plate.mp4 \
  --props='{"bgm":false,"plate":true}'
```

渲后抽帧对比原片同帧（`ffmpeg -ss <t> -i ... -frames:v 1`）：确认字幕已剥离、其余视觉逐帧一致。非 Remotion 来源（AI 拼贴、Stock 剪辑）可跳过 plate 概念，直接用无字幕版成片当底片。

## 3. 时间线数据提取（三张表）

从工程常量/manifest 提取，**不在导出时手抄约数帧号**：

- **镜头表** `(名称, from帧, to帧)`：来源为 B-roll manifest / composition 的 SHOTS 常量；帧 = `round(秒 × FPS)`；
- **字幕表** `(文本, from帧, to帧)`：来源为 `Sub/master.srt`；相邻镜头同文案合并为一段；
- **SFX 表** `(文件, 目标时刻, 峰值秒, 音量)`：来源为装配 manifest 的音频钉帧。SFX 按**内部峰值**对齐，不按文件头：`start = 目标时刻 − 峰值秒`；长样本显式截断时长照抄。

时间常量规则：全程浮点秒记账，**只在最后一步换算帧和微秒**（提前取整让误差滚雪球）。秒直接交给 `jianying.py`（`--target-start` 秒参数），脚本内部规避了微秒取整缝隙。

## 4. 用 jianying.py 建草稿

标准序列（详见 [skills/video-jianying-draft/SKILL.md](../../skills/video-jianying-draft/SKILL.md)）：

```text
create_draft 1920x1080@<FPS>
  → add_video <plate> --target-start <s> --duration <d>   （逐镜头切段：同底片、不同区间）
  → add_subtitle <master.srt>                              （或双语拆两轨：ZH 大 EN 小）
  → add_audio <sfx> --target-start <s> --volume <v>        （贪心分道自动处理重叠）
  → add_audio <bgm> --track-name BGM --volume 0.72
  → save_draft
```

要点：

- **底片切段**：`add_video` 对同一 plate 文件按镜头区间多次添加——同一素材自动共享，不同区间各自成段，剪映里每段可单独变速/重排；
- **重叠 SFX**：同轨音频不可重叠，`add_audio` 默认贪心溢出 `SFX-2` 等新轨（无需手工分道）；
- **双语字幕**：一段文本一字号；中文大英文小必须拆两轨（`字幕ZH` / `字幕EN`），先拆 SRT 再分别 add；
- **样式换算**：字号/垂直定位/颜色换算常数见 video-jianying-draft SKILL.md「实测标定与经验常数」（CSS px ÷ 10.8 ≈ 剪映 size 等）；
- 字体不指定用剪映默认；导出后提醒用户在剪映里换字体微调。

## 5. 安装与验收

1. `save_draft` 前剪映必须**完全退出**（脚本已内置进程检测拦截）；
2. 新机器/新剪映版本首跑先做**冒烟测试**（video-jianying-draft SKILL.md 有步骤）；
3. 脚本自检：`save_draft` 输出的 `media_copied`/`missing_media`、轨道数、字幕条数符合预期；
4. 用户三查：整片播放连贯、SFX 卡点正确；双击字幕改文字/字号/颜色；任选一段底片变速；
5. 交付时说明：剪映打开保存后草稿升级加密——**单向转换**，要改字幕方案/镜头切分就改导出参数重装（幂等覆盖），不要试图读回剪映改过的草稿。

## 6. 隐私

Mac 版草稿 platform 字段含本机设备标识（device_id/hard_disk_id/mac_address）。自包含草稿目录**不要直接分发给他人**——对外只交付渲出的成片；确要给可编辑工程，在对方机器上重新导出。
