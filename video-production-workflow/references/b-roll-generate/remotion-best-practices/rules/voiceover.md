---
name: voiceover
description: Adding AI-generated voiceover to Remotion compositions using TTS
metadata:
  tags: voiceover, audio, tts, speech, calculateMetadata, dynamic duration
---

# Adding AI voiceover to a Remotion composition

Use an explicitly approved TTS tool to generate speech audio per scene, then use [`calculateMetadata`](./calculate-metadata) to dynamically size the composition to match the audio. This reference does not select a provider or require a provider API key.

## Prerequisites

The TTS provider must be selected by the current Agent or the user. Do not add provider-specific API keys to the Skill `.env` unless a concrete integration is implemented and explicitly requested.

Ensure the environment variable is available when running the generation script:

```bash
node --strip-types generate-voiceover.ts
```

## Generating audio with an approved provider

Create a provider-specific script only after the provider has been approved. It should write MP3 files to the `public/` directory so Remotion can access them via `staticFile()`.

The core API call for a single scene:

```ts title="generate-voiceover.ts"
const audioBuffer = await approvedTtsProvider(
  scene.text,
  scene.voice,
);
writeFileSync(`public/voiceover/${compositionId}/${scene.id}.mp3`, audioBuffer);
```

## Dynamic composition duration with calculateMetadata

Use [`calculateMetadata`](./calculate-metadata.md) to measure the [audio durations](./get-audio-duration.md) and set the composition length accordingly.

```tsx
import { CalculateMetadataFunction, staticFile } from "remotion";
import { getAudioDuration } from "./get-audio-duration";

const FPS = 30;

const SCENE_AUDIO_FILES = [
  "voiceover/my-comp/scene-01-intro.mp3",
  "voiceover/my-comp/scene-02-main.mp3",
  "voiceover/my-comp/scene-03-outro.mp3",
];

export const calculateMetadata: CalculateMetadataFunction<Props> = async ({
  props,
}) => {
  const durations = await Promise.all(
    SCENE_AUDIO_FILES.map((file) => getAudioDuration(staticFile(file))),
  );

  const sceneDurations = durations.map((durationInSeconds) => {
    return durationInSeconds * FPS;
  });

  return {
    durationInFrames: Math.ceil(sceneDurations.reduce((sum, d) => sum + d, 0)),
  };
};
```

The computed `sceneDurations` are passed into the component via a `voiceover` prop so the component knows how long each scene should be.

If the composition uses [`<TransitionSeries>`](./transitions.md), subtract the overlap from total duration: [./transitions.md#calculating-total-composition-duration](./transitions.md#calculating-total-composition-duration)

## Rendering audio in the component

See [audio.md](./audio.md) for more information on how to render audio in the component.

## Delaying audio start

See [audio.md#delaying](./audio.md#delaying) for more information on how to delay the audio start.
