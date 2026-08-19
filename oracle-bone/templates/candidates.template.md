# 候选池（candidates.md）

> oracle-trends / oracle-seed / oracle-recommend 共用。条目 schema 见 [shared-references/candidate-schema.md](../shared-references/candidate-schema.md)。
> 每条 H3 entry 格式：

```markdown
### [tier1] <标题>
- **id**: <12 位稳定 hash>
- **source**: <trend:hackernews | pool:markdown | paste:manual | seed>
- **snapshot_at**: <YYYY-MM-DD>
- **category**: <分类>
- **composite (rough, vN)**: X.X — <各维分>
- **track**: <轨道 id | cross:t1+t2 | null>
- **predicted bucket**: <粗估桶>
- **note**: <备注>
```

tier 语义：tier1 强候选 / tier2 备选 / tier3 长尾 / skip 用户跳过 / risky 风险议题 / done 已发布。
去重纪律：同 id 不重复入池；已发布的移出；用户拒绝的 6 个月内不推。

<!-- 候选条目从这里开始追加 -->
