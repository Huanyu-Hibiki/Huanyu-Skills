# Changelog

## v0.8.5 - 2026-09-16

- **剪映 CLI 补全转场/关键帧/滤镜（借鉴 jianying-editor-skill MIT 实现方案，原生实现，登记见 external-references）**：`jianying.py` 新增 6 个子命令 + `add_video` 视频淡入淡出：
  - `list_enums --kind transition|filter|intro|outro|group|mask [--search 关键词]`——枚举查表（vendor 内置转场 362 / 滤镜 468 / 动画 290 个，中文名即枚举名），落实「绝不猜 ID」纪律；
  - `list_segments [--track T]`——各轨片段 index/start/end/时长/material_id，转场/滤镜/关键帧的目标片段统一用 track+index 寻址；
  - `add_transition --track --index --type 叠化 [--duration 0.8]`（挂目标片段头部，与上一段重叠）；
  - `add_animation --kind intro|outro|group --type 渐显`；
  - `add_filter --type 自然 [--intensity 0-100]`（落盘在 draft 的 materials.effects）；
  - `add_keyframe --property uniform_scale|alpha|position_x/y|rotation|scale_x/y|brightness|contrast|saturation|volume --time 片段相对秒 --value`——Ken Burns 缓推、画中画运镜、进度式动画；`volume` 属性走音频段专用接口；
  - `add_video --fade-in/--fade-out`（alpha 关键帧封装，与 `add_audio --fade-in/out` 对称）。
- **序列化缺口修复**（E2E 自测发现）：vendor 的材质收集只在 add_segment 时发生，转场/滤镜/动画/淡入淡出属于对已有片段的增量修改（pickle 往返），落盘的 draft_content.json 会静默丢材质——`save_draft` 落盘前新增 `_collect_materials` 统一重收集（按类型 ID 去重，幂等），并把该不变量写进 SKILL 扩展纪律。
- **错误路径结构化**：枚举猜错/轨道不存在/序号越界统一输出 stdout JSON（`success:false` + `close_matches` 相近建议 / `tracks` 现有轨道列表 / 查表提示）+ 退出码 1，Agent 可结构化自纠。
- E2E 验证（ffmpeg 合成素材全链路）：双段铺轨 → 叠化转场/渐显动画/自然滤镜/uniform_scale 关键帧对/视频淡入 → save_draft → 解析 draft_content.json 确认四类材质与关键帧全部真实落盘；误猜枚举得 close_matches 建议；`list_enums --search 叠` 精准过滤。

## v0.8.4 - 2026-09-16

- **素材落位匹配（用户痛点：多段录屏/实拍素材不知道放时间轴哪里）**：新 `scripts/b-roll-finder/match_footage.py`，精剪后运行，三条策略：
  - **镜号映射（机械）**：素材文件名按目录规范带镜号（`实拍【EP001-S01-001到S04-001】.mp4`）→ 对上 `storyboard.json` 的 `broll_candidates.shot_id` → 在 `Sub/master.srt` 找该条旁白原句 → beat 落点 = 句起点 +0.3s（词锚规则），区间 = min(素材时长, 句长+2s, 8s)；
  - **语义候选（只出材料不下结论）**：文件名无镜号的素材列出清单 + 未占用时段，交 Agent/用户语义配对——脚本不瞎猜；
  - **时长对齐防冲突（机械）**：素材 <2s 给 warning、beat 重叠自动顺延、素材时长是硬上限（裁内容先问用户）。
- **A/B 边界前置**：带人声讲解的录屏是 A-roll（走粗剪转录挑 take），只有无声覆盖素材进本匹配（folder-schema 既有规则的执行化）；
- 产出 `Polished/broll-compose.draft.json` + `match_report.md`，🔴 匹配表用户逐条确认后才转正进装配——配对是建议，语义配对权在人；
- video-polish 装配流程第 2 步改为「装配清单二选一」（落位骨架转正 / 手写 compose），主 SKILL 路由表、workflow 模板、b-roll-finder SKILL 新「素材落位匹配」节级联；
- 测试：镜号录屏（2 段）正确落到对应旁白句 +0.3s，无镜号素材进语义配对清单。

