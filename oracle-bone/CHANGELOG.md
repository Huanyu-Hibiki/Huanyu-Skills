# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed — 工作流入口合并与制作边界收敛（2026-09-18）

- `oracle-learn-from` 与 `oracle-apprentice` 合并为 `oracle-study`，提供 `benchmark` / `practice` / `dual` 三种模式；旧名称变为薄兼容别名，只读迁移由新入口负责。
- `oracle-cover` 合并封面生成与参考封面分析，通过 `--mode generate|analyze` 选择；旧 `oracle-cover-analyze` 变为薄兼容别名转发到 `analyze`。
- 移除运行时 `oracle-edit-plan`；剪辑计划、视觉包装、动效逆向、B-roll 与成片 QA 统一路由 `video-production-workflow`。历史协议和词典移入 `references/legacy-*`，不删除用户资料。
- 根 `/oracle-bone` 改为最小任务路由器：明确请求直接进入 leaf skill，跨层请求只做必要组合；交互中区分事实、经验、推断与待验证假设。
- 安装清单从 29 个收敛为 26 个运行时 skill，并补充 study/cover/routing 契约测试。

### Added — 视觉拆解模式 + 包装规格 + VPW 交接（2026-09-12，第二十批，方法论原理参考 hypit）

- **新增共享规格语言 `references/packaging-vocabulary.md`**：视觉系统六元组（内容外观/空间关系/入场/活跃行为/持续/退场，绑定转写段落）/ 动效四语义（入场抓注意/落定建状态/替换保可读/退场让位）+ 描述纪律（动效名字只是起点，要写路径/缩放/透明度/节奏/过冲）/ 声音四层（语音主轴/音乐情绪底/环境跨切延续/音效挂感知事件）/ **词锚规格**（锚"transcript 第 N 段"不锚秒——换文案规格仍有效，执行侧词级时间戳兑现成秒）
- **oracle-apprentice 新增 `—visual` 模式**：拆博主的视频包装与动效——Phase V0 证据准备（现有转录管线拿段落时间戳 + ffmpeg 抽帧：scene 变化点密采 + 每 3s 粗采，证据 ≤40 张控成本 + **多模态检查**：Read 读帧失败即降级文字层拆解并如实声明，绝不按转写脑补画面）→ Phase V1 系统级拆解落 `packaging-notes.md`（描述与解释分开，无证据标未证实）→ Phase V2 值得偷的包装过三重验证门照旧；oracle-edit-plan 为其消费方
- **oracle-edit-plan 增强**：plan 模式加「包装规格」节（从 packaging-notes/cover-patterns 搬运规格，本期不做的如实列出不虚设）；accept 模式加包装验收（词锚核对/字幕配置可读/共享布局/装饰性清退）
- **VPW 交接分支**（oracle-edit-plan Integration）：单机=按姊妹 skill video-production-workflow 的 handoff-contracts 打包（定稿→manuscript.md 带 YAML 头 + edit-plan + packaging-notes 落其 `video scripts/`，broll/motion 意图整理为其明文欢迎的 broll-compose.json/motion_request_list.md；两套目录约定不合并）；双机=制作交接包（edits/handoff-manifest.md 清单）经 git/网盘到剪辑机，VPW 在 B 机自闭环，成片+master.srt 回传走 accept 验收——中间过程 AI 不可见，两边 state 不跨机互写
- MAINTENANCE §5 署名 hypit（修改版 Apache 2.0，仅原理零复制）+ 登记 VPW 交接点（对应其 external-references 吸收词典格式的先例）；行为用例 27

### Added — oracle-feishu 飞书多维表格同步（2026-09-12，第十九批）

- **新子 skill oracle-feishu（29 号）**：把链路结构化数据同步到飞书多维表格做可视化与监测——**五张表全部从本地文件确定性推导**：episodes 作品总表（预测 vs 实际/偏差/状态，源 = predictions + state.shoots）/ candidates 候选池（含 source_tier/回流标记，源 = candidates.md + history）/ calibration 校准样本（bucket 命中率，源 = 已复盘 predictions）/ trends 热点台账（信源贡献度）/ snapshots 状态快照（buffer/待复盘/confidence 时间序列）
- **单向只读镜像铁律**：本地文件是唯一事实源，绝不从飞书回写；幂等 upsert（按稳定 id / 快照按日期覆盖）
- **前置用户自配**（本 skill 不代配凭据）：用户在 Agent 配好飞书 CLI + `.oracle-secrets.json`（已 gitignore）写 feishu 块——`cli_cmd` 命令模板（{app_token}/{table_id}/{file} 三占位符，不绑定具体 CLI 实现）+ app_token + 表 id；表结构用户在飞书侧按字段清单自建
- 预检四态（state/secrets/CLI/auth）；首次同步数据出境 🔴 CHECKPOINT（full-auto 档不豁免）；`—dry-run` 只推导不推送；字段缺失推空值不猜；数据最小化（正文不出境）
- 全链路同步：计数 29（root/README/DESIGN §5 §10/install/uninstall/ps1/MAINTENANCE）+ 路由表 + context.py readlist + workflow.template 触发词；行为用例 26

