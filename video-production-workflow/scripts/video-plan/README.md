# video-plan 执行资源

`video-plan` 的核心动作是模型根据终稿进行语义分镜拆解、A-roll/B-roll 路由和交接文档生成，不是机械转换，因此没有一个可以代替判断的脚本。

本目录保留入口说明，实际格式约束位于：

- `../../templates/storyboard.template.md`
- `../../templates/asset-request-list.template.md`
- `../../templates/motion-request-list.template.md`
- `../../references/video-plan/output-template.md`

初始化、状态、迁移和素材文件操作由相应的新 Skill 脚本负责；`video-plan` 的输出必须由模型读取完整文稿后落盘，不能用空模板伪造完成状态。
