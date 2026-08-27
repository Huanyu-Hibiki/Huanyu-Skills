# 焕羽 IP / cheat-on-content / PulseHub 三系统整合实证（2026-07-28）

用于 `/ip-opc-system` 生成 `opc-sop.md` 前的系统盘点参考。核心教训：不要只按 founder-ip 内部文档生成 SOP，必须先实查三套系统的权威目录与当前状态。

## 1. 三套系统权威位置

| 系统 | 角色 | 权威产出目录 |
|---|---|---|
| founder-ip | IP 战略层：战略、人设、商业模式、内容漏斗、长期选题库 | `C:\work\Huanyu Hub\Huanyu-Knowledge\company\01-Projects\焕羽个人IP\founder-ip` |
| cheat-on-content | 视频内容执行层：A/B 双轨、选题、评分、盲预测、拍摄登记、发布登记、复盘、rubric 进化 | `C:\work\Huanyu Hub\Huanyu-Knowledge\raw\video-creation` |
| PulseHub | 图文获客与营销资产层：关键词、用户洞察、小红书/公众号文案、私域承接、数据反馈 | `C:\work\Huanyu Hub\Huanyu-Knowledge\raw\pulsehub` |

## 2. 实查状态摘要

### founder-ip

当前已有：

- `strategy-memo.md`
- `persona-charter.md`
- `business-model-canvas.md`
- `content-funnel.md`
- `topic-pool.md`
- `opc-sop.md`

结论：战略层、人格层、商业层、内容漏斗层、OPC 整合层已跑通。`founder-ip` 负责长期约束，不直接替代内容执行。

### cheat-on-content

当前 `raw/video-creation` 实查要点：

- `.cheat-state.json` 存在且是全局唯一状态文件。
- 既有 EP001-EP005 视频项目。
- EP005 已发布，pending retro 仍在队列。
- `cheat-on-content` 总协议已经明确两条链路：
  - Track A：Build in Public + 历史壳子 / 借古论今 / IP 同频。
  - Track B：张三群像 + 产品获客 / 工程合规场景 / 文衡或照胆转化。

关键修正：不要说“缺少 B 链路”。正确说法是：**B 链路已设计，但一直没有实际拍摄进入校准池**。

### PulseHub

当前 `raw/pulsehub/project/焕羽格致社-工程合规AI获客` 已有：

- `项目档案.md`
- `人群语料库.md`
- `付费用户洞察报告.md`
- `关键词矩阵.md`
- `选题库.md`
- `爆款素材库.md`
- `个人风格.md`
- `outputs/001-开标前10分钟防废标自查.md`
- `话术资产.md`
- `数据反馈.md`

第一轮策略：先打 **文衡 + 防废标**，再用 **照胆 + AI 审合同靠不靠谱** 承接合同线。

## 3. 正确系统图

```text
founder-ip
  ↓ 定长期战略、人设、商业模式、内容边界

cheat-on-content
  ├─ Track A：BiP + 历史壳子 = IP 同频 / 品牌厚度
  └─ Track B：张三群像 + 产品获客 + 产品演示 = 转化 / 咨询 / 产品验证

PulseHub
  ↓ 图文获客、关键词、小红书/公众号文案、私域承接

双机 + 飞书 Wiki
  ↓ 本机轻协作，N 卡机器重生产
```

## 4. PulseHub 与 B 轨的边界（本次用户纠正）

PulseHub 更适合发布图文，不适合以张三视角展开视频。

PulseHub 适合做：

- 小红书图文。
- 公众号文章。
- 关键词矩阵。
- 用户痛点语料。
- 爆款结构拆解。
- CTA / 私域话术。
- 数据反馈。

PulseHub 可以喂给 B 轨：

- 关键词。
- 痛点原话。
- 场景语料。
- CTA。
- 私域承接方式。

PulseHub 不替代：

- cheat-on-content 的 B 轨张三视频结构。
- `cheat-predict` 盲预测。
- `cheat-retro` / `cheat-compass-retro` 复盘。
- B 轨 rubric 进化。

## 5. `opc-sop.md` 必写结论

1. `ip-opc-system` 的重点不是新建 B 链路，而是把已经设计但未拍摄的 B 链路纳入每周生产节奏。
2. 每周节奏建议从“只跑 A”切成 `1A + 1B + PulseHub 图文跟随`：
   - A：Build in Public + 历史壳子，维持 IP 同频。
   - B：张三群像 + 产品获客，验证文衡 / 照胆转化。
   - PulseHub：跟随 B 轨主题做小红书 / 公众号图文与私域承接。
3. 若用 PulseHub 的 `outputs/001-开标前10分钟防废标自查.md` 作为第一条 B 轨输入，只能取关键词、痛点、CTA 和产品承接；**不能直接照抄为张三视频脚本**。
4. Track 路由必须写清：
   - A 轨 post-draft review → `cheat-who-for`。
   - B 轨 post-draft review → `cheat-open-source`。
5. 第一优先瓶颈写：**B 轨已设计但未实际拍摄**。

## 6. 常见误判

- ❌ 误判：cheat-on-content 只有历史壳子路线。  
  ✅ 正确：cheat-on-content 已有 A/B 双轨，只是 B 轨还没拍起来。

- ❌ 误判：PulseHub 是 B 轨张三视频主生产器。  
  ✅ 正确：PulseHub 是图文获客和营销资产层；B 轨视频仍由 cheat-on-content 组织。

- ❌ 误判：PulseHub 图文稿可以直接变成 B 轨视频稿。  
  ✅ 正确：PulseHub 图文只能提供关键词 / 痛点 / CTA；B 轨视频必须重新做张三视角、产品演示、预期管理和 `cheat-open-source` 审查。

- ❌ 误判：founder-ip 的 `topic-pool.md` 与 PulseHub 的 `选题库.md` 二选一。  
  ✅ 正确：前者是长期 IP 选题池，后者是短期图文获客选题池；`opc-sop.md` 要写清各自进入 A/B/图文链路的方式。
