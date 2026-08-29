# VALIDATION — 2026-08-29 优化轮（darwin / ip-coach 对照借鉴）

## 改动范围（commit 45de524…）

- stage_constraint 约束机制（SKILL.md）：四类约束判定表（positioning_unclear / expression_unstable / capacity_limited / conversion_blocked / none）+ 纪律（依据+升级条件 / 宁可低估 / 连续两次同向才切换）
- 四子 skill 接线：oracle-init Phase 4.5 初判（随 Phase 4 收口确认）+ Phase 5 state 写入；oracle-seed Phase 1.6 选题约束检查；oracle-compass-retro Phase 3 约束回写（🔴 CHECKPOINT + 防噪）；oracle-recommend Phase 2.6 约束提示
- 反馈分流协议（SKILL.md 路由表）：product-feedback 与创作者数据/校准池分离
- 协作契约 #9 档案写入确认：三档案改字段 = 展示→确认→落盘→`## 变更记录`
- 行为测试用例 12 条（examples/behavior-test-cases.md）+ test-prompts.json 扩至 6 条
- 存量断链修复 3 处：adapters/HOWTO.md 的 `../../` 层级错；migration-protocol.md 两处示例占位被写成真实链接

## 校验结果

- 相对链接：126 个 md / 80 条链接 / **断链 0**（修复前 3）
- stage_constraint 接线一致性：主 SKILL.md 判定表 ↔ init 初判 ↔ seed 检查 ↔ compass 回写 ↔ recommend 提示，五处引用同一张表（单一来源）
- state 兼容性：stage_constraint 为新增 optional 字段，无 schema_version bump；旧 state 缺字段时按 `none` 兜底（seed Phase 1.6 / recommend Phase 2.6 均已注明）
- 体积：主 SKILL.md 增量 22 行，四子 skill 共 31 行（均 <150% 上限）

## 未覆盖（诚实声明）

- 行为用例 1-12 未跑子 agent 实测（full_test），仅静态规格化——下轮 darwin dim8 验证时执行
- state-management.md 的 schema 文档未同步 stage_constraint 字段说明（字段 optional、消费方已兜底，留待下次 bump 时正式入 schema）
