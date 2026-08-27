import { describe, expect, it } from 'vitest'
import { BilibiliResolver } from '../src/resolvers/bilibili.js'

describe('BilibiliResolver', () => {
  const resolver = new BilibiliResolver()

  describe('canonical URLs (no network)', () => {
    it('resolves BV ID from desktop URL', async () => {
      const url = 'https://www.bilibili.com/video/BV1xx411c7mD'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.platform).toBe('bilibili')
      expect(result!.workId).toBe('BV1xx411c7mD')
      expect(result!.url).toBe('https://www.bilibili.com/video/BV1xx411c7mD')
      expect(result!.originalLink).toBe(url)
      expect(result!.token).toBeUndefined()
      expect(result!.resolvedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/)
    })

    it('resolves BV ID from m.bilibili.com', async () => {
      const url = 'https://m.bilibili.com/video/BV1yy411c7mE'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.workId).toBe('BV1yy411c7mE')
      expect(result!.url).toBe('https://www.bilibili.com/video/BV1yy411c7mE')
    })

    it('strips tracking params and produces canonical URL', async () => {
      const url = 'https://www.bilibili.com/video/BV1xx411c7mD?spm_id_from=333.788&from=search'
      const result = await resolver.resolve(url)

      expect(result!.workId).toBe('BV1xx411c7mD')
      expect(result!.url).toBe('https://www.bilibili.com/video/BV1xx411c7mD')
    })

    it('resolves legacy av ID', async () => {
      const url = 'https://www.bilibili.com/video/av123456'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.workId).toBe('av123456')
      expect(result!.url).toBe('https://www.bilibili.com/video/av123456')
    })

    it('handles lowercase bv prefix (case-insensitive)', async () => {
      // The regex uses /i flag, so bv prefix should match
      const url = 'https://www.bilibili.com/video/bv1xx411c7mD'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      // Note: regex captures the original case from the URL
      expect(result!.workId.toLowerCase()).toBe('bv1xx411c7md')
    })

    it('accepts URL without www prefix', async () => {
      const url = 'https://bilibili.com/video/BV1xx411c7mD'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.workId).toBe('BV1xx411c7mD')
    })
  })

  describe('returns null for unsupported URLs', () => {
    it('returns null for non-bilibili hostname', async () => {
      const result = await resolver.resolve('https://www.youtube.com/watch?v=abc')
      expect(result).toBeNull()
    })

    it('returns null for bilibili URL without /video/ path', async () => {
      const result = await resolver.resolve('https://www.bilibili.com/bangumi/play/ep123')
      expect(result).toBeNull()
    })

    it('returns null for bilibili homepage', async () => {
      const result = await resolver.resolve('https://www.bilibili.com/')
      expect(result).toBeNull()
    })

    it('returns null for malformed URL', async () => {
      const result = await resolver.resolve('not-a-url')
      expect(result).toBeNull()
    })

    it('returns null for empty string', async () => {
      const result = await resolver.resolve('')
      expect(result).toBeNull()
    })

    it('returns null for /video/ path without valid ID', async () => {
      const result = await resolver.resolve('https://www.bilibili.com/video/')
      expect(result).toBeNull()
    })
  })
})
