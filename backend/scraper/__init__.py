"""
scraper package — Image scraping, background removal, and asset downloads into ~/.splic/stickers/.
"""

from .sticker_engine import (
    fetch_and_make_sticker,
    list_downloaded_stickers,
    clean_background,
    get_sticker_path,
    STICKERS_DIR,
    HAS_REMBG,
)

__all__ = [
    "fetch_and_make_sticker",
    "list_downloaded_stickers",
    "clean_background",
    "get_sticker_path",
    "STICKERS_DIR",
    "HAS_REMBG",
]
