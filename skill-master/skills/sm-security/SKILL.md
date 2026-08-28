---
name: sm-security
description: 静态安全扫描一个 skill 目录：规则引擎打 0-100 风险分，逐条复核 critical/high 发现并降误报，产出 SAFE/CAUTION/DO NOT INSTALL 安装建议。用于安装第三方 skill 前的安全审查。Use when 用户提到"检查这个skill安全吗"、"扫描skill"、"有没有后门"、"skill安全"、"skill恶意"时使用。
---

# sm-security — skill 安全扫描与深度复核

对指定 skill 跑 `scripts/scanner.py` 规则引擎（25 条规则，五大类：
提示注入 / 数据外泄 / 破坏命令 / 混淆隐藏 / 过度权限），再由 LLM
逐条复核 findings、降误报，产出分级报告与安装建议。

遵循三原则（shared-references/skill-anatomy.md §6.2）：

- **脚本做确定性事**——规则匹配与打分交给 scanner.py，不自行重写正则
- **LLM 做判断事**——误报复核、降级定级、安装建议是语义判断
- **危险操作必须确认**——只扫描不删除，处置决定权在用户（见"边界"）

以下路径均相对 skill-master 仓库根（本 skill 目录向上两级即仓库根）。

## 工作流

1. [ ] **定位目标**：要扫的是本地 skill 目录（推荐）或单个文件路径。
   - 用户没给路径就**问**，不猜、不默认扫某个目录
   - 只接受本地路径；远程仓库 / URL 需用户先下载到本地再扫

2. [ ] **运行 scanner.py**（PowerShell，从仓库根执行）：

   ```powershell
   python scripts/scanner.py <目标路径> --json
   ```

   - 目标文件数很多时可追加 `--max-files N` 调整枚举上限（默认 500）
   - 成功时 stdout 恒为单一 JSON：`{"score": 0-100, "findings":
     [{rule_id, severity, file, line, evidence, explanation}],
     "truncated": bool}`
   - 退出码非 0 → 按"错误处理"小节办
   - `"truncated": true` 时，后续报告必须注明**"结果可能不完整"**
     （超出上限的文件未被扫描）

3. [ ] **LLM 复核**（critical/high 逐条必做；操作手册
   `references/security/severity-guide.md` §1 四步）：
   1. 读 finding：记下 rule_id / severity / file / line / evidence
   2. 读 false_positive_note：在 `scripts/scanner.py` 的 RULES 表按
      rule_id 查误报说明（与 taxonomy §2 各规则行同源）
   3. 看上下文：打开命中文件定位到 line，读前后约 10 行，判断语境
      ——功能代码 / 示例代码块 / 注释说明 / 文档叙述
   4. 下判定：**确认 / 疑似误报 / 需降级** 三选一，表述用
      severity-guide §2 的模板；**任何情况下不静默吞掉 finding**
   - medium/low 抽查即可（与已确认发现同文件的优先抽）
   - 复核纪律（severity-guide §4）：不上调到 critical；降级后按新
     级别重算分数；多条 medium 共现指向同一意图可聚合上调、合并陈述

4. [ ] **分级报告**：
   - **风险分**：0-100。scanner 原始分 + 复核降级后的重算分，换算按
     taxonomy §4（critical +50 / high +25 / medium +10 / low +5，
     含可执行脚本 ×1.3，上限 100）
   - **severity 分布**：critical / high / medium / low 各几条（按
     复核后级别统计，降级条目标注原始级别）
   - **findings 列表**：逐条列出——判定标注（【确认】/【疑似误报】/
     【降级：x→y】）+ rule_id + severity + file:line + evidence +
     explanation；**疑似误报与降级带标注保留列出，不得移除**
   - **建议**：SAFE / CAUTION / DO NOT INSTALL。硬规则（taxonomy
     §4）：任一 critical **确认**即 DO NOT INSTALL，无论总分多少；
     critical 判疑似误报时不自动放行——保留标注并建议人工抽查后
     决定。其余按复核后分数与确认发现的最高 severity 综合判断：
     无确认发现或仅 low → SAFE；存在确认 high 或多条确认 medium →
     CAUTION；介于其间的，写明判断理由

5. [ ] **兜底声明**（报告结尾固定附注，一字不落）：

   > 本结论仅基于规则扫描 + LLM 复核，不构成完整安全审计。
   > 供应链依赖、输出处理、记忆污染、数据流污点、YARA 特征五个
   > 维度未被规则覆盖（taxonomy §6）。

## 错误处理

- **目标不存在 / 参数非法**：scanner 退出码非 0，stdout 为
  `{"error": "..."}`——向用户**原样展示** error JSON 并**停止**：
  不重试、不猜测、不绕过脚本自行扫描。最常见成因是路径打错，向
  用户确认正确路径后重跑一次即可
- **truncated: true 的含义**：目标文件数超过 `--max-files` 上限
  （默认 500），排序靠后的文件**未被扫描**——不是"扫了但没发现"。
  报告注明"结果可能不完整"，建议用户提高 N 后重扫；另单文件超过
  50MB 时该文件跳过内容扫描，同样计入不完整因素

## 边界

- **只扫描，不删除**：发现恶意 skill 时的产出是证据与处置建议
  （不安装 / 卸载 / 隔离 / 上报来源），**不代删、不修改目标文件**
  ——删除属危险操作，决定权与执行权都在用户（三原则第 3 条）
- **与 sm-analyzer 分工**：sm-analyzer 做结构与质量分析并出 HTML
  报告（内含风险章节）；本 skill 是独立深度安全审查——规则引擎
  全量扫描 + 逐条复核 + 安装结论。装第三方 skill 前拿不准安全
  与否 → 本 skill；要完整拆解一个 skill 的结构与质量 → sm-analyzer
