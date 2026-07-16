"""Ταξινομητής δύο σταδίων:
Στάδιο Α (Haiku, φτηνό): κατηγορία + σοβαρότητα + τουρκικό αφήγημα.
Στάδιο Β (Haiku): ελληνική σύνοψη + γωνία ΜΟΝΟ για όσα περνούν τα κατώφλια.
"""
import json
import os
import re as _re
import urllib.error
import urllib.request

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_URL = (f"https://generativelanguage.googleapis.com/v1beta/models/"
              f"{GEMINI_MODEL}:generateContent")

BATCH = 8


def _clean(text: str) -> str:
    import html as _html
    text = _re.sub(r"<[^>]+>", " ", text or "")
    return _re.sub(r"\s+", " ", _html.unescape(text)).strip()


SYSTEM_TRIAGE = """Είσαι αναλυτής για Έλληνα δημοσιογράφο άμυνας/διεθνών.
Ταξινομείς ειδήσεις. Απαντάς ΜΟΝΟ με έγκυρο JSON array.

Για κάθε item: {"id": ..., "category": ..., "severity": 1-5,
"turkish_narrative": true/false}

category ένα από: ["Ελληνοτουρκικά", "Αιγαίο-ΑΟΖ", "Κυπριακό", "Θράκη",
"Άμυνα-Εξοπλισμοί", "Μεταναστευτικό", "Ενέργεια",
"Πράσινη Ενέργεια-Περιβάλλον", "Συντηρητική Ατζέντα", "ΥΠΕΞ-Ανατ.Μεσόγειος",
"Διπλωματία", "Άσχετο"]

severity: 1=ρουτίνα, 3=αξίζει ρεπορτάζ, 5=κρίση/έκτακτο.
turkish_narrative: true αν προωθεί μονομερώς τουρκικό κρατικό αφήγημα.

Κανόνες:
- "Ενέργεια" = υδρογονάνθρακες/ΑΟΖ/EastMed/ελληνοτουρκικός ανταγωνισμός.
- "Πράσινη Ενέργεια-Περιβάλλον" = ΑΠΕ, κλίμα, ηλεκτροκίνηση, πυρηνικά/SMR,
  LNG, ESG, ευρωπαϊκή ενεργειακή πολιτική.
- Items με side "green_*": πάντα "Πράσινη Ενέργεια-Περιβάλλον" (ή "Άσχετο"
  αν lifestyle χωρίς ουσία)· severity = αξία για ελληνικό πράσινο κοινό,
  Ευρώπη/Ελλάδα βαραίνουν, ΗΠΑ/Ασία μόνο αν διεθνούς σημασίας.
- Μεταναστευτικό: δηλώσεις αξιωματούχων/ΜΚΟ, αρθρογραφία και πρωτογενή
  περιστατικά (αφίξεις, ναυάγια, δομές) Ελλάδας/Ευρώπης. Τοπικά ρεπορτάζ
  από Κρήτη/Αιγαίο/Έβρο με αριθμούς ή νέα δομών: severity τουλάχιστον 3.
- Items με side "conservative_*": πάντα "Συντηρητική Ατζέντα" (ή "Άσχετο").
  Οι συνόψεις παραμένουν αυστηρά πραγματολογικές — τι γράφτηκε, από ποιον,
  με ποια στοιχεία. severity = δημοσιογραφική αξία για ελληνικό συντηρητικό
  κοινό: ευρωπαϊκά θέματα (μεταναστευτικό, εθνική κυριαρχία, οικογένεια,
  θρησκευτική ελευθερία, culture wars) βαραίνουν· αμερικανικά μόνο αν έχουν
  ευρωπαϊκή απήχηση. 5=μεγάλο θέμα με ελληνικό ενδιαφέρον, 3=αξίζει
  βίντεο/άρθρο, 1-2=εσωτερική κομματική ρουτίνα τρίτων χωρών.
- Items με side "mfa_official": πάντα "ΥΠΕΞ-Ανατ.Μεσόγειος" (ή "Άσχετο"
  αν είναι εντελώς άσχετο, π.χ. προξενικές υπηρεσίες ρουτίνας). Στόχος:
  χαρτογράφηση κινήσεων υπουργείων εξωτερικών Κύπρου, Αιγύπτου, Ισραήλ,
  Λιβάνου, Συρίας, Τουρκίας, Λιβύης — επισκέψεις, δηλώσεις, συμφωνίες,
  διμερείς επαφές. severity: 4-5 αν αφορά άμεσα Ελλάδα/Κύπρο/Τουρκία ή
  αλλαγή στάσης χώρας, 3 αν είναι σχετικό διπλωματικό κίνημα της περιοχής,
  1-2 αν είναι τυπική/πρωτοκολλαρισμένη ανακοίνωση.
- Ό,τι δεν αφορά τίποτα από αυτά: "Άσχετο", severity 1."""

SYSTEM_ENRICH = """Είσαι αναλυτής για Έλληνα δημοσιογράφο. Για κάθε item
απαντάς ΜΟΝΟ με JSON array από {"id": ..., "summary_el": ..., "angle": ...}.
- summary_el: σύνοψη 1-2 προτάσεων στα ελληνικά, δημοσιογραφικό ύφος,
  με ονόματα και αριθμούς όπου υπάρχουν.
- angle: πρόταση γωνίας για άρθρο σε ελληνικό μέσο (1 πρόταση) ή null."""


