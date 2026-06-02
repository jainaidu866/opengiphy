<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'

import { fetchCollection } from '@/api/client'

const { data, isLoading, isError } = useQuery({
  queryKey: ['collection'],
  queryFn: () => fetchCollection(1, 50),
})

const gifs = computed(() => data.value ?? [])
</script>

<template>
  <section>
    <h1 class="mb-2 text-3xl font-bold text-white">Your Collection</h1>
    <p class="mb-8 text-gray-400">GIFs you've saved.</p>

    <!-- Loading skeleton -->
    <div
      v-if="isLoading"
      class="columns-1 gap-4 sm:columns-2 lg:columns-3 xl:columns-4"
    >
      <div
        v-for="n in 6"
        :key="n"
        class="mb-4 break-inside-avoid animate-pulse rounded-xl bg-ink-700"
        :style="{ height: `${160 + ((n * 37) % 140)}px` }"
      />
    </div>

    <div
      v-else-if="isError"
      class="rounded-xl border border-giphy-pink/40 bg-giphy-pink/10 p-8 text-center text-giphy-pink"
    >
      Something went wrong loading your collection.
    </div>

    <!-- Empty state -->
    <div
      v-else-if="gifs.length === 0"
      class="flex flex-col items-center justify-center rounded-2xl border border-dashed border-ink-600 bg-ink-800/50 py-24 text-center"
    >
      <p class="text-2xl font-bold text-white">No saved GIFs yet</p>
      <p class="mt-2 text-gray-400">
        Tap the 🔖 button on any GIF to save it here.
      </p>
      <RouterLink to="/" class="btn-primary mt-6">Discover GIFs</RouterLink>
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
  </section>
</template>
