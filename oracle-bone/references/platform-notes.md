# 平台坑备查（Platform Notes）

> Windows / Obsidian / 文件锁等平台特定问题的压缩备查。通用问题，各 skill 遇到时查这里。

---

## Windows 文件写入

**症状**：`PermissionError: [WinError 5] 拒绝访问`——`write` / `os.replace` / `shutil.copy` 全失败。

**诊断顺序**（按此排查，不要跳）：
1. 文件是否 ReadOnly 属性（`Get-ItemProperty <file> | Select Attributes` 显示 `ReadOnly`）→ `attrib -R <file>` 后重试（写完按需 `attrib +R` 恢复保护语义）
2. 是否笔记软件（Obsidian 等）进程锁句柄 → 让用户完全退出该软件（关标签页不够，要退进程）
3. 都不是 → 其他进程 hold 句柄（搜索索引 / 同步盘）

**反例**：以为是被锁，反复换写入 API 三次都失败，最后 dump 属性才发现是 ReadOnly——先查属性再动手。

## 文件夹 rename 被锁

**症状**：`os.rename` / `mv` / `Rename-Item` 全报 WinError 5，`attrib -R` 已清。

**根因**：后台进程持有目录树句柄（笔记软件 / 搜索索引 / 同步盘）。

**修复**：
1. 确认进程 → 让用户完全退出
2. 仍失败 → **copy + delete fallback**（绕过 rename 锁）：
   ```powershell
   New-Item -ItemType Directory -Path "<new>" -Force
   Copy-Item -Recurse "<old>\*" "<new>\"
   Remove-Item -Recurse -Force "<old>"
   ```
3. **文件夹名避开冒号**（全角"："部分版本也会拒）——最优标题含冒号时目录名去掉，标题行保留原文

## 中文路径 + glob

- glob 对中文路径偶发返回空——**不得仅凭 glob 的 "No files found" 判定不存在**，用目录读取（`Get-ChildItem` / `Test-Path -LiteralPath`）二次确认
- MSYS/git-bash 的 `/c/...` 路径某些 Python 库不认（要 `C:/...` Windows 风格）——跨工具传路径统一用 Windows 风格

## PowerShell 5.1 UTF-8

- `Set-Content -Encoding UTF8` 会写 BOM——可能破坏 YAML frontmatter 解析。用 .NET：`[System.IO.File]::WriteAllText($f, $raw, (New-Object System.Text.UTF8Encoding($false)))`
- 控制台显示中文乱码 ≠ 文件坏——`Get-Content` 默认 ANSI codepage 读 UTF-8 的显示问题；验证文件内容用 Read 工具或显式 `-Encoding UTF8`

## 输出位置纪律

- 面向用户的选项/方案菜单**永远写在消息正文**——不藏在 execute_code / 脚本的 stdout 里（部分消息渠道只渲染正文，stdout 会被吞）

## 各平台 API 快查（trend/perf adapter 用）

- B 站：登录态 cookie 在 `bilibili.com` 域（不是 www 子域）；分区 ranking 端点有 -352 风控（非 cookie 问题，skip 即可）
- 抖音：反爬极严，热搜端点免严格登录态可用；内容抓取需会话 cookie
- 代理环境：国内平台下载常需 `NO_PROXY="*"` 绕过系统代理

## 编辑长 SKILL.md

- `old_string` 唯一命中 ≠ 插对位置——同名小标题/重复结构多的文件，patch 前先定位父章节，patch 后验证位置（offset(parent) < offset(new) < offset(next_section)）
- 缩进敏感的 Python 代码不用字符串 patch——数组切片重写 + `ast.parse` 验证
