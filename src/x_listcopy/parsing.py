from __future__ import annotations

import re
import urllib.parse
from collections.abc import Iterable

from .models import ListReference


def parse_list_reference(value: str) -> ListReference:
    raw = value.strip()
    if re.fullmatch(r"\d+", raw):
        return ListReference(kind="id", list_id=raw)

    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme and parsed.netloc:
        path_parts = [
            urllib.parse.unquote(part)
            for part in parsed.path.strip("/").split("/")
            if part
        ]
    else:
        path_parts = [part for part in raw.strip("/").split("/") if part]

    if len(path_parts) >= 3 and path_parts[0] == "i" and path_parts[1] == "lists":
        if re.fullmatch(r"\d+", path_parts[2]):
            return ListReference(kind="id", list_id=path_parts[2])

    if len(path_parts) >= 3 and path_parts[1] == "lists":
        owner = path_parts[0].lstrip("@")
        slug = path_parts[2]
        if owner and slug:
            return ListReference(kind="slug", owner_screen_name=owner, slug=slug)

    if len(path_parts) == 2:
        owner = path_parts[0].lstrip("@")
        slug = path_parts[1]
        if owner and slug:
            return ListReference(kind="slug", owner_screen_name=owner, slug=slug)

    raise ValueError("List must be a numeric id, /i/lists/<id>, or owner/list-slug.")


def extract_users_from_timeline(timeline: dict) -> tuple[list[dict[str, str | None]], str | None]:
    users: list[dict[str, str | None]] = []
    seen: set[str] = set()
    bottom_cursor: str | None = None

    for entry in _timeline_entries(timeline):
        cursor = _extract_bottom_cursor(entry)
        if cursor:
            bottom_cursor = cursor

        for user in _extract_user_results(entry):
            user_id = user.get("rest_id")
            if not user_id or user_id in seen:
                continue
            seen.add(user_id)
            legacy = user.get("legacy") or {}
            users.append({"id": user_id, "screen_name": legacy.get("screen_name")})

    return users, bottom_cursor


def filter_new_members(
    source_members: list[dict[str, str | None]],
    destination_members: list[dict[str, str | None]],
) -> list[dict[str, str | None]]:
    destination_ids = {user.get("id") for user in destination_members if user.get("id")}
    return [user for user in source_members if user.get("id") not in destination_ids]


def is_list_response_decode_error(error: str) -> bool:
    return (
        "com.twitter.strato.serialization.DecodeException" in error
        and "default_banner_media_results" in error
    )


def _timeline_entries(timeline: dict) -> Iterable[dict]:
    for instruction in timeline.get("instructions") or []:
        if not isinstance(instruction, dict):
            continue
        entries = instruction.get("entries")
        if entries:
            for entry in entries:
                if isinstance(entry, dict):
                    yield entry
        entry = instruction.get("entry")
        if isinstance(entry, dict):
            yield entry


def _extract_bottom_cursor(entry: dict) -> str | None:
    for obj in _walk_dicts(entry):
        if obj.get("cursorType") == "Bottom" and isinstance(obj.get("value"), str):
            return obj["value"]
    return None


def _extract_user_results(entry: dict) -> Iterable[dict]:
    for obj in _walk_dicts(entry):
        user_results = obj.get("user_results")
        result = user_results.get("result") if isinstance(user_results, dict) else None
        if isinstance(result, dict) and result.get("__typename", "User") == "User":
            yield result


def _walk_dicts(value) -> Iterable[dict]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)
