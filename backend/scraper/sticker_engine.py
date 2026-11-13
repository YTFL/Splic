"""
scraper/sticker_engine.py — Scrapes images, removes backgrounds, and caches stickers in ~/.splic/stickers/.
"""

import io
import os
import re
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

import requests
from PIL import Image

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

try:
    import rembg
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False

from config import STICKERS_DIR, TIMELINE_STUDIO_STICKERS_DIR, TIMELINE_STUDIO_MANIFEST

logger = logging.getLogger("scraper.sticker_engine")
logger.setLevel(logging.INFO)

# Static default stickers fallback map
STATIC_FALLBACK_MAP = {
    "money": "/assets/stickers/shop-coins.png",
    "paise": "/assets/stickers/shop-coins.png",
    "cash": "/assets/stickers/shop-coins.png",
    "rupee": "/assets/stickers/shop-coins.png",
    "fire": "/assets/stickers/trend-flame.png",
    "aag": "/assets/stickers/trend-flame.png",
    "hot": "/assets/stickers/trend-flame.png",
    "star": "/assets/stickers/trend-starburst.png",
    "bolt": "/assets/stickers/trend-bolt.png",
    "bijli": "/assets/stickers/trend-bolt.png",
    "verified": "/assets/stickers/trend-verified.png",
    "like": "/assets/stickers/react-like.png",
    "heart": "/assets/stickers/react-heart.png",
    "dil": "/assets/stickers/react-heart.png",
    "alert": "/assets/stickers/react-alert.png",
    "khatra": "/assets/stickers/react-alert.png",
    "gift": "/assets/stickers/shop-gift.png",
    "bag": "/assets/stickers/shop-bag.png",
    "cart": "/assets/stickers/shop-cart.png",
    "food": "/assets/stickers/shop-bag.png",
    "khana": "/assets/stickers/shop-bag.png",
    "camera": "/assets/stickers/shop-camera.png",
    "idea": "/assets/stickers/shop-idea.png",
    "music": "/assets/stickers/voice-music-note.png",
    "mic": "/assets/stickers/voice-mic.png",
    "crown": "/assets/stickers/trend-crown.png",
    "rocket": "/assets/stickers/trend-rocket.png",
}


def normalize_keyword(keyword: str) -> str:
    """Normalize keyword to safe lowercase filename slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", keyword.lower()).strip("_")
    return slug or "sticker"


def get_sticker_path(filename_or_slug: str) -> Optional[Path]:
    """Retrieve Path if sticker exists in user's ~/.splic/stickers/ folder."""
    filename = filename_or_slug if filename_or_slug.endswith(".png") else f"{filename_or_slug}.png"
    target = STICKERS_DIR / filename
    if target.exists() and target.is_file():
        return target
    return None


def find_static_fallback(keyword: str) -> Optional[str]:
    """Find a matching pre-bundled static sticker as a fallback."""
    kw_lower = keyword.lower().strip()
    for k, path in STATIC_FALLBACK_MAP.items():
        if k in kw_lower or kw_lower in k:
            return path

    if TIMELINE_STUDIO_MANIFEST.exists():
        try:
            with open(TIMELINE_STUDIO_MANIFEST, "r", encoding="utf-8") as f:
                items = json.load(f)
            for item in items:
                name = item.get("nameEn", "").lower()
                item_id = item.get("id", "").lower()
                if kw_lower in name or kw_lower in item_id:
                    return item.get("src")
        except Exception as e:
            logger.warning(f"Error reading stickers manifest: {e}")

    return None


def clean_background(img: Image.Image) -> Image.Image:
    """
    Remove background and crop transparent borders.
    Uses rembg if installed, otherwise uses smart alpha keying for solid backgrounds.
    """
    max_dim = 512
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    rgba_img = img.convert("RGBA")

    if HAS_REMBG:
        try:
            output = rembg.remove(rgba_img)
            bbox = output.getbbox()
            if bbox:
                output = output.crop(bbox)
            return output
        except Exception as e:
            logger.warning(f"rembg processing failed, falling back to smart keying: {e}")

    alpha = rgba_img.split()[3]
    extrema = alpha.getextrema()
    if extrema[0] < 50:
        bbox = rgba_img.getbbox()
        if bbox:
            rgba_img = rgba_img.crop(bbox)
        return rgba_img

    w, h = rgba_img.size
    corners = [
        rgba_img.getpixel((0, 0)),
        rgba_img.getpixel((w - 1, 0)),
        rgba_img.getpixel((0, h - 1)),
        rgba_img.getpixel((w - 1, h - 1)),
    ]
    avg_r = sum(c[0] for c in corners) // 4
    avg_g = sum(c[1] for c in corners) // 4
    avg_b = sum(c[2] for c in corners) // 4

    is_light_bg = (avg_r > 230 and avg_g > 230 and avg_b > 230)
    is_dark_bg = (avg_r < 25 and avg_g < 25 and avg_b < 25)

    if is_light_bg or is_dark_bg:
        pixels = rgba_img.load()
        tolerance = 30
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                diff = abs(r - avg_r) + abs(g - avg_g) + abs(b - avg_b)
                if diff < tolerance:
                    pixels[x, y] = (r, g, b, 0)
                elif diff < tolerance * 2:
                    alpha_factor = (diff - tolerance) / tolerance
                    pixels[x, y] = (r, g, b, int(255 * alpha_factor))

    bbox = rgba_img.getbbox()
    if bbox:
        rgba_img = rgba_img.crop(bbox)

    return rgba_img


