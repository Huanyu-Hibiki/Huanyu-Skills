# 个人词典（voice-lexicon）

> 复制为 `<项目>/video scripts/lexicon.md` 后维护；跨项目通用的专名放项目根 `voice-lexicon.md`。
>
> - `transcribe.py --lexicon` 读取「专名表」作为 ASR initial-prompt 偏置；
> - `align_to_manuscript.py` 读取「纠错规则」标注 ASR↔文稿偏差；
> - 校对阶段发现的新错词：用户确认后追加到本文件（词典候选回流，下期生效）。

## 专名表（转写一律按此拼写）

- 焕羽（人名，频道名）
- 示例术语（产品名/品牌名/技术名词，逐条一行）

## 纠错规则（听到左边 → 写右边；按上下文替换，不盲替）

- 示例错词 → 示例正词
