#!/usr/bin/env python3
"""Fetch and merge Stash icon sets. Requires Python 3.9+ and curl.

Run: python3 scripts/build_icon_sets.py
Use --output-dir DIR to write both JSON files to another directory.
Source sets and their icons retain their original order; the first URL wins.
All downloads and validation finish before any output file is replaced.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit


PAGE_URL = "https://clashios.app/blog/icon-set"
MINI_NAMES = {"mini+", "mini icons", "mini Color"}
GROUPS = (
    ("Qure Color", "Koolson/Qure", "QureColor.json"),
    ("Mini Color", "Orz-3/mini", "MiniColor.json"),
)


def fetch(url):
    if urlsplit(url).scheme not in {"https", "http"}:
        raise ValueError(f"Unsupported URL: {url}")
    result = subprocess.run(
        ["curl", "--location", "--silent", "--show-error", "--fail",
         "--proto", "=http,https", "--proto-redir", "=http,https",
         "--retry", "2", "--connect-timeout", "10", "--max-time", "45", url],
        capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(f"Download failed: {url}\n{result.stderr.decode(errors='replace').strip()}")
    return result.stdout


class IconSetLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.seen = set()

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        link = urlsplit(href)
        if link.scheme != "stash" or link.netloc != "install-icon-set":
            return
        # The site embeds raw URLs, including literal '+' in Mini filenames.
        # Form decoding (parse_qs/unquote_plus) would turn those into spaces.
        for parameter in link.query.split("&"):
            key, separator, value = parameter.partition("=")
            if not separator or unquote(key) != "url":
                continue
            url = unquote(value)
            if not url:
                continue
            if url not in self.seen:
                self.seen.add(url)
                self.urls.append(url)


def parse_links(html):
    parser = IconSetLinks()
    parser.feed(html)
    if not parser.urls:
        raise ValueError("No Stash icon-set links found on the page")
    return parser.urls


def load_set(url):
    data = json.loads(fetch(url))
    if not isinstance(data, dict) or not isinstance(data.get("name"), str):
        raise ValueError(f"Invalid icon-set name: {url}")
    return url, data


def merge_sets(source_sets):
    merged = {name: [] for name, _, _ in GROUPS}
    seen = {name: set() for name in merged}
    matched_mini = set()
    counts = {name: 0 for name in merged}
    for source_url, data in source_sets:
        name = data["name"]
        if name == "Qure Color" or name.startswith("Qure Color ("):
            group = "Qure Color"
        elif name in MINI_NAMES:
            group = "Mini Color"
            matched_mini.add(name)
        else:
            continue
        icons = data.get("icons")
        if not isinstance(icons, list) or not icons:
            raise ValueError(f"Missing or empty icons array: {source_url}")
        counts[group] += 1
        added = 0
        for icon in icons:
            if not isinstance(icon, dict) or not all(
                isinstance(icon.get(key), str) and icon[key].strip()
                for key in ("name", "url")
            ):
                raise ValueError(f"Invalid icon record: {source_url}: {icon!r}")
            url = icon["url"]
            if urlsplit(url).scheme not in {"http", "https"}:
                raise ValueError(f"Invalid icon URL: {url}")
            if url not in seen[group]:
                seen[group].add(url)
                merged[group].append({"name": icon["name"], "url": url})
                added += 1
        print(f"{name}: {len(icons)} records, {added} added", flush=True)
    if not counts["Qure Color"]:
        raise ValueError("No Qure Color sets found")
    if matched_mini != MINI_NAMES:
        raise ValueError(f"Missing Mini sets: {', '.join(sorted(MINI_NAMES - matched_mini))}")
    return merged


def validate_image(url):
    data = fetch(url)
    # These source sets contain PNG icons. Reject successful HTML error pages too.
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"Icon response is not a PNG: {url}")


def write_outputs(merged, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    staged = []
    try:
        for name, repo, filename in GROUPS:
            data = {
                "name": name,
                "description": f"基于开源项目 https://github.com/{repo} 整理。",
                "icons": merged[name],
            }
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=output_dir,
                prefix=f".{filename}.", suffix=".tmp", delete=False,
            ) as stream:
                staged.append((Path(stream.name), output_dir / filename))
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        for temporary, target in staged:
            os.replace(temporary, target)
            print(f"Written: {target}", flush=True)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def build(page_url, output_dir, workers):
    urls = parse_links(fetch(page_url).decode("utf-8"))
    print(f"Found {len(urls)} source sets", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        # executor.map yields in input order regardless of download completion order.
        source_sets = list(pool.map(load_set, urls))
        merged = merge_sets(source_sets)
        icon_urls = list(dict.fromkeys(
            icon["url"] for icons in merged.values() for icon in icons
        ))
        for count, _ in enumerate(pool.map(validate_image, icon_urls), 1):
            if count % 50 == 0 or count == len(icon_urls):
                print(f"Validated {count}/{len(icon_urls)} images", flush=True)
    write_outputs(merged, output_dir)
    for name, icons in merged.items():
        print(f"{name}: {len(icons)} unique icons", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page-url", default=PAGE_URL)
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    if not shutil.which("curl"):
        parser.error("curl is required")
    try:
        build(args.page_url, args.output_dir, args.workers)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
