import { ref } from 'vue'

// A tiny module-level store used to hand a freshly-created GIF from the Create
// studio over to the Upload form (so the user can title/tag it and publish).
// Module-scoped refs survive route navigation within the SPA session.

export interface DraftMeta {
  title?: string
  category?: string
  isSticker?: boolean
}

const draftFile = ref<File | null>(null)
const draftMeta = ref<DraftMeta>({})

export function useDraft() {
  function setDraft(file: File, meta: DraftMeta = {}) {
    draftFile.value = file
    draftMeta.value = meta
  }

  /** Consume the draft (returns it and clears the store). */
  function takeDraft(): { file: File | null; meta: DraftMeta } {
    const file = draftFile.value
    const meta = draftMeta.value
    draftFile.value = null
    draftMeta.value = {}
    return { file, meta }
  }

  return { draftFile, draftMeta, setDraft, takeDraft }
}
