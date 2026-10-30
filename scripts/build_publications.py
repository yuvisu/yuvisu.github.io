#!/usr/bin/env python3
"""Build _data/publications.json from the YUCV BibTeX files.

The CV (YH_KB/YUCV/bib) is the source of truth for publications. Run this
after editing the CV's .bib files, then commit the regenerated JSON:

    python3 scripts/build_publications.py
    python3 scripts/build_publications.py --bib /path/to/YUCV/bib

Rules follow the CV's README:
  - keywords = {journal | conference | submitted} decides the group.
  - In conference.bib, entries after the "Abstracts" divider are abstracts.
  - @comment entries are hidden, as they are in the CV.
  - "Huang*, Yu" marks co-first or corresponding authorship.
Links come from scripts/pub_links.json (bib key -> URL); arXiv, bioRxiv and
medRxiv identifiers in howpublished/note are linked automatically.
Bib keys listed in scripts/pub_hidden.json stay in the CV but not on the site.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BIB = Path.home() / "Documents/YH_KB/YUCV/bib"
BIB_FILES = ["journal.bib", "conference.bib", "submitted.bib"]
ME = ("Huang", "Yu")
MAX_AUTHORS = 12      # longer lists are shortened
KEEP_LEADING = 8      # authors kept at the start of a shortened list

LATEX = [
    (r"{\v{S}}", "Š"), (r"\v{S}", "Š"), (r"{\o}", "ø"), (r"\o", "ø"),
    (r"$\times$", "×"), (r"\&", "&"), ("---", "—"), ("--", "–"),
    ("\\ ", " "), ("~", " "),
]


def clean(text):
    for src, dst in LATEX:
        text = text.replace(src, dst)
    text = re.sub(r"\\emph\{([^{}]*)\}", r"<em>\1</em>", text)
    text = re.sub(r"\\textit\{([^{}]*)\}", r"<em>\1</em>", text)
    text = text.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", text).strip()


def read_braced(s, i):
    """Return (content, end) for the brace group starting at s[i] == '{'."""
    depth, start = 0, i
    while i < len(s):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start + 1:i], i + 1
        i += 1
    raise ValueError("unbalanced braces near: " + s[start:start + 60])


def parse_fields(body):
    fields, i = {}, 0
    for m in re.finditer(r"(\w+)\s*=\s*\{", body):
        if m.start() < i:
            continue
        value, i = read_braced(body, m.end() - 1)
        fields[m.group(1).lower()] = value
    return fields


def parse_bib(path):
    """Yield (entry_type, key, fields, after_abstracts_divider)."""
    text = path.read_text(encoding="utf-8-sig")
    entry_re = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,")
    divider_at = None
    m = re.search(r"^%[ -]*Abstracts[ -]*$", text, re.M)
    if m:
        divider_at = m.start()
    for m in entry_re.finditer(text):
        body, _ = read_braced(text, text.index("{", m.start()))
        body = body.split(",", 1)[1]
        abstract = divider_at is not None and m.start() > divider_at
        yield m.group(1).lower(), m.group(2), parse_fields(body), abstract


def parse_authors(raw):
    authors = []
    for part in re.split(r"\s+and\s+", raw):
        last, _, first = part.partition(",")
        star = "*" in last
        last, first = clean(last.replace("*", "")), clean(first)
        authors.append({
            "name": f"{first} {last}".strip(),
            "me": (last, first) == ME,
            "star": star,
        })
    return authors


def shorten(authors):
    if len(authors) <= MAX_AUTHORS:
        return authors
    keep = set(range(KEEP_LEADING)) | {len(authors) - 1}
    keep |= {i for i, a in enumerate(authors) if a["me"]}
    out, prev = [], -1
    for i in sorted(keep):
        if i != prev + 1:
            out.append({"gap": True})
        out.append(authors[i])
        prev = i
    return out


def details(f):
    """Volume(number), pages or article number, e.g. '15(1), 8653'."""
    vol = f.get("volume", "")
    if vol and f.get("number"):
        vol += f"({f['number']})"
    loc = f.get("pages") or f.get("eid") or ""
    return clean(", ".join(x for x in (vol, loc) if x))


def auto_link(f):
    blob = " ".join(f.get(k, "") for k in ("howpublished", "note"))
    m = re.search(r"arXiv:(\d{4}\.\d{4,5})", blob)
    if m:
        return f"https://arxiv.org/abs/{m.group(1)}"
    m = re.search(r"(?:bioRxiv|medRxiv)\s+(\d{4}\.\d{2}\.\d{2}\.\d+)", blob)
    if m:
        return f"https://doi.org/10.1101/{m.group(1)}"
    return ""


def build(bib_dir):
    links_file = ROOT / "scripts/pub_links.json"
    links = json.loads(links_file.read_text()) if links_file.exists() else {}
    hidden_file = ROOT / "scripts/pub_hidden.json"
    hidden = set(json.loads(hidden_file.read_text())) if hidden_file.exists() else set()
    items = []
    for name in BIB_FILES:
        for etype, key, f, abstract in parse_bib(bib_dir / name):
            if etype == "comment" or key in hidden:
                continue
            group = f.get("keywords", "").strip()
            if group == "conference" and abstract:
                group = "abstract"
            if group == "submitted":
                group = "preprint"
            venue = f.get("journal") or f.get("booktitle") or f.get("howpublished", "")
            authors = parse_authors(f["author"])
            items.append({
                "key": key,
                "type": group,
                "year": int(f["year"]),
                "title": clean(f["title"]),
                "authors": shorten(authors),
                "n_authors": len(authors),
                # First, co-first (starred in the first two places), or last author.
                # A star further down the list marks a corresponding author only.
                "first_or_senior": authors[0]["me"] or authors[-1]["me"] or any(
                    a["me"] and a["star"] for a in authors[:2]),
                "venue": clean(venue),
                "details": details(f),
                "note": clean(f.get("note", "")),
                # null rather than "" so Liquid's {% if p.url %} is false
                "url": links.get(key) or auto_link(f) or None,
            })
    # Newest first; within a year keep the CV's own order.
    items.sort(key=lambda p: -p["year"])
    counts = {t: sum(p["type"] == t for p in items)
              for t in ("journal", "conference", "abstract", "preprint")}
    counts["total"] = len(items)
    return {"counts": counts, "items": items}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bib", type=Path, default=DEFAULT_BIB,
                    help=f"folder with the CV .bib files (default: {DEFAULT_BIB})")
    args = ap.parse_args()
    data = build(args.bib)
    out = ROOT / "_data/publications.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    c = data["counts"]
    print(f"Wrote {out.relative_to(ROOT)}: {c['total']} items "
          f"({c['journal']} journal, {c['conference']} conference, "
          f"{c['abstract']} abstracts, {c['preprint']} preprints)")
    missing = [p["key"] for p in data["items"] if not p["url"]]
    if missing:
        print(f"{len(missing)} without a link (add them to scripts/pub_links.json): "
              + ", ".join(missing))


if __name__ == "__main__":
    main()
