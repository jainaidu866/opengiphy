<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { isAxiosError } from 'axios'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  fetchGif,
  fetchLikes,
  fetchRelated,
  fetchSavedStatus,
  reportGif,
  toggleLike,
  toggleSave,
} from '@/api/client'
import { useClipboard } from '@/composables/useClipboard'
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

// Related GIFs (by shared tags). Keyed by gif id so it refetches on navigation.
const { data: related } = useQuery({
  queryKey: computed(() => ['related', gifId.value]),
  queryFn: () => fetchRelated(gifId.value),
})
const relatedGifs = computed(() => related.value ?? [])

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

const { copied, copy: copyToClipboard } = useClipboard(1500)
function copyCode() {
  copyToClipboard(embedCode.value)
}

// Share: copy this GIF's page URL to the clipboard.
const { copied: shareCopied, copy: copyShare } = useClipboard()
function shareGif() {
  copyShare(window.location.href)
}

// Save (bookmark) to the user's collection. Only fetch status when logged in.
const { data: savedStatus } = useQuery({
  queryKey: computed(() => ['saved', gifId.value]),
  queryFn: () => fetchSavedStatus(gifId.value),
  enabled: isLoggedIn,
})
const saved = ref(false)
watch(
  savedStatus,
  (value) => {
    if (value) saved.value = value.saved
  },
  { immediate: true },
)

