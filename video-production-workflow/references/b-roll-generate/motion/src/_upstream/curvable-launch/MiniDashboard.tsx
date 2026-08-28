'use client';

import React, { useEffect } from 'react';
import { useCurrentFrame } from 'remotion';
import { CV } from '../theme';
import { SANS_FAMILY, MONO_FAMILY } from './fonts';
import { SceneGlowSkia } from '../SceneGlowSkia';
import { glowStore, loadPresets } from '../glowStore';
import {
  ArrowUpIcon,
  PlayGlyph,
  FrameBackGlyph,
  FrameForwardGlyph,
  JumpStartGlyph,
  JumpEndGlyph,
  FullscreenGlyph,
  CheckGlyph,
  LogoMark,
} from './icons';

// Frame-driven props. The orchestrator computes these from useCurrentFrame()
// and passes them in. The dashboard is otherwise stateless.
export type MiniDashboardProps = {
  // Composer (bottom input)
  composerText: string;
  composerCursorVisible: boolean;
  sendButtonActive: boolean;

  // Chat messages  -  rendered top-down in order, gap between
  showUserMsg1: boolean;          // "Make me a launch video for Curvable."
  showEarlyThinking: boolean;     // "Thinking..." between user1 and agent intro
  showAgentIntro: boolean;        // "Got it. Pulling your brand  -  share your site?"
  showUrlAsk: boolean;            // URL ask card
  urlInputText: string;
  urlInputCursorVisible: boolean;
  urlSubmitActive: boolean;
  urlSubmitted: boolean;          // After submit, hide submit button / show check
  showAgentLead: boolean;         // "Pulling your brand now."
  brandStage: number;             // 0..8 progressive reveal
  showMidThinking: boolean;       // "Thinking..." between brand reveal and the question
  showAgentVideoQuestion: boolean;
  showUserMsg2: boolean;          // "Yes"
  showThinking: boolean;
  showGenerating: boolean;        // "Generating..." shimmer bubble before video ready
  showVideoReady: boolean;        // "Video ready" success card at end of chat
  hideTransportPill: boolean;     // true once the closing overlay takes over

  // Generation: clips appear one by one during the "Thinking…" phase, and
  // the displayed total time grows with each. By the time all clips are
  // visible, totalFrames matches the closing overlay's display.
  clipLabels: readonly string[];
  clipAppearFrames: readonly number[];
  currentFrame: number;
  generatedClipCount: number;
  projectTotalFrames: number;

  // Vertical scroll offset (px) for the messages area, so latest content
  // stays on screen as more bubbles appear.
  chatScrollOffset: number;

  // Preview glow (matches SceneGlowSkia envelope: 0 = off, 1 = full on)
  glowIntensity: number;

  // Playhead in frames within the preview transport pill.
  previewFrame: number;

  // Typewriter fade  -  when the current frame is inside the composer's or URL
  // input's typing range, each glyph is born in the accent colour and fades
  // to the resting text colour. The parent decides which range is active so
  // the same Composer component handles both prompt and "Yes" typings.
  // Pass null when no typing animation should run.
  composerTypingStart: number | null;
  composerFramesPerChar: number;
  urlTypingStart: number | null;
  urlFramesPerChar: number;
};

// Library typewriter port  -  hard-switch variant. Each glyph stays in
// `primary` for `primaryTail * framesPerChar` frames after its own birth and
// then snaps to `resting`. While typing this means the latest `primaryTail`
// glyphs are always primary; when typing stops, those trailing glyphs age
// out one by one at the same rate the user was typing.
//
// Glow stack while a glyph is in its primary window: two blurred copies of
// the letter sit behind it, ported verbatim from the library text-swap
// preset's orange-flash glow. The glow vanishes the moment the glyph snaps
// to resting.
// Brand-orange accent. Reads from a CSS variable on the nearest ancestor
// so the library Prompt-input wrapper can recolour the typing flash glow,
// composer Send button, dashboard chips, and "Generating video…" pill
// when the global library `primary` is non-orange. Fallback keeps every
// existing LP composition and per-project copy identical.
const TYPE_PRIMARY = 'var(--cv-md-accent, #F04E23)';
const TYPE_RESTING = '#fcfbf8';
const TYPE_PRIMARY_TAIL = 2;
const TYPE_GLOW_SHAPES: { opacity: number; sizeMul: number; blurPx: number }[] = [
  { opacity: 1, sizeMul: 0.98, blurPx: 10 },
  { opacity: 0.32, sizeMul: 1.45, blurPx: 26 },
];

