"""Ταξινομητής: στέλνει τα νέα items στο Claude API για κατηγορία,
σοβαρότητα, ελληνική σύνοψη και δημοσιογραφικό angle."""
import json
import os

import urllib.request

import re as _re

API_URL = "https://api.anthropic.com/v1/messages"


def _clean(text: str) -> str:
    """Καθαρίζει HTML tags/entities από RSS snippets πριν σταλούν στο μοντέλο."""
    import html as _html
    text = _re.sub(r"<[^>]+>", " ", text or "")
    return _re.sub(r"\s+", " ", _html.unescape(text)).strip()
MODEL = "claude-sonnet-4-6"
BATCH = 5

SYSTEM = """Είσαι αναλυτής εθνικών θεμάτων για Έλληνα δημοσιογράφο διεθνούς
ειδησεογραφίας και άμυνας. Ταξινομείς ειδήσεις που αφορούν ελληνικά εθνικά
ζητήματα. Απαντάς ΜΟΝΟ με έγκυρο JSON array, χωρίς markdown, χωρίς σχόλια.

Για κάθε item επιστρέφεις αντικείμενο με:
- id: το id που σου δόθηκε
- category: ένα από ["Ελληνοτουρκικά", "Αιγαίο-ΑΟΖ", "Κυπριακό", "Θράκη",
  "Άμυνα-Εξοπλισμοί", "Μεταναστευτικό", "Ενέργεια", "Διπλωματία", "Άσχετο"]
- severity: 1-5 (1=ρουτίνα, 3=αξίζει ρεπορτάζ, 5=κρίση/έκτακτο)
- summary_el: σύνοψη 1-2 προτάσεων στα ελληνικά, δημοσιογραφικό ύφος,
  με ονόματα και αριθμούς όπου υπάρχουν
- angle: πρόταση γωνίας για άρθρο σε ελληνικό μέσο (1 πρόταση) ή null
- turkish_narrative: true αν το item προωθεί τουρκικό αφήγημα (πηγή
  τουρκικού κράτους/ΜΜΕ με μονομερή πλαισίωση), αλλιώς false

Αν το item δεν αφορά πραγματικά ελληνικά εθνικά ζητήματα, βάλε
category "Άσχετο" και severity 1."""


def classify(items: list[dict]) -> list[dict]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[!] Λείπει ANTHROPIC_API_KEY — τα items μένουν αταξινόμητα")
        for it in items:
            it.update({"category": "Αταξινόμητο", "severity": 2,
                       "summary_el": it["summary_raw"][:200], "angle": None,
                       "turkish_narrative": False})
        return items

    def call_api(chunk):
        payload = [{"id": it["id"], "source": it["source"], "side": it["side"],
                    "title": _clean(it["title"]),
                    "summary": _clean(it["summary_raw"])[:600]}
                   for it in chunk]
        body = json.dumps({
            "model": MODEL,
            "max_tokens": 8000,
            "system": SYSTEM,
            "messages": [{"role": "user",
                          "content": json.dumps(payload, ensure_ascii=False)}],
        }).encode("utf-8")
        req = urllib.request.Request(API_URL, data=body, headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        })
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
        text = "".join(b.get("text", "") for b in data.get("content", []))
        text = text.replace("```json", "").replace("```", "").strip()
        return {r["id"]: r for r in json.loads(text)}

    def classify_chunk(chunk):
        """Αν αποτύχει η παρτίδα, σπάει στα δύο και ξαναδοκιμάζει."""
        try:
            return call_api(chunk)
        except Exception as e:
            import urllib.error
            if isinstance(e, urllib.error.HTTPError):
                try:
                    body = e.read().decode("utf-8", errors="replace")[:300]
                except Exception:
                    body = ""
                if "credit balance" in body.lower():
                    print("[!] ΤΕΛΕΙΩΣΕ Η ΠΙΣΤΩΣΗ — top-up στο console.anthropic.com")
                    return {}
                e = Exception(f"HTTP {e.code}: {body}")
            if len(chunk) == 1:
                print(f"[!] Απέτυχε μεμονωμένο item: {e}")
                return {}
            mid = len(chunk) // 2
            print(f"[!] Σφάλμα batch ({len(chunk)}) — σπάω σε δύο: {e}")
            res = classify_chunk(chunk[:mid])
            res.update(classify_chunk(chunk[mid:]))
            return res

    out = []
    for i in range(0, len(items), BATCH):
        chunk = items[i:i + BATCH]
        results = classify_chunk(chunk)
        for it in chunk:
            r = results.get(it["id"], {})
            it.update({
                "category": r.get("category", "Αταξινόμητο"),
                "severity": int(r.get("severity", 2)),
                "summary_el": r.get("summary_el", _clean(it["summary_raw"])[:200]),
                "angle": r.get("angle"),
                "turkish_narrative": bool(r.get("turkish_narrative", False)),
            })
            out.append(it)
        print(f"[+] Ταξινομήθηκαν {len(chunk)} items")

    return out
