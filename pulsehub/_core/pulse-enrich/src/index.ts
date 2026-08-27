/**
 * pulse-enrich — Agent-native signal detection + scoring.
 *
 * PulseHub does NOT call any LLM directly. Instead:
 *   1. `prepareEnrichment()` runs keyword detection locally + builds an LLM prompt
 *   2. The caller (AI Agent) invokes its own LLM with the prompt
 *   3. `parseLLMResponse()` normalizes the LLM's response
 *
 * This means PulseHub works with any AI Agent (Claude Code, Cursor, Hermes,
 * opencode, etc.) without requiring OPENAI_API_KEY or any LLM configuration.
 * The Agent's currently-selected model is always used.
 *
 * For non-Agent use (CLI scripts, batch jobs), use `enrichWithLLMCallback()`
 * and pass your own LLM invocation function.
 */

import type { Opportunity, OpportunityMetadata, ResolvedLink } from '@pulsehub/types'
import { detectSignals, type KeywordDetectionResult } from './detector.js'
import { scoreOpportunity, type ScoringResult } from './scorer.js'
import { buildEnrichmentPrompt, type EnrichmentPrompt } from './prompt.js'
import { parseLLMResponse, type LLMEnrichmentResponse } from './parser.js'

export interface PreparedEnrichment {
  /** Result of local keyword detection. Always available, no LLM needed. */
  keywordSignals: KeywordDetectionResult
  /** Score computed from keywords alone (used if no LLM is available). */
  keywordScore: ScoringResult
  /** LLM prompt for the calling Agent to feed into its own model. */
  llmPrompt?: EnrichmentPrompt
}

export interface EnrichResult extends Opportunity {
  /** Suggested comment angle (only present if LLM was used). */
  suggestedAngle?: string
  /** Raw keyword detection output (always present). */
  keywordDetection: KeywordDetectionResult
}

/**
 * Step 1 + 2 of the enrichment pipeline.
 *
 * Runs local keyword detection + scoring, and prepares an LLM prompt for the
 * calling Agent to invoke with its own model.
 *
 * The Agent's flow becomes:
 * ```ts
 * const prep = prepareEnrichment(link, metadata)
 * // Use keyword-only result if you don't want LLM analysis:
 * console.log(prep.keywordScore)
 * // OR: invoke the Agent's LLM with the prompt:
 * const llmResponse = await agent.invokeLLM(prep.llmPrompt.system, prep.llmPrompt.user)
 * const llmResult = parseLLMResponse(llmResponse)
 * const opp = combineResults(link, metadata, prep, llmResult)
 * ```
 */
export function prepareEnrichment(
  link: ResolvedLink,
  metadata: OpportunityMetadata = {},
): PreparedEnrichment {
  const text = [metadata.title, metadata.description].filter(Boolean).join('\n\n')
  const keywordSignals = detectSignals(text)

  const publishedAt = metadata.publishedAt ? new Date(metadata.publishedAt) : null
  const keywordScore = scoreOpportunity({
    signals: keywordSignals,
    publishedAt,
    platform: link.platform,
  })

  // Build LLM prompt only if there's text to analyze
  const llmPrompt = text.length > 0
    ? buildEnrichmentPrompt(link, metadata, keywordSignals)
    : undefined

  return { keywordSignals, keywordScore, llmPrompt }
}

/**
 * Step 3: Parse the LLM's response into structured data.
 *
 * Tolerant of markdown fences, trailing prose, and minor JSON errors.
 */
export function parseLLMResult(content: string): LLMEnrichmentResponse {
  return parseLLMResponse(content)
}

/**
 * Combine keyword + LLM results into a final Opportunity.
 *
 * If LLM analysis succeeded, use its score + reason (more nuanced).
 * Otherwise fall back to keyword-based scoring.
 */
export function combineResults(
  link: ResolvedLink,
  metadata: OpportunityMetadata,
  prepared: PreparedEnrichment,
  llmResult?: LLMEnrichmentResponse,
): EnrichResult {
  return {
    link,
    metadata,
    signals: llmResult?.signals ?? {
      purchaseIntent: prepared.keywordSignals.purchaseIntent,
      questionIntent: prepared.keywordSignals.questionIntent,
      complaint: prepared.keywordSignals.complaint,
      matchedKeywords: prepared.keywordSignals.matchedKeywords,
    },
    score: llmResult?.score ?? prepared.keywordScore.score,
    scoreReason: llmResult?.scoreReason ?? prepared.keywordScore.reason,
    enrichedAt: new Date().toISOString(),
    suggestedAngle: llmResult?.suggestedAngle,
    keywordDetection: prepared.keywordSignals,
  }
}

/**
 * Convenience: full pipeline with an external LLM callback.
 *
 * For AI Agents: prefer using `prepareEnrichment` + `parseLLMResult` directly,
 * so your Agent can see and reason about the LLM prompt before invoking.
 *
 * For CLI scripts / batch jobs: use this with your own LLM invocation function.
 *
 * @example
 *   const opp = await enrichWithLLMCallback(link, metadata, async (prompt) => {
 *     return await myLLMClient.complete(prompt.system, prompt.user)
 *   })
 */
export async function enrichWithLLMCallback(
  link: ResolvedLink,
  metadata: OpportunityMetadata | undefined,
  callLLM: (prompt: EnrichmentPrompt) => Promise<string>,
): Promise<EnrichResult> {
  const prepared = prepareEnrichment(link, metadata ?? {})

  if (!prepared.llmPrompt) {
    // No text to analyze — return keyword-only result
    return combineResults(link, metadata ?? {}, prepared)
  }

  try {
    const llmText = await callLLM(prepared.llmPrompt)
    const llmResult = parseLLMResult(llmText)
    return combineResults(link, metadata ?? {}, prepared, llmResult)
  }
  catch (error) {
    console.warn(
      '[pulse-enrich] LLM callback failed, falling back to keyword scoring:',
      error instanceof Error ? error.message : error,
    )
    return combineResults(link, metadata ?? {}, prepared)
  }
}

/**
 * Keyword-only enrichment. No LLM involved — use this in pure CLI mode or when
 * you explicitly want fast deterministic scoring.
 */
export function enrichWithKeywords(
  link: ResolvedLink,
  metadata: OpportunityMetadata = {},
): EnrichResult {
  const prepared = prepareEnrichment(link, metadata)
  return combineResults(link, metadata, prepared)
}

// Re-exports for convenience
export { detectSignals } from './detector.js'
export { scoreOpportunity, minutesUntilWindowCloses } from './scorer.js'
export { buildEnrichmentPrompt } from './prompt.js'
export { parseLLMResponse } from './parser.js'
export type { KeywordDetectionResult } from './detector.js'
export type { ScoringResult } from './scorer.js'
export type { EnrichmentPrompt } from './prompt.js'
export type { LLMEnrichmentResponse } from './parser.js'
