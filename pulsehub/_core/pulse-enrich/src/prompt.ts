/**
 * LLM prompt builder for content enrichment.
 *
 * PulseHub does NOT call any LLM API directly. Instead, it generates a
 * structured prompt that the calling AI Agent (Claude Code, Cursor,
 * opencode, etc.) feeds into its OWN configured LLM. The Agent then passes
 * the LLM's response back to `parser.ts` for normalization.
 *
 * This design means:
 *   - No OPENAI_API_KEY needed
 *   - No redundant LLM configuration
 *   - The Agent's currently-selected model is always used
 *   - PulseHub works in any Agent framework without LLM-specific glue
 */

import type { OpportunityMetadata, Platform, ResolvedLink } from '@pulsehub/types'
import type { KeywordDetectionResult } from './detector.js'

export interface EnrichmentPrompt {
  /** System prompt — defines the LLM's role and output format. */
  system: string
  /** User prompt — the specific content to analyze. */
  user: string
  /** Context metadata, for the caller's bookkeeping. */
  context: {
    platform: Platform
    publishedAt?: string
    keywordSignals: KeywordDetectionResult
  }
}

const SYSTEM_PROMPT = `You are a Chinese social media engagement analyst.

Your job: analyze the given content (title + description, possibly transcript) and detect engagement signals.

Signal categories:
1. purchase-intent — author or commenters want to BUY something (求链接, 怎么买, 多少钱, 种草, 求同款, etc.)
2. question-intent — author is asking for ADVICE (求推荐, 怎么选, 值得买吗, etc.)
3. complaint — author is UNHAPPY with a product/service (翻车, 踩雷, 别买, 假货, etc.)

Watch for Chinese internet slang and sarcasm. "想要" with 😂 emoji is likely ironic, not real purchase intent.

Return ONLY valid JSON in this exact shape (no markdown fences, no extra text):
{
  "purchaseIntent": boolean,
  "questionIntent": boolean,
  "complaint": boolean,
  "matchedKeywords": ["求推荐", "预算"],
  "score": "high" | "medium" | "low",
  "scoreReason": "one short sentence explaining the score",
  "suggestedAngle": "one short sentence suggesting the comment angle (in Chinese)"
}

Scoring guide:
- "high": strong purchase intent + content is fresh (assume fresh if no date given)
- "medium": question intent, or purchase intent but unclear budget/urgency
- "low": no signal, complaint only, or sarcasm detected

Never include actual comment text — only suggest the ANGLE.`

/**
 * Build an LLM prompt for analyzing a piece of content.
 *
 * The caller (AI Agent) is responsible for actually invoking its LLM with
 * this prompt and returning the response string to `parseLLMResponse()`.
 *
 * @example
 *   const prompt = buildEnrichmentPrompt(link, metadata, keywordSignals)
 *   // Agent uses its own LLM:
 *   const llmResponse = await agent.invokeLLM(prompt.system, prompt.user)
 *   // Parse back into structured data:
 *   const result = parseLLMResponse(llmResponse)
 */
export function buildEnrichmentPrompt(
  link: ResolvedLink,
  metadata: OpportunityMetadata,
  keywordSignals: KeywordDetectionResult,
): EnrichmentPrompt {
  const text = [metadata.title, metadata.description].filter(Boolean).join('\n\n')

  const userLines: string[] = []
  userLines.push(`Platform: ${link.platform}`)
  if (metadata.publishedAt) userLines.push(`Published: ${metadata.publishedAt}`)
  if (metadata.author) userLines.push(`Author: ${metadata.author}`)

  // Surface the keyword detection result so the LLM can confirm/reject/extend
  if (keywordSignals.matchedKeywords.length > 0) {
    userLines.push(`Keyword detection hints: ${keywordSignals.matchedKeywords.join(', ')}`)
    userLines.push(`(Use these as a starting point. Confirm or reject based on context. Watch for negation/sarcasm.)`)
  }

  userLines.push('')
  userLines.push('Content to analyze:')
  userLines.push('---')
  // Truncate to keep prompt small — most metadata fits in 1000 chars
  userLines.push(text.slice(0, 2000) || '(no text content available)')
  userLines.push('---')

  return {
    system: SYSTEM_PROMPT,
    user: userLines.join('\n'),
    context: {
      platform: link.platform,
      publishedAt: metadata.publishedAt,
      keywordSignals,
    },
  }
}
