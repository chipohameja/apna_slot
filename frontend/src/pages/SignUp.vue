<script setup>
import { Button, ErrorMessage, FormControl, useCall } from 'frappe-ui'
import { reactive } from 'vue'
import { useRoute } from 'vue-router'

import PublicLayout from '../layouts/PublicLayout.vue'
import { landOn } from '../session'

const route = useRoute()
const form = reactive({ full_name: '', email: '', phone: '', password: '' })

const signUp = useCall({
  url: '/api/v2/method/apna_slot.api.auth.sign_up',
  method: 'POST',
  immediate: false,
  onSuccess: () => landOn(route.query.redirect || '/'),
})
</script>

<template>
  <PublicLayout>
    <form
      class="mx-auto flex w-full max-w-sm flex-col gap-4 px-6 py-16"
      @submit.prevent="signUp.submit({ ...form })"
    >
      <h1 class="text-2xl font-semibold text-ink-gray-9">Create your account</h1>
      <FormControl v-model="form.full_name" label="Full name" required />
      <FormControl
        v-model="form.email"
        type="email"
        label="Email"
        autocomplete="username"
        required
      />
      <FormControl
        v-model="form.phone"
        type="tel"
        label="Phone"
        description="Optional"
      />
      <FormControl
        v-model="form.password"
        type="password"
        label="Password"
        autocomplete="new-password"
        required
      />
      <ErrorMessage :message="signUp.error?.message" />
      <Button
        variant="solid"
        theme="gray"
        :loading="signUp.loading"
        type="submit"
      >
        Sign up
      </Button>
      <p class="text-p-sm text-ink-gray-6">
        Already have an account?
        <router-link
          :to="{ path: '/login', query: route.query }"
          class="text-ink-gray-9 underline"
        >
          Log in
        </router-link>
      </p>
    </form>
  </PublicLayout>
</template>
