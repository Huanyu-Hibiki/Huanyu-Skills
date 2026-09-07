# Profile 主页设计要素（单一来源）

> 主页仓库（username/username）的设计要素清单。外部实战范本的内行做法已提炼为通用规则——编写主页时**直接按本文件执行，不引用、不复刻任何第三方主页仓库**。

## 1. 渲染机制（为什么这样做）

- 创建与用户名**完全同名**（含大小写）的 public 仓库，根目录放 `README.md`，GitHub 自动渲染到个人主页 Overview——这是唯一官方途径
- README.md 不在根目录或仓库名不一致 → Overview 不渲染

## 2. 双语互链

- `README.md`（英文默认）+ `README.zh-CN.md`（中文），两份顶部第一行互链：`**English** · [中文](README.zh-CN.md)`
- 两份各自被搜索引擎索引，覆盖两组搜索词；内容等价表达，不做逐字机翻

## 3. 漏斗信息架构（按序）

1. **`# Hi, I'm X 👋` + 自我介绍**：第一人称两三句，讲一条故事线（我是谁 → 在做什么 → 为什么这样做）；身份关键词自然嵌入；坦诚的表达（如非传统背景）比堆砌头衔更可信。紧跟一行社媒链接（如 `🐦 X · ✍️ 博客 · ▶️ YouTube`）——没有真实链接就整行不放
2. **`---` 分隔**
3. **🆕 最新**：发行公告位，放最新作品 + 一句话价值；大版本发布后回来更新
4. **⭐ 精选**：用得最多 / 最能代表你的项目；一行导语（如 "The ones people use most."）
5. **主题分组**：按领域分节，emoji 标题 + 一句话导语；**项目可跨板块重复出现**（精选位 + 分组位）增加曝光

## 4. 项目行格式

```markdown
emoji [**项目名**](仓库链接) (<!--stars:项目名-->1.2k<!--/stars--> stars) - 一句话描述（从项目真实 README 提炼）
```

- star 数包在 `<!--stars:仓库名-->` … `<!--/stars-->` 注释标记内：渲染不可见、脚本可定位刷新
- 描述一句话讲清「是什么 + 给谁用」，与该仓库 description 同源口径
- **0-star 或未发布：整个 `(… stars)` 括号不加**

## 5. 减法清单（最重要的一节）

- 不展示 0 star / 低 star 数（负资产），不放 stats 卡片、Star History
- 不放 fork 的仓库
- 不链接 private 仓库（访客 404 = 死链）
- 没有真实链接的社媒、没有真实素材的图片占位，一律不放

## 6. 配套 profile 元数据

- Bio 填满（= 主页的 meta description）；Company / Location / Website 尽量填
- Pin ≤6 个最能代表你的仓库；头像清晰；保持公开活跃

## 7. star 数自动刷新（可选组件）

有 star 之后再启用：把本 skill 的 `references/update-stars.yml` 与 `references/update-stars.py` 复制进主页仓库的 `.github/workflows/` 与 `.github/scripts/`，把脚本头部 `OWNER` 改成用户名。手动触发（workflow_dispatch），按标记刷新数字，格式与 GitHub 展示一致（<1000 精确值，以上一位小数 k 并去掉尾零）。