### Changed — 选题情报判定纪律（2026-09-12，第十八批，方法论原理参考 market-intelligence-radar）

- **信源层级 source_tier（A-E）进候选 schema**：A 官方一手 / B 权威半官方 / C 专业媒体 / D 社区讨论（弱证据）/ E 聚合号与 SEO 摘要（只可溯源）；trend-sources adapter 文档标注默认层级；**E 层单源不入池**——只做线索找 A-D 佐证；**recommend 稳分位证据门**：E 层或无佐证 D 层候选不进稳分位（顺位递补，可进实验位/弱信号）——防营销号带节奏混进"今日必拍"
- **旧闻回流检测（第五态 recirculation）**：归一化键未命中但同实体同事件类型的跨站新稿 = 旧热点二次发酵——计 trends-history 台账不进新候选数，池内原条目附注"二次发酵中"（REVISION 式持续热度信号）；拿不准标"疑似旧闻回流"
- **event_at 计龄口径**：velocity 计龄优先事件发生时间（旧事件新发稿按发布时间算会虚高）；无 event_at 标注"按发布口径"；都不立 → 新鲜度 unknown、热度 N/A 不猜、入池降档展示；candidate-schema 新增 `source_tier` / `event_at` 可选字段
- **覆盖账本**：trends 汇总先出"源 × 信封状态 × 最新验证变化/none × 缺口"表再出候选表——"今天没料"变得可审计，不注水凑条数
- MAINTENANCE §5 署名（market-intelligence-radar，MIT，仅借鉴原理实现全原创）；行为用例 25

### Added — oracle-edit-plan 剪辑计划与成片验收（2026-09-12，第十七批，方法论原理参考 OpenMontage）

- **新子 skill oracle-edit-plan（28 号，plan/accept 双模式）**：把链路里"实际制作（AI 不可见）"变成可计划、可验收——plan 模式（shoot 后）：素材探测（ffprobe 逐文件或口头三问，**禁止按文件名脑补**）→ 规划含义（覆盖率/混拍/缺口）→ 剪辑计划工件落 `edits/edit-plan.md`（节奏定调：调性→镜头时长区间+前 5 秒钩子剪辑密度；剪切点清单**每刀必带理由**；转场词汇表全片 ≤4 + 社媒模板腔禁用清单；声音设计：口播为主轴/声音比画面提前滑入焊住硬切/全片唯一一处静音留白；邻接多样性：相邻两镜不同景别不同主体；B-roll 覆盖核对；字幕计划）→ 🔴 CHECKPOINT 用户确认；accept 模式（成片回来）：ffprobe 机械核查（时长 ±10%/前 5 秒钩子在位/转场在词汇表内/断句完整性/静音 ≤1）+ 幻灯片感六项自查（同画面久留/装饰性空镜/动态不足/意图不明镜头/文字堆砌/口说无凭的电影感）→ 每条指位 + 带修法
- **协作契约 12：审稿三轴**——所有审查类输出（no-ai-slop / who-for / open-source / edit-plan 验收 / retro 诊断）逐条过：准确（finding 指到具体位置，禁幻觉批评）/ 完整（发现同类扫全文）/ 建设性（critical 必带修法，提不出的标「待查」不阻塞）；往返最多 2 轮后带警告放行，卡点交给数据复盘
- **oracle-shoot**：Phase 5 输出加 edit-plan 下游可选指路
- content-folder-schema 新增 `edits/` 子目录（edit-plan.md + acceptance.md）；retro 可读 acceptance 区分"内容偏差 vs 制作偏差"
- 全链路同步：根 SKILL.md（链路/路由/目录树/契约 12 条/计数 28）/ DESIGN §5 §6 §10 / README / MAINTENANCE / install/uninstall / context.py / workflow.template；行为用例 24
- **License 边界**：OpenMontage 为 AGPLv3——仅学习原理，未复制任何代码或文本（MAINTENANCE §5 署名），oracle-bone 维持 MIT

## [1.1.0] - 2026-09-12

本版主线：**语音起稿循环（oracle-voice）+ 语音转写体系**（App 转写优先 / SenseVoice 中文快线 / whisper 多语种）+ **标题链路合并**（oracle-title 吸收 title-pick）+ **参考项目机制补强**（验证门 / 置信度地板 / 四态信封 / 交互预算三档）。

### Changed — 参考项目机制补强（2026-09-12，第十六批，借鉴 cangjie-skill / huashu-skills / union-search-skill / last30days-skill）

