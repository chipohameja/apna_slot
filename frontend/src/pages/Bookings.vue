<script setup>
import { Badge, Button, LoadingText, useCall } from 'frappe-ui'
import { useRouter } from 'vue-router'

import PublicLayout from '../layouts/PublicLayout.vue'
import { STATUS_THEMES } from '../lib/bookingStatus'
import { clockTime, money } from '../lib/format'

const router = useRouter()
const bookings = useCall({
  url: '/api/v2/method/apna_slot.api.booking.list_mine',
})
</script>

<template>
  <PublicLayout>
    <div class="mx-auto flex w-full max-w-3xl flex-col gap-4 px-6 py-12">
      <h1 class="text-2xl font-semibold text-ink-gray-9">My bookings</h1>

      <LoadingText v-if="bookings.loading && !bookings.data" text="Loading bookings" />

      <div v-else-if="!bookings.data?.length" class="flex flex-col items-start gap-3">
        <p class="text-p-base text-ink-gray-6">You have no bookings yet.</p>
        <Button variant="subtle" @click="router.push('/')">Find a venue</Button>
      </div>

      <div v-else class="divide-y divide-outline-gray-1 rounded border border-outline-gray-1">
        <router-link
          v-for="booking in bookings.data"
          :key="booking.name"
          :to="`/checkout/${booking.name}`"
          class="flex items-center justify-between gap-4 px-4 py-3 hover:bg-surface-gray-1"
        >
          <div class="min-w-0">
            <p class="truncate text-p-base font-medium text-ink-gray-8">
              {{ booking.venue_name }} · {{ booking.resource_name }}
            </p>
            <p class="text-p-sm text-ink-gray-5">
              {{ booking.line_date }} · {{ clockTime(booking.start_time) }}–{{
                clockTime(booking.end_time)
              }}
            </p>
          </div>
          <div class="flex shrink-0 items-center gap-3">
            <span class="hidden text-p-base text-ink-gray-8 sm:inline">
              {{ money(booking.total_amount, booking.currency) }}
            </span>
            <Badge :theme="STATUS_THEMES[booking.status] ?? 'gray'" :label="booking.status" />
          </div>
        </router-link>
      </div>
    </div>
  </PublicLayout>
</template>
