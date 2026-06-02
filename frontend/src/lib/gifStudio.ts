// Client-side GIF studio engine: decode a source GIF (or image) into full
// frames, then composite a stack of layers (animated captions + emoji/stickers)
// on top — with optional crop/resize, filters and trimming — and re-encode a
// brand-new GIF. Used by CreateView so the downloaded/uploaded file actually
// contains everything the user added, just like Giphy's Create studio.

import { parseGIF, decompressFrames } from 'gifuct-js'
import { GIFEncoder, quantize, applyPalette } from 'gifenc'

export interface StudioFrame {
  /** Full-source-size composited RGBA pixels for this frame. */
  imageData: ImageData
  /** Frame duration in milliseconds. */
  delay: number
}

export interface DecodedGif {
  width: number
  height: number
  frames: StudioFrame[]
}

export type CaptionAnimation =
  | 'none'
  | 'bounce'
  | 'shake'
  | 'rainbow'
  | 'wave'
  | 'pulse'

export type GifFilter =
  | 'none'
  | 'grayscale'
  | 'sepia'
  | 'invert'
  | 'saturate'
  | 'contrast'

export type FitMode = 'cover' | 'contain'

// Layers ---------------------------------------------------------------------
// Positions/sizes are stored as fractions of the output dimensions so they stay
// stable across crop/resize.

export interface BaseLayerProps {
  id: string
  /** Center X as a fraction of output width (0..1). */
  x: number
  /** Center Y as a fraction of output height (0..1). */
  y: number
}

export interface TextLayer extends BaseLayerProps {
  type: 'text'
  text: string
  fontFamily: string
  /** Font size as a fraction of output height. */
  scale: number
  color: string
  animation: CaptionAnimation
}

export interface EmojiLayer extends BaseLayerProps {
  type: 'emoji'
  emoji: string
  /** Glyph size as a fraction of min(outW, outH). */
  scale: number
}

export type Layer = TextLayer | EmojiLayer

export interface OutputConfig {
  width: number
  height: number
  fit: FitMode
}

export interface RenderState {
  filter: GifFilter
  layers: Layer[]
  /** Layer id drawn with a selection box (preview only). */
  selectedId?: string | null
}

// Choice lists shared with the UI -------------------------------------------

export const FONT_CHOICES = [
  { label: 'Impact (meme)', value: '"Anton", "Impact", sans-serif' },
  { label: 'Poppins', value: '"Poppins", sans-serif' },
  { label: 'Comic', value: '"Comic Sans MS", "Comic Neue", cursive' },
  { label: 'Mono', value: '"Courier New", monospace' },
  { label: 'Serif', value: 'Georgia, serif' },
]

export const ANIMATION_CHOICES: { label: string; value: CaptionAnimation }[] = [
  { label: 'Static', value: 'none' },
  { label: 'Bounce', value: 'bounce' },
  { label: 'Shake', value: 'shake' },
  { label: 'Rainbow', value: 'rainbow' },
  { label: 'Wave', value: 'wave' },
  { label: 'Pulse', value: 'pulse' },
]

export const FILTER_CHOICES: { label: string; value: GifFilter }[] = [
  { label: 'None', value: 'none' },
  { label: 'B&W', value: 'grayscale' },
  { label: 'Sepia', value: 'sepia' },
  { label: 'Invert', value: 'invert' },
  { label: 'Vivid', value: 'saturate' },
  { label: 'Punch', value: 'contrast' },
]

export type AspectKey = 'original' | 'landscape' | 'portrait' | 'custom'
export const ASPECT_CHOICES: { label: string; value: AspectKey }[] = [
  { label: 'Original', value: 'original' },
  { label: 'Landscape', value: 'landscape' },
  { label: 'Portrait', value: 'portrait' },
  { label: 'Custom', value: 'custom' },
]

