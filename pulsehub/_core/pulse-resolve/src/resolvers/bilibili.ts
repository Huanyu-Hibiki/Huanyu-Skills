import type { ResolvedLink } from '@pulsehub/types'
import type { Resolver } from './types.js'
import axios from 'axios'

/**
 * Bilibili URL resolver.
 *
 * Ported from AiToEarn's `bilibili-work.provider.ts` (MIT).
 * Source: https://github.com/yikart/AiToEarn/blob/main/project/aitoearn-backend/apps/aitoearn-server/src/core/channels/platforms/bilibili/bilibili-work.provider.ts
 *
 * Handles:
 *   - Canonical URLs: bilibili.com/video/{BVid}, m.bilibili.com/video/{BVid}
 *   - Short links:    b23.tv/{slug}  → redirects to canonical URL
 *   - ID formats:     BV[0-9A-Z]+ (current) and av\d+ (legacy)
 */
export class BilibiliResolver implements Resolver {
  private static readonly HOSTNAME_PRIMARY = 'bilibili.com'
  private static readonly HOSTNAME_MOBILE = 'm.bilibili.com'
  private static readonly HOSTNAME_SHORT = 'b23.tv'
  private static readonly USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
  private static readonly SHORT_LINK_TIMEOUT_MS = 10_000
  private static readonly SHORT_LINK_MAX_REDIRECTS = 5

  /**
   * Matches `/video/{id}` where id is either:
   *   - BV-prefixed alphanumeric (current format, e.g., BV1xx411c7mD)
   *   - av-prefixed numeric (legacy format, e.g., av123456)
   */
  private static readonly VIDEO_ID_PATTERN = /\/video\/(BV[0-9A-Z]+|av\d+)/i

  async resolve(rawLink: string): Promise<ResolvedLink | null> {
    const normalized = await this.normalizeLink(rawLink)
    const videoId = this.parseVideoId(normalized)
    if (!videoId) {
      return null
    }

    const url = `https://www.bilibili.com/video/${videoId}`
    return {
      platform: 'bilibili',
      workId: videoId,
      url,
      originalLink: rawLink,
      resolvedAt: new Date().toISOString(),
    }
  }

  /**
   * If the link is a b23.tv short link, follow redirects to get the canonical URL.
   * On failure, returns the original link (parseVideoId will then fail and produce null).
   */
  private async normalizeLink(link: string): Promise<string> {
    let url: URL
    try {
      url = new URL(link)
    }
    catch {
      return link
    }

    if (url.hostname.replace(/^www\./, '') === BilibiliResolver.HOSTNAME_SHORT) {
      return await this.resolveRedirectUrl(link)
    }
    return link
  }

  /**
   * Extract the BV/av ID from a canonical Bilibili URL.
   * Returns undefined for non-bilibili hosts or unrecognized paths.
   */
  private parseVideoId(link: string): string | undefined {
    let url: URL
    try {
      url = new URL(link)
    }
    catch {
      return undefined
    }

    const hostname = url.hostname.replace(/^www\./, '')
    if (hostname !== BilibiliResolver.HOSTNAME_PRIMARY && hostname !== BilibiliResolver.HOSTNAME_MOBILE) {
      return undefined
    }

    return url.pathname.match(BilibiliResolver.VIDEO_ID_PATTERN)?.[1]
  }

  /**
   * Follow a b23.tv short link to its final destination.
   * Returns the original link on failure (rather than throwing) so the caller
   * can gracefully fall through to the next resolver.
   */
  private async resolveRedirectUrl(link: string): Promise<string> {
    try {
      const response = await axios.get(link, {
        maxRedirects: BilibiliResolver.SHORT_LINK_MAX_REDIRECTS,
        timeout: BilibiliResolver.SHORT_LINK_TIMEOUT_MS,
        headers: { 'User-Agent': BilibiliResolver.USER_AGENT },
      })
      return response.request?.res?.responseUrl || response.config?.url || link
    }
    catch (error) {
      console.warn(
        `[pulse-resolve] failed to resolve Bilibili short link: ${link}`,
        error instanceof Error ? error.message : error,
      )
      return link
    }
  }
}
