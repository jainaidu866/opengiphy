<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useDraft } from '@/stores/draft'
import {
  ANIMATION_CHOICES,
  ASPECT_CHOICES,
  EMOJI_CATEGORIES,
  FILTER_CHOICES,
  FONT_CHOICES,
  bytesToGifFile,
  decodeGif,
  encodeStudioGif,
  frameFromImage,
  hitTest,
  randomId,
  renderComposite,
  type AspectKey,
  type DecodedGif,
  type EmojiLayer,
  type FitMode,
  type GifFilter,
  type Layer,
  type OutputConfig,
  type RenderState,
  type TextLayer,
} from '@/lib/gifStudio'

const router = useRouter()
const { setDraft } = useDraft()

type Step = 'type' | 'source' | 'edit'
type Kind = 'gif' | 'sticker'
type Tool = 'caption' | 'stickers' | 'filter' | 'crop' | 'trim' | 'layers'

const step = ref<Step>('type')
const kind = ref<Kind>('gif')
const activeTool = ref<Tool>('caption')

const error = ref('')
const isDragging = ref(false)
const rendering = ref(false)
const isPlaying = ref(true)

// Decoded source + the live preview canvas.
const decoded = ref<DecodedGif | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
let rafId: number | null = null
let objectUrl: string | null = null
let loopStart = performance.now()

// --- Render state -----------------------------------------------------------
const filter = ref<GifFilter>('none')
const layers = ref<Layer[]>([])
const selectedId = ref<string | null>(null)

// Crop / resize.
const aspect = ref<AspectKey>('original')
const fit = ref<FitMode>('cover')
const customW = ref(320)
const customH = ref(320)

// Trim (inclusive frame indices).
const trimStart = ref(0)
const trimEnd = ref(0)
const thumbs = ref<string[]>([])

// Emoji / sticker picker.
const emojiSearch = ref('')
const recentEmojis = ref<string[]>([])
const activeEmojiTab = ref('Trending')

// --- Helpers ----------------------------------------------------------------
function clamp01(n: number): number {
  return Math.min(1, Math.max(0, n))
}
function clampInt(n: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, Math.round(n || 0)))
}

const output = computed<OutputConfig>(() => {
  const d = decoded.value
  if (!d) return { width: 1, height: 1, fit: fit.value }
  switch (aspect.value) {
    case 'landscape': {
      const base = Math.min(480, Math.max(d.width, d.height))
      return { width: base, height: Math.round((base * 9) / 16), fit: fit.value }
    }
    case 'portrait': {
      const base = Math.min(480, Math.max(d.width, d.height))
      return { width: Math.round((base * 9) / 16), height: base, fit: fit.value }
    }
    case 'custom':
      return {
        width: clampInt(customW.value, 32, 1000),
        height: clampInt(customH.value, 32, 1000),
        fit: fit.value,
      }
    default: {
      const longest = Math.max(d.width, d.height)
      const scale = longest > 480 ? 480 / longest : 1
      return {
        width: Math.round(d.width * scale),
        height: Math.round(d.height * scale),
        fit: fit.value,
      }
    }
  }
})

const sIdx = computed(() => Math.min(trimStart.value, trimEnd.value))
const eIdx = computed(() => Math.max(trimStart.value, trimEnd.value))
const lastFrame = computed(() =>
  decoded.value ? decoded.value.frames.length - 1 : 0,
)
const isAnimated = computed(() => (decoded.value?.frames.length ?? 0) > 1)

function sumDelays(from: number, toInclusive: number): number {
  const d = decoded.value
  if (!d) return 0
  let acc = 0
  for (let i = from; i <= toInclusive; i++) acc += d.frames[i]?.delay ?? 0
  return acc
}
const trimDuration = computed(() => sumDelays(sIdx.value, eIdx.value))

