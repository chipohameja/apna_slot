<script setup>
import {
  Button,
  Combobox,
  ErrorMessage,
  FormControl,
  FormLabel,
  Select,
  useCall,
} from 'frappe-ui'
import { reactive } from 'vue'

import PublicLayout from '../../layouts/PublicLayout.vue'
import { humanMessage } from '../../lib/errors'
import { landOn, session } from '../../session'

const CURRENCIES = ['AED', 'INR', 'USD', 'EUR', 'GBP']
const timezones = Intl.supportedValuesOf('timeZone')

const form = reactive({
  publisher_name: '',
  contact_email: session.user,
  currency: CURRENCIES[0],
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
})

const createPublisher = useCall({
  url: '/api/v2/method/apna_slot.api.publisher.create_publisher',
  method: 'POST',
  immediate: false,
  onSuccess: () => landOn('/'),
})
</script>

<template>
  <PublicLayout>
    <form
      class="mx-auto flex w-full max-w-md flex-col gap-4 px-6 py-16"
      @submit.prevent="createPublisher.submit({ ...form })"
    >
      <div>
        <h1 class="text-2xl font-semibold text-ink-gray-9">List your venue</h1>
        <p class="mt-1 text-p-base text-ink-gray-6">
          Create the business that your venues will belong to.
        </p>
      </div>
      <FormControl v-model="form.publisher_name" label="Business name" required />
      <FormControl
        v-model="form.contact_email"
        type="email"
        label="Contact email"
        required
      />
      <div class="space-y-1.5">
        <FormLabel label="Currency" required />
        <Select v-model="form.currency" :options="CURRENCIES" class="w-full" />
        <p class="text-p-xs text-ink-gray-5">
          Your venues are priced and paid in this currency
        </p>
      </div>
      <div class="space-y-1.5">
        <FormLabel label="Timezone" required />
        <Combobox v-model="form.timezone" :options="timezones" class="w-full" />
      </div>
      <ErrorMessage :message="humanMessage(createPublisher.error)" />
      <Button
        variant="solid"
        theme="gray"
        :loading="createPublisher.loading"
        type="submit"
      >
        Create business
      </Button>
    </form>
  </PublicLayout>
</template>
