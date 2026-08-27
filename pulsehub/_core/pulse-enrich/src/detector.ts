/**
 * Signal detector — keyword-based detection for Chinese social content.
 *
 * This is the fast, free, offline fallback. For higher accuracy (recognizing
 * sarcasm, context-dependent intent, etc.), use the LLM enricher in `llm.ts`.
 *
 * Source: signals/ library in the PulseHub repo.
 */

import type { OpportunitySignals } from '@pulsehub/types'

// ─── keyword libraries ─────────────────────────────────────────────────────
// Curated from signals/purchase-intent.md, signals/question-intent.md, signals/complaint.md

const PURCHASE_KEYWORDS = [
  // Generic
  '求链接', '求链接啊', '链接呢', '链接一下',
  '怎么买', '哪里买', '哪里能买', '上哪买', '怎么下单', '怎么付款',
  '多少钱', '多少米', '什么价位', '价格多少', '价格',
  '想要', '想买', '种草', '被种草',
  '求同款', '求型号', '求牌子',
  '预算',
  // Confirmation
  '已下单', '已入手', '已购入', '已拍',
  // Resale
  '出二手', '闲鱼出',
] as const

const QUESTION_KEYWORDS = [
  '求推荐', '求安利', '求建议',
  '怎么选', '怎么挑', '选哪个', '哪个好', '哪个好用',
  '值得买吗', '值不值', '划算吗',
  '有用过的吗', '有人试过吗', '谁买过',
  '怎么用', '怎么做', '怎么操作',
  '能出个', '能测一下',
  '求教程', '求攻略',
] as const

const COMPLAINT_KEYWORDS = [
  '太贵了', '不值', '性价比低', '不划算',
  '差评', '翻车', '踩雷', '退货', '退款',
  '售后差', '客服差',
  '别买', '别上当', '避雷', '千万别买',
  '假货', '高仿', '山寨', '仿冒',
  '智商税', '割韭菜',
  '失望', '后悔',
] as const

// Negation prefixes — if any of these precede a keyword within N chars, it's NOT that signal
const NEGATIONS = ['不', '没', '别', '勿', '无', '非']

// ─── detector ──────────────────────────────────────────────────────────────

export interface KeywordDetectionResult extends OpportunitySignals {
  /** Raw matched keywords, for transparency in the output report. */
  matched: {
    purchase: string[]
    question: string[]
    complaint: string[]
  }
}

/**
 * Detect signals in text using keyword matching with negation awareness.
 *
 * @param text combined title + description (+ optional transcript)
 * @returns detected signals + matched keyword lists
 */
export function detectSignals(text: string): KeywordDetectionResult {
  const lower = text.toLowerCase()

  const purchase = filterNegated(lower, PURCHASE_KEYWORDS)
  const question = filterNegated(lower, QUESTION_KEYWORDS)
  const complaint = filterNegated(lower, COMPLAINT_KEYWORDS)

  return {
    purchaseIntent: purchase.length > 0,
    questionIntent: question.length > 0,
    complaint: complaint.length > 0,
    matchedKeywords: [...purchase, ...question, ...complaint],
    matched: {
      purchase,
      question,
      complaint,
    },
  }
}

/**
 * Filter out negated matches: if any negation char appears within 3 chars
 * before the keyword, the match is suppressed.
 *
 * Example: "不想要" contains "想要" but is preceded by "不" → suppressed.
 *
 * This is a simple heuristic. For Chinese content with complex negation,
 * fall back to LLM analysis (`llm.ts`).
 */
function filterNegated(haystack: string, keywords: readonly string[]): string[] {
  const matches: string[] = []
  for (const kw of keywords) {
    let fromIndex = 0
    while (true) {
      const idx = haystack.indexOf(kw, fromIndex)
      if (idx === -1) break
      // Check the 3 chars before the match for negation
      const prefixStart = Math.max(0, idx - 3)
      const prefix = haystack.slice(prefixStart, idx)
      const isNegated = NEGATIONS.some(neg => prefix.includes(neg))
      if (!isNegated) {
        matches.push(kw)
        break // one match per keyword is enough
      }
      fromIndex = idx + kw.length
    }
  }
  return matches
}
