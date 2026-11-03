export function formatAmount(amountCents: number, currency: string): string {
  return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(amountCents / 100)
}

// dateStyle/timeStyle cannot be combined with timeZoneName (Intl throws), so the zone is appended.
export function formatDateTime(isoDateTime: string): string {
  const formatted = new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'UTC',
  }).format(new Date(isoDateTime))
  return `${formatted} UTC`
}

// Due dates are plain YYYY-MM-DD; format in UTC so the day never shifts with the viewer's timezone.
export function formatDate(isoDate: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeZone: 'UTC' }).format(
    new Date(`${isoDate}T00:00:00Z`),
  )
}
