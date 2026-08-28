---
name: sm-writer
description: 从零编写新 skill，一次一问访谈需求，按三阶段流程起草、自检，用户确认后落盘成新目录。Use when 用户提到"帮我写个skill"、"新做一个skill"、"写个技能"、"做个skill"、"创建skill"时使用。
---

# sm-writer — skill 编写（④）

把用户的模糊想法变成一个可触发的新 skill 目录。本文件只编排三阶段
流程，细节全部下沉到仓库内手册（渐进式披露，skill-anatomy §4；
路径以 skill-master 仓库根为基准——本 skill 目录向上两级即仓库根）：

- 三阶段流程与访谈技巧：[references/writing/workflow.md](../../references/writing/workflow.md)
- 落盘前 A-E 逐项自检：[references/writing/structure-checklist.md](../../references/writing/structure-checklist.md)
- 结构规范与 description 公式：[shared-references/skill-anatomy.md](../../shared-references/skill-anatomy.md)

## 工作流

### 阶段一：需求收集（workflow.md §1）

1. [ ] **必问四项，一次一问，问全才动笔**——每项等用户回答后再问下一
   项，能出选择题就出选择题（问法示例见 workflow.md §1）：
   - 覆盖什么**任务域**？管什么、不管什么
   - 有哪些具体**使用场景**？80% 场景是哪个——它决定最小工作流
   - **要不要脚本**？有没有确定性操作（校验 / 枚举 / 渲染 / 统计）
   - **要不要参考资料**？有没有 SKILL.md 装不下的深度细节
2. [ ] **识别"解法式描述"**：用户说的常是解法而非需求（"我要一个能
   定时扫描的 skill"）。听到就追问一句"这想解决什么问题？"，确认
   真问题后再决定解法是否成立

### 阶段二：起草（workflow.md §2）

3. [ ] **frontmatter**：name 与目录名一致；description 按 anatomy §5
   公式——第一句做什么（动词 + 具体对象，不用形容词），第二句
   `Use when` + 触发词（用户原话，避开与其他 skill 相撞的通用词，
   anatomy §5.2）。例：`提取 PDF 文本与表格、填写表单。Use when
   用户提到 PDF、表格提取。`
4. [ ] **最小工作流**：只装 80% 场景的步骤清单——编号 + 勾选框，一步
   只说"做什么"，"怎么做"下沉（anatomy §6.1）
5. [ ] **边界与危险操作门槛**：写明不做什么（防误触发）；写 / 删 / 改
   类操作先展示将做什么、确认后执行（anatomy §6.2）
6. [ ] **按需建子目录**：SKILL.md 超 200 行才拆 references/（原地留
   1-2 行指针，下沉规则 anatomy §4.2）；有确定性操作才建 scripts/；
   两者皆无则都不建，不预建空目录（anatomy §1）

### 阶段三：复核与落盘（workflow.md §3）

7. [ ] **先自检再交用户**：对照 structure-checklist.md A-E 逐项过完，
   有问题先修复——不把"description 缺触发词"这类低级问题留给用户
   发现
8. [ ] **呈现草案要点，不贴全文**：name、description、工作流步骤概览、
   建了哪些子目录及为什么——全文是给 Agent 读的，用户要的是决策点
9. [ ] **问三件事**：这些使用场景都覆盖了吗？有缺漏或含糊的地方吗？
   哪部分该更详细、哪部分该更简略？
10. [ ] **确认后才落盘**：展示目标路径与将创建的文件清单，用户点头
    才写文件；用户要改就回到阶段二迭代

## 硬约束

- **一次一问**：全程任何提问一次只问一个，选择题优先——一次抛五个
  问题，等于一个问题都没问清
- **确认前禁止写文件**：落盘是危险操作（anatomy §6.2）；未经用户明确
  确认，不创建、不覆盖任何文件
- **落盘后建议验证触发**：请用户用 3 条正例 + 1 条负例的测试话术走查
  新 skill 触发是否准确，测试集构造方法见
  [references/optimizing/eval-notes.md](../../references/optimizing/eval-notes.md) §一

## 边界

- **优化已有 skill 归 sm-optimizer**：用户说"优化 / 改"某个已存在的
  skill 时不接手，交回路由层——本 skill 只管从零新建（"帮我写 / 新做
  一个"）
- **写完不自动进优化**：落盘并验证触发后流程即结束；用户明确要求时
  才转 sm-optimizer，不擅自续跑
