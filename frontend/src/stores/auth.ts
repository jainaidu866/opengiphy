import { computed, ref } from 'vue'

import client, { clearToken, getToken, setToken } from '@/api/client'

export interface User {
  id: number
  username: string
  email: string
}

// Module-level singleton state — shared across every component that
// calls useAuth().
const token = ref<string | null>(getToken())
const user = ref<User | null>(null)
const ready = ref(false)

const isLoggedIn = computed(() => !!token.value)

async function fetchMe(): Promise<void> {
  if (!token.value) {
    user.value = null
    return
  }
  const { data } = await client.get<User>('/auth/me')
  user.value = data
}

async function login(email: string, password: string): Promise<void> {
  const { data } = await client.post<{ access_token: string }>('/auth/login', {
    email,
    password,
  })
  setToken(data.access_token)
  token.value = data.access_token
  await fetchMe()
}

async function register(
  email: string,
  username: string,
  password: string,
): Promise<void> {
  await client.post('/auth/register', { email, username, password })
  // Auto-login right after a successful registration.
  await login(email, password)
}

function logout(): void {
  clearToken()
  token.value = null
  user.value = null
}

// Called once on app start: if a token is present, restore the session.
async function init(): Promise<void> {
  if (token.value) {
    try {
      await fetchMe()
    } catch {
      // Invalid/expired token — the response interceptor already cleared it.
      logout()
    }
  }
  ready.value = true
}

export function useAuth() {
  return {
    user,
    token,
    ready,
    isLoggedIn,
    login,
    register,
    logout,
    fetchMe,
    init,
  }
}
