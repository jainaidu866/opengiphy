<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { isAxiosError } from 'axios'

import { useAuth } from '@/stores/auth'

const { register } = useAuth()
const router = useRouter()

const email = ref('')
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    await register(email.value, username.value, password.value)
    router.push('/')
  } catch (err) {
    if (isAxiosError(err) && err.response?.data?.detail) {
      error.value = String(err.response.data.detail)
    } else {
      error.value = 'Registration failed. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="mx-auto mt-10 max-w-md">
    <div class="rounded-2xl border border-ink-700 bg-ink-800 p-8 shadow-2xl">
      <h1 class="text-2xl font-bold text-white">Create your account</h1>
      <p class="mt-1 text-sm text-gray-400">
        Join OpenGIPHY and start sharing GIFs.
      </p>

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
            for="username"
            class="mb-1 block text-sm font-medium text-gray-300"
          >
            Username
          </label>
          <input
            id="username"
            v-model="username"
            type="text"
            autocomplete="username"
            required
            minlength="3"
            placeholder="coolcat"
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
            autocomplete="new-password"
            required
            minlength="6"
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
          {{ loading ? 'Creating account…' : 'Sign up' }}
        </button>
      </form>

      <p class="mt-6 text-center text-sm text-gray-400">
        Already have an account?
        <RouterLink to="/login" class="font-semibold text-giphy-blue hover:underline">
          Log in
        </RouterLink>
      </p>
    </div>
  </div>
</template>
