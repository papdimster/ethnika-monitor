"""Ταξινομητής: στέλνει τα νέα items στο Claude API για κατηγορία,
σοβαρότητα, ελληνική σύνοψη και δημοσιογραφικό angle."""
import json
import os

import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"
BATCH = 10

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

    out = []
    for i in range(0, len(items), BATCH):
        chunk = items[i:i + BATCH]
        payload = [{"id": it["id"], "source": it["source"], "side": it["side"],
                    "title": it["title"], "summary": it["summary_raw"][:600]}
                   for it in chunk]
        body = json.dumps({
            "model": MODEL,
            "max_tokens": 4000,
            "system": SYSTEM,
            "messages": [{"role": "user",
                          "content": json.dumps(payload, ensure_ascii=False)}],
        }).encode("utf-8")

        req = urllib.request.Request(API_URL, data=body, headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        })
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            text = "".join(b.get("text", "") for b in data.get("content", []))
            text = text.replace("```json", "").replace("```", "").strip()
            results = {r["id"]: r for r in json.loads(text)}
        except Exception as e:
            print(f"[!] Σφάλμα ταξινόμησης batch: {e}")
            results = {}

        for it in chunk:
            r = results.get(it["id"], {})
            it.update({
                "category": r.get("category", "Αταξινόμητο"),
                "severity": int(r.get("severity", 2)),
                "summary_el": r.get("summary_el", it["summary_raw"][:200]),
                "angle": r.get("angle"),
                "turkish_narrative": bool(r.get("turkish_narrative", False)),
            })
            out.append(it)
        print(f"[+] Ταξινομήθηκαν {len(chunk)} items")

    return out