function TypingText({
  text,
  start,
  framesPerChar,
  primary = TYPE_PRIMARY,
  resting = TYPE_RESTING,
  primaryTail = TYPE_PRIMARY_TAIL,
}: {
  text: string;
  start: number;
  framesPerChar: number;
  primary?: string;
  resting?: string;
  primaryTail?: number;
}) {
  const frame = useCurrentFrame();
  const primaryLife = primaryTail * framesPerChar;
  return (
    <>
      {text.split('').map((ch, i) => {
        const bornAt = start + (i + 1) * framesPerChar;
        const isOrange = frame - bornAt < primaryLife;
        const color = isOrange ? primary : resting;
        return (
          <span
            key={i}
            style={{ position: 'relative', display: 'inline-block', whiteSpace: 'pre' }}
          >
            {isOrange &&
              TYPE_GLOW_SHAPES.map((g, gi) => (
                <span
                  key={gi}
                  aria-hidden
                  style={{
                    position: 'absolute',
                    left: '50%',
                    top: '50%',
                    transform: `translate(-50%, -50%) scale(${g.sizeMul})`,
                    color: primary,
                    opacity: g.opacity,
                    filter: g.blurPx > 0 ? `blur(${g.blurPx}px)` : undefined,
                    pointerEvents: 'none',
                    whiteSpace: 'pre',
                    lineHeight: 1,
                  }}
                >
                  {ch}
                </span>
              ))}
            <span style={{ position: 'relative', color, whiteSpace: 'pre' }}>{ch}</span>
          </span>
        );
      })}
    </>
  );
}

// Width is 1440 to mirror a real laptop screen. The orchestrator scales/
// translates this whole component as needed (intro, zoom, etc).
export const MD_WIDTH = 1440;
export const MD_HEIGHT = 900;

// Sidebar dimensions (matches editor's resizable panel defaults).
const SIDE_W = 420;
const HEADER_H = 48; // sidebar header
const COMPOSER_H = 132;

// Position constants the orchestrator uses to aim the camera and the cursor.
// Numbers are dashboard-local pixels.
export const INPUT_CENTER = { x: 14 + (SIDE_W - 28) / 2, y: MD_HEIGHT - 70 };
export const SEND_BTN_CENTER = { x: SIDE_W - 14 - 14 - 16, y: MD_HEIGHT - 38 };

// URL ask card sits in the chat scroll area. With messages at top:
//   header (48) + scroll-pad-top (16) + UserMsg1 (~48) + gap 12
//   + AgentIntro (~28) + gap 12 + UrlAskCard label (25) + gap 10 = ~199
// URL input row center is just below that.
export const URL_ASK_INPUT_CENTER = { x: 16 + (SIDE_W - 32 - 8 - 38) / 2, y: 219 };
export const URL_ASK_SUBMIT_CENTER = { x: SIDE_W - 16 - 19, y: 219 };

// Centers of message bubbles for camera targeting (approximate).
export const USER_MSG1_CENTER = { x: SIDE_W / 2, y: HEADER_H + 16 + 25 };
export const TOP_CHAT_CENTER = { x: SIDE_W / 2, y: HEADER_H + 90 };
export const BRAND_CARD_CENTER = { x: SIDE_W / 2, y: HEADER_H + 16 + 48 + 12 + 28 + 12 + 80 + 12 + 28 + 12 + 200 };
export const VIDEO_QUESTION_CENTER = {
  x: SIDE_W / 2,
  y: HEADER_H + 16 + 48 + 12 + 28 + 12 + 80 + 12 + 28 + 12 + 380 + 12 + 18,
};

