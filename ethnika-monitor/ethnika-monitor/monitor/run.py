"""Ορχηστρωτής: τρέχει συλλογή → ταξινόμηση → ενημέρωση data/items.json."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from monitor.collector import collect  # noqa: E402
from monitor.classifier import classify  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "items.json")
RETENTION_DAYS = 14
DROP_CATEGORIES = {"Άσχετο"}


def main():
    existing = []
    if os.path.exists(DATA):
        with open(DATA, encoding="utf-8") as f:
            existing = json.load(f).get("items", [])
    known = {it["id"] for it in existing}

    fresh = collect(
        os.path.join(ROOT, "config", "sources.yaml"),
        os.path.join(ROOT, "config", "keywords.yaml"),
        known,
    )
    print(f"[=] Νέα items προς ταξινόμηση: {len(fresh)}")

    if fresh:
        fresh = classify(fresh)
        fresh = [it for it in fresh if it["category"] not in DROP_CATEGORIES]

    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
    merged = [it for it in existing + fresh if it["published"] >= cutoff]
    merged.sort(key=lambda x: (x["published"]), reverse=True)

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
