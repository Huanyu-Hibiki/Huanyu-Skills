import { describe, expect, it } from 'vitest'
import { ZhihuResolver } from '../src/resolvers/zhihu.js'

describe('ZhihuResolver', () => {
  const resolver = new ZhihuResolver()

  describe('canonical URLs', () => {
    it('resolves question/answer URL', async () => {
      const url = 'https://www.zhihu.com/question/123456789/answer/987654321'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.platform).toBe('zhihu')
      expect(result!.workId).toBe('a-987654321')
      expect(result!.url).toBe('https://www.zhihu.com/question/123456789/answer/987654321')
      expect(result!.originalLink).toBe(url)
      expect(result!.token).toBeUndefined()
      expect(result!.resolvedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/)
    })

    it('resolves question URL without answer (question page)', async () => {
      const url = 'https://www.zhihu.com/question/123456789'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.workId).toBe('q-123456789')
      expect(result!.url).toBe('https://www.zhihu.com/question/123456789')
    })

    it('resolves zhuanlan (column article) URL', async () => {
      const url = 'https://zhuanlan.zhihu.com/p/12345678'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.workId).toBe('p-12345678')
      expect(result!.url).toBe('https://zhuanlan.zhihu.com/p/12345678')
    })

    it('accepts zhihu.com without www', async () => {
      const url = 'https://zhihu.com/question/123/answer/456'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.workId).toBe('a-456')
    })

    it('strips tracking params from answer URL', async () => {
      const url = 'https://www.zhihu.com/question/123/answer/456?utm_source=wechat_session&utm_medium=social'
      const result = await resolver.resolve(url)

      expect(result!.workId).toBe('a-456')
      expect(result!.url).toBe('https://www.zhihu.com/question/123/answer/456')
    })
  })

  describe('returns null for unsupported URLs', () => {
    it('returns null for non-zhihu hostname', async () => {
      const result = await resolver.resolve('https://www.bilibili.com/video/BV1xx')
      expect(result).toBeNull()
    })

    it('returns null for zhihu homepage', async () => {
      const result = await resolver.resolve('https://www.zhihu.com/')
      expect(result).toBeNull()
    })

    it('returns null for zhihu /pin/ (想法) URLs', async () => {
      // Pins are not supported (low engagement value, no public comment API)
      const result = await resolver.resolve('https://www.zhihu.com/pin/123456789')
      expect(result).toBeNull()
    })

    it('returns null for zhihu /people/ URLs', async () => {
      const result = await resolver.resolve('https://www.zhihu.com/people/abc123')
      expect(result).toBeNull()
    })

    it('returns null for zhihu /topic/ URLs', async () => {
      const result = await resolver.resolve('https://www.zhihu.com/topic/123456')
      expect(result).toBeNull()
    })

    it('returns null for zhihu /search URLs', async () => {
      const result = await resolver.resolve('https://www.zhihu.com/search?q=abc')
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

    it('returns null for /question/ without ID', async () => {
      const result = await resolver.resolve('https://www.zhihu.com/question/')
      expect(result).toBeNull()
    })

    it('returns null for zhuanlan without article ID', async () => {
      const result = await resolver.resolve('https://zhuanlan.zhihu.com/p/')
      expect(result).toBeNull()
    })
  })
})
