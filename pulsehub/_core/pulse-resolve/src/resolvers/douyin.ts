import type { ResolvedLink } from '@pulsehub/types'
import type { Resolver } from './types.js'
import axios from 'axios'

/**
 * Douyin URL resolver.
 *
 * Ported from AiToEarn's `douyin-work.provider.ts` (MIT).
 * Source: https://github.com/yikart/AiToEarn/blob/main/project/aitoearn-backend/apps/aitoearn-server/src/core/channels/platforms/douyin/douyin-work.provider.ts
 *
 * Handles:
 *   - Video URLs:   douyin.com/video/{id}, /note/{id} (image post), ?modal_id={id}
 *   - Legacy URLs:  iesdouyin.com/share/video/{id}
 *   - Short links:  v.douyin.com/{slug}  → redirects to canonical URL
 */
export class DouyinResolver implements Resolver {
  private static readonly HOSTNAME_PRIMARY = 'douyin.com'
  private static readonly HOSTNAME_LEGACY = 'iesdouyin.com'
  private static readonly HOSTNAME_SHORT = 'v.douyin.com'
  private static readonly USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
  private static readonly SHORT_LINK_TIMEOUT_MS = 10_000
  private static readonly SHORT_LINK_MAX_REDIRECTS = 5

  async resolve(rawLink: string): Promise<ResolvedLink | null> {
    const normalized = await this.normalizeLink(rawLink)
    const workId = this.parseWorkId(normalized)
    if (!workId) {
      return null
    }

    const url = this.buildWorkLink(workId, normalized)
    return {
      platform: 'douyin',
      workId,
      url,
      originalLink: rawLink,
      resolvedAt: new Date().toISOString(),
    }
  }

  /**
   * If the link is a v.douyin.com short link, follow redirects.
   * Returns the original link on failure or for non-short URLs.
   */
  private async normalizeLink(link: string): Promise<string> {
    try {
      const url = new URL(link)
      if (url.hostname.replace(/^www\./, '') === DouyinResolver.HOSTNAME_SHORT) {
        return await this.resolveRedirectUrl(link)
      }
    }
    catch {
      return link
    }
    return link
  }

  /**
   * Extract the work ID from a canonical Douyin URL.
   *
   * Supported patterns on douyin.com:
   *   /video/{id}        — video post
   *   /note/{id}         — image post (图文)
   *   ?modal_id={id}     — modal-style video view
   *
   * Supported patterns on iesdouyin.com (legacy):
   *   /share/video/{id}  — legacy share URL
   */
  private parseWorkId(link: string): string | undefined {
    let url: URL
    try {
      url = new URL(link)
    }
    catch {
      return undefined
    }

    const hostname = url.hostname.replace(/^www\./, '')
    const pathname = url.pathname

    if (hostname === DouyinResolver.HOSTNAME_PRIMARY) {
      if (pathname.startsWith('/video/')) {
        return pathname.split('/video/')[1]?.split(/[?&#/]/)[0] || undefined
      }
      if (pathname.startsWith('/note/')) {
        return pathname.split('/note/')[1]?.split(/[?&#/]/)[0] || undefined
      }
      return url.searchParams.get('modal_id') ?? undefined
    }

    if (hostname === DouyinResolver.HOSTNAME_LEGACY) {
      return pathname.match(/\/video\/(\d+)/)?.[1]
    }

    return undefined
  }

  /**
   * Build a canonical clickable URL for the work.
   * Preserves the /note/ vs /video/ distinction (image posts vs videos).
   */
  private buildWorkLink(workId: string, resolvedUrl: string): string {
    try {
      const url = new URL(resolvedUrl)
      if (
        url.hostname.replace(/^www\./, '') === DouyinResolver.HOSTNAME_PRIMARY
        && url.pathname.startsWith('/note/')
      ) {
        return `https://www.douyin.com/note/${workId}`
      }
    }
    catch {
      // Fall back to the canonical video URL below.
    }
    return `https://www.douyin.com/video/${workId}`
  }

  /**
   * Follow a v.douyin.com short link to its final destination.
   * Returns the original link on failure (graceful degradation).
   */
  private async resolveRedirectUrl(link: string): Promise<string> {
    try {
      const response = await axios.get(link, {
        maxRedirects: DouyinResolver.SHORT_LINK_MAX_REDIRECTS,
        timeout: DouyinResolver.SHORT_LINK_TIMEOUT_MS,
        headers: { 'User-Agent': DouyinResolver.USER_AGENT },
      })
      return response.request?.res?.responseUrl || response.config?.url || link
    }
    catch (error) {
      console.warn(
        `[pulse-resolve] failed to resolve Douyin short link: ${link}`,
        error instanceof Error ? error.message : error,
      )
      return link
    }
  }
}
