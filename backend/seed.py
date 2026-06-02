"""Seed the database with ~100+ REAL demo GIFs across every category.

Fetches genuine animated GIFs from Tenor's public API (per category search),
downloads the .gif files into the upload directory, and inserts matching Gif
rows owned by a few demo users. Useful for manually testing search,
categories, trending, related GIFs, likes, collections, etc.

Run from the backend/ directory:

    python seed.py            # seed once (skips if demo data already present)
    SEED_FORCE=1 python seed.py   # add another batch even if data exists

Network: uses Tenor's public demo API key by default. Override with TENOR_KEY.
"""

import json
import os
import random
import time
import urllib.parse
import urllib.request
import uuid

from sqlmodel import Session, select

from auth import hash_password
from database import create_db_and_tables, engine
from models import Gif, Like, User

# Where downloaded .gif files are written. Matches routers.gifs.UPLOAD_DIR
# default so the static mount at /uploads serves them.
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

# Tenor's long-standing public demo key. Override with your own via TENOR_KEY.
TENOR_KEY = os.getenv("TENOR_KEY", "LIVDSRZULELA")
TENOR_SEARCH = "https://g.tenor.com/v1/search"
USER_AGENT = "Mozilla/5.0 (OpenGIPHY-seed)"

# Per-category search queries (to pull varied, on-theme real GIFs) plus a pool
# of tags so the seeded data stays searchable. Categories mirror
# backend/constants.py CATEGORIES.
CATEGORY_DATA = {
    "funny": {
        "queries": ["funny", "comedy", "laughing", "lol"],
        "tags": ["funny", "lol", "haha", "comedy", "laugh"],
    },
    "reactions": {
        "queries": ["reaction", "shocked", "omg wow", "surprised"],
        "tags": ["reaction", "wow", "shocked", "omg", "mood"],
    },
    "sports": {
        "queries": ["sports", "soccer goal", "basketball dunk", "touchdown"],
        "tags": ["sports", "goal", "win", "game", "highlight"],
    },
    "animals": {
        "queries": ["cute puppy", "kitten", "happy dog", "funny cat"],
        "tags": ["animals", "cat", "dog", "cute", "pet"],
    },
    "food": {
        "queries": ["pizza", "burger", "coffee", "dessert"],
        "tags": ["food", "yummy", "pizza", "snack", "delicious"],
    },
    "music": {
        "queries": ["dancing", "music", "guitar solo", "dj"],
        "tags": ["music", "dance", "beat", "song", "vibes"],
    },
    "gaming": {
        "queries": ["gaming", "video game", "gamer win", "boss fight"],
        "tags": ["gaming", "gamer", "win", "playstation", "rage"],
    },
    "anime": {
        "queries": ["anime", "anime fight", "kawaii", "anime happy"],
        "tags": ["anime", "manga", "kawaii", "otaku", "weeb"],
    },
    "memes": {
        "queries": ["meme", "dank meme", "this is fine", "stonks"],
        "tags": ["memes", "dank", "viral", "relatable", "internet"],
    },
}

DEMO_USERS = [
    {"email": "demo@opengiphy.dev", "username": "demo", "password": "demo1234"},
    {"email": "gifmaster@opengiphy.dev", "username": "gifmaster", "password": "demo1234"},
    {"email": "memequeen@opengiphy.dev", "username": "memequeen", "password": "demo1234"},
]

PER_CATEGORY = 12  # 9 categories * 12 = up to 108 GIFs


def _http_get(url: str) -> bytes:
    """GET a URL with a browser-like User-Agent (Tenor/CDN reject the default)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def _title_from(description: str, fallback: str) -> str:
    """Build a tidy title from Tenor's content_description."""
    desc = (description or "").strip()
    if not desc:
        return fallback
    # Capitalize first letter, cap length so it fits nicely in the UI.
    title = desc[0].upper() + desc[1:]
    return title[:70].rstrip()


def tenor_search(query: str, limit: int, pos: str | None = None) -> tuple[list[dict], str | None]:
    """Search Tenor for GIFs. Returns (results, next_pos)."""
    params = {
        "q": query,
        "key": TENOR_KEY,
        "limit": str(limit),
        "media_filter": "minimal",
        "contentfilter": "high",
    }
    if pos:
        params["pos"] = pos
    url = f"{TENOR_SEARCH}?{urllib.parse.urlencode(params)}"
    data = json.loads(_http_get(url))
    return data.get("results", []), data.get("next") or None


