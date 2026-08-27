/**
 * pulse-ops — Operational hardening for PulseHub.
 *
 * Public API surface. Import from here, not from individual modules.
 */

export { checkLimit, recordRequest, checkAndRecord, getAllUsage, resetPlatform, resetAll, PLATFORM_LIMITS } from './rate-limiter.js'
export type { RateLimitCheck } from './rate-limiter.js'

export { recordAnomaly, isPaused, resume, getAllPaused, getRecentEvents, clearAll } from './anomaly.js'
export type { AnomalyType, AnomalyEvent, PauseStatus } from './anomaly.js'

export { checkHealth } from './health.js'
export type { HealthReport, ServiceStatus, PlatformHealth, ArchiveHealth } from './health.js'

export { backup, restore } from './backup.js'

export { logger } from './logger.js'
export type { LogLevel } from './logger.js'

export { STATE_DIR, ARCHIVE_DIR, readState, writeState, ensureDir, todayKey } from './state.js'
