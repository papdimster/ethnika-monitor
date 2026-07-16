"""Ορχηστρωτής: RSS + Telegram + σελίδες HTML → ταξινόμηση → data/items.json."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from monitor.collector import collect, load_yaml, title_key  # noqa: E402
from monitor.classifier import classify, enrich  # noqa: E402
from monitor.scrapers import scrape_telegram, scrape_page  # noqa: E402
from monitor.alerts import send_alerts  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "items.json")
SOURCES = os.path.join(ROOT, "config", "sources.yaml")
KEYWORDS = os.path.join(ROOT, "config", "keywords.yaml")
RETENTION_DAYS = 7
DROP_CATEGORIES = {"Άσχετο"}


def min_severity_map(cfg) -> dict:
    m = {}
    for f in cfg.get("feeds", []) or []:
        if f.get("min_severity"):
            m[f["name"]] = int(f["min_severity"])
    for t in cfg.get("telegram", []) or []:
        if t.get("min_severity"):
            m["Telegram @" + t["username"].lstrip("@")] = int(t["min_severity"])
    for p in cfg.get("html_pages", []) or []:
        if p.get("min_severity"):
            m[p["name"]] = int(p["min_severity"])
    return m


def main():
    existing = []
    if os.path.exists(DATA):
        with open(DATA, encoding="utf-8") as f:
            existing = json.load(f).get("items", [])
    known = {it["id"] for it in existing}
    known_titles = {title_key(it["source"], it["title"]) for it in existing}

    cfg = load_yaml(SOURCES)
    kw_cfg = load_yaml(KEYWORDS)
    keywords = kw_cfg["keywords"] + kw_cfg.get("broad_geo_keywords", [])

    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
    fresh = collect(SOURCES, KEYWORDS, known, known_titles, min_published=cutoff)
    for ch in cfg.get("telegram", []) or []:
        fresh += scrape_telegram(ch, keywords, known)
    for pg in cfg.get("html_pages", []) or []:
        fresh += scrape_page(pg, keywords, known)

    print(f"[=] Νέα items προς ταξινόμηση: {len(fresh)}")

    # Θεραπεία: ξαναταξινομούμε παλιά Αταξινόμητα, έως 25 ανά τρέξιμο
    retry_pool = [it for it in existing if it.get("category") == "Αταξινόμητο"][:25]
    if retry_pool:
        print(f"[=] Επαναδιαλογή {len(retry_pool)} παλιών αταξινόμητων")
        classify(retry_pool)  # ενημερώνει τα αντικείμενα επιτόπου
        healed = [it for it in retry_pool
                  if it["category"] not in ("Αταξινόμητο", "Άσχετο")
                  and it["severity"] >= 3]
        enrich(healed)

    if fresh:
        fresh = classify(fresh)
        fresh = [it for it in fresh if it["category"] not in DROP_CATEGORIES]
        min_sev = min_severity_map(cfg)
        before = len(fresh)
        fresh = [it for it in fresh
                 if it["severity"] >= max(2, min_sev.get(it["source"], 1))]
        if before != len(fresh):
            print(f"[=] Κόπηκαν {before - len(fresh)} items κάτω από το κατώφλι πηγής")
        # Το ακριβό enrich (ελληνική σύνοψη+γωνία) μόνο σε ΣΟΒ 3+ — αυτά
        # που πραγματικά βλέπεις στο default view. Τα ΣΟΒ 2 μένουν με την
        # ωμή περίληψη πηγής· είναι ήδη κρυμμένα πίσω από το προεπιλεγμένο
        # φίλτρο, δεν έχει νόημα να πληρώνουμε πλήρη επεξεργασία γι' αυτά.
        worth_enrich = [it for it in fresh if it["severity"] >= 3]
        enrich(worth_enrich)
        send_alerts(fresh)

    merged = [it for it in existing + fresh
              if it["published"] >= cutoff
              and not it["id"].startswith("demo")
              and it.get("category") not in DROP_CATEGORIES
              and it.get("severity", 2) >= 2]
    merged.sort(key=lambda x: x["published"], reverse=True)

    # Αποφυγή διπλοεγγραφών: ίδια πηγή + σχεδόν ίδιος τίτλος = κρατάμε ένα
    seen_titles, deduped = set(), []
    for it in merged:
        key = (it["source"], "".join(ch for ch in it["title"].lower() if ch.isalnum())[:70])
        if key in seen_titles:
            continue
        seen_titles.add(key)
        deduped.append(it)
    merged = deduped

    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump({
            "updated": datetime.now(timezone.utc).isoformat(),
            "count": len(merged),
            "items": merged,
        }, f, ensure_ascii=False, indent=1)

    print(f"[✓] Σύνολο στο dashboard: {len(merged)} items")


if __name__ == "__main__":
    main()
