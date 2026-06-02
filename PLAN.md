# OpenGIPHY — Feature Plan

Planning document for 5 new features. **No code yet** — this breaks each feature
into small, individually testable tasks with the files involved and a complexity
estimate.

Conventions assumed (from the existing codebase):
- Backend: FastAPI + SQLModel, routers under `backend/routers/`, dev schema via
  `create_all()` (no migrations), pytest in `backend/tests/` (in-memory SQLite).
- Frontend: Vue 3 `<script setup>`, typed API in `frontend/src/api/client.ts`,
  TanStack Query for fetching, Vitest tests in `frontend/src/tests/`.
- "Testable unit" = a task that can be verified by a pytest case, a Vitest case,
  or a clear manual check.

Complexity key: **small** ≈ <1 file of real logic · **medium** ≈ 2–4 files +
tests · **large** ≈ new model/route/view + tests.

---

## Suggested build order

1. **Share Button** (small, no backend) — quick win, isolated.
2. **Infinite Scroll** (medium, no backend) — frontend-only refactor of HomeView.
3. **Related GIFs** (medium) — one read-only endpoint + detail-page section.
4. **Categories** (large) — schema change touches upload + list + new views.
5. **Collections** (large) — new model + auth'd router + new page.

Features 1–3 are independent. Features 4 and 5 each add persistent data and are
best done last.

---

## Feature 1 — Infinite Scroll

**What it does:** Replaces the Prev/Next buttons on the Home page with automatic
loading of the next page of GIFs as the user scrolls to the bottom.

**Files to change**
- Backend: _none_ — `GET /gifs/` already supports `page`/`limit`. (Optional
  later: return a `has_more` flag instead of relying on the page-size heuristic.)
- Frontend:
  - `frontend/src/api/client.ts` — no signature change; confirm `fetchGifs` page
    param is wired for sequential pages.
  - `frontend/src/views/HomeView.vue` — swap `useQuery` for `useInfiniteQuery`;
    remove pagination UI; add a scroll sentinel.
  - `frontend/src/tests/HomeView.test.ts` — update pagination assertions.

**Tasks (in order)**
1. Replace HomeView's `useQuery` with `useInfiniteQuery`, with `getNextPageParam`
   returning the next page number while the last page length === PAGE_SIZE.
2. Flatten `data.pages` into a single `gifs` list used by the existing grid.
3. Remove the Prev/Next buttons and the `page`/`nextPage`/`prevPage` logic.
4. Add an `IntersectionObserver` sentinel `<div>` at the bottom of the grid that
   calls `fetchNextPage()` when visible.
5. Reset/refetch from page 1 when `search` or `sort` changes (already part of the
   query key).
6. Add an "end of results" indicator + a small loading spinner for `isFetchingNextPage`.
7. Update `HomeView.test.ts`: "renders first page", "empty state", and a test that
   triggering the sentinel requests page 2 (mock IntersectionObserver).

**Complexity:** medium

---

## Feature 2 — Categories

**What it does:** Lets users tag each upload with one of a fixed set of categories
and browse all GIFs in a category from a dedicated page.

Fixed categories: `funny, reactions, sports, animals, food, music, gaming, anime, memes`.

**Files to change**
- Backend:
  - `backend/models.py` — add nullable `category: Optional[str]` to `Gif`.
  - `backend/constants.py` (new) — the canonical `CATEGORIES` list.
  - `backend/routers/gifs.py` — accept `category` on upload (validate against list);
    add `category` filter to `GET /gifs/`; serialize `category` in `GifResponse`.
  - `backend/tests/test_gifs.py` — category validation + filtering tests.
- Frontend:
  - `frontend/src/api/client.ts` — add `category` to `Gif`; add `categories`
    constant; add `category` param to `fetchGifs`; send `category` in `uploadGif`.
  - `frontend/src/views/UploadView.vue` — category `<select>` (optional field).
  - `frontend/src/views/CategoryView.vue` (new) — grid filtered by `:name`.
  - `frontend/src/views/CategoriesView.vue` (new) — landing grid of category tiles.
  - `frontend/src/router/index.ts` — add `/categories` and `/category/:name`.
  - `frontend/src/App.vue` — "Categories" nav link.
  - `frontend/src/tests/` — `CategoryView.test.ts` (new).

**Tasks (in order)**
1. Add `CATEGORIES` constant in `backend/constants.py`.
2. Add `category` column to the `Gif` model.
3. Validate `category` on upload (400 if not in `CATEGORIES`; allow empty/None).
4. Add `category` query param to `GET /gifs/` and include it in serialization.
5. Backend tests: upload with valid/invalid category; list filtered by category.
6. Frontend: extend `Gif` type + add shared `categories` constant in `client.ts`.
7. Frontend: add `category` to `uploadGif` and a select in `UploadView`.
8. Build `CategoryView.vue` (reuses the grid; calls `fetchGifs(..., category)`).
9. Build `CategoriesView.vue` (static tiles linking to each `/category/:name`).
10. Wire both routes + add the nav link in `App.vue`.
11. Vitest: `CategoryView` renders the filtered grid and empty state.

**Complexity:** large

---

## Feature 3 — Related GIFs

**What it does:** Shows a row of related GIFs at the bottom of the detail page,
ranked by how many tags they share with the current GIF.

**Files to change**
- Backend:
  - `backend/routers/gifs.py` — new `GET /gifs/{id}/related?limit=` endpoint
    (public): find other GIFs whose tags overlap, rank by shared-tag count.
  - `backend/tests/test_gifs.py` — related-results + ordering + self-exclusion tests.