## v0.8.3 - 2026-09-15

- **卡顿/重复自动剪除（用户痛点：录视频卡顿重读一句话，转录环节感知不到）**：新 `scripts/video-rough-cut/detect_repeats.py`，嵌入粗剪 keeps 链路（select_takes → **detect_repeats** → tighten_pauses → EDL），词级时间戳上检测三类：
  - **词级结巴**（"我们我们来看"，同词连读 ≤0.5s）→ 自动剪首次，保留最后一次；
  - **前缀废弃**（说一半停住重说完整："我觉得这个 → 我觉得这个方案"）→ 后文以首次尝试为真前缀且停顿 ≥0.08s，自动剪首次——停顿条件区分"往下说"与"重说"（正常连续语流任意前 N 词都是后文前缀，无停顿不触发）；
  - **相似重说 / 长间隔整句重读** → 只进 `repeats_report.md` 待确认清单，**不自动剪**——非前缀的相似重说与排比句（"非常实用/非常好用"）在文本上无法区分，宁可留一处结巴给用户裁决，不冒险剪掉排比（🔴 句级删除 diff 确认纪律）。
- 字幕不受影响：caption_corrected.srt 以文稿拼写为准（文稿本来没有结巴），剪除只作用于音频时间线；确认要剪的待确认项手工并入 keeps 后重跑 tighten_pauses。
- 产出：`keeps_dedup_<source>.json`（喂 tighten_pauses）+ `repeats_report.json/.md`（自动剪除清单 + 待确认清单，含删/留文本、相似度、间隔）；5 个边界场景测试全过（结巴/前缀改口/排比不误剪/整句重读只标记/正常语流零误报），keeps 减除与 cut 区间精确对账。
- 修复两个实现 bug（自测发现）：窗口从大到小遍历时 `break` 方向反了（大窗口超长间隔会挡住小窗口的真改口）；`global` 声明位置导致启动即语法错误。
- 级联：rough-cut 流程（13 步）/执行脚本/硬规则/失败模式表/输出树、主 SKILL.md 端到端、workflow 模板。

## v0.8.2 - 2026-09-14

- **吸收 OpenMontage 治理层（AGPL-3.0，仅原理——全部为本合集原生实现，登记见 external-references）**：把"会不会像 PPT / 会不会违约 / 为什么这么选"变成带数值的门，五个新脚本全部零依赖（Python 标准库 + ffprobe/ffmpeg），输入输出对齐既有产物（storyboard.md/json、edl.json、broll-compose.json、master.srt）：
- **幻灯片风险闸**（新 `scripts/video-plan/slideshow_risk.py`）：分镜审批前必跑——意图缺失/文字卡过载/节奏盲区/同类连排/泛化词/B-roll 极端六维打分（0-10，越高越像 PPT），pass/warn/reject 三档，reject 打回重排不得进审批闸；报告落 `video scripts/slideshow_risk_report.json`。
- **交付承诺**：`storyboard.json` 顶层 `delivery_promise`（mode + min_motion_ratio，口播+剪映默认 hybrid/0.2）；新 `scripts/video-polish/check_delivery_promise.py` 装配前核对——已批准条目缺失 = fail 禁止装配，静帧兜底致运动比低于承诺 = degraded 必须用户显式批准降级并记决策日志，不静默出片。
- **跨阶段决策日志**（新 `shared-references/decision-log.md` + `templates/decision-log.template.json`，项目根 `decision_log.json`）：append-only，每条 ≥2 个被考虑选项（score+reason+rejected_because），改决策只追加同 (category, subject) 新条目；写入时机挂进 video-plan（交付承诺）/rough-cut（take 裁决）/b-roll-finder（风格决策）/caption-correct（词典增改）/polish（降级与预授权）。
- **旁白-画面对齐断言**（新 `scripts/video-polish/check_cue_alignment.py`）：master.srt 句级 cue × EDL 切点 + B-roll 起点事件，±1.0s 窗口无画面事件的句子超 15% 列 P1 finding——"说到时画面上没东西"由机械检查回答。
- **成片技术探针**（新 `scripts/video-polish/final_probe.py`）：发布前最低完备性机检——时长 vs 预期 ±5%、音轨存在、峰值电平（>-0.5dBFS 判逼近削波）、10/35/65/90% 四点抽帧自动落盘；探针 JSON 存档进 QA 报告。
- **素材技术准入探针**（新 `scripts/video-assets/probe_source.py`）：下载后即测实测分辨率（640×360 假高清）/时长/关键帧最大间隔（>5s 给重编码命令），不达标不进渲染队列，走未完成清单或升级链。
- **QA 完备性下限与评审产出规则**（video-polish）：抽帧 ≥4/时长 ±5%/峰值门槛等可判定最低标准（缺数据本身记 finding）；finding 必须指到镜号/时间码/文件，P0/P1 必附修复动作否则降级 investigation；发现 critical 必扫同类；阶段评审 ≤2 轮后无新增 critical 不再开轮；P2 同质化检验语"把标题遮住还认得出这条片吗"。
- **风格档量化承诺**（storyboard 风格档节 + video-plan）：运动强度/视觉差异/信息密度三拨盘（1-10）+ 反默认清单 3-5 条 + 偏离预算 ≤20% 场景须写 per-scene 理由。
- **字幕格式化前置检查**（video-caption-correct）：显示时长 ≥ max(1s, 字数÷5)、>7 字/秒拆条、cue 尾延后 ~200ms、安全区——与词典纠错解耦。
- **断点续跑纪律**（state-management）：转录缓存/B-roll 工作区/剪映 cache 即持久检查点，被取代产物版本递增保留（history 语义）。

