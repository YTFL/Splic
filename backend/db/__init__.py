"""
db package — Embedded NoSQL Document Store (TinyDB) in ~/.splic/db.json.
"""

from .database import (
    get_db,
    close_db,
    create_project,
    get_project,
    list_projects,
    update_project,
    delete_project,
    record_sticker,
    get_project_stickers,
    get_all_stickers,
    get_sticker_by_keyword,
)

__all__ = [
    "get_db",
    "close_db",
    "create_project",
    "get_project",
    "list_projects",
    "update_project",
    "delete_project",
    "record_sticker",
    "get_project_stickers",
    "get_all_stickers",
    "get_sticker_by_keyword",
]