- Frontend:
  - `frontend/src/api/client.ts` — `fetchRelated(id, limit?)`.
  - `frontend/src/views/GifDetailView.vue` — "Related GIFs" section under the embed box.
  - `frontend/src/tests/GifDetailView.test.ts` — assert related section renders.

**Tasks (in order)**
1. Implement `GET /gifs/{id}/related`: load the GIF's tags, gather candidates that
   share ≥1 tag (OR over tags using the existing portable tag-text match),
   exclude the GIF itself.
2. Rank candidates by shared-tag count in Python; cap at `limit` (default 6);
   reuse `_serialize` so results include `like_count`/`url`.
3. Return an empty list cleanly when the GIF has no tags or no matches.
4. Backend tests: returns tag-sharing GIFs, excludes self, respects `limit`,
   orders by overlap, empty when no tags.
5. Frontend: add `fetchRelated` to `client.ts`.
6. Frontend: add a "Related GIFs" grid to the bottom of `GifDetailView` (own query,
   keyed by gif id; hidden when empty).
7. Vitest: mock `fetchRelated`, assert thumbnails render and link to `/gif/:id`.

**Complexity:** medium

---

## Feature 4 — Share Button

**What it does:** Adds a one-click button (on both grid cards and the detail page)
that copies the GIF's direct page link to the clipboard.

**Files to change**
- Backend: _none_.
- Frontend:
  - `frontend/src/composables/useClipboard.ts` (new) — small copy-with-feedback helper
    (extracted so GifDetailView's existing copy logic can reuse it too).
  - `frontend/src/views/HomeView.vue` — share button on each card.
  - `frontend/src/views/GifDetailView.vue` — share button near the title.
  - `frontend/src/tests/` — `useClipboard`/share assertions.

**Tasks (in order)**
1. Create `useClipboard()` composable: `copy(text)` writes to `navigator.clipboard`
   and exposes a transient `copied` flag.
2. Add a share button to the GifDetail header that copies
   `window.location.origin + /gif/:id` and shows "Link copied!".
3. (Optional refactor) Point the existing embed "Copy" button at `useClipboard`.
4. Add a share icon button on each HomeView card (stop click propagation so it
   doesn't trigger navigation).
5. Vitest: clicking share calls `clipboard.writeText` with the correct URL and
   flips the copied state.

**Complexity:** small

---

## Feature 5 — Collections (Saved GIFs)

**What it does:** Lets a logged-in user save/un-save GIFs to a personal collection
and view all saved GIFs at `/collections`.

Scope: one implicit collection per user (a "saved" set), mirroring the Likes design.

**Files to change**
- Backend:
  - `backend/models.py` — new `Collection` model (`user_id` + `gif_id` composite PK,
    `created_at`).
  - `backend/routers/collections.py` (new) — `POST /gifs/{id}/save` (auth, toggle),
    `GET /gifs/{id}/saved` (optional-auth status), `GET /collections` (auth, the
    current user's saved GIFs, paginated).
  - `backend/main.py` — register the collections router.
  - `backend/tests/test_collections.py` (new) — toggle/list/auth tests.
- Frontend:
  - `frontend/src/api/client.ts` — `toggleSave`, `fetchSavedStatus`, `fetchCollection`.
  - `frontend/src/views/GifDetailView.vue` + `frontend/src/views/HomeView.vue` —
    save button (optimistic, like the heart).
  - `frontend/src/views/CollectionsView.vue` (new) — grid of saved GIFs.
  - `frontend/src/router/index.ts` — `/collections` route with `requiresAuth`.
  - `frontend/src/App.vue` — "Collections" nav link (logged-in only).
  - `frontend/src/tests/` — `CollectionsView.test.ts` (new).

**Tasks (in order)**
1. Add the `Collection` model (composite PK on `user_id` + `gif_id`).
2. Implement `POST /gifs/{id}/save` toggle (auth; create/delete row; 404 if GIF
   missing; return `{saved}`).
3. Implement `GET /gifs/{id}/saved` (optional auth; `{saved}` for current viewer).
4. Implement `GET /collections` (auth; paginated saved GIFs via `_serialize`).
5. Register router in `main.py`.
6. Backend tests: save toggles on/off, list reflects saves, list/save require auth,
   save 404 on missing GIF.
7. Frontend: add the three API functions to `client.ts`.
8. Frontend: add a save (🔖) button to GifDetail with optimistic toggle + revert,
   redirecting guests to `/login` (same pattern as likes).
9. Frontend: add the same save button to HomeView cards.
10. Build `CollectionsView.vue` (grid + empty state) and wire the protected route.
11. Add the logged-in-only "Collections" nav link in `App.vue`.
12. Vitest: `CollectionsView` renders saved GIFs and the empty state; save button
    calls `toggleSave`.

**Complexity:** large

---

## Cross-cutting notes

- **Schema:** Features 2 and 5 change the DB. Dev uses `create_all()`, so a fresh
  start picks up new tables/columns automatically; existing local data may need a
  DB reset (no migrations yet — would be the point to add Alembic).
- **Per-viewer state:** `saved` (Feature 5) has the same list-endpoint limitation
  as `liked_by_me` — grid cards won't know the saved state until toggled unless the
  list endpoint is extended; acceptable for now, document it.
- **Each feature ends green:** every feature's last task should leave
  `pytest` (backend) and `npm run test` + `npm run build` (frontend) passing.