## v0.8.1 - 2026-09-12

- **吸收 video-talkcraft 第二轮（PolyForm-NC，仅原理自写——全部为自写表述，登记见 external-references）**，按管线阶段落地 19 项未吸收机制中的高价值子集：
- **分镜问责结构**（storyboard 模板 + video-plan）：每镜一句话意图（动效/素材行每个动作答得出"配合谁"）、素材行落到已登记路径或显式「待采」、动效简报增「主体接力线」（谁让位给谁，不允许无主角/双主角节拍）、**「未完成 / 未采集清单」强制节**（内容可"无"、节不允许缺——拦截"未完成被包装成设计原则"；b-roll-generate Gate 0 与装配 QA 查节在册）、枢轴句归下一镜、文稿数字建议汉字（词锚逐字对位卫生）。
- **G0 风格档**：video-plan 新增「风格档」节——按全稿判领域产出 `video scripts/style-profile.md`（底色策略/唯一强调色/字体气质/材质卡型/图表语言/素材气质/能量档/"不做的事"），系列视频从上期复制按集扩展（跨集一致性外置配置）；深底主导需用户确认；章节卡"同族不同章"轮换。
- **蒙皮契约**（b-roll-generate 4c）：模板/库卡/AI 生成画面进成片前按风格档换皮——必换（色 token/字体/材质/图表语/占位图）、不动（时序/缓动/几何/音效 cue）、语义色不换色相、同片同类一套皮、manifest 记蒙皮行。
- **相机层与运动减法**（b-roll-generate 4a）：每条 B-roll 默认极缓推拉 1.00→1.04~1.06（唯一缓动、末键落段尾外防停死）、禁 x/y 摇移/旋转/脉冲/idle 堆积、一镜一个时间操纵者、细密纹理不进缩放层。
- **纯文字镜陪衬图形**（b-roll-generate 4b）：素材路由只有"文"的条目必须含线稿图形层（"讲 X 所以画 Y"、基础件词汇表、一镜一图、核心图形 ≥ 屏高 20%、每句口播至少一个可见变化）。
- **时间线 QA 升级**（b-roll-timing-and-qa）：镜头边界转场处置（禁裸切/一边界一式/黑震全片限一/交叠 12-16 帧两侧同向/100s 片 5-7 强边界/长镜连续运镜替代）、段尾同收（最后退场=段尾，禁底床空转 >0.4s）、状态切换窗 ±0.5s 入抽帧清单（角标↔满幅/字幕带换位等几何过渡）、音效覆盖口径（≈0.4 记/s，"少而准"管单点不叠不砍覆盖）、可听度机检（cue 窗峰值 ≥-45dBFS、混音掩蔽分级、UNMASKED 门槛与气口数对账——不可达早下结论）、渲前静止探针。
- **排版几何规范**（新增 `shared-references/layout-geometry.md`）：安全边/字幕带/12 栏吸附、间距令牌与"外≥组≥内"层级铁律、字形边缘对齐/包围盒居中/人物对侧半幅、字阶档与字号下限（"先删字→拆行→最后缩字"）、包围盒碰撞三类豁免、九项机检清单——polish QA 引用。
- **独立评审升级**（video-polish）：评审材料**四件套**（3×4 评审拼图 / 模板对照帧"是同一设计吗" / 词落点定妆帧表 / 音效可听度机器报告）、计划 vs 成片核对（附 storyboard 设计清单与风格档"不做的事"）、执行纪律（增量落盘/结束行才算完成/分片 ≤7 镜/三次无产出标注"未获独立评审"禁自评替代）、**闸先读闸**（FAIL 先读判定口径，输入决定不可修的问题早下结论交用户）。
- **素材纪律**（video-assets）：英文视觉概念词检索、先视频后图片降级链、分辨率 ≥ 画幅×最大缩放、免署名源优先（CC BY 系先确认署名成本）、关键事实来源页截图存档（只存链接不留证据 = 无法自证）。
- **字幕/画面文字**（video-caption-correct）：画面文字 ≤12 字提炼不照抄字幕、跟读字幕零动效、关键词弹出全片 ≤3 次、字幕标点策略（保留句读=默认 / 极简无标点）由风格档声明。
- **元机制入库**（external-references 引用规则第 5 条）：外部借鉴的失效模式必须转化为机制（断言/强制节/机器检查），不允许只写劝诫文档；Agent 做不到的验收必须指定机器替身并写明测量口径与盲区。

