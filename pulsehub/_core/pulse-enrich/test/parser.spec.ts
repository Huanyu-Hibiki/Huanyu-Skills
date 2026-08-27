import { describe, expect, it } from 'vitest'
import { parseLLMResponse } from '../src/parser.js'

describe('parseLLMResponse', () => {
  describe('valid JSON inputs', () => {
    it('parses clean JSON', () => {
      const content = JSON.stringify({
        purchaseIntent: true,
        questionIntent: false,
        complaint: false,
        matchedKeywords: ['求链接', '多少钱'],
        score: 'high',
        scoreReason: 'Strong purchase intent',
        suggestedAngle: 'Mention product specs',
      })
      const result = parseLLMResponse(content)
      expect(result.signals.purchaseIntent).toBe(true)
      expect(result.signals.questionIntent).toBe(false)
      expect(result.signals.matchedKeywords).toEqual(['求链接', '多少钱'])
      expect(result.score).toBe('high')
      expect(result.scoreReason).toBe('Strong purchase intent')
      expect(result.suggestedAngle).toBe('Mention product specs')
    })

    it('parses JSON with markdown fence', () => {
      const content = '```json\n{"purchaseIntent": true, "questionIntent": false, "complaint": false, "matchedKeywords": [], "score": "medium", "scoreReason": "x", "suggestedAngle": "y"}\n```'
      const result = parseLLMResponse(content)
      expect(result.signals.purchaseIntent).toBe(true)
      expect(result.score).toBe('medium')
    })

    it('parses JSON with bare fence (no language)', () => {
      const content = '```\n{"purchaseIntent": false, "questionIntent": true, "complaint": false, "matchedKeywords": [], "score": "low", "scoreReason": "x", "suggestedAngle": "y"}\n```'
      const result = parseLLMResponse(content)
      expect(result.signals.questionIntent).toBe(true)
    })

    it('parses JSON embedded in prose', () => {
      const content = `Here's my analysis:
{"purchaseIntent": true, "questionIntent": false, "complaint": false, "matchedKeywords": ["求链接"], "score": "high", "scoreReason": "x", "suggestedAngle": "y"}
Hope this helps!`
      const result = parseLLMResponse(content)
      expect(result.signals.purchaseIntent).toBe(true)
      expect(result.signals.matchedKeywords).toEqual(['求链接'])
    })

    it('parses JSON with trailing prose after object', () => {
      const content = `{"purchaseIntent": false, "questionIntent": false, "complaint": false, "matchedKeywords": [], "score": "low", "scoreReason": "x", "suggestedAngle": "y"}

Note: this content has no commercial intent.`
      const result = parseLLMResponse(content)
      expect(result.score).toBe('low')
    })
  })

  describe('field normalization', () => {
    it('coerces truthy non-boolean values', () => {
      const content = '{"purchaseIntent": 1, "questionIntent": "yes", "complaint": 0, "matchedKeywords": [], "score": "high", "scoreReason": "x", "suggestedAngle": "y"}'
      const result = parseLLMResponse(content)
      expect(result.signals.purchaseIntent).toBe(true)
      expect(result.signals.questionIntent).toBe(true)
      expect(result.signals.complaint).toBe(false)
    })

    it('normalizes invalid score to "low"', () => {
      const content = '{"purchaseIntent": false, "questionIntent": false, "complaint": false, "matchedKeywords": [], "score": "invalid", "scoreReason": "x", "suggestedAngle": "y"}'
      const result = parseLLMResponse(content)
      expect(result.score).toBe('low')
    })

    it('normalizes missing score to "low"', () => {
      const content = '{"purchaseIntent": false, "questionIntent": false, "complaint": false, "matchedKeywords": []}'
      const result = parseLLMResponse(content)
      expect(result.score).toBe('low')
      expect(result.scoreReason).toBe('(no reason provided)')
      expect(result.suggestedAngle).toBe('(no angle suggested)')
    })

    it('filters non-string matchedKeywords', () => {
      const content = '{"purchaseIntent": true, "questionIntent": false, "complaint": false, "matchedKeywords": ["valid", 42, null, "also-valid"], "score": "high", "scoreReason": "x", "suggestedAngle": "y"}'
      const result = parseLLMResponse(content)
      expect(result.signals.matchedKeywords).toEqual(['valid', 'also-valid'])
    })

    it('handles missing matchedKeywords', () => {
      const content = '{"purchaseIntent": false, "questionIntent": false, "complaint": false, "score": "low", "scoreReason": "x", "suggestedAngle": "y"}'
      const result = parseLLMResponse(content)
      expect(result.signals.matchedKeywords).toEqual([])
    })
  })

  describe('error cases', () => {
    it('throws on no JSON at all', () => {
      expect(() => parseLLMResponse('Just prose, no JSON here.')).toThrow(/No JSON found/)
    })

    it('throws on empty string', () => {
      expect(() => parseLLMResponse('')).toThrow(/No JSON found/)
    })

    it('throws on malformed JSON', () => {
      const content = '{"purchaseIntent": true, "score": "high"' // missing closing brace
      expect(() => parseLLMResponse(content)).toThrow(/not valid JSON/)
    })
  })

  describe('nested JSON in strings', () => {
    it('does not confuse braces inside string values', () => {
      // The `{` inside the string value should not break brace matching
      const content = '{"purchaseIntent": false, "questionIntent": false, "complaint": false, "matchedKeywords": [], "score": "low", "scoreReason": "contains } char", "suggestedAngle": "y"}'
      const result = parseLLMResponse(content)
      expect(result.scoreReason).toBe('contains } char')
    })

    it('handles escaped quotes in strings', () => {
      const content = '{"purchaseIntent": false, "questionIntent": false, "complaint": false, "matchedKeywords": [], "score": "low", "scoreReason": "he said \\"hi\\"", "suggestedAngle": "y"}'
      const result = parseLLMResponse(content)
      expect(result.scoreReason).toBe('he said "hi"')
    })
  })
})
