import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import HomeView from '@/views/HomeView.vue'
import { fetchGifs, type Gif } from '@/api/client'

// Keep real token helpers (auth store depends on them); stub the list call.
vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>(
    '@/api/client',
  )
  return { ...actual, fetchGifs: vi.fn(), toggleLike: vi.fn() }
})

function makeGif(id: number, title: string, tags: string[] = []): Gif {
  return {
    id,
    user_id: 1,
    title,
    description: null,
    tags,
    file_path: `${id}.gif`,
    url: `/uploads/${id}.gif`,
    view_count: 0,
    like_count: 0,
    created_at: '2024-01-01T00:00:00Z',
    uploader_username: 'alice',
  }
}

const Blank = { template: '<div />' }

function makeRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: Blank },
      { path: '/login', name: 'login', component: Blank },
      { path: '/upload', name: 'upload', component: Blank },
      { path: '/gif/:id', name: 'gif-detail', component: Blank },
      { path: '/profile/:username', name: 'profile', component: Blank },
    ],
  })
}

async function mountHome() {
  const router = makeRouter()
  await router.push('/')
  await router.isReady()
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const wrapper = mount(HomeView, {
    global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
  })
  await flushPromises()
  await flushPromises()
  return { wrapper }
}

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms))

describe('HomeView', () => {
  beforeEach(() => {
    vi.mocked(fetchGifs).mockReset()
  })

  it('renders a GIF grid when data is available', async () => {
    vi.mocked(fetchGifs).mockResolvedValue([
      makeGif(1, 'First GIF'),
      makeGif(2, 'Second GIF'),
    ])
    const { wrapper } = await mountHome()

    expect(wrapper.findAll('img')).toHaveLength(2)
    expect(wrapper.text()).toContain('First GIF')
    expect(wrapper.text()).toContain('Second GIF')
  })

  it('shows the empty state when there are no GIFs', async () => {
    vi.mocked(fetchGifs).mockResolvedValue([])
    const { wrapper } = await mountHome()

    expect(wrapper.findAll('img')).toHaveLength(0)
    expect(wrapper.text()).toContain('No GIFs yet')
    expect(wrapper.text()).toContain('Upload a GIF')
  })

  it('requests the next page when the scroll sentinel intersects', async () => {
    // Capture the IntersectionObserver callback so we can trigger it manually.
    let trigger: (() => void) | undefined
    class CapturingObserver {
      constructor(cb: (entries: { isIntersecting: boolean }[]) => void) {
        trigger = () => cb([{ isIntersecting: true }])
      }
      observe() {}
      unobserve() {}
      disconnect() {}
      takeRecords() {
        return []
      }
    }
    vi.stubGlobal('IntersectionObserver', CapturingObserver)

    // First page returns a full page (PAGE_SIZE=20) so hasNextPage is true.
    const firstPage = Array.from({ length: 20 }, (_, i) => makeGif(i + 1, `Gif ${i + 1}`))
    vi.mocked(fetchGifs).mockImplementation(async (page?: number) =>
      page === 2 ? [makeGif(99, 'Page Two Gif')] : firstPage,
    )

    const { wrapper } = await mountHome()
    expect(wrapper.findAll('img')).toHaveLength(20)

    // Fire the sentinel; the second page should be requested and appended.
    trigger?.()
    await flushPromises()
    await flushPromises()

    expect(
      vi.mocked(fetchGifs).mock.calls.some((args: unknown[]) => args[0] === 2),
    ).toBe(true)
    expect(wrapper.text()).toContain('Page Two Gif')

    vi.unstubAllGlobals()
  })

  it('triggers a filtered query when the search input changes', async () => {
    vi.mocked(fetchGifs).mockImplementation(
      async (_page?: number, _limit?: number, search?: string) =>
        search === 'cats'
          ? [makeGif(3, 'Cat Party', ['cats'])]
          : [makeGif(1, 'First GIF'), makeGif(2, 'Second GIF')],
    )
    const { wrapper } = await mountHome()
    expect(wrapper.findAll('img')).toHaveLength(2)

    await wrapper.find('input[type="search"]').setValue('cats')
    // Search is debounced ~300ms before the query key updates.
    await wait(350)
    await flushPromises()
    await flushPromises()

    // The list call was eventually made with the search term.
    expect(
      vi.mocked(fetchGifs).mock.calls.some((args: unknown[]) => args[2] === 'cats'),
    ).toBe(true)
    expect(wrapper.findAll('img')).toHaveLength(1)
    expect(wrapper.text()).toContain('Cat Party')
  })
})
