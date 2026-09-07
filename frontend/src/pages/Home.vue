<script setup>
import { Button, LoadingText, useCall } from 'frappe-ui'
import { useRouter } from 'vue-router'

import PublicLayout from '../layouts/PublicLayout.vue'
import { money } from '../lib/format'
import { session } from '../session'

const router = useRouter()
const venues = useCall({
  url: '/api/v2/method/apna_slot.api.discovery.search_venues',
})
</script>

<template>
  <PublicLayout>
    <div class="mx-auto flex max-w-3xl flex-col gap-8 px-6 py-12">
      <div class="flex flex-col gap-4">
        <h1 class="text-3xl font-semibold text-ink-gray-9">Apna Slot</h1>
        <p class="text-base text-ink-gray-6">
          Book turf, courts and halls by the hour.
        </p>
        <div v-if="session.is_guest">
          <Button variant="subtle" @click="router.push('/signup')">Get started</Button>
        </div>
      </div>

      <LoadingText v-if="venues.loading && !venues.data" text="Loading venues" />

      <p v-else-if="!venues.data?.length" class="text-p-base text-ink-gray-6">
        No venues are listed yet.
      </p>

      <div v-else class="grid gap-3 sm:grid-cols-2">
        <router-link
          v-for="venue in venues.data"
          :key="venue.slug"
          :to="`/venues/${venue.slug}`"
          class="flex flex-col gap-1 rounded border border-outline-gray-1 bg-surface-white p-4 hover:border-outline-gray-3"
        >
          <h2 class="text-p-base font-medium text-ink-gray-8">{{ venue.venue_name }}</h2>
          <p class="text-p-sm text-ink-gray-5">{{ venue.city }}, {{ venue.country }}</p>
          <p class="mt-1 text-p-sm text-ink-gray-7">
            from {{ money(venue.from_price, venue.currency) }} per slot ·
            {{ venue.resource_count }}
            {{ venue.resource_count === 1 ? 'resource' : 'resources' }}
          </p>
        </router-link>
      </div>
    </div>
  </PublicLayout>
</template>
