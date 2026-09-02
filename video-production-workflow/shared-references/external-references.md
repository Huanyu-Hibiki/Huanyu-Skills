# External References（外部参考项目登记与许可证边界）

本合集在制作过程中吸收了以下外部开源项目的方法论。各项目许可证不同，**可吸收的方式不同**；所有子 Skill 引用外部目录前先查本表。

| 项目 | 许可证 | 允许的吸收方式 | 本合集的吸收位置 |
|---|---|---|---|
| [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft) | **Apache-2.0** | ✅ 可分析原理、可改编代码/文档（保留署名、标注修改） | `video-jianying-draft`（vendor 安装层模式、标定常数、成片导出流程）、`references/video-jianying-draft/remotion-export.md`、`references/video-polish/music-beat-sync.md`、b-roll-generate 镜头纪律 |
| [video-talkcraft](https://github.com/Vincentwei1021/video-talkcraft) | **PolyForm Noncommercial 1.0.0** | ⚠️ **仅限分析原理**——非商业许可证与本合集 MIT 冲突，禁止复制其代码、文本、模板、demo 产物进本仓库；商业使用需原作者授权 | 以自写表述沉淀原理：词锚机器校验/镜尾保护带（`b-roll-timing-and-qa.md`）、排版预算/语义拍进场/三段式（`motion-brief-standards.md`）、P0/P1/P2 分级与独立评审（`video-polish`） |
| Remotion | Remotion License（公司版需付费） | 引擎依赖 | 仅作为渲染引擎调用；用户公司 >3 人或做自动化产品时需自行购买 Remotion 许可 |
| pyJianYingDraft | 上游仓库许可证 | vendor 内置 | `scripts/video-jianying-draft/vendor/`，剪映 Draft 生成 |
| ai-video-director（本地模板参考） | 项目内参考 | 原理分析 | 覆盖模式四布局、导演简报结构、审批闸门设计（v0.7.0 已吸收进 motion-brief-standards） |

## 引用规则

1. 子 Skill 的外部参考目录（`<外部参考项目根>\...`）一律是**软依赖**：路径不存在时跳过并在 `notes.md` 记录，不阻塞流程；
2. **PolyForm-NC 项目（video-talkcraft）的任何文件不得复制进本仓库**，也不得让用户"从那边拷过来用"；只允许阅读理解后用自写表述沉淀原理；
3. Apache-2.0 项目改编时保留来源注明（各吸收文档头部已标注）；后续二次修改无需额外声明，但不得移除原署名；
4. 新增外部依赖前先在此登记许可证结论，未查证许可证的项目不接入。
