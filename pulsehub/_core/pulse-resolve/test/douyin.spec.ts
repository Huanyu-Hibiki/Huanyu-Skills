import { describe, expect, it } from 'vitest'
import { DouyinResolver } from '../src/resolvers/douyin.js'

describe('DouyinResolver', () => {
  const resolver = new DouyinResolver()

  describe('canonical URLs (no network)', () => {
    it('resolves /video/{id} URL', async () => {
      const url = 'https://www.douyin.com/video/7234567890123456789'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.platform).toBe('douyin')
      expect(result!.workId).toBe('7234567890123456789')
      expect(result!.url).toBe('https://www.douyin.com/video/7234567890123456789')
      expect(result!.originalLink).toBe(url)
      expect(result!.token).toBeUndefined()
      expect(result!.resolvedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/)
    })

    it('resolves /note/{id} URL (image post) and preserves note path', async () => {
      const url = 'https://www.douyin.com/note/7234567890123456789'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.workId).toBe('7234567890123456789')
      // Note URLs must stay as /note/ (image posts vs videos)
      expect(result!.url).toBe('https://www.douyin.com/note/7234567890123456789')
    })

    it('resolves modal_id query parameter', async () => {
      const url = 'https://www.douyin.com/discover?modal_id=7234567890123456789'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.workId).toBe('7234567890123456789')
    })

    it('resolves iesdouyin.com legacy share URL', async () => {
      const url = 'https://www.iesdouyin.com/share/video/7234567890123456789'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.workId).toBe('7234567890123456789')
    })

    it('strips trailing slash from video ID', async () => {
      const url = 'https://www.douyin.com/video/7234567890123456789/'
      const result = await resolver.resolve(url)

      expect(result!.workId).toBe('7234567890123456789')
    })

    it('strips query params after ID', async () => {
      const url = 'https://www.douyin.com/video/7234567890123456789?previous_page=app_code_link'
      const result = await resolver.resolve(url)

      expect(result!.workId).toBe('7234567890123456789')
      expect(result!.url).toBe('https://www.douyin.com/video/7234567890123456789')
    })

    it('accepts URL without www prefix', async () => {
      const url = 'https://douyin.com/video/7234567890123456789'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.workId).toBe('7234567890123456789')
    })

    it('builds /video/ canonical URL when path is unknown but modal_id is present', async () => {
      // When resolved via modal_id (not /note/), canonical URL should use /video/
      const url = 'https://www.douyin.com/?modal_id=7234567890123456789'
      const result = await resolver.resolve(url)

      expect(result!.url).toBe('https://www.douyin.com/video/7234567890123456789')
    })
  })

  describe('returns null for unsupported URLs', () => {
    it('returns null for non-douyin hostname', async () => {
      const result = await resolver.resolve('https://www.bilibili.com/video/BV1xx')
      expect(result).toBeNull()
    })

    it('returns null for douyin homepage without modal_id', async () => {
      const result = await resolver.resolve('https://www.douyin.com/')
      expect(result).toBeNull()
    })

    it('returns null for douyin user profile URL', async () => {
      const result = await resolver.resolve('https://www.douyin.com/user/abc123')
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

    it('returns null for /video/ path without ID', async () => {
      const result = await resolver.resolve('https://www.douyin.com/video/')
      expect(result).toBeNull()
    })
  })
})
