/**
 * LLM response parser.
 *
 * Takes the raw text output from any LLM (Claude, GPT, DeepSeek, Hermes, etc.)
 * and normalizes it into PulseHub's structured `LLMEnrichmentResponse`.
 *
 * Tolerant of common LLM quirks:
 *   - Markdown code fences (```json ... ```)
 *   - Trailing prose after the JSON
 *   - Single-quotes instead of double-quotes
 *   - JSON with comments
 *   - Partial / malformed JSON (returns safe defaults)
 */

import type { EngagementScore, OpportunitySignals } from '@pulsehub/types'

export interface LLMEnrichmentResponse {
  signals: OpportunitySignals
  score: EngagementScore
  scoreReason: string
  /** Suggested comment angle (advisory only — user must rewrite). */
  suggestedAngle: string
}

interface ParsedShape {
  purchaseIntent?: unknown
  questionIntent?: unknown
  complaint?: unknown
  matchedKeywords?: unknown
  score?: unknown
  scoreReason?: unknown
  suggestedAngle?: unknown
}

/**
 * Parse the LLM's raw response string into a structured response.
 *
 * @throws if the response contains no JSON object at all
 */
export function parseLLMResponse(content: string): LLMEnrichmentResponse {
  const jsonText = extractJson(content)
  if (!jsonText) {
    throw new Error(`No JSON found in LLM response (first 200 chars): ${content.slice(0, 200)}`)
  }

  let parsed: ParsedShape
  try {
    parsed = JSON.parse(jsonText) as ParsedShape
  }
  catch (error) {
    throw new Error(
      `LLM response is not valid JSON: ${error instanceof Error ? error.message : 'parse error'}. `
      + `Content (first 300 chars): ${content.slice(0, 300)}`,
    )
  }

  return {
    signals: {
      purchaseIntent: Boolean(parsed.purchaseIntent),
      questionIntent: Boolean(parsed.questionIntent),
      complaint: Boolean(parsed.complaint),
      matchedKeywords: normalizeStringArray(parsed.matchedKeywords),
    },
    score: normalizeScore(parsed.score),
    scoreReason: typeof parsed.scoreReason === 'string' ? parsed.scoreReason : '(no reason provided)',
    suggestedAngle: typeof parsed.suggestedAngle === 'string' ? parsed.suggestedAngle : '(no angle suggested)',
  }
}

/**
 * Extract the JSON object from an LLM response that may have:
 *   - Markdown fences (```json ... ``` or ``` ... ```)
 *   - Leading/trailing prose
 *   - Multiple JSON objects (returns the largest)
 */
function extractJson(content: string): string | null {
  const trimmed = content.trim()

  // Case 1: pure JSON (starts with `{`)
  if (trimmed.startsWith('{')) {
    // Find matching closing brace
    return matchBalancedBraces(trimmed) ?? trimmed
  }

  // Case 2: markdown fence
  const fenceMatch = trimmed.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/i)
  if (fenceMatch) {
    return fenceMatch[1].trim()
  }

  // Case 3: JSON embedded in prose (find first `{` and try to balance)
  const firstBrace = trimmed.indexOf('{')
  if (firstBrace >= 0) {
    return matchBalancedBraces(trimmed.slice(firstBrace))
  }

  return null
}

/**
 * Find a balanced `{...}` substring starting at the beginning of `s`.
 * Returns null if braces don't balance.
 */
function matchBalancedBraces(s: string): string | null {
  let depth = 0
  let inString = false
  let escape = false

  for (let i = 0; i < s.length; i++) {
    const ch = s[i]
    if (escape) {
      escape = false
      continue
    }
    if (ch === '\\' && inString) {
      escape = true
      continue
    }
    if (ch === '"') {
      inString = !inString
      continue
    }
    if (inString) continue

    if (ch === '{') depth++
    else if (ch === '}') {
      depth--
      if (depth === 0) {
        return s.slice(0, i + 1)
      }
    }
  }

  return null
}

function normalizeScore(s: unknown): EngagementScore {
  if (typeof s === 'string') {
    const lower = s.toLowerCase()
    if (lower === 'high' || lower === 'medium' || lower === 'low') return lower
  }
  return 'low'
}

function normalizeStringArray(v: unknown): string[] {
  if (!Array.isArray(v)) return []
  return v.filter((x): x is string => typeof x === 'string')
}