## v0.8.0 - 2026-09-12

- **转录-校对合并（用户指定）**：字幕校对不再是必经阶段——`video-rough-cut` 流程新增第 5 步「文稿自动校对」（`align_to_manuscript.py` 默认必跑）：字幕直接采用文稿拼写（ASR 错字/同音词自动消失），ASR↔文稿偏差、口癖候选、低置信句落盘待复核；`video-caption-correct` 重定位为**条件复核闸门**（低置信句/偏差超阈值或用户要求时进入），其独立转录入口 `run_transcribe`、火山云脚本、审核页 FCPXML/PRPROJ 导出标注 legacy 仅离线场景保留；管线强制阶段 10 → 9。
- **修复 SRT 命名冲突**：`align_to_manuscript.py` 粗剪阶段原把 SRT 误写为 `Sub/master.srt`（与精剪契约撞名，会骗过 status 与 b-roll-finder 的时间真源校验）——默认模式改产出 `Sub/caption_corrected.srt`，`--final-keeps` 兜底模式保留 `master.srt` 语义。
- **个人词典机制**（吸收 OpenTypeless MIT 机制 + oracle-voice 词典格式，见 external-references 登记）：`transcribe.py --lexicon` 读取专名表做 ASR initial-prompt 偏置；`align_to_manuscript.py` 解析纠错规则标注偏差、移植 auto_filler 保守口癖规则集产出 `speech_errors.json`（advisory，不自动删音频）、新增来源状态语义（`provenance_counts`：manuscript_aligned / low_confidence）与 `asr_substitutions` 偏差清单；新增 `templates/lexicon.template.md`——人工确认的错词回流词典，下期转录自动生效。
- **默认安装瘦身（.venv 约 5.4GB → 约 0.7GB）**：`openai-whisper` + `torch==2.7.1+cu126` + `torchaudio` 移入可选 extra `whisper`（默认引擎 faster-whisper 走 ctranslate2，不依赖 PyTorch）；`transcribe.py` GPU 探测改用 ctranslate2（不依赖 torch，有卡机器默认安装仍走 CUDA）；install.ps1/install.sh/README/DEPENDENCIES/download_models 同步；需要备选引擎时 `uv sync --extra whisper`（约 +5GB）。
- **B-roll 动效选型升级**：新增 `references/b-roll-generate/motion-template-catalog.md`——模板注册表查表选型（visualRole/tags/textLength/pairWith）、family-engine × variant × palette 派生、props 约束层（超限拒绝在生成端）、渲前快检层（tsc + 首帧静图 + 三帧 renderStill 脚本化）、时长内容驱动（calculateMetadata 优先、默认值退化为 fallback）、透明通道 × 渲染环境组合规则（云端分块渲染透明 WebM 边界闪烁 → 一律 ProRes 4444）、字幕作动效锚点；b-roll-generate Gate 1/2 之间强制渲前快检；`motion-brief-standards.md` 时长节同步。
- **剪映 Draft 增强**：`add_audio` 新增 `--fade-in/--fade-out`（秒）；SKILL.md 新增「vendor 深层能力与扩展模式」——关键帧/转场/滤镜/蒙版/段动画 API 登记（枚举从 vendor metadata 查表，绝不猜 ID）、save-time JSON patch 模式（适配剪映新版本字段的逃生通道）、机器可读验收清单；音频混音约定（BGM 与旁白共存默认 volume 0.6 + fade 1s）。
- **粗剪渲后自评**：自检步骤明确「对成片每个切点 ±1.5s 抽帧+抽波形核对」（video-use 同源手法）；`tighten_pauses` 硬规则补配乐/低音量/多人重叠段的人工确认门（无能量门禁时宁可保留）。
- **编排与文档全量同步**：主 SKILL.md 端到端流程（03 内含自动校对、03b 条件复核）、阶段路由表、来源映射表（消除「字幕转录」双行歧义）；`handoff-contracts.md`（粗剪新增 caption_corrected/alignment 交接行、转录唯一入口约束）；`video-folder-schema.md`（Rough/analysis/、Sub 产物归属标注）；`state-management.md`（caption_correct 条件阶段语义）；`video-status` 派生检查；`scripts/README.md`；`templates/workflow.template.md`。
- **许可证登记**：`shared-references/external-references.md` 新增 OpenTypeless（MIT）、OpenChatCut（AGPL-3.0，仅原理）、video-use（MIT）、HyperFrames（Apache-2.0）、remotion-templates（无 LICENSE，仅思路）、remotion-scenes/video-forge/video-skills-toolkit（MIT）七项边界；Remotion Free License 条款明确（个人/≤3 人免费，禁止转售衍生品）。

