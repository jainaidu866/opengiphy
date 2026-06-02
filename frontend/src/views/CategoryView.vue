<script setup lang="ts">
import { useInfiniteQuery } from '@tanstack/vue-query'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { categories, fetchGifs } from '@/api/client'

const PAGE_SIZE = 20

const route = useRoute()
const name = computed(() => String(route.params.name || ''))
const isValid = computed(() =>
  (categories as readonly string[]).includes(name.value),
)
const displayName = computed(() =>
  name.value ? name.value.charAt(0).toUpperCase() + name.value.slice(1) : '',
)

const {
  data,
  isLoading,
  isError,
  isFetchingNextPage,
  hasNextPage,
  fetchNextPage,
} = useInfiniteQuery({
  queryKey: computed(() => ['category', name.value]),
  queryFn: ({ pageParam }) =>
    fetchGifs(pageParam, PAGE_SIZE, undefined, 'new', name.value),
  initialPageParam: 1,
  getNextPageParam: (lastPage, allPages) =>
    lastPage.length === PAGE_SIZE ? allPages.length + 1 : undefined,
  enabled: isValid,
})

const gifs = computed(() => (data.value?.pages ?? []).flat())

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
</script>

<template>
  <section>
    <div class="mb-8 flex items-center gap-3">
      <RouterLink
        to="/categories"
        class="text-sm text-gray-400 transition hover:text-white"
      >
        ← All categories
      </RouterLink>
    </div>

    <h1 class="mb-6 text-3xl font-bold text-white">
      {{ displayName }} GIFs
    </h1>

    <!-- Invalid category -->
    <div
      v-if="!isValid"
      class="rounded-xl border border-giphy-pink/40 bg-giphy-pink/10 p-8 text-center text-giphy-pink"
    >
      Unknown category “{{ name }}”.
      <RouterLink to="/categories" class="block mt-3 text-giphy-blue hover:underline">
        Browse categories
      </RouterLink>
    </div>

    <!-- Loading skeleton -->
    <div
      v-else-if="isLoading"
      class="columns-1 gap-4 sm:columns-2 lg:columns-3 xl:columns-4"
    >
      <div
        v-for="n in 8"
        :key="n"
        class="mb-4 break-inside-avoid animate-pulse rounded-xl bg-ink-700"
        :style="{ height: `${160 + ((n * 37) % 140)}px` }"
      />
    </div>

    <div
      v-else-if="isError"
      class="rounded-xl border border-giphy-pink/40 bg-giphy-pink/10 p-8 text-center text-giphy-pink"
    >
      Something went wrong loading GIFs.
    </div>

    <!-- Empty state -->
    <div
      v-else-if="gifs.length === 0"
      class="flex flex-col items-center justify-center rounded-2xl border border-dashed border-ink-600 bg-ink-800/50 py-24 text-center"
    >
      <p class="text-2xl font-bold text-white">No GIFs in this category yet</p>
      <p class="mt-2 text-gray-400">Be the first to upload one!</p>
      <RouterLink to="/upload" class="btn-primary mt-6">Upload a GIF</RouterLink>
    </div>

    <!-- Grid -->
    <div v-else class="columns-1 gap-4 sm:columns-2 lg:columns-3 xl:columns-4">
      <RouterLink
        v-for="gif in gifs"
        :key="gif.id"
        :to="`/gif/${gif.id}`"
        class="group mb-4 block animate-fade-in break-inside-avoid overflow-hidden rounded-xl border border-ink-700 bg-ink-800 transition hover:border-giphy-purple/60"
      >
        <img
          :src="gif.url"
          :alt="gif.title"
          loading="lazy"
          class="w-full bg-ink-900 transition duration-300 group-hover:scale-[1.03]"
        />
        <h3 class="truncate p-3 font-semibold text-white">{{ gif.title }}</h3>
      </RouterLink>
    </div>

    <!-- Infinite-scroll sentinel -->
    <div v-if="isValid && !isLoading && gifs.length > 0" class="mt-10 text-center">
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
      <p v-else-if="!hasNextPage" class="py-4 text-sm text-gray-500">
        🎉 You've reached the end
      </p>
    </div>
  </section>
</template>