function clock(ms: number): string {
  const s = ms / 1000
  const m = Math.floor(s / 60)
  const rem = s - m * 60
  return `${m}:${rem.toFixed(2).padStart(5, '0')}`
}
const trimStartLabel = computed(() => clock(sumDelays(0, sIdx.value - 1)))
const trimEndLabel = computed(() => clock(sumDelays(0, eIdx.value)))
const durationLabel = computed(() => `${(trimDuration.value / 1000).toFixed(2)}s`)

const selectedLayer = computed(
  () => layers.value.find((l) => l.id === selectedId.value) ?? null,
)
const selectedText = computed<TextLayer | null>(() =>
  selectedLayer.value?.type === 'text' ? (selectedLayer.value as TextLayer) : null,
)
const selectedEmoji = computed<EmojiLayer | null>(() =>
  selectedLayer.value?.type === 'emoji'
    ? (selectedLayer.value as EmojiLayer)
    : null,
)

const emojiTabs = computed(() => [
  { label: 'Favourites', emojis: recentEmojis.value },
  ...EMOJI_CATEGORIES,
])
function selectEmojiTab(label: string) {
  activeEmojiTab.value = label
  emojiSearch.value = ''
}
const displayedEmojis = computed(() => {
  const q = emojiSearch.value.trim().toLowerCase()
  if (q) {
    return EMOJI_CATEGORIES.filter((c) =>
      c.label.toLowerCase().includes(q),
    ).flatMap((c) => c.emojis)
  }
  const tab = emojiTabs.value.find((t) => t.label === activeEmojiTab.value)
  return tab ? tab.emojis : []
})

// --- File intake ------------------------------------------------------------
function chooseKind(k: Kind) {
  kind.value = k
  step.value = 'source'
}

async function handleFile(file: File | null | undefined) {
  error.value = ''
  if (!file) return
  const isGif =
    file.type === 'image/gif' || file.name.toLowerCase().endsWith('.gif')
  try {
    let result: DecodedGif
    if (isGif) {
      result = decodeGif(await file.arrayBuffer())
    } else if (file.type.startsWith('image/')) {
      result = await decodeImageFile(file)
    } else {
      error.value = 'Please choose a GIF or an image file.'
      return
    }
    decoded.value = result
    layers.value = []
    selectedId.value = null
    filter.value = 'none'
    aspect.value = 'original'
    fit.value = 'cover'
    customW.value = clampInt(result.width, 32, 1000)
    customH.value = clampInt(result.height, 32, 1000)
    trimStart.value = 0
    trimEnd.value = result.frames.length - 1
    thumbs.value = buildThumbs(result)
    activeTool.value = 'caption'
    step.value = 'edit'
    isPlaying.value = true
    startLoop()
  } catch (err) {
    console.error(err)
    error.value = 'Could not read that file. Try a different GIF or image.'
  }
}

function decodeImageFile(file: File): Promise<DecodedGif> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      const result = frameFromImage(img)
      URL.revokeObjectURL(url)
      resolve(result)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('image load failed'))
    }
    img.src = url
  })
}

function onFileInput(event: Event) {
  const input = event.target as HTMLInputElement
  void handleFile(input.files?.[0])
}
function onDrop(event: DragEvent) {
  isDragging.value = false
  void handleFile(event.dataTransfer?.files?.[0])
}

function buildThumbs(d: DecodedGif): string[] {
  const thumbW = 56
  const thumbH = Math.max(1, Math.round((thumbW * d.height) / d.width))
  const out = document.createElement('canvas')
  out.width = thumbW
  out.height = thumbH
  const octx = out.getContext('2d')!
  const src = document.createElement('canvas')
  src.width = d.width
  src.height = d.height
  const sctx = src.getContext('2d')!
  const result: string[] = []
  const maxThumbs = 16
  const stepN = Math.max(1, Math.ceil(d.frames.length / maxThumbs))
  for (let i = 0; i < d.frames.length; i += stepN) {
    sctx.putImageData(d.frames[i].imageData, 0, 0)
    octx.clearRect(0, 0, thumbW, thumbH)
    octx.drawImage(src, 0, 0, thumbW, thumbH)
    result.push(out.toDataURL())
  }
  return result
}