// Preview frame in the right panel  -  main panel left edge at SIDE_W, centered
// horizontally inside it. Vertical: 64px top padding + half of the preview
// height. The preview is 16:9 with width = main_width - 48 padding, capped at 980.
export const PREVIEW_FRAME_CENTER = {
  x: SIDE_W + (MD_WIDTH - SIDE_W) / 2,
  y: 64 + Math.round(980 * 9 / 16 / 2),
};

export const MiniDashboard: React.FC<MiniDashboardProps> = (props) => {
  return (
    <div
      style={{
        width: MD_WIDTH,
        height: MD_HEIGHT,
        background: CV.darkBg,
        display: 'flex',
        position: 'relative',
        overflow: 'hidden',
        fontFamily: SANS_FAMILY,
        color: CV.darkText,
      }}
    >
      <Sidebar {...props} />
      <Main
        glowIntensity={props.glowIntensity}
        previewFrame={props.previewFrame}
        hideTransportPill={props.hideTransportPill}
        clipLabels={props.clipLabels}
        clipAppearFrames={props.clipAppearFrames}
        currentFrame={props.currentFrame}
        generatedClipCount={props.generatedClipCount}
        projectTotalFrames={props.projectTotalFrames}
      />
    </div>
  );
};

// ============================================================================
// Sidebar (left panel)
// ============================================================================

function Sidebar(props: MiniDashboardProps) {
  return (
    <aside
      style={{
        width: SIDE_W,
        background: CV.darkBg,
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        borderRight: `1px solid ${CV.darkBorder}`,
      }}
    >
      <SidebarHeader />
      <MessageScroll {...props} />
      <Composer
        composerText={props.composerText}
        composerCursorVisible={props.composerCursorVisible}
        sendButtonActive={props.sendButtonActive}
        typingStart={props.composerTypingStart}
        framesPerChar={props.composerFramesPerChar}
      />
    </aside>
  );
}

function SidebarHeader() {
  return (
    <div
      style={{
        padding: '14px 14px 12px 14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 8,
        minWidth: 320,
      }}
    >
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
        <LogoMark variant="white" size={22} />
        <span
          style={{
            fontSize: 14,
            fontWeight: 600,
            letterSpacing: '-0.2px',
            color: CV.darkText,
          }}
        >
          Curvable launch video
        </span>
      </div>
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 999,
          border: `1px solid ${CV.darkBorder}`,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: CV.darkMutedSubtle,
        }}
      >
        <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M15 18l-6-6 6-6" />
        </svg>
      </div>
    </div>
  );
}

function MessageScroll(props: MiniDashboardProps) {
  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          transform: `translateY(${-props.chatScrollOffset}px)`,
          padding: '16px 16px 8px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          willChange: 'transform',
        }}
      >
        {props.showUserMsg1 && <UserBubble text="Make me a launch video for Curvable." />}
        {props.showEarlyThinking && <ThinkingBubble />}
        {props.showAgentIntro && (
          <AgentBubble text="Got it. Drop your site so I can pull your brand." />
        )}
        {props.showUrlAsk && !props.urlSubmitted && (
          <UrlAskCard
            value={props.urlInputText}
            cursorVisible={props.urlInputCursorVisible}
            submitActive={props.urlSubmitActive}
            submitted={props.urlSubmitted}
            typingStart={props.urlTypingStart}
            framesPerChar={props.urlFramesPerChar}
          />
        )}
        {props.urlSubmitted && <UserBubble text={props.urlInputText} />}
        {props.showAgentLead && <AgentBubble text="Pulling your brand now." />}
        {props.brandStage > 0 && <BrandCard stage={props.brandStage} />}
        {props.showMidThinking && <ThinkingBubble />}
        {props.showAgentVideoQuestion && (
          <AgentBubble text="Should I start?" />
        )}
        {props.showUserMsg2 && <UserBubble text="Yes" />}
        {props.showThinking && <ThinkingBubble />}
        {props.showGenerating && <GeneratingBubble />}
        {props.showVideoReady && <VideoReadyBubble />}
      </div>
    </div>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
      <div
        style={{
          background: CV.darkSurface,
          color: CV.darkText,
          padding: '11px 18px',
          borderRadius: 23,
          fontSize: 16,
          lineHeight: '25px',
          fontWeight: 400,
          whiteSpace: 'pre-wrap',
          maxWidth: '85%',
        }}
      >
        {text}
      </div>
    </div>
  );
}

