# candidate-pool — 候选池数据源

/oracle-recommend 消用的外部候选池（Notion / Excel / RSS 等自有池子）。

## 通用契约

- fetch → 符合 [candidate-schema](../../shared-references/candidate-schema.md) 的 items（`source = "pool:<name>"`）
- **id 归一化与 trend 源一致**（source_type 都是 `pool`→注意：跨 type 不自动去重，同名不同 type 视为不同来源，pool 源内部要自己保证稳定 id）
- **只推荐已打分的**——REQUIRE_SCORED=true 是 recommend 的诚实门槛，池子拉进来还没打分的会先过 /oracle-score 粗筛

## 接入示例（Notion）

导出为 markdown → 按 H3 结构 normalize 进 candidates.md；或 Notion API 拉数据库视图 → 逐条转 schema。

## 常见坑

- 私有池子往往含"随手记的一闪念"——入池前先问用户要不要全部粗打分，别把 50 条碎片全灌进推荐排序
- 池子与 candidates.md 双向同步不自动做：**以 candidates.md 为单一真值**，外部池是导入源不是镜像
