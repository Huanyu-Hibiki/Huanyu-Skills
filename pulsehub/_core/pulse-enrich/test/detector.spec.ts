import { describe, expect, it } from 'vitest'
import { detectSignals } from '../src/detector.js'

describe('detectSignals', () => {
  describe('purchase intent', () => {
    it('detects "求链接" in title', () => {
      const result = detectSignals('求链接，这个无线耳机多少钱')
      expect(result.purchaseIntent).toBe(true)
      expect(result.matched.purchase).toContain('求链接')
      expect(result.matched.purchase).toContain('多少钱')
    })

    it('detects "怎么买"', () => {
      const result = detectSignals('这个怎么买？求链接')
      expect(result.purchaseIntent).toBe(true)
      expect(result.matched.purchase).toContain('怎么买')
    })

    it('detects "种草" intent', () => {
      const result = detectSignals('被这个种草了，想要')
      expect(result.purchaseIntent).toBe(true)
      expect(result.matched.purchase).toContain('种草')
    })

    it('detects multiple purchase keywords', () => {
      const result = detectSignals('多少钱？怎么买？预算 500 求同款')
      expect(result.purchaseIntent).toBe(true)
      expect(result.matched.purchase.length).toBeGreaterThanOrEqual(3)
    })

    it('suppresses negated "想要" (不想要)', () => {
      const result = detectSignals('我不想要这个')
      expect(result.matched.purchase).not.toContain('想要')
      expect(result.purchaseIntent).toBe(false)
    })

    it('suppresses negated "想买" (不想买)', () => {
      const result = detectSignals('千万别买，不想买这个')
      expect(result.matched.purchase).not.toContain('想买')
    })
  })

  describe('question intent', () => {
    it('detects "求推荐"', () => {
      const result = detectSignals('求推荐无线耳机')
      expect(result.questionIntent).toBe(true)
      expect(result.matched.question).toContain('求推荐')
    })

    it('detects "值得买吗"', () => {
      const result = detectSignals('这个值得买吗？')
      expect(result.questionIntent).toBe(true)
      expect(result.matched.question).toContain('值得买吗')
    })

    it('detects "怎么选"', () => {
      const result = detectSignals('两款怎么选')
      expect(result.questionIntent).toBe(true)
    })
  })

  describe('complaint', () => {
    it('detects "翻车"', () => {
      const result = detectSignals('刚买的就翻车了')
      expect(result.complaint).toBe(true)
      expect(result.matched.complaint).toContain('翻车')
    })

    it('detects "智商税"', () => {
      const result = detectSignals('这玩意儿就是智商税')
      expect(result.complaint).toBe(true)
      expect(result.matched.complaint).toContain('智商税')
    })

    it('detects "假货"', () => {
      const result = detectSignals('收到的是假货')
      expect(result.complaint).toBe(true)
      expect(result.matched.complaint).toContain('假货')
    })
  })

  describe('mixed signals', () => {
    it('detects purchase + question together', () => {
      const result = detectSignals('求推荐无线耳机，预算 500，怎么选')
      expect(result.purchaseIntent).toBe(true)
      expect(result.questionIntent).toBe(true)
    })

    it('detects complaint + question', () => {
      const result = detectSignals('翻车了，求推荐替代款')
      expect(result.complaint).toBe(true)
      expect(result.questionIntent).toBe(true)
    })
  })

  describe('no signals', () => {
    it('returns empty for unrelated content', () => {
      const result = detectSignals('今天天气真好，去公园散步')
      expect(result.purchaseIntent).toBe(false)
      expect(result.questionIntent).toBe(false)
      expect(result.complaint).toBe(false)
      expect(result.matchedKeywords).toHaveLength(0)
    })

    it('returns empty for empty text', () => {
      const result = detectSignals('')
      expect(result.purchaseIntent).toBe(false)
    })
  })

  describe('case insensitivity', () => {
    it('matches regardless of case (English mixed in)', () => {
      const result = detectSignals('求链接 ABCdef 多少钱')
      expect(result.purchaseIntent).toBe(true)
    })
  })
})
