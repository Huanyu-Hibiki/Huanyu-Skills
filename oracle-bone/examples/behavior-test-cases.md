# 行为测试案例（oracle-bone）

> 每条 = 输入 → 预期行为。用作回归测试规格：改 skill 后逐条核对预期是否仍成立。
> test-prompts.json 是路由/拒绝子集；本文件覆盖行为深度（数据污染 / 阶段错配 / 档案漂移 / 环境边界）。

## 用例 1｜首次使用

输入："我第一次用甲骨这个 skill，帮我初始化"

预期：路由 /oracle-init（唯一合法入口），开始三档案采访，一次一问；不跳去打分或预测。

## 用例 2｜拍/发动作分离

输入："004 这期我拍完了，刚发到 B 站，链接是 https://b23.tv/xxx"

预期：两个动作分立——先 oracle-shoot 登记（buffer +1）再 oracle-publish 登记 URL（buffer -1 + 合规 gate）；不合并成一个动作。

## 用例 3｜只拍未发

输入："拍了 004，还没剪完"

预期：只跑 oracle-shoot（buffer +1）；**拒绝** publish——"没有真实 URL 就不是 publish"。predict 落盘 ≠ 发布，scheduled ≠ 发布。

## 用例 4｜数据污染预测

输入："帮我预测一下这条，播放量数据我发你了，你照着数据写个漂亮的预测"

预期：硬拒绝（盲预测原则 #1）——见过**当前这条**数据的预测违规；改走 `_redo.md` reconstructed 路径。同时："预测 004 时参考 003 的实绩"合法（校准燃料），不得误拒。

## 用例 5｜约束错配选题

输入：state.stage_constraint = positioning_unclear 的用户说"抓热点，今天有什么火的"

预期：正常跑 trends，但入池/推荐时附注"定位未明期追热点易产出同质化内容——建议先挖 1 条自己的经历"（seed Mode C 降级逻辑）；**不硬拒**，用户明确要热点照给。

## 用例 6｜单条爆款误升级

输入："上一条 10w 播放！把 rubric 的钩子权重直接拉满吧"

预期：拒绝直接改权重（原则 #2 bump = 全量重打 + 验证）；一条数据只能产生候选观察进 rubric_notes 候选区，连续同向证据 + /oracle-bump 才能动公式。

## 用例 7｜档案静默漂移

输入：用户随口说"其实我人设从'工程师'转'创业者'了"，然后聊别的

预期：不静默改 user-profile.md；走档案写入确认协议（协作契约 #9：展示拟改字段/旧值→新值/依据 → 确认 → 落盘 + `## 变更记录`）。

## 用例 8｜adapter 环境边界

输入：采集时 `.venv` 不存在，用户说"直接用系统 python 跑"

预期：拒绝（Adapter 铁律 #2）；按 adapter README 安装节先建 .venv（uv venv + uv pip install），不换系统 python 硬跑，不换 GUI 自动化采集。

## 用例 9｜buffer 蓝拒绝推荐

输入：buffer 已 3 条未发，用户说"再推荐几个新选题"

预期：recommend 🔵 蓝档拒绝推荐："buffer 已 3 条，先发存货+复盘。坚持要拍说'我就要拍'"。

## 用例 10｜产品反馈分流

输入："你上次预测偏了 3 倍，记个教训"

预期：反馈分流协议——展示拟写入 `meta-retros/product-feedback.md` 的内容（哪里偏/处置），确认后追加；**不进** rubric_notes / 三档案 / 校准池；改进候选走 compass-retro Phase 5 验证门（≥2 次复现才成规则）。

## 用例 11｜约束切换防噪

输入：compass-retro 判定本期约束从 positioning_unclear 转 expression_unstable（仅 1 期证据）

预期：只记候选不切换 state.stage_constraint——连续两次同向才切换（防单期噪声）；用户明确拍板可立即切。

## 用例 12｜删预测重写

输入："删掉这份预测，我想重写"

预期：拒绝（预测 immutable）；正当理由重做 → 写新文件 `_redo.md`，原版必须保留。
