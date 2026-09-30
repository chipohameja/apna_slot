<script setup>
import { Badge, Button, ErrorMessage, LoadingText, useCall } from 'frappe-ui'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import PublicLayout from '../layouts/PublicLayout.vue'
import { STATUS_THEMES } from '../lib/bookingStatus'
import { useCountdown } from '../lib/countdown'
import { humanMessage } from '../lib/errors'
import { clockTime, money } from '../lib/format'

const route = useRoute()

const booking = useCall({
  url: `/api/v2/document/Booking/${route.params.booking}`,
})

const pay = useCall({
  url: '/api/v2/method/apna_slot.api.payment.start',
  method: 'POST',
  immediate: false,
})

const held = computed(() => booking.data?.status === 'Pending Payment')
const { secondsLeft, label } = useCountdown(() => booking.data?.hold_expires_at)

async function payNow() {
  const checkout = await pay.submit({ booking: route.params.booking })
  // a real gateway hosts its own page off-site, so we follow its redirect rather than route
  if (checkout) window.location.href = checkout.redirect_url
}
</script>

<template>
  <PublicLayout>
    <div class="mx-auto flex w-full max-w-md flex-col gap-4 px-6 py-10">
      <LoadingText v-if="booking.loading && !booking.data" text="Loading booking" />

      <template v-else-if="booking.data">
        <div class="flex items-center justify-between">
          <h1 class="text-2xl font-semibold text-ink-gray-9">
            {{ held ? 'Your hold' : 'Your booking' }}
          </h1>
          <Badge
            :theme="STATUS_THEMES[booking.data.status] ?? 'gray'"
            :label="booking.data.status"
          />
        </div>

        <p v-if="held && secondsLeft" class="text-p-base text-ink-gray-6">
          These slots are yours for another
          <span class="font-medium text-ink-gray-9">{{ label }}</span
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

        <template v-if="held && secondsLeft">
          <Button variant="solid" theme="gray" :loading="pay.loading" @click="payNow">
            Pay {{ money(booking.data.total_amount, booking.data.currency) }}
          </Button>
          <ErrorMessage :message="humanMessage(pay.error)" />
        </template>
      </template>
    </div>
  </PublicLayout>
</template>