def explain_api_error(e) -> str:
    try:
        body = e.read().decode("utf-8", errors="replace")[:300]
    except Exception:
        body = ""
    if "credit balance" in body.lower():
        return "ΤΕΛΕΙΩΣΕ Η ΠΙΣΤΩΣΗ — top-up στο console.anthropic.com"
    return f"HTTP {e.code}: {body}"


def _call_gemini(system: str, payload, api_key: str, max_tokens: int):
    """Στάδιο Α (triage) μέσω Gemini Flash-Lite — 10x φθηνότερο, μόνο για
    κατηγορία/σοβαρότητα (μηχανική δουλειά, όχι ελληνική πρόζα)."""
    body = json.dumps({
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": json.dumps(payload, ensure_ascii=False)}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{GEMINI_URL}?key={api_key}", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    text = text.replace("```json", "").replace("```", "").strip()
    return {r["id"]: r for r in json.loads(text)}


def _call(system: str, payload, api_key: str, max_tokens: int):
    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "system": [{"type": "text", "text": system,
                    "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user",
                      "content": json.dumps(payload, ensure_ascii=False)}],
    }).encode("utf-8")
    req = urllib.request.Request(ANTHROPIC_URL, data=body, headers={
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    })
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    text = "".join(b.get("text", "") for b in data.get("content", []))
    text = text.replace("```json", "").replace("```", "").strip()
    return {r["id"]: r for r in json.loads(text)}


def _resilient(system, chunk_payload, api_key, max_tokens):
    """Σπάει την παρτίδα στα δύο αν αποτύχει, μέχρι το μεμονωμένο item."""
    try:
        return _call(system, chunk_payload, api_key, max_tokens)
    except Exception as e:
        if isinstance(e, urllib.error.HTTPError):
            msg = explain_api_error(e)
            if "ΠΙΣΤΩΣΗ" in msg:
                print(f"[!] {msg}")
                return {}
            e = Exception(msg)
        if len(chunk_payload) == 1:
            print(f"[!] Απέτυχε μεμονωμένο item: {e}")
            return {}
        mid = len(chunk_payload) // 2
        print(f"[!] Σφάλμα batch ({len(chunk_payload)}) — σπάω σε δύο: {e}")
        res = _resilient(system, chunk_payload[:mid], api_key, max_tokens)
        res.update(_resilient(system, chunk_payload[mid:], api_key, max_tokens))
        return res


def _triage_batch(payload, anthropic_key, gemini_key):
    """Gemini Flash-Lite πρώτα (10x φθηνότερο) — αν δεν υπάρχει κλειδί ή
    αποτύχει με οποιονδήποτε τρόπο (δίκτυο, quota, κακό JSON), πέφτουμε
    αυτόματα πίσω στο Anthropic Haiku, χωρίς να χαθεί ούτε ένα item."""
    if gemini_key:
        try:
            return _call_gemini(SYSTEM_TRIAGE, payload, gemini_key, 2000)
        except Exception as e:
            print(f"[!] Gemini απέτυχε ({e}) — fallback σε Haiku για αυτή την παρτίδα")
    return _resilient(SYSTEM_TRIAGE, payload, anthropic_key, 2000)


def classify(items: list[dict]) -> list[dict]:
    """Στάδιο Α σε όλα: κατηγορία/σοβαρότητα. Σύνοψη/γωνία μπαίνουν
    αργότερα με το enrich() μόνο σε όσα επιβιώσουν."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    gemini_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[!] Λείπει ANTHROPIC_API_KEY — τα items μένουν αταξινόμητα")
        for it in items:
            it.update({"category": "Αταξινόμητο", "severity": 2,
                       "summary_el": _clean(it["summary_raw"])[:200],
                       "angle": None, "turkish_narrative": False})
        return items

    if gemini_key:
        print("[i] Triage μέσω Gemini Flash-Lite (fallback: Haiku)")

    for i in range(0, len(items), BATCH):
        chunk = items[i:i + BATCH]
        payload = [{"id": it["id"], "side": it["side"],
                    "title": _clean(it["title"]),
                    "summary": _clean(it["summary_raw"])[:300]}
                   for it in chunk]
        results = _triage_batch(payload, api_key, gemini_key)
        for it in chunk:
            r = results.get(it["id"], {})
            it.update({
                "category": r.get("category", "Αταξινόμητο"),
                "severity": int(r.get("severity", 2)),
                "turkish_narrative": bool(r.get("turkish_narrative", False)),
                "summary_el": it.get("summary_el") or _clean(it["summary_raw"])[:200],
                "angle": it.get("angle"),
            })
        print(f"[+] Διαλογή {len(chunk)} items")
    return items


def enrich(items: list[dict]) -> None:
    """Στάδιο Β: ελληνική σύνοψη + γωνία μόνο για τα items που κρατάμε."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not items:
        return
    for i in range(0, len(items), BATCH):
        chunk = items[i:i + BATCH]
        payload = [{"id": it["id"], "title": _clean(it["title"]),
                    "summary": _clean(it["summary_raw"])[:600]}
                   for it in chunk]
        results = _resilient(SYSTEM_ENRICH, payload, api_key, 4000)
        for it in chunk:
            r = results.get(it["id"], {})
            if r.get("summary_el"):
                it["summary_el"] = r["summary_el"]
            it["angle"] = r.get("angle", it.get("angle"))
        print(f"[+] Εμπλουτίστηκαν {len(chunk)} items")
