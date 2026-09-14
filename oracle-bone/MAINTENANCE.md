# MAINTENANCE — oracle-bone 维护规则

面向维护者的工程纪律：上下文预算、跨文件同步规则、发布前检查。行为协议本身住在
[shared-references/](shared-references/) 与各子 skill，本文只约束"改的时候怎么改不坏"。

---

## 1. 上下文预算（棘轮）

oracle-bone 是 28 子 skill + 13 协议的大家族，上下文是稀缺资源：入口越肥，注意力和
token 双输。以下数字由 [tests/test_context_budget.py](tests/test_context_budget.py) 机械执行：

| 对象 | 预算（bytes） | 基线说明 |
|---|---|---|
| 主 `SKILL.md` | ≤ 31,000 | 2026-09-07 现状 ≈ 30,057 |
| 每个子 skill `SKILL.md` | ≤ 18,000 | 当前最大 oracle-init ≈ 17,455 |
| 每份 shared-references 协议 | ≤ 15,000 | 当前最大 state-management ≈ 13,743 |
| 单任务运行时读取（主 SKILL + 1 子 skill + ≤2 份协议） | ≤ 78,000 | 最坏组合实测 ≈ 73.7K |
| `tools/context.py` 摘要输出 | ≤ 6,000 | 脚本内置截断保护 |

**棘轮语义**：预算只许收紧、不许放松。破预算的改动要么同 PR 给出等量瘦身，
要么在本文档记录放松理由与日期（并在 CHANGELOG 标注）。优化方向是逐步下调数字，
不是贴着上限长。

**配套纪律**：

- 主 SKILL.md 是路由器不是仓库——新内容优先沉到对应子 skill 或协议里
- 子 skill 之间不得互设"必读前置"；跨 skill 共享的判断逻辑下沉 shared-references
- 每次任务只读当前流程真正需要的文件（各子 skill 的 Inputs/Workflow 已声明，照声明读）

---

## 2. 任务摘要出口（tools/context.py）

各子 skill 在 Phase 0/1 需要全局状态时，调 `python tools/context.py <项目根> --task <后缀>`
取 ≤6KB 的任务相关摘要，代替各自全量解读 state——保证所有 skill 拿到同一口径
（confidence 派生、buffer 口径、约束兜底均以此脚本实现为准）。

- **只读**：脚本绝不写 state；写操作仍归各子 skill（见 state-management.md 字段写入责任表）
- 退出码：0 正常 / 2 未初始化（路由 /oracle-init，不代建）/ 3 损坏（建议备份重建）
- state 缺字段时按协议兜底（如 stage_constraint 缺 → none），不崩、不猜
- schema 漂移时输出 ⚠ 并指向 /oracle-migrate，不阻塞只读任务

---

## 3. 跨文件同步规则

改一处时，同 PR 判断并更新下游，不许"下次再说"：

| 改了什么 | 必须同步检查 |
|---|---|
| shared-references 任何协议 | 所有引用它的子 skill（各 SKILL.md 链接 + Inputs 段）；行为语义变化同步 `examples/behavior-test-cases.md` 与 `test-prompts.json` 的 expected |
| state schema | 只能走 [migrations/registry.md](migrations/registry.md)（单一来源）：版本链 + `<old>-to-<new>.md` + oracle-init Phase 5 硬编码版本；新 optional 字段可不 bump，但要在 state-management.md 补字段说明与兜底值 |
| 主 SKILL.md 路由表（触发词/前置条件） | 对应子 skill frontmatter 的 description 触发词保持一致；新增子 skill 同步文件清单与 DESIGN.md §5 |
| rubric 体系 / starter-rubrics | 任何权重变更只能走 /oracle-bump 全量重打门（原则 #2），不能直接改 starter 了事 |
| 预算数字（本文 §1） | tests/test_context_budget.py 的 BUDGETS 常量同步改，测试必须绿 |
| tools/ 脚本 | 至少一个子 skill 消费（Inputs 表挂引用）——不做零引用工具；行为变化跑 tests/ 回归 |

原则：**单一事实源**。同一事实只在一处维护（见 state-management.md 信息主档速查表），
其他位置引用而不复制；发现两处矛盾时以主档为准修次档。

---

## 4. 发布前检查

```bash
python -m unittest discover -s tests -v      # 预算棘轮 + context.py 回归
python -m py_compile tools/context.py        # 语法
```

外加人工核对：

- [ ] 主 SKILL.md / 子 skill / 协议均在预算内（测试已盖，但看一眼警告输出）
- [ ] 相对链接无断链（改了文件名/路径时）
- [ ] schema 相关改动有 migration 记录或"optional 不 bump"说明
- [ ] CHANGELOG.md 已追加本次批次
- [ ] 行为语义变化时 behavior-test-cases / test-prompts.json 的 expected 已更新

---

## 5. 来源与致谢

本项目的「上下文预算棘轮」「任务摘要出口」「真源层↔运行层同步规则」三项工程纪律，
在**设计思想**上借鉴了 `template/ip-strategist`（耳总著，CC BY-NC 4.0）的仓库工程实践。

oracle-voice 的「个人词典 + 转写纠错规则」「文字轮润色纪律」（口误自纠 / 专名不猜 / 指令句当内容）
在**机制思想**上借鉴了 [OpenTypeless](https://github.com/tover0314-w/opentypeless)（MIT）的
本地词典、correction rules 与润色 prompt 设计。

第十六批的四处补强借鉴了四个参考项目：oracle-apprentice 的三重验证门 / 触发场景 / 反例结构化
借鉴 [cangjie-skill](https://github.com/kangarooking/cangjie-skill)（MIT）；oracle-recommend 的置信度地板
与诚实空池、oracle-trends 的 velocity 热度修正与四态信封借鉴
[last30days-skill](https://github.com/mvanhorn/last30days-skill)（MIT）与
[union-search-skill](https://github.com/runningZ1/union-search-skill)（README/代码头声明 MIT，仓库无 LICENSE 文件）；
交互预算三档借鉴 huashu-skills（**该仓库无 License**——仅借鉴机制思想，零文本复制，不引入其任何内容）。

oracle-edit-plan 的「剪辑计划工件 + 成片分层验收 + 审稿三轴」在**方法论原理**上参考了
OpenMontage（本地参考项目，**AGPLv3**）的剪辑决策与成片质检门设计——**仅学习原理，
未复制其任何代码或文本**（AGPL 传染性约束下必须如此），实现全部原创、oracle-bone 维持 MIT。

借鉴边界（clean-room 声明）：

- 只吸收**思想与规则形态**（预算棘轮、任务摘要、同步矩阵、词典纠错、润色纪律），**未复制其任何文本、代码或文档段落**
- 实现完全按 oracle-bone 自身架构（state 单一来源 / 子 skill Inputs 声明 / migrations 链 / voice-lexicon.md）原创重写
- oracle-bone 维持 **MIT** 许可不变，不引入 CC BY-NC 条款；各仓库代码互不混用
- 感谢原作者公开其工程实践——本文件即为署名致谢
