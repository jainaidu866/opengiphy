import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import GifDetailView from '@/views/GifDetailView.vue'
import {
  fetchGif,
  fetchLikes,
  fetchRelated,
  fetchSavedStatus,
  toggleLike,
  toggleSave,
  type Gif,
  type LikeStatus,
  type ToggleLikeResult,
} from '@/api/client'
import { useAuth } from '@/stores/auth'

// Keep the real client module (default export + token helpers, used by the
// auth store) but stub the network functions GifDetailView calls.
vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>(
    '@/api/client',
  )
  return {
    ...actual,
    fetchGif: vi.fn(),
    fetchLikes: vi.fn(),
    fetchRelated: vi.fn(),
    fetchSavedStatus: vi.fn(),
    toggleLike: vi.fn(),
    toggleSave: vi.fn(),
    reportGif: vi.fn(),
  }
})

const GIF: Gif = {
  id: 5,
  user_id: 9,
  title: 'Dancing Cat',
  description: 'A cat that really moves',
  tags: ['funny', 'cat'],
  file_path: 'dancing.gif',
  url: '/uploads/dancing.gif',
  view_count: 42,
  like_count: 7,
  created_at: '2024-01-15T00:00:00Z',
  uploader_username: 'alice',
}

const Blank = { template: '<div />' }

function makeRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: Blank },
      { path: '/login', name: 'login', component: Blank },
      { path: '/gif/:id', name: 'gif-detail', component: Blank },
      { path: '/profile/:username', name: 'profile', component: Blank },
    ],
  })
}

async function mountDetail() {
  const router = makeRouter()
  await router.push('/gif/5')
  await router.isReady()
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const wrapper = mount(GifDetailView, {
    global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
  })
  // Resolve the gif + likes queries.
  await flushPromises()
  await flushPromises()
  return { wrapper }
}

describe('GifDetailView', () => {
  beforeEach(() => {
    vi.mocked(fetchGif).mockReset()
    vi.mocked(fetchLikes).mockReset()
    vi.mocked(fetchRelated).mockReset()
    vi.mocked(toggleLike).mockReset()
    vi.mocked(fetchGif).mockResolvedValue(GIF)
    vi.mocked(fetchLikes).mockResolvedValue({
      like_count: 7,
      liked_by_me: false,
    } satisfies LikeStatus)
    vi.mocked(fetchRelated).mockResolvedValue([])
    vi.mocked(fetchSavedStatus).mockResolvedValue({ saved: false })

    // Log in as a different user (so report controls render etc.).
    const auth = useAuth()
    auth.token.value = 'test-token'
    auth.user.value = { id: 1, username: 'bob', email: 'bob@example.com' }

    // Stub the clipboard for the copy test.
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
      configurable: true,
    })
  })

  it('renders GIF metadata correctly', async () => {
    const { wrapper } = await mountDetail()
    const text = wrapper.text()
    expect(text).toContain('Dancing Cat')
    expect(text).toContain('A cat that really moves')
    expect(text).toContain('@alice')
    expect(text).toContain('42')
    expect(text).toContain('#funny')
    expect(text).toContain('#cat')
    expect(text).toContain('7 likes')
  })

  it('toggles the like button correctly', async () => {
    vi.mocked(toggleLike).mockResolvedValue({
      liked: true,
      like_count: 8,
    } satisfies ToggleLikeResult)

    const { wrapper } = await mountDetail()
    const likeBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('♡') || b.text().includes('♥'))
    expect(likeBtn).toBeTruthy()
    expect(likeBtn!.text()).toContain('♡')
    expect(likeBtn!.text()).toContain('7')

    await likeBtn!.trigger('click')
    await flushPromises()

    expect(toggleLike).toHaveBeenCalledWith('5')
    expect(likeBtn!.text()).toContain('♥')
    expect(likeBtn!.text()).toContain('8')
    expect(wrapper.text()).toContain('8 likes')
  })

  it('copies the embed code when the copy button is clicked', async () => {
    const { wrapper } = await mountDetail()

    // Embed panel is collapsed by default — open it from the sidebar first.
    const embedBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Embed'))
    expect(embedBtn).toBeTruthy()
    await embedBtn!.trigger('click')
    await flushPromises()

    const copyBtn = wrapper
      .findAll('button')
      .find((b) => b.text().trim() === 'Copy')
    expect(copyBtn).toBeTruthy()

    await copyBtn!.trigger('click')
    await flushPromises()

    const writeText = navigator.clipboard.writeText as ReturnType<typeof vi.fn>
    expect(writeText).toHaveBeenCalledTimes(1)
    const copied = writeText.mock.calls[0][0] as string
    expect(copied).toContain('/uploads/dancing.gif')
    expect(copied).toContain('Dancing Cat')
    expect(copyBtn!.text()).toContain('Copied!')
  })

  it('renders the Related GIFs section with thumbnails linking to detail', async () => {
    vi.mocked(fetchRelated).mockResolvedValue([
      {
        id: 11,
        user_id: 9,
        title: 'Related One',
        description: null,
        tags: ['cat'],
        file_path: 'r1.gif',
        url: '/uploads/r1.gif',
        view_count: 0,
        like_count: 0,
        created_at: '2024-02-01T00:00:00Z',
        uploader_username: 'alice',
      },
    ])

    const { wrapper } = await mountDetail()
    expect(fetchRelated).toHaveBeenCalledWith('5')
    expect(wrapper.text()).toContain('Related GIFs')
    expect(wrapper.text()).toContain('Related One')
    const link = wrapper
      .findAll('a')
      .find((a) => a.attributes('href') === '/gif/11')
    expect(link).toBeTruthy()
  })

  it('saves the GIF when the save button is clicked', async () => {
    vi.mocked(toggleSave).mockResolvedValue({ saved: true })

    const { wrapper } = await mountDetail()
    const saveBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Save'))
    expect(saveBtn).toBeTruthy()
    expect(saveBtn!.text()).toContain('Save')

    await saveBtn!.trigger('click')
    await flushPromises()

    expect(toggleSave).toHaveBeenCalledWith('5')
    expect(saveBtn!.text()).toContain('Saved')
  })
})
