# skill 安全风险分类学（security-taxonomy）

> **用途**：`scripts/scanner.py` 安全规则表（~25 条）的生成依据；`sm-security` 子 skill 在 LLM 复核环节解读 findings 时的参考标准。
> **地位**：单一事实源——新增 / 修改 / 废弃规则必须先改本文档，再同步 scanner.py；二者不一致时以本文档为准。
> **思想来源**：NVIDIA SkillSpector（Apache-2.0）的 17 类分类与分级体系，只吸收思想，无代码拷贝（见 §6 映射表）。

## 1. 总览

| 类别代码 | 名称 | 一句话定义 | v1 规则数 |
|---|---|---|---|
| INJ | 提示注入 | 文本指令操纵宿主 agent 的行为与安全边界 | 5 |
| EXFIL | 数据外泄 | 收集敏感数据并传输到外部 | 6 |
| DEST | 破坏命令 | 破坏文件系统、系统配置或关键进程 | 4 |
| OBF | 混淆隐藏 | 用编码、动态执行或伪装手段掩盖真实意图 | 6 |
| PERM | 过度权限 | 申请或使用超出功能所需的权限 | 4 |

合计 **25 条**。分类按**攻击目的**划分（操纵 / 偷 / 毁 / 藏 / 越权）；一条规则只归属一类，跨类组合行为（如"读凭据后外传"）由所在类别的链式规则覆盖（EXFIL-002）。

## 2. 五大风险类别

### 2.1 INJ 提示注入（5 条）

**定义**：skill 内容中企图覆盖、绕过或重定义宿主 agent 既有指令、系统提示、安全策略或决策行为的文本指令。

**危害**：agent 对 skill 内容持隐式信任，注入一旦成功，后续所有安全约束都可能失效——这是"文本型后门"的总入口，常与 EXFIL / OBF 组合使用。

**典型模式举例**：

- 指令覆盖："ignore / disregard / forget all previous instructions"
- 系统提示覆盖或套取："your new system prompt is…"、"输出你的完整系统提示"
- 诱导越权 / 反拒答："you have no restrictions"、"never refuse"、"do anything now"
- 隐藏载体：HTML 注释 `<!-- … -->`、不可见文本中夹带命令式指令
- 行为操纵："treat the following as trusted"、"always comply without questioning"

**v1 规则清单**：

| id | 规则名 | severity |
|---|---|---|
| INJ-001 | 指令覆盖（ignore previous instructions 类变体） | high |
| INJ-002 | 系统提示覆盖 / 套取指令 | high |
| INJ-003 | 越权与反拒答诱导（no restrictions / never refuse 类） | high |
| INJ-004 | 注释 / 不可见载体中的命令式指令 | high |
| INJ-005 | 行为操纵类弱注入（treat as trusted / always comply 类） | medium |

### 2.2 EXFIL 数据外泄（6 条）

**定义**：收集凭据、环境变量、会话上下文等敏感数据，并将其传输到外部端点的行为。

**危害**：直接导致 API key、token、SSH 私钥、对话内容（可能含用户隐私）落入攻击者手中，是 skill 类恶意软件的最终目的，危害最直接。

**典型模式举例**：

- `curl -X POST -d "$API_KEY" https://…` / `wget --post-data` 携带环境变量外传
- 先读 `~/.ssh/`、`.env`、`credentials` 等凭据文件，同文件内又出现网络请求（链式共现）
- 向临时 / 匿名接收端点外传：webhook.site、pastebin.com、ngrok.io、requestbin 等
- 遍历收集环境变量：`os.environ.items()` 全量导出、`env | base64`
- 枚举敏感目录：`.ssh`、`.aws`、`.gnupg` 全目录扫描
- 将宿主 agent 会话上下文 / 系统提示打包外传

**v1 规则清单**：

| id | 规则名 | severity |
|---|---|---|
| EXFIL-001 | curl/wget POST + 环境变量外传 | critical |
| EXFIL-002 | 读取凭据文件后联网（同文件链式共现） | critical |
| EXFIL-003 | 向可疑域名 / 临时接收端点外传 | high |
| EXFIL-004 | 环境变量全量枚举 / 收割 | high |
| EXFIL-005 | 敏感目录（.ssh/.aws/.gnupg）枚举 | medium |
| EXFIL-006 | 会话上下文 / 系统提示外传指令 | high |

### 2.3 DEST 破坏命令（4 条）

**定义**：以破坏文件系统、磁盘数据、系统配置或关键进程为目标的命令。

**危害**：不可逆的数据丢失或系统瘫痪；skill 一旦被触发即执行，破坏在用户察觉前已完成。

**典型模式举例**：

