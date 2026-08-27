/**
 * Engagement scoring logic.
 *
 * Converts detected signals + publication time + platform into a score
 * (high / medium / low) with a human-readable reason.
 */

import type { EngagementScore, Platform } from '@pulsehub/types'
import type { KeywordDetectionResult } from './detector.js'

interface ScoringInput {
  signals: KeywordDetectionResult
  publishedAt: Date | null
  platform: Platform
}

export interface ScoringResult {
  score: EngagementScore
  reason: string
}

// Per-platform decay curves (in minutes). After this window, even high-signal
// content is downgraded because engagement value drops.
const PLATFORM_WINDOWS: Record<Platform, { high: number, medium: number, low: number }> = {
  // 小红书/抖音 decay fastest — comments in first 30 min get 10x visibility
  rednote: { high: 30, medium: 180, low: 1440 },
  douyin: { high: 30, medium: 120, low: 720 },

  // B站 decays slower — long-form content has 24h+ tail
  bilibili: { high: 360, medium: 1440, low: 4320 },

  // WeChat / Zhihu have very long tails — week-long windows
  wechat_official: { high: 1440, medium: 4320, low: 10080 },
  wechat_channels: { high: 180, medium: 720, low: 1440 },
  zhihu: { high: 1440, medium: 4320, low: 10080 }, // answers rank for years
}

/**
 * Compute engagement score based on signals + time + platform.
 *
 * The algorithm is intentionally simple and explainable:
 *   1. Purchase intent → strongest boost
 *   2. Question intent → medium boost
 *   3. Complaint → negative signal (downgrade unless about competitor)
 *   4. Time window per platform modulates the above
 */
export function scoreOpportunity(input: ScoringInput): ScoringResult {
  const { signals, publishedAt, platform } = input
  const windows = PLATFORM_WINDOWS[platform]

  // Compute age (null = unknown, treat as fresh for scoring)
  const ageMin = publishedAt
    ? (Date.now() - publishedAt.getTime()) / 60_000
    : 0

  // Detect signals
  const hasPurchase = signals.matched.purchase.length > 0
  const hasQuestion = signals.matched.question.length > 0
  const hasComplaint = signals.matched.complaint.length > 0

  const signalParts: string[] = []
  if (hasPurchase) signalParts.push(`purchase(${signals.matched.purchase.join(',')})`)
  if (hasQuestion) signalParts.push(`question(${signals.matched.question.join(',')})`)
  if (hasComplaint) signalParts.push(`complaint(${signals.matched.complaint.join(',')})`)

  const ageDesc = publishedAt
    ? ageMin < 60 ? `${Math.round(ageMin)}min ago`
    : ageMin < 1440 ? `${Math.round(ageMin / 60)}h ago`
    : `${Math.round(ageMin / 1440)}d ago`
  : 'unknown age'

  // Scoring logic — order matters (highest first)
  if (hasComplaint && !hasPurchase && !hasQuestion) {
    return {
      score: 'low',
      reason: `Complaint signal without purchase/question — likely negative sentiment. ${ageDesc}.`,
    }
  }

  if (hasPurchase && ageMin <= windows.high) {
    return {
      score: 'high',
      reason: `Strong purchase intent within ${windows.high}min window for ${platform}. Signals: ${signalParts.join('; ')}. ${ageDesc}.`,
    }
  }

  if (hasPurchase && ageMin <= windows.medium) {
    return {
      score: 'medium',
      reason: `Purchase intent but past peak window. Signals: ${signalParts.join('; ')}. ${ageDesc}.`,
    }
  }

  if (hasQuestion && ageMin <= windows.high) {
    return {
      score: 'medium',
      reason: `Question intent within fresh window. Signals: ${signalParts.join('; ')}. ${ageDesc}.`,
    }
  }

  if ((hasPurchase || hasQuestion) && ageMin <= windows.low) {
    return {
      score: 'low',
      reason: `Signal present but past engagement window. Signals: ${signalParts.join('; ')}. ${ageDesc}.`,
    }
  }

  // Default
  return {
    score: 'low',
    reason: `No strong signals detected${signals.matched.purchase.length === 0 && signals.matched.question.length === 0 ? '' : ` (only: ${signalParts.join('; ')})`}. ${ageDesc}.`,
  }
}

/** Helper: how many minutes until the high-value window closes (negative if already closed). */
export function minutesUntilWindowCloses(platform: Platform, publishedAt: Date): number {
  const windows = PLATFORM_WINDOWS[platform]
  const ageMin = (Date.now() - publishedAt.getTime()) / 60_000
  return windows.high - ageMin
}
