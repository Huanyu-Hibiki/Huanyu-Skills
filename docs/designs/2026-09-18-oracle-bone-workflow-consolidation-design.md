# oracle-bone 工作流收敛设计

## 目标

将 oracle-bone 从 29 个分散入口收敛为 26 个职责清晰的 skill：统一对标学习与封面工作流，移除已由 video-production-workflow 覆盖的制作能力，并让根 skill 能按自然语言需求进行最小路由。

## 已确认边界

- `oracle-cover` 保留为唯一封面 skill，提供 `generate` 与 `analyze` 两种模式。
- `oracle-study` 替代 `oracle-learn-from` 与 `oracle-apprentice`，提供 `benchmark`、`practice`、`dual` 三种模式。
- 删除 `oracle-edit-plan` 及 oracle-bone 内的剪辑计划、成片验收、制作交接能力。
- `video-production-workflow` 是终稿之后唯一的视频制作、包装、动效逆向、剪辑和 QA 系统；oracle-bone 不重复其视觉制作与爆款视频视觉分析能力。
- `cheat-on-content` 是 oracle-bone 的历史原版；运行时引用改为 oracle-bone，历史溯源可保留原名称。
- 本轮不将 dbskill 的内容资产工程、理论研究、共鸣/脚本流失诊断做成新 oracle skill；只吸收其最小路由与对标判断原则。

## 用户场景

1. 用户不知道当前该走哪一步时，调用 `/oracle-bone` 并用自然语言描述目标；根 skill 读取已有状态，路由到一个最匹配的叶子 skill，必要时只追问一个会改变路由的问题。
2. 用户要学习对标时，调用 `/oracle-study`：可分析账号级样本与数据、单条文稿的可练习机制，或在共享素材下同时完成两者。
3. 用户要生成本期封面或拆解参考封面时，均调用 `/oracle-cover`，由模式与输入类型决定工作流。
4. 用户确认终稿后转入 `/video-production-workflow` 完成制作；视频实际发布与数据回流后回到 oracle-bone 的 publish/retro 校准闭环。

## 设计

### 根路由

根 skill 从静态触发词表升级为任务路由器：先恢复用户目标、已有材料、项目状态和当前阶段；单个 leaf skill 已能交付时直接路由；仅在同一交付物需要独立必要能力时组合；缺失信息只有在会改变路由时才询问一个问题。根路由不自动启动长链，也不得绕过盲预测和发布状态不变量。

对话输出采用最轻可用模式：评价只交付评价、改稿只改稿；显式区分已知事实、用户经验、AI 推断和待验证假设。对标分析仅限公开、可观察的产出与机制，不推测创作者的私生活、动机或未公开能力。

### oracle-study

统一入口接受账号、作品、工作流或机制作为对标对象。所有模式先明确目标结果，并用 `产出 / 机制 / 资产` 三层区分可学内容：

- `benchmark`：3–10 个样本、表现数据与用户印象，产出仅定性的参照信号；不能直接改 rubric 权重。
- `practice`：一条素材的用户复述、质疑、迁移与最小实践，输出可落到用户轨道的知识卡片。
- `dual`：先共用素材归档，再分别输出账号级信号与单条可实践机制；统计关联不自动成为可复制技巧。

共享归档以 `study/<对象>/samples/<content-id>/` 为源；分析结果分别落在 benchmark、techniques 和包装学习档案中。视频包装/动效逆向不属于本 skill，交给 video-production-workflow。

### oracle-cover

`generate` 根据终稿、标题、频道视觉框架与已有 `cover-patterns.md` 生成跨比例封面提示词；`analyze` 从用户提供的参考图提炼可复用构图和视觉逻辑，确认后写入 `cover-patterns.md`。两种模式共用版权边界：只借结构与视觉逻辑，不复制原人物身份、品牌、Logo、水印或原文案。

### 删除制作层

删除 `oracle-edit-plan`，包括 `edits/`、剪辑计划、成片验收、VPW 交接包和只为这些能力服务的协议表述。oracle-bone 仅输出确认终稿，并在文档中把 VPW 标注为独立下游系统；两边不跨项目写 state 或中间工件。

## 数据与兼容性

- 对旧的 apprentice / learn-from / cover-analyze 名称提供兼容别名与触发词兼容路由：提示新命令，但只执行新模式实现，绝不保留重复工作流。
- 对旧 study 目录保留可读取的兼容说明；新写入统一采用 oracle-study 的归档结构。
- 旧 state 中 benchmark 字段保持兼容；apprentice 相关字段迁移为 study 记录时需明确唯一写入者、默认值与是否需要 schema bump。首次迁移必须先展示影响并获得用户确认，不能自动移动目录或修改 state。
- `dual` 模式由系统按数据和用户印象推荐一个深拆样本，用户确认选择后才进入 practice 闭环。
- 旧 `--visual` 及“拆包装 / 拆视频动效”请求由根路由直接交给 video-production-workflow；oracle-study 不再保留视觉逆向分析。

## 已确认交互决策

- 用户调用根 `/oracle-bone` 且需求足够明确时，直接执行所选 leaf skill，而不是只返回命令建议。
- 根路由不明确时，只提出一个会改变路由的澄清问题。
- 旧用户内容项目中的 `edits/` 等历史工件不由本次 skill 仓库重构删除；本次只删除 oracle-bone 包内对 edit-plan 的能力声明、模板和引用。

## 验收与测试 seam

1. 文档与静态测试 seam：skill 清单、路由表、目录 schema、context 读取清单和预算测试一致，删除的 skill 无残留可执行路由。
2. 路由行为 seam：代表性自然语言请求分别路由到 study、cover、VPW 边界或既有 leaf skill；不确定请求只提出一个关键澄清。
3. 工件契约 seam：study 和 cover 的模式说明、输出位置、引用关系及版权/证据约束可被静态行为用例验证。

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| 合并后单个 skill 超出上下文预算 | 入口保持轻量，模式细节按需读取协议；不直接拼接旧文件 |
| 删除 edit-plan 造成 VPW 交接断裂 | 明确以确认终稿为边界；移除 oracle 的旧交接包，不改 VPW 自己的项目契约 |
| study 将统计关联误报为可复刻机制 | 保留 benchmark 与 practice 两条证据链、知识卡片三重验证门 |
| 路由器变成默认长链编排 | 强制单任务、最轻模式、缺信息只问一题与流程不变量 |
