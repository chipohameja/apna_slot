<script setup>
import { Button } from 'frappe-ui'
import { useRouter } from 'vue-router'

import PublicLayout from '../layouts/PublicLayout.vue'
import { session } from '../session'

const router = useRouter()
</script>

<template>
  <PublicLayout>
    <div class="mx-auto flex max-w-2xl flex-col gap-4 px-6 py-24">
      <h1 class="text-3xl font-semibold text-ink-gray-9">Apna Slot</h1>
      <p class="text-base text-ink-gray-6">
        Book turf, courts and halls by the hour.
      </p>
      <div class="flex gap-2">
        <Button variant="solid" theme="gray" icon-left="lucide-search" disabled>
          Find a venue
        </Button>
        <Button
          v-if="session.is_guest"
          variant="subtle"
          @click="router.push('/signup')"
        >
          Get started
        </Button>
      </div>
    </div>
  </PublicLayout>
</template>
