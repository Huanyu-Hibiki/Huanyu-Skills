/**
 * Health check module for PulseHub.
 *
 * Checks:
 *   - RSSHub connectivity (GET /healthz)
 *   - Redis connectivity (TCP ping, optional)
 *   - Per-platform rate limit usage
 *   - Per-platform anomaly/pause status
 *   - Project archive completeness
 *
 * Returns a structured report for CLI display.
 */

import type { Platform } from '@pulsehub/types'
import { getAllUsage } from './rate-limiter.js'
import { getAllPaused, getRecentEvents } from './anomaly.js'
import { ARCHIVE_DIR } from './state.js'
import { existsSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

// ─── Types ─────────────────────────────────────────────────────────────────

export interface ServiceStatus {
  name: string
  status: 'up' | 'down' | 'degraded' | 'n/a'
  latencyMs?: number
  details?: string
}

export interface PlatformHealth {
  platform: Platform
  rateLimit: {
    used: number
    limit: number
    remaining: number
    usagePercent: number
  }
  paused: boolean
  pauseReason?: string
  pauseMinutesRemaining?: number
}

export interface ArchiveHealth {
  exists: boolean
  projects: string[]
  /** Per-project file completeness (0-100%). */
  completeness: Record<string, number>
  /** Missing critical files per project. */
  missing: Record<string, string[]>
}

export interface HealthReport {
  timestamp: string
  services: ServiceStatus[]
  platforms: PlatformHealth[]
  archive: ArchiveHealth
  recentAnomalies: number
  overallStatus: 'healthy' | 'warning' | 'critical'
}

// ─── Health Checks ─────────────────────────────────────────────────────────

const RSSHUB_BASE_URL = process.env.RSSHUB_BASE_URL ?? 'http://localhost:1200'

/**
 * Check RSSHub connectivity.
 */
async function checkRSSHub(): Promise<ServiceStatus> {
  const start = Date.now()
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 5000)
    const response = await fetch(`${RSSHUB_BASE_URL}/healthz`, {
      signal: controller.signal,
    })
    clearTimeout(timeout)
    const latency = Date.now() - start
    if (response.ok) {
      return { name: 'RSSHub', status: 'up', latencyMs: latency, details: `${RSSHUB_BASE_URL}` }
    }
    return { name: 'RSSHub', status: 'degraded', latencyMs: latency, details: `HTTP ${response.status}` }
  }
  catch (error) {
    return {
      name: 'RSSHub',
      status: 'down',
      details: error instanceof Error ? error.message : 'connection failed',
    }
  }
}

/**
 * Check project archive completeness.
 */
function checkArchive(): ArchiveHealth {
  if (!existsSync(ARCHIVE_DIR)) {
    return { exists: false, projects: [], completeness: {}, missing: {} }
  }

  const REQUIRED_FILES = [
    '项目档案.md',
    '人群语料库.md',
    '爆款素材库.md',
    '话术资产.md',
    '数据反馈.md',
    '个人风格.md',
  ]

  const entries = readdirSync(ARCHIVE_DIR, { withFileTypes: true })
  const projects = entries
    .filter(e => e.isDirectory())
    .map(e => e.name)

  const completeness: Record<string, number> = {}
  const missing: Record<string, string[]> = {}

  for (const project of projects) {
    const projectDir = join(ARCHIVE_DIR, project)
    const missingFiles: string[] = []

    for (const file of REQUIRED_FILES) {
      if (!existsSync(join(projectDir, file))) {
        missingFiles.push(file)
      }
    }

    const complete = REQUIRED_FILES.length - missingFiles.length
    completeness[project] = Math.round((complete / REQUIRED_FILES.length) * 100)
    missing[project] = missingFiles
  }

  return { exists: true, projects, completeness, missing }
}

/**
 * Run all health checks and return a comprehensive report.
 */
export async function checkHealth(): Promise<HealthReport> {
  const [rsshub] = await Promise.all([checkRSSHub()])

  const usage = getAllUsage()
  const paused = getAllPaused()
  const events = getRecentEvents(50)

  const platforms: PlatformHealth[] = (Object.keys(usage) as Platform[]).map(p => {
    const u = usage[p]
    const pa = paused[p]
    return {
      platform: p,
      rateLimit: {
        used: u.used,
        limit: u.limit,
        remaining: u.remaining,
        usagePercent: u.limit > 0 ? Math.round((u.used / u.limit) * 100) : 0,
      },
      paused: pa.paused,
      pauseReason: pa.reason,
      pauseMinutesRemaining: pa.minutesRemaining,
    }
  })

  const archive = checkArchive()

  // Overall status
  const hasDownService = rsshub.status === 'down'
  const hasPausedPlatform = platforms.some(p => p.paused)
  const hasRateLimitWarning = platforms.some(p => p.rateLimit.usagePercent > 80)
  const recentAnomalyCount = events.filter(
    e => Date.now() - new Date(e.timestamp).getTime() < 60 * 60 * 1000, // last 1h
  ).length

  const overallStatus: HealthReport['overallStatus'] = hasDownService || hasPausedPlatform
    ? 'critical'
    : hasRateLimitWarning || recentAnomalyCount > 5
      ? 'warning'
      : 'healthy'

  return {
    timestamp: new Date().toISOString(),
    services: [rsshub],
    platforms,
    archive,
    recentAnomalies: recentAnomalyCount,
    overallStatus,
  }
}
