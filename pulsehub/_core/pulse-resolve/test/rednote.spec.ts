import { describe, expect, it } from 'vitest'
import { RedNoteResolver } from '../src/resolvers/rednote.js'

describe('RedNoteResolver', () => {
  const resolver = new RedNoteResolver()

  describe('canonical URLs (no network)', () => {
    it('resolves /explore/{noteId} URL', async () => {
      const url = 'https://www.xiaohongshu.com/explore/65f8e7ab000000000d00aabc?xsec_token=ABxyz123'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.platform).toBe('rednote')
      expect(result!.workId).toBe('65f8e7ab000000000d00aabc')
      expect(result!.url).toBe(url)
      expect(result!.originalLink).toBe(url)
      expect(result!.token).toEqual({ xsec_token: 'ABxyz123' })
      expect(result!.resolvedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/)
    })

    it('resolves URL without www prefix', async () => {
      const url = 'https://xiaohongshu.com/explore/65f8e7ab000000000d00aabc?xsec_token=t'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.workId).toBe('65f8e7ab000000000d00aabc')
    })

    it('resolves /red_video/{noteId} URL', async () => {
      const url = 'https://www.xiaohongshu.com/red_video/abc123def456?xsec_token=t'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.workId).toBe('abc123def456')
    })

    it('resolves /discovery/item/{noteId} URL', async () => {
      const url = 'https://www.xiaohongshu.com/discovery/item/aaa111bbb222?xsec_token=t'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.workId).toBe('aaa111bbb222')
    })

    it('resolves /user/profile/{uid}/{noteId} URL', async () => {
      // AiToEarn logic: segments[3] is the noteId
      // Path: /user/profile/{uid}/{noteId} → segments = ['user', 'profile', uid, noteId]
      const profileUrl = 'https://www.xiaohongshu.com/user/profile/abc123/aaa111?xsec_token=t'
      const result = await resolver.resolve(profileUrl)

      expect(result).not.toBeNull()
      expect(result!.workId).toBe('aaa111')
    })

    it('preserves xsec_token exactly (no trim if no spaces)', async () => {
      const token = 'ABxyz123456_Mixed-Case.789'
      const url = `https://www.xiaohongshu.com/explore/abc?xsec_token=${token}`
      const result = await resolver.resolve(url)

      expect(result!.token).toEqual({ xsec_token: token })
    })

    it('trims whitespace from xsec_token', async () => {
      const url = 'https://www.xiaohongshu.com/explore/abc?xsec_token=%20%20ABxyz%20%20'
      const result = await resolver.resolve(url)

      expect(result!.token).toEqual({ xsec_token: 'ABxyz' })
    })

    it('sets token to undefined when xsec_token is missing', async () => {
      const url = 'https://www.xiaohongshu.com/explore/abc'
      const result = await resolver.resolve(url)

      expect(result).not.toBeNull()
      expect(result!.token).toBeUndefined()
    })

    it('handles URL with extra query params', async () => {
      const url = 'https://www.xiaohongshu.com/explore/abc?xsec_token=t&utm_source=share&share_id=xyz'
      const result = await resolver.resolve(url)

      expect(result!.workId).toBe('abc')
      expect(result!.token).toEqual({ xsec_token: 't' })
    })
  })

  describe('returns null for unsupported URLs', () => {
    it('returns null for non-xiaohongshu hostname', async () => {
      const result = await resolver.resolve('https://www.bilibili.com/video/BV1xx')
      expect(result).toBeNull()
    })

    it('returns null for unsupported xiaohongshu path', async () => {
      const result = await resolver.resolve('https://www.xiaohongshu.com/unknown/path')
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

    it('returns null for xiaohongshu homepage', async () => {
      const result = await resolver.resolve('https://www.xiaohongshu.com/')
      expect(result).toBeNull()
    })
  })
})
