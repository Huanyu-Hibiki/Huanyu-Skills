# 出图规格与 HTML→PNG 管线

## 画布规格

| 用途 | 尺寸 | 比例 | 说明 |
|---|---|---|---|
| 封面（轮播第 1 张） | 1080×1080（可放大到 1200×1200） | 1:1 | 闲鱼列表页缩略展示；第一张即封面 |
| 详情图（轮播第 2 张起） | 1080×1440 | 3:4 | 竖版在闲鱼商品页展示面积最大 |
| 全套张数 | **硬上限 9 张**（闲鱼单商品图片数量上限，超出传不上去） | — | 推荐 6-8 张：少于 5 张显得敷衍，多于 8 张完读率下降；留 1 张余量给真实案例图/买家秀类素材 |

- 统一用 1080 宽基准：`body { width:1080px; height:<1080|1440>px; }`
- 全套图必须同宽，比例混排会导致上传后展示不齐

## HTML 骨架（单文件、内联 CSS、零依赖）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@700;900&family=Noto+Sans+SC:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    width:1080px; height:1440px;      /* 封面改 1080px */
    overflow:hidden;                   /* 超出画布的内容直接裁掉——宁可改版式不可溢出 */
    font-family:'Noto Sans SC','Microsoft YaHei',sans-serif;
    position:relative;
  }
</style>
</head>
<body>
  <!-- 区块用绝对定位或 flex 布局，禁止依赖视口单位 -->
</body>
</html>
```

硬性要求：

1. **不用视口单位**（vw/vh）、**不用媒体查询**——画布是固定的，Playwright 视口即画布
2. **overflow:hidden 兜底**：内容装不下 = 设计问题，回去减内容或拆图，不许缩字号硬塞
3. **图片素材**：本地相对路径即可（截图时按 file:// 加载）；网络图截图前确认能加载，加载失败换本地
4. **字体回退栈**：每个 font-family 都带 `'Microsoft YaHei','SimHei',sans-serif` 兜底；无网络时 Google Fonts 会静默失败，务必 `--wait-for-timeout` 后再截

## 可读性下限（1080 宽画布）

| 元素 | 最小字号 | 说明 |
|---|---|---|
| 封面主标题 | 96px | 目标 120-160px |
| 详情图大标题 | 64px | — |
| 卡片标题/小节标题 | 40px | — |
| 正文 | 28px | 低于 28px 在手机上难读 |
| 注释/免责小字 | 22px | 仅限免责声明等非核心信息 |
| 行高 | 1.4-1.6 | 标题可压到 1.15 |

## 截图命令（Playwright）

```bash
# 首次准备（装过可跳过）
npx playwright install chromium

# 逐张导出（view-port-size 即画布尺寸）
npx playwright screenshot "file:///C:/abs/path/detail-html/01-封面.html" "C:/abs/path/images/01-封面.png" --viewport-size=1080,1080 --wait-for-timeout=2500
npx playwright screenshot "file:///C:/abs/path/detail-html/02-是什么.html" "C:/abs/path/images/02-是什么.png" --viewport-size=1080,1440 --wait-for-timeout=2500
```

- `--wait-for-timeout=2500`：等 Google Fonts 与图片加载完成，必带
- 路径用 `file:///` + 正斜杠绝对路径（Windows 下 `C:/...` 不是 `C:\...`）
- 批量：写一个循环脚本按清单逐张执行，输出后核对每张文件尺寸（用文件管理器或 `Get-ChildItem` 看尺寸/大小）

## 交付规格

- 输出 PNG 到 `<商品目录>/images/`，命名 `01-封面.png`、`02-是什么.png`…（编号即上传顺序）
- 单张文件大小控制：闲鱼对图片有压缩，过大的 PNG 上传后反而变糊；HTML 里避免大面积照片级渐变，截图后若单张 > 5MB，用工具转质量 85 的 JPG
- 上传顺序 = 文件名编号顺序，封面永远是 01

## 自检截图（可选但推荐）

批量导出后，把全套图缩略拼一张检查图（任意方式：HTML 平铺 200px 宽缩略图再截一张），肉眼过一遍"缩略图测试"——这一步能提前暴露缩略后不可读的问题。
