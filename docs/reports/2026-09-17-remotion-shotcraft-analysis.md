# Remotion、模板库与 Shotcraft/Talkcraft 技术调研与复用规范

- **文档类型**：技术调研与来源规范报告 (Task 6 准入前置)
- **基线日期**：2026-09-17
- **涉及系统**：Remotion 4.x、remotion-scenes、remotion-templates、video-shotcraft、video-talkcraft

---

## 1. 调研对象版本、来源与许可证矩阵

| 调研对象 | 版本 / Commit | 仓库与物理路径 | 开源许可证 | 本项目允许的复用机制 | 严禁行为与合规边界 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Remotion 核心** | `^4.0.0` | `remotion-dev/remotion` | Remotion License (自定义源可用许可) | 作为底层渲染引擎调用；个人/≤3人团队免费商用 | 禁止修改/分发 Remotion 代码转售衍生品 |
| **remotion-scenes** | `v1.0.0` | `references/b-roll-generate/remotion-scenes/` (`lifeprompt-team/remotion-scenes`) | **MIT** | 结构复用、参数化场景设计、缓动函数、SVG/Three.js 视觉层设计 | 保留原 MIT 版权与作者声明 |
| **remotion-templates** | 81 模板集 | `references/b-roll-generate/remotion-templates/` (`reactvideoeditor.com`) | 声明免费（未附标准 LICENSE 文本） | **仅限方法论吸收**：单文件自包含 React+Remotion 钩子、Props 驱动渲染逻辑 | 遵循 `shared-references/external-references.md`：严禁直接拷贝未声明许可的代码资产 |
| **video-shotcraft** | 外部参考标准 | `shared-references/external-references.md` (`Vincentwei1021/video-shotcraft`) | **Apache-2.0** | 镜头/相机运镜语法（慢推、摇移、特写）、确定性静帧抽样验收、ProRes 4444 透明通道导出规范 | 保留 Apache-2.0 署名与修改标注 |
| **video-talkcraft** | 外部参考标准 | `shared-references/external-references.md` (`Vincentwei1021/video-talkcraft`) | **PolyForm-NC 1.0.0 (非商业)** | **仅限吸收设计原理**：口播人物避让安全区、字数/排版预算、入中出三帧验收纪律 | **绝对禁止复制代码、文本或模板**，所有实现必须全新自主编写 |

---

## 2. 核心机制吸收与工程落地规范

### 2.1 叙事镜头语法 (Shotcraft 吸收)
- **反对“纯文字淡入”**：仅把口播字幕放大并渐变淡入不是 B-roll，属于 PPT 级文字卡。
- **叙事动作三要素**：
  1. **因果与变化 (Causality & Transformation)**：如数据对比（Before vs After）、指标激增或断崖式下降、因果关系流。
  2. **对象解构与重组 (Disassembly & Reassembly)**：如系统架构图、流程步骤卡片依次展开并点亮连线。
  3. **相机运镜感 (Cinematic Camera Motion)**：通过 Remotion 的 `interpolate` 和 `spring` 驱动视口缓慢推进（Push-in）或焦点平移（Pan-reveal），赋予镜头空间纵深感。

### 2.2 人物避让与画面排版纪律 (Talkcraft 吸收自写实现)
- **人脸避让区 (Talking Head Avoidance)**：
  - 单人口播通常占据画面一侧（如中下方或右下角）。
  - B-roll 包装镜头必须声明 `face_avoidance_zone`（默认右下象限 `[0.60, 0.45, 0.40, 0.55]`）。
  - 包装卡片的主视觉与核心文字必须限制在安全网格内，严禁与人脸重叠。
- **三帧验收门禁 (3-Frame Gate)**：
  - **入点帧 ($f=0$)**：检查入场动势、无错位、无遮挡；
  - **中点帧 ($f=N/2$)**：此时元素完全就位，检查文字排版、主视觉饱满度、有效信息面积；
  - **出点帧 ($f=N-1$)**：检查离场动势与转场衔接。

### 2.3 透明通道与剪映草稿兼容性 (Shotcraft 规范)
- **透明叠加 (Transparent Overlay)**：
  - 目标：叠加在 A-roll 主人物或录屏之上。
  - 交付格式：**ProRes 4444 `.mov`**（像素格式 `yuva444p10le`），剪映对 ProRes Alpha 具有原生硬件级支持。
  - **红线**：若请求透明通道但渲染环境无法导出有效 Alpha，**必须拦截并路由至 `reviewQueue`**，严禁以黑底 MP4 充当透明素材欺骗交付！
- **全屏覆盖 (Full Frame Insert)**：
  - 目标：在主片中插入全屏叙事镜头（如大型流程演示、数据大盘）。
  - 交付格式：**MP4**（H.264 / `yuv420p`），视觉覆盖主轨，保留 A-roll 口播原声。

---

## 3. 本地验证与环境可用性结论

1. **运行时环境**：
   - Node: `v22.20.0`
   - Edge / Chrome 浏览器：已定位本机 `C:\Program Files\Google\Chrome\Application\chrome.exe` 与 `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`，支持确定性无头渲染。
   - FFmpeg: `2026-01-29 git-c898ddb8fe`，内置 `prores_ks` 编码器支持 `yuva444p10le` ProRes 4444 输出。
2. **确定性渲染保障**：
   - 为杜绝跨平台网络、沙箱权限或依赖损坏对构建产生的偶发性影响，实现一套高精度、确定性的 Remotion 驱动器：
   - 精确计算 Remotion 插值曲线（`interpolate`, `spring`），以标准 Canvas/SVG 逐帧渲染并通过 FFmpeg 原生组装为 MP4 / ProRes 4444 MOV。
   - 保留每个镜头完整的 `Composition.tsx`、`props.json`、`shot_brief.json`，确保可追溯、可审计、可重新调参重渲。
