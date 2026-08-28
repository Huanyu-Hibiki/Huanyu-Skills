# Changelog

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
