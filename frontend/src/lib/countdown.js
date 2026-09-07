import { computed, onUnmounted, ref, toValue } from 'vue'

// Frappe sends UTC datetimes as "YYYY-MM-DD HH:MM:SS" with no zone marker, so the
// browser would otherwise read a hold deadline in its own timezone.
function parseUtc(value) {
  return value ? Date.parse(`${String(value).replace(' ', 'T')}Z`) : null
}

export function useCountdown(deadline) {
  const now = ref(Date.now())
  const ticker = setInterval(() => (now.value = Date.now()), 1000)
  onUnmounted(() => clearInterval(ticker))

  const secondsLeft = computed(() => {
    const at = parseUtc(toValue(deadline))
    return at ? Math.max(0, Math.round((at - now.value) / 1000)) : 0
  })

  const label = computed(
    () => `${Math.floor(secondsLeft.value / 60)}:${String(secondsLeft.value % 60).padStart(2, '0')}`,
  )

  return { secondsLeft, label }
}
