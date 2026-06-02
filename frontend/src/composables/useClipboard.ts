import { ref } from 'vue'

// Small clipboard helper with transient "copied" feedback.
// `copy(text)` writes to the clipboard and flips `copied` to true for 2s.
export function useClipboard(resetMs = 2000) {
  const copied = ref(false)
  let timer: ReturnType<typeof setTimeout> | undefined

  async function copy(text: string): Promise<boolean> {
    try {
      await navigator.clipboard.writeText(text)
      copied.value = true
      clearTimeout(timer)
      timer = setTimeout(() => (copied.value = false), resetMs)
      return true
    } catch {
      copied.value = false
      return false
    }
  }

  return { copied, copy }
}
