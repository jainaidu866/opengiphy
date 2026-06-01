import axios from 'axios'

const TOKEN_KEY = 'opengiphy_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

// Axios instance pointing at the backend. In production the FastAPI app
// serves this built frontend on the same origin, so an empty baseURL sends
// requests straight to the backend routes (/auth, /gifs, /profiles, ...).
const client = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: attach the bearer token (if any) to every request.
client.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: on 401, drop the token and bounce to /login.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearToken()
      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    }
    return Promise.reject(error)
  },
)

export default client

// ---------------------------------------------------------------------------
// Typed GIF API
// ---------------------------------------------------------------------------

export interface Gif {
  id: number
  user_id: number
  title: string
  description: string | null
  tags: string[]
  file_path: string
  url: string
  view_count: number
  like_count: number
  created_at: string
  uploader_username: string
}

export type SortMode = 'new' | 'trending'

export async function fetchGifs(
  page = 1,
  limit = 20,
  search?: string,
  sort: SortMode = 'new',
): Promise<Gif[]> {
  const params: Record<string, string | number> = { page, limit, sort }
  if (search && search.trim()) {
    params.search = search.trim()
  }
  const { data } = await client.get<Gif[]>('/gifs/', { params })
  return data
}

export async function fetchGif(id: number | string): Promise<Gif> {
  const { data } = await client.get<Gif>(`/gifs/${id}`)
  return data
}

export async function uploadGif(
  formData: FormData,
  onProgress?: (percent: number) => void,
): Promise<Gif> {
  const { data } = await client.post<Gif>('/gifs/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded * 100) / event.total))
      }
    },
  })
  return data
}

// ---------------------------------------------------------------------------
// Likes
// ---------------------------------------------------------------------------

export interface LikeStatus {
  like_count: number
  liked_by_me: boolean
}

export interface ToggleLikeResult {
  liked: boolean
  like_count: number
}

export async function fetchLikes(id: number | string): Promise<LikeStatus> {
  const { data } = await client.get<LikeStatus>(`/gifs/${id}/likes`)
  return data
}

export async function toggleLike(
  id: number | string,
): Promise<ToggleLikeResult> {
  const { data } = await client.post<ToggleLikeResult>(`/gifs/${id}/like`)
  return data
}

// ---------------------------------------------------------------------------
// Profiles
// ---------------------------------------------------------------------------

export interface Profile {
  username: string
  created_at: string
  gifs: Gif[]
}

export async function fetchProfile(
  username: string,
  page = 1,
  limit = 20,
): Promise<Profile> {
  const { data } = await client.get<Profile>(`/profiles/${username}`, {
    params: { page, limit },
  })
  return data
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

export async function reportGif(
  id: number | string,
  reason: string,
): Promise<{ message: string }> {
  const { data } = await client.post<{ message: string }>(
    `/gifs/${id}/report`,
    { reason },
  )
  return data
}
