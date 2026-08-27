import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

let tmpDir: string

beforeEach(async () => {
  tmpDir = mkdtempSync(join(tmpdir(), 'pulse-anomaly-'))
  process.env.PULSE_STATE_DIR = tmpDir
  // Dynamic import after env is set
  const anomaly = await import('../src/anomaly.js')
  anomaly.clearAll()
})

afterEach(() => {
  rmSync(tmpDir, { recursive: true, force: true })
  delete process.env.PULSE_STATE_DIR
})

describe('AnomalyDetector', () => {
  it('records anomaly and pauses platform', async () => {
    const anomaly = await import('../src/anomaly.js')
    const status = anomaly.recordAnomaly('rednote', 'captcha', 'slider detected')
    expect(status.paused).toBe(true)
    expect(status.reason).toBe('captcha')
    expect(status.minutesRemaining).toBeGreaterThan(0)
  })

  it('different anomaly types have different durations', async () => {
    const anomaly = await import('../src/anomaly.js')

    const captcha = anomaly.recordAnomaly('bilibili', 'captcha')
    expect(captcha.minutesRemaining).toBe(24 * 60) // 24h

    anomaly.resume('bilibili')

    const rateLimit = anomaly.recordAnomaly('bilibili', 'rate_limit')
    expect(rateLimit.minutesRemaining).toBe(2 * 60) // 2h

    anomaly.resume('bilibili')

    const network = anomaly.recordAnomaly('bilibili', 'network_error')
    expect(network.minutesRemaining).toBe(5) // 5min
  })

  it('isPaused returns true after captcha', async () => {
    const anomaly = await import('../src/anomaly.js')
    anomaly.recordAnomaly('douyin', 'captcha')
    const status = anomaly.isPaused('douyin')
    expect(status.paused).toBe(true)
    expect(status.reason).toBe('captcha')
  })

  it('isPaused returns false for clean platform', async () => {
    const anomaly = await import('../src/anomaly.js')
    const status = anomaly.isPaused('bilibili')
    expect(status.paused).toBe(false)
  })

  it('resume clears the pause', async () => {
    const anomaly = await import('../src/anomaly.js')
    anomaly.recordAnomaly('rednote', 'captcha')
    expect(anomaly.isPaused('rednote').paused).toBe(true)

    anomaly.resume('rednote')
    expect(anomaly.isPaused('rednote').paused).toBe(false)
  })

  it('getAllPaused returns all platforms', async () => {
    const anomaly = await import('../src/anomaly.js')
    anomaly.recordAnomaly('rednote', 'captcha')
    const all = anomaly.getAllPaused()
    expect(Object.keys(all)).toHaveLength(6)
    expect(all.rednote.paused).toBe(true)
    expect(all.bilibili.paused).toBe(false)
  })

  it('getRecentEvents returns recorded events', async () => {
    const anomaly = await import('../src/anomaly.js')
    anomaly.recordAnomaly('rednote', 'captcha', 'slider')
    anomaly.recordAnomaly('bilibili', 'rate_limit', 'HTTP 429')
    const events = anomaly.getRecentEvents(10)
    expect(events).toHaveLength(2)
    expect(events[0].type).toBe('rate_limit') // most recent first
    expect(events[1].type).toBe('captcha')
  })

  it('caps events at 100', async () => {
    const anomaly = await import('../src/anomaly.js')
    for (let i = 0; i < 110; i++) {
      anomaly.recordAnomaly('bilibili', 'network_error')
      anomaly.resume('bilibili')
    }
    const events = anomaly.getRecentEvents(200)
    expect(events.length).toBeLessThanOrEqual(100)
  })
})
