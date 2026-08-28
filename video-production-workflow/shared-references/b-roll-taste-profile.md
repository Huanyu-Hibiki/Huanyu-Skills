# B-roll Taste Profile（B-roll 偏好档案）

`b-roll-finder` 在分析和搜索前读取本档案。它记录用户的真实选择、来源偏好和禁用项；没有用户确认的 `Confirmed-by` 标记时，不得把示例偏好当成用户偏好。

## 首次确认

```text
Confirmed-by: <用户姓名> (<YYYY-MM-DD>)
```

首次使用逐项询问：

1. B-roll 是否默认去除全部源音；
2. 静态图是否默认轻微中心缩放，还是完全静止；
3. 是否显示来源署名，署名颜色和位置；
4. 是否允许使用 Remotion 概念动效；
5. 是否允许 AI 生成 B-roll，允许哪些模型；
6. 禁用项：梗、政治、人物脸、文字卡、某类视觉风格等；
7. 默认画幅、单个 B-roll 时长和 B-roll 密度。

## 项目偏好

| 维度 | 当前值 | 来源 / 日期 |
|---|---|---|
| 默认主题 | `<tech / history / business / other>` | `<user>` |
| B-roll 源音 | `<always silent / preserve when requested>` | `<user>` |
| 静态图动效 | `<static / subtle zoom-in>` | `<user>` |
| 来源署名 | `<off / white / black / auto>` | `<user>` |
| Remotion 概念图 | `<on / off>` | `<user>` |
| AI 生成视频 | `<on / off / approval-only>` | `<user>` |
| 默认密度 | `<sparse / medium / dense>` | `<user>` |
| 默认画幅 | `<16:9 / 9:16 / source>` | `<user>` |

## B-roll 指纹

按实际发布视频或用户确认的参考片段记录：

- 常用 B-roll 类型：`<receipts / entity / concept / product / archive>`；
- 典型覆盖率：`<percentage>`；
- 典型镜头时长：`<seconds>`；
- 片头是否允许 burst montage：`<yes/no>`；
- 可接受的长停留：`<seconds>`；
- 常用颜色、字体、颗粒和转场：`<notes>`。

## 可信来源

| 主题 | 来源 / 账号 | 权威理由 | 允许用途 |
|---|---|---|---|
| `<topic>` | `<source>` | `<official / primary / reputable>` | `<entity / receipt / product>` |

## Guardrails

- 用户会话中明确说“不用”的类别立即写入本节；
- 禁用项永远不再搜索、推荐或自动恢复；
- 事实证据优先使用原始来源；
- 真实实体不使用无关概念卡替代；
- AI 生成画面不得冒充真实新闻、网页、产品界面或人物证据。
