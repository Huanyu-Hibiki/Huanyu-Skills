# video-fine-cut 执行资源

`video-fine-cut` 是剪映/Filmora GUI 中的人工精剪阶段，负责剪气口、删冗余、调整节奏、音乐、音效和字幕样式。它不应被一个自动脚本替代，否则会绕过用户对表达节奏的判断。

精剪完成后使用：

```text
Sub/master.srt
Polished/fine_cut.mp4
```

然后进入 `b-roll-finder`。如果需要 FFmpeg 预览或 B-roll 装配，调用 `../video-polish/compose_broll.py`。