## v0.7.1 - 2026-09-02

- **吸收 video-shotcraft（Apache-2.0，署名改编）**：新增 `references/video-jianying-draft/remotion-export.md`——成片反导出为可编辑剪映草稿（分层原则/plate 底片/时间线三表/安装验收/单向转换与隐私警告），`video-jianying-draft` SKILL.md 增「成片导出模式」章节并在主 SKILL.md 路由表登记；新增 `references/video-polish/music-beat-sync.md`——BGM 节拍网格测定（最小二乘拟合/半双倍歧义/鼓 stem 分离）、kick/snare/hihat 三分类、网格四指标验收、拍号时间线、渲后回测 ≤3f 与输出音轨偏移分账、BGM/无 BGM 双版本交付。
- **吸收 video-talkcraft（PolyForm-NC，仅原理自写，禁止复制内容——见 external-references.md）**：`b-roll-timing-and-qa.md` 增词锚机器校验（落点查表生成/误差 ≤0.1s/镜尾保护带 ≥0.5s/未到拍不显形/开镜不空台）与音效电平纪律（≤0.35、低口播 12dB、同帧一 cue）；`motion-brief-standards.md` 增排版预算（同屏主体组 ≤3、空象限、新元素只在语义拍边界进场、三段式铁律、人物角标 chip、真图硬规与标注坐标机器实测）；`video-polish` 增 P0/P1/P2 缺陷分级、全新上下文独立评审（≤3 轮）、返修时间码三段闭环、390px 手机宽可读性终检、loudnorm 响度归一交付。
- **外部项目许可证登记**：新增 `shared-references/external-references.md`（shotcraft Apache-2.0 可改编 / talkcraft PolyForm-NC 仅原理 / Remotion 公司许可提示等），b-roll-generate 外部参考表登记 talkcraft 并标注许可证红线。
- **字幕语义分页**：`video-caption-correct` 增语义分页与标点规则（按语义断行禁固定宽度硬切、页尾分离符省略但问叹号/成对结构符保留、放大字号必须重排）。
- **转录与安装增强**：`transcribe.py` 增 `--initial-prompt`（领域词表偏置识别，两引擎都支持）；`install.ps1` 增 `-AutoInstall` 静默模式（无人值守/CI）；新增 `run_transcribe.ps1` Windows 原生转录入口（本地引擎免 Git Bash，云端引擎委托 bash）；ModelScope 镜像仓实测校验回填（Systran 官方仓存在，镜像列表修正）。