function AgentBubble({ text }: { text: string }) {
  return (
    <div
      style={{
        fontSize: 16,
        lineHeight: '25px',
        fontWeight: 400,
        color: CV.darkText,
        whiteSpace: 'pre-wrap',
        maxWidth: '90%',
      }}
    >
      {text}
    </div>
  );
}

function ThinkingBubble() {
  return (
    <div
      style={{
        fontSize: 16,
        lineHeight: '25px',
        fontWeight: 500,
        letterSpacing: '-0.1px',
      }}
    >
      <span className="cv-shimmer-text">Thinking...</span>
    </div>
  );
}

function GeneratingBubble() {
  return (
    <div
      style={{
        fontSize: 16,
        lineHeight: '25px',
        fontWeight: 500,
        letterSpacing: '-0.1px',
      }}
    >
      <span className="cv-shimmer-text">Generating...</span>
    </div>
  );
}

// ============================================================================
// URL ask card
// ============================================================================

function UrlAskCard({
  value,
  cursorVisible,
  submitActive,
  submitted,
  typingStart,
  framesPerChar,
}: {
  value: string;
  cursorVisible: boolean;
  submitActive: boolean;
  submitted: boolean;
  typingStart: number | null;
  framesPerChar: number;
}) {
  const isEmpty = value.length === 0;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ fontSize: 16, color: CV.darkText }}>Got a website?</div>
      <div style={{ display: 'flex', gap: 8 }}>
        <div
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            background: CV.darkSurfaceSunken,
            border: `1px solid ${CV.darkBorderStrong}`,
            borderRadius: 999,
            padding: '0 16px',
            height: 38,
            color: isEmpty ? CV.darkMutedSubtle : CV.darkText,
            fontSize: 14,
          }}
        >
          {isEmpty ? (
            'https://yourcompany.com'
          ) : typingStart != null ? (
            <TypingText
              text={value}
              start={typingStart}
              framesPerChar={framesPerChar}
            />
          ) : (
            value
          )}
          {cursorVisible && !isEmpty && (
            <span
              style={{
                display: 'inline-block',
                width: 2,
                height: 16,
                background: TYPE_PRIMARY,
                marginLeft: 1,
                verticalAlign: 'middle',
              }}
            />
          )}
        </div>
        <div
          style={{
            width: 38,
            height: 38,
            borderRadius: 999,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: submitActive || submitted ? TYPE_PRIMARY : CV.darkSurfaceSunken,
            border: submitActive || submitted ? 'none' : `1px solid ${CV.darkBorderStrong}`,
            color: '#fff',
          }}
        >
          {submitActive || submitted ? (
            <CheckGlyph size={14} color="#fff" />
          ) : (
            <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke={CV.darkMutedSubtle} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Brand card  -  progressive reveal driven by `stage`
// ============================================================================

const BRAND_COLORS = ['#F04E23', '#1C1C1C', '#FCFBF8', '#272725', '#CDCAC4', '#D43F17'];
const BRAND_FONTS = [
  { name: 'Geist Sans', family: SANS_FAMILY },
  { name: 'Geist Mono', family: MONO_FAMILY },
  { name: 'Inter', family: 'Inter, system-ui, sans-serif' },
];

function BrandCard({ stage }: { stage: number }) {
  const headerRevealed = stage >= 1;
  const colorsRevealedCount = Math.max(0, Math.min(6, stage - 1));
  const fontsRevealed = stage >= 8;

  return (
    <div
      style={{
        background: CV.darkSurface,
        border: `1px solid ${CV.darkBorderStrong}`,
        borderRadius: 14,
        width: 360,
        overflow: 'hidden',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 14 }}>
        {headerRevealed ? (
          <>
            <span
              style={{
                width: 48,
                height: 48,
                borderRadius: 15,
                background: '#fff',
                color: '#fff',
                fontSize: 22,
                fontWeight: 700,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                lineHeight: 0,
                overflow: 'hidden',
              }}
            >
              <LogoMark variant="black" size={36} tight />
            </span>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: 16, fontWeight: 600, color: CV.darkText }}>Curvable</span>
              <span
                style={{
                  fontSize: 12,
                  color: CV.darkMutedSubtle,
                  fontFamily: MONO_FAMILY,
                }}
              >
                curvable.ai
              </span>
            </div>
          </>
        ) : (
          <>
            <div style={{ width: 48, height: 48, borderRadius: 15, background: '#3a3a37' }} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ width: 110, height: 12, borderRadius: 6, background: '#3a3a37' }} />
              <div style={{ width: 80, height: 10, borderRadius: 6, background: '#3a3a37' }} />
            </div>
          </>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)' }}>
        {BRAND_COLORS.map((c, i) => {
          const revealed = i < colorsRevealedCount;
          return <ColorSwatch key={i} color={revealed ? c : null} />;
        })}
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          background: fontsRevealed ? '#fff' : 'transparent',
        }}
      >
        {BRAND_FONTS.map((f, i) => (
          <FontSwatch key={i} font={fontsRevealed ? f : null} showDivider={fontsRevealed && i > 0} />
        ))}
      </div>
    </div>
  );
}

