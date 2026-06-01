<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { fetchProfile } from '@/api/client'

const PAGE_SIZE = 20

const route = useRoute()
const username = computed(() => route.params.username as string)
const page = ref(1)

// Reset to page 1 when navigating between profiles.
watch(username, () => {
  page.value = 1
})

const { data, isLoading, isError } = useQuery({
  queryKey: computed(() => ['profile', username.value, page.value]),
  queryFn: () => fetchProfile(username.value, page.value, PAGE_SIZE),
  placeholderData: (prev) => prev,
})

const gifs = computed(() => data.value?.gifs ?? [])
const hasNextPage = computed(() => gifs.value.length === PAGE_SIZE)

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
  })
}
</script>

<template>
  <section>
    <div v-if="isLoading" class="py-24 text-center text-gray-400">Loading…</div>

    <div
      v-else-if="isError || !data"
      class="flex flex-col items-center justify-center py-24 text-center"
    >
      <p class="text-2xl font-bold text-white">User not found</p>
      <p class="mt-2 text-gray-400">
        There's no one here by the name @{{ username }}.
      </p>
      <RouterLink to="/" class="btn-primary mt-6">Back home</RouterLink>
    </div>

    <template v-else>
      <!-- Profile header -->
      <header class="mb-10 flex items-center gap-4">
        <div
          class="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-giphy-purple to-giphy-pink text-2xl font-bold text-white"
        >
          {{ data.username.charAt(0).toUpperCase() }}
        </div>
        <div>
          <h1 class="text-3xl font-bold text-white">@{{ data.username }}</h1>
          <p class="text-sm text-gray-400">
            Joined {{ formatDate(data.created_at) }}
          </p>
        </div>
      </header>

      <!-- Empty state -->
      <div
        v-if="gifs.length === 0"
        class="flex flex-col items-center justify-center rounded-2xl border border-dashed border-ink-600 bg-ink-800/50 py-24 text-center"
      >
        <p class="text-xl font-bold text-white">No GIFs uploaded yet</p>
        <p class="mt-2 text-gray-400">This user hasn't shared anything.</p>
      </div>

      <!-- GIF grid -->
      <div
        v-else
        class="columns-1 gap-4 sm:columns-2 lg:columns-3 xl:columns-4"
      >
        <RouterLink
          v-for="gif in gifs"
          :key="gif.id"
          :to="`/gif/${gif.id}`"
          class="group mb-4 block break-inside-avoid overflow-hidden rounded-xl border border-ink-700 bg-ink-800 transition hover:border-giphy-purple/60 hover:shadow-lg hover:shadow-giphy-purple/20"
        >
          <img
            :src="gif.url"
            :alt="gif.title"
            loading="lazy"
            class="w-full bg-ink-900 transition duration-300 group-hover:scale-[1.02]"
          />
          <div class="p-3">
            <h3 class="truncate font-semibold text-white">{{ gif.title }}</h3>
            <div class="mt-1 flex items-center gap-3 text-sm text-gray-400">
              <span title="Views">👁 {{ gif.view_count }}</span>
              <span title="Likes" class="text-giphy-pink">
                ♥ {{ gif.like_count }}
              </span>
            </div>
          </div>
        </RouterLink>
      </div>

      <!-- Pagination -->
      <div
        v-if="gifs.length > 0"
        class="mt-10 flex items-center justify-center gap-4"
      >
        <button
          type="button"
          class="rounded-lg border border-ink-600 px-4 py-2 text-sm font-medium text-gray-300 transition hover:border-giphy-purple hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="page === 1"
          @click="page -= 1"
        >
          ← Prev
        </button>
        <span class="text-sm text-gray-400">Page {{ page }}</span>
        <button
          type="button"
          class="rounded-lg border border-ink-600 px-4 py-2 text-sm font-medium text-gray-300 transition hover:border-giphy-purple hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="!hasNextPage"
          @click="page += 1"
        >
          Next →
        </button>
      </div>
    </template>
  </section>
</template>
