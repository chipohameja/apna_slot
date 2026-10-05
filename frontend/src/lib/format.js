export function money(amount, currency) {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(amount)
}

export function clockTime(value) {
  return String(value).slice(0, 5)
}

export function isoDate(date) {
  return date.toISOString().slice(0, 10)
}

// "6 Oct", matching the server's `formatdate(date, "d MMM")` in refusal messages
export function shortDate(isoDay) {
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' }).format(
    new Date(`${isoDay}T00:00:00Z`),
  )
}
