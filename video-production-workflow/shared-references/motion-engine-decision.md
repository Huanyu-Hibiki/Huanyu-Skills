# Motion Engine Decision（B-roll 生成引擎决策）

所有生成引擎都输出 B-roll，不直接修改主视频时间线。`b-roll-generate` 按“内容需求优先、工具其次”的顺序选择引擎。

## 决策树

```text
需要真实证据、人物、产品或地点？
  ├─ 是 → 先找权威/用户真实素材，不生成伪证据
  └─ 否
      需要一个明确的纸拼贴/半调/物件组装隐喻？
         ├─ 是 → b-roll-generate / 拼贴路线
        └─ 否
            需要跨视频复用、props 参数化或复杂数据/架构？
               ├─ 是 → b-roll-generate / Remotion 路线
              └─ 否
                  需要快速 HTML、字幕同步、标题、UI、转场或浮层？
                     ├─ 是 → b-roll-generate / HyperFrames 路线
                    └─ 否 → 根据成本、可编辑性和视觉风格选择
```

## 工具对照

| 引擎 | 技术形式 | 适合的 B-roll | 主要优点 | 不适合 |
|---|---|---|---|---|
| `b-roll-generate / 拼贴路线` | 图像生成 + Gemini Omni Flash | 半调纸拼贴、编辑风、抽象隐喻、assemble-from-empty | 风格明确，适合一句话转视觉隐喻 | 精确图层编辑、复杂信息图、真实产品 UI |
| `b-roll-generate / Remotion 路线` | React + TypeScript + Remotion | 透明浮层、流程、架构、数据、可复用品牌模板 | 项目化、可复用、props 类型化 | 一次性小标题卡、主视频剪辑 |
| `b-roll-generate / Remotion 规范` | Remotion 技术规则 | 所有 Remotion B-roll 的实现规范 | 统一时间、素材、组件、渲染和 QA 规则 | 独立的选题或审美决策 |
| `b-roll-generate / HyperFrames 路线` | HTML + CSS + GSAP | 标题卡、Kinetic Typography、UI、字幕、转场、快速解释 | HTML 直接预览，迭代快 | 复杂数据组件化、长期维护的大型模板 |
| 真实素材 | 用户素材 / Stock / 官方视频 | 事实、人物、产品、地点、现场和证据 | 真实性和信息可信度高 | 抽象概念、不可拍摄关系 |

## 输出标准

每个生成 slot 至少包含：

```text
<project>/Polished/B-roll/BROLL-001_名称/
├── brief.md
├── style-decision.md
├── prompt/                  # AI / HyperFrames / Remotion 提示词
├── source/                  # 静帧、参考图或工程源
├── out/
│   ├── preview.mp4
│   ├── final.mp4
│   └── final-alpha.mov      # 有透明通道且适用时
├── qa.md
└── notes.md
```

## 混合使用

可以让 HyperFrames 负责标题、字幕和转场，让 Remotion 负责图表和架构，让真实录屏负责证据，让拼贴路线负责概念隐喻。混合时每个 slot 仍然只有一个主引擎，避免互相覆盖和难以复现。
