# Schema Migration Registry

## 当前版本

```text
LATEST_SCHEMA = 0.1
```

## 版本链

| 版本 | 类型 | 说明 |
|---|---|---|
| 0.1 | 初始版本 | 建立 `.video-workflow-state.json`、阶段状态、交接契约和 B-roll manifest |

## 迁移规则

- 新增可选字段：增加 minor 版本，在 state 读取时提供默认值，并登记迁移说明；
- 删除、重命名或改变字段语义：增加 breaking 版本，必须提供迁移脚本或人工步骤；
- 不静默把旧版 state 当成新版使用；
- 迁移前备份 `.video-workflow-state.json`；
- 迁移后重新生成 `STATUS.md`，并检查所有 artifacts 路径。
