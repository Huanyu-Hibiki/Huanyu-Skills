# Export Formats

Use these command templates after replacing `<COMPOSITION_ID>` and `<name>`.

Run commands from:

```text
<视频项目根>\{第X期：视频标题}\edit\remotion\MotionXX_CompositionName\remotion-project\
```

Render to the sibling `..\out\` folder:

```text
<视频项目根>\{第X期：视频标题}\edit\remotion\MotionXX_CompositionName\out\
```

## Studio Preview

```bash
npm run dev
```

## Still Check

```bash
npx remotion still <COMPOSITION_ID> --frame=<FRAME> --scale=0.5
```

## MP4 Insert

Use for full-frame insert clips imported into Filmora.

```bash
npx remotion render <COMPOSITION_ID> ../out/<name>.mp4
```

## Transparent WebM Overlay

Use for transparent overlays when Filmora handles alpha correctly. Transparent WebM requires PNG frames, VP8 or VP9, and `yuva420p` pixel format.

```bash
npx remotion render <COMPOSITION_ID> ../out/<name>.webm --image-format=png --pixel-format=yuva420p --codec=vp8
```

## PNG Sequence

Use when alpha video import is unreliable or frame-level control is needed in the editor.

```bash
npx remotion render <COMPOSITION_ID> ../out/<name>-sequence --sequence --image-format=png
```

## ProRes 4444 Transparent Video

Use for editing-software-friendly transparent video when the editor supports ProRes alpha.
For Jianying/CapCut workflows, prefer this as the primary transparent overlay deliverable even if Windows' built-in player cannot preview it; validate by importing into Jianying or with `ffprobe`, not by Windows playback.

```bash
npx remotion render <COMPOSITION_ID> ../out/<name>.mov --image-format=png --pixel-format=yuva444p10le --codec=prores --prores-profile=4444
```

## Format Selection

- `MP4 insert`: Full-frame explainer, title card, product walkthrough insert.
- `transparent WebM`: Overlay above facecam or OBS.
- `PNG sequence`: Maximum compatibility and frame-level alpha fallback.
- `ProRes 4444`: Primary transparent-overlay workflow for Jianying/CapCut when file size is acceptable.
- `magenta-key MP4`: Fallback only when alpha import or rendering fails; composite over `#ff00ff` and key it out in the editor.
