/**
 * Per-platform rate limiter for PulseHub.
 *
 * Tracks daily request counts per platform and enforces hard limits.
 * State persists to `~/.pulsehub/state/rate-limits.json`.
 *
 * Limits are based on `docs/risk-control.md` recommendations:
 *   - Small account safety thresholds
 *   - Auto-reset at local midnight
 */

import type { Platform } from '@pulsehub/types'
import { readState, writeState, todayKey, isToday } from './state.js'

// ─── Limits ────────────────────────────────────────────────────────────────

/**
 * Conservative daily request limits per platform.
 * These are for *page views / API calls*, not comments.
 *
 * Source: recipes/<platform>.md "Risk Control Rules" sections.
 */
export const PLATFORM_LIMITS: Record<Platform, number> = {
  rednote: 30,              // Very tight — aggressive anti-bot
  douyin: 20,               // Very tight — signature checks
  bilibili: 80,             // Loose — most permissive major platform
  wechat_official: 50,      // Moderate — public articles are safe
  wechat_channels: 20,      // Tight — requires scan login
  zhihu: 40,                // Moderate — more tolerant than 小红书
}

// ─── State Shape ───────────────────────────────────────────────────────────

interface RateLimitState {
  /** Date key for daily reset. */
  date: string
  /** Per-platform counts. */
  counts: Record<string, number>
}

const EMPTY_STATE: RateLimitState = {
  date: todayKey(),
  counts: {},
}

// ─── Public API ────────────────────────────────────────────────────────────

export interface RateLimitCheck {
  /** Whether the request is allowed. */
  allowed: boolean
  /** Remaining requests today. */
  remaining: number
  /** Daily limit. */
  limit: number
  /** Used today. */
  used: number
  /** When the counter resets (local midnight). */
  resetsAt: Date
}

/**
 * Check if a request to `platform` is allowed without incrementing.
 */
export function checkLimit(platform: Platform): RateLimitCheck {
  const state = loadState()
  const limit = PLATFORM_LIMITS[platform]
  const used = state.counts[platform] ?? 0
  const remaining = Math.max(0, limit - used)

  // Reset time = next local midnight
  const resetsAt = new Date()
  resetsAt.setHours(24, 0, 0, 0)

  return {
    allowed: used < limit,
    remaining,
    limit,
    used,
    resetsAt,
  }
}

/**
 * Record a request to `platform`. Increments the daily counter.
 * Call this *after* a successful request (not before).
 */
export function recordRequest(platform: Platform, count = 1): void {
  const state = loadState()
  state.counts[platform] = (state.counts[platform] ?? 0) + count
  saveState(state)
}

/**
 * Check + record in one call. Returns the check result *before* incrementing.
 * If the request would exceed the limit, does NOT increment.
 */
export function checkAndRecord(platform: Platform): RateLimitCheck {
  const check = checkLimit(platform)
  if (check.allowed) {
    recordRequest(platform)
    return { ...check, used: check.used + 1, remaining: check.remaining - 1 }
  }
  return check
}

/**
 * Get usage for all platforms (for the health dashboard).
 */
export function getAllUsage(): Record<Platform, RateLimitCheck> {
  const platforms = Object.keys(PLATFORM_LIMITS) as Platform[]
  return platforms.reduce((acc, p) => {
    acc[p] = checkLimit(p)
    return acc
  }, {} as Record<Platform, RateLimitCheck>)
}

/**
 * Manually reset a platform's counter (admin action).
 */
export function resetPlatform(platform: Platform): void {
  const state = loadState()
  delete state.counts[platform]
  saveState(state)
}

/**
 * Reset all counters (admin action, or for testing).
 */
export function resetAll(): void {
  saveState({ ...EMPTY_STATE })
}

// ─── Internal ──────────────────────────────────────────────────────────────

function loadState(): RateLimitState {
  const raw = readState<RateLimitState>('rate-limits.json', EMPTY_STATE)
  // Auto-reset if date has changed
  if (!isToday(raw.date)) {
    return { ...EMPTY_STATE }
  }
  return raw
}

function saveState(state: RateLimitState): void {
  writeState('rate-limits.json', { ...state, date: todayKey() })
}
