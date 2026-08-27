import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

// Dynamic import — modules read PULSE_STATE_DIR at call time via state.ts
async function importModules() {
  // Set env BEFORE import so state.ts picks up the right directory
  const tmpDir = mkdtempSync(join(tmpdir(), 'pulse-test-'))
  process.env.PULSE_STATE_DIR = tmpDir
  // Dynamic import to ensure fresh module load with correct env
  const rateLimiter = await import('../src/rate-limiter.js')
  return { rateLimiter, tmpDir }
}

describe('RateLimiter', () => {
  let tmpDir: string
  let rl: Awaited<ReturnType<typeof importModules>>['rateLimiter']

  beforeEach(async () => {
    const result = await importModules()
    rl = result.rateLimiter
    tmpDir = result.tmpDir
    rl.resetAll()
  })

  afterEach(() => {
    rmSync(tmpDir, { recursive: true, force: true })
    delete process.env.PULSE_STATE_DIR
  })

  describe('checkLimit', () => {
    it('allows requests when under limit', () => {
      const check = rl.checkLimit('bilibili')
      expect(check.allowed).toBe(true)
      expect(check.remaining).toBe(80) // bilibili limit
      expect(check.used).toBe(0)
    })

    it('blocks requests when limit reached', () => {
      // Record 80 requests (bilibili limit)
      for (let i = 0; i < 80; i++) rl.recordRequest('bilibili')
      const check = rl.checkLimit('bilibili')
      expect(check.allowed).toBe(false)
      expect(check.remaining).toBe(0)
      expect(check.used).toBe(80)
    })

    it('uses different limits per platform', () => {
      const bilibili = rl.checkLimit('bilibili')
      const rednote = rl.checkLimit('rednote')
      expect(bilibili.limit).toBe(80)
      expect(rednote.limit).toBe(30)
    })
  })

  describe('recordRequest', () => {
    it('increments counter', () => {
      rl.recordRequest('bilibili')
      rl.recordRequest('bilibili')
      rl.recordRequest('bilibili')
      const check = rl.checkLimit('bilibili')
      expect(check.used).toBe(3)
    })

    it('supports batch increment', () => {
      rl.recordRequest('bilibili', 10)
      const check = rl.checkLimit('bilibili')
      expect(check.used).toBe(10)
    })
  })

  describe('checkAndRecord', () => {
    it('checks and increments atomically', () => {
      const result = rl.checkAndRecord('bilibili')
      expect(result.allowed).toBe(true)
      expect(result.used).toBe(1) // incremented
      expect(result.remaining).toBe(79)
    })

    it('does not increment when blocked', () => {
      // Fill up the limit
      for (let i = 0; i < 80; i++) rl.recordRequest('bilibili')
      const result = rl.checkAndRecord('bilibili')
      expect(result.allowed).toBe(false)
      expect(result.used).toBe(80) // NOT incremented
    })
  })

  describe('resetPlatform', () => {
    it('resets a specific platform counter', () => {
      rl.recordRequest('bilibili', 50)
      rl.recordRequest('rednote', 10)
      rl.resetPlatform('bilibili')
      expect(rl.checkLimit('bilibili').used).toBe(0)
      expect(rl.checkLimit('rednote').used).toBe(10) // unchanged
    })
  })

  describe('getAllUsage', () => {
    it('returns all platforms', () => {
      rl.recordRequest('bilibili', 5)
      const usage = rl.getAllUsage()
      expect(Object.keys(usage)).toHaveLength(6)
      expect(usage.bilibili.used).toBe(5)
      expect(usage.bilibili.limit).toBe(80)
      expect(usage.rednote.limit).toBe(30)
    })
  })

  describe('persistence', () => {
    it('persists across module re-imports', async () => {
      rl.recordRequest('bilibili', 10)
      // Re-import with same tmpDir
      const rl2 = (await import('../src/rate-limiter.js'))
      const check = rl2.checkLimit('bilibili')
      expect(check.used).toBe(10)
    })
  })
})