function ColorSwatch({ color }: { color: string | null }) {
  if (!color) {
    return (
      <div
        style={{
          aspectRatio: '1 / 1',
          background: '#3a3a37',
          opacity: 0.55,
        }}
      />
    );
  }
  const isLight = isLightColor(color);
  return (
    <div
      style={{
        aspectRatio: '1 / 1',
        background: color,
        position: 'relative',
      }}
    >
      <div
        style={{
          position: 'absolute',
          right: 8,
          bottom: 8,
          fontSize: 13,
          fontWeight: 500,
          fontFamily: MONO_FAMILY,
          color: isLight ? 'rgba(0,0,0,0.78)' : 'rgba(255,255,255,0.9)',
        }}
      >
        {color.toUpperCase()}
      </div>
    </div>
  );
}

function FontSwatch({
  font,
  showDivider,
}: {
  font: { name: string; family: string } | null;
  showDivider: boolean;
}) {
  if (!font) {
    return (
      <div
        style={{
          aspectRatio: '1 / 1',
          background: '#3a3a37',
          opacity: 0.55,
        }}
      />
    );
  }
  return (
    <div
      style={{
        aspectRatio: '1 / 1',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderLeft: showDivider ? '1px solid #e6e4dd' : 'none',
        color: '#111',
        fontFamily: font.family,
        fontSize: 22,
        lineHeight: 1,
      }}
    >
      AaBbCc
    </div>
  );
}

function isLightColor(hex: string): boolean {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return r * 0.299 + g * 0.587 + b * 0.114 > 160;
}

// ============================================================================
// Composer
// ============================================================================

