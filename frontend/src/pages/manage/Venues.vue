<script setup>
import { Badge, Button, ErrorMessage, LoadingText, useList } from 'frappe-ui'
import { useRouter } from 'vue-router'

import PublicLayout from '../../layouts/PublicLayout.vue'
import { humanMessage } from '../../lib/errors'

const STATUS_THEMES = {
  Published: 'green',
  Draft: 'gray',
  Unlisted: 'orange',
  Suspended: 'red',
  'Under Review': 'blue',
}

const router = useRouter()
const venues = useList({
  doctype: 'Venue',
  fields: ['name', 'venue_name', 'city', 'status'],
  orderBy: 'creation desc',
  limit: 50,
})

function setStatus(venue, status) {
  venues.setValue.submit({ name: venue.name, status })
}
</script>

<template>
  <PublicLayout>
    <div class="mx-auto flex w-full max-w-3xl flex-col gap-4 px-6 py-12">
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-semibold text-ink-gray-9">Venues</h1>
        <Button
          variant="solid"
          theme="gray"
          icon-left="lucide-plus"
          @click="router.push('/manage/venues/new')"
        >
          New venue
        </Button>
      </div>

      <ErrorMessage :message="humanMessage(venues.setValue.error)" />

      <LoadingText v-if="venues.loading && !venues.data" text="Loading venues" />

      <p v-else-if="!venues.data?.length" class="text-p-base text-ink-gray-6">
        No venues yet. Create one, then publish it to make it bookable.
      </p>

      <div v-else class="divide-y divide-outline-gray-1 rounded border border-outline-gray-1">
        <div
          v-for="venue in venues.data"
          :key="venue.name"
          data-testid="venue-row"
          class="flex items-center justify-between gap-4 px-4 py-3"
        >
          <div class="min-w-0">
            <p class="truncate text-p-base font-medium text-ink-gray-8">
              {{ venue.venue_name }}
            </p>
            <p class="text-p-sm text-ink-gray-5">{{ venue.city }}</p>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <Badge :theme="STATUS_THEMES[venue.status]" :label="venue.status" />
            <Button
              v-if="venue.status !== 'Published'"
              :loading="venues.setValue.loading"
              @click="setStatus(venue, 'Published')"
            >
              Publish
            </Button>
            <Button
              v-else
              :loading="venues.setValue.loading"
              @click="setStatus(venue, 'Unlisted')"
            >
              Unlist
            </Button>
          </div>
        </div>
      </div>
    </div>
  </PublicLayout>
</template>
