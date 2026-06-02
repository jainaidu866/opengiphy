import { VueQueryPlugin, QueryClient } from '@tanstack/vue-query'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import CategoryView from '@/views/CategoryView.vue'
import { fetchGifs, type Gif } from '@/api/client'

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>(
    '@/api/client',
  )
  return { ...actual, fetchGifs: vi.fn() }
})

function makeGif(id: number, title: string): Gif {
  return {
    id,
    user_id: 1,
    title,
    description: null,
    tags: [],
    category: 'animals',
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
      { path: '/upload', name: 'upload', component: Blank },
      { path: '/categories', name: 'categories', component: Blank },
      { path: '/category/:name', name: 'category', component: CategoryView },
      { path: '/gif/:id', name: 'gif-detail', component: Blank },
    ],
  })
}

async function mountCategory(name: string) {
  const router = makeRouter()
  await router.push(`/category/${name}`)
  await router.isReady()
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const wrapper = mount(CategoryView, {
    global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
  })
  await flushPromises()
  await flushPromises()
  return { wrapper }
}

describe('CategoryView', () => {
  beforeEach(() => {
    vi.mocked(fetchGifs).mockReset()
  })

  it('renders the filtered grid for a valid category', async () => {
    vi.mocked(fetchGifs).mockResolvedValue([
      makeGif(1, 'Puppy'),
      makeGif(2, 'Kitten'),
    ])
    const { wrapper } = await mountCategory('animals')

    expect(wrapper.text()).toContain('Animals GIFs')
    expect(wrapper.findAll('img')).toHaveLength(2)
    expect(wrapper.text()).toContain('Puppy')
    // fetchGifs was called with the category as the 5th argument.
    expect(
      vi.mocked(fetchGifs).mock.calls.some(
        (args: unknown[]) => args[4] === 'animals',
      ),
    ).toBe(true)
  })

  it('shows the empty state when the category has no GIFs', async () => {
    vi.mocked(fetchGifs).mockResolvedValue([])
    const { wrapper } = await mountCategory('food')

    expect(wrapper.findAll('img')).toHaveLength(0)
    expect(wrapper.text()).toContain('No GIFs in this category yet')
  })

  it('shows an error for an unknown category and does not fetch', async () => {
    const { wrapper } = await mountCategory('not-real')
    expect(wrapper.text()).toContain('Unknown category')
    expect(fetchGifs).not.toHaveBeenCalled()
  })
})
