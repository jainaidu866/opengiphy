import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import LoginView from '@/views/LoginView.vue'

// Mock the auth store so we can control login() per test.
const { loginMock } = vi.hoisted(() => ({ loginMock: vi.fn() }))
vi.mock('@/stores/auth', () => ({
  useAuth: () => ({ login: loginMock }),
}))

const Blank = { template: '<div />' }

function makeRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: Blank },
      { path: '/login', name: 'login', component: Blank },
      { path: '/register', name: 'register', component: Blank },
    ],
  })
}

async function mountLogin() {
  const router = makeRouter()
  await router.push('/login')
  await router.isReady()
  const wrapper = mount(LoginView, { global: { plugins: [router] } })
  return { wrapper, router }
}

describe('LoginView', () => {
  beforeEach(() => {
    loginMock.mockReset()
  })

  it('renders email and password fields', async () => {
    const { wrapper } = await mountLogin()
    const email = wrapper.find('#email')
    const password = wrapper.find('#password')
    expect(email.exists()).toBe(true)
    expect(email.attributes('type')).toBe('email')
    expect(password.exists()).toBe(true)
    expect(password.attributes('type')).toBe('password')
  })

  it('shows an error message on failed login', async () => {
    loginMock.mockRejectedValueOnce(new Error('bad credentials'))
    const { wrapper } = await mountLogin()

    await wrapper.find('#email').setValue('user@example.com')
    await wrapper.find('#password').setValue('wrongpass')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(loginMock).toHaveBeenCalledWith('user@example.com', 'wrongpass')
    expect(wrapper.text()).toContain('Invalid email or password')
  })

  it('redirects to home on successful login', async () => {
    loginMock.mockResolvedValueOnce(undefined)
    const { wrapper, router } = await mountLogin()
    const push = vi.spyOn(router, 'push')

    await wrapper.find('#email').setValue('user@example.com')
    await wrapper.find('#password').setValue('correctpass')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(loginMock).toHaveBeenCalledWith('user@example.com', 'correctpass')
    expect(push).toHaveBeenCalledWith('/')
    expect(wrapper.text()).not.toContain('Invalid email or password')
  })
})
