# Implementation Plan Template

Use this before writing code. Wait for user confirmation unless they explicitly asked for direct implementation.

```md
# Implementation Plan

- **Motion Request ID**: Motion 01
- **Video Project Folder**: `D:\work\OPC\videos\{第X期：视频标题}`
- **Material Workspace**: `edit\remotion\Motion01_MultiAgentResearchFlow\`
- **Remotion Project Path**: `edit\remotion\Motion01_MultiAgentResearchFlow\remotion-project\`
- **Render Output Path**: `edit\remotion\Motion01_MultiAgentResearchFlow\out\`
- **Composition Name**: MultiAgentResearchFlow
- **Purpose**: Explain multi-AI collaborative research flow
- **Format**: MP4 insert / transparent WebM overlay / PNG sequence / ProRes 4444
- **Resolution / FPS**: 1920x1080, 30fps
- **Duration**: 9s

## Timeline Plan

- 0.0-1.0s: Central task card appears
- 1.0-3.0s: AI nodes branch outward
- 3.0-6.5s: Report cards generate and move inward
- 6.5-9.0s: Final market report card resolves

## Layout Plan

- Full-frame insert / transparent overlay
- Key text inside title-safe area
- Avoid covering facecam or OBS input area if overlay

## Props Design

- `title`
- `labels`
- `accentColor`
- `nodeGap`
- `glowIntensity`
- `animationSpeed`
- `showGrid`

## Data Source

- `motion_request_list.md`
- Optional request data in `src/data/<request>.ts`

## Library Choices

- Default: React + SVG + Remotion built-ins
- New dependencies: None / proposed dependency with reason

## Export Commands

- Studio preview
- Still check
- MP4 insert
- Transparent WebM
- PNG sequence
- ProRes 4444 if needed

## Risks / Assumptions

- List unclear timing, missing assets, logo availability, font requirements, or alpha-channel constraints.
```