- **oracle-apprentice 三重验证门**（借鉴 cangjie-skill，MIT）：新增 Phase 3.5——「值得偷」项进卡片前过 V1 跨域（≥2 独立语境）/ V2 预测力（能推演没拆过的场景）/ V3 独特性（抹掉博主名字人人都说的常识不通过），不过留档 analysis.md「未通过验证」节写明卡哪门；知识卡片新增「触发场景」（何时想起用 + 语言信号）与结构化「反例」（失效场景 + 为什么掉进去 + 预警信号三段齐）；术语拆解补 key_distinction（博主个人黑话 vs 常识用法 → 可入 voice-lexicon 专名表）；通过率自检——全过 = V3 失守
- **oracle-recommend 置信度地板 + 诚实空池**（借鉴 last30days，MIT）：MIN_COMPOSITE_TO_RECOMMEND = 6.0（与 trends 入池同标尺），低于只作弱信号；某轨全不过线该轨零推荐；全池不过线 → Phase 3.5「本池没有值得做的候选」+ 最接近弱信号（差距归因）+ 补池建议——绝不硬凑 Top N（推弱候选 = 产能拍扑街稿 + 污染校准池）
- **oracle-trends 四处强化**（借鉴 last30days + union-search）：① Phase 0 运行前预检——逐 adapter 依赖三态健康表（✅/⚠️/❌），❌ 的明示"本轮未覆盖该源"② 信封四态语义——✅ 有货 / ⚠️ no-results（唯一可说"该源没货"）/ ❌ failed（覆盖不完全）/ ⏭️ skipped-unconfigured ③ 去重升级归一化键——URL 剥 utm/gclid/fbclid + 解短链 + scheme/host 小写，标题空白归一 + casefold ④ velocity 热度修正——互动 × 1/√(小时龄+1)，<24h ×1.2，多源佐证 ×(1+0.15×(n−1))，与 composite 正交（只做展示与 ±0.3 平手裁决），输出加「热度/时效」列
- **交互预算三档**（借鉴 huashu-skills 的 Full Auto/Guided/Collaborative——该仓库无 License，仅借鉴机制）：init Phase 1 新增 Q5 采集 state.interaction_level（缺省 guided）；协作契约新增契约 11——full-auto 只守不可逆硬门（生成类直接给 ⭐推荐并落盘 + 修改入口），决策类（选题/标题/发布）三档都拍板，随时切换；快速自检清单补第 10 条
- **明确不搬**：cover 的"短 prompt 黄金律"（与第十四批封面排版数值设计冲突）；last30days 的 worthiness 评分（oracle-bone 有自校准 rubric，不引入外部打分体系）
- MAINTENANCE §5 致谢四项目（union-search MIT 声明于 README/代码头但无 LICENSE 文件；huashu-skills 无 License——零文本复制声明）

### Changed — oracle-voice 语音起稿 + title 合并终审（2026-09-12，第十五批，姜胡说方法论吸收 + 结构简化）

**新增**
- **新子 skill oracle-voice（语音起稿循环，情绪先行 · 原话保真）**：像和朋友聊天一样录音讲选题（情绪是桥，先接情绪再进内容；不怕跑题停顿，停顿不转文字）→ adapter 转写（script-extraction，.venv 铁律；失败走手动粘贴绝不编造）→ **双心态打磨循环**：文字轮只管吃透知识（去语气词/补"回头查"清单/标❓断点——断点等用户下轮自己圆，AI 不代补；整理稿本身是知识库资产）、录音轮只管表达（不照稿念）→ 收敛判据（无未解断点 + 用户自评讲顺）→ 基于最终转写稿出 **3 条候选稿**（开场黄金 3 秒各配不同 hook-prototypes 原型 + 结构按 script_patterns + 金句必有转写原话原型）→ 🔴 CHECKPOINT 迭代（选 N / 再来 3 条 / 第 X 条缺 Y 微调）→ 定稿落 scripts/（header 继承 seed draft 格式）
- **oracle-voice 硬纪律**：PRESERVE_VOICE（AI 只删重复/调顺序/拆长句/加小标题，不加一个用户没说过的观点——治"AI 直出稿没有我"）；DASH_BAN（候选稿/定稿禁用破折号）；EMOTION_FIRST；裸转写模式（—transcribe-only，与链路解耦）
- 补 oracle-cover-analyze/test-prompts.json（此前唯一缺测试 prompts 的子 skill）

