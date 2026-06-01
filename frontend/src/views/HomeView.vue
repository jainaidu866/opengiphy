<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchGifs, toggleLike, type Gif, type SortMode } from '@/api/client'
import { useAuth } from '@/stores/auth'

const PAGE_SIZE = 20

const route = useRoute()
const router = useRouter()
const { isLoggedIn } = useAuth()

const initialSearch = (route.query.search as string) || ''

const page = ref(1)
const searchInput = ref(initialSearch)
const debouncedSearch = ref(initialSearch)
const sort = ref<SortMode>('new')

// Debounce: wait 300ms after typing stops before triggering a new query.
let debounceTimer: ReturnType<typeof setTimeout> | undefined
watch(searchInput, (value) => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    debouncedSearch.value = value
    page.value = 1 // reset to first page on a new search
  }, 300)
})

function setSort(mode: SortMode) {
  if (sort.value === mode) return
  sort.value = mode
  page.value = 1
}

const queryKey = computed(() => [
  'gifs',
  page.value,
  debouncedSearch.value,
  sort.value,
])

const { data, isLoading, isFetching, isError } = useQuery({
  queryKey,
  queryFn: () =>
    fetchGifs(page.value, PAGE_SIZE, debouncedSearch.value, sort.value),
  placeholderData: (prev) => prev,
})

const gifs = computed(() => data.value ?? [])
const hasNextPage = computed(() => gifs.value.length === PAGE_SIZE)

function nextPage() {
  if (hasNextPage.value) page.value += 1
}
function prevPage() {
  if (page.value > 1) page.value -= 1
}

// Per-card like overrides applied on top of the fetched like_count.
const likeState = reactive<Record<number, { liked: boolean; count: number }>>(
  {},
)

function likeCount(gif: Gif): number {
  return likeState[gif.id]?.count ?? gif.like_count
}
function isLiked(gif: Gif): boolean {
  return likeState[gif.id]?.liked ?? false
}

async function handleCardLike(gif: Gif) {
  if (!isLoggedIn.value) {
    router.push('/login')
    return
  }
  const prev = likeState[gif.id] ?? { liked: false, count: gif.like_count }
  const nextLiked = !prev.liked
  // Optimistic update.
  likeState[gif.id] = {
    liked: nextLiked,
    count: prev.count + (nextLiked ? 1 : -1),
  }
  try {
    const res = await toggleLike(gif.id)
    likeState[gif.id] = { liked: res.liked, count: res.like_count }
  } catch {
    likeState[gif.id] = prev // revert on failure
  }
}
</script>