## v0.7.0 - 2026-09-02

- **转录引擎切换**（用户指定）：默认引擎改为 **faster-whisper large-v3**（Windows 友好：CPU int8 / CUDA 双支持，无显卡可跑），openai-whisper 保留为备选（`--engine whisper` 或 `ASR_ENGINE=whisper`）；Fun-ASR 移出默认转录路径与默认依赖（`uv sync --extra funasr` 可选安装，仅 legacy `funasr_srt.py` 使用）。`transcribe.py` 重写为单引擎词级转录（去除 Fun-ASR 合并逻辑），输出 JSON 格式向后兼容（words 结构不变），`transcribe_batch.py` 同步 `--engine/--model`。
- **一键安装**（用户指定）：新增 `scripts/setup/install.ps1`（Windows）与 `install.sh`（macOS/Linux）——自动装 uv、建 `.venv`、`uv sync`、检查 FFmpeg/Node（winget/brew 提示安装）、支持国内 `-Mirror` 清华镜像、引导模型下载。
- **模型一键下载**（用户指定）：新增 `scripts/setup/download_models.py`——默认只下载 faster-whisper large-v3 到 Skill 根 `models/`；`--source auto/modelscope/huggingface`（国内魔搭优先、国外 HF、HF 失联自动切 hf-mirror）；`--include whisper/funasr` 可选追加；断点续传 + `--list` 状态查看；`transcribe.py` 优先解析 `models/` 本地模型，自动下载也落入 `models/`（`VIDEO_MODELS_DIR` 可覆盖）。
- **README 小白化重写**（用户指定）：安装章节按「装 Agent → 放 Skill → 一键安装 → 配密钥」四步重写，含 uv/FFmpeg/Node 手动安装指引、模型国内外双源说明、安装自检与 FAQ。
- **动效导演简报标准**（吸收 motion-director / ai-video-director 两套模板 skill）：新增 `shared-references/motion-brief-standards.md`——输入四分类（目标帧重构/概念文案/流程数据/稿转场景）、时长默认假设、五相位交叠时间轴、自然语言→动作翻译表、趣味性策略、覆盖模式（A-only/B-only/AB-live 四布局）、引擎选择速查、导演简报输出结构、三帧静图+3s 短样片风格闸门、执行验收清单。
- **分镜模板升级**：`storyboard.template.md` 主表增「覆盖模式」列；新增「动效导演简报」区（MOTION-XXX 编号）与「Remotion/HyperFrames 素材组织」区（composition 命名、props 参数化、透明通道、独立工作区结构）；`broll_candidates` 增 `coverage_mode/input_class/motion_brief_ref` 字段；`motion-request-list.template.md` 同步覆盖模式列。
- 子 skill 联动：`video-plan` 增「动效条目导演简报（必做）」与规划规则；`b-roll-generate` Gate 1 增「三帧一样片」风格预览闸门与五相位时间轴检查、brief.md 必须承接分镜简报；`motion-engine-decision.md` 增速查交叉引用与双引擎互斥；README/DEPENDENCIES/SKILL/doctor.js/run_transcribe.sh 等全部文档同步 faster-whisper 语义；`.gitignore` 增 `models/`。