// Emoji "sticker" picker — categorized so the UI can show tabs.
export const EMOJI_CATEGORIES: { label: string; emojis: string[] }[] = [
  {
    label: 'Trending',
    emojis: ['🔥', '💯', '😂', '✨', '👀', '🎉', '❤️', '😎', '🤯', '🙌', '💀', '👑', '⚡', '🌈', '🎶', '💪'],
  },
  {
    label: 'Smileys',
    emojis: ['😀', '😁', '😂', '🤣', '😊', '😍', '😘', '😜', '🤪', '😎', '🥳', '😭', '😡', '🤔', '😴', '🤩', '🥰', '😏', '😱', '🤗'],
  },
  {
    label: 'Hearts',
    emojis: ['❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '💖', '💕', '💗', '💓', '💞', '💘', '❣️', '💔'],
  },
  {
    label: 'Animals',
    emojis: ['🐶', '🐱', '🦊', '🐼', '🐨', '🦁', '🐯', '🐸', '🐵', '🐷', '🐰', '🐻', '🐧', '🦄', '🐝', '🦋'],
  },
  {
    label: 'Food',
    emojis: ['🍕', '🍔', '🌮', '🍟', '🍩', '🍪', '🎂', '🍦', '🍓', '🍑', '🥑', '☕', '🍻', '🍷', '🍿', '🍫'],
  },
  {
    label: 'Party',
    emojis: ['🎉', '🎊', '🥳', '🎈', '🎁', '🎆', '🎇', '✨', '🪩', '🍾', '🎂', '👑', '🏆', '🌟', '💫', '🎵'],
  },
  {
    label: 'Symbols',
    emojis: ['⭐', '🌟', '💥', '💢', '💦', '💨', '🕒', '✅', '❌', '❓', '❗', '➡️', '⬆️', '🔝', '♻️', '🆒'],
  },
]

// ---------------------------------------------------------------------------

function newCanvas(w: number, h: number): HTMLCanvasElement {
  const c = document.createElement('canvas')
  c.width = w
  c.height = h
  return c
}

export function randomId(): string {
  return Math.random().toString(36).slice(2, 9)
}

/** Decode a GIF ArrayBuffer into fully-composited frames (handles disposal). */
export function decodeGif(buffer: ArrayBuffer): DecodedGif {
  const parsed = parseGIF(buffer)
  const raw = decompressFrames(parsed, true)
  const width = parsed.lsd.width
  const height = parsed.lsd.height

  const main = newCanvas(width, height)
  const mctx = main.getContext('2d')!
  const patchCanvas = newCanvas(width, height)
  const pctx = patchCanvas.getContext('2d')!

  const frames: StudioFrame[] = []
  for (const f of raw) {
    const { dims, disposalType } = f
    let snapshot: ImageData | null = null
    if (disposalType === 3) {
      snapshot = mctx.getImageData(0, 0, width, height)
    }

    patchCanvas.width = dims.width
    patchCanvas.height = dims.height
    const patch = new ImageData(
      new Uint8ClampedArray(f.patch),
      dims.width,
      dims.height,
    )
    pctx.putImageData(patch, 0, 0)
    mctx.drawImage(patchCanvas, dims.left, dims.top)

    frames.push({
      imageData: mctx.getImageData(0, 0, width, height),
      delay: f.delay && f.delay > 0 ? f.delay : 100,
    })

    if (disposalType === 2) {
      mctx.clearRect(dims.left, dims.top, dims.width, dims.height)
    } else if (disposalType === 3 && snapshot) {
      mctx.putImageData(snapshot, 0, 0)
    }
  }

  return { width, height, frames }
}

/** Build a single-frame "GIF" from a static image element. */
export function frameFromImage(img: HTMLImageElement): DecodedGif {
  const maxW = 600
  const scale = img.naturalWidth > maxW ? maxW / img.naturalWidth : 1
  const width = Math.max(1, Math.round(img.naturalWidth * scale))
  const height = Math.max(1, Math.round(img.naturalHeight * scale))
  const c = newCanvas(width, height)
  const ctx = c.getContext('2d')!
  ctx.drawImage(img, 0, 0, width, height)
  return {
    width,
    height,
    frames: [{ imageData: ctx.getImageData(0, 0, width, height), delay: 1000 }],
  }
}

function filterToCss(filter: GifFilter): string {
  switch (filter) {
    case 'grayscale':
      return 'grayscale(1)'
    case 'sepia':
      return 'sepia(0.85)'
    case 'invert':
      return 'invert(1)'
    case 'saturate':
      return 'saturate(2.2)'
    case 'contrast':
      return 'contrast(1.6) saturate(1.2)'
    default:
      return 'none'
  }
}

// Reusable scratch canvas for drawing the (source-sized) base frame.
let _src: HTMLCanvasElement | null = null

/** Where the base frame is drawn inside the output canvas (cover/contain). */
function baseRect(
  srcW: number,
  srcH: number,
  out: OutputConfig,
): { dx: number; dy: number; dw: number; dh: number } {
  const scale =
    out.fit === 'cover'
      ? Math.max(out.width / srcW, out.height / srcH)
      : Math.min(out.width / srcW, out.height / srcH)
  const dw = srcW * scale
  const dh = srcH * scale
  return {
    dx: (out.width - dw) / 2,
    dy: (out.height - dh) / 2,
    dw,
    dh,
  }
}

/**
 * Render one composited frame (base + filter + layers) onto `ctx`, which must
 * be sized to `out`. `phase` is 0..1 around the whole loop and drives layer
 * animations so the live preview and the baked output match.
 */
export function renderComposite(
  ctx: CanvasRenderingContext2D,
  base: ImageData,
  out: OutputConfig,
  state: RenderState,
  phase: number,
  forPreview = false,
): void {
  const srcW = base.width
  const srcH = base.height

  if (!_src || _src.width !== srcW || _src.height !== srcH) {
    _src = newCanvas(srcW, srcH)
  }
  const sctx = _src.getContext('2d')!
  sctx.putImageData(base, 0, 0)

  ctx.clearRect(0, 0, out.width, out.height)
  // Backdrop (matters for 'contain' letterboxing).
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, out.width, out.height)

  const { dx, dy, dw, dh } = baseRect(srcW, srcH, out)
  ctx.save()
  ctx.filter = filterToCss(state.filter)
  ctx.drawImage(_src, dx, dy, dw, dh)
  ctx.restore()

  for (const layer of state.layers) {
    drawLayer(ctx, layer, out, phase)
    if (forPreview && layer.id === state.selectedId) {
      drawSelection(ctx, layer, out)
    }
  }
}

