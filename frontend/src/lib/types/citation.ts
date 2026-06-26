export type CitationContextChunk = {
  chunkIndex: number
  text: string
  isCited: boolean
}

export type CitationData = {
  citationIndex: number
  chunkId: string
  ticker: string
  companyName: string
  form: string
  filingDate: string
  page: number | null
  section: string | null
  excerpt: string
  chunkIndex: number | null
  context: CitationContextChunk[]
}
