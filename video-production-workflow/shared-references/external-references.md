# External References（外部参考项目登记与许可证边界）

本合集在制作过程中吸收了以下外部开源项目的方法论。各项目许可证不同，**可吸收的方式不同**；所有子 Skill 引用外部目录前先查本表。

| 项目 | 许可证 | 允许的吸收方式 | 本合集的吸收位置 |
|---|---|---|---|
| [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft) | **Apache-2.0** | ✅ 可分析原理、可改编代码/文档（保留署名、标注修改） | `video-jianying-draft`（vendor 安装层模式、标定常数、成片导出流程）、`references/video-jianying-draft/remotion-export.md`、`references/video-polish/music-beat-sync.md`、b-roll-generate 镜头纪律 |
| [video-talkcraft](https://github.com/Vincentwei1021/video-talkcraft) | **PolyForm Noncommercial 1.0.0** | ⚠️ **仅限分析原理**——非商业许可证与本合集 MIT 冲突，禁止复制其代码、文本、模板、demo 产物进本仓库；商业使用需原作者授权 | 以自写表述沉淀原理。v0.7.1：词锚机器校验/镜尾保护带（`b-roll-timing-and-qa.md`）、排版预算/语义拍进场/三段式（`motion-brief-standards.md`）、P0/P1/P2 分级与独立评审（`video-polish`）。v0.8.1：SHOTBOOK 问责结构（意图句/素材行/主体接力线/未完成清单强制节 → storyboard 模板与 video-plan）、G0 风格档与蒙皮契约（style-profile + b-roll-generate 4c）、相机层与运动减法/纯文镜线稿陪衬图形（b-roll-generate 4a/4b）、边界转场处置/段尾同收/状态切换窗/音效覆盖口径与可听度机检（`b-roll-timing-and-qa.md`）、排版几何规范（`layout-geometry.md`）、评审材料四件套与计划 vs 成片核对（`video-polish`）、素材分辨率下限/降级链/证据截图（`video-assets`）、画面文字不照抄字幕（`video-caption-correct`）、词锚数字卫生（`video-plan`） |
| Remotion | Remotion License（自定义源可用许可） | 引擎依赖 | 仅作为渲染引擎调用；个人/≤3 人营利组织免费（含商用）；用户公司 >3 人或做自动化产品时需自行购买 Remotion 许可；**不得复制/修改 Remotion 代码用于转售或再许可衍生品** |
| pyJianYingDraft | 上游仓库许可证 | vendor 内置 | `scripts/video-jianying-draft/vendor/`，剪映 Draft 生成 |
| ai-video-director（本地模板参考） | 项目内参考 | 原理分析 | 覆盖模式四布局、导演简报结构、审批闸门设计（v0.7.0 已吸收进 motion-brief-standards） |
| [OpenTypeless](https://github.com/)（本地参考副本） | **MIT** | ✅ 可分析原理、可借鉴代码（保留版权声明） | 词典+纠错规则双机制与"保守消歧"判据、产出质量状态语义（normal/partial/fallback）、人工确认结果回流为纠错规则资产——吸收进转录自动校对（`align_to_manuscript.py`、`transcribe.py --lexicon`、`video scripts/lexicon.md`） |
| [oracle-voice](../../oracle-bone/skills/oracle-voice/SKILL.md)（本合集姊妹 skill） | 合集内 | ✅ 机制复用 | `voice-lexicon.md` 词典格式（专名表/纠错规则）与"词典候选回流"闭环——视频侧落地为 `video scripts/lexicon.md` + `templates/lexicon.template.md` |
| [OpenChatCut](https://github.com/)（本地参考副本） | **AGPL-3.0-or-later** | ⚠️ **仅限分析原理**——AGPL 与本合集 MIT 冲突，禁止复制其代码进本仓库 | 仅以自写表述吸收思路：停顿规则语法化（compress/range/long + 逐边界覆盖）、静音删除前能量门禁、镜头切换作剪点约束、渲染前 advisory 自审——登记为 rough-cut/tighten_pauses 的演进方向 |
| [OpenMontage](https://github.com/)（本地参考副本） | **AGPL-3.0-or-later** | ⚠️ **仅限分析原理**——AGPL 与本合集 MIT 冲突，禁止复制其代码、schema、YAML 进本仓库 | 仅以方法论事实（维度/阈值/机制思想）自写原生实现：幻灯片风险量化评分（`scripts/video-plan/slideshow_risk.py`，自有维度与权重）、交付承诺与运动比核对（`check_delivery_promise.py` + storyboard `delivery_promise`）、跨阶段决策日志（`decision-log.md`，append-only/双选项/追加式修订）、渲后完备性下限与评审 finding 产出规则（`video-polish`）、旁白-画面对齐断言（`check_cue_alignment.py`）、素材源技术准入探针（`probe_source.py`）、风格档三拨盘与 20% 偏离预算（storyboard 风格档节）、字幕格式化数值（`video-caption-correct`） |
| [video-use](https://github.com/browser-use/video-use)（本地参考副本） | **MIT** | ✅ 可分析原理、可借鉴代码（保留版权声明） | 词级转录为主阅读视图 + 渲后对成片切点 ±1.5s 抽帧自评回路；本合集 rough-cut 的 `pack_transcripts.py`/`timeline_view.py`/EDL 结构与其同源，v0.8.0 补齐渲后自评与规则/示例二分理念 |
| [HyperFrames](https://github.com/HeyGen/hyperframes)（本地参考副本） | **Apache-2.0** | ✅ 可分析原理、可借鉴 | 渲染前 lint/check/doctor 快检层、HTML 直渲染路线的定位（标题卡/关键词强调）、talking-head-recut 的"字幕驱动覆盖层"思路——吸收进 `references/b-roll-generate/motion-template-catalog.md` |
| remotion-templates（1000 模板库，本地参考副本） | **无 LICENSE 声明** | ⚠️ **仅限分析思路与机制**——许可未声明即默认保留所有权利，禁止复制其代码、模板或资产进本仓库 | 仅吸收方法论：family-engine × variant × palette 派生、机器可读注册表（visualRole/tags/textLength/pairWith）、机械验收 gate——`references/b-roll-generate/motion-template-catalog.md` |
| remotion-scenes / video-forge / video-skills-toolkit（本地参考副本） | **MIT** | ✅ 可参考/复制（保留版权声明并登记） | video-skills-toolkit 的"逐字稿→字幕驱动一切动画→低清 proof→高清出片"心法、video-forge 的 props 元数据（textLength/durationRange/pairWith）——`references/b-roll-generate/motion-template-catalog.md` |
| [jianying-editor-skill](https://github.com/luoluoluo22/jianying-editor-skill)（本地参考副本） | **MIT**（内置 vendor pyJianYingDraft 为 Apache-2.0） | ✅ 可分析原理、可借鉴（保留版权声明并登记） | v0.8.2：vendor 深层能力登记、save-time JSON patch 模式、机器可读验收清单（`video-jianying-draft` SKILL）。v0.8.5：转场/关键帧/滤镜的 CLI 暴露思路（枚举查表选型替代猜 ID、片段寻址 inspector、错误给相近建议的结构化契约）——`jianying.py` 的 `list_enums`/`list_segments`/`add_transition`/`add_animation`/`add_filter`/`add_keyframe` 为本合集原生实现，未复制其代码；其素材 CSV 索引、TTS、UI 自动化导出未采纳 |

## 引用规则

1. 子 Skill 的外部参考目录（`<外部参考项目根>\...`）一律是**软依赖**：路径不存在时跳过并在 `notes.md` 记录，不阻塞流程；
2. **PolyForm-NC 项目（video-talkcraft）的任何文件不得复制进本仓库**，也不得让用户"从那边拷过来用"；只允许阅读理解后用自写表述沉淀原理；
3. Apache-2.0 项目改编时保留来源注明（各吸收文档头部已标注）；后续二次修改无需额外声明，但不得移除原署名；
4. 新增外部依赖前先在此登记许可证结论，未查证许可证的项目不接入；
5. **从外部项目借鉴失效模式时，必须转化为机制（断言/强制节/机器检查/改名），不允许只写劝诫文档**——"答案在文档里但没人在正确时刻查"的解法是把检查挪到正确时刻做成闸；"Agent 做不到的验收"（听音频、看视频）必须指定机器替身（ffprobe/抽帧/RMS 量测）并写明测量口径与盲区。
