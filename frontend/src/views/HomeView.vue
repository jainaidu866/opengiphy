<script setup lang="ts">
import { useInfiniteQuery } from '@tanstack/vue-query'
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  fetchGifs,
  toggleLike,
  toggleSave,
  type Gif,
  type SortMode,
} from '@/api/client'
import { useClipboard } from '@/composables/useClipboard'
import { useAuth } from '@/stores/auth'

const PAGE_SIZE = 20

const route = useRoute()
const router = useRouter()
const { isLoggedIn } = useAuth()

// Dismissible "Start Creating" banner (logged-in only). Persisted in localStorage.
const BANNER_KEY = 'hideBanner'
const bannerDismissed = ref(localStorage.getItem(BANNER_KEY) === 'true')
const showBanner = computed(() => isLoggedIn.value && !bannerDismissed.value)
function dismissBanner() {
  bannerDismissed.value = true
  localStorage.setItem(BANNER_KEY, 'true')
}

const initialSearch = (route.query.search as string) || ''

const searchInput = ref(initialSearch)
const debouncedSearch = ref(initialSearch)
const sort = ref<SortMode>('new')

// Debounce: wait 300ms after typing stops before triggering a new query.
let debounceTimer: ReturnType<typeof setTimeout> | undefined
watch(searchInput, (value) => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    debouncedSearch.value = value
  }, 300)
})

function setSort(mode: SortMode) {
  if (sort.value === mode) return
  sort.value = mode
}

// Changing search/sort builds a new query key, which resets the infinite
// query back to page 1 automatically.
const queryKey = computed(() => ['gifs', debouncedSearch.value, sort.value])

const {
  data,
  isLoading,
  isFetching,
  isFetchingNextPage,
  isError,
  hasNextPage,
  fetchNextPage,
} = useInfiniteQuery({
  queryKey,
  queryFn: ({ pageParam }) =>
    fetchGifs(pageParam, PAGE_SIZE, debouncedSearch.value, sort.value),
  initialPageParam: 1,
  getNextPageParam: (lastPage, allPages) =>
    lastPage.length === PAGE_SIZE ? allPages.length + 1 : undefined,
})

// Flatten the paged results into a single list for the grid.
const gifs = computed(() => (data.value?.pages ?? []).flat())

// IntersectionObserver sentinel: load the next page when it scrolls into view.
const sentinel = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | undefined

watch(sentinel, (el) => {
  observer?.disconnect()
  if (!el) return
  observer = new IntersectionObserver((entries) => {
    if (
      entries[0]?.isIntersecting &&
      hasNextPage.value &&
      !isFetchingNextPage.value
    ) {
      fetchNextPage()
    }
  })
  observer.observe(el)
})

onBeforeUnmount(() => observer?.disconnect())

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

// Share: copy a card's GIF page URL; track which card last copied.
const { copy } = useClipboard()
const sharedId = ref<number | null>(null)
let shareTimer: ReturnType<typeof setTimeout> | undefined

async function handleShare(gif: Gif) {
  const ok = await copy(`${window.location.origin}/gif/${gif.id}`)
  if (ok) {
    sharedId.value = gif.id
    clearTimeout(shareTimer)
    shareTimer = setTimeout(() => (sharedId.value = null), 2000)
  }
}

// Per-card save (bookmark) state, toggled optimistically.
const savedState = reactive<Record<number, boolean>>({})
function isSaved(gif: Gif): boolean {
  return savedState[gif.id] ?? false
}
async function handleCardSave(gif: Gif) {
  if (!isLoggedIn.value) {
    router.push('/login')
    return
  }
  const prev = savedState[gif.id] ?? false
  savedState[gif.id] = !prev // optimistic
  try {
    const res = await toggleSave(gif.id)
    savedState[gif.id] = res.saved
  } catch {
    savedState[gif.id] = prev // revert on failure
  }
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

    <!-- Start Creating CTA banner (logged-in, dismissible) -->
    <div
      v-if="showBanner"
      class="relative mb-8 flex flex-col items-center justify-between gap-4 overflow-hidden rounded-2xl bg-gradient-to-r from-giphy-purple via-giphy-pink to-giphy-blue p-6 sm:flex-row"
    >
      <div>
        <p class="text-xl font-bold text-white">
          🎬 Share your GIFs with the world
        </p>
        <p class="mt-1 text-sm text-white/80">
          Upload your favorite animated moments in seconds.
        </p>
      </div>
      <RouterLink
        to="/upload"
        class="shrink-0 rounded-full bg-white px-6 py-2 font-bold text-ink-900 shadow transition hover:bg-white/90"
      >
        Create
      </RouterLink>
      <button
        type="button"
        class="absolute right-2 top-2 text-white/70 transition hover:text-white"
        title="Dismiss"
        @click="dismissBanner"
      >
        ✕
      </button>
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
      :class="{ 'opacity-60': isFetching && !isFetchingNextPage }"
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
          <!-- Share + Save buttons (top-right on hover) -->
          <div
            class="absolute right-2 top-2 flex gap-1 opacity-0 transition group-hover:opacity-100"
          >
            <button
              type="button"
              class="rounded-full bg-black/60 px-2 py-1 text-xs font-medium text-white backdrop-blur transition hover:bg-black/80"
              :title="isSaved(gif) ? 'Saved' : 'Save to collection'"
              @click.stop.prevent="handleCardSave(gif)"
            >
              {{ isSaved(gif) ? '🔖' : '🏷️' }}
            </button>
            <button
              type="button"
              class="rounded-full bg-black/60 px-2 py-1 text-xs font-medium text-white backdrop-blur transition hover:bg-black/80"
              :title="sharedId === gif.id ? 'Link copied!' : 'Copy link'"
              @click.stop.prevent="handleShare(gif)"
            >
              {{ sharedId === gif.id ? 'Copied!' : '🔗' }}
            </button>
          </div>
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

    <!-- Infinite-scroll sentinel + status -->
    <div v-if="!isLoading && gifs.length > 0" class="mt-10 text-center">
      <!-- Sentinel: observed to trigger loading the next page -->
      <div ref="sentinel" class="h-px w-full" />

      <div
        v-if="isFetchingNextPage"
        class="flex items-center justify-center gap-2 py-4 text-sm text-gray-400"
      >
        <span
          class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-giphy-purple border-t-transparent"
        />
        Loading more…
      </div>
      <p
        v-else-if="!hasNextPage"
        class="py-4 text-sm text-gray-500"
      >
        🎉 You've reached the end
      </p>
    </div>
  </section>
</template>
