import type { ResolvedLink } from '@pulsehub/types'
import type { Resolver } from './types.js'

/**
 * WeChat Official Account (公众号) URL resolver.
 *
 * Not ported from AiToEarn — AiToEarn has no public WeChat Official URL resolver.
 * Implemented from scratch based on the canonical WeChat article URL format.
 *
 * Handles:
 *   - Short article URL:  mp.weixin.qq.com/s/{slug}
 *   - Full article URL:   mp.weixin.qq.com/s?__biz={biz}&mid={mid}&idx={idx}&sn={sn}
 *
 * Note: WeChat articles don't have a stable numeric ID. The `sn` parameter
 * (or the `{slug}` in short URLs) is the closest thing to a unique identifier.
 *
 * Public access: WeChat article URLs are publicly accessible without login.
 */
export class WeChatOfficialResolver implements Resolver {
  private static readonly HOSTNAME = 'mp.weixin.qq.com'
  private static readonly SHORT_PATH_PREFIX = '/s'

  async resolve(rawLink: string): Promise<ResolvedLink | null> {
    let url: URL
    try {
      url = new URL(rawLink)
    }
    catch {
      return null
    }

    const hostname = url.hostname.replace(/^www\./, '')
    if (hostname !== WeChatOfficialResolver.HOSTNAME) {
      return null
    }

    // Path must be /s (short) or /s?params (full). Other paths (/mp/, /cgi-bin/) are not articles.
    if (!url.pathname.startsWith(WeChatOfficialResolver.SHORT_PATH_PREFIX)) {
      return null
    }

    const workId = this.extractArticleId(url)
    if (!workId) {
      return null
    }

    return {
      platform: 'wechat_official',
      workId,
      // Preserve original URL — WeChat articles are sensitive to URL params
      // (changing params can break the article or trigger anti-scraping).
      url: rawLink,
      originalLink: rawLink,
      resolvedAt: new Date().toISOString(),
    }
  }

  /**
   * Extract a stable article identifier.
   *
   * Preference order:
   *   1. `sn` query param (present in full URLs, stable per-article)
   *   2. Path slug in /s/{slug} short URLs (also stable, but opaque)
   *
   * Returns undefined for non-article URLs (e.g., /s without slug or params).
   */
  private extractArticleId(url: URL): string | undefined {
    // Full URL format: /s?__biz=...&mid=...&idx=...&sn=...
    const sn = url.searchParams.get('sn')
    if (sn) {
      return sn
    }

    // Short URL format: /s/{slug}  (slug is typically a base64-like opaque string)
    // Pathname would be "/s/abc123def..." — split and take the second segment.
    if (url.pathname !== WeChatOfficialResolver.SHORT_PATH_PREFIX) {
      const segments = url.pathname.split('/').filter(Boolean)
      // segments[0] = 's', segments[1] = slug
      if (segments[0] === 's' && segments[1]) {
        return segments[1]
      }
    }

    return undefined
  }
}
