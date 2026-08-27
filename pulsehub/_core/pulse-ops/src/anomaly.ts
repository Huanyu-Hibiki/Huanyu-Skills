/**
 * Anomaly detector for PulseHub.
 *
 * Tracks error patterns per platform and automatically pauses
 * when thresholds are hit (captcha, rate-limit responses, auth failures).
 *
 * State persists to `~/.pulsehub/state/anomalies.json`.
 *
 * Pause durations are conservative — better to pause too long than
 * to get an account banned.
 */

import type { Platform } from '@pulsehub/types'
import { readState, writeState } from './state.js'

// ─── Error Types ───────────────────────────────────────────────────────────

export type AnomalyType =
  | 'captcha'           // Slider / image verification triggered
  | 'rate_limit'        // HTTP 429 or platform equivalent
  | 'auth_failure'      // HTTP 401/403 or login redirect
  | 'empty_results'     // Search returns 0 results for normal query
  | 'network_error'     // Timeout / connection refused

export interface AnomalyEvent {
  type: AnomalyType
  platform: Platform
  timestamp: string    // ISO
  details?: string
}

// ─── Pause Durations (milliseconds) ────────────────────────────────────────

/**
 * How long to pause a platform after each anomaly type.
 * Conservative defaults — when in doubt, pause longer.
 */
const PAUSE_DURATIONS: Record<AnomalyType, number> = {
  captcha: 24 * 60 * 60 * 1000,       // 24 hours — strongest signal
  rate_limit: 2 * 60 * 60 * 1000,     // 2 hours — back off and retry
  auth_failure: 12 * 60 * 60 * 1000,  // 12 hours — re-login needed
  empty_results: 1 * 60 * 60 * 1000,  // 1 hour — might be temporary
  network_error: 5 * 60 * 1000,       // 5 minutes — transient
}

// ─── State Shape ───────────────────────────────────────────────────────────

interface AnomalyState {
  /** Recent events (capped at 100). */
  events: AnomalyEvent[]
  /** Currently paused platforms. */
  paused: Record<string, {
    until: string     // ISO timestamp
    reason: AnomalyType
    pausedAt: string  // ISO timestamp
  }>
}

const EMPTY_STATE: AnomalyState = {
  events: [],
  paused: {},
}

const MAX_EVENTS = 100

// ─── Internal state helpers ────────────────────────────────────────────────

function loadState(): AnomalyState {
  return readState<AnomalyState>('anomalies.json', EMPTY_STATE)
}

function saveState(state: AnomalyState): void {
  writeState('anomalies.json', state)
}

// ─── Public API ────────────────────────────────────────────────────────────

export interface PauseStatus {
  paused: boolean
  until?: Date
  reason?: AnomalyType
  pausedAt?: Date
  /** Minutes remaining (if paused). */
  minutesRemaining?: number
}

/**
 * Record an anomaly event. If thresholds are hit, auto-pause the platform.
 */
export function recordAnomaly(
  platform: Platform,
  type: AnomalyType,
  details?: string,
): PauseStatus {
  const state = loadState()

  // Record event
  const event: AnomalyEvent = {
    type,
    platform,
    timestamp: new Date().toISOString(),
    details,
  }
  state.events.unshift(event)
  if (state.events.length > MAX_EVENTS) {
    state.events = state.events.slice(0, MAX_EVENTS)
  }

  // Auto-pause based on anomaly type
  const duration = PAUSE_DURATIONS[type]
  const until = new Date(Date.now() + duration)
  state.paused[platform] = {
    until: until.toISOString(),
    reason: type,
    pausedAt: new Date().toISOString(),
  }

  saveState(state)

  return {
    paused: true,
    until,
    reason: type,
    pausedAt: new Date(),
    minutesRemaining: Math.round(duration / 60_000),
  }
}

/**
 * Check if a platform is currently paused.
 */
export function isPaused(platform: Platform): PauseStatus {
  const state = loadState()
  const entry = state.paused[platform]

  if (!entry) {
    return { paused: false }
  }

  const until = new Date(entry.until)
  if (until.getTime() <= Date.now()) {
    // Pause expired — clean up
    delete state.paused[platform]
    saveState(state)
    return { paused: false }
  }

  return {
    paused: true,
    until,
    reason: entry.reason,
    pausedAt: new Date(entry.pausedAt),
    minutesRemaining: Math.round((until.getTime() - Date.now()) / 60_000),
  }
}

/**
 * Manually resume a paused platform (admin action).
 */
export function resume(platform: Platform): void {
  const state = loadState()
  delete state.paused[platform]
  saveState(state)
}

/**
 * Get all paused platforms (for the health dashboard).
 */
export function getAllPaused(): Record<Platform, PauseStatus> {
  const platforms: Platform[] = ['bilibili', 'douyin', 'rednote', 'wechat_official', 'wechat_channels', 'zhihu']
  return platforms.reduce((acc, p) => {
    acc[p] = isPaused(p)
    return acc
  }, {} as Record<Platform, PauseStatus>)
}

/**
 * Get recent anomaly events (for debugging / health dashboard).
 */
export function getRecentEvents(limit = 20): AnomalyEvent[] {
  const state = loadState()
  return state.events.slice(0, limit)
}

/**
 * Clear all anomaly state (for testing or admin reset).
 */
export function clearAll(): void {
  saveState({ ...EMPTY_STATE })
}