**流程变更**
- **seed → voice 接线**：seed 定题后默认输出「录音聊天卡」（讲什么/讲给谁/看完做什么/情绪触发点）并引导 /oracle-voice；**AI 直出 draft 降级为 seed 显式降级路径**（用户点名"你直接写"才走，脚手架警告不变）；Phase 2A-2 钩子/兴趣属性/互动设计规则保留在 seed 作单一来源，voice Phase 5-6 引用执行
- **oracle-title 合并 oracle-title-pick**（27→26→27）：Phase A 生成（原流程不动）→ Phase B 终审（淘汰清单合并为一份：结构段 Phase A 筛 + 红线段 Phase B 再拦；5 维隐式评估 + ⭐推荐 ≤80 字理由）→ Phase C **单次 CHECKPOINT**（用推荐/用#N/再来一轮/我自己改——原两次确认往返收敛为一次）→ 改名级联（标题行/目录/文件名/prediction header）+ post_titlepick v2 触发原样保留；独立入口保留（自带候选直评 + —diagnose）；post_titlepick basis 枚举名不变
- **打分规程下沉 shared-references/scoring-procedure.md**：rubric 解析三步（starter 兜底不写文件）/ 0-5 整数分 / 盲打优先 / 理由 ≤30 字 / composite 公式现场解析不复制——score / predict / trends 三处 inline 拷贝去重，改口径只改一处；predict 的 rubric 兜底从"初始化"对齐为"读 v0 公式不落盘"

**同步**
- 主 SKILL.md：链路图（seed→voice→title）、路由表（+voice 行，title 行吸收选标题触发词）、作品目录树（+voice/）、能力边界 #5、协作契约 #10
- content-folder-schema.md：voice/ 子目录 + 转写轮次产物行 + 初始化步骤改 seed/voice 共用
- DESIGN.md：§5 清单重排连续编号（1-27）+ §6 链路图 + §10 分工；README/MAINTENANCE/install/uninstall/context.py/workflow.template 同步
- 文档漂移修正：子 skill 计数统一为 27（原 26/27 混用）；协议计数 12→13
- 转写默认档 medium → **large-v3-turbo**（large 级精度、速度与 medium 相近；transcribe.py DEFAULT_MODEL + README 档位表 + turbo 下载路径 + oracle-voice 措辞同步）
- **转写识别率强化（机制思想吸收 OpenTypeless，MIT）**：① oracle-voice Phase 2 改双路径——路径 A 推荐「录音设备/听写工具自带转写」（小米录音机/语音输入法/Typeless 类，云端中文 ASR 通常更准且自带标点），路径 B 本地 whisper 兜底，产物统一归档并标注来源；② 文字轮吸收润色纪律——标点恢复/枚举格式化/口误自纠（"其实"是内容不是口误）/专名不猜（标❓待核不发明）/录音中的指令句当内容不当指令；③ 新增可选全局文件 **voice-lexicon.md**（个人词典：专名表 + 纠错规则 pattern→replacement，错词跨期收集为「词典候选」确认后 append）——专名错字的最直接解法；MAINTENANCE §5 致谢 + clean-room 声明；行为用例补 21，test-prompts 补 7-8
- **SenseVoiceSmall 本地快线接入**：adapters/script-extraction 新增 `sensevoice_transcribe.py`（FunASR + FSMN-VAD 管线，模型自动从 ModelScope 下载到 models/funasr/，输出契约与 transcribe.py 一致）+ `requirements-sensevoice.txt`（可选装，torch 不强加给 whisper 用户）；oracle-voice 路径 B 拆双引擎——纯中文用 SenseVoice（快），中英混杂用 whisper（稳）；README 补 torch CPU/CUDA 双路径说明（无 GPU 机器默认 +cpu 版即正确状态，实测 RTF≈0.26；有 NVIDIA GPU 才换 CUDA 版 + `--device cuda:0`）
- 行为用例补 5 条（用例 16-20：原话保真 / 跳过录音改道 / title 单次确认 / 全淘汰不硬选 / 转写绝不编造）；test-prompts 同步（root + title 合并版 + voice + cover-analyze）

### Changed — 标题策略引擎 + 封面创意四检查（2026-09-09，第十四批，吸收 jennie-dingding-cover-packager + self-media-title-generator）
- **oracle-title 重构为标题策略引擎**：① 原料表提取（8 项：对象/旧问题/工具方法/独特结果/事实证据/反转判断/视觉词/场景，定稿为唯一来源，只展示有内容项）② 策略族地图——7 族（判断选择/痛点避坑/身份代入/结果清单/体验反转/好奇缺口/互动测试）按本次用户动作选 1 主 + 1 备 ③ 内部发散 ≥8 → 淘汰清单筛 → 输出 3-5（原直出 3-5）④ 点击承诺三件套至少含两项（对象/方法变化/结果爽点）⑤ 新增已有标题诊断（—diagnose：五查 + 直接保留/轻微压缩/建议重做 + 同策略/换策略优化版）⑥ 事实纪律：数字/结果/经历必须可回溯定稿，不为套策略编造
- **oracle-cover 吸收封面创意系统**：创意四检查（语义准确/因果可见/高概念/低视觉噪音）为落盘前硬自检 + 语义桥接三行（标题承诺/内容机制/画面机制说同一件事，字面具象化=弱）+ 3:4 两行标题默认占比数值（宽 90-93%/高 31-34%/顶距 6-8%/左右 4-5%）+ 跨平台锁定（同标题同主题同配色，按比例重构图不裁切；确认后标题逐字锁定）
- **oracle-cover-analyze 对偶接线**：拆解卡新增"创意四项快评"（✅/⚠️/❌ + 一句理由）——拆图与生成用同一把尺；cover-patterns.template.md 同步
- **版权边界**：只吸收策略族分类学/流程思想与排版数值，未复制 75 公式文本；公式精炼引用走自有的 references/dbskill-essence-distill.md（title 接线行）
- 主 SKILL.md 路由表同步"诊断标题"触发词

