# bilibili-popular — B 站热门/排行

- **依赖**：无（popular 端点）；ranking 端点需登录态 cookie
- **稳定性**：★★★☆☆（端点偶有风控变动）
- **fetch 接口**：

```bash
# 热门（无需登录，最稳）：
curl -s "https://api.bilibili.com/x/web-interface/popular?ps=20&pn=1" \
  -H "User-Agent: Mozilla/5.0"
# 检查 .code == 0，提取 data.list[].title / owner.name / stat.view

# 全站排行（需 SESSDATA cookie）：
curl -s "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all" \
  -H "User-Agent: Mozilla/5.0" -b "SESSDATA=<from .oracle-secrets.json>"
```

- **输出**：`source = "trend:bilibili-popular"`；snapshot_text = 标题 + UP 主 + 播放/弹幕数 + 分区
- **失败模式**：
  - code=-352（风控）→ skip 该端点，不重试（不是 cookie 问题，别浪费时间换 cookie）
  - code=-101（未登录）→ 提示配置 cookie 或退回 popular 端点
- **cookie 坑**（实测）：登录态在 `bilibili.com` 域，不在 `www.bilibili.com` 域（后者只有设备指纹）。检查：`grep SESSDATA <cookie文件>` 有结果才是对的。**多个域名子文件夹都要查完再下"缺登录态"结论**