def fetch_and_make_sticker(keyword: str, timeout: float = 4.0) -> Optional[Dict[str, Any]]:
    """
    Search, strip background, and save transparent sticker PNG into ~/.splic/stickers/<slug>.png.
    """
    slug = normalize_keyword(keyword)
    filename = f"{slug}.png"
    target_path = STICKERS_DIR / filename

    # 1. Check local user storage cache (~/.splic/stickers/)
    if target_path.exists() and target_path.stat().st_size > 0:
        logger.info(f"User storage cache hit for '{keyword}' -> {target_path}")
        return {
            "keyword": keyword,
            "slug": slug,
            "filename": filename,
            "asset_url": f"/api/stickers/{filename}",
            "save_path": str(target_path),
            "size_bytes": target_path.stat().st_size,
            "cached": True,
            "fallback": False,
        }

    # 2. Search web image using DDGS
    image_bytes = None
    if DDGS is not None:
        search_queries = [
            f"{keyword} isolated transparent png sticker",
            f"{keyword} logo transparent png",
        ]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        for query in search_queries:
            try:
                ddg = DDGS(timeout=timeout)
                results = list(ddg.images(query, max_results=2))
                if not results:
                    continue

                for res in results:
                    img_url = res.get("image") or res.get("thumbnail")
                    if not img_url:
                        continue
                    try:
                        resp = requests.get(img_url, headers=headers, timeout=timeout)
                        if resp.status_code == 200 and len(resp.content) > 1000:
                            image_bytes = resp.content
                            break
                    except Exception as ex:
                        logger.debug(f"Failed fetching {img_url}: {ex}")
                        continue

                if image_bytes:
                    break
            except Exception as e:
                err_str = str(e).lower()
                logger.warning(f"Search query '{query}' failed: {e}")
                if "dns" in err_str or "resolution" in err_str or "noroute" in err_str:
                    break
                continue

    # 3. Process and save to user's ~/.splic/stickers/ folder
    if image_bytes:
        try:
            raw_img = Image.open(io.BytesIO(image_bytes))
            processed_img = clean_background(raw_img)
            processed_img.save(target_path, "PNG", optimize=True)

            logger.info(f"Saved sticker for '{keyword}' in user storage -> {target_path}")
            return {
                "keyword": keyword,
                "slug": slug,
                "filename": filename,
                "asset_url": f"/api/stickers/{filename}",
                "save_path": str(target_path),
                "size_bytes": target_path.stat().st_size,
                "cached": False,
                "fallback": False,
            }
        except Exception as e:
            logger.error(f"Error processing image for '{keyword}': {e}")

    # 4. Fallback to pre-bundled static stickers if web discovery is unavailable
    fallback = find_static_fallback(keyword)
    if fallback:
        logger.info(f"Using static fallback for '{keyword}' -> {fallback}")
        return {
            "keyword": keyword,
            "slug": slug,
            "filename": Path(fallback).name,
            "asset_url": fallback,
            "save_path": None,
            "size_bytes": 0,
            "cached": False,
            "fallback": True,
        }

    logger.warning(f"No sticker could be generated or matched for '{keyword}'")
    return None


def list_downloaded_stickers() -> List[Dict[str, Any]]:
    """List all stickers currently in the user storage ~/.splic/stickers/ folder."""
    if not STICKERS_DIR.exists():
        return []

    stickers = []
    for file_path in STICKERS_DIR.glob("*.png"):
        stickers.append({
            "filename": file_path.name,
            "slug": file_path.stem,
            "size_bytes": file_path.stat().st_size,
            "asset_url": f"/api/stickers/{file_path.name}",
            "save_path": str(file_path),
            "modified_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
        })
    return stickers
