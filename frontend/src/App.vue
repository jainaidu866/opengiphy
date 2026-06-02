<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuth } from '@/stores/auth'

const { user, isLoggedIn, logout } = useAuth()
const router = useRouter()

function handleLogout() {
  logout()
  router.push('/')
}

// Giphy-style "Create" dropdown (Create / Upload).
const showCreateMenu = ref(false)
function toggleCreateMenu() {
  showCreateMenu.value = !showCreateMenu.value
}
function closeCreateMenu() {
  showCreateMenu.value = false
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
          class="text-gradient-animated text-2xl font-extrabold tracking-tight"
        >
          OpenGIPHY
        </RouterLink>

        <div class="flex items-center gap-2 sm:gap-3">
          <RouterLink
            to="/categories"
            class="nav-link hidden sm:inline-block"
            active-class="nav-link-active"
          >
            Categories
          </RouterLink>

          <template v-if="isLoggedIn">
            <RouterLink
              to="/collections"
              class="nav-link hidden sm:inline-block"
              active-class="nav-link-active"
            >
              Collections
            </RouterLink>
            <!-- Create dropdown (Giphy-style: Create / Upload) -->
            <div class="relative">
              <button
                type="button"
                class="flex items-center gap-1 rounded-full bg-gradient-to-r from-giphy-green to-giphy-blue px-4 py-1.5 text-sm font-bold text-white shadow transition hover:opacity-90"
                @click="toggleCreateMenu"
              >
                <span class="text-base leading-none">+</span> Create
                <span class="text-[10px] leading-none">▾</span>
              </button>

              <!-- Click-away backdrop -->
              <div
                v-if="showCreateMenu"
                class="fixed inset-0 z-20"
                @click="closeCreateMenu"
              />

              <!-- Menu -->
              <div
                v-if="showCreateMenu"
                class="absolute right-0 z-30 mt-2 w-48 overflow-hidden rounded-xl border border-ink-700 bg-ink-800 shadow-xl"
              >
                <RouterLink
                  to="/create"
                  class="flex flex-col gap-0.5 px-4 py-3 transition hover:bg-ink-700"
                  @click="closeCreateMenu"
                >
                  <span class="text-sm font-semibold text-white">
                    🎨 Create
                  </span>
                  <span class="text-xs text-gray-400">
                    Caption &amp; animate a GIF
                  </span>
                </RouterLink>
                <div class="h-px bg-ink-700" />
                <RouterLink
                  to="/upload"
                  class="flex flex-col gap-0.5 px-4 py-3 transition hover:bg-ink-700"
                  @click="closeCreateMenu"
                >
                  <span class="text-sm font-semibold text-white">
                    ⬆️ Upload
                  </span>
                  <span class="text-xs text-gray-400">Upload your own GIF</span>
                </RouterLink>
              </div>
            </div>
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
