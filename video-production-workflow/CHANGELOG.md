# Changelog

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
