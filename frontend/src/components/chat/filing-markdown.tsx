import { Fragment, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

/**
 * Focused renderer for the markdown that SEC filing chunks contain: GFM pipe
 * tables, headings, simple lists, and inline emphasis. We render this subset
 * ourselves rather than pulling in a full markdown stack, since filing chunks
 * are constrained and tables are the part that actually needs structure.
 */

type Align = 'left' | 'center' | 'right'

type Block =
  | { kind: 'heading'; level: number; text: string }
  | { kind: 'paragraph'; lines: string[] }
  | { kind: 'list'; ordered: boolean; items: string[] }
  | { kind: 'table'; header: string[]; align: Align[]; rows: string[][] }

function splitRow(line: string): string[] {
  let trimmed = line.trim()
  if (trimmed.startsWith('|')) {
    trimmed = trimmed.slice(1)
  }
  if (trimmed.endsWith('|')) {
    trimmed = trimmed.slice(0, -1)
  }
  return trimmed.split('|').map((cell) => cell.trim())
}

function isTableSeparator(line: string): boolean {
  if (!line.includes('-')) {
    return false
  }
  const cells = splitRow(line)
  return cells.length > 0 && cells.every((cell) => /^:?-+:?$/.test(cell))
}

function cellAlign(cell: string): Align {
  const left = cell.startsWith(':')
  const right = cell.endsWith(':')
  if (left && right) {
    return 'center'
  }
  if (right) {
    return 'right'
  }
  return 'left'
}

function parseBlocks(markdown: string): Block[] {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n')
  const blocks: Block[] = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index]
    const trimmed = line.trim()

    if (trimmed === '') {
      index += 1
      continue
    }

    const headingMatch = /^(#{1,6})\s+(.*)$/.exec(trimmed)
    if (headingMatch) {
      blocks.push({
        kind: 'heading',
        level: headingMatch[1].length,
        text: headingMatch[2].trim(),
      })
      index += 1
      continue
    }

    if (
      trimmed.includes('|') &&
      index + 1 < lines.length &&
      isTableSeparator(lines[index + 1])
    ) {
      const header = splitRow(trimmed)
      const align = splitRow(lines[index + 1]).map(cellAlign)
      index += 2
      const rows: string[][] = []
      while (index < lines.length && lines[index].includes('|')) {
        rows.push(splitRow(lines[index]))
        index += 1
      }
      blocks.push({ kind: 'table', header, align, rows })
      continue
    }

    const listMatch = /^(\d+\.|[-*+])\s+/.exec(trimmed)
    if (listMatch) {
      const ordered = /\d/.test(listMatch[1])
      const items: string[] = []
      while (index < lines.length) {
        const itemMatch = /^(\d+\.|[-*+])\s+(.*)$/.exec(lines[index].trim())
        if (!itemMatch) {
          break
        }
        items.push(itemMatch[2].trim())
        index += 1
      }
      blocks.push({ kind: 'list', ordered, items })
      continue
    }

    const paragraph: string[] = []
    while (index < lines.length) {
      const current = lines[index].trim()
      if (
        current === '' ||
        /^(#{1,6})\s+/.test(current) ||
        /^(\d+\.|[-*+])\s+/.test(current) ||
        (current.includes('|') &&
          index + 1 < lines.length &&
          isTableSeparator(lines[index + 1]))
      ) {
        break
      }
      paragraph.push(current)
      index += 1
    }
    blocks.push({ kind: 'paragraph', lines: paragraph })
  }

  return blocks
}

const INLINE_RE = /(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*]+\*|_[^_]+_)/g

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  INLINE_RE.lastIndex = 0

  while ((match = INLINE_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index))
    }
    const token = match[0]
    const key = `${keyPrefix}-${match.index}`
    if (token.startsWith('**') || token.startsWith('__')) {
      nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>)
    } else if (token.startsWith('`')) {
      nodes.push(
        <code
          key={key}
          className="bg-muted rounded px-1 py-0.5 font-mono text-[0.85em]"
        >
          {token.slice(1, -1)}
        </code>,
      )
    } else {
      nodes.push(<em key={key}>{token.slice(1, -1)}</em>)
    }
    lastIndex = match.index + token.length
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex))
  }

  return nodes
}

const ALIGN_CLASS: Record<Align, string> = {
  left: 'text-left',
  center: 'text-center',
  right: 'text-right',
}

function renderBlock(block: Block, key: string): ReactNode {
  switch (block.kind) {
    case 'heading': {
      const Tag = `h${Math.min(block.level + 2, 6)}` as 'h3'
      return (
        <Tag key={key} className="text-foreground text-sm font-semibold">
          {renderInline(block.text, key)}
        </Tag>
      )
    }
    case 'paragraph':
      return (
        <p key={key} className="text-foreground">
          {block.lines.map((line, lineIndex) => (
            <Fragment key={`${key}-${lineIndex}`}>
              {lineIndex > 0 ? <br /> : null}
              {renderInline(line, `${key}-${lineIndex}`)}
            </Fragment>
          ))}
        </p>
      )
    case 'list': {
      const ListTag = block.ordered ? 'ol' : 'ul'
      return (
        <ListTag
          key={key}
          className={cn(
            'text-foreground space-y-1 pl-5',
            block.ordered ? 'list-decimal' : 'list-disc',
          )}
        >
          {block.items.map((item, itemIndex) => (
            <li key={`${key}-${itemIndex}`}>
              {renderInline(item, `${key}-${itemIndex}`)}
            </li>
          ))}
        </ListTag>
      )
    }
    case 'table':
      return (
        <div key={key} className="overflow-x-auto">
          <table className="border-border w-full border-collapse text-xs">
            <thead>
              <tr className="border-border border-b">
                {block.header.map((cell, cellIndex) => (
                  <th
                    key={`${key}-h-${cellIndex}`}
                    className={cn(
                      'text-muted-foreground px-2 py-1.5 font-semibold',
                      ALIGN_CLASS[block.align[cellIndex] ?? 'left'],
                    )}
                  >
                    {renderInline(cell, `${key}-h-${cellIndex}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, rowIndex) => (
                <tr
                  key={`${key}-r-${rowIndex}`}
                  className="border-border/60 border-b last:border-0"
                >
                  {block.header.map((_, cellIndex) => (
                    <td
                      key={`${key}-r-${rowIndex}-${cellIndex}`}
                      className={cn(
                        'px-2 py-1.5 align-top',
                        ALIGN_CLASS[block.align[cellIndex] ?? 'left'],
                      )}
                    >
                      {renderInline(row[cellIndex] ?? '', `${key}-c-${rowIndex}-${cellIndex}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
  }
}

type FilingMarkdownProps = {
  content: string
  className?: string
}

export function FilingMarkdown({ content, className }: FilingMarkdownProps) {
  const blocks = parseBlocks(content)
  return (
    <div className={cn('space-y-3 leading-relaxed', className)}>
      {blocks.map((block, index) => renderBlock(block, `block-${index}`))}
    </div>
  )
}