## v0.6.0 - 2026-08-29

- video-jianying-draft 对标 video-shotcraft 实战库重写健壮性（darwin 四轮，paired judge 累计 4×3-0 keep，功能测试 40 项全过）：
- 修 5 个真 bug：同名素材两层静默错链（save 层复制 + add_material 按名去重层）、重叠音频同轨必崩（SegmentOverlap）、save 前直接 rmtree 旧草稿、死 `local_path` 属性导致 assets 副本从未生效、`.env` 失效 `CAPCUT_MCP_DIR` 全 skill 断链。
- 健壮性：草稿名防路径逃逸校验、剪映进程检测（写盘前拦截，防半写损坏）、草稿根已验证自动探测（`--output` 可省）、媒体打包进草稿 `assets/` 并改写路径（草稿自包含，原素材移动不影响）、原子落盘、缺失媒体上报 `missing_media`。
- 新增 macOS 支持（移植 video-shotcraft `mac_draft.py` 实测逻辑）：`draft_info.json` 入口、platform 设备指纹（明文老草稿自动扫描 / `--donor-draft` / 实验模式三档）、媒体池登记、`root_meta_info.json` 注册与失败回滚；指纹扫描排除自身，防冒用 vendor 模板携带的他人指纹。
- `add_audio` 重叠音频默认贪心分道（自动溢出 `BGM-2`/`SFX-2` 新轨），`--no-lane-split` 严格模式；同名媒体自动加后缀永不静默错链。
- SKILL.md 沉淀实测标定常数（字号换算 ÷10.8、transform_y 半高归一、微秒边界铁律、双语字幕双轨）+ 新机器冒烟测试 + 交付验收清单；失败模式表扩至 11 行。

## v0.5.0 - 2026-08-25

- 终评残留弱点修复轮（11 文件，paired 3-judge：10 keep / 1 revert）：
- video-rough-cut 补 8 分支失败模式表（转录空输出/缓存失效/take 未匹配>20%/顺序冲突/爆音/源缺失/时长漂移/GPU 降级）。
- video-jianying-draft 补失败表（模板版本回退/草稿加密/cache 丢失恢复）+ save_draft 🔴 检查点 + 独立禁止节。
- video-migrate 独立禁止节被 judge 多数决 revert（5/6 复述原则节），仅保留唯一新规则「迁移与修复分离」并入原则节——本合集 darwin 棘轮首次真实回滚。
- video-status / video-polish / video-assets / video-caption-correct 各补 1 个校准 🔴 检查点（矛盾路由/final 前 QA 图/下载清单/句级删除 diff 确认）。
- 全部 14 个 skill 测试 prompt ≥3 条（新增第 3 条均为失败/拒绝 case）。
- b-roll-generate 硬编码工作区路径改为结构化合集根探测（向上两级 + scripts/b-roll-generate/ 判据）。
- 根 SKILL.md 修正 scripts/video-plan、scripts/video-fine-cut 为纯文档目录的措辞；README 安装路径去机器特定化 + .env 文件夹分发警告。
- 复评（3 全新 judge）：合集均分 82.8 → 85.7；目标修复 jianying-draft +9.3、rough-cut +8.3。

## v0.4.0 - 2026-08-25

- b-roll-generate 吸收 `collage-broll-style`（TapNow 版）的生成原理（用户指定）：
- 新增「AI 生成模式」顶层二分：**vox 拼贴**（彩色纸拼贴 + 空场首帧组装）与**首尾帧**（任意风格的起止帧控制），含各自硬纪律。
- 新增「模型可用性与降级级联」：T1 配置 API（check_setup.sh 探测）→ T2 ChatGPT Web 端 image2（静帧/空场首帧）→ T3 Google Flow（视频）；降级显式告知、notes.md 记 engine 层级、产物统一落盘命名、降级不重开审美确认。
- 新增「拼贴风格多样性」：底色按语义轮换表（焦橙/芥末黄/墨绿/深紫/青绿/钴蓝），批次纪律（相邻不同底、N 条 ≥⌈N/3⌉ 色系、manifest 记 hex 防撞色、连续两期同色系提醒）。
- 首尾帧路线新增「空场首帧派生」：以确认静帧图生图清空（替代 ffmpeg 纯色图），底色纸纹与尾帧一致；自动 QA 不单开确认门，失败退同底色文生图兜底。

