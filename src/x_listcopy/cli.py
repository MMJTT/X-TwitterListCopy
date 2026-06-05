from __future__ import annotations

import argparse
import sys
import time

from .client import XClient
from .parsing import filter_new_members


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Copy X/Twitter List members using your logged-in web cookies."
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Source list id, /i/lists/<id> URL, or owner/list-slug.",
    )
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--dest-list-id", help="Existing destination list id.")
    target.add_argument("--create-list-name", help="Create a new destination list with this name.")
    parser.add_argument("--description", default="", help="Description when creating a list.")
    parser.add_argument("--private", action="store_true", help="Create the list as private.")
    parser.add_argument("--limit", type=int, help="Copy at most N members.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve and count members without creating or adding.",
    )
    parser.add_argument("--yes", action="store_true", help="Required for non-dry-run mutations.")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Seconds to wait between member additions.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.dry_run and not (args.dest_list_id or args.create_list_name):
        raise SystemExit("Use --dest-list-id or --create-list-name, or run with --dry-run.")
    if not args.dry_run and not args.yes:
        raise SystemExit("Refusing to modify X without --yes. Run --dry-run first.")

    client = XClient.from_env()
    viewer = client.viewer()
    source = client.resolve_list(args.source)
    members = client.fetch_members(source.id, limit=args.limit)

    viewer_legacy = viewer.get("legacy") or {}
    print(f"Logged in as @{viewer_legacy.get('screen_name') or viewer.get('rest_id')}", flush=True)
    print(f"Source list: {source.name or source.id} ({source.id})", flush=True)
    print(f"Members fetched: {len(members)}", flush=True)

    if args.dry_run:
        sample = ", ".join(
            "@" + user["screen_name"] for user in members[:10] if user.get("screen_name")
        )
        if sample:
            print(f"Sample: {sample}", flush=True)
        return 0

    if args.create_list_name:
        dest = client.create_list(args.create_list_name, args.description, args.private)
        print(f"Created destination list: {dest.name or dest.id} ({dest.id})", flush=True)
    else:
        dest = client.resolve_list(args.dest_list_id)
        print(f"Destination list: {dest.name or dest.id} ({dest.id})", flush=True)

    destination_members = client.fetch_members(dest.id)
    members_to_add = filter_new_members(members, destination_members)
    skipped = len(members) - len(members_to_add)
    if skipped:
        print(f"Skipping {skipped} members already present in the destination list.", flush=True)

    added = 0
    failed: list[tuple[dict[str, str | None], str]] = []
    for user in members_to_add:
        try:
            client.add_member(dest.id, user["id"])
            added += 1
            label = "@" + user["screen_name"] if user.get("screen_name") else user["id"]
            print(f"[{added}/{len(members_to_add)}] added {label}", flush=True)
            time.sleep(args.delay)
        except Exception as exc:
            failed.append((user, str(exc)))
            label = "@" + user["screen_name"] if user.get("screen_name") else user["id"]
            print(f"[failed] {label}: {exc}", file=sys.stderr, flush=True)

    print(f"Finished. Added {added}; failed {len(failed)}.", flush=True)
    return 1 if failed else 0
