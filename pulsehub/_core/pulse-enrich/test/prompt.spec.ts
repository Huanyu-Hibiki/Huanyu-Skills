import { describe, expect, it } from 'vitest'
import { buildEnrichmentPrompt } from '../src/prompt.js'
import { detectSignals } from '../src/detector.js'
import type { ResolvedLink } from '@pulsehub/types'

const fakeLink = (platform: ResolvedLink['platform']): ResolvedLink => ({
  platform,
  workId: 'abc123',
  url: 'https://example.com/abc123',
  originalLink: 'https://example.com/abc123',
  resolvedAt: '2026-07-27T00:00:00.000Z',
})

describe('buildEnrichmentPrompt', () => {
  it('returns system prompt with role definition', () => {
    const keywords = detectSignals('test')
    const prompt = buildEnrichmentPrompt(fakeLink('rednote'), { title: 'test' }, keywords)
    expect(prompt.system).toContain('Chinese social media engagement analyst')
    expect(prompt.system).toContain('purchase-intent')
    expect(prompt.system).toContain('JSON')
  })

  it('includes platform in user prompt', () => {
    const keywords = detectSignals('test')
    const prompt = buildEnrichmentPrompt(fakeLink('bilibili'), { title: 'test' }, keywords)
    expect(prompt.user).toContain('Platform: bilibili')
  })

  it('includes publishedAt when provided', () => {
    const keywords = detectSignals('test')
    const prompt = buildEnrichmentPrompt(
      fakeLink('rednote'),
      { title: 'test', publishedAt: '2026-07-27T10:00:00Z' },
      keywords,
    )
    expect(prompt.user).toContain('Published: 2026-07-27T10:00:00Z')
  })

  it('includes title and description in user prompt', () => {
    const keywords = detectSignals('test')
    const prompt = buildEnrichmentPrompt(
      fakeLink('rednote'),
      { title: '求推荐无线耳机', description: '预算 500 元' },
      keywords,
    )
    expect(prompt.user).toContain('求推荐无线耳机')
    expect(prompt.user).toContain('预算 500 元')
  })

  it('surfaces keyword hints to the LLM', () => {
    const keywords = detectSignals('求链接 多少钱')
    expect(keywords.matchedKeywords.length).toBeGreaterThan(0)
    const prompt = buildEnrichmentPrompt(
      fakeLink('rednote'),
      { title: '求链接 多少钱' },
      keywords,
    )
    expect(prompt.user).toContain('Keyword detection hints')
    expect(prompt.user).toContain('求链接')
  })

  it('does not include keyword hints section when no keywords matched', () => {
    const keywords = detectSignals('今天天气真好')
    expect(keywords.matchedKeywords).toHaveLength(0)
    const prompt = buildEnrichmentPrompt(
      fakeLink('rednote'),
      { title: '今天天气真好' },
      keywords,
    )
    expect(prompt.user).not.toContain('Keyword detection hints')
  })

  it('truncates long content to 2000 chars', () => {
    const longText = 'a'.repeat(3000)
    const keywords = detectSignals(longText)
    const prompt = buildEnrichmentPrompt(fakeLink('rednote'), { title: longText }, keywords)
    expect(prompt.user).toContain('---')
    expect(prompt.user.length).toBeLessThan(3000 + 1000) // prompt + framing
  })

  it('includes context object for caller bookkeeping', () => {
    const keywords = detectSignals('test')
    const prompt = buildEnrichmentPrompt(
      fakeLink('zhihu'),
      { title: 'test', publishedAt: '2026-07-27T10:00:00Z' },
      keywords,
    )
    expect(prompt.context.platform).toBe('zhihu')
    expect(prompt.context.publishedAt).toBe('2026-07-27T10:00:00Z')
    expect(prompt.context.keywordSignals).toBe(keywords)
  })
})
