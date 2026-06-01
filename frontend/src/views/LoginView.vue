<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from '@/stores/auth'

const { login } = useAuth()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    await login(email.value, password.value)
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch {
    error.value = 'Invalid email or password'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="mx-auto mt-10 max-w-md">
    <div class="rounded-2xl border border-ink-700 bg-ink-800 p-8 shadow-2xl">
      <h1 class="text-2xl font-bold text-white">Welcome back</h1>
      <p class="mt-1 text-sm text-gray-400">Log in to your OpenGIPHY account.</p>

      <form class="mt-6 space-y-4" @submit.prevent="onSubmit">
        <div>
          <label for="email" class="mb-1 block text-sm font-medium text-gray-300">
            Email
          </label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            required
            placeholder="you@example.com"
            class="input-field"
          />
        </div>

        <div>
          <label
            for="password"
            class="mb-1 block text-sm font-medium text-gray-300"
          >
            Password
          </label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
            placeholder="••••••••"
            class="input-field"
          />
        </div>

        <p
          v-if="error"
          class="rounded-lg border border-giphy-pink/40 bg-giphy-pink/10 px-3 py-2 text-sm text-giphy-pink"
        >
          {{ error }}
        </p>

        <button type="submit" class="btn-primary w-full" :disabled="loading">
          {{ loading ? 'Logging in…' : 'Log in' }}
        </button>
      </form>

      <p class="mt-6 text-center text-sm text-gray-400">
        No account?
        <RouterLink to="/register" class="font-semibold text-giphy-blue hover:underline">
          Create one
        </RouterLink>
      </p>
    </div>
  </div>
</template>
