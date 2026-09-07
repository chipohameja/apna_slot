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
