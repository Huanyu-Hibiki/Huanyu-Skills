# PulseHub 项目初始化实战参考

> 给 `pulse-init` 提供实战 SOP 和踩坑，不是重复 SKILL.md 内容。本文件由 2026-07-28 实战经验沉淀。

## 1. 启动前必查的三件事

### 1.1 模板路径（Windows + Hermes）

`pulse-init` SKILL.md 写的"`<PulseHub 仓库>/skills/_archive/`"在 Hermes 部署下**不直接可用**。正确的模板源：

```text
C:\Users\kabuto\.hermes\skills\marketing\pulsehub\_archive\
├── README.md
├── 爆款素材库.md
├── 个人风格.md
├── 话术资产.md
├── 人群语料库.md
├── 数据反馈.md
└── 项目档案.md
```

如果用户没显式给 PulseHub 仓库路径，**默认走 Hermes skill 副本**——别去 `<PulseHub 仓库>/skills/_archive/` 找文件。

### 1.2 双轨现状查询

启动前先读 MEMORY.md 检查 "xinmeiti-huoke vs PulseHub" 双轨状态。当前默认：

- `xinmeiti-huoke` 保持 active 直到用户明确说"移除"
- `PulseHub` 双轨并行（v2）
- 新 `pulse-init` 创建的项目档案**与**旧 `raw/xinmeitihuoke/项目档案.md` 是两套，独立保存

如果用户已有 `raw/xinmeitihuoke/项目档案.md`，**Step 8 之前必须问一句**：

```
你已经在 raw/xinmeitihuoke/ 下有一份旧项目档案。
PulseHub 是新建独立项目大脑，还是要迁移/复用旧档案里的关键字段？
```

### 1.3 PulseHub 产品定价权威源

用户报价格时，文衡、照胆的价格是**产品定价页**的权威值，不是 AI 推断。如果用户口述价格与定价页不一致，先信用户（可能刚改过），再标注待 verify。

## 2. 项目档案路径的两种规范

PulseHub SKILL.md 默认写 `~/.pulsehub/archive/<项目名>/`，但 Obsidian wiki 端的业务归位规范是：

```text
C:\work\Huanyu Hub\Huanyu-Knowledge\raw\pulsehub\
├── project\
├── signals\
├── outputs\
├── reviews\
└── README.md
```

**实战策略**：pulse-init 创建项目时建议同时维护两边：

- `~/.pulsehub/archive/<项目名>/` ← PulseHub skill 体系内部权威
- `C:\work\Huanyu Hub\Huanyu-Knowledge\raw\pulsehub\project\` ← Obsidian wiki 复利位置

两边内容主体相同（参见 `obsidian-wiki/references/raw-dual-write-pattern.md`）。

## 3. 决策校验的 ABCD 选项形式（OP 用户硬偏好）

SKILL.md 已经写了"核心原则 4 / Pitfall P1-P3"，**继续遵守**：

- 每个澄清题先抛 ABCD 选项
- 每项一句话说明
- 允许多选 + "X 包括一小部分"
- 不要追加"或自定义答案"尾巴

## 4. 实战 Round 顺序（已被验证的 11 题）

今天跑通 Round 1（基本信息）+ Round 2 头部（人群）共约 11 题：

1. 凑合方案（ABCD）
2. 能否人工交付（ABCD）
3. 核心付费客户（ABCD，用户答 "A、C、D，B 包括一小部分"）
4. 痛的程度（ABCD）
5. 付费意愿状态（ABCD）
6. MVP 边界 4 问（每个 ABCD）
7. Processize 3 问（每个 ABCD）
8. 定价状态（ABCD）
9. 变现模式（ABCD）
10. 第一批付费客户来源（ABCD）
11. 第一批客户路径/变现（ABCD）

**建议**：单次会话如果走完 Round 1+2 太多题，用户容易疲劳。可以分两轮跑——今天跑 Round 1（基本信息）+ Round 2 头部（凑合方案、人工交付、客户），明天再跑 Round 2 剩余 + Round 3+4。

## 5. 收工协议

完整跑通 pulse-init 一次性会很长，建议：

- 跑完 Step 1-3（决策校验 6 步）→ 落 daily note 标记核心任务进度
- 跑完 Step 8（项目档案 4 轮）→ 落 daily note 标记进度
- 跑完 Step 9（个人风格）→ 落 daily note + 跑 pulse-init 输出
- **不强行一次跑完 10 步**——尊重 3 件协议

## 6. 验证清单（pulse-init 完成后跑）

```bash
# 1. 项目档案存在
test -s ~/.pulsehub/archive/<项目名>/项目档案.md && echo "项目档案 ✅"

# 2. 占位符清理
grep -c '\[待填写\]' ~/.pulsehub/archive/<项目名>/项目档案.md
# 应该 = 0（除可选字段外）

# 3. 累积产出索引更新
grep -E '^\| (人群语料库|爆款素材库|话术资产|数据反馈|个人风格)\.md' ~/.pulsehub/archive/<项目名>/项目档案.md
```

完成验证后再向用户报"项目大脑已建立"。