"""Πρωινό δελτίο: σύνοψη 24ώρου από το Claude — για dashboard και Telegram."""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "items.json")
OUT = os.path.join(ROOT, "data", "digest.json")

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"

PROMPT = """Είσαι ο βοηθός Έλληνα δημοσιογράφου διεθνών θεμάτων και άμυνας.
Σου δίνονται οι ειδήσεις εθνικού ενδιαφέροντος του τελευταίου 24ώρου
(ήδη ταξινομημένες με κατηγορία και σοβαρότητα 1-5).

Γράψε πρωινό ενημερωτικό δελτίο στα ελληνικά, 250-400 λέξεις, με δομή:
1. Μία πρόταση-εικόνα του 24ώρου.
2. Τα 3-5 σημαντικότερα θέματα, το καθένα με 1-2 προτάσεις ουσίας
   (ονόματα, αριθμοί) — όχι απλή απαρίθμηση τίτλων.
3. «Αξίζει άρθρο»: 1-2 θέματα με δημοσιογραφική γωνία που ξεχωρίζουν.
4. «Τουρκικό αφήγημα»: αν υπάρχουν items σημασμένα έτσι, μία πρόταση
   για το τι σπρώχνει σήμερα η Άγκυρα.

Ύφος λιτό, επαγγελματικό, χωρίς εισαγωγές τύπου "Καλημέρα" και χωρίς
markdown μορφοποίηση — σκέτο κείμενο με κενές γραμμές μεταξύ ενοτήτων."""


def build_digest() -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[!] Λείπει ANTHROPIC_API_KEY")
        return None

    with open(DATA, encoding="utf-8") as f:
        items = json.load(f).get("items", [])

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    recent = [it for it in items if it["published"] >= cutoff]
    if not recent:
        print("[=] Κανένα item 24ώρου — δεν βγαίνει δελτίο")
        return None

    payload = [{"category": it["category"], "severity": it["severity"],
                "source": it["source"], "title": it["title"],
                "summary": it.get("summary_el", ""),
                "turkish_narrative": it.get("turkish_narrative", False)}
               for it in sorted(recent, key=lambda x: -x["severity"])[:60]]

    body = json.dumps({
        "model": MODEL,
        "max_tokens": 1500,
        "system": PROMPT,
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
    text = "".join(b.get("text", "") for b in data.get("content", [])).strip()
    print(f"[+] Δελτίο: {len(text)} χαρακτήρες από {len(recent)} items")
    return text


def send_telegram(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    stamp = datetime.now(timezone.utc).strftime("%d/%m")
    full = f"📋 ΠΡΩΙΝΟ ΔΕΛΤΙΟ ΕΘΝΙΚΩΝ ΘΕΜΑΤΩΝ — {stamp}\n\n{text}"
    # Το Telegram κόβει στους 4096 χαρακτήρες — σπάμε αν χρειαστεί
    chunks = [full[i:i + 3900] for i in range(0, len(full), 3900)]
    for chunk in chunks:
        body = json.dumps({"chat_id": chat_id, "text": chunk}).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=30)
        except Exception as e:
            print(f"[!] Telegram digest: {e}")
            return
    print("[+] Δελτίο στάλθηκε στο Telegram")


def main():
    text = build_digest()
    if not text:
        return
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({
            "generated": datetime.now(timezone.utc).isoformat(),
            "text": text,
        }, f, ensure_ascii=False, indent=1)
    send_telegram(text)


if __name__ == "__main__":
    main()
