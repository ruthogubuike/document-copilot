import type { UIMessage } from 'ai'

import type { CitationContextChunk, CitationData } from '@/lib/types/citation'

const CITATION_MARKER_RE = /\[(\d+)\]/g

const INSUFFICIENT_EVIDENCE_PHRASES = [
  'not enough evidence',
  'insufficient evidence',
  'corpus does not contain',
  'does not contain enough',
  'does not contain any',
  'do not contain any',
  'do not contain',
  'cannot find',
  'no evidence',
  'not in the corpus',
  'do not support that inference',
  'filings do not',
  'no information',
  'not disclosed',
  'no disclosed',
  'not stated',
  'no stated',
  'does not state',
  'does not mention',
  'not available',
  'filings reviewed',
] as const

type MessagePart = UIMessage['parts'][number]

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function parseContextChunks(value: unknown): CitationContextChunk[] {
  if (!Array.isArray(value)) {
    return []
  }

  const chunks: CitationContextChunk[] = []
  for (const entry of value) {
    if (
      isRecord(entry) &&
      typeof entry.chunkIndex === 'number' &&
      typeof entry.text === 'string'
    ) {
      chunks.push({
        chunkIndex: entry.chunkIndex,
        text: entry.text,
        isCited: entry.isCited === true,
      })
    }
  }
  return chunks
}

function parseCitationData(data: unknown): CitationData | null {
  if (!isRecord(data)) {
    return null
  }

  const {
    citationIndex,
    chunkId,
    ticker,
    companyName,
    form,
    filingDate,
    page,
    section,
    excerpt,
    chunkIndex,
    context,
  } = data

  if (
    typeof citationIndex !== 'number' ||
    typeof chunkId !== 'string' ||
    typeof ticker !== 'string' ||
    typeof companyName !== 'string' ||
    typeof form !== 'string' ||
    typeof filingDate !== 'string' ||
    typeof excerpt !== 'string'
  ) {
    return null
  }

  return {
    citationIndex,
    chunkId,
    ticker,
    companyName,
    form,
    filingDate,
    page: typeof page === 'number' ? page : null,
    section: typeof section === 'string' ? section : null,
    excerpt,
    chunkIndex: typeof chunkIndex === 'number' ? chunkIndex : null,
    context: parseContextChunks(context),
  }
}

export function isCitationPart(part: MessagePart): part is MessagePart & {
  type: 'data-citation'
  data: CitationData
} {
  if (part.type !== 'data-citation') {
    return false
  }

  if (!('data' in part)) {
    return false
  }

  return parseCitationData(part.data) !== null
}

export function getCitationParts(message: UIMessage): CitationData[] {
  const citations: CitationData[] = []

  for (const part of message.parts) {
    if (!isCitationPart(part)) {
      continue
    }

    const parsed = parseCitationData(part.data)
    if (parsed) {
      citations.push(parsed)
    }
  }

  return citations.sort((a, b) => a.citationIndex - b.citationIndex)
}

const filingDateFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
})

export function formatCitationLabel(citation: CitationData): string {
  const dateLabel = filingDateFormatter.format(new Date(citation.filingDate))
  const parts = [`${citation.ticker} ${citation.form}`, dateLabel]

  if (citation.page !== null) {
    parts.push(`p. ${citation.page}`)
  } else if (citation.section) {
    parts.push(citation.section)
  }

  return parts.join(' · ')
}

export type TextWithCitationSegment =
  | { kind: 'text'; value: string }
  | { kind: 'citation'; index: number; citation: CitationData | null }

export function splitTextWithCitationMarkers(
  text: string,
  citations: CitationData[],
): TextWithCitationSegment[] {
  const byIndex = new Map(citations.map((c) => [c.citationIndex, c]))
  const segments: TextWithCitationSegment[] = []
  let lastIndex = 0

  for (const match of text.matchAll(CITATION_MARKER_RE)) {
    const matchIndex = match.index ?? 0
    const markerIndex = Number(match[1])

    if (matchIndex > lastIndex) {
      segments.push({ kind: 'text', value: text.slice(lastIndex, matchIndex) })
    }

    segments.push({
      kind: 'citation',
      index: markerIndex,
      citation: byIndex.get(markerIndex) ?? null,
    })

    lastIndex = matchIndex + match[0].length
  }

  if (lastIndex < text.length) {
    segments.push({ kind: 'text', value: text.slice(lastIndex) })
  }

  return segments
}

export function looksLikeInsufficientEvidence(text: string): boolean {
  const normalized = text.toLowerCase()
  return INSUFFICIENT_EVIDENCE_PHRASES.some((phrase) => normalized.includes(phrase))
}

export function shouldShowNoCorpusCallout(
  text: string,
  citations: CitationData[],
): boolean {
  return citations.length === 0 && looksLikeInsufficientEvidence(text)
}
