export function formatRelativeTime(value: string): string {
  const date = new Date(value)
  const diffMs = date.getTime() - Date.now()
  const diffSec = Math.round(diffMs / 1000)
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })

  if (Math.abs(diffSec) < 60) {
    return rtf.format(diffSec, 'second')
  }

  const diffMin = Math.round(diffSec / 60)
  if (Math.abs(diffMin) < 60) {
    return rtf.format(diffMin, 'minute')
  }

  const diffHour = Math.round(diffMin / 60)
  if (Math.abs(diffHour) < 24) {
    return rtf.format(diffHour, 'hour')
  }

  const diffDay = Math.round(diffHour / 24)
  return rtf.format(diffDay, 'day')
}