function drawLayer(
  ctx: CanvasRenderingContext2D,
  layer: Layer,
  out: OutputConfig,
  phase: number,
): void {
  if (layer.type === 'text') drawText(ctx, layer, out, phase)
  else drawEmoji(ctx, layer, out, phase)
}

function drawText(
  ctx: CanvasRenderingContext2D,
  layer: TextLayer,
  out: OutputConfig,
  phase: number,
): void {
  const text = layer.text.trim()
  if (!text) return

  const fontSize = Math.max(10, Math.round(out.height * layer.scale))
  ctx.save()
  ctx.font = `bold ${fontSize}px ${layer.fontFamily}`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.lineJoin = 'round'
  ctx.lineWidth = Math.max(2, fontSize * 0.12)

  const t = phase * Math.PI * 2
  const cx = layer.x * out.width
  const cy = layer.y * out.height

  let dy = 0
  let dx = 0
  if (layer.animation === 'bounce') dy = Math.sin(t) * (out.height * 0.04)
  if (layer.animation === 'shake') dx = Math.sin(t * 3) * (out.width * 0.02)
  ctx.globalAlpha =
    layer.animation === 'pulse' ? 0.55 + 0.45 * Math.abs(Math.sin(t)) : 1

  if (layer.animation === 'wave') {
    const chars = [...text]
    const widths = chars.map((c) => ctx.measureText(c).width)
    const total = widths.reduce((a, b) => a + b, 0)
    let x = cx - total / 2
    ctx.textAlign = 'left'
    chars.forEach((ch, i) => {
      const yy = cy + Math.sin(t + i * 0.6) * (out.height * 0.03)
      ctx.strokeStyle = '#000'
      ctx.fillStyle = layer.color
      ctx.strokeText(ch, x, yy)
      ctx.fillText(ch, x, yy)
      x += widths[i]
    })
  } else {
    ctx.fillStyle =
      layer.animation === 'rainbow'
        ? `hsl(${Math.round((phase * 360) % 360)}, 95%, 60%)`
        : layer.color
    ctx.strokeStyle = '#000'
    ctx.strokeText(text, cx + dx, cy + dy)
    ctx.fillText(text, cx + dx, cy + dy)
  }
  ctx.restore()
}