async function handleSave() {
  if (!isLoggedIn.value) {
    router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  const prev = saved.value
  saved.value = !prev // optimistic
  try {
    const res = await toggleSave(gifId.value)
    saved.value = res.saved
  } catch {
    saved.value = prev // revert on failure
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

// Info + embed panels are collapsed by default (revealed from the sidebar).
const showInfo = ref(false)
const showEmbed = ref(false)
const downloadName = computed(() => {
  const base =
    gif.value?.title?.replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '').toLowerCase() ||
    'opengiphy'
  return `${base}.gif`
})

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
  <div class="mx-auto max-w-5xl">
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

      <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <!-- ============ LEFT: preview + details ============ -->
        <div class="min-w-0">
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

          <!-- Title -->
          <h1 class="mt-6 text-3xl font-extrabold leading-tight text-white">
            {{ gif.title }}
          </h1>

          <p v-if="gif.description" class="mt-2 text-gray-300">
            {{ gif.description }}
          </p>

          <!-- Tags -->
          <div v-if="gif.tags.length" class="mt-4 flex flex-wrap gap-2">
            <RouterLink
              v-for="tag in gif.tags"
              :key="tag"
              :to="{ path: '/', query: { search: tag } }"
              class="rounded-full bg-ink-700 px-3 py-1 text-sm font-medium text-giphy-blue transition hover:bg-ink-600"
            >
              #{{ tag }}
            </RouterLink>
          </div>

          <!-- Meta line -->
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

          <!-- Info panel (toggled from the sidebar) -->
          <div
            v-if="showInfo"
            class="mt-5 grid grid-cols-2 gap-3 rounded-2xl border border-ink-700 bg-ink-800 p-5 text-sm"
          >
            <div>
              <p class="text-gray-500">GIF ID</p>
              <p class="font-semibold text-white">#{{ gif.id }}</p>
            </div>
            <div>
              <p class="text-gray-500">Category</p>
              <p class="font-semibold text-white">
                {{ gif.category ?? 'Uncategorized' }}
              </p>
            </div>
            <div>
              <p class="text-gray-500">Uploaded</p>
              <p class="font-semibold text-white">
                {{ formatDate(gif.created_at) }}
              </p>
            </div>
            <div>
              <p class="text-gray-500">Views</p>
              <p class="font-semibold text-white">{{ gif.view_count }}</p>
            </div>
          </div>

          <!-- Embed code generator (hidden until the Embed button is clicked) -->
          <div
            v-if="showEmbed"
            class="mt-8 rounded-2xl border border-ink-700 bg-ink-800 p-5"
          >
            <div class="mb-3 flex items-center justify-between">
              <h2 class="font-semibold text-white">Embed this GIF</h2>
              <button
                type="button"
                class="text-gray-500 transition hover:text-white"
                title="Close"
                @click="showEmbed = false"
              >
                ✕
              </button>
            </div>

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

          <!-- Related GIFs -->
          <section v-if="relatedGifs.length" class="mt-10">
            <h2 class="mb-4 text-xl font-bold text-white">Related GIFs</h2>
            <div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <RouterLink
                v-for="rel in relatedGifs"
                :key="rel.id"
                :to="`/gif/${rel.id}`"
                class="group block overflow-hidden rounded-xl border border-ink-700 bg-ink-800 card-hover hover:border-giphy-purple/60"
              >
                <img
                  :src="rel.url"
                  :alt="rel.title"
                  loading="lazy"
                  class="aspect-square w-full bg-ink-900 object-cover transition duration-300 group-hover:scale-[1.03]"
                />
                <p class="truncate p-2 text-sm text-gray-300">{{ rel.title }}</p>
              </RouterLink>
            </div>
          </section>
        </div>

        <!-- ============ RIGHT: action sidebar ============ -->
        <aside class="h-max space-y-4 lg:sticky lg:top-20">
          <!-- Uploader card -->
          <RouterLink
            :to="`/profile/${gif.uploader_username}`"
            class="flex items-center gap-3 rounded-2xl border border-ink-700 bg-ink-800 p-4 transition hover:border-giphy-green/50"
          >
            <span
              class="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-giphy-purple to-giphy-pink text-lg font-bold text-white"
            >
              {{ gif.uploader_username.charAt(0).toUpperCase() }}
            </span>
            <span class="min-w-0">
              <span class="block truncate font-semibold text-white">
                @{{ gif.uploader_username }}
              </span>
              <span class="block text-xs text-gray-400">Creator</span>
            </span>
          </RouterLink>

          <!-- Views stat -->
          <div class="rounded-2xl border border-ink-700 bg-ink-800 p-4 text-center">
            <p class="text-2xl font-extrabold text-white">
              {{ gif.view_count.toLocaleString() }}
            </p>
            <p class="text-xs uppercase tracking-wide text-gray-500">Views</p>
          </div>

          <!-- Action buttons -->
          <div class="space-y-2">
            <button
              type="button"
              class="detail-action"
              :class="
                likedByMe
                  ? 'border-giphy-pink bg-giphy-pink/10 text-giphy-pink'
                  : 'border-ink-700 text-gray-200 hover:border-giphy-pink hover:text-giphy-pink'
              "
              @click="handleLike"
            >
              <span>{{ likedByMe ? '♥' : '♡' }} {{ likeCount }}</span>
              <span class="text-sm text-gray-400">Favorite</span>
            </button>

            <button
              type="button"
              class="detail-action"
              :class="
                saved
                  ? 'border-giphy-blue bg-giphy-blue/10 text-giphy-blue'
                  : 'border-ink-700 text-gray-200 hover:border-giphy-blue hover:text-giphy-blue'
              "
              @click="handleSave"
            >
              <span>🔖</span>
              <span>{{ saved ? 'Saved' : 'Save' }}</span>
            </button>

            <button
              type="button"
              class="detail-action border-ink-700 text-gray-200 hover:border-giphy-green hover:text-giphy-green"
              :title="shareCopied ? 'Link copied!' : 'Copy link to this GIF'"
              @click="shareGif"
            >
              <span>🔗</span>
              <span>{{ shareCopied ? 'Copied!' : 'Copy Link' }}</span>
            </button>

            <a
              :href="gif.url"
              :download="downloadName"
              class="detail-action border-ink-700 text-gray-200 hover:border-giphy-purple hover:text-giphy-purple"
            >
              <span>⬇</span>
              <span>Download</span>
            </a>

            <button
              type="button"
              class="detail-action text-gray-200 hover:border-giphy-purple hover:text-giphy-purple"
              :class="
                showEmbed ? 'border-giphy-purple text-giphy-purple' : 'border-ink-700'
              "
              @click="showEmbed = !showEmbed"
            >
              <span>&lt;/&gt;</span>
              <span>Embed</span>
            </button>

            <button
              type="button"
              class="detail-action border-ink-700 text-gray-200 hover:border-white hover:text-white"
              @click="showInfo = !showInfo"
            >
              <span>ⓘ</span>
              <span>Info</span>
            </button>

            <button
              v-if="canReport"
              type="button"
              class="detail-action border-ink-700 text-gray-400 hover:border-giphy-pink hover:text-giphy-pink"
              @click="openReport"
            >
              <span>⚐</span>
              <span>Report</span>
            </button>
          </div>
        </aside>
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

<style scoped>
.detail-action {
  @apply flex w-full items-center justify-between gap-2 rounded-xl border px-4 py-3 font-semibold transition;
}
</style>