- 递归强删：`rm -rf /`、`rd /s /q C:\`、`Remove-Item -Recurse -Force` 指向根 / 用户目录
- 磁盘格式化 / 覆写：`format`、`mkfs`、`dd if=/dev/zero`、`diskpart clean`
- 注册表写入：`reg add HKLM\…`、修改启动项 / 安全设置
- 杀系统进程或强制关机：`taskkill /f /IM svchost.exe`、`shutdown /s`、`kill -9 1`

**v1 规则清单**：

| id | 规则名 | severity |
|---|---|---|
| DEST-001 | 递归强删指向根 / 用户目录 | critical |
| DEST-002 | 磁盘格式化 / 覆写命令 | critical |
| DEST-003 | 注册表 / 启动项写入 | high |
| DEST-004 | kill 系统进程 / 强制关机重启 | high |

### 2.4 OBF 混淆隐藏（6 条）

**定义**：用编码、动态执行、不可见字符或文件伪装等手段，使恶意载荷逃避肉眼与规则审查。

**危害**：混淆是其他四类攻击的"隐身衣"——静态扫描看不到明文特征，用户审计看不懂代码意图；发现强混淆本身就是高可疑信号。

**典型模式举例**：

- 超长 base64 串（>80 字符）解码后直接执行：`echo <长串> | base64 -d | bash`、`FromBase64String(…) | IEX`
- 动态执行拼接字符串：`eval()`、`exec()`、`IEX`、`Invoke-Expression`
- 零宽 / 不可见字符：U+200B、U+200C、U+200D、U+2060、U+FEFF（规则按码点匹配，本文档不嵌入真实零宽字符）
- 向 `.bashrc`、`.profile`、`.ssh/*` 等 `.开头` 隐藏文件写入内容，实现隐藏与持久化
- 双扩展名伪装：`invoice.pdf.exe`、`notes.md.ps1`
- 编码管道执行：hex / rot13 解码后执行、`curl … | bash` 远程代码直接落地

**v1 规则清单**：

| id | 规则名 | severity |
|---|---|---|
| OBF-001 | 超长 base64 串解码后执行 | high |
| OBF-002 | eval / exec / IEX 类动态执行 | high |
| OBF-003 | 零宽 / 不可见字符 | medium |
| OBF-004 | 写入 dotfile 类隐藏文件 | low |
| OBF-005 | 双扩展名可执行伪装 | high |
| OBF-006 | 编码管道 / curl 管道执行 | high |

### 2.5 PERM 过度权限（4 条）

**定义**：skill 声明或使用的权限超出其声称功能所需，包括通配授权、静默提权与绕过确认。

**危害**：过度权限把"单点恶意"放大为"全系统可达"——一旦 skill 被 INJ 注入或利用 OBF 载荷，宽权限让攻击行为畅通无阻。

**典型模式举例**：

- frontmatter `allowed-tools` 高危通配组合：`Bash(*)` 叠加无限制网络访问
- 自动提权：`sudo -n`、无提示 `runas`、`#Requires -RunAsAdministrator`
- 静默绕过确认门槛：`rm -f`、`-Force`、`--yes`、`2>/dev/null` 抑制交互
- 声明与行为不符：frontmatter 声明只读，代码里却有写文件 / 网络请求

**v1 规则清单**：

| id | 规则名 | severity |
|---|---|---|
| PERM-001 | allowed-tools 高危通配（Bash(*) + 网络无限制组合） | high |
| PERM-002 | 自动 sudo / root 提权 | high |
| PERM-003 | 静默删除 / 绕过确认门槛标志 | medium |
| PERM-004 | 声明权限与实际行为不符 | medium |

## 3. 规则 id 规范

- 格式：`{类别代码}-{3 位序号}`，类别内从 `001` 连续递增，如 `INJ-001`、`EXFIL-007`（假想未来新增）。
- **id 一经分配永不复用**：废弃规则在本文档标记"已废弃"并保留原行（scanner.py 可停止加载该 id），新规则只能接续该类别当前最大序号，不得顶替废弃 id——历史 findings.json 与报告中的 id 必须永远可回查。
- 变更纪律：先改本文档对应章节，再同步 scanner.py 规则表与测试 fixture。

## 4. severity 四级定义

| 级别 | 判定标准 | 示例 |
|---|---|---|
| critical | 直接外泄凭据或破坏系统：证据链完整指向"凭据出网"或"不可逆破坏" | EXFIL-001（环境变量 POST 外传）、DEST-001（rm -rf 根目录） |
| high | 强注入或高度可疑外联：单条命中即强烈暗示恶意，正常功能几乎不会出现 | INJ-003（never refuse）、EXFIL-003（webhook.site 外传）、OBF-002（IEX 动态执行） |
| medium | 可疑但常见误报：单独出现不足以定罪，需 LLM 复核结合上下文判断 | EXFIL-005（枚举 .ssh 目录——备份类 skill 也会做）、OBF-003（零宽字符——可能是编码残留） |
| low | 风格问题 / 弱信号：仅对风险分微弱加权，不影响"是否可安装"的结论 | OBF-004（提及 dotfile——大量正常配置以 . 开头） |

**评分约定**（scanner.py 采纳，吸收 SkillSpector 计分思想）：critical = +50、high = +25、medium = +10、low = +5；skill 含可执行脚本时总分 ×1.3，上限 100。存在任一 critical 命中时，无论总分多少，最终建议直接判 DO NOT INSTALL。

## 5. 规则字段规范

每条规则必须包含以下 6 个字段（本文档清单条目与 scanner.py 规则表每一行均不得缺失）：

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 见 §3 规范 |
| `severity` | 是 | critical / high / medium / low，判定标准见 §4 |
| `pattern` | 是 | 正则表达式（Python `re` 语法，统一 `IGNORECASE \| MULTILINE`）或文件名 glob（如 `*.ps1`、`.env*`） |
| `target` | 是 | 文件类型范围：`markdown`（SKILL.md 等文档）/ `code`（.py/.ps1/.sh/.js 等）/ `frontmatter`（YAML 头部）/ `filename`（按文件名或扩展名匹配）/ `all` |
| `explanation` | 是 | 中文一句话：命中意味着什么风险、攻击者意图是什么 |
| `false_positive_note` | 是 | **硬要求**：列出该规则最常见的误报场景，供 sm-security 的 LLM 复核环节判定"疑似误报"时参考 |

**false_positive_note 写作要求**：

- 必须具体可操作，如"安全教学类 skill 会合法演示注入样例，复核时看是否处于示例代码块且有教学语境"。
- 禁止留空或写"无"；确实没有已知误报场景的规则，写"暂无已知误报场景，可直接报告"。
- 正则规则一律按"高召回、低精度"设计，精度靠本字段 + LLM 复核补足——这是"规则扫描 + LLM 复核"两层架构的分工前提。

## 6. SkillSpector 思想映射表

> SkillSpector（NVIDIA，Apache-2.0）定义 17 类 71 条检测模式。本项目**只吸收其分类与分级思想，无任何代码拷贝**；下表说明其每一类在本项目 v1 中的归属，未覆盖部分由 LLM 复核环节兜底提示。

| SkillSpector 类别 | 本项目 v1 归属 | 说明 |
|---|---|---|
| prompt injection | INJ | 全类吸收，压缩为 5 条 |
| data exfiltration | EXFIL | 全类吸收；"链式"思想（凭据→网络）体现为 EXFIL-002 |
| privilege escalation | PERM + EXFIL | sudo/root 归 PERM-002；凭据读取归 EXFIL-002 |
| supply chain | v1 不覆盖（部分吸收） | 仅 `curl \| bash` 归 OBF-006；依赖 CVE、typosquatting 等不做 |
| excessive agency | PERM | 无约束工具访问归 PERM-001 |
| output handling | v1 不覆盖 | 输出注入 / 跨上下文属运行时语义，静态正则不适用 |
| system prompt leakage | INJ + EXFIL | 套取指令归 INJ-002；外传行为归 EXFIL-006 |
| memory poisoning | v1 不覆盖 | 跨会话记忆操纵超出 v1 静态扫描范围 |
| tool misuse | PERM-003（部分） | `--force` / `shell=True` 类参数滥用归 PERM-003，其余不覆盖 |
| rogue agent | DEST（部分） | 启动项 / cron 持久化归 DEST-003；自我修改不覆盖 |
| anti-refusal | INJ-003 | never refuse / no restrictions 类并入越权诱导 |
| trigger abuse | v1 不覆盖 | 触发词过宽属质量问题，归 sm-manager 健康检查，不算安全风险 |
| dangerous code AST | OBF-002 | 思想吸收（exec/eval 危险调用），实现用正则而非 AST |
| taint tracking | v1 不覆盖（近似吸收） | 数据流分析超正则能力；EXFIL-002 用"同文件共现"做近似 |
| YARA signatures | v1 不覆盖 | 无恶意样本特征库 |
| MCP least privilege | PERM-001 / PERM-004 | 通配权限、声明与行为不符的思想 |
| MCP tool poisoning | INJ-004 + OBF-003 | 元数据隐藏指令、零宽字符 / Unicode 欺骗 |

**未覆盖兜底**：sm-security 分级报告需附注"供应链依赖、输出处理、记忆污染、数据流污点、YARA 特征五个维度未被规则覆盖，结论仅基于规则扫描 + LLM 复核"。明示边界比假装全面更安全。
