# 安装说明（手动安装）

合集内 9 套系统全部支持**手动复制安装**，无需命令行工具。

## 准备

确认你的 Agent 客户端支持 skills 目录（Claude Code / OpenCode / Codex / Cursor 均可）。
下文以 `~/.claude/skills/` 为例；其他客户端把目标路径换成对应 skills 目录即可。

## 目录布局

安装后每个系统在 skills 目录下是一个独立文件夹：

```
~/.claude/skills/
├── founder-ip/            # 整套系统（含全部子 skill）
│   ├── SKILL.md           # 系统入口 / 路由器
│   ├── README.md
│   └── skills/            # 子 skill 目录
│       └── ip-strategy/
│           └── SKILL.md
└── pulse-router/          # 单独安装的子 skill 也可以
    └── SKILL.md
```

## 逐套安装说明

### founder-ip（founder-ip）

- 整套安装：复制 `founder-ip/` 整个目录到 Agent 的 skills 目录（如 `~/.claude/skills/founder-ip/`）。
- 子 skill 单装：复制 `skills/ip-strategy/` 到 skills 目录即可单独使用（skill 名以该目录 SKILL.md 的 `name` 为准）。

### GitHub-Renovation（github-renovation）

- 整套安装：复制 `GitHub-Renovation/` 整个目录到 Agent 的 skills 目录（如 `~/.claude/skills/GitHub-Renovation/`）。
- 本系统为单一 skill：安装即复制上面整个目录。

### oracle-bone（oracle-bone）

- 整套安装：复制 `oracle-bone/` 整个目录到 Agent 的 skills 目录（如 `~/.claude/skills/oracle-bone/`）。
- 子 skill 单装：复制 `skills/oracle-init/` 到 skills 目录即可单独使用（skill 名以该目录 SKILL.md 的 `name` 为准）。

### PPT-design（ppt-design）

- 整套安装：复制 `PPT-design/` 整个目录到 Agent 的 skills 目录（如 `~/.claude/skills/PPT-design/`）。
- 本系统为单一 skill：安装即复制上面整个目录。

### pulsehub（pulsehub）

- 整套安装：复制 `pulsehub/` 整个目录到 Agent 的 skills 目录（如 `~/.claude/skills/pulsehub/`）。
- 子 skill 单装：复制 `pulse-router/` 到 skills 目录即可单独使用（skill 名以该目录 SKILL.md 的 `name` 为准）。

### shendu-yuedu（shendu-yuedu）

- 整套安装：复制 `shendu-yuedu/` 整个目录到 Agent 的 skills 目录（如 `~/.claude/skills/shendu-yuedu/`）。
- 子 skill 单装：复制 `01-init/` 到 skills 目录即可单独使用（skill 名以该目录 SKILL.md 的 `name` 为准）。

### skill-master（skill-master）

- 整套安装：复制 `skill-master/` 整个目录到 Agent 的 skills 目录（如 `~/.claude/skills/skill-master/`）。
- 子 skill 单装：复制 `skills/sm-manager/` 到 skills 目录即可单独使用（skill 名以该目录 SKILL.md 的 `name` 为准）。

### video-production-workflow（video-production-workflow）

- 整套安装：复制 `video-production-workflow/` 整个目录到 Agent 的 skills 目录（如 `~/.claude/skills/video-production-workflow/`）。
- 子 skill 单装：复制 `skills/video-init/` 到 skills 目录即可单独使用（skill 名以该目录 SKILL.md 的 `name` 为准）。

### xianyu-skill（xianyu-skill）

- 整套安装：复制 `xianyu-skill/` 整个目录到 Agent 的 skills 目录（如 `~/.claude/skills/xianyu-skill/`）。
- 子 skill 单装：复制 `01-detail-images/` 到 skills 目录即可单独使用（skill 名以该目录 SKILL.md 的 `name` 为准）。
- 随包模板：五套锁定模板（dashi-ppt-skill、frontend-slides、guizang-ppt-skill、huashu-design、ppt-master）体积较大，只随合集包与合集仓库分发；xianyu-skill 单系统包不含 `template/PPT/`，需要模板请下载合集包或克隆合集仓库。


## 常见问题

- **子 skill 单装会不会缺东西？** 单装某个子 skill 时，它自身目录内的文件是完整的；
  少数系统有跨子 skill 的共享资源（如 pulsehub 的 `_core/`、`_shared/`），
  依赖这些资源的能力需要整套安装才可用。
- **已安装同名付费完整版怎么办？** 各 SKILL.md 的说明中已注明让位约定：
  同类请求交给 Pro 版处理。
<!-- 同步点：五套锁定模板名单与 preview_lite.py `_install_section`、CHANGELOG.md 保持一致，增删模板须同步更新。 -->
- **模板文件在哪？** `xianyu-skill/template/PPT/` 内置五套锁定版本的第三方模板，
  已随合集附带原许可文件，无需单独下载。
