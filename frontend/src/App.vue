<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useAuth } from '@/stores/auth'

const { user, isLoggedIn, logout } = useAuth()
const router = useRouter()

function handleLogout() {
  logout()
  router.push('/')
}
</script>

<template>
  <div class="min-h-full">
    <nav
      class="sticky top-0 z-10 border-b border-ink-700 bg-ink-900/80 backdrop-blur"
    >
      <div
        class="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6"
      >
        <RouterLink
          to="/"
          class="bg-gradient-to-r from-giphy-purple via-giphy-pink to-giphy-blue bg-clip-text text-2xl font-extrabold tracking-tight text-transparent"
        >
          OpenGIPHY
        </RouterLink>

        <div class="flex items-center gap-2 sm:gap-3">
          <template v-if="isLoggedIn">
            <RouterLink
              to="/upload"
              class="nav-link hidden sm:inline-block"
              active-class="nav-link-active"
            >
              Upload
            </RouterLink>
            <RouterLink
              :to="`/profile/${user?.username ?? ''}`"
              class="text-sm font-semibold text-giphy-green hover:underline"
            >
              @{{ user?.username }}
            </RouterLink>
            <button
              type="button"
              class="rounded-md border border-ink-600 px-3 py-1.5 text-sm font-medium text-gray-300 transition hover:border-giphy-pink hover:text-white"
              @click="handleLogout"
            >
              Logout
            </button>
          </template>

          <template v-else>
            <RouterLink
              to="/login"
              class="nav-link"
              active-class="nav-link-active"
            >
              Login
            </RouterLink>
            <RouterLink to="/register" class="btn-primary !px-4 !py-1.5 text-sm">
              Register
            </RouterLink>
          </template>
        </div>
      </div>
    </nav>

    <main class="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <RouterView />
    </main>
  </div>
</template>