### Changed — oracle-description 反 AI 味重写（2026-09-09，第十三批，实战反馈 + 真实语料校准）
- **根因（实战 EP007-EP014 复盘）**：旧规范自己教的——"每行一个价值点，emoji 引导""小红书高 emoji 密度""标签 10-15 个"产出五件套模板腔（钩子→emoji 价值点→🎯适合→❤️支持→署名），期期同骨架
- **两条铁律（🛑）**：① 内容事实一致——描述是视频内容的概括，每个数字/结果/承诺必须能在定稿找到出处（Workflow 新增"事实清单"步骤：定稿提取 3-5 条最强事实，所有平台文案只从清单取材 + 逐句回溯自检）；② 反 AI 味——混进真人描述堆违和即重写
- **emoji 配额制**：B站/视频号/公众号/抖音 0-1 个，小红书 ≤3 个且禁做项目符号；情绪靠语气词和具体事实（真实语料九篇几乎零 emoji："啊啊啊啊太可爱了！"）
- **结构纪律**：废五件套；改"第一人称 + 具体事实 + 自然段落"；句式黑名单（纯纯干货/排比三连/还在纠结XX/课程目录式罗列）+ 口吻三禁（公告/公关稿/功能说明书）
- **标签收敛**：每平台 ≤8 个（小红书 4-8 / 抖音 3-5），只写定稿真实相关词 + 已有活动标签；CTA 收敛为整个描述一个主 CTA
- 行为用例补 3 条（用例 13-15：emoji 超配额 / 事实漂移 / 模板腔）；方法论来源：对标/视频文案/文案参考.md 九篇真人描述 + jennie-dingding-cover-packager 的"第一人称自然口吻、避免公告/公关稿/功能说明书语气"与内容兑现检查思想（只借思想，未复制文本）

### Added — oracle-cover-analyze 对标封面拆解（2026-09-09，第十二批）
- **新子 skill oracle-cover-analyze**（27 号）：拆解对标封面 → 固定 schema（构图结构/标题区层级/人物与物件/背景氛围/视觉动线/视觉隐喻）→ 复用配方落盘项目根 `cover-patterns.md`（append-only，不嵌原图）——补齐三维度对标的视觉维度（learn-from=数据 / apprentice=写法 / cover-analyze=视觉）
- **参考程度门**（🔴 Phase 1 一次确认）：轻度=只借结构逻辑与隐喻转译 / 重度=构图层级字体氛围尽量贴近；默认轻度，重度须显式
- **版权三不三借**（🛑 硬红线）：不复制人物身份/logo/品牌元素/原文案/水印，只借构图结构/信息层级/视觉逻辑；字体气质与色彩氛围只记方向
- 批量共性归纳（≥3 张、须 ≥ 半数样本出现）；URL 走 curl 下载到 `.oracle-cache/cover-ref/`（gitignore 区），不开浏览器 GUI（Adapter 铁律）；识别不了标"无法判断"不编造
- **oracle-cover 接线**：框架来源新增 #2"对标配方"（cover-patterns.md），优先级在 _base.md 之后、user-profile 之前；Inputs 表 + Integration 同步
- 接线：主 SKILL.md（路由表 + 文件清单 + 26→27）/ DESIGN.md（§5 清单 + §6 链路 + §10）/ state-management.md 信息主档表（cover-patterns.md 主档行）/ tools/context.py（cover 任务读取清单）
- 新模板：templates/cover-patterns.template.md（拆解档案骨架）
- 来源：结合 template/cover 三个封面 skill（dailun / oh-my / xiaoliang）的生成方法论与"对标封面拆解"实战思路（参考程度确认 + 结构拆解 + 替换边界）设计；实现为 oracle-bone 原创表达

