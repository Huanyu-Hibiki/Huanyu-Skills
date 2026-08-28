# 落盘前结构自检清单

> 来源：检查点思想吸收自 Matt Pocock 的 [write-a-skill](https://github.com/mattpocock/skills/tree/main/skills/productivity/write-a-skill)（MIT 许可）的 review checklist 与其 `skill_structure_validator.py` 的机器检查项，判据已与本项目对齐后重写。
> 用途：sm-writer 起草后、落盘前逐项勾选。各条判据的"为什么"与细节**不在本文展开**，统一见 [skill-anatomy.md](../../shared-references/skill-anatomy.md)（下文 §x 均指该文档；其 §3 健康判据与 `scripts/inventory.py` 一一对应）。三阶段流程见 [workflow.md](workflow.md)。

用法：从 A 到 E 逐节勾选。任何一项不过 → 修复后重查，不带病落盘。

## A. frontmatter

- [ ] `name` 与目录名完全一致（§3.4）
- [ ] `description` ≤1024 字符（§3.3）
- [ ] `description` 含触发词，句式为"做什么 + Use when 何时用"（§5.1）
- [ ] `allowed-tools` 按需：用不到就不写；写了只列实际用到的工具（§2）

## B. 结构

- [ ] SKILL.md ≤200 行（§4.1）
- [ ] `references/` 只有一层，无嵌套子目录（§1）
- [ ] 无循环引用——任何文件不指回引用它的文件（§4.3）
- [ ] 无预建空目录：没有脚本就没有 `scripts/`，没有深度细节就没有 `references/`（§1）

## C. 内容

- [ ] 工作流步骤化：编号步骤 + 勾选框，一步一句话（§6.1）
- [ ] 危险操作（写 / 删 / 改）有确认门槛：先展示将做什么，确认后执行（§6.2）
- [ ] 触发词是用户原话而非生造术语，且避开与其他 skill 相撞的通用词（§5.2）
- [ ] SKILL.md 内至少有一个最小可用示例，不把最常用信息推到 references/（§4.3）

## D. 脚本（仅当创建了 scripts/；没有则本节整体跳过）

- [ ] stdout 只输出机器可读结果，人话解读交给 LLM（§1）
- [ ] 失败时退出码非 0，错误信息走 stderr
- [ ] 只依赖标准库；同样输入必产出同样输出（可复现，§6.2）

## E. 交付

- [ ] 以上全部勾完，才进入 workflow.md §3 的用户复核——自检在前，复核在后
