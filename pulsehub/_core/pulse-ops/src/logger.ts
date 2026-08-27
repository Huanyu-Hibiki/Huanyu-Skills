/**
 * Structured logger for PulseHub ops.
 *
 * Writes JSON lines to `~/.pulsehub/state/pulsehub.log` AND stderr.
 * Designed for machine parsing (grep, jq, ELK) and human reading.
 */

import { appendFileSync } from 'node:fs'
import { join } from 'node:path'
import { STATE_DIR, ensureDir } from './state.js'

export type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogEntry {
  ts: string
  level: LogLevel
  msg: string
  platform?: string
  skill?: string
  data?: Record<string, unknown>
}

const LOG_FILE = join(STATE_DIR, 'pulsehub.log')
const MAX_LOG_LEVEL: LogLevel = (process.env.PULSE_LOG_LEVEL as LogLevel) ?? 'info'

const LEVEL_PRIORITY: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
}

/**
 * Log a structured entry. Writes to both file and stderr.
 */
export function log(
  level: LogLevel,
  msg: string,
  context?: { platform?: string, skill?: string, data?: Record<string, unknown> },
): void {
  if (LEVEL_PRIORITY[level] < LEVEL_PRIORITY[MAX_LOG_LEVEL]) return

  const entry: LogEntry = {
    ts: new Date().toISOString(),
    level,
    msg,
    ...context,
  }

  // Write to file (JSON line)
  try {
    ensureDir(STATE_DIR)
    appendFileSync(LOG_FILE, JSON.stringify(entry) + '\n', 'utf8')
  }
  catch {
    // If we can't write to file (disk full / permissions), don't crash
  }

  // Write to stderr (for terminal / journald capture)
  const prefix = level === 'error' ? '✗' : level === 'warn' ? '⚠' : level === 'info' ? 'ℹ' : '·'
  const platformTag = context?.platform ? `[${context.platform}]` : ''
  const skillTag = context?.skill ? `[${context.skill}]` : ''
  process.stderr.write(`${prefix} ${platformTag}${skillTag} ${msg}\n`)
}

export const logger = {
  debug: (msg: string, ctx?: Parameters<typeof log>[2]) => log('debug', msg, ctx),
  info: (msg: string, ctx?: Parameters<typeof log>[2]) => log('info', msg, ctx),
  warn: (msg: string, ctx?: Parameters<typeof log>[2]) => log('warn', msg, ctx),
  error: (msg: string, ctx?: Parameters<typeof log>[2]) => log('error', msg, ctx),
}
