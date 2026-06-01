<script setup lang="ts">
import { isAxiosError } from 'axios'
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'

import { uploadGif } from '@/api/client'

const router = useRouter()

const file = ref<File | null>(null)
const previewUrl = ref<string | null>(null)
const title = ref('')
const description = ref('')
const tagsInput = ref('')

const isDragging = ref(false)
const uploading = ref(false)
const progress = ref(0)
const error = ref('')

const TITLE_MAX = 100

const canSubmit = computed(
  () => !!file.value && title.value.trim().length > 0 && !uploading.value,
)

// Live preview of the tags the user is typing.
const parsedTags = computed(() =>
  tagsInput.value
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean),
)

function setFile(selected: File | null) {
  error.value = ''
  if (!selected) return
  if (!selected.name.toLowerCase().endsWith('.gif')) {
    error.value = 'Only .gif files are allowed.'
    return
  }
  file.value = selected
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = URL.createObjectURL(selected)
}

function onFileInput(event: Event) {
  const input = event.target as HTMLInputElement
  setFile(input.files?.[0] ?? null)
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  setFile(event.dataTransfer?.files?.[0] ?? null)
}

function clearFile() {
  file.value = null
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = null
  progress.value = 0
}

async function onSubmit() {
  if (!file.value || !title.value.trim()) return
  error.value = ''
  uploading.value = true
  progress.value = 0

  const tags = tagsInput.value
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean)

  const formData = new FormData()
  formData.append('file', file.value)
  formData.append('title', title.value.trim())
  formData.append('description', description.value.trim())
  formData.append('tags', JSON.stringify(tags))

  try {
    const gif = await uploadGif(formData, (percent) => {
      progress.value = percent
    })
    router.push(`/gif/${gif.id}`)
  } catch (err) {
    if (isAxiosError(err) && err.response?.data?.detail) {
      error.value = String(err.response.data.detail)
    } else {
      error.value = 'Upload failed. Please try again.'
    }
    uploading.value = false
  }
}

onBeforeUnmount(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})
</script>

<template>
  <div class="mx-auto max-w-2xl">
    <h1 class="text-3xl font-bold text-white">Upload a GIF</h1>
    <p class="mt-1 text-gray-400">Share your favorite animated moment.</p>

    <form class="mt-8 space-y-6" @submit.prevent="onSubmit">
      <!-- Drop zone / preview -->
      <div
        v-if="!previewUrl"
        class="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-16 text-center transition duration-200"
        :class="
          isDragging
            ? 'scale-[1.02] border-giphy-purple bg-giphy-purple/10 shadow-lg shadow-giphy-purple/20'
            : 'border-ink-600 bg-ink-800/50 hover:border-giphy-purple/60'
        "
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop"
        @click="($refs.fileInput as HTMLInputElement).click()"
      >
        <p class="text-4xl transition" :class="{ 'scale-125': isDragging }">
          🎞️
        </p>
        <p class="mt-3 font-semibold text-white">
          {{ isDragging ? 'Drop it!' : 'Drag & drop a GIF here' }}
        </p>
        <p class="mt-1 text-sm text-gray-400">or click to browse (.gif only)</p>
        <input
          ref="fileInput"
          type="file"
          accept="image/gif,.gif"
          class="hidden"
          @change="onFileInput"
        />
      </div>

      <div
        v-else
        class="relative overflow-hidden rounded-2xl border border-ink-700 bg-ink-800"
      >
        <img :src="previewUrl" alt="Preview" class="mx-auto max-h-96" />
        <button
          type="button"
          class="absolute right-3 top-3 rounded-full bg-ink-900/80 px-3 py-1 text-sm text-white hover:bg-giphy-pink"
          @click="clearFile"
        >
          Remove
        </button>
      </div>

      <!-- Fields -->
      <div>
        <div class="mb-1 flex items-center justify-between">
          <label for="title" class="block text-sm font-medium text-gray-300">
            Title <span class="text-giphy-pink">*</span>
          </label>
          <span
            class="text-xs"
            :class="
              title.length >= TITLE_MAX ? 'text-giphy-pink' : 'text-gray-500'
            "
          >
            {{ title.length }}/{{ TITLE_MAX }}
          </span>
        </div>
        <input
          id="title"
          v-model="title"
          type="text"
          required
          :maxlength="TITLE_MAX"
          placeholder="Give it a catchy title"
          class="input-field"
        />
      </div>

      <div>
        <label
          for="description"
          class="mb-1 block text-sm font-medium text-gray-300"
        >
          Description
        </label>
        <textarea
          id="description"
          v-model="description"
          rows="3"
          placeholder="Optional description"
          class="input-field resize-y"
        />
      </div>

      <div>
        <label for="tags" class="mb-1 block text-sm font-medium text-gray-300">
          Tags
        </label>
        <input
          id="tags"
          v-model="tagsInput"
          type="text"
          placeholder="funny, cat, reaction (comma separated)"
          class="input-field"
        />
        <div v-if="parsedTags.length" class="mt-2 flex flex-wrap gap-2">
          <span
            v-for="tag in parsedTags"
            :key="tag"
            class="rounded-full bg-ink-700 px-3 py-1 text-sm text-giphy-blue"
          >
            #{{ tag }}
          </span>
        </div>
      </div>

      <!-- Progress -->
      <div v-if="uploading" class="space-y-2">
        <div class="h-2 w-full overflow-hidden rounded-full bg-ink-700">
          <div
            class="h-full bg-gradient-to-r from-giphy-purple to-giphy-pink transition-all"
            :style="{ width: `${progress}%` }"
          />
        </div>
        <p class="text-center text-sm text-gray-400">
          Uploading… {{ progress }}%
        </p>
      </div>

      <p
        v-if="error"
        class="rounded-lg border border-giphy-pink/40 bg-giphy-pink/10 px-3 py-2 text-sm text-giphy-pink"
      >
        {{ error }}
      </p>

      <button type="submit" class="btn-primary w-full" :disabled="!canSubmit">
        {{ uploading ? 'Uploading…' : 'Upload GIF' }}
      </button>
    </form>
  </div>
</template>