function Composer({
  composerText,
  composerCursorVisible,
  sendButtonActive,
  typingStart,
  framesPerChar,
}: {
  composerText: string;
  composerCursorVisible: boolean;
  sendButtonActive: boolean;
  typingStart: number | null;
  framesPerChar: number;
}) {
  const isEmpty = composerText.length === 0;
  return (
    <div style={{ padding: 14, minWidth: 320, background: CV.darkBg }}>
      <div
        style={{
          background: CV.darkSurface,
          border: `1px solid ${CV.darkBorderStrong}`,
          borderRadius: 20,
          padding: '14px 14px 10px 14px',
        }}
      >
        <div
          style={{
            fontSize: 16,
            lineHeight: '24px',
            fontFamily: 'inherit',
            color: isEmpty ? CV.darkMutedSubtle : CV.darkText,
            padding: '4px 4px 8px 4px',
            minHeight: 48,
            whiteSpace: 'pre-wrap',
          }}
        >
          {isEmpty ? (
            'Ask Curvable...'
          ) : typingStart != null ? (
            <TypingText
              text={composerText}
              start={typingStart}
              framesPerChar={framesPerChar}
            />
          ) : (
            composerText
          )}
          {composerCursorVisible && !isEmpty && (
            <span
              style={{
                display: 'inline-block',
                width: 2,
                height: 16,
                background: TYPE_PRIMARY,
                verticalAlign: 'middle',
                marginLeft: 1,
                transform: 'translateY(-1px)',
              }}
            />
          )}
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 999,
              background: sendButtonActive ? TYPE_PRIMARY : 'rgba(255,255,255,0.08)',
              color: sendButtonActive ? '#fff' : CV.darkMutedSubtle,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background 160ms ease, color 160ms ease',
            }}
          >
            <ArrowUpIcon size={14} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main panel  -  preview + transport + timeline
// ============================================================================

function Main({
  glowIntensity,
  previewFrame,
  hideTransportPill,
  clipLabels,
  clipAppearFrames,
  currentFrame,
  generatedClipCount,
  projectTotalFrames,
}: {
  glowIntensity: number;
  previewFrame: number;
  hideTransportPill: boolean;
  clipLabels: readonly string[];
  clipAppearFrames: readonly number[];
  currentFrame: number;
  generatedClipCount: number;
  projectTotalFrames: number;
}) {
  return (
    <main
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        minWidth: 0,
        position: 'relative',
      }}
    >
      <UserPill />
      <div
        style={{
          flex: 1,
          minHeight: 0,
          padding: '64px 24px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
        }}
      >
        <PreviewFrame
          glowIntensity={glowIntensity}
          previewFrame={previewFrame}
          hideTransportPill={hideTransportPill}
          projectTotalFrames={projectTotalFrames}
        />
      </div>
      <Timeline
        clipLabels={clipLabels}
        clipAppearFrames={clipAppearFrames}
        currentFrame={currentFrame}
        generatedClipCount={generatedClipCount}
      />
    </main>
  );
}

function UserPill() {
  return (
    <div style={{ position: 'absolute', top: 16, right: 16, zIndex: 5 }}>
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          padding: '4px 12px 4px 4px',
          borderRadius: 999,
          background: 'rgba(255,255,255,0.05)',
          border: `1px solid ${CV.darkBorder}`,
          color: CV.darkText,
          fontSize: 13,
          fontWeight: 500,
        }}
      >
        <div
          style={{
            width: 26,
            height: 26,
            borderRadius: 999,
            background: 'linear-gradient(135deg, var(--cv-md-accent, #F04E23), var(--cv-md-accent-dark, #b13816))',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: 11,
            fontWeight: 700,
          }}
        >
          T
        </div>
        <span>Tiago</span>
        <svg width={10} height={10} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </div>
    </div>
  );
}

