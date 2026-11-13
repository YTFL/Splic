"""
scraper/resolver.py — Resolves the director's JSON 1 (sticker_requests) into PNG assets.

Order per request:
  source="library" : sticker library id (bundled manifest or a cached scrape)
  source="scrape"  : disk cache (~/.splic/stickers/<slug>.png)
                     -> DuckDuckGo + rembg with the director's query (4 s budget each)
                     -> bundled sticker whose name matches the concept
                     -> unresolved (the placement is dropped; the pipeline never fails)
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Any, Callable, Dict, List, Optional

import catalog
from .sticker_engine import fetch_and_make_sticker, find_static_fallback, get_sticker_path, normalize_keyword

logger = logging.getLogger("scraper.resolver")

STICKER_TIMEOUT = 4.0           # per-sticker scrape budget (AGENTS.md Rule 6)
STICKER_BATCH_DEADLINE = 15.0   # wall-clock cap for all scrapes together


def resolve_sticker_requests(
    requests: List[Dict[str, Any]],
    allow_network: bool = True,
    timeout: float = STICKER_TIMEOUT,
    deadline: float = STICKER_BATCH_DEADLINE,
    on_scraped: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Return {ref: {"asset_url", "resolution"}} for every request that resolved.

    `on_scraped(result)` is called for each freshly scraped / cached PNG so the
    caller can index it (TinyDB). Unresolved refs are simply absent.
    """
    library = catalog.sticker_library()
    out: Dict[str, Dict[str, Any]] = {}
    to_scrape: Dict[str, List[Dict[str, Any]]] = {}  # slug -> requests sharing it

    for req in requests:
        ref = req["ref"]
        if req["source"] == "library":
            entry = library.get(req.get("library_id") or "")
            if entry:
                out[ref] = {
                    "asset_url": entry["asset_url"],
                    "resolution": "cache" if entry["category"] == "scraped" else "library",
                }
                continue
        slug = normalize_keyword(req["concept"])
        cached = get_sticker_path(slug)
        if cached:
            out[ref] = {"asset_url": f"/api/stickers/{cached.name}", "resolution": "cache"}
            continue
        to_scrape.setdefault(slug, []).append(req)

    if allow_network and to_scrape:
        pool = ThreadPoolExecutor(max_workers=min(4, len(to_scrape)))
        futures = {
            pool.submit(fetch_and_make_sticker, reqs[0]["concept"], timeout, reqs[0].get("query")): slug
            for slug, reqs in to_scrape.items()
        }
        done, _pending = wait(futures, timeout=deadline)
        for fut in done:
            slug = futures[fut]
            try:
                res = fut.result()
            except Exception as exc:  # the scraper must never crash the pipeline
                logger.warning("Sticker scrape failed for %s: %s", slug, exc)
                continue
            if not res or not res.get("asset_url"):
                continue
            resolution = "fallback_library" if res.get("fallback") else ("cache" if res.get("cached") else "scraped")
            for req in to_scrape[slug]:
                out[req["ref"]] = {"asset_url": res["asset_url"], "resolution": resolution}
            if not res.get("fallback") and res.get("save_path") and on_scraped:
                try:
                    on_scraped(res)
                except Exception as exc:
                    logger.warning("Could not index sticker '%s': %s", slug, exc)
        pool.shutdown(wait=False, cancel_futures=True)

    for reqs in to_scrape.values():
        for req in reqs:
            if req["ref"] in out:
                continue
            static = find_static_fallback(req["concept"])
            if static:
                out[req["ref"]] = {"asset_url": static, "resolution": "fallback_library"}
    return out