<template>
  <section>
    <!-- Search bar -->
    <div class="mx-auto mb-6 max-w-2xl">
      <div class="relative">
        <span
          class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4 text-gray-500"
        >
          🔍
        </span>
        <input
          v-model="searchInput"
          type="search"
          placeholder="Search GIFs by title, description, or tag…"
          class="input-field !py-3 !pl-11 text-base"
        />
      </div>
    </div>

    <!-- New / Trending tabs -->
    <div class="mb-8 flex items-center justify-center gap-2">
      <button
        type="button"
        class="rounded-full px-5 py-2 text-sm font-semibold transition"
        :class="
          sort === 'new'
            ? 'bg-gradient-to-r from-giphy-purple to-giphy-pink text-white'
            : 'bg-ink-700 text-gray-300 hover:text-white'
        "
        @click="setSort('new')"
      >
        ✨ New
      </button>
      <button
        type="button"
        class="rounded-full px-5 py-2 text-sm font-semibold transition"
        :class="
          sort === 'trending'
            ? 'bg-gradient-to-r from-giphy-purple to-giphy-pink text-white'
            : 'bg-ink-700 text-gray-300 hover:text-white'
        "
        @click="setSort('trending')"
      >
        🔥 Trending
      </button>
    </div>

    <!-- Loading skeleton -->
    <div
      v-if="isLoading"
      class="columns-1 gap-4 sm:columns-2 lg:columns-3 xl:columns-4"
    >
      <div
        v-for="n in 8"
        :key="n"
        class="mb-4 break-inside-avoid animate-pulse rounded-xl bg-ink-700"
        :style="{ height: `${160 + ((n * 37) % 140)}px` }"
      />
    </div>

    <!-- Error state -->
    <div
      v-else-if="isError"
      class="rounded-xl border border-giphy-pink/40 bg-giphy-pink/10 p-8 text-center text-giphy-pink"
    >
      Something went wrong loading GIFs. Please try again.
    </div>

    <!-- Empty state -->
    <div
      v-else-if="gifs.length === 0"
      class="flex flex-col items-center justify-center rounded-2xl border border-dashed border-ink-600 bg-ink-800/50 py-24 text-center"
    >
      <p class="text-2xl font-bold text-white">
        {{ debouncedSearch ? 'No GIFs match your search' : 'No GIFs yet' }}
      </p>
      <p class="mt-2 text-gray-400">
        {{
          debouncedSearch
            ? 'Try a different keyword.'
            : 'Be the first to share one!'
        }}
      </p>
      <RouterLink to="/upload" class="btn-primary mt-6">Upload a GIF</RouterLink>
    </div>

    <!-- GIF masonry grid -->
    <div
      v-else
      class="columns-1 gap-4 sm:columns-2 lg:columns-3 xl:columns-4"
      :class="{ 'opacity-60': isFetching }"
    >
      <RouterLink
        v-for="gif in gifs"
        :key="gif.id"
        :to="`/gif/${gif.id}`"
        class="group mb-4 block animate-fade-in break-inside-avoid overflow-hidden rounded-xl border border-ink-700 bg-ink-800 transition hover:border-giphy-purple/60 hover:shadow-lg hover:shadow-giphy-purple/20"
      >
        <div class="relative overflow-hidden">
          <img
            :src="gif.url"
            :alt="gif.title"
            loading="lazy"
            class="w-full bg-ink-900 transition duration-300 group-hover:scale-[1.03]"
          />
          <!-- Title overlay on hover -->
          <div
            class="pointer-events-none absolute inset-x-0 bottom-0 translate-y-2 bg-gradient-to-t from-black/80 to-transparent p-3 opacity-0 transition duration-300 group-hover:translate-y-0 group-hover:opacity-100"
          >
            <p class="truncate font-semibold text-white">{{ gif.title }}</p>
          </div>
        </div>
        <div class="p-3">
          <h3 class="truncate font-semibold text-white">{{ gif.title }}</h3>
          <div
            class="mt-1 flex items-center justify-between text-sm text-gray-400"
          >
            <RouterLink
              :to="`/profile/${gif.uploader_username}`"
              class="text-giphy-green hover:underline"
              @click.stop
            >
              @{{ gif.uploader_username }}
            </RouterLink>
            <span class="flex items-center gap-3">
              <span title="Views">👁 {{ gif.view_count }}</span>
              <button
                type="button"
                class="flex items-center gap-1 transition hover:text-giphy-pink"
                :class="isLiked(gif) ? 'text-giphy-pink' : 'text-gray-400'"
                :title="isLoggedIn ? 'Like' : 'Log in to like'"
                @click.stop.prevent="handleCardLike(gif)"
              >
                {{ isLiked(gif) ? '♥' : '♡' }} {{ likeCount(gif) }}
              </button>
            </span>
          </div>
        </div>
      </RouterLink>
    </div>

    <!-- Pagination -->
    <div
      v-if="!isLoading && gifs.length > 0"
      class="mt-10 flex items-center justify-center gap-4"
    >
      <button
        type="button"
        class="rounded-lg border border-ink-600 px-4 py-2 text-sm font-medium text-gray-300 transition hover:border-giphy-purple hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
        :disabled="page === 1"
        @click="prevPage"
      >
        ← Prev
      </button>
      <span class="text-sm text-gray-400">Page {{ page }}</span>
      <button
        type="button"
        class="rounded-lg border border-ink-600 px-4 py-2 text-sm font-medium text-gray-300 transition hover:border-giphy-purple hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
        :disabled="!hasNextPage"
        @click="nextPage"
      >
        Next →
      </button>
    </div>
  </section>
</template>
