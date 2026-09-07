<script setup>
import { Button, ErrorMessage, FormControl, LoadingText, TabButtons, useCall } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import PublicLayout from '../layouts/PublicLayout.vue'
import { clockTime, isoDate, money } from '../lib/format'
import { humanMessage } from '../lib/errors'
import { session } from '../session'

const BOOKABLE = ['available', 'booked']

const route = useRoute()
const router = useRouter()
const resource = ref(null)
const day = ref(isoDate(new Date(Date.now() + 86400000)))

const venue = useCall({
  url: '/api/v2/method/apna_slot.api.discovery.get_venue',
  params: { slug: route.params.slug },
  onSuccess: (data) => (resource.value = data.resources[0]?.name),
})

// driven by the watch below, never by `refetch`: the resource is unknown until the venue
// loads, and an auto-refetch fires one doomed request with a null resource on every visit
const grid = useCall({
  url: '/api/v2/method/apna_slot.api.availability.get_day',
  params: () => ({ resource: resource.value, date: day.value }),
  immediate: false,
})

const book = useCall({
  url: '/api/v2/method/apna_slot.api.booking.create',
  method: 'POST',
  immediate: false,
})

const slots = computed(() => (grid.data ?? []).filter((slot) => BOOKABLE.includes(slot.status)))
const resourceTabs = computed(() =>
  (venue.data?.resources ?? []).map((row) => ({ label: row.resource_name, value: row.name })),
)

watch([resource, day], ([selected]) => selected && grid.reload(), { immediate: true })

async function hold(slot) {
  if (session.is_guest) return router.push({ name: 'Login', query: { redirect: route.fullPath } })
  const receipt = await book.submit({
    resource: resource.value,
    slot_date: day.value,
    start_time: slot.start_time,
  })
  if (receipt) return router.push(`/checkout/${receipt.booking}`)
  grid.reload() // someone else took it; the refreshed grid says so
}
</script>

<template>
  <PublicLayout>
    <div class="mx-auto flex w-full max-w-3xl flex-col gap-6 px-6 py-10">
      <LoadingText v-if="venue.loading && !venue.data" text="Loading venue" />
      <ErrorMessage v-else-if="venue.error" message="This venue is not available." />

      <template v-else-if="venue.data">
        <div>
          <h1 class="text-2xl font-semibold text-ink-gray-9">{{ venue.data.venue_name }}</h1>
          <p class="mt-1 text-p-base text-ink-gray-6">
            {{ venue.data.city }}, {{ venue.data.country }} · {{ venue.data.timezone }}
          </p>
        </div>

        <TabButtons
          v-if="resourceTabs.length > 1"
          v-model="resource"
          :buttons="resourceTabs"
        />

        <FormControl v-model="day" type="date" label="Date" :min="isoDate(new Date())" />

        <div class="flex flex-col gap-3">
          <LoadingText v-if="grid.loading && !grid.data" text="Loading slots" />
          <p v-else-if="!slots.length" class="text-p-base text-ink-gray-6">
            Nothing open on this date.
          </p>
          <div v-else class="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <Button
              v-for="slot in slots"
              :key="slot.start_time"
              :variant="slot.status === 'available' ? 'subtle' : 'ghost'"
              :disabled="slot.status !== 'available' || book.loading"
              class="h-auto py-2"
              @click="hold(slot)"
            >
              <span class="flex flex-col items-start gap-0.5">
                <span class="text-p-base text-ink-gray-8">
                  {{ clockTime(slot.start_time) }}–{{ clockTime(slot.end_time) }}
                </span>
                <span class="text-p-xs text-ink-gray-5">
                  {{ slot.status === 'available' ? money(slot.price, venue.data.currency) : 'Booked' }}
                </span>
              </span>
            </Button>
          </div>
          <ErrorMessage :message="humanMessage(book.error)" />
        </div>
      </template>
    </div>
  </PublicLayout>
</template>