def collect_category_gifs(category: str, queries: list[str], want: int) -> list[dict]:
    """Gather up to `want` unique real GIFs for a category across its queries.

    Returns a list of {url, description} dicts (Tenor gif media + caption).
    """
    found: dict[str, dict] = {}
    for query in queries:
        if len(found) >= want:
            break
        pos: str | None = None
        # Paginate this query until we have enough or run dry.
        for _ in range(4):  # safety cap on pages per query
            if len(found) >= want:
                break
            try:
                results, pos = tenor_search(query, limit=20, pos=pos)
            except Exception as exc:  # noqa: BLE001 - network is best-effort
                print(f"  ! search '{query}' failed: {exc}")
                break
            if not results:
                break
            for item in results:
                media = item.get("media") or []
                if not media:
                    continue
                gif = media[0].get("gif") or {}
                gif_url = gif.get("url")
                if not gif_url or item["id"] in found:
                    continue
                found[item["id"]] = {
                    "url": gif_url,
                    "description": item.get("content_description", ""),
                }
                if len(found) >= want:
                    break
            if not pos:
                break
    return list(found.values())


def ensure_users(session: Session) -> list[User]:
    users = []
    for data in DEMO_USERS:
        existing = session.exec(
            select(User).where(User.username == data["username"])
        ).first()
        if existing is None:
            existing = User(
                email=data["email"],
                username=data["username"],
                hashed_password=hash_password(data["password"]),
            )
            session.add(existing)
            session.commit()
            session.refresh(existing)
        users.append(existing)
    return users


def main() -> None:
    create_db_and_tables()
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    force = os.getenv("SEED_FORCE") == "1"

    with Session(engine) as session:
        users = ensure_users(session)
        demo = users[0]

        already = session.exec(
            select(Gif).where(Gif.user_id == demo.id)
        ).first()
        if already is not None and not force:
            total = len(session.exec(select(Gif)).all())
            print(
                f"Demo data already present ({total} GIFs total). "
                "Set SEED_FORCE=1 to add another batch. Skipping."
            )
            return

        created = []
        for category, data in CATEGORY_DATA.items():
            print(f"Fetching real GIFs for '{category}' ...")
            candidates = collect_category_gifs(
                category, data["queries"], PER_CATEGORY
            )
            saved = 0
            for cand in candidates:
                # Download the real .gif into the upload dir.
                try:
                    blob = _http_get(cand["url"])
                except Exception as exc:  # noqa: BLE001
                    print(f"  ! download failed: {exc}")
                    continue
                if not blob.startswith(b"GIF8"):
                    print("  ! skipped non-GIF payload")
                    continue

                filename = f"{uuid.uuid4().hex}.gif"
                disk_path = os.path.join(UPLOAD_DIR, filename)
                with open(disk_path, "wb") as fh:
                    fh.write(blob)

                owner = random.choice(users)
                title = _title_from(
                    cand["description"], f"{category.capitalize()} GIF"
                )

                # Tags: the category-themed pool + the category name itself.
                tags = random.sample(data["tags"], k=3) + [category]

                gif = Gif(
                    user_id=owner.id,
                    title=title,
                    description=f"A real {category} GIF for testing OpenGIPHY.",
                    tags=list(dict.fromkeys(tags)),  # de-dup, keep order
                    category=category,
                    file_path=disk_path.replace("\\", "/"),
                    view_count=random.randint(0, 5000),
                )
                session.add(gif)
                created.append(gif)
                saved += 1
                time.sleep(0.05)  # be polite to the CDN
            print(f"  -> saved {saved} GIFs for '{category}'")

        session.commit()
        for g in created:
            session.refresh(g)

        # Sprinkle some likes so Trending differs from New.
        like_rows = 0
        for gif in created:
            for user in random.sample(users, k=random.randint(0, len(users))):
                session.add(Like(user_id=user.id, gif_id=gif.id))
                like_rows += 1
        session.commit()

        total = len(session.exec(select(Gif)).all())
        print(
            f"Seeded {len(created)} real GIFs across {len(CATEGORY_DATA)} "
            f"categories ({like_rows} likes) by users: "
            f"{', '.join(u.username for u in users)}."
        )
        print(f"Total GIFs in DB now: {total}.")


if __name__ == "__main__":
    main()
