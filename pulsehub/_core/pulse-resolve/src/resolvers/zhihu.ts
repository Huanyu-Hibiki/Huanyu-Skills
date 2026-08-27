import type { ResolvedLink } from '@pulsehub/types'
import type { Resolver } from './types.js'

/**
 * Zhihu URL resolver.
 *
 * Not ported from AiToEarn — AiToEarn has no Zhihu support.
 * Implemented from scratch based on canonical Zhihu URL formats.
 *
 * Handles:
 *   - Answers:    zhihu.com/question/{qid}/answer/{aid}
 *   - Articles:   zhuanlan.zhihu.com/p/{pid}
 *
 * Note: Zhihu also has 想法 (pins) at zhihu.com/pin/{pid}, but those are
 * low-value for engagement (no public comment API) and not supported here.
 */
export class ZhihuResolver implements Resolver {
  private static readonly HOSTNAME_PRIMARY = 'zhihu.com'
  private static readonly HOSTNAME_ZHUANLAN = 'zhuanlan.zhihu.com'

  async resolve(rawLink: string): Promise<ResolvedLink | null> {
    let url: URL
    try {
      url = new URL(rawLink)
    }
    catch {
      return null
    }

    const hostname = url.hostname.replace(/^www\./, '')

    if (hostname === ZhihuResolver.HOSTNAME_ZHUANLAN) {
      return this.resolveZhuanlanArticle(url, rawLink)
    }

    if (hostname === ZhihuResolver.HOSTNAME_PRIMARY) {
      return this.resolveQuestionAnswer(url, rawLink)
    }

    return null
  }

  /**
   * Resolve zhuanlan.zhihu.com/p/{pid} → article.
   */
  private resolveZhuanlanArticle(url: URL, originalLink: string): ResolvedLink | null {
    const match = url.pathname.match(/\/p\/(\d+)/)
    if (!match) {
      return null
    }

    const articleId = match[1]
    return {
      platform: 'zhihu',
      workId: `p-${articleId}`,
      url: `https://zhuanlan.zhihu.com/p/${articleId}`,
      originalLink,
      resolvedAt: new Date().toISOString(),
    }
  }

  /**
   * Resolve zhihu.com/question/{qid}/answer/{aid} → answer.
   *
   * Also handles /question/{qid} without /answer/ (question page itself,
   * no specific answer selected). In that case workId is the question ID.
   */
  private resolveQuestionAnswer(url: URL, originalLink: string): ResolvedLink | null {
    const segments = url.pathname.split('/').filter(Boolean)

    // Format: /question/{qid}/answer/{aid}
    if (segments[0] === 'question' && segments[1] && segments[2] === 'answer' && segments[3]) {
      const questionId = segments[1]
      const answerId = segments[3]
      return {
        platform: 'zhihu',
        workId: `a-${answerId}`,
        url: `https://www.zhihu.com/question/${questionId}/answer/${answerId}`,
        originalLink,
        resolvedAt: new Date().toISOString(),
      }
    }

    // Format: /question/{qid}  (question page, no specific answer)
    if (segments[0] === 'question' && segments[1]) {
      const questionId = segments[1]
      return {
        platform: 'zhihu',
        workId: `q-${questionId}`,
        url: `https://www.zhihu.com/question/${questionId}`,
        originalLink,
        resolvedAt: new Date().toISOString(),
      }
    }

    return null
  }
}
