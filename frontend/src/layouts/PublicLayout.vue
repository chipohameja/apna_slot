<script setup>
import { Button, Dropdown } from 'frappe-ui'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { logOut, session } from '../session'

const router = useRouter()
const publisher = computed(() => session.publishers[0])
const accountOptions = [{ label: 'Log out', icon: 'lucide-log-out', onClick: logOut }]
</script>

<template>
  <div class="flex min-h-screen flex-col bg-surface-white">
    <header
      class="flex items-center justify-between gap-2 border-b border-outline-gray-1 px-4 py-3 sm:px-6"
    >
      <router-link
        to="/"
        class="whitespace-nowrap text-lg font-semibold text-ink-gray-9"
      >
        Apna Slot
      </router-link>

      <div v-if="session.is_guest" class="flex items-center gap-2">
        <Button variant="ghost" @click="router.push('/login')">Log in</Button>
        <Button variant="solid" theme="gray" @click="router.push('/signup')">
          Sign up
        </Button>
      </div>

      <div v-else class="flex items-center gap-2">
        <Button
          v-if="publisher"
          variant="ghost"
          @click="router.push('/manage/venues')"
        >
          {{ publisher.publisher_name }}
        </Button>
        <Button v-else variant="subtle" @click="router.push('/manage/onboarding')">
          List your venue
        </Button>
        <Dropdown :options="accountOptions">
          <Button variant="ghost" icon-right="lucide-chevron-down">
            {{ session.full_name }}
          </Button>
        </Dropdown>
      </div>
    </header>

    <main class="flex-1">
      <slot />
    </main>
  </div>
</template>
