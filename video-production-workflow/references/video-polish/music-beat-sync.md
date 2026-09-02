# music-beat-sync — BGM 节奏分析与卡点（装配层）

> 方法论改编自开源项目 [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft)（Apache-2.0，`references/music-beat-sync.md`），按本合集 `video-polish` 装配体系改写。原项目实测：70s / 18 镜 / 131.97 BPM 宣传片渲后回测全部切点误差 ≤2.2 帧（感知阈值约 3 帧）。

适用：`video-plan` 的 `music_cue_sheet.json` 已选音乐、或 `video-polish` 装配配了强节奏 BGM 时，转场与关键动效落点要卡拍。

**铁律：音乐先行。** 节拍网格没验收通过之前不锁定切点/动效落点；时长对不上时改时间参数，不删改口播内容。全程浮点秒记账，**换算成帧只发生在最后一步**（提前取整让误差在管线里滚雪球）。

## 1. 节拍网格测定

librosa 已在合集 `.venv` 里，直接 `uv run python`：

```python
import numpy as np, librosa

y, sr = librosa.load("bgm.mp3", sr=None, mono=True)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, tightness=400, units="time")

# beat_track 的 tempo 标量可能偏差 2%+，但 beat 时刻序列是好的：
# 对 beat 序列做最小二乘等距网格拟合 t_i = t0 + i*T，求真实 BPM 与相位。
i = np.arange(len(beats))
A = np.vstack([i, np.ones_like(i)]).T
(T, t0), *_ = np.linalg.lstsq(A, beats, rcond=None)
bpm = 60.0 / T
residual = beats - (t0 + i * T)
print(f"BPM={bpm:.2f} t0={t0:.4f}s 残差±{abs(residual).max()*1000:.0f}ms")
```

- 残差 ≤ ±15ms（半帧内）= 机器鼓点、网格可信；残差大 = 有变速段，分段拟合；
- **半倍/双倍歧义必查**：BPM 在 2x/0.5x 之间跳时，判据是 kick 是否主要落在整数拍（一半落拍一半落半拍 = 网格快了一倍）；对 0.5x/1x/2x 候选各算 §3 指标，选覆盖率最高的；
- 人声/编曲厚会把鼓攻击埋掉：先 `librosa.effects.hpss` 取打击成分再测；仍不干净用 Demucs 分鼓轨（`uvx --from demucs demucs --two-stems=drums -n htdemucs bgm.mp3`），之后全在鼓轨上做。

## 2. 鼓点分类（决定什么钉在哪一拍）

分频段各测瞬态（在鼓成分上）：

| 类别 | 频段 | 驱动 |
|---|---|---|
| kick | 40-160 Hz | 冲击/slam/骤缩——画面"被砸"的一拍 |
| snare | 150-500 Hz 体 + 1-3 kHz 打击面 | 替换/闪切/构图切换——"换一件事"的一拍 |
| hihat | 6-14 kHz | 微动密度——hihat 密的段微动可密，稀的段必须收 |

```python
from scipy.signal import butter, sosfilt
def band_env(y, sr, lo, hi):
    sos = butter(4, [lo, hi], btype="band", fs=sr, output="sos")
    env = librosa.onset.onset_strength(y=sosfilt(sos, y), sr=sr)
    return env, librosa.times_like(env, sr=sr)
```

命中存 `{t, s, k}` 列表。**命中表是候选池不是触发器**：强鼓点曲 kick 每拍都有，逐拍"被砸"就是镜头随节奏抖动。全画面级冲击（震屏/闪帧/整画面 scale 泵）全片 ≤3 处、钉在最强 hit 上、相邻间隔 ≥16 拍；其余拍点只作**时机**参照，动效落在元素层不落在整画面。

RMS 能量曲线（`librosa.feature.rms`）切出音乐结构表：breakdown 放呼吸位，高能段镜头可多层，低能段收 1-2 层——装配的能量曲线贴着它排。

## 3. 网格验收（先验收，后锁切点）

候选网格对齐最近真实瞬态，算四个指标：

| 指标 | 门槛 |
|---|---|
| 网格拍命中真实瞬态比例 | ≥98% |
| 平均绝对对齐误差 | <10ms |
| 漂移（残差线性回归斜率×全长） | 全曲累计 <5ms |
| 第 0 拍落在真实音乐攻击上 | 必须 |

候选与获胜理由写入 `<项目>/Polished/analysis/beat_data.json`（bpm/beats/hits/rms/sections，浮点秒不预取整），它是每个切点的审计链。

## 4. 装配用拍号表达落点

`music_cue_sheet.json` 和 `broll-compose.json` 的时刻从拍号推导：`beatT(n) = t0 + n*T`；密集规则切点用网格拍，**稀疏重音/孤立定格钉真实瞬态**（网格在稀疏处的漂移会被单个重音放大成可感偏差），结尾定格用最后瞬态 + RMS 静默确认。B-roll/SFX 按内部峰值对齐不按文件头：`起始 = 目标拍 − 峰值秒`。

## 5. 渲后回测（闭环，必做）

```bash
ffmpeg -i Final/video_final.mp4 -vn -acodec pcm_s16le /tmp/render-audio.wav
```

对渲出音轨重跑 §1 拟合（BGM 从成片里量，连编码偏移一起验），逐切点对比设计帧号 vs 实测帧号：**≤3 帧合格，>3 帧必修**。

系统性同向偏移先查**输出音轨偏移**（AAC encoder priming 等，48kHz 典型 ≈1.3 帧），用 BGM 原文件与渲出音轨归一化互相关量出，单设一个补偿常量加在拍号换算上；**不要逐锚点手改拍号，不要把补偿混进分析真值 t0**（换 codec/重新分析时会二次补偿）。

## 6. 双版本交付

配了 BGM 的片子固定交付两版：**带 BGM 版 + 无 BGM 版**（保留口播/SFX），从同一装配 manifest 渲出，方便用户后期自配音乐。