// --- Live preview loop ------------------------------------------------------
function startLoop() {
  stopLoop()
  loopStart = performance.now()
  const tick = (now: number) => {
    const cv = canvasRef.value
    const d = decoded.value
    if (cv && d) {
      const out = output.value
      if (cv.width !== out.width || cv.height !== out.height) {
        cv.width = out.width
        cv.height = out.height
      }
      const ctx = cv.getContext('2d')!
      const frames = d.frames
      const s = sIdx.value
      const e = eIdx.value
      const count = e - s + 1
      let idx = s
      let phase = 0
      if (count > 1 && trimDuration.value > 0) {
        const elapsed = isPlaying.value
          ? (now - loopStart) % trimDuration.value
          : 0
        let acc = 0
        for (let i = s; i <= e; i++) {
          acc += frames[i].delay
          if (elapsed < acc) {
            idx = i
            break
          }
        }
        phase = (idx - s) / count
      }
      const state: RenderState = {
        filter: filter.value,
        layers: layers.value,
        selectedId: selectedId.value,
      }
      renderComposite(ctx, frames[idx].imageData, out, state, phase, true)
    }
    rafId = requestAnimationFrame(tick)
  }
  rafId = requestAnimationFrame(tick)
}

function stopLoop() {
  if (rafId !== null) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
}

function togglePlay() {
  isPlaying.value = !isPlaying.value
  loopStart = performance.now()
}

function reset() {
  stopLoop()
  decoded.value = null
  layers.value = []
  selectedId.value = null
  thumbs.value = []
  step.value = 'type'
}

// --- Layer manipulation -----------------------------------------------------
function addText() {
  const layer: TextLayer = {
    id: randomId(),
    type: 'text',
    x: 0.5,
    y: 0.85,
    text: 'Your text',
    fontFamily: FONT_CHOICES[0].value,
    scale: 0.12,
    color: '#ffffff',
    animation: 'none',
  }
  layers.value.push(layer)
  selectedId.value = layer.id
  activeTool.value = 'caption'
}

function addEmoji(emoji: string) {
  const layer: EmojiLayer = {
    id: randomId(),
    type: 'emoji',
    x: 0.5,
    y: 0.5,
    emoji,
    scale: 0.25,
  }
  layers.value.push(layer)
  selectedId.value = layer.id
  recentEmojis.value = [
    emoji,
    ...recentEmojis.value.filter((e) => e !== emoji),
  ].slice(0, 16)
}

function duplicateSelected() {
  const l = selectedLayer.value
  if (!l) return
  const copy = {
    ...l,
    id: randomId(),
    x: clamp01(l.x + 0.05),
    y: clamp01(l.y + 0.05),
  } as Layer
  layers.value.push(copy)
  selectedId.value = copy.id
}

function deleteSelected() {
  if (!selectedId.value) return
  layers.value = layers.value.filter((l) => l.id !== selectedId.value)
  selectedId.value = null
}

function bringToFront(id: string) {
  const idx = layers.value.findIndex((l) => l.id === id)
  if (idx === -1) return
  const [l] = layers.value.splice(idx, 1)
  layers.value.push(l)
  selectedId.value = id
}

function layerLabel(l: Layer): string {
  return l.type === 'text' ? l.text.trim() || 'Text' : l.emoji
}

// --- Drag layers on the canvas ----------------------------------------------
const dragging = ref(false)
const dragOffset = { x: 0, y: 0 }

function canvasPoint(ev: PointerEvent): { x: number; y: number } {
  const cv = canvasRef.value!
  const rect = cv.getBoundingClientRect()
  return {
    x: ((ev.clientX - rect.left) / rect.width) * cv.width,
    y: ((ev.clientY - rect.top) / rect.height) * cv.height,
  }
}

