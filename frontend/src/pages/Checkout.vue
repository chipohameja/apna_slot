<script setup>
import { Badge, LoadingText, useCall } from 'frappe-ui'
import { computed, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import PublicLayout from '../layouts/PublicLayout.vue'
import { clockTime, money } from '../lib/format'

const route = useRoute()
const now = ref(Date.now())
const ticker = setInterval(() => (now.value = Date.now()), 1000)
onUnmounted(() => clearInterval(ticker))

const booking = useCall({
  url: `/api/v2/document/Booking/${route.params.booking}`,
})

const held = computed(() => booking.data?.status === 'Pending Payment')
const secondsLeft = computed(() => {
  if (!booking.data?.hold_expires_at) return 0
  const deadline = Date.parse(`${booking.data.hold_expires_at.replace(' ', 'T')}Z`)
  return Math.max(0, Math.round((deadline - now.value) / 1000))
})
const countdown = computed(() => {
  const seconds = secondsLeft.value
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
})
</script>

<template>
  <PublicLayout>
    <div class="mx-auto flex w-full max-w-md flex-col gap-4 px-6 py-10">
      <LoadingText v-if="booking.loading && !booking.data" text="Loading booking" />

      <template v-else-if="booking.data">
        <div class="flex items-center justify-between">
          <h1 class="text-2xl font-semibold text-ink-gray-9">Your hold</h1>
          <Badge :theme="held ? 'orange' : 'gray'" :label="booking.data.status" />
        </div>

        <p v-if="held && secondsLeft" class="text-p-base text-ink-gray-6">
          These slots are yours for another
          <span class="font-medium text-ink-gray-9">{{ countdown }}</span
          >.
        </p>
        <p v-else-if="held" class="text-p-base text-ink-gray-6">
          This hold has lapsed. The slots go back to the grid on the next sweep.
        </p>

        <div class="divide-y divide-outline-gray-1 rounded border border-outline-gray-1">
          <div
            v-for="line in booking.data.lines"
            :key="line.name"
            class="flex items-center justify-between px-4 py-3"
          >
            <div>
              <p class="text-p-base text-ink-gray-8">
                {{ line.line_date }} · {{ clockTime(line.start_time) }}–{{ clockTime(line.end_time) }}
              </p>
              <p class="text-p-xs text-ink-gray-5">{{ line.price_rule }}</p>
            </div>
            <span class="text-p-base text-ink-gray-8">
              {{ money(line.price, booking.data.currency) }}
            </span>
          </div>
          <div class="flex items-center justify-between px-4 py-3">
            <span class="text-p-base font-medium text-ink-gray-9">Total</span>
            <span class="text-p-base font-medium text-ink-gray-9">
              {{ money(booking.data.total_amount, booking.data.currency) }}
            </span>
          </div>
        </div>

        <p class="text-p-sm text-ink-gray-5">Payment arrives with the mock gateway.</p>
      </template>
    </div>
  </PublicLayout>
</template>
