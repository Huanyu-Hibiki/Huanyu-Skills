# B站搜索 API 用法（2026-08-05 验证）

> 比 DOM scraping 可靠得多。在 Chrome DevTools `evaluate_script` 里跑，复用用户登录态。

## 搜索 API

```javascript
async () => {
  const resp = await fetch(
    'https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=' +
      encodeURIComponent('工程合同审查AI') + '&page=1',
    { credentials: 'include' }
  );
  const data = await resp.json();
  if (data.code !== 0) return { error: data.message };

  const results = (data.data?.result || []).slice(0, 20).map(v => ({
    bv: v.bvid,
    url: `https://www.bilibili.com/video/${v.bvid}`,
    title: v.title.replace(/<[^>]+>/g, ''),  // strip <em> tags
    author: v.author,
    play: v.play,
    reply: v.reply,
    video_review: v.video_review,
    duration: v.duration,
    tag: v.tag,
    description: v.description
  }));

  return { count: results.length, total: data.data?.numResults, results };
}
```

## 视频详情 metadata

B站视频页 `window.__INITIAL_STATE__.videoData` 含完整数据，比 DOM selector 可靠：

```javascript
async () => {
  await new Promise(r => setTimeout(r, 3000));
  const state = window.__INITIAL_STATE__;
  if (state?.videoData) {
    const v = state.videoData;
    return {
      title: v.title,
      desc: v.desc,
      owner: v.owner?.name,
      stat: {
        view: v.stat?.view,
        danmaku: v.stat?.danmaku,
        reply: v.stat?.reply,
        favorite: v.stat?.favorite,
        coin: v.stat?.coin,
        like: v.stat?.like,
      }
    };
  }
}
```

## 为什么不用 DOM scraping

B站搜索页 `.bili-video-card__info--tit` 等 selector 返回的 textContent 是脏数据（"稍后再看51561126:23" = 稍后再看+播放量+时长拼接），不是标题。API 返回干净的 JSON。
