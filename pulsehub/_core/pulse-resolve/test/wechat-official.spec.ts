import { describe, expect, it } from 'vitest'
import { WeChatOfficialResolver } from '../src/resolvers/wechat-official.js'

describe('WeChatOfficialResolver', () => {
  const resolver = new WeChatOfficialResolver()

  describe('canonical URLs', () => {
    it('resolves short article URL /s/{slug}', async () => {
      const url = 'https://mp.weixin.qq.com/s/abc123def456ghi'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.platform).toBe('wechat_official')
      expect(result!.workId).toBe('abc123def456ghi')
      expect(result!.url).toBe(url)
      expect(result!.originalLink).toBe(url)
      expect(result!.token).toBeUndefined()
      expect(result!.resolvedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/)
    })

    it('resolves full article URL with sn param', async () => {
      const url = 'https://mp.weixin.qq.com/s?__biz=MzIwMzUyNDk0Nw==&mid=2247485123&idx=1&sn=abc123def456&chksm=...'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.workId).toBe('abc123def456')
      // URL preserved as-is (WeChat articles are sensitive to param changes)
      expect(result!.url).toBe(url)
    })

    it('prefers sn over path slug when both present (rare)', async () => {
      // Hypothetical: /s/{slug}?__biz=...&sn=xxx
      const url = 'https://mp.weixin.qq.com/s/someslug?sn=realsn123'
      const result = await resolver.resolve(url)

      expect(result!.workId).toBe('realsn123')
    })

    it('preserves full URL params (WeChat requires them)', async () => {
      const url = 'https://mp.weixin.qq.com/s?__biz=xxx&mid=123&idx=1&sn=yyy&chksm=zzz&scene=27'
      const result = await resolver.resolve(url)

      expect(result!.url).toBe(url)
    })
  })

  describe('returns null for non-article URLs', () => {
    it('returns null for /s path without slug or params', async () => {
      const result = await resolver.resolve('https://mp.weixin.qq.com/s')
      expect(result).toBeNull()
    })

    it('returns null for /mp/ path (profile pages)', async () => {
      const result = await resolver.resolve('https://mp.weixin.qq.com/mp/profilebin')
      expect(result).toBeNull()
    })

    it('returns null for /cgi-bin/ paths (API endpoints)', async () => {
      const result = await resolver.resolve('https://mp.weixin.qq.com/cgi-bin/appmsg')
      expect(result).toBeNull()
    })

    it('returns null for non-WeChat hostname', async () => {
      const result = await resolver.resolve('https://www.bilibili.com/video/BV1xx')
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

    it('returns null for /s?without sn param', async () => {
      // Has /s path but no slug and no sn — can't identify article
      const result = await resolver.resolve('https://mp.weixin.qq.com/s?__biz=xxx&mid=123')
      expect(result).toBeNull()
    })
  })
})
