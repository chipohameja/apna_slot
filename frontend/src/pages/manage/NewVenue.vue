<script setup>
import {
  Button,
  Combobox,
  ErrorMessage,
  FormControl,
  FormLabel,
  Select,
  useCall,
  useList,
} from 'frappe-ui'
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import PublicLayout from '../../layouts/PublicLayout.vue'
import { humanMessage } from '../../lib/errors'
import { session } from '../../session'

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const SLOT_DURATIONS = ['30', '45', '60', '90', '120']

const router = useRouter()
const publisher = session.publishers[0]
const timezones = Intl.supportedValuesOf('timeZone')
const countries = useList({
  doctype: 'Country',
  fields: ['name'],
  orderBy: 'name asc',
  limit: 300,
})
const countryOptions = computed(() => (countries.data ?? []).map((row) => row.name))

const form = reactive({
  venue_name: '',
  address_line_1: '',
  city: '',
  country: '',
  timezone: publisher.timezone,
  resource_name: '',
  slot_duration_minutes: '60',
  base_price: null,
  opens_at: '18:00',
  closes_at: '22:00',
})

// kept across a retry so a resource that fails validation does not leave a second venue behind
const venueName = ref(null)
const createVenue = useCall({ url: '/api/v2/document/Venue', method: 'POST', immediate: false })
const createResource = useCall({
  url: '/api/v2/document/Bookable%20Resource',
  method: 'POST',
  immediate: false,
})

async function submit() {
  venueName.value = venueName.value ?? (await createVenue.submit(venuePayload()))?.name
  if (!venueName.value) return
  if (await createResource.submit(resourcePayload(venueName.value))) {
    router.push('/manage/venues')
  }
}

function venuePayload() {
  const { venue_name, address_line_1, city, country, timezone } = form
  return { publisher: publisher.name, venue_name, address_line_1, city, country, timezone }
}

function resourcePayload(venue) {
  return {
    venue,
    resource_name: form.resource_name,
    slot_duration_minutes: form.slot_duration_minutes,
    base_price: form.base_price,
    weekly_schedule: DAYS.map((day) => ({
      day_of_week: day,
      opens_at: form.opens_at,
      closes_at: form.closes_at,
    })),
  }
}
</script>

<template>
  <PublicLayout>
    <form
      class="mx-auto flex w-full max-w-md flex-col gap-4 px-6 py-12"
      @submit.prevent="submit"
    >
      <div>
        <h1 class="text-2xl font-semibold text-ink-gray-9">New venue</h1>
        <p class="mt-1 text-p-base text-ink-gray-6">
          A venue needs one bookable resource before it can be published.
        </p>
      </div>

      <FormControl v-model="form.venue_name" label="Venue name" required />
      <FormControl v-model="form.address_line_1" label="Address" required />
      <FormControl v-model="form.city" label="City" required />
      <div class="space-y-1.5">
        <FormLabel label="Country" required />
        <Combobox v-model="form.country" :options="countryOptions" class="w-full" />
      </div>
      <div class="space-y-1.5">
        <FormLabel label="Timezone" required />
        <Combobox v-model="form.timezone" :options="timezones" class="w-full" />
        <p class="text-p-xs text-ink-gray-5">
          Opening hours and every slot are read in this timezone
        </p>
      </div>

      <h2 class="mt-2 text-lg font-semibold text-ink-gray-9">First resource</h2>

      <FormControl
        v-model="form.resource_name"
        label="Resource name"
        placeholder="Turf A"
        required
      />
      <div class="space-y-1.5">
        <FormLabel label="Slot duration (minutes)" required />
        <Select v-model="form.slot_duration_minutes" :options="SLOT_DURATIONS" class="w-full" />
      </div>
      <FormControl
        v-model.number="form.base_price"
        type="number"
        :label="`Price per slot (${publisher.currency})`"
        required
      />
      <div class="grid grid-cols-2 gap-3">
        <FormControl v-model="form.opens_at" type="time" label="Opens at" required />
        <FormControl v-model="form.closes_at" type="time" label="Closes at" required />
      </div>
      <p class="text-p-xs text-ink-gray-5">
        These hours apply to every day of the week, and must divide into whole slots.
      </p>

      <ErrorMessage
        :message="humanMessage(createVenue.error) || humanMessage(createResource.error)"
      />
      <Button
        variant="solid"
        theme="gray"
        type="submit"
        :loading="createVenue.loading || createResource.loading"
      >
        Create venue
      </Button>
    </form>
  </PublicLayout>
</template>
