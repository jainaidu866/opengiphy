// Vitest global setup.
//
// Node 22+ exposes an experimental global `localStorage` that throws unless
// run with `--localstorage-file`, and it shadows jsdom's implementation.
// Replace it with a simple in-memory store so the auth module can read/write
// tokens during tests.
class LocalStorageMock implements Storage {
  private store: Record<string, string> = {}

  get length(): number {
    return Object.keys(this.store).length
  }
  clear(): void {
    this.store = {}
  }
  getItem(key: string): string | null {
    return Object.prototype.hasOwnProperty.call(this.store, key)
      ? this.store[key]
      : null
  }
  key(index: number): string | null {
    return Object.keys(this.store)[index] ?? null
  }
  removeItem(key: string): void {
    delete this.store[key]
  }
  setItem(key: string, value: string): void {
    this.store[key] = String(value)
  }
}

Object.defineProperty(globalThis, 'localStorage', {
  value: new LocalStorageMock(),
  configurable: true,
  writable: true,
})

// jsdom has no IntersectionObserver; provide a no-op default so components
// that observe a scroll sentinel (e.g. HomeView infinite scroll) can mount.
// Individual tests may override this to capture/trigger the callback.
class IntersectionObserverStub {
  constructor(_cb: IntersectionObserverCallback) {}
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
  takeRecords(): [] {
    return []
  }
}

Object.defineProperty(globalThis, 'IntersectionObserver', {
  value: IntersectionObserverStub,
  configurable: true,
  writable: true,
})