function onPointerDown(ev: PointerEvent) {
  const cv = canvasRef.value
  if (!cv) return
  const { x, y } = canvasPoint(ev)
  const ctx = cv.getContext('2d')!
  const hit = hitTest(ctx, layers.value, output.value, x, y)
  selectedId.value = hit ? hit.id : null
  if (hit) {
    dragging.value = true
    cv.setPointerCapture(ev.pointerId)
    dragOffset.x = x / cv.width - hit.x
    dragOffset.y = y / cv.height - hit.y
  }
}

function onPointerMove(ev: PointerEvent) {
  if (!dragging.value || !selectedId.value) return
  const cv = canvasRef.value
  if (!cv) return
  const { x, y } = canvasPoint(ev)
  const layer = layers.value.find((l) => l.id === selectedId.value)
  if (!layer) return
  layer.x = clamp01(x / cv.width - dragOffset.x)
  layer.y = clamp01(y / cv.height - dragOffset.y)
}

function onPointerUp(ev: PointerEvent) {
  dragging.value = false
  const cv = canvasRef.value
  if (cv?.hasPointerCapture(ev.pointerId)) cv.releasePointerCapture(ev.pointerId)
}

// --- Output -----------------------------------------------------------------
function bake(): Uint8Array {
  if (!decoded.value) throw new Error('nothing to bake')
  const state: RenderState = {
    filter: filter.value,
    layers: layers.value,
    selectedId: null,
  }
  return encodeStudioGif(
    decoded.value,
    output.value,
    state,
    sIdx.value,
    eIdx.value,
  )
}

function suggestedTitle(): string | undefined {
  const firstText = layers.value.find((l) => l.type === 'text') as
    | TextLayer
    | undefined
  return firstText?.text.trim() || undefined
}

function download() {
  if (!decoded.value) return
  rendering.value = true
  setTimeout(() => {
    try {
      const bytes = bake()
      const file = bytesToGifFile(bytes, `${kind.value}-${Date.now()}.gif`)
      if (objectUrl) URL.revokeObjectURL(objectUrl)
      objectUrl = URL.createObjectURL(file)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = file.name
      a.click()
    } catch (err) {
      console.error(err)
      error.value = 'Rendering failed. Try a smaller GIF.'
    } finally {
      rendering.value = false
    }
  }, 30)
}

function continueToUpload() {
  if (!decoded.value) return
  rendering.value = true
  setTimeout(() => {
    try {
      const bytes = bake()
      const file = bytesToGifFile(bytes, `${kind.value}-${Date.now()}.gif`)
      setDraft(file, {
        title: suggestedTitle(),
        isSticker: kind.value === 'sticker',
      })
      router.push('/upload')
    } catch (err) {
      console.error(err)
      error.value = 'Rendering failed. Try a smaller GIF.'
      rendering.value = false
    }
  }, 30)
}

onBeforeUnmount(() => {
  stopLoop()
  if (objectUrl) URL.revokeObjectURL(objectUrl)
})

const tools: { key: Tool; label: string; icon: string }[] = [
  { key: 'caption', label: 'Caption', icon: 'Aa' },
  { key: 'stickers', label: 'Stickers', icon: '😊' },
  { key: 'filter', label: 'Filters', icon: '✦' },
  { key: 'crop', label: 'Crop', icon: '⛶' },
  { key: 'trim', label: 'Trim', icon: '✂' },
  { key: 'layers', label: 'Layers', icon: '▤' },
]
</script>

