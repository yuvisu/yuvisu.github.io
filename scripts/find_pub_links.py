#!/usr/bin/env python3
"""Fill scripts/pub_links.json with DOI links for papers that have none.

Looks each title up on Crossref and accepts a DOI only when the returned
title is a near-exact match, so a wrong paper is never linked. Existing
entries in pub_links.json are kept; edit that file by hand to fix or add a
link. Run build_publications.py first, then this, then build again:

    python3 scripts/build_publications.py
    python3 scripts/find_pub_links.py
    python3 scripts/build_publications.py
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINKS = ROOT / "scripts/pub_links.json"
MIN_RATIO = 0.93


def norm(title):
    title = re.sub(r"<[^>]+>", "", title)
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def crossref(title):
    q = urllib.parse.urlencode({"query.bibliographic": title, "rows": 5,
                                "select": "DOI,title"})
    req = urllib.request.Request(f"https://api.crossref.org/works?{q}",
                                 headers={"User-Agent": "yuvisu.github.io link finder"})
    for wait in (2, 5, 15, 0):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)["message"]["items"]
        except urllib.error.HTTPError as e:
            if e.code != 429 or not wait:
                raise
            time.sleep(wait)  # rate limited: back off and retry


def main():
    pubs = json.loads((ROOT / "_data/publications.json").read_text())["items"]
    links = json.loads(LINKS.read_text()) if LINKS.exists() else {}
    used = set(links.values())
    for p in pubs:
        if p["url"] or p["key"] in links:
            continue
        want = norm(p["title"])
        best = (0.0, None)
        try:
            for item in crossref(p["title"]):
                # A published paper should link to the paper, not its medRxiv/bioRxiv preprint.
                if p["type"] != "preprint" and item["DOI"].startswith("10.1101/"):
                    continue
                if f"https://doi.org/{item['DOI']}" in used:  # already another paper's DOI
                    continue
                got = norm((item.get("title") or [""])[0])
                ratio = SequenceMatcher(None, want, got).ratio()
                if ratio > best[0]:
                    best = (ratio, item["DOI"])
        except Exception as e:  # network hiccup: skip, rerun later
            print(f"  {p['key']}: lookup failed ({e})")
            continue
        if best[0] >= MIN_RATIO:
            links[p["key"]] = f"https://doi.org/{best[1]}"
            used.add(links[p["key"]])
            print(f"+ {p['key']}: {best[1]} ({best[0]:.2f})")
        else:
            print(f"  {p['key']}: no confident match ({best[0]:.2f})")
        time.sleep(1)
    LINKS.write_text(json.dumps(dict(sorted(links.items())), indent=1) + "\n")


if __name__ == "__main__":
    main()
