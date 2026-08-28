# severity 复核与定级指南（severity-guide）

> **用途**：`sm-security` 子 skill LLM 复核环节的操作手册——拿到 scanner findings 后如何逐条判定、如何表述、如何定级与收敛。
> **地位**：severity 四级定义与判据以 `shared-references/security-taxonomy.md` §4 为**单一事实源**，本文只讲"如何把判据用到具体 finding 上"，不另立标准。规则模式写法见 `references/security/pattern-examples.md`。
> **思想来源**：NVIDIA SkillSpector（Apache-2.0）的两阶段分析思想（静态高召回 → LLM 提精度）与 baseline 抑制思想，只吸收思想，无代码拷贝。

## 1. 复核流程（每条 finding 四步）

1. **读 finding**：记下 `rule_id`、`severity`、`file`、`line`、`evidence`。
2. **读 false_positive_note**：在 RULES 表（scanner.py）查该 rule_id 的误报说明——它是规则作者预判的误报场景，先对照再判断。
3. **打开命中文件看上下文**：定位到 `line`，读前后各约 10 行；判断 evidence 处于什么语境（功能代码 / 示例代码块 / 注释说明 / 文档叙述）。
4. **下判定**：三选一——确认 / 疑似误报 / 需降级（模板见 §2）；任何情况下**不许静默吞掉** finding。

## 2. 三种判定与表述模板

| 判定 | 适用 | 报告表述模板 |
|---|---|---|
| 确认 | 上下文无法给出良性解释，证据链完整 | `【确认】{rule_id}（{severity}）@ {file}:{line}——{explanation}。上下文检查：{一句话说明为何不构成良性场景}。` |
| 疑似误报 | 命中内容有明确良性语境，但**不能 100% 排除风险** | `【疑似误报】{rule_id}（{severity}）@ {file}:{line}——命中 "{evidence}"，但上下文显示{良性语境说明}。保留列出，建议人工抽查。` |
| 需降级 | 风险真实存在但达不到原 severity | `【降级：{原级别}→{新级别}】{rule_id} @ {file}:{line}——{降级理由，指向缺失的证据环节}。` |

规则：疑似误报与降级**都必须出现在报告中**（带标注），不得从 findings 列表移除；只有"确认"计入风险分全额权重，降级后按新级别计分。

## 3. 判定依据示例（典型场景）

1. **教学类 skill 的注入样例**：INJ-003 命中 `never refuse`，但位于 markdown 示例代码块内，上下文是"以下为恶意样本特征演示"→ **疑似误报**（保留列出）。
2. **备份类 skill 枚举 .ssh**：EXFIL-005 命中 `~/.ssh`，SKILL.md 声明"备份工具，范围含 SSH 密钥（用户勾选）"，代码只读不传网 → **疑似误报**。
3. **curl GET 公开 API 无凭据**：EXFIL 类规则命中，细看为 `curl https://api.github.com/repos/x`——GET 请求、无 `-d`、无凭据变量 → **需降级**，说明"无数据外发行为"。
4. **注释中的 rm -rf**：DEST-001 命中 `rm -rf /`，位于 shell 注释 `# 千万别 rm -rf /` → **疑似误报**；但同一文件后续若有真实执行行，升级回确认。

## 4. severity 边界案例

**critical → high（证据链不完整）**：critical 的标准是"证据链完整指向凭据出网或不可逆破坏"（taxonomy §4）。EXFIL-002 命中"读凭据文件 + 网络请求同文件共现"，但请求指向 skill 自身声明的 API、且凭据变量未出现在请求参数里 → 证据链断在"凭据是否真的出网"，降 high 并在报告中写明断点。

**medium → high（多条共现指向同一意图）**：单条 medium（如 EXFIL-005 枚举 .ssh）不足以定罪；但同一 skill 内 EXFIL-005 + EXFIL-004（全量枚举环境变量）+ EXFIL-003（可疑端点外传）共现、且服务于同一数据流 → 整体升级为 high，报告中合并陈述为一个"聚合发现"并注明各原始 id。

**不升级到 critical 原则**：复核可以降级或聚合上调，但**不得把单条 finding 上调为 critical**——critical 意味着直接判 DO NOT INSTALL（taxonomy §4 评分约定：任一 critical 命中即 DO NOT INSTALL），必须由完整证据链支撑；证据链是否完整以 scanner 原始命中为准，不靠推测补链。

## 5. 报告纪律

1. **不承诺 100% 检出**：报告结尾固定附注"本结论仅基于规则扫描 + LLM 复核，不构成完整安全审计"。
2. **兜底声明**：原文引用 taxonomy §6——"供应链依赖、输出处理、记忆污染、数据流污点、YARA 特征五个维度未被规则覆盖"。五个维度一个不能少。
3. **疑似误报也要列出**：带【疑似误报】/【降级】标注完整列出并说明语境依据；静默吞掉 = 复核失职。
4. **分数、标签、建议三者一致**：0-100 分、severity 标签、建议（SAFE / CAUTION / DO NOT INSTALL）严格按 taxonomy §4 评分约定换算（critical +50 / high +25 / medium +10 / low +5，可执行脚本 ×1.3，上限 100）；复核降级后按新级别重算，任一 critical 确认存在时建议一栏如实反映复核后的结论。

## 6. v2 展望：baseline 抑制

吸收 SkillSpector 的 baseline / suppression 思想：v1 每次复核都要重新解释相同的疑似误报；v2 可引入 baseline 文件——已人工确认的误报按"规则 id + 文件 + 证据指纹"登记并写明理由，后续扫描自动标注"已确认误报（baseline）"不再重复报告，但保留在报告附录供审计；源文件变更后指纹失效，finding 自动回到待复核状态。
