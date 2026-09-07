<script setup>
import { Button, ErrorMessage, FormControl } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import PublicLayout from '../layouts/PublicLayout.vue'
import { landOn, logIn } from '../session'

const route = useRoute()
const form = reactive({ email: '', password: '' })
const error = ref(null)
const loading = ref(false)

async function submit() {
  loading.value = true
  error.value = null
  try {
    await logIn(form.email, form.password)
    landOn(route.query.redirect || '/')
  } catch (exception) {
    error.value = 'Those credentials did not match an account.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <PublicLayout>
    <form
      class="mx-auto flex w-full max-w-sm flex-col gap-4 px-6 py-16"
      @submit.prevent="submit"
    >
      <h1 class="text-2xl font-semibold text-ink-gray-9">Log in</h1>
      <FormControl
        v-model="form.email"
        type="email"
        label="Email"
        autocomplete="username"
        required
      />
      <FormControl
        v-model="form.password"
        type="password"
        label="Password"
        autocomplete="current-password"
        required
      />
      <ErrorMessage :message="error" />
      <Button variant="solid" theme="gray" :loading="loading" type="submit">
        Log in
      </Button>
      <p class="text-p-sm text-ink-gray-6">
        New here?
        <router-link to="/signup" class="text-ink-gray-9 underline">
          Create an account
        </router-link>
      </p>
    </form>
  </PublicLayout>
</template>
