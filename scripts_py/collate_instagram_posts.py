#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_timestamp(value):
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None

    normalized = text
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    if (
        len(normalized) >= 5
        and normalized[-5] in "+-"
        and normalized[-4:].isdigit()
        and normalized[-3] != ":"
    ):
        normalized = normalized[:-5] + normalized[-5:-2] + ":" + normalized[-2:]

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = None
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        ):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue

    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def resolve_base_dir():
    absolute = Path("/data")
    if absolute.exists():
        return absolute
    local = Path.cwd() / "data"
    if local.exists():
        return local
    raise FileNotFoundError("No /data or ./data directory found.")


def extract_posts(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        posts = payload.get("posts")
        if isinstance(posts, list):
            return posts
    return []


def build_record(post):
    return {
        "id": None,
        "caption": post.get("caption"),
        "media_type": None,
        "media_url": None,
        "permalink": post.get("url"),
        "timestamp": post.get("timestamp"),
    }


def main():
    base_dir = resolve_base_dir()
    json_files = sorted(base_dir.glob("*.json"))

    total_read = 0
    order_counter = 0
    deduped = {}
    no_permalink = []

    for path in json_files:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        posts = extract_posts(payload)
        for post in posts:
            if not isinstance(post, dict):
                continue
            total_read += 1
            order_counter += 1

            record = build_record(post)
            parsed_ts = parse_timestamp(record["timestamp"])
            permalink = record["permalink"]

            if permalink:
                existing = deduped.get(permalink)
                if existing is None:
                    deduped[permalink] = (record, parsed_ts, order_counter)
                else:
                    existing_record, existing_ts, existing_order = existing
                    if existing_ts is not None and parsed_ts is not None:
                        if parsed_ts > existing_ts:
                            deduped[permalink] = (
                                record,
                                parsed_ts,
                                existing_order,
                            )
                    else:
                        deduped[permalink] = (
                            existing_record,
                            existing_ts,
                            existing_order,
                        )
            else:
                no_permalink.append((record, parsed_ts, order_counter))

    combined = list(deduped.values()) + no_permalink

    def sort_key(item):
        record, parsed_ts, order = item
        if parsed_ts is None:
            return (1, 0, order)
        return (0, -parsed_ts.timestamp(), order)

    combined.sort(key=sort_key)
    output = [record for record, _, _ in combined]

    output_path = base_dir / "collated_posts.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=True, indent=2)

    total_written = len(output)
    duplicates_removed = total_read - total_written
    print(f"Total read: {total_read}")
    print(f"Total written: {total_written}")
    print(f"Duplicates removed: {duplicates_removed}")


if __name__ == "__main__":
    main()
