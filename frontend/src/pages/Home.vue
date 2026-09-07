<script setup>
import { Button } from 'frappe-ui'
</script>

<template>
  <main class="min-h-screen bg-surface-white">
    <div class="mx-auto flex max-w-2xl flex-col gap-4 px-6 py-24">
      <h1 class="text-3xl font-semibold text-ink-gray-9">Apna Slot</h1>
      <p class="text-base text-ink-gray-6">
        Book turf, courts and halls by the hour.
      </p>
      <div>
        <Button variant="solid" theme="gray" icon-left="lucide-search">
          Find a venue
        </Button>
      </div>
    </div>
  </main>
</template>
