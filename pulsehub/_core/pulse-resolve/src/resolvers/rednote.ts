import type { ResolvedLink } from '@pulsehub/types'
import type { Resolver } from './types.js'
import axios from 'axios'

/**
 * RedNote (Xiaohongshu) URL resolver.
 *
 * Ported from AiToEarn's `rednote-work.provider.ts` (MIT).
 * Source: https://github.com/yikart/AiToEarn/blob/main/project/aitoearn-backend/apps/aitoearn-server/src/core/channels/platforms/rednote/rednote-work.provider.ts
 *
 * Handles:
 *   - Canonical URLs: xiaohongshu.com/explore/{id}, /red_video/{id}, /discovery/item/{id}, /user/profile/...
 *   - Short links:    xhslink.com/a/{slug}  → redirects to canonical URL
 *   - Token preservation: xsec_token is critical, without it the URL returns 403
 */
export class RedNoteResolver implements Resolver {
  private static readonly HOSTNAME_PRIMARY = 'xiaohongshu.com'
  private static readonly HOSTNAME_SHORT = 'xhslink.com'
  private static readonly USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
  private static readonly SHORT_LINK_TIMEOUT_MS = 10_000
  private static readonly SHORT_LINK_MAX_REDIRECTS = 5

  async resolve(rawLink: string): Promise<ResolvedLink | null> {
    const parsed = await this.parseRedNoteUrl(rawLink)
    if (!parsed.noteId) {
      return null
    }

    const url = parsed.resolvedUrl ?? rawLink
    const token = parsed.xsecToken
      ? { xsec_token: parsed.xsecToken }
      : undefined

    return {
      platform: 'rednote',
      workId: parsed.noteId,
      url,
      originalLink: rawLink,
      token,
      resolvedAt: new Date().toISOString(),
    }
  }

  /**
   * Parse a RedNote URL into its components.
   * Returns `{ noteId: null }` when the link is not a recognized RedNote URL.
   */
  private async parseRedNoteUrl(
    workLink: string,
  ): Promise<{ noteId: string | null, resolvedUrl?: string, xsecToken?: string }> {
    let url: URL
    try {
      url = new URL(workLink)
    }
    catch {
      return { noteId: null }
    }

    const hostname = url.hostname.replace(/^www\./, '')

    if (hostname === RedNoteResolver.HOSTNAME_PRIMARY) {
      return {
        noteId: this.extractNoteId(url),
        resolvedUrl: workLink,
        xsecToken: this.getXsecToken(url),
      }
    }

    if (hostname === RedNoteResolver.HOSTNAME_SHORT) {
      return await this.resolveShortLink(workLink)
    }

    return { noteId: null }
  }

  /**
   * Extract the noteId from a canonical Xiaohongshu URL.
   *
   * Supported path patterns:
   *   /explore/{noteId}
   *   /red_video/{noteId}
   *   /discovery/item/{noteId}
   *   /user/profile/{uid}/{?}/{noteId}   (segments[3] — profile pages embed noteId)
   */
  private extractNoteId(url: URL): string | null {
    const segments = url.pathname.split('/').filter(Boolean)

    if (segments[0] === 'explore' && segments[1]) {
      return segments[1]
    }
    if (segments[0] === 'red_video' && segments[1]) {
      return segments[1]
    }
    if (segments[0] === 'discovery' && segments[1] === 'item' && segments[2]) {
      return segments[2]
    }
    if (segments[0] === 'user' && segments[1] === 'profile' && segments[3]) {
      return segments[3]
    }

    return null
  }

  /**
   * Follow an xhslink.com short link and parse the final destination.
   * Returns `{ noteId: null }` if the redirect target is not a Xiaohongshu URL.
   */
  private async resolveShortLink(
    shortUrl: string,
  ): Promise<{ noteId: string | null, resolvedUrl?: string, xsecToken?: string }> {
    try {
      const response = await axios.get(shortUrl, {
        maxRedirects: RedNoteResolver.SHORT_LINK_MAX_REDIRECTS,
        timeout: RedNoteResolver.SHORT_LINK_TIMEOUT_MS,
        headers: { 'User-Agent': RedNoteResolver.USER_AGENT },
      })

      // axios exposes the final URL after redirects in different shapes depending
      // on the runtime; cover both Node (response.request.res.responseUrl) and
      // the generic fallback (response.config.url).
      const finalUrl: string | undefined
        = (response.request as { res?: { responseUrl?: string } })?.res?.responseUrl
          ?? response.config.url
      if (!finalUrl) {
        return { noteId: null }
      }

      const resolvedUrl = new URL(finalUrl)
      if (resolvedUrl.hostname.replace(/^www\./, '') !== RedNoteResolver.HOSTNAME_PRIMARY) {
        return { noteId: null }
      }

      return {
        noteId: this.extractNoteId(resolvedUrl),
        resolvedUrl: finalUrl,
        xsecToken: this.getXsecToken(resolvedUrl),
      }
    }
    catch (error) {
      console.warn(
        `[pulse-resolve] failed to resolve RedNote short link: ${shortUrl}`,
        error instanceof Error ? error.message : error,
      )
      return { noteId: null }
    }
  }

  /**
   * Extract the `xsec_token` query param. Trimmed; returns undefined when absent.
   * This token is REQUIRED for the URL to be visitable.
   */
  private getXsecToken(url: URL): string | undefined {
    return url.searchParams.get('xsec_token')?.trim() || undefined
  }
}
