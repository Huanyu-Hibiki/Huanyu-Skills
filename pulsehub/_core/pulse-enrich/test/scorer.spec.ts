import { describe, expect, it } from 'vitest'
import { scoreOpportunity, minutesUntilWindowCloses } from '../src/scorer.js'
import { detectSignals } from '../src/detector.js'
import type { Platform } from '@pulsehub/types'

const NOW = Date.now()

function minsAgo(min: number): Date {
  return new Date(NOW - min * 60_000)
}

describe('scoreOpportunity', () => {
  describe('rednote (fast decay)', () => {
    const platform: Platform = 'rednote'

    it('scores high for purchase intent within 30min', () => {
      const signals = detectSignals('求链接 无线耳机')
      const result = scoreOpportunity({
        signals,
        publishedAt: minsAgo(15),
        platform,
      })
      expect(result.score).toBe('high')
      expect(result.reason).toContain('purchase')
    })

    it('scores medium for purchase intent between 30min and 3h', () => {
      const signals = detectSignals('求链接')
      const result = scoreOpportunity({
        signals,
        publishedAt: minsAgo(120),
        platform,
      })
      expect(result.score).toBe('medium')
    })

    it('scores medium for question intent within 30min', () => {
      const signals = detectSignals('求推荐')
      const result = scoreOpportunity({
        signals,
        publishedAt: minsAgo(20),
        platform,
      })
      expect(result.score).toBe('medium')
    })

    it('scores low for purchase intent past 24h', () => {
      const signals = detectSignals('求链接')
      const result = scoreOpportunity({
        signals,
        publishedAt: minsAgo(1500),
        platform,
      })
      expect(result.score).toBe('low')
    })

    it('scores low for complaint-only signal', () => {
      const signals = detectSignals('翻车了')
      const result = scoreOpportunity({
        signals,
        publishedAt: minsAgo(15),
        platform,
      })
      expect(result.score).toBe('low')
      expect(result.reason).toContain('Complaint')
    })

    it('scores low for no signals', () => {
      const signals = detectSignals('今天天气真好')
      const result = scoreOpportunity({
        signals,
        publishedAt: minsAgo(15),
        platform,
      })
      expect(result.score).toBe('low')
    })
  })

  describe('bilibili (slow decay)', () => {
    const platform: Platform = 'bilibili'

    it('scores high for purchase intent within 6h', () => {
      const signals = detectSignals('求同款')
      const result = scoreOpportunity({
        signals,
        publishedAt: minsAgo(300),
        platform,
      })
      expect(result.score).toBe('high')
    })

    it('scores medium for purchase intent 6-24h', () => {
      const signals = detectSignals('求同款')
      const result = scoreOpportunity({
        signals,
        publishedAt: minsAgo(1000),
        platform,
      })
      expect(result.score).toBe('medium')
    })
  })

  describe('zhihu (very long tail)', () => {
    const platform: Platform = 'zhihu'

    it('scores high for purchase intent within 24h', () => {
      // Use purchase-intent keyword (求链接) not question (求推荐) — question in
      // high window gets medium, only purchase gets high.
      const signals = detectSignals('求链接')
      const result = scoreOpportunity({
        signals,
        publishedAt: minsAgo(800),
        platform,
      })
      expect(result.score).toBe('high')
    })

    it('scores medium for question intent within 24h', () => {
      const signals = detectSignals('求推荐')
      const result = scoreOpportunity({
        signals,
        publishedAt: minsAgo(800),
        platform,
      })
      expect(result.score).toBe('medium')
    })
  })

  describe('null publishedAt', () => {
    it('treats unknown age as fresh', () => {
      const signals = detectSignals('求链接')
      const result = scoreOpportunity({
        signals,
        publishedAt: null,
        platform: 'rednote',
      })
      expect(result.score).toBe('high')
    })
  })
})

describe('minutesUntilWindowCloses', () => {
  it('returns positive number for fresh content', () => {
    const result = minutesUntilWindowCloses('rednote', minsAgo(10))
    expect(result).toBeGreaterThan(0) // ~20 min remaining
  })

  it('returns negative number for stale content', () => {
    const result = minutesUntilWindowCloses('rednote', minsAgo(60))
    expect(result).toBeLessThan(0)
  })
})
