import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import CollectionsView from '@/views/CollectionsView.vue'
import { fetchCollection, type Gif } from '@/api/client'

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>(
    '@/api/client',
  )
  return { ...actual, fetchCollection: vi.fn() }
})

function makeGif(id: number, title: string): Gif {
  return {
    id,
    user_id: 1,
    title,
    description: null,
    tags: [],
    category: null,
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
      { path: '/collections', name: 'collections', component: CollectionsView },
      { path: '/gif/:id', name: 'gif-detail', component: Blank },
    ],
  })
}

async function mountCollections() {
  const router = makeRouter()
  await router.push('/collections')
  await router.isReady()
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const wrapper = mount(CollectionsView, {
    global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
  })
  await flushPromises()
  await flushPromises()
  return { wrapper }
}

describe('CollectionsView', () => {
  beforeEach(() => {
    vi.mocked(fetchCollection).mockReset()
  })

  it('renders the saved GIFs', async () => {
    vi.mocked(fetchCollection).mockResolvedValue([
      makeGif(1, 'Saved One'),
      makeGif(2, 'Saved Two'),
    ])
    const { wrapper } = await mountCollections()

    expect(wrapper.findAll('img')).toHaveLength(2)
    expect(wrapper.text()).toContain('Saved One')
    expect(wrapper.text()).toContain('Saved Two')
  })

  it('shows the empty state when nothing is saved', async () => {
    vi.mocked(fetchCollection).mockResolvedValue([])
    const { wrapper } = await mountCollections()

    expect(wrapper.findAll('img')).toHaveLength(0)
    expect(wrapper.text()).toContain('No saved GIFs yet')
  })
})
