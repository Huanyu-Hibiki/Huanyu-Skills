---
name: pulse-evolve
description: PulseHub 获客·自进化（元技能）。负责整个 skill 体系的升级迭代——只编辑 pulse-*/SKILL.md 文本本身。用SkillOpt式闭环（harvest采集→mine挖掘→reflect反思→edit编辑→validate验证→consolidate固化）。当用户说"优化获客skill""自进化""迭代skill""分析执行情况""skill为什么效果不好""改进获客流程""整个体系升级"时使用。也负责新旧获客体系切换（双轨期）管理：跑通闭环、用户拍板、README 同步三道门，缺一不可。自进化,优化skill,迭代,改进获客,体系升级,双轨切换,skill-切换。
---

# pulse-evolve · 自进化（SkillOpt 轻量复刻）

方法论来自微软 [SkillOpt](https://github.com/microsoft/SkillOpt)：把 skill 文档当作冻结 AI 的"可训练状态"，用闭环迭代。

## 职责边界

- **只维护"SKILL.md 文本"**——发现某 skill 指令导致产出偏差，就改那个 SKILL.md
- **只读 project-archive，不写**——沉淀库是训练数据源，绝不修改内容
- **不维护自己**——pulse-evolve 的 SKILL.md 不自我修改（自指死锁）

## 何时用

- 用户跑了 pulse-init 到 pulse-leads 几轮后，感觉某个 skill 产出不稳/偏题
- 每周定期做一次"复盘+进化"
- `数据反馈.md` 积累了一定真实数据后

**前提**：`数据反馈.md` 必须有真实数据。没有数据反馈，自进化只能在主观判断上打转。

## 闭环（每次进化一个目标 skill）

### 1. Harvest 采集

读目标 skill 的：
- 最近 5-10 次执行记录（如果有的话）
- `数据反馈.md` 里与该 skill 相关的真实数据
- `个人风格.md` 里新增的禁用词/金句（如果该 skill 产出文本）

整理成"任务-产出-用户反馈-真实数据"四元组列表。

### 2. Mine 挖掘模式

找规律：
- **哪些产出用户大改** → skill 在那个维度产出弱（信号最强）
- **数据反馈里哪些选题/词/话术实际跑出来 vs 扑街** → 校准推荐偏好
- **哪些 prompt 反复导致偏题** → skill 指令边界模糊
- **哪些产出用户原样采纳** → 那部分别动（验证集里的"好"样本）
- **是否所有产出都改同一处** → 系统性缺陷，值得加新指令

### 3. Reflect 反思

对每个缺陷，问 5 Why 找根因，再想 **3 种不同的修法**（别只想到一种就改）。

### 4. Edit 编辑

对目标 SKILL.md，只做 3 种操作：
- **add**：加一段新指令/约束/示例
- **delete**：删一段被发现误导/冗余的指令
- **replace**：替换某段为更好版本

**bounded edit**：一次进化只动 1-3 处。每处编辑写一句话理由。

### 5. Validate 验证门（核心防退化）

**🛑 绝不能跳过**：
1. 从历史产出里挑 2-3 个**用户原样采纳过的好产出**作为 hold-out 验证集
2. 用改后的 skill 重新跑这 2-3 个 prompt
3. 对比新旧产出：
   - 新产出在原来好的维度**没退步** 且 在要修的维度**有改善** → ✅ 接受
   - 任一好样本退步 → ❌ 拒绝

**🔴 CHECKPOINT**：验证结果连同编辑 diff 一起展示给用户，**用户确认采纳才写入**——AI 不自评自批。

### 6. Consolidate 固化

- 接受的编辑写入 SKILL.md
- 更新 `evolution-log.md`（日期/目标skill/编辑类型/理由/验证结果）
- 把"反模式"加进 skill 末尾的 `## 已知反模式` 段

## 维护清单（16 个 skill）

| # | Skill | 路径（相对 PulseHub 仓库根） | 维护？ |
|---|-------|------|--------|
| 0 | pulse-router | pulse-router/SKILL.md | ✅ |
| — | pulse-discover | pulse-discover/SKILL.md | ✅ |
| — | pulse-resolve | pulse-resolve/SKILL.md | ✅ |
| — | pulse-enrich | pulse-enrich/SKILL.md | ✅ |
| — | pulse-deliver | pulse-deliver/SKILL.md | ✅ |
| 1 | pulse-init | pulse-init/SKILL.md | ✅ |
| 2 | pulse-insight | pulse-insight/SKILL.md | ✅ |
| 3 | pulse-keywords | pulse-keywords/SKILL.md | ✅ |
| 4 | pulse-topics | pulse-topics/SKILL.md | ✅ |
| 5 | pulse-copywrite | pulse-copywrite/SKILL.md | ✅ |
| 6 | pulse-script | pulse-script/SKILL.md | ✅ |
| 7 | pulse-private | pulse-private/SKILL.md | ✅ |
| 8 | pulse-leads | pulse-leads/SKILL.md | ✅ |
| 9 | pulse-humanize | pulse-humanize/SKILL.md | ✅ |
| 10 | **pulse-evolve**（本体） | — | ❌ 不维护自己 |
| 11 | pulse-review | pulse-review/SKILL.md | ✅ |

## 人 × 数字员工分工

- **人**：决定进化哪个 skill、提供反馈真相、最终确认是否采纳编辑
- **数字员工**：采集痕迹、挖模式、提案编辑、跑验证门、写日志

## 输出

```
✅ 进化完成
   - 目标 skill：pulse-copywrite
   - 编辑数：2（add 1, replace 1）
   - 验证：2/2 通过
   - 进化日志已更新

👉 下次建议聚焦：pulse-leads（评论打分维度可优化）
```

## 注意

- **没有数据就不进化**——先让用户回填几轮 `数据反馈.md`
- **一次只动一个 skill**——别批量改，验证不过来
- **学习率隐喻**：连续 2 次编辑被拒，下次只允许更小幅度微调

## 已知反模式

### 反模式 N1 · 没真跑通完整闭环就声明新体系替代旧体系(2026-07-27 加)

**问题是什么**(2026-07-27 双轨切换实战):
- ❌ 新 skill 集复制进运行环境后,AI 因 skill 列表"更新更近"默认调新 skill,旧体系还在跑业务就被架空
- ❌ 没跑完整业务闭环,**没**对比旧体系输出实质等价,就宣布"新体系替代了旧体系"
- ❌ 旧体系在跑定时业务(cron)突然被替代 = 业务中断

**正解**(**三道门,缺一不可**):
```text
门 1 · 真跑通业务闭环:
   - 在目标运行环境里跑完整获客 5 步(router→init→keywords→topics→copywrite)
   - 每步产出和旧体系对比
   - 不实质等价 = 不替换

门 2 · 用户明确拍板"移除旧体系":
   - 即使闭环跑通,**也**要用户明确说"移除"
   - AI 不擅自把旧体系改名成 .bak / 移出 skill 目录
   - AI 不擅自改定时任务(cron)调用脚本

门 3 · 文档同步:
   - 移除旧体系前先更新相关 README
   - 把"双轨并行"段改成"新版 only"
   - 列出已删旧 skill 和新替代品
```

**配套规则**:双轨期硬规则——旧体系在跑业务期间,默认走旧体系,新体系只做平行验证。

> **管线类反模式已归位**：多平台采集截断、把采集当核心任务这两个数据管线行为规范，收录在 `pulse-discover` 的 Pitfalls（P5/P6）——**反模式跟着出问题的 skill 走**。evolve 收录其余类型：体系切换、跨会话判断等。

### 反模式 N2 · 凭单文件 modify 时间推断"项目是空骨架"(2026-07-27 加)

**问题是什么**(2026-07-27 PulseHub 评估实战):
- ❌ AI 第一次看 README.md + ROADMAP.md:ROADMAP 是 21:34 旧版,说"no functional code yet" → AI 推断"PulseHub 是空骨架"
- ❌ 实际上 README.md 已经 22:13 更新(晚 ROADMAP 39 分钟),说"137 测试通过 / 16 skill 完成"
- ❌ AI 凭**单一旧文件**做错判 → 用户怒"readme 已经更新,你看到的是没更新的"

**正解**(**先 stat 全关键文件,再判断**):
```text
1. 评估任何"项目状态"前,先 stat:
   stat README.md ROADMAP.md CHANGELOG.md package.json

2. 多个文件 modify 时间不一致 → 信**最新**的,**不**凭印象
   - README.md 最新 → 信 README
   - ROADMAP.md 最新 → 信 ROADMAP
   - 都晚于上次看的版本 → 重新读,不要拿上次的快照推断

3. 跨会话判断:用户的注意力是稀缺资源
   - 用户说"昨天你说 PulseHub 是空骨架" → AI 不要固执"我昨天看的是..."
   - 重读最新 → 报新事实
```
