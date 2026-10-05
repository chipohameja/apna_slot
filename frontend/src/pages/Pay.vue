<script setup>
import { Button, ErrorMessage, LoadingText, useCall } from 'frappe-ui'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useCountdown } from '../lib/countdown'
import { humanMessage } from '../lib/errors'
import { money, shortDate } from '../lib/format'

// a real gateway takes a moment to answer, and the customer should see that it does
const SETTLING_MS = 1500

const route = useRoute()
const router = useRouter()
const settling = ref(null)

const checkout = useCall({
  url: '/api/v2/method/apna_slot.api.payment.get_checkout',
  params: { token: route.params.token },
})

const pay = useCall({
  url: '/api/v2/method/apna_slot.api.payment.simulate',
  method: 'POST',
  immediate: false,
})

const { secondsLeft, label } = useCountdown(() => checkout.data?.expires_at)
const open = computed(() => ['Created', 'Pending'].includes(checkout.data?.status))
const summary = computed(() => {
  const lines = checkout.data?.lines ?? []
  const sessions = lines.length === 1 ? '1 session' : `${lines.length} sessions`
  return `${sessions} · ${checkout.data.resource_name} · from ${shortDate(lines[0]?.line_date)}`
})

async function decide(outcome) {
  settling.value = outcome
  await new Promise((resolve) => setTimeout(resolve, SETTLING_MS))
  const result = await pay.submit({ token: route.params.token, outcome })
  settling.value = null
  if (!result) return
  // abandonment is silence: the hold stands until the timer takes it
  router.push(outcome === 'abandoned' ? '/' : `/checkout/${result.booking}`)
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-surface-gray-2 px-6 py-12">
    <div
      class="w-full max-w-sm rounded-lg border border-outline-gray-2 bg-surface-white p-6 shadow-sm"
    >
      <p class="text-p-xs uppercase tracking-wide text-ink-gray-5">
        Mock Payment Gateway — no real money moves
      </p>

      <LoadingText v-if="checkout.loading && !checkout.data" text="Loading payment" />
      <ErrorMessage v-else-if="checkout.error" message="This payment link is not valid." />

      <template v-else-if="checkout.data">
        <p class="mt-4 text-3xl font-semibold text-ink-gray-9">
          {{ money(checkout.data.amount, checkout.data.currency) }}
        </p>
        <p class="mt-1 text-p-base text-ink-gray-6">{{ summary }}</p>
        <p class="mt-1 text-p-sm text-ink-gray-5">{{ checkout.data.venue_name }}</p>

        <template v-if="open && secondsLeft">
          <p class="mt-4 text-p-sm text-ink-gray-6">
            Pay within <span class="font-medium text-ink-gray-9">{{ label }}</span>
          </p>

          <div class="mt-6 flex flex-col gap-2">
            <Button
              variant="solid"
              :loading="settling === 'succeeded'"
              :disabled="!!settling"
              @click="decide('succeeded')"
            >
              Succeed
            </Button>
            <Button
              variant="outline"
              :loading="settling === 'failed'"
              :disabled="!!settling"
              @click="decide('failed')"
            >
              Fail
            </Button>
            <Button
              variant="ghost"
              :loading="settling === 'abandoned'"
              :disabled="!!settling"
              @click="decide('abandoned')"
            >
              Abandon
            </Button>
          </div>
          <ErrorMessage class="mt-2" :message="humanMessage(pay.error)" />
        </template>

        <p v-else-if="open" class="mt-4 text-p-base text-ink-gray-6">
          This hold has expired. Pick your slots again.
        </p>
        <p v-else class="mt-4 text-p-base text-ink-gray-6">
          This payment is already {{ checkout.data.status.toLowerCase() }}.
        </p>
      </template>
    </div>
  </div>
</template>