### Added — 上下文预算棘轮 + 任务摘要出口（2026-09-09，第十一批，对照 template/ip-strategist 借鉴）
- **MAINTENANCE.md 新增**：上下文预算棘轮表（主 SKILL ≤31KB / 子 skill ≤18KB / 协议 ≤15KB / 单任务运行时 ≤78KB / 摘要 ≤6KB，只许收紧）+ 跨文件同步规则矩阵（协议↔子 skill / schema↔migrations / 路由↔frontmatter / 工具须有消费方）+ 发布前检查清单
- **tools/context.py 新增**：任务状态摘要器（只读，≤6KB）——confidence 派生表 / buffer / 待复盘到期 / stage_constraint 兜底 / schema 漂移警告代码化为单一口径；退出码 0/2/3（未初始化不代建，路由 /oracle-init）；26 子 skill 后缀各配建议读取清单
- **tests/test_context_budget.py 新增**（首个 unittest 套件，纯 stdlib）：预算棘轮 4 项 + context.py 行为回归 6 项，`python -m unittest discover -s tests -v` 即跑
- 接线：主 SKILL.md（按需读取纪律 + 文件清单 + 开发者节）/ state-management.md 读协议（任务摘要快速路径）/ oracle-status Inputs（可选快速路径）
- **借鉴边界（clean-room）**：设计思想借鉴 template/ip-strategist（CC BY-NC 4.0）的预算棘轮 / 任务摘要 / 真源-运行层同步三项工程纪律，实现按 oracle-bone 自身架构原创重写，未复制任何文本或代码；oracle-bone 维持 MIT 不变，致谢见 MAINTENANCE.md §5

### Added — 三平台五维详情采集（2026-08-26，第十批）
- **B站/小红书/视频号补齐五维增量指标**（对齐抖音统一键：封面点击率/跳出率+口径/5s完播率/完播率/平均播放时长）——此前三平台只有播放/点赞/收藏/评论基本计数
- 采集路径：B站=本卡片「数据」弹窗刮取+XHR 监听；小红书=「数据分析」触发 analyze/note_detail API；视频号=「数据中心」触发详情 API；均为 DOM 叫法刮取 + API 容错解析双源
- 容错解析器：递归扫载荷中 ≥2 个五维候选字段的对象（snake/camel 字段名候选全覆盖），百分数智能格式化（0.452→45.2%），时长归一（毫秒/分秒/mm:ss→Xs）；未知形状静默返回空
- collect.py：detail_steps 传 wid（B站按卡片定位）；详情期监听数据自动回流列表行（只填空字段）；修复 B站导出死代码（原 detail_steps 因缺 DETAIL_URL 从未被执行）
- B站诚实边界：无 2s/3s 跳出率与 5s完播指标——留空不硬凑
- README 新增「五维增量指标采集」节（--details N 用法 + 平台叫法映射表 + 校准指引）
### Fixed — Adapter 铁律：封杀 computer-use 替代采集（2026-08-26，第九批，实战反馈 II）
- **根因**：AI Agent 自带 computer-use skill（"Load whenever computer_use tool is available"）随时抢活；oracle-bone 的 `<skill包>` 占位符 + 裸 `python` 命令在非 Claude runtime 解析不了 → 模型滑向视觉操作
- 伞 SKILL.md 新增「🔴 Adapter 铁律」：adapter 一律 Bash 调脚本、解释器必须用 adapter 自带 .venv（含 `<包根>` 解析规则与 Windows/Unix 路径）、禁止 computer-use/GUI/亲手开浏览器替代
- compass-retro / retro 的采集命令改为可执行形态（`<PY>` + `<包根>` 显式解析）+ 就地 🚫 禁令；伞触发词补「采集数据/拉数据」
### Fixed — auto-collect 登录门重写（2026-08-26，第八批，实战反馈）
- **根因**：网页登录态 1-2 周过期后，采集路径检测到未授权只塞一行错误就关窗口——headful 下二维码闪现即关（"不提醒不等待"），headless 下完全不可见；AI agent 拿不到机制信息开始自由发挥（挨个开浏览器/检查 Edge）
- headful 失效 → 弹登录页 + 大声提示 + **轮询等扫码 3 分钟**（`wait_for_login`，30s 节奏提醒），成功自动继续采集
- headless 失效 → 立即退出码 2 + 尾行 `NEEDS_AUTH=<平台>`（机器可读）；`--auth-only` 等待加上限 10 分钟 + `AUTH_FAILED` 退出码
- `all` 收尾汇总失效平台 + 逐平台恢复命令；单平台失效不弃整轮
- compass-retro SKILL.md 新增「🔴 登录态协议」（profile 位置/与日常浏览器无关/过期属正常/唯一恢复路径），README 新增「登录态生命周期」

### Fixed — 工具脚本接线闭环（2026-08-20，第七批）
- **score-curve.py 此前零引用**（自述供 bump/status 参考但从未接线）→ 三处接入：oracle-bump Phase 0 诊断前置（偏差方向序列决定 rubric bump vs bucket-only 分流）+ FAIL 诊断报告成因定位；oracle-status Inputs/分轨校准行（平均偏差 + bucket 命中率，交叉核验 state 偏差队列）；oracle-compass-retro Phase 4.5 新增"预测系统修订候选"
- **dashboard.py → oracle-status**（自述供 status 消费但未接）→ Inputs 表 + 📈 健康度"实绩快照新鲜度"行（超过一个复盘周期未更新 = Path B 用户手动档拖延信号）
- 边界已实测：score-curve 对无样本项目输出"无有效校准样本"退出；dashboard 无库时 `{"ok":false,"message":"no_runs"}`——status 只读调用不崩

