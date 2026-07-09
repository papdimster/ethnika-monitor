"""Συλλέκτης: κατεβάζει RSS feeds, φιλτράρει με keywords, κρατά νέα items."""
import hashlib
import time
from datetime import datetime, timezone

import feedparser
import yaml


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def item_id(link: str) -> str:
    return hashlib.sha256(link.encode("utf-8")).hexdigest()[:16]


def matches_keywords(text: str, keywords: list[str]) -> list[str]:
    """Σύντομες λατινικές λέξεις (<=4 χαρ.) πιάνονται μόνο ως αυτόνομες λέξεις,
    ώστε π.χ. το 'ege' να μην πιάνεται μέσα στο 'allegedly'."""
    import re as _re
    low = text.lower()
    hits = []
    for k in keywords:
        kl = k.lower()
        if len(kl) <= 4 and kl.isascii():
            if _re.search(r"(?<![a-z0-9])" + _re.escape(kl) + r"(?![a-z0-9])", low):
                hits.append(k)
        elif kl in low:
            hits.append(k)
    return hits


def parse_date(entry) -> str:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def collect(sources_path: str, keywords_path: str, known_ids: set[str]) -> list[dict]:
    """Επιστρέφει νέα items που πιάνουν keywords και δεν υπάρχουν ήδη."""
    sources = load_yaml(sources_path)["feeds"]
    keywords = load_yaml(keywords_path)["keywords"]
    fresh = []

    for src in sources:
        try:
            parsed = feedparser.parse(src["url"])
        except Exception as e:
            print(f"[!] {src['name']}: {e}")
            continue

        for entry in parsed.entries[:40]:
            link = getattr(entry, "link", None)
            title = getattr(entry, "title", "") or ""
            if not link or not title:
                continue

            iid = item_id(link)
            if iid in known_ids:
                continue

            summary = getattr(entry, "summary", "") or ""
            hits = matches_keywords(f"{title} {summary}", keywords)
            if not hits and not src.get("skip_keywords"):
                continue

            fresh.append({
                "id": iid,
                "title": title.strip(),
                "link": link,
                "summary_raw": summary.strip()[:1200],
                "source": src["name"],
                "side": src.get("side", "unknown"),
                "lang": src.get("lang", "en"),
                "published": parse_date(entry),
                "collected": datetime.now(timezone.utc).isoformat(),
                "keywords_hit": hits[:8],
            })
        print(f"[+] {src['name']}: {len(parsed.entries)} entries")

    return fresh
