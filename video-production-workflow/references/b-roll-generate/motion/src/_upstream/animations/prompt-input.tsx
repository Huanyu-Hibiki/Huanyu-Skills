'use client';

// LP-OWNED prompt-input scene. Recreates the cursor-types-into-composer beat
// from the curvable-launch composition (frames ~200-340 of the legacy edit)
// in a self-contained, square-friendly form for the LP tile.
//
// What's inside:
//   - BulbBg behind, looping continuously for the floating background.
//   - MiniDashboard imported from the curvable-launch seed (we don't fork it
//     here; if the LP needs to diverge from the seed dashboard, fork later).
//   - Cursor3D overlaid, parked at the composer input while typing happens
//     and then flying to the send button at the end of the typing window.
//   - A 3D perspective wrapper exposing tiltX/tiltY/tiltZ/scale/perspective
//     so the sandbox can dial the camera angle live.
//
// The MiniDashboard takes ~20 props. For this scene we only animate the
// composer; every other timeline flag is false so the dashboard renders its
// empty / pre-send state. The composer's TypingText helper inside the
// dashboard does the typewriter when we set composerText + composerTypingStart.

import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import {
  MiniDashboard,
  MD_WIDTH,
  MD_HEIGHT,
  INPUT_CENTER,
  SEND_BTN_CENTER,
} from '../curvable-launch/MiniDashboard';
import { Cursor3D } from '../Cursor3D';

export type PromptInputProps = {
  typingText: string;
  framesPerChar: number;
  typingStartFrame: number;
  holdAfterTypingFrames: number;
  loopFrames: number;

  // 3D pose.
  perspective: number;
  tiltX: number;
  tiltY: number;
  tiltZ: number;
  dashboardScale: number;
  dashboardOffsetX: number;
  dashboardOffsetY: number;
  dashboardBorderRadius: number;
  // Gentle vertical bob on the dashboard (and the cursor with it) so the
  // panel feels like it's floating in front of the bulb. Amplitude in px,
  // period in frames.
  floatAmplitude: number;
  floatPeriodFrames: number;


  // Background.
  background: string;
  bulbPrimary: string;
  bulbPeakRise: number;
  bulbSpeed: number;
  // Horizontal scale multiplier applied to the bulb wrapper. The bulb's own
  // polygons are fixed-width inside the seed, so we stretch the rendered
  // output via CSS instead of forking the composition geometry.
  bulbWidth: number;

  // Cursor.
  showCursor: boolean;
  cursorScale: number;
  // Cursor 3D pose  -  explicit tilt + extrusion depth. The cursor is rendered
  // inside the dashboard's preserve-3d tree, so these tilts compose with the
  // dashboard's rotateX/Y to position the cursor in the same 3D space.
  cursorTiltX: number;
  cursorTiltY: number;
  cursorTiltZ: number;
  cursorDepth: number;
  // All cursor coordinates are in dashboard-local pixels (MD_WIDTH x MD_HEIGHT).
  cursorOffscreenX: number;
  cursorOffscreenY: number;
  cursorIdleX: number;
  cursorIdleY: number;
  cursorSendX: number;
  cursorSendY: number;
  cursorFlyInDurationFrames: number;
  cursorClickInputDurationFrames: number;
  cursorFlyToSendDurationFrames: number;
  cursorClickSendDurationFrames: number;
  // After the send click, the cursor flies BACK to cursorOffscreenX/Y over
  // this duration instead of fading. The dashboard is untouched.
  cursorFlyOutDurationFrames: number;
  cursorClickShrink: number; // smallest scale at click
};

// Defaults baked from the user-signed-off JSON (the camera pose, scale, and
// cursor positions you dialed in on the sandbox). Cross-referenced against
// INPUT_CENTER/SEND_BTN_CENTER so the seed values stay traceable.
export const PromptInputDefaults: PromptInputProps = {
  typingText: 'Make me a launch video for Curvable.',
  framesPerChar: 2,
  typingStartFrame: 32,
  holdAfterTypingFrames: 0,
  loopFrames: 160,

  perspective: 1400,
  tiltX: 17,
  tiltY: 27,
  tiltZ: -3,
  dashboardScale: 1.65,
  dashboardOffsetX: 785,
  dashboardOffsetY: -570,
  dashboardBorderRadius: 24,
  floatAmplitude: 18,
  floatPeriodFrames: 180,

  background: '#0d0d0d',
  bulbPrimary: '#DC3A1A',
  bulbPeakRise: 11,
  bulbSpeed: 1,
  bulbWidth: 1.4,

  showCursor: true,
  cursorScale: 0.7,
  cursorTiltX: 24,
  cursorTiltY: -14.5,
  cursorTiltZ: 26,
  cursorDepth: 6,
  cursorOffscreenX: 385,
  cursorOffscreenY: 1050,
  cursorIdleX: 110,
  cursorIdleY: 884,
  cursorSendX: 238,
  cursorSendY: 906,
  cursorFlyInDurationFrames: 26,
  cursorClickInputDurationFrames: 8,
  cursorFlyToSendDurationFrames: 18,
  cursorClickSendDurationFrames: 8,
  cursorFlyOutDurationFrames: 26,
  cursorClickShrink: 0.78,
};

