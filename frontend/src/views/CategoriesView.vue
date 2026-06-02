<script setup lang="ts">
import { categories } from '@/api/client'

const emojis: Record<string, string> = {
  funny: '😂',
  reactions: '😮',
  sports: '⚽',
  animals: '🐾',
  food: '🍕',
  music: '🎵',
  gaming: '🎮',
  anime: '✨',
  memes: '🤣',
}

function label(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1)
}
</script>

<template>
  <section>
    <h1 class="mb-2 text-3xl font-bold text-white">Categories</h1>
    <p class="mb-8 text-gray-400">Browse GIFs by category.</p>

    <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      <RouterLink
        v-for="name in categories"
        :key="name"
        :to="`/category/${name}`"
        class="group flex flex-col items-center justify-center rounded-2xl border border-ink-700 bg-ink-800 py-10 transition hover:border-giphy-purple/60 hover:bg-ink-700"
      >
        <span class="text-4xl transition group-hover:scale-110">
          {{ emojis[name] }}
        </span>
        <span class="mt-3 font-semibold text-white">{{ label(name) }}</span>
      </RouterLink>
    </div>
  </section>
</template>
