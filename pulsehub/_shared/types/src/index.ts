/**
 * @pulsehub/types
 *
 * Shared TypeScript contracts used across PulseHub apps, packages, and skills.
 * See ARCHITECTURE.md §5 Data Contracts for the rationale behind each shape.
 */

// ──────────────────────────────────────────────────────────────────────────
// Platform Identifier
// ──────────────────────────────────────────────────────────────────────────

export const PLATFORMS = [
  'bilibili',
  'douyin',
  'rednote',
  'wechat_official',
  'wechat_channels',
  'zhihu',
] as const

export type Platform = (typeof PLATFORMS)[number]

// ──────────────────────────────────────────────────────────────────────────
// Stage 2 Output: ResolvedLink
// ──────────────────────────────────────────────────────────────────────────

/**
 * Output of `pulse-resolve`. A canonical representation of any social-media URL.
 */
export interface ResolvedLink {
  /** Target platform. */
  platform: Platform
  /** Platform-native work ID (BV number, note ID, etc.). */
  workId: string
  /** Canonical, clickable URL. May include tokens (e.g., RedNote xsec_token). */
  url: string
  /** The original URL the user provided (before normalization). */
  originalLink: string
  /** Tokens that must be preserved when sharing the URL (e.g., `xsec_token`). */
  token?: Record<string, string>
  /** ISO timestamp when the resolution happened. */
  resolvedAt: string
}

// ──────────────────────────────────────────────────────────────────────────
// Stage 3 Output: Opportunity
// ──────────────────────────────────────────────────────────────────────────

export interface OpportunityMetadata {
  title?: string
  description?: string
  author?: string
  authorUid?: string
  publishedAt?: string
  durationSec?: number
  thumbnailUrl?: string
  tags?: string[]
}

export interface OpportunitySignals {
  /** Strong purchase-intent language detected (求链接 / 怎么买 / 价格). */
  purchaseIntent: boolean
  /** Question-style content (求推荐 / 怎么做). */
  questionIntent: boolean
  /** Complaint or dissatisfaction with a competitor. */
  complaint: boolean
  /** All keywords that matched, for transparency. */
  matchedKeywords: string[]
}

export type EngagementScore = 'high' | 'medium' | 'low'

export interface Opportunity {
  /** The resolved link this opportunity refers to. */
  link: ResolvedLink
  /** Metadata fetched from the platform or yt-dlp. */
  metadata: OpportunityMetadata
  /** Signal detection results. */
  signals: OpportunitySignals
  /** AI-assigned engagement value. */
  score: EngagementScore
  /** Human-readable reason for the score. */
  scoreReason: string
  /** ISO timestamp when enrichment completed. */
  enrichedAt: string
}

// ──────────────────────────────────────────────────────────────────────────
// Stage 4 Output: Report
// ──────────────────────────────────────────────────────────────────────────

export interface ReportEntry {
  opportunity: Opportunity
  /** Suggested comment angle (user rewrites before posting). */
  suggestedAngle: string
  /** Best-comment window in minutes from publish time. */
  bestWindowMin: number
  /** Why this opportunity was included in the report. */
  inclusionReason: string
}

export interface Report {
  generatedAt: string
  query: string
  totalFound: number
  high: ReportEntry[]
  medium: ReportEntry[]
  low: ReportEntry[]
}

// ──────────────────────────────────────────────────────────────────────────
// Discovery Intent (Stage 1 input)
// ──────────────────────────────────────────────────────────────────────────

export type DiscoveryMode =
  | 'topic_search' // Find posts about a topic
  | 'competitor_watch' // Watch a specific account
  | 'own_comments' // Monitor comments on your own posts
  | 'trending' // Industry hot topics

export interface DiscoveryIntent {
  mode: DiscoveryMode
  platform: Platform
  /** Search query, competitor handle, etc., depending on mode. */
  target: string
  /** Maximum number of candidates to discover. */
  limit: number
  /** Optional time window (only consider posts newer than this). */
  since?: string
}
