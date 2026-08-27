# 知乎开放平台搜索 API

> 2026-08-05 实证可用。用户提供了 API Key，每天免费 5000 次调用。
> 文档：https://developer.zhihu.com/docs?key=zhihu_search

## 接口

```
GET https://developer.zhihu.com/api/v1/content/zhihu_search
```

## 鉴权

```
Authorization: Bearer <API_KEY>
X-Request-Timestamp: <秒级 Unix 时间戳>
Content-Type: application/json
```

API Key 存在 `~/.hermes/.env` 的 `ZHIHU_API_KEY` 变量里。读取方式：

```python
import os
api_key = os.environ.get("ZHIHU_API_KEY", "")
```

## 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| Query | String | 是 | 查询关键词 |
| Count | Int32 | 否 | 数量，默认10，最大10 |

## 返回

`Data.Items[]` 每项含：
- `Title`, `ContentType`（Article/Answer）, `ContentID`, `ContentText`（摘要，**已自带内容**，通常无需再抓全文）, `Url`
- `VoteUpCount`, `CommentCount`, `AuthorName`, `EditTime`
- `CommentInfoList`（精选评论）

## 示例

```python
import requests, time, os

API_KEY = os.environ["ZHIHU_API_KEY"]
URL = "https://developer.zhihu.com/api/v1/content/zhihu_search"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "X-Request-Timestamp": str(int(time.time())),
    "Content-Type": "application/json"
}
params = {"Query": "工程合同审查", "Count": 10}
resp = requests.get(URL, headers=headers, params=params, timeout=15)
data = resp.json()
# data["Code"] == 0 → 成功；data["Data"]["Items"] 为结果列表
```

## 为什么用 API 而不是 scraping

1. **不会被反爬拦截**（网页端会返回 40362 "请求异常"）
2. **不需要登录态**（API Key 鉴权即可）
3. **ContentText 自带摘要**，通常无需再逐条打开 URL 抓正文
4. **每天 5000 次免费**，够用

## 多关键词策略

一个搜索词最多返回 10 条。要扩大覆盖面，跑多个相关 Query（如 "合同审查AI"、"工程合同审查"、"施工合同 风险"），然后按 ContentID 去重。
