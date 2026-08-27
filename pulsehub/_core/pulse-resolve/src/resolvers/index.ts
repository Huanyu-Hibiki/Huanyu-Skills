import type { ResolvedLink } from '@pulsehub/types'
import type { Resolver } from './types.js'

/**
 * Resolvers registered here will be tried in order.
 * The first one that returns a non-null result wins.
 *
 * To add a new platform:
 *   1. Implement `Resolver` in `./<platform>.ts`
 *   2. Import and add to the `resolvers` array below
 *   3. Add tests in `../test/<platform>.spec.ts`
 */
import { BilibiliResolver } from './bilibili.js'
import { DouyinResolver } from './douyin.js'
import { RedNoteResolver } from './rednote.js'
import { WeChatOfficialResolver } from './wechat-official.js'
import { ZhihuResolver } from './zhihu.js'

const resolvers: Resolver[] = [
  new BilibiliResolver(),
  new DouyinResolver(),
  new RedNoteResolver(),
  new WeChatOfficialResolver(),
  new ZhihuResolver(),
  // TODO: wechat_channels (requires scan-login, not URL-resolvable from outside)
]

/**
 * Try each resolver in order. Returns null if no resolver matches.
 *
 * @example
 *   const link = await resolveLink('https://xhslink.com/a/abc123')
 *   // → { platform: 'rednote', workId: '...', url: '...', token: { xsec_token: '...' }, ... }
 */
export async function resolveLink(rawLink: string): Promise<ResolvedLink | null> {
  for (const resolver of resolvers) {
    const result = await resolver.resolve(rawLink)
    if (result) {
      return result
    }
  }
  return null
}

export { type Resolver } from './types.js'
export { BilibiliResolver } from './bilibili.js'
export { DouyinResolver } from './douyin.js'
export { RedNoteResolver } from './rednote.js'
export { WeChatOfficialResolver } from './wechat-official.js'
export { ZhihuResolver } from './zhihu.js'
