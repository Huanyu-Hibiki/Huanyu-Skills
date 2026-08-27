# 图文配图工作流（guizang-social-card-skill 联动）

> 2026-08-05 确认：PulseHub 产出"图文"必须含实际渲染的配图。

## 触发条件

当 pulse-copywrite 产出小红书图文笔记时，文字稿完成后必须走配图流程。

## 工具

`guizang-social-card-skill`（已安装）

## 流程

1. **pulse-copywrite 产出文字稿**（含每张图的文字内容规划）
2. **问用户图片来源**（guizang skill 的 Intake 步骤要求）：
   - A. 用户自己有照片/截图（推荐——最不"AI感"）
   - B. 去 Pexels/Unsplash 找工程场景图
   - C. 用 AI 生成配图
3. **选风格**：
   - Swiss International（数据/清单/对比场景，工程合同适用）
   - Editorial Magazine（叙事/深度文章适用）
4. **选 accent**：safety-orange（工程安全色）/ ikb（专业蓝）/ lemon-yellow / lemon-green
5. **用 guizang 模板渲染**：拷贝 `template-swiss-card.html` 或 `template-editorial-card.html`
6. **用 Playwright 截图**输出 1080×1440 PNG（小红书3:4标准）
7. **用 Chrome DevTools 验证**文字无溢出、无边缘碰撞

## 输出位置

```
outputs/social-cards/<编号>-<slug>/
  ├── index.html          # guizang 模板
  ├── assets/             # 配图素材
  └── output/
      ├── xhs-01.png      # 封面
      ├── xhs-02.png      # 内容页1
      ...
      └── xhs-07.png      # 结尾页
```

## 渲染命令（crawl4ai venv 有 Playwright）

```bash
"C:/Users/kabuto/.hermes/venvs/crawl4ai/Scripts/python.exe" -c "
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def render():
    task_dir = Path('.')
    output_dir = task_dir / 'output'
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1080, 'height': 1440})
        html_path = (task_dir / 'index.html').resolve()
        await page.goto('file:///' + str(html_path).replace(chr(92), '/'))
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(3)
        posters = await page.query_selector_all('.poster.xhs')
        for i, poster in enumerate(posters, 1):
            await poster.screenshot(path=str(output_dir / f'xhs-{i:02d}.png'))
        await browser.close()

asyncio.run(render())
"
```

## 注意

- 小红书图文 = **文字 + 图片**，不能只给文字大纲
- 图片用 guizang skill 的布局配方（S01-S12 Swiss / M01-M16 Editorial），不要自己写 CSS
- 渲染后用 Chrome DevTools `evaluate_script` 检查溢出
