# auto-collect — 一键采集 adapter（Playwright）

oracle-retro / oracle-compass-retro 的自动化数据来源。**设计模式参考 data-scientist-community（AGPL-3.0，作者赵逍遥）的思路，clean-room 重写**——监听创作者后台自身 API 响应 + DOM 兜底双源合并、复用用户浏览器 Profile、断点续跑。

## 合规红线（先读）

- 只采集**你自己账号**、你有权访问的创作者后台数据
- 首次授权必须在**可见浏览器窗口**由本人扫码/登录完成（headless=false）
- **不绕过**验证码/风控/频控；单平台单次采集 ≥2 分钟间隔，别贪
- Profile/Cookie 只存本机用户目录，绝不入库、不进 git
- 平台页面随时改版——采集器坏了先跑 `--auth-only` 看登录态，再跑 `--debug` 截图定位选择器漂移

## 安装（uv 虚拟环境）

```bash
cd adapters/perf-data/auto-collect
uv venv .venv --python 3.12
uv pip install --python .venv/Scripts/python.exe -r requirements.txt    # Windows
# uv pip install --python .venv/bin/python -r requirements.txt          # macOS/Linux
.venv/Scripts/python.exe -m playwright install chromium
```

## 日常运行（全部走 uv venv 的 python）

```bash
# 首次授权（每平台一次，弹出真浏览器窗口本人扫码）
.venv/Scripts/python.exe collect.py douyin --auth-only
.venv/Scripts/python.exe collect.py xiaohongshu --auth-only
.venv/Scripts/python.exe collect.py bilibili --auth-only
.venv/Scripts/python.exe collect.py wechat --auth-only
.venv/Scripts/python.exe collect.py kuaishou --auth-only

# 日常采集
.venv/Scripts/python.exe collect.py all --days 30
```

skill 内（oracle-retro / oracle-publish）调用本 adapter 时，统一用 auto-collect 目录下
`.venv/Scripts/python.exe`（AI 按 `find_venv()` 逻辑定位：本目录 .venv 存在即用，
不存在提示用户先按上面步骤安装）。

## 首次授权（每平台一次）

```bash
python collect.py douyin --auth-only        # 打开可见浏览器，本人扫码
python collect.py xiaohongshu --auth-only
python collect.py bilibili --auth-only
python collect.py kuaishou --auth-only
python collect.py wechat --auth-only        # 视频号：微信扫码（会话时效较短，过期重跑即可）
```

授权态存在 `~/oracle-bone-profiles/<platform>/`（专用持久 Profile，不碰日常 Chrome）。Profile 被平台风控标记污染时，用 `fresh` 模式一键重置（有 marker 防误删保护）：

```bash
.venv/Scripts/python.exe -c "from core.browser import BrowserSession; BrowserSession('douyin', headless=False, fresh=True).__enter__()"
```

## 日常采集

```bash
.venv/Scripts/python.exe collect.py douyin --days 30          # 最近 30 天作品
.venv/Scripts/python.exe collect.py all --days 14             # 全平台连采（含间隔）
.venv/Scripts/python.exe collect.py bilibili --limit 20       # 只采最新 20 条
```

产物（写入项目根 `.oracle-cache/collections/<ts>/`）：

```
unified.json      归一后的统一 schema 数据（→ snapshot_store archive）
five-dim.json     五维增量指标（→ compass-retro 五维闸门）
raw/*.json        平台原始响应（调试用，可删）
run.json          本次采集元信息（平台/条数/耗时/错误）
```

## 标准管线（AI 执行时按此调）

```bash
PY=.venv/Scripts/python.exe    # auto-collect 目录下的 uv venv
# 1. 采集
$PY collect.py all --days 30
# 2. 存快照
$PY ../../../../tools/snapshot_store.py archive --db <project>/content-analytics.db --input .oracle-cache/collections/<ts>/unified.json
# 3. 分析
$PY ../../../../tools/dashboard.py --db <project>/content-analytics.db --markdown
```

## 采集器结构

```
collect.py            CLI 入口
core/browser.py       Profile 管理 + 授权检查 + 导航重试
core/framework.py     监听+DOM 双源扫描框架 + 断点
platforms/douyin.py   抖音创作者中心
platforms/xiaohongshu.py
platforms/bilibili.py
platforms/kuaishou.py
platforms/wechat.py   视频号助手（端点候选态——首跑必 --debug 校准，见文件头说明）
```

## 视频号（wechat）专项说明

- 登录：微信扫码，**会话时效比其他平台短**，过期重新 `--auth-only` 即可
- 后台 API 公开资料最少 → 采集器处于**候选端点态**：首跑流程
  1. `.venv/Scripts/python.exe collect.py wechat --auth-only --debug` 微信扫码登录
  2. `.venv/Scripts/python.exe collect.py wechat --days 30 --debug`——DOM 兜底保底拿基础数据
  3. 打开产物 `<ts>/wechat-urls.log`，找作品列表真实响应 URL（通常含 list/post/finder 字样、状态 200、响应体大）
  4. 把 URL 特征回填 `platforms/wechat.py` 的 `ENDPOINTS`（收窄后重跑，监听数据更全）
- 部分账号详情页有完播率/平均播放时长（需要 `--details N` 逐作品进详情页）

## 失败模式速查

| 症状 | 处理 |
|---|---|
| 授权页循环 | `--auth-only` 重新本人登录 |
| 列表加载超时 | 平台改版 → `--debug` 截图看 DOM，校准 platforms/*.py 里的 SELECTORS |
| 监听 0 条响应 | 后端 API 路径变了 → `--debug` 打印所有响应 URL，更新 ENDPOINTS |
| 单作品详情失败 | 框架自动跳过记 error，不阻塞整批（断点续跑补） |
