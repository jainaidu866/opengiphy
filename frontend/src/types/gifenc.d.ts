// Minimal type declarations for `gifenc` (no official types shipped).
declare module 'gifenc' {
  export interface WriteFrameOptions {
    palette?: number[][]
    delay?: number
    transparent?: boolean
    transparentIndex?: number
    dispose?: number
    repeat?: number
    first?: boolean
  }

  export interface Encoder {
    writeFrame(
      index: Uint8Array | Uint8ClampedArray,
      width: number,
      height: number,
      opts?: WriteFrameOptions,
    ): void
    finish(): void
    bytes(): Uint8Array
    bytesView(): Uint8Array
    reset(): void
  }

  export function GIFEncoder(opts?: { auto?: boolean; initialCapacity?: number }): Encoder

  export function quantize(
    rgba: Uint8Array | Uint8ClampedArray,
    maxColors: number,
    opts?: { format?: string; oneBitAlpha?: boolean | number; clearAlpha?: boolean; clearAlphaThreshold?: number; clearAlphaColor?: number },
  ): number[][]

  export function applyPalette(
    rgba: Uint8Array | Uint8ClampedArray,
    palette: number[][],
    format?: string,
  ): Uint8Array
}
