# tests/fixtures — 测试资产说明

本目录是 pytest（`tests/test_*.py`）与脚本 CLI 验收共用的静态 fixture 集。
全部为纯静态文件、进 git；不含任何可执行逻辑，不要手改生成结果。

## agents-tree/ — 假 Agent 目录树（inventory.py 测试资产）

模拟多 Agent skill 安装场景。入口注册表：`agents-tree/agents-tree.yaml`，
schema 与 `shared-references/agents.yaml` 完全一致（冻结契约）：
顶层 `agents:` 列表，每条目恰有 `name` / `enabled` / `paths` 三键，
路径正斜杠、相对路径以该 yaml 所在目录为基准。

### Agent 级预期（installed 探测）

| agent（yaml name） | paths | 预期 installed | 说明 |
|---|---|---|---|
| fake-opencode | ./fake-opencode | true | 2 个 skill：alpha-skill、beta-skill |
| fake-claude | ./fake-claude | true | 6 个 skill 目录（含 4 个坏样本） |
| not-installed-agent | ./does-not-exist | false | 目录不存在 → `installed:false`，非错误，枚举正常继续 |

### Skill 级预期（健康 + health_issues）

| 目录 | 预期结果 |
|---|---|
| fake-opencode/alpha-skill | 健康：`has_skill_md:true`、`frontmatter_ok:true`、`desc_len<1024`、frontmatter name 与目录名一致 |
| fake-opencode/beta-skill | 健康（同上） |
| fake-claude/good-skill | 健康（同上，对照组） |
| fake-claude/no-manifest | **health_issue：missing_skill_md** — 目录内只有 notes.md、无 SKILL.md；仍应被枚举为 skill 条目（`has_skill_md:false`） |
| fake-claude/broken-frontmatter | **health_issue：frontmatter 残缺** — SKILL.md 只有开头 `---` 无结尾 `---`，解析不出 name/description（`frontmatter_ok:false`） |
| fake-claude/long-desc | **health_issue：description 超 1024 字符** — description 恰好 1200 字符（脚本生成，勿手改；重生成脚本未入库，由任务 5 会话一次性执行） |
| fake-claude/name-mismatch | **health_issue：命名不一致** — frontmatter `name: original-name`，目录名却是 name-mismatch |
| fake-claude/alpha-skill | 内容健康，但与 fake-opencode/alpha-skill 重名 → 进入 duplicates |

### duplicates 预期

| name | locations |
|---|---|
| alpha-skill | fake-opencode/alpha-skill/SKILL.md 与 fake-claude/alpha-skill/SKILL.md（共 2 处，跨 Agent） |

### issue 字符串冻结状态

- `missing_skill_md`：已由设计文档数据模型示例冻结。
- frontmatter 残缺 / desc 超长 / 命名不一致三类 issue 的**确切字符串**由任务 7
  的 `tests/test_inventory.py` 冻结；本 README 只冻结语义预期，不预先绑定字符串。

## 后续 fixture（占位，落地时更新本 README）

- `malicious-skill/`、`clean-skill/` — scanner.py 测试资产（任务 9）。
- `golden/report.html` — report.py golden file（任务 14）。