### Added — script-extraction 五平台拟人化反爬（2026-08-20，第六批）
- **平台档案自动分流**：B站/小红书/抖音/知乎 URL 自动识别，套用对应反爬档案（抖音/小红书自动 `impersonate=chrome` TLS 指纹拟真 + 1.5s 请求间隔；全局退避重试 3s→8s）
- **curl-cffi 0.16.1b1** 加入 requirements——yt-dlp TLS/JA3 指纹拟真依赖（缺失自动降级并警告）
- `--cookies-from-browser chrome/edge/firefox`：直接复用本机浏览器登录态（B站字幕、抖音/小红书流地址必需），免导出 cookies.txt
- **视频号诚实拦截**：无公开网页提取器，URL 直接引导本地文件/粘稿；知乎纯文字回答标注"无需转录直接复制"
- 反爬策略移植自 data-scientist-community 实战（真实登录态 + 拟真指纹 + 拟人节奏 + 退避不硬怼）；README 新增「五大平台支持」表 + 抖音实操序列
- 修复：yt-dlp nightly `--retry-sleep` 新语法（`http:linear=3:8`）；字幕语言改为精确匹配（杜绝 YouTube 机翻轨 429）

### Added — script-extraction 真实转录管线（2026-08-19，第五批）
- **adapters/script-extraction/transcribe.py**：URL/本地文件 → yt-dlp（**nightly**，字幕轨优先含 auto-ASR）→ ffmpeg 抽音频 → **faster-whisper** 转录（VAD + 段落分组）→ transcript.md（输出契约不变）
- 模型三级解析：`--model-dir` > 本目录 `models/faster-whisper-<档位>/`（自动发现，gitignored）> 在线下载（失败时报错并指向 README 模型节）
- **README 模型下载双源指南**：ModelScope（pengzhendong/faster-whisper-* 系列，国内推荐）与 HuggingFace（Systran/faster-whisper-*，含 hf-mirror 镜像法），统一落位 `models/faster-whisper-<档位>/`
- 专属 `.venv`（faster-whisper 1.2.1 + ctranslate2 4.8.1 + yt-dlp nightly 2026.08.19，uv 三步 setup 与 auto-collect 同构）
- oracle-apprentice Phase 0/1 接线：预检（venv/ffmpeg/模型）+ URL 分支精确命令 + 落盘即完成；手动粘稿仍是零依赖主路径

### Improved — init 采访协议强化（2026-08-19）
- oracle-init 新增 🔴「采访执行协议」：一次只问一个问题、用户答完再问下一个、每问追问 ≤2 轮、每 Phase 复述确认、问完关键问题才产出档案文档
- 用户档案采访 6 问 → 8 问：新增 **内容风格**（口吻/节奏/视觉调性）与 **内容喜好**（喜欢做的题材 + 喜欢看的领域，cold-start seed 选题种子）
- user-profile.template.md 同步新增「内容风格」「内容喜好」节；主 SKILL.md 档案表与 README 同步

### Improved — darwin 优化第一轮（2026-08-19）
- Runtime 中立性：README 安装节三层结构（runtime 路径表）+ install.sh `--target <dir>`（参数可组合、缺参报错）
- 盲预测「污染边界」定义：其他作品实绩 = 合法锚点输入，仅当前作品自身数据构成污染（消除过度拒绝歧义）
- 主 SKILL.md 🔴/🛑 视觉检查点 ×4；hooks 对非 hook runtime 的降级注记；文件清单修正（删 2 幽灵引用、补 4 个 tools）
- 打包卫生：`.venv`/`__pycache__`/`content-analytics.db` 保持 gitignore 排除

### Added — v0.1.0 全量构建（2026-08-19）
- 骨架：主 SKILL.md（总协议 + 26 子 skill 路由表 + 三原则 + 轨道机制 + 协作契约）+ README + install/uninstall + LICENSE + .gitignore
- shared-references 12 份核心协议 + migrations/registry.md（schema 1.0）
- 26 个子 skill 全量（主链 7 / 选题打磨 8 / review 质检 5 / 支撑 6）
- starter-rubrics 5 份（opinion-video 已拟合参考版 / zero 等权 / conversion-video 泛化版 / 长文短文扩展位）
- templates 14 份（含三份档案模板 user-profile / content-plan / audience-profiles）
- hooks 三件套（prediction-immutability / session-start / meta-logging）
- tools/score-curve.py + adapters 四类（trend-sources 6 源 / perf-data / candidate-pool / script-extraction）
- references 5 份种子（做号定位提炼 / dbskill 精华 / 漏斗理论 / 转化轨手册 / 平台坑备查）+ examples

