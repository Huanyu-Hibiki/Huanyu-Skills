import type { ResolvedLink } from '@pulsehub/types'

export interface Resolver {
  /** Try to parse `rawLink`. Return null if this resolver doesn't handle it. */
  resolve(rawLink: string): Promise<ResolvedLink | null>
}
