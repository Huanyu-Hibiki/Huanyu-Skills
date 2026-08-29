# VALIDATION — 2026-08-29 优化轮（darwin / ip-coach 对照借鉴）

## 改动范围（commit fb93dff…951b04d）

- 阶段诊断接线到 mode detection（SKILL.md）：四阶段 × 优先动作 × 暂不做清单 + "阶段 = 当前最大约束"心法 + 诊断输出三元组（暂定阶段/依据/升级条件）
- 字段归属表（strategy-immutability.md）：7 类字段唯一主档 + 三条引用纪律（事前防矛盾）
- 档案写入确认协议（strategy-immutability.md）：interview-profile 等事实档案改字段 = 展示→确认→落盘→变更记录
- PRODUCT-FEEDBACK 反馈分流（SKILL.md 路由表）：对 skill 的评价与战略事实分离
- ip-strategy Phase 4.5 正向资产盘点：~30% 有据正向配额（上下限）+ 决策段第 8 节 + 首屏 8 件事
- 行为测试用例 12 条（examples/behavior-test-cases.md）+ test-prompts.json 扩至 6 条

## 校验结果

- 相对链接：19 个 md / 52 条链接 / **断链 0**
- 引用一致性：strategy-immutability 字段归属表新增"当前阶段"行 ↔ SKILL.md 阶段诊断段 ↔ status 看板，三处互指一致
- 模板一致性：ip-strategy 首屏"8 件事" ↔ 落盘前 CHECKPOINT"8 项" ↔ 决策段第 8 节，编号对齐
- 体积：SKILL.md 增量 25 行（<150% 上限）

## 未覆盖（诚实声明）

- 行为用例 1-12 未跑子 agent 实测（full_test），仅静态规格化——下轮 darwin dim8 验证时执行
- dontbesilent 外部库未核验（原库不在仓库内，README 已声明）
