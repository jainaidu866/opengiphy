<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { isAxiosError } from 'axios'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchGif, fetchLikes, reportGif, toggleLike } from '@/api/client'
import { useAuth } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const { isLoggedIn, user } = useAuth()
const gifId = computed(() => route.params.id as string)

const { data: gif, isLoading, isError } = useQuery({
  queryKey: computed(() => ['gif', gifId.value]),
  queryFn: () => fetchGif(gifId.value),
})

// Likes: fetch initial state, then track locally for optimistic toggling.
const { data: likes } = useQuery({
  queryKey: computed(() => ['likes', gifId.value]),
  queryFn: () => fetchLikes(gifId.value),
})

const likeCount = ref(0)
const likedByMe = ref(false)
watch(
  likes,
  (value) => {
    if (value) {
      likeCount.value = value.like_count
      likedByMe.value = value.liked_by_me
    }
  },
  { immediate: true },
)

async function handleLike() {
  if (!isLoggedIn.value) {
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  const prevLiked = likedByMe.value
  const prevCount = likeCount.value
  // Optimistic update.
  likedByMe.value = !prevLiked
  likeCount.value = prevCount + (likedByMe.value ? 1 : -1)
  try {
    const res = await toggleLike(gifId.value)
    likedByMe.value = res.liked
    likeCount.value = res.like_count
  } catch {
    likedByMe.value = prevLiked // revert on failure
    likeCount.value = prevCount
  }
}

const absoluteUrl = computed(() =>
  gif.value ? `${window.location.origin}${gif.value.url}` : '',
)

type Tab = 'html' | 'markdown' | 'url'
const activeTab = ref<Tab>('html')
const tabs: { key: Tab; label: string }[] = [
  { key: 'html', label: 'HTML' },
  { key: 'markdown', label: 'Markdown' },
  { key: 'url', label: 'Direct URL' },
]

const embedCode = computed(() => {
  if (!gif.value) return ''
  switch (activeTab.value) {
    case 'html':
      return `<img src="${absoluteUrl.value}" alt="${gif.value.title}">`
    case 'markdown':
      return `![${gif.value.title}](${absoluteUrl.value})`
    case 'url':
      return absoluteUrl.value
  }
})

const copied = ref(false)
async function copyCode() {
  try {
    await navigator.clipboard.writeText(embedCode.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 1500)
  } catch {
    copied.value = false
  }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

const likeLabel = computed(
  () => `${likeCount.value} ${likeCount.value === 1 ? 'like' : 'likes'}`,
)

// True only for a logged-in user viewing someone else's GIF.
const isOwnGif = computed(
  () => isLoggedIn.value && user.value?.username === gif.value?.uploader_username,
)
const canReport = computed(() => isLoggedIn.value && !isOwnGif.value)

// --- Report modal ---
const showReport = ref(false)
const reportReason = ref('')
const reportError = ref('')
const reportSuccess = ref(false)
const reportSubmitting = ref(false)

function openReport() {
  reportReason.value = ''
  reportError.value = ''
  reportSuccess.value = false
  showReport.value = true
}
function closeReport() {
  showReport.value = false
}

async function submitReport() {
  reportError.value = ''
  if (reportReason.value.trim().length < 10) {
    reportError.value = 'Please provide at least 10 characters.'
    return
  }
  reportSubmitting.value = true
  try {
    await reportGif(gifId.value, reportReason.value.trim())
    reportSuccess.value = true
    setTimeout(() => (showReport.value = false), 1500)
  } catch (err) {
    if (isAxiosError(err) && err.response?.data?.detail) {
      reportError.value = String(err.response.data.detail)
    } else {
      reportError.value = 'Could not submit report. Please try again.'
    }
  } finally {
    reportSubmitting.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-3xl">
    <div v-if="isLoading" class="py-24 text-center text-gray-400">
      Loading…
    </div>

    <div
      v-else-if="isError || !gif"
      class="rounded-xl border border-giphy-pink/40 bg-giphy-pink/10 p-8 text-center text-giphy-pink"
    >
      This GIF could not be found.
      <RouterLink to="/" class="block mt-4 text-giphy-blue hover:underline">
        Back to home
      </RouterLink>
    </div>

    <template v-else>
      <!-- Back to home -->
      <RouterLink
        to="/"
        class="mb-4 inline-flex items-center gap-1 text-sm text-gray-400 transition hover:text-white"
      >
        ← Back to home
      </RouterLink>

      <!-- GIF preview -->
      <div
        class="overflow-hidden rounded-2xl border border-ink-700 bg-ink-800 p-3"
      >
        <img
          :src="gif.url"
          :alt="gif.title"
          class="mx-auto max-h-[70vh] rounded-lg"
        />
      </div>

      <!-- Report (subtle, only for logged-in non-owners) -->
      <div v-if="canReport" class="mt-2 text-right">
        <button
          type="button"
          class="text-xs text-gray-500 transition hover:text-giphy-pink"
          @click="openReport"
        >
          ⚐ Report this GIF
        </button>
      </div>

      <!-- Metadata -->
      <div class="mt-6">
        <div class="flex items-start justify-between gap-4">
          <h1 class="text-3xl font-bold text-white">{{ gif.title }}</h1>
          <button
            type="button"
            class="flex shrink-0 items-center gap-2 rounded-lg border px-4 py-2 font-semibold transition"
            :class="
              likedByMe
                ? 'border-giphy-pink bg-giphy-pink/10 text-giphy-pink'
                : 'border-ink-600 text-gray-300 hover:border-giphy-pink hover:text-giphy-pink'
            "
            @click="handleLike"
          >
            {{ likedByMe ? '♥' : '♡' }} {{ likeCount }}
          </button>
        </div>

        <p v-if="gif.description" class="mt-3 text-gray-300">
          {{ gif.description }}
        </p>

        <!-- Tags -->
        <div v-if="gif.tags.length" class="mt-4 flex flex-wrap gap-2">
          <RouterLink
            v-for="tag in gif.tags"
            :key="tag"
            :to="{ path: '/', query: { search: tag } }"
            class="rounded-full bg-ink-700 px-3 py-1 text-sm text-giphy-blue transition hover:bg-ink-600"
          >
            #{{ tag }}
          </RouterLink>
        </div>

        <div
          class="mt-5 flex flex-wrap items-center gap-x-6 gap-y-1 text-sm text-gray-400"
        >
          <span>
            by
            <RouterLink
              :to="`/profile/${gif.uploader_username}`"
              class="font-semibold text-giphy-green hover:underline"
            >
              @{{ gif.uploader_username }}
            </RouterLink>
          </span>
          <span>{{ formatDate(gif.created_at) }}</span>
          <span>👁 {{ gif.view_count }} views</span>
          <span>♥ {{ likeLabel }}</span>
        </div>
      </div>

      <!-- Embed code generator -->
      <div class="mt-8 rounded-2xl border border-ink-700 bg-ink-800 p-5">
        <h2 class="mb-3 font-semibold text-white">Embed this GIF</h2>

        <div class="flex gap-1 border-b border-ink-700">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            class="px-4 py-2 text-sm font-medium transition"
            :class="
              activeTab === tab.key
                ? 'border-b-2 border-giphy-purple text-white'
                : 'text-gray-400 hover:text-white'
            "
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="mt-4 flex items-stretch gap-2">
          <code
            class="flex-1 overflow-x-auto rounded-lg bg-ink-900 px-4 py-3 text-sm text-giphy-green"
          >
            {{ embedCode }}
          </code>
          <button
            type="button"
            class="shrink-0 rounded-lg bg-gradient-to-r from-giphy-purple to-giphy-pink px-4 text-sm font-semibold text-white transition hover:opacity-90"
            @click="copyCode"
          >
            {{ copied ? 'Copied!' : 'Copy' }}
          </button>
        </div>
      </div>
    </template>

    <!-- Report modal -->
    <div
      v-if="showReport"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      @click.self="closeReport"
    >
      <div class="w-full max-w-md rounded-2xl border border-ink-700 bg-ink-800 p-6">
        <div v-if="reportSuccess" class="py-6 text-center">
          <p class="text-4xl">✅</p>
          <p class="mt-3 text-lg font-semibold text-white">
            Thanks for reporting
          </p>
          <p class="mt-1 text-sm text-gray-400">
            Our team will review this GIF.
          </p>
        </div>

        <template v-else>
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-bold text-white">Report this GIF</h2>
            <button
              type="button"
              class="text-gray-500 hover:text-white"
              @click="closeReport"
            >
              ✕
            </button>
          </div>
          <p class="mt-1 text-sm text-gray-400">
            Tell us what's wrong (at least 10 characters).
          </p>

          <textarea
            v-model="reportReason"
            rows="4"
            placeholder="Describe the issue…"
            class="input-field mt-4 resize-y"
          />

          <p
            v-if="reportError"
            class="mt-2 rounded-lg border border-giphy-pink/40 bg-giphy-pink/10 px-3 py-2 text-sm text-giphy-pink"
          >
            {{ reportError }}
          </p>

          <div class="mt-5 flex justify-end gap-3">
            <button
              type="button"
              class="rounded-lg border border-ink-600 px-4 py-2 text-sm font-medium text-gray-300 transition hover:text-white"
              @click="closeReport"
            >
              Cancel
            </button>
            <button
              type="button"
              class="btn-primary !px-4 !py-2 text-sm"
              :disabled="reportSubmitting"
              @click="submitReport"
            >
              {{ reportSubmitting ? 'Submitting…' : 'Submit report' }}
            </button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