function drawEmoji(
  ctx: CanvasRenderingContext2D,
  layer: EmojiLayer,
  out: OutputConfig,
  phase: number,
): void {
  const size = Math.max(12, Math.round(Math.min(out.width, out.height) * layer.scale))
  ctx.save()
  ctx.font = `${size}px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  // A gentle idle wiggle so stickers feel alive on multi-frame GIFs.
  const t = phase * Math.PI * 2
  const dy = Math.sin(t) * (size * 0.04)
  ctx.fillText(layer.emoji, layer.x * out.width, layer.y * out.height + dy)
  ctx.restore()
}

function drawSelection(
  ctx: CanvasRenderingContext2D,
  layer: Layer,
  out: OutputConfig,
): void {
  const b = layerBounds(ctx, layer, out)
  ctx.save()
  ctx.strokeStyle = '#9933ff'
  ctx.lineWidth = Math.max(1.5, out.width * 0.004)
  ctx.setLineDash([out.width * 0.02, out.width * 0.015])
  ctx.strokeRect(b.x, b.y, b.w, b.h)
  ctx.restore()
}

/** Bounding box (output-pixel space) for hit-testing / selection. */
export function layerBounds(
  measureCtx: CanvasRenderingContext2D,
  layer: Layer,
  out: OutputConfig,
): { x: number; y: number; w: number; h: number } {
  const cx = layer.x * out.width
  const cy = layer.y * out.height
  if (layer.type === 'emoji') {
    const size = Math.max(12, Math.round(Math.min(out.width, out.height) * layer.scale))
    return { x: cx - size / 2, y: cy - size / 2, w: size, h: size }
  }
  const fontSize = Math.max(10, Math.round(out.height * layer.scale))
  measureCtx.save()
  measureCtx.font = `bold ${fontSize}px ${layer.fontFamily}`
  const w = Math.max(fontSize, measureCtx.measureText(layer.text || ' ').width)
  measureCtx.restore()
  const pad = fontSize * 0.3
  return {
    x: cx - w / 2 - pad,
    y: cy - fontSize / 2 - pad,
    w: w + pad * 2,
    h: fontSize + pad * 2,
  }
}

/** Topmost layer under a point (output-pixel space), or null. */
export function hitTest(
  measureCtx: CanvasRenderingContext2D,
  layers: Layer[],
  out: OutputConfig,
  px: number,
  py: number,
): Layer | null {
  for (let i = layers.length - 1; i >= 0; i--) {
    const b = layerBounds(measureCtx, layers[i], out)
    if (px >= b.x && px <= b.x + b.w && py >= b.y && py <= b.y + b.h) {
      return layers[i]
    }
  }
  return null
}

/**
 * Bake the trimmed frame range with all layers/filter/crop into a new GIF.
 * `start`/`end` are inclusive frame indices into `decoded.frames`.
 */
export function encodeStudioGif(
  decoded: DecodedGif,
  out: OutputConfig,
  state: RenderState,
  start: number,
  end: number,
): Uint8Array {
  const canvas = newCanvas(out.width, out.height)
  const octx = canvas.getContext('2d')!

  const s = Math.max(0, Math.min(start, decoded.frames.length - 1))
  const e = Math.max(s, Math.min(end, decoded.frames.length - 1))
  const count = e - s + 1

  const enc = GIFEncoder()
  for (let i = s; i <= e; i++) {
    const phase = count > 1 ? (i - s) / count : 0
    renderComposite(octx, decoded.frames[i].imageData, out, state, phase, false)
    const { data } = octx.getImageData(0, 0, out.width, out.height)
    const palette = quantize(data, 256)
    const index = applyPalette(data, palette)
    enc.writeFrame(index, out.width, out.height, {
      palette,
      delay: decoded.frames[i].delay,
    })
  }
  enc.finish()
  return enc.bytes()
}

/** Convenience: produce a downloadable/uploadable File from encoded bytes. */
export function bytesToGifFile(bytes: Uint8Array, name = 'opengiphy-creation.gif'): File {
  const ab = bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength,
  ) as ArrayBuffer
  const blob = new Blob([ab], { type: 'image/gif' })
  return new File([blob], name, { type: 'image/gif' })
}