function PreviewFrame({
  glowIntensity,
  previewFrame,
  hideTransportPill,
  projectTotalFrames,
}: {
  glowIntensity: number;
  previewFrame: number;
  hideTransportPill: boolean;
  projectTotalFrames: number;
}) {
  // Load real presets on mount and toggle the glow on/off via the shared
  // glowStore. The actual SceneGlowSkia render lives at canvas level outside
  // the dashboard so the rainbow fills the whole video frame.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const presets = await loadPresets();
      if (cancelled || !presets) return;
      glowStore.set(presets.rainbow);
    })();
    return () => {
      cancelled = true;
    };
  }, []);
  useEffect(() => {
    glowStore.setEnabled(glowIntensity > 0.01);
  }, [glowIntensity]);

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        maxWidth: 980,
        aspectRatio: '16 / 9',
        background: '#000',
        border: `1px solid ${CV.darkBorder}`,
        borderRadius: 18,
        overflow: 'hidden',
        boxShadow: '0 30px 90px -30px rgba(0,0,0,0.8)',
      }}
    >
      {/* Wrapper opacity drives the visible fade so the glow dissolves
          cleanly into the dark frame at the end. The boolean prop just
          gates the shader for performance. */}
      {/* `borderRadius: 'inherit'` is required so the shader picks up the
          frame's 18px corner radius and its rect-glow lines up with the
          rounded clip. Without it the shader draws square corners and the
          frame clips them to round, leaving dark wedges at each corner. */}
      <div style={{ position: 'absolute', inset: 0, opacity: glowIntensity, borderRadius: 'inherit' }}>
        <SceneGlowSkia visible={glowIntensity > 0.01} />
      </div>
      {!hideTransportPill && <TransportPill frame={previewFrame} totalFrames={projectTotalFrames} fps={30} />}
    </div>
  );
}

function VideoReadyBubble() {
  return (
    <div
      style={{
        background: CV.darkSurface,
        border: `1px solid ${CV.darkBorderStrong}`,
        borderRadius: 14,
        maxWidth: '85%',
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '12px 18px',
      }}
    >
      <span
        style={{
          width: 18,
          height: 18,
          borderRadius: 999,
          background: TYPE_PRIMARY,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <CheckGlyph size={10} color="#fff" />
      </span>
      <span style={{ fontSize: 16, lineHeight: '25px', color: CV.darkText, fontWeight: 500 }}>
        Video ready
      </span>
    </div>
  );
}

function TransportPill({
  frame,
  totalFrames,
  fps,
}: {
  frame: number;
  totalFrames: number;
  fps: number;
}) {
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: 14,
        display: 'flex',
        justifyContent: 'center',
        zIndex: 10,
      }}
    >
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          background: 'rgba(20,20,20,0.78)',
          border: '1px solid rgba(255,255,255,0.10)',
          borderRadius: 999,
          padding: '5px 6px',
          backdropFilter: 'blur(12px) saturate(1.1)',
          boxShadow: '0 12px 30px -10px rgba(0,0,0,0.6)',
        }}
      >
        <span
          style={{
            fontFamily: MONO_FAMILY,
            fontSize: 12,
            color: CV.darkText,
            padding: '0 6px 0 10px',
            letterSpacing: '0.02em',
            minWidth: 64,
            textAlign: 'center',
          }}
        >
          {formatTimecode(frame, fps)}
        </span>
        <TransportBtn>
          <JumpStartGlyph />
        </TransportBtn>
        <TransportBtn>
          <FrameBackGlyph />
        </TransportBtn>
        <TransportBtn primary>
          <PlayGlyph />
        </TransportBtn>
        <TransportBtn>
          <FrameForwardGlyph />
        </TransportBtn>
        <TransportBtn>
          <JumpEndGlyph />
        </TransportBtn>
        <span
          style={{
            fontFamily: MONO_FAMILY,
            fontSize: 12,
            color: CV.darkMutedSubtle,
            padding: '0 6px 0 6px',
            letterSpacing: '0.02em',
            minWidth: 64,
            textAlign: 'center',
          }}
        >
          {formatTimecode(totalFrames, fps)}
        </span>
        <TransportBtn>
          <FullscreenGlyph />
        </TransportBtn>
      </div>
    </div>
  );
}