### Added — 数据分析基础设施（2026-08-19，第二批）
- **tools/data_normalizer.py**：四平台数据统一归一器（字段别名映射 / "1.2万"多值解析 / 跳出率口径标注 3s vs 2s / 零值过滤 / 标题清理）——actual_data 从此只有一种 schema（根治 bump P5 schema 漂移坑）
- **tools/snapshot_store.py**：SQLite 采集快照库（runs + snapshots 时序模型，latest vs prev diff 出播放增量/新作/互动率变化）
- **tools/dashboard.py**：分析引擎——五维增量指标提取 + quantile 分位阈值 + 规则建议（高互动低播放→复刻/衍生；高播放低互动→互动触发器/who-for；增长最快旧作→apprentice 拆解）+ A/B 粗分类
- **adapters/perf-data/auto-collect/**：Playwright 一键采集（四平台 .py 采集器：监听后台 API 响应 + DOM 兜底双源合并 / 复用本机浏览器 Profile / 授权保守检查 / 断点续跑 / --auth-only 首次授权 / --debug 校准模式）。**设计模式参考 data-scientist-community（AGPL-3.0，作者赵逍遥），clean-room 重写**——完整管线 collect → normalize → snapshot → dashboard
- 接线：oracle-retro Path B 改三级数据源（auto-collect → 手动导出归一 → manual paste）；oracle-compass-retro Phase 1/2 自动拉快照库 + quantile 建议联动 Phase 3/6
- 单测：归一器（万单位/逗号/口径/零值/标题话题清理）+ 快照 diff（增量/新作）+ 分位建议 + A/B 粗分——全部通过

### Added — 视频号采集（2026-08-19，第三批）
- `platforms/wechat.py`：视频号助手采集器（channels.weixin.qq.com）——宽容解析 + DOM 兜底；**候选端点态**，首跑 `--debug` 按 urls.log 校准 ENDPOINTS（README 有四步流程）
- collect.py：注册 wechat 平台 + `--debug` 新增全量响应 URL 日志（`<platform>-urls.log`）——端点校准的工作流基建
- data_normalizer：视频号字段别名（推荐量→收藏量）+ 平台探测关键词（视频号/wechat/channels/微信）
- oracle-publish：URL 识别表补 `channels.weixin.qq.com → wechat`
- 已覆盖平台：抖音 / 小红书 / B站 / 快手 / **视频号**（5 平台）

### Added — 发布链接自动解析（2026-08-19，第四批）
- **tools/link_resolver.py**：发布链接三合一——短链重定向解析（v.douyin.com/b23.tv/xhslink.com）→ 平台识别 + 内容 ID 提取（BV号/aweme_id/note_id）→ 标题抓取（B站走公开 view API 最稳；其他抓 og:title/`<title>` + 平台后缀清理）→ difflib 模糊匹配 shoots 队列 + 未发布 prediction（含"解析标题是完整版 vs 作品名短版"的包含关系加分）
- **oracle-publish Phase 1 重构**：Step 1a 链接自动解析（用户粘 N 条链接 → 确认表"链接→平台→标题→匹配作品(score)"→ 确认即登记）；Step 1b 手动流程保留为降级路径；Platform ID 直接复用解析的 content_id
- 纪律：score≥0.55 标 ⭐ 仍需用户确认；标题抓取失败不阻塞（平台+ID 已有）；无网络回退手动
- 测试：平台检测 8 例 / ID 提取 / 标题清理 / 模糊匹配（含 B站真网解析）全部通过

### 实机校准完成 — 四平台数据全通（2026-08-19，第五批）
- **授权修复**：`--auth-only` 循环不再 unauthorized 即退出——浏览器保持打开等本人扫码，authorized 自动继续（用户实机纠错）
- **B站校准**：卡片 = `.article-card`，BV+标题挂 `<a href>` 链接（不在主文本流）；headless 会被风控给空壳页 → 采集默认 headed
- **抖音校准**：列表在响应顶层 `items[]`；`metrics{}` 直带五维增量指标（cover_click_rate/bounce_rate_2s/completion_rate_5s/completion_rate/avg_view_second）+ view_count/like/favorite/subscribe——**五维闸门数据源就位**
- **小红书校准**：笔记管理页 = `/new/note-manager`（非发布页）；列表 API `note/user/posted`；**框架级修复：监听先于导航挂载**（首屏 API 在页面加载时发出，晚挂整段错过）
- **视频号校准**：post_list 状态码 **201 是正常业务响应**（framework 收 200+201）；objectId 带 `export/` 前缀取尾段；进入页面需点"内容管理→视频"触发 SPA 路由（新增平台 `post_navigate` 钩子）
- **反垃圾修复**：DOM 兜底行作品 ID 必须匹配真实 ID 形态（纯数字≥6/BV号/十六进制）——"时长冒充 ID"垃圾行不再污染合并
- **实测结果**：B站 8 条 + 抖音 8 条（含五维）+ 小红书 9 条 + 视频号 7 条 = **32 条入快照库**，dashboard quantile 建议正常输出