## v0.3.1 - 2026-08-25

- darwin 全量优化 pass（11 个 SKILL.md，2 轮 paired judge 仲裁，3-0/33 + 3-0/7 keep，0 revert）：
- 全部子 skill 补齐「失败模式与恢复」三段式表（触发条件/一线修复/仍失败兜底）；关键决策点加显性 🔴 CHECKPOINT 标记（init 参数询问、fine-cut 交接、b-roll-generate Gate 1 付费/写码闸门）。
- 根 SKILL.md 目录清单修正为与仓库实际一致的结构，消除缩进错位和部署态/模板态混淆。
- video-migrate 推断规则对齐 `migrate.py` 实际行为（纯文件存在性判断），去除文档虚构的 JSON 解析/时长校验。
- b-roll-generate 清除失真引用：`generate_video.py` 参数表对齐真实 argparse；首尾帧路线改用真实脚本 `generate_veo_first_last.py`（含必需 `--gcs-uri`、9:16/720p 默认值警告）；移除不存在的 `prepare_first_last.py`/`qa_collage_video.py`。
- 外部参考目录（`<外部参考项目根>\*`）降级为软依赖：不可用时跳过并记录，不阻塞流程。
- 5 个 skill 补充 dim9「禁止/反例清单」章节。

## v0.3.0 - 2026-08-25

- 粗剪新增 `select_takes.py`：多遍重读场景下检测每句文稿的所有 take，按文本匹配/首尾完整/停顿/语速打分选最佳，产出 `takes_decision.json/md` 与 `finalKeeps_<source>.json`；EDL 只能引用被选中的 take。
- 粗剪新增 `tighten_pauses.py`：保留段内 ≥0.35s 句中停顿默认收紧到约 0.25s，可产出 render.py 兼容 EDL 骨架；精剪阶段不再手工剪重复 take 与死停顿。
- 剪映 Draft 新增 `subtitle_split.py` 并接入 `add_subtitle`：超长字幕条默认拆为 ≤18 显示单位（汉字 1、ASCII 0.5）的剪映原生风格短条，时间轴连续、拆分点优先标点，另存 `.split.srt` 供核对；字幕样式修正为居中对齐。
- `align_to_manuscript.py` 句子逗号再拆阈值 80→32 字，上游 SRT 条目更字幕友好。
- 分镜→B-roll 衔接：`storyboard.json` 强制包含 `broll_candidates` 结构化数组；`b-roll-finder` 机会表新增分镜镜号列与强制对账表（保留/降级/待定），不得静默丢弃前期规划；`b-roll-generate` Gate 0 纳入 `motion_request_list.md` 核对。
- 新增确定性测试：`test_select_takes.py`（4 用例）、`test_subtitle_split.py`（7 用例）。

## v0.2.0 - 2026-08-13

- 新增 `video-skill-optimize`，从真实任务、用户纠正、失败和成功模式记录脱敏证据。
- 引入 SkillOpt 风格的有界候选、留出案例严格增益 Gate、拒绝缓冲和人工采纳。
- 新增目标哈希校验、采纳前备份和原子替换，禁止优化器自动修改自身。

## v0.1.0 - 2026-08-12

- 创建视频制作 workflow 合集。
- 固化“规划 → 粗剪 → 校对 → Draft → 素材 → 精剪 → B-roll → 合成”的阶段顺序。
- 将 Remotion、HyperFrames 和拼贴 AI 明确归入 B-roll 生成体系。
- 增加项目目录、状态、交接契约、B-roll 风格和 QA 参考文档。
- 统一使用根目录 `.venv` 和 `uv.lock` 管理 Python 依赖，脚本不再回退到系统 Python 或 Anaconda。