<template>
  <div class="mx-auto max-w-5xl">
    <header class="mb-6 text-center">
      <h1 class="text-gradient-animated text-4xl font-extrabold tracking-tight">
        GIF Studio
      </h1>
      <p class="mt-1 text-gray-400">
        Create a {{ kind === 'sticker' ? 'sticker' : 'GIF' }} — add captions,
        stickers, filters, crop &amp; trim, then download or publish.
      </p>
    </header>

    <!-- STEP 1: choose GIF or Sticker -->
    <div v-if="step === 'type'" class="grid gap-5 sm:grid-cols-2">
      <button type="button" class="studio-card group" @click="chooseKind('gif')">
        <span class="text-5xl transition group-hover:scale-110">🎬</span>
        <span class="mt-3 text-xl font-bold text-white">GIF</span>
        <span class="mt-1 text-sm text-gray-400">
          Caption an animated GIF and share it.
        </span>
      </button>
      <button
        type="button"
        class="studio-card group"
        @click="chooseKind('sticker')"
      >
        <span class="text-5xl transition group-hover:scale-110">🌟</span>
        <span class="mt-3 text-xl font-bold text-white">Sticker</span>
        <span class="mt-1 text-sm text-gray-400">
          Make a fun captioned sticker.
        </span>
      </button>
    </div>

    <!-- STEP 2: pick a source file -->
    <div v-else-if="step === 'source'">
      <div
        class="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-20 text-center transition duration-200"
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
        <p class="text-5xl" :class="{ 'scale-125': isDragging }">📁</p>
        <p class="mt-3 font-semibold text-white">
          {{ isDragging ? 'Drop it!' : `Choose a ${kind} source` }}
        </p>
        <p class="mt-1 text-sm text-gray-400">
          Drag &amp; drop or click — GIF or image (PNG/JPG/WebP)
        </p>
        <input
          ref="fileInput"
          type="file"
          accept=".gif,image/gif,image/png,image/jpeg,image/webp"
          class="hidden"
          @change="onFileInput"
        />
      </div>
      <button
        type="button"
        class="mt-4 text-sm text-gray-400 transition hover:text-white"
        @click="step = 'type'"
      >
        ← Back
      </button>
    </div>

    <!-- STEP 3: editor -->
    <div v-else class="grid gap-5 lg:grid-cols-[1fr_320px]">
      <!-- Preview + tool rail -->
      <div class="flex gap-3">
        <div
          class="relative flex flex-1 items-center justify-center overflow-hidden rounded-2xl border border-ink-700 bg-ink-900"
          :class="kind === 'sticker' ? 'studio-checkerboard' : ''"
        >
          <canvas
            ref="canvasRef"
            class="block max-h-[60vh] max-w-full touch-none select-none"
            :style="{ cursor: dragging ? 'grabbing' : 'grab' }"
            @pointerdown="onPointerDown"
            @pointermove="onPointerMove"
            @pointerup="onPointerUp"
            @pointerleave="onPointerUp"
          />
          <button
            v-if="isAnimated"
            type="button"
            class="absolute bottom-3 left-3 flex h-10 w-10 items-center justify-center rounded-full bg-black/60 text-white backdrop-blur transition hover:bg-black/80"
            :title="isPlaying ? 'Pause' : 'Play'"
            @click="togglePlay"
          >
            {{ isPlaying ? '⏸' : '▶' }}
          </button>
          <span
            class="absolute bottom-3 right-3 rounded-full bg-black/60 px-3 py-1 text-xs font-semibold text-white backdrop-blur"
          >
            {{ durationLabel }}
          </span>
        </div>

        <!-- Giphy-style vertical tool rail -->
        <div class="flex flex-col gap-2">
          <button
            v-for="tool in tools"
            :key="tool.key"
            type="button"
            class="flex h-12 w-12 flex-col items-center justify-center rounded-xl border text-base font-bold transition"
            :class="
              activeTool === tool.key
                ? 'border-giphy-purple bg-giphy-purple/15 text-white'
                : 'border-ink-700 bg-ink-800 text-gray-400 hover:text-white'
            "
            :title="tool.label"
            @click="activeTool = tool.key"
          >
            <span>{{ tool.icon }}</span>
          </button>
        </div>
      </div>

      <!-- Controls -->
      <div class="rounded-2xl border border-ink-700 bg-ink-800 p-5">
        <!-- Caption tool -->
        <div v-if="activeTool === 'caption'" class="space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="font-bold text-white">Caption</h2>
            <button
              type="button"
              class="rounded-lg bg-giphy-purple/20 px-3 py-1 text-xs font-semibold text-giphy-purple transition hover:bg-giphy-purple/30"
              @click="addText"
            >
              + Add text
            </button>
          </div>

          <p v-if="!selectedText" class="text-sm text-gray-400">
            Add a text layer, then drag it on the preview to position it.
          </p>

          <template v-else>
            <input
              v-model="selectedText.text"
              type="text"
              placeholder="Add a caption…"
              class="input-field"
            />
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-400">
                Font
              </label>
              <select v-model="selectedText.fontFamily" class="input-field">
                <option
                  v-for="f in FONT_CHOICES"
                  :key="f.value"
                  :value="f.value"
                >
                  {{ f.label }}
                </option>
              </select>
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-400">
                Animation
              </label>
              <div class="grid grid-cols-3 gap-2">
                <button
                  v-for="a in ANIMATION_CHOICES"
                  :key="a.value"
                  type="button"
                  class="rounded-lg border px-2 py-1.5 text-xs font-semibold transition"
                  :class="
                    selectedText.animation === a.value
                      ? 'border-giphy-pink bg-giphy-pink/15 text-white'
                      : 'border-ink-600 text-gray-300 hover:text-white'
                  "
                  @click="selectedText.animation = a.value"
                >
                  {{ a.label }}
                </button>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <label class="text-xs font-medium text-gray-400">Color</label>
              <input
                v-model="selectedText.color"
                type="color"
                class="h-8 w-12 rounded bg-ink-700"
              />
              <label class="ml-2 text-xs font-medium text-gray-400">Size</label>
              <input
                v-model.number="selectedText.scale"
                type="range"
                min="0.06"
                max="0.3"
                step="0.01"
                class="flex-1 accent-giphy-purple"
              />
            </div>
            <button
              type="button"
              class="w-full rounded-lg border border-ink-600 px-3 py-2 text-sm text-gray-300 transition hover:border-giphy-pink hover:text-white"
              @click="deleteSelected"
            >
              🗑 Delete this text
            </button>
          </template>
        </div>

        <!-- Stickers / Emoji tool -->
        <div v-else-if="activeTool === 'stickers'" class="space-y-3">
          <h2 class="font-bold text-white">Stickers</h2>
          <input
            v-model="emojiSearch"
            type="text"
            placeholder="Search categories…"
            class="input-field"
          />
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="t in emojiTabs"
              :key="t.label"
              type="button"
              class="rounded-full px-3 py-1 text-xs font-semibold transition"
              :class="
                activeEmojiTab === t.label && !emojiSearch
                  ? 'bg-giphy-purple text-white'
                  : 'bg-ink-700 text-gray-300 hover:text-white'
              "
              @click="selectEmojiTab(t.label)"
            >
              {{ t.label }}
            </button>
          </div>
          <div
            v-if="displayedEmojis.length"
            class="grid max-h-64 grid-cols-6 gap-1 overflow-y-auto pr-1"
          >
            <button
              v-for="(em, i) in displayedEmojis"
              :key="em + i"
              type="button"
              class="flex h-10 items-center justify-center rounded-lg text-2xl transition hover:bg-ink-700"
              @click="addEmoji(em)"
            >
              {{ em }}
            </button>
          </div>
          <p v-else class="text-sm text-gray-400">
            No stickers here yet — add some from another tab.
          </p>

          <div
            v-if="selectedEmoji"
            class="flex items-center gap-3 border-t border-ink-700 pt-3"
          >
            <label class="text-xs font-medium text-gray-400">Size</label>
            <input
              v-model.number="selectedEmoji.scale"
              type="range"
              min="0.08"
              max="0.6"
              step="0.01"
              class="flex-1 accent-giphy-purple"
            />
          </div>
        </div>

        <!-- Filter tool -->
        <div v-else-if="activeTool === 'filter'" class="space-y-4">
          <h2 class="font-bold text-white">Filters</h2>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="f in FILTER_CHOICES"
              :key="f.value"
              type="button"
              class="rounded-lg border px-3 py-2 text-sm font-semibold transition"
              :class="
                filter === f.value
                  ? 'border-giphy-blue bg-giphy-blue/15 text-white'
                  : 'border-ink-600 text-gray-300 hover:text-white'
              "
              @click="filter = f.value"
            >
              {{ f.label }}
            </button>
          </div>
        </div>

        <!-- Crop / resize tool -->
        <div v-else-if="activeTool === 'crop'" class="space-y-4">
          <h2 class="font-bold text-white">Crop &amp; Size</h2>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="a in ASPECT_CHOICES"
              :key="a.value"
              type="button"
              class="rounded-lg border px-3 py-2 text-sm font-semibold transition"
              :class="
                aspect === a.value
                  ? 'border-giphy-green bg-giphy-green/15 text-white'
                  : 'border-ink-600 text-gray-300 hover:text-white'
              "
              @click="aspect = a.value"
            >
              {{ a.label }}
            </button>
          </div>

          <div v-if="aspect === 'custom'" class="grid grid-cols-2 gap-3">
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-400">
                Width (px)
              </label>
              <input
                v-model.number="customW"
                type="number"
                min="32"
                max="1000"
                class="input-field"
              />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-400">
                Height (px)
              </label>
              <input
                v-model.number="customH"
                type="number"
                min="32"
                max="1000"
                class="input-field"
              />
            </div>
          </div>

          <div>
            <label class="mb-1 block text-xs font-medium text-gray-400">
              Image fit
            </label>
            <div class="grid grid-cols-2 gap-2">
              <button
                type="button"
                class="rounded-lg border px-3 py-2 text-sm font-semibold transition"
                :class="
                  fit === 'cover'
                    ? 'border-giphy-blue bg-giphy-blue/15 text-white'
                    : 'border-ink-600 text-gray-300 hover:text-white'
                "
                @click="fit = 'cover'"
              >
                Fill
              </button>
              <button
                type="button"
                class="rounded-lg border px-3 py-2 text-sm font-semibold transition"
                :class="
                  fit === 'contain'
                    ? 'border-giphy-blue bg-giphy-blue/15 text-white'
                    : 'border-ink-600 text-gray-300 hover:text-white'
                "
                @click="fit = 'contain'"
              >
                Fit
              </button>
            </div>
          </div>
          <p class="text-xs text-gray-500">
            Output: {{ output.width }} × {{ output.height }} px
          </p>
        </div>

        <!-- Trim tool -->
        <div v-else-if="activeTool === 'trim'" class="space-y-4">
          <h2 class="font-bold text-white">Trim</h2>
          <p v-if="!isAnimated" class="text-sm text-gray-400">
            This is a single still frame — nothing to trim.
          </p>
          <template v-else>
            <div
              v-if="thumbs.length"
              class="flex gap-0.5 overflow-hidden rounded-lg border border-ink-700"
            >
              <img
                v-for="(t, i) in thumbs"
                :key="i"
                :src="t"
                class="h-12 flex-1 object-cover"
                alt=""
              />
            </div>
            <div class="flex items-center justify-between text-xs text-gray-300">
              <span>{{ trimStartLabel }}</span>
              <span class="font-semibold text-white">{{ durationLabel }}</span>
              <span>{{ trimEndLabel }}</span>
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-400">
                Start frame ({{ sIdx + 1 }})
              </label>
              <input
                v-model.number="trimStart"
                type="range"
                min="0"
                :max="lastFrame"
                step="1"
                class="w-full accent-giphy-green"
              />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-400">
                End frame ({{ eIdx + 1 }})
              </label>
              <input
                v-model.number="trimEnd"
                type="range"
                min="0"
                :max="lastFrame"
                step="1"
                class="w-full accent-giphy-pink"
              />
            </div>
          </template>
        </div>

        <!-- Layers tool -->
        <div v-else class="space-y-3">
          <div class="flex items-center justify-between">
            <h2 class="font-bold text-white">Layers</h2>
            <span class="text-xs text-gray-500">{{ layers.length }} total</span>
          </div>
          <p v-if="!layers.length" class="text-sm text-gray-400">
            No layers yet — add text or a sticker.
          </p>
          <ul v-else class="space-y-1.5">
            <li
              v-for="l in [...layers].reverse()"
              :key="l.id"
              class="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition"
              :class="
                selectedId === l.id
                  ? 'border-giphy-purple bg-giphy-purple/10'
                  : 'border-ink-600'
              "
            >
              <button
                type="button"
                class="flex-1 truncate text-left text-gray-200"
                @click="bringToFront(l.id)"
              >
                <span class="mr-1">{{ l.type === 'text' ? '🅣' : '🙂' }}</span>
                {{ layerLabel(l) }}
              </button>
            </li>
          </ul>
          <div v-if="selectedLayer" class="flex gap-2 border-t border-ink-700 pt-3">
            <button
              type="button"
              class="flex-1 rounded-lg border border-ink-600 px-3 py-2 text-sm font-semibold text-gray-200 transition hover:border-giphy-blue hover:text-giphy-blue"
              @click="duplicateSelected"
            >
              ⧉ Duplicate
            </button>
            <button
              type="button"
              class="flex-1 rounded-lg border border-ink-600 px-3 py-2 text-sm font-semibold text-gray-200 transition hover:border-giphy-pink hover:text-giphy-pink"
              @click="deleteSelected"
            >
              🗑 Delete
            </button>
          </div>
          <button
            type="button"
            class="mt-2 w-full rounded-lg border border-ink-600 px-3 py-2 text-sm text-gray-300 transition hover:border-giphy-pink hover:text-white"
            @click="reset"
          >
            ↺ Start over
          </button>
        </div>
      </div>

      <!-- Action bar spans full width under the grid -->
      <div class="lg:col-span-2">
        <p
          v-if="error"
          class="mb-3 rounded-lg border border-giphy-pink/40 bg-giphy-pink/10 px-3 py-2 text-sm text-giphy-pink"
        >
          {{ error }}
        </p>
        <div class="flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            class="btn-primary flex-1 !py-3"
            :disabled="rendering"
            @click="continueToUpload"
          >
            {{ rendering ? 'Rendering…' : 'Continue to Upload →' }}
          </button>
          <button
            type="button"
            class="flex-1 rounded-lg border border-ink-600 px-4 py-3 font-semibold text-gray-200 transition hover:border-giphy-blue hover:text-giphy-blue disabled:opacity-50"
            :disabled="rendering"
            @click="download"
          >
            ⬇ Download
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.studio-card {
  @apply flex flex-col items-center justify-center rounded-2xl border border-ink-700 bg-ink-800 px-6 py-14 text-center transition hover:border-giphy-purple hover:bg-ink-700;
}
.studio-checkerboard {
  background-image:
    linear-gradient(45deg, #1a1a23 25%, transparent 25%),
    linear-gradient(-45deg, #1a1a23 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #1a1a23 75%),
    linear-gradient(-45deg, transparent 75%, #1a1a23 75%);
  background-size: 24px 24px;
  background-position: 0 0, 0 12px, 12px -12px, -12px 0;
}
</style>
