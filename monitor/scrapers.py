"""Scrapers χωρίς εξωτερικές βιβλιοθήκες:
- Δημόσια κανάλια Telegram μέσω του web preview (t.me/s/<channel>)
- Σελίδες HTML χωρίς RSS (π.χ. Millet Gazetesi / Batı Trakya)
"""
import hashlib
import html as htmllib
import re
import urllib.request
from datetime import datetime, timezone

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def _strip_tags(s: str) -> str:
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    return htmllib.unescape(s).strip()


def _iid(link: str) -> str:
    return hashlib.sha256(link.encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------- Telegram

def scrape_telegram(channel_cfg: dict, keywords: list[str],
                    known_ids: set[str]) -> list[dict]:
    """Διαβάζει το t.me/s/<username> — τα ~20 τελευταία posts."""
    username = channel_cfg["username"].lstrip("@")
    try:
        page = _get(f"https://t.me/s/{username}")
    except Exception as e:
        print(f"[!] TG @{username}: {e}")
        return []

    items = []
    blocks = page.split('tgme_widget_message_wrap')[1:]
    for block in blocks:
        m_post = re.search(r'data-post="([^"]+)"', block)
        if not m_post:
            continue
        link = "https://t.me/" + m_post.group(1)
        iid = _iid(link)
        if iid in known_ids:
            continue

        m_text = re.search(
            r'tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block, re.S)
        text = _strip_tags(m_text.group(1)) if m_text else ""
        if len(text) < 15:
            continue

        low = text.lower()
        hits = [k for k in keywords if k.lower() in low]
        if not hits and not channel_cfg.get("skip_keywords"):
            continue

        m_time = re.search(r'datetime="([^"]+)"', block)
        published = m_time.group(1) if m_time else _now()

        items.append({
            "id": iid,
            "title": text[:180] + ("…" if len(text) > 180 else ""),
            "link": link,
            "summary_raw": text[:1200],
            "source": f"Telegram @{username}",
            "side": channel_cfg.get("side", "telegram"),
            "lang": channel_cfg.get("lang", "en"),
            "published": published,
            "collected": _now(),
            "keywords_hit": hits[:8],
        })
    print(f"[+] TG @{username}: {len(blocks)} posts, {len(items)} νέα σχετικά")
    return items


# ------------------------------------------------------------- HTML pages

def scrape_page(page_cfg: dict, keywords: list[str],
                known_ids: set[str]) -> list[dict]:
    """Μαζεύει links άρθρων από σελίδα χωρίς RSS."""
    url = page_cfg["url"]
    pattern = page_cfg["link_pattern"]
    try:
        page = _get(url)
    except Exception as e:
        print(f"[!] {page_cfg['name']}: {e}")
        return []

    seen, items = set(), []
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S):
        link, raw_title = m.group(1), _strip_tags(m.group(2))
        if pattern not in link or link.rstrip("/").endswith(pattern.strip("/")):
            continue
        if link.startswith("/"):
            base = "/".join(url.split("/")[:3])
            link = base + link
        if link in seen or len(raw_title) < 25:
            continue
        seen.add(link)

        iid = _iid(link)
        if iid in known_ids:
            continue

        if not page_cfg.get("skip_keywords"):
            low = raw_title.lower()
            if not [k for k in keywords if k.lower() in low]:
                continue

        items.append({
            "id": iid,
            "title": raw_title,
            "link": link,
            "summary_raw": "",
            "source": page_cfg["name"],
            "side": page_cfg.get("side", "unknown"),
            "lang": page_cfg.get("lang", "tr"),
            "published": _now(),
            "collected": _now(),
            "keywords_hit": [],
        })
    print(f"[+] {page_cfg['name']}: {len(items)} νέα άρθρα")
    return items
