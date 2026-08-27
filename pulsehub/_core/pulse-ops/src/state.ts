/**
 * State persistence layer for PulseHub ops.
 *
 * All operational state lives at `~/.pulsehub/state/`:
 *   - rate-limits.json   (per-platform daily request counts)
 *   - anomalies.json     (paused platforms + reasons)
 *   - metrics.json       (cumulative counters)
 *   - pulsehub.log       (structured log)
 *
 * This module provides atomic read/write with safe defaults.
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync, renameSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'
import { randomBytes } from 'node:crypto'

export const STATE_DIR = process.env.PULSE_STATE_DIR
  ?? join(homedir(), '.pulsehub', 'state')

export const ARCHIVE_DIR = process.env.PULSE_ARCHIVE_DIR
  ?? join(homedir(), '.pulsehub', 'archive')

/** Ensure a directory exists. */
export function ensureDir(dir: string): void {
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true })
  }
}

/**
 * Read a JSON state file with safe default.
 * Returns `defaultValue` if file doesn't exist or is corrupted.
 */
export function readState<T>(filename: string, defaultValue: T): T {
  const filepath = join(STATE_DIR, filename)
  try {
    if (!existsSync(filepath)) return defaultValue
    const raw = readFileSync(filepath, 'utf8')
    return JSON.parse(raw) as T
  }
  catch {
    return defaultValue
  }
}

/**
 * Write JSON state file atomically (write to temp, then rename).
 * Prevents corruption if process is killed mid-write.
 */
export function writeState<T>(filename: string, data: T): void {
  ensureDir(STATE_DIR)
  const filepath = join(STATE_DIR, filename)
  const tmpPath = `${filepath}.${randomBytes(4).toString('hex')}.tmp`
  writeFileSync(tmpPath, JSON.stringify(data, null, 2), 'utf8')
  renameSync(tmpPath, filepath)
}

/**
 * Get the current date key for daily reset (e.g., "2026-07-27").
 * Rate limits reset daily at local midnight.
 */
export function todayKey(): string {
  return new Date().toISOString().slice(0, 10)
}

/** Check if a date key is today. */
export function isToday(key: string): boolean {
  return key === todayKey()
}