// Silence unused-import warnings for the constants that are now only referenced
// in the comments above (kept imported so they're easy to see during edits).
void INPUT_CENTER;
void SEND_BTN_CENTER;

export const PromptInputMeta = {
  width: 1080,
  height: 1080,
  fps: 30,
};

export const computePromptInputDuration = (
  p: Pick<PromptInputProps, 'loopFrames' | 'typingText' | 'framesPerChar' | 'typingStartFrame' | 'holdAfterTypingFrames'>,
): number => {
  // Allow either an explicit loopFrames floor or the natural length needed
  // for typing + hold, whichever is greater.
  const typingFrames = p.typingText.length * p.framesPerChar;
  const natural = p.typingStartFrame + typingFrames + p.holdAfterTypingFrames + 30;
  return Math.max(p.loopFrames, natural);
};

// MiniDashboard's native size. Imported from the seed so we stay in sync if
// the dashboard ever resizes.
const DASH_W = MD_WIDTH;
const DASH_H = MD_HEIGHT;

export const PromptInput: React.FC<PromptInputProps> = (props) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  const totalFrames = computePromptInputDuration(props);
  const localFrame = ((frame % totalFrames) + totalFrames) % totalFrames;

  const typingFrames = props.typingText.length * props.framesPerChar;
  const typingEnd = props.typingStartFrame + typingFrames;

  // Send fires at the smallest frame of the send-click (V-shape midpoint), so
  // the message bubble + composer reset visually pop on the click  -  matches the
  // legacy curvable-launch timing (showUserMsg1Frame === cursorClick2 smallest).
  const sendClickStart = typingEnd + props.cursorFlyToSendDurationFrames;
  const sendFiresFrame = sendClickStart + Math.floor(props.cursorClickSendDurationFrames / 2);
  const sent = localFrame >= sendFiresFrame;

  const composerText = (() => {
    if (sent) return '';
    if (localFrame < props.typingStartFrame) return '';
    if (localFrame >= typingEnd) return props.typingText;
    const charsTyped = Math.max(
      0,
      Math.floor((localFrame - props.typingStartFrame) / props.framesPerChar),
    );
    return props.typingText.slice(0, charsTyped);
  })();
  const sendActive = composerText.length > 0;

  const cursorPos = useMemo3DCursor(localFrame, props, typingEnd);

  // Snap float period to an integer division of totalFrames so the bob
  // wraps cleanly at the loop boundary.
  const floatCycles = Math.max(
    1,
    Math.round(totalFrames / Math.max(1, props.floatPeriodFrames)),
  );
  const effectiveFloatPeriod = totalFrames / floatCycles;

  const floatY =
    props.floatAmplitude *
    Math.sin((2 * Math.PI * localFrame) / effectiveFloatPeriod);



  return (
    <AbsoluteFill style={{ background: 'transparent', overflow: 'hidden' }}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width,
          height,
          perspective: `${props.perspective}px`,
          perspectiveOrigin: '50% 45%',
        }}
      >
        {/* OUTER wrapper  -  owns the 3D pose and the float bob. No overflow
            clip here so the cursor (a sibling of the clipped dashboard
            below) can extend past the dashboard rectangle when it flies in
            from off-screen. */}
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            width: DASH_W,
            height: DASH_H,
            transformStyle: 'preserve-3d',
            transform: [
              `translate(-50%, -50%)`,
              `translate(${props.dashboardOffsetX}px, ${props.dashboardOffsetY + floatY}px)`,
              `rotateX(${props.tiltX}deg)`,
              `rotateY(${props.tiltY}deg)`,
              `rotateZ(${props.tiltZ}deg)`,
              `scale(${props.dashboardScale})`,
            ].join(' '),
          }}
        >
          {/* INNER wrapper  -  just the dashboard, clipped to rounded corners. */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              borderRadius: props.dashboardBorderRadius,
              overflow: 'hidden',
            }}
          >
            <MiniDashboard
              composerText={composerText}
              composerCursorVisible={false}
              sendButtonActive={sendActive}
              showUserMsg1={sent}
              showEarlyThinking={false}
              showAgentIntro={false}
              showUrlAsk={false}
              urlInputText=""
              urlInputCursorVisible={false}
              urlSubmitActive={false}
              urlSubmitted={false}
              showAgentLead={false}
              brandStage={0}
              showMidThinking={false}
              showAgentVideoQuestion={false}
              showUserMsg2={false}
              showThinking={false}
              showGenerating={false}
              showVideoReady={false}
              hideTransportPill={false}
              clipLabels={[]}
              clipAppearFrames={[]}
              currentFrame={localFrame}
              generatedClipCount={0}
              projectTotalFrames={300}
              chatScrollOffset={0}
              glowIntensity={0}
              previewFrame={0}
              composerTypingStart={props.typingStartFrame}
              composerFramesPerChar={props.framesPerChar}
              urlTypingStart={null}
              urlFramesPerChar={2}
            />
          </div>

          {/* Cursor lives OUTSIDE the clipped wrapper but inside the 3D pose
              wrapper, so it inherits the tilt/scale/float but isn't clipped
              by the dashboard's rounded rect. */}
          {props.showCursor && (
            <Cursor3D
              x={cursorPos.x}
              y={cursorPos.y}
              scale={cursorPos.scale * props.cursorScale}
              tiltX={props.cursorTiltX}
              tiltY={props.cursorTiltY}
              tiltZ={props.cursorTiltZ}
              depth={props.cursorDepth}
            />
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// Cursor lifecycle (relative to localFrame inside the loop):
//   1. flyIn        -  offscreen -> idle (composer input)        ends just before clickInput
//   2. clickInput   -  scale dip + rebound on the input            ends AT typingStartFrame
//   3. typing       -  cursor parked at idle while characters land
//   4. flyToSend    -  idle -> send button
//   5. clickSend    -  scale dip + rebound on send
//   6. flyOut       -  send -> offscreen (over cursorFlyOutDurationFrames)
//   7. hold         -  sits at offscreen through the rest of the loop
//
// flyIn and clickInput are positioned BEHIND typingStartFrame so the input
// click visually triggers typing. flyToSend + clickSend run AFTER typingEnd.
// flyOut replaces the previous opacity fade so the dashboard stays untouched.
function useMemo3DCursor(
  localFrame: number,
  p: PromptInputProps,
  typingEnd: number,
): { x: number; y: number; scale: number } {
  const clickInputEnd = p.typingStartFrame;
  const clickInputStart = clickInputEnd - p.cursorClickInputDurationFrames;
  const flyInEnd = clickInputStart;
  const flyInStart = Math.max(0, flyInEnd - p.cursorFlyInDurationFrames);

  const flyToSendStart = typingEnd;
  const flyToSendEnd = flyToSendStart + p.cursorFlyToSendDurationFrames;
  const clickSendStart = flyToSendEnd;
  const clickSendEnd = clickSendStart + p.cursorClickSendDurationFrames;

  // 1. Fly in.
  if (localFrame < flyInStart) {
    return { x: p.cursorOffscreenX, y: p.cursorOffscreenY, scale: 1 };
  }
  if (localFrame < flyInEnd) {
    const t = (localFrame - flyInStart) / Math.max(1, p.cursorFlyInDurationFrames);
    const eased = t * t * (3 - 2 * t);
    return {
      x: p.cursorOffscreenX + (p.cursorIdleX - p.cursorOffscreenX) * eased,
      y: p.cursorOffscreenY + (p.cursorIdleY - p.cursorOffscreenY) * eased,
      scale: 1,
    };
  }

  // 2. Click input  -  V-shaped scale dip across the full click duration.
  if (localFrame < clickInputEnd) {
    return {
      x: p.cursorIdleX,
      y: p.cursorIdleY,
      scale: vClickScale(localFrame - clickInputStart, p.cursorClickInputDurationFrames, p.cursorClickShrink),
    };
  }

  // 3. Typing  -  parked at idle.
  if (localFrame < flyToSendStart) {
    return { x: p.cursorIdleX, y: p.cursorIdleY, scale: 1 };
  }

  // 4. Fly to send.
  if (localFrame < flyToSendEnd) {
    const t = (localFrame - flyToSendStart) / Math.max(1, p.cursorFlyToSendDurationFrames);
    const eased = t * t * (3 - 2 * t);
    return {
      x: p.cursorIdleX + (p.cursorSendX - p.cursorIdleX) * eased,
      y: p.cursorIdleY + (p.cursorSendY - p.cursorIdleY) * eased,
      scale: 1,
    };
  }

  // 5. Click send.
  if (localFrame < clickSendEnd) {
    return {
      x: p.cursorSendX,
      y: p.cursorSendY,
      scale: vClickScale(localFrame - clickSendStart, p.cursorClickSendDurationFrames, p.cursorClickShrink),
    };
  }

  // 6. Fly out  -  back to the offscreen position over cursorFlyOutDurationFrames.
  const flyOutStart = clickSendEnd;
  const flyOutEnd = flyOutStart + p.cursorFlyOutDurationFrames;
  if (localFrame < flyOutEnd) {
    const t = (localFrame - flyOutStart) / Math.max(1, p.cursorFlyOutDurationFrames);
    const eased = t * t * (3 - 2 * t);
    return {
      x: p.cursorSendX + (p.cursorOffscreenX - p.cursorSendX) * eased,
      y: p.cursorSendY + (p.cursorOffscreenY - p.cursorSendY) * eased,
      scale: 1,
    };
  }

  // 7. Hold off-screen.
  return { x: p.cursorOffscreenX, y: p.cursorOffscreenY, scale: 1 };
}

function vClickScale(localFrame: number, totalFrames: number, shrink: number): number {
  if (totalFrames <= 0) return 1;
  const half = totalFrames / 2;
  if (localFrame <= half) {
    const t = localFrame / Math.max(1, half);
    return 1 - (1 - shrink) * t;
  }
  const t = (localFrame - half) / Math.max(1, totalFrames - half);
  return shrink + (1 - shrink) * t;
}