function TransportBtn({ children, primary }: { children: React.ReactNode; primary?: boolean }) {
  return (
    <span
      style={{
        width: primary ? 30 : 26,
        height: primary ? 30 : 26,
        borderRadius: 999,
        background: primary ? '#fff' : 'transparent',
        color: primary ? '#000' : CV.darkText,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {children}
    </span>
  );
}

function formatTimecode(frame: number, fps: number): string {
  const totalSec = Math.floor(frame / fps);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  const f = frame % fps;
  return `${pad2(m)}:${pad2(s)}:${pad2(f)}`;
}
function pad2(n: number) {
  return n < 10 ? `0${n}` : `${n}`;
}

// ============================================================================
// Timeline
// ============================================================================

function Timeline({
  clipLabels,
  clipAppearFrames,
  currentFrame,
  generatedClipCount,
}: {
  clipLabels: readonly string[];
  clipAppearFrames: readonly number[];
  currentFrame: number;
  generatedClipCount: number;
}) {
  return (
    <div style={{ padding: '0 14px 14px 14px' }}>
      <div
        style={{
          background: CV.darkSurface,
          border: `1px solid ${CV.darkBorderStrong}`,
          borderBottom: 'none',
          borderRadius: '14px 14px 0 0',
          height: 150,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          style={{
            height: 18,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <span
            style={{
              width: 44,
              height: 4,
              borderRadius: 999,
              background: 'rgba(255,255,255,0.22)',
            }}
          />
        </div>
        <div style={{ padding: '10px 14px 14px 14px', flex: 1, position: 'relative' }}>
          <TimelineRuler />
          <div style={{ display: 'flex', gap: 4, height: 32, marginTop: 12 }}>
            {clipLabels.map((label, i) => {
              const appearFrame = clipAppearFrames[i] ?? 0;
              const visible = currentFrame >= appearFrame;
              // 10-frame fade-in / slide-in once the clip "lands".
              const t = Math.max(0, Math.min(1, (currentFrame - appearFrame) / 10));
              return (
                <div
                  key={label}
                  style={{
                    flex: 1,
                    background: '#4d4d4a',
                    borderRadius: 9999,
                    padding: '0 12px',
                    display: 'flex',
                    alignItems: 'center',
                    fontSize: 12,
                    color: CV.darkText,
                    fontWeight: 500,
                    letterSpacing: '-0.1px',
                    opacity: visible ? t : 0,
                    transform: visible ? `translateY(${(1 - t) * 8}px)` : 'translateY(8px)',
                  }}
                >
                  {label}
                </div>
              );
            })}
          </div>
          {generatedClipCount > 0 && <Playhead />}
        </div>
      </div>
    </div>
  );
}

function TimelineRuler() {
  const ticks = Array.from({ length: 11 });
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', height: 28, position: 'relative' }}>
      {ticks.map((_, i) => (
        <div key={i} style={{ flex: 1, position: 'relative', height: '100%' }}>
          <div
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              width: 1,
              height: 8,
              background: 'rgba(255,255,255,0.35)',
            }}
          />
          <div
            style={{
              position: 'absolute',
              bottom: 12,
              left: 4,
              fontSize: 10,
              color: CV.darkMutedSubtle,
              fontFamily: MONO_FAMILY,
            }}
          >
            {i}s
          </div>
        </div>
      ))}
    </div>
  );
}

function Playhead() {
  return (
    <div
      style={{
        position: 'absolute',
        top: 22,
        left: '18%',
        width: 1,
        bottom: 0,
        background: TYPE_PRIMARY,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: -7,
          left: '-4.5px',
          width: 10,
          height: 8,
          background: TYPE_PRIMARY,
          clipPath: 'polygon(50% 100%, 0 0, 100% 0)',
        }}
      />
    </div>
  );
}
