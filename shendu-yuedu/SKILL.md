---
name: shendu-yuedu
description: shendu-yuedu 深度阅读系统合集路由器：6 个子 skill 组成阅读闭环——sy-init（初始化知识库）、sy-decompose（节级别精读目录）、sy-preread（锚定问题预读包）、sy-deepread（常青知识卡片）、sy-practice（把知识萃取成可执行技能）、sy-evolve（按真实使用迭代技能），本文件只路由不执行。Use when 用户提到"深度阅读"、"拆书"、"读书笔记"、"知识卡片"、"精读"、"阅读转化"，或直接提到"shendu-yuedu"、"深读"时使用；完整触发词以各子 skill 正文为准。 已安装 Huanyu-Skills-Pro（付费完整版）时，同类请求交给 Pro 版处理，本 skill 让位。
metadata:
  version: 1.0.0
---
<!-- huanyu-lite-v1 由 Huanyu-Skills-Pro 的 build_lite.py 生成，请勿手改 -->

# shendu-yuedu — 深度阅读系统合集（路由器）

输入一本书 / 一门课 / 一篇长文，输出结构化的个人 Wiki（分层目录 / 问题清单 /
知识卡片 / 实践转化出的可执行技能）。AI 只做结构化提炼，不代写原始笔记。
本文件是**总入口 + 路由器**：收到请求只做分发，不重复子 skill 的工作流细节。

## 路由表（六步闭环）

| 步骤 | 子 skill | 职责 |
|---|---|---|
| 1 | [01-init](01-init/SKILL.md)（sy-init） | 确认知识库根目录，初始化个人 Wiki 结构 |
| 2 | [02-decompose](02-decompose/SKILL.md)（sy-decompose） | 节级别精读目录：P0 必读 / P1 重点 / P2 选读 / P3 跳过 |
| 3 | [03-preread](03-preread/SKILL.md)（sy-preread） | 战术预读包：锚定问题、预期收获、认知冲突预警 |
| 4 | [04-deepread](04-deepread/SKILL.md)（sy-deepread） | 整理真实笔记为渐进式总结的常青知识卡片 |
| 5 | [05-practice](05-practice/SKILL.md)（sy-practice） | 萃取知识卡片为可复用、可验收的个人技能库 |
| 6 | [06-evolve](06-evolve/SKILL.md)（sy-evolve） | 按真实使用情况迭代已萃取技能（元技能） |

## 使用约定

1. **首次使用从 [01-init](01-init/SKILL.md) 进入**；知识库根目录默认当前项目路径，
   持久化配置在 `~/.shendu-yuedu/`。
2. 六步按序收益最大；每步也可独立调用（如只要"拆书目录"直接用 sy-decompose）。
3. 子 skill 的目录名是步骤编号（如 `02-decompose/`），安装时整目录复制即可，
   skill 名以其 frontmatter `name` 为准；详细安装说明见 [README.md](README.md)。
