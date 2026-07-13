"""Ειδοποιήσεις Telegram για items υψηλής σοβαρότητας (ΣΟΒ >= 4)."""
import html
import json
import os
import urllib.request

ALERT_MIN_SEVERITY = 4
MAX_ALERTS_PER_RUN = 8   # ασφάλεια για το πρώτο τρέξιμο

SEV_ICON = {4: "🟠", 5: "🔴"}


def _send(token: str, chat_id: str, text: str) -> bool:
    body = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("ok", False)
    except Exception as e:
        print(f"[!] Telegram send: {e}")
        return False


def send_alerts(items: list[dict]) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return  # δεν έχουν ρυθμιστεί ειδοποιήσεις — συνεχίζουμε σιωπηλά

    hot = [it for it in items if it.get("severity", 0) >= ALERT_MIN_SEVERITY]
    hot = hot[:MAX_ALERTS_PER_RUN]
    sent = 0
    for it in hot:
        icon = SEV_ICON.get(it["severity"], "🟠")
        text = (
            f"{icon} <b>ΣΟΒ {it['severity']} · {html.escape(it.get('category', ''))}</b>\n"
            f"<b>{html.escape(it['title'][:200])}</b>\n\n"
            f"{html.escape(it.get('summary_el', '')[:500])}\n\n"
            f"{it['link']}"
        )
        if _send(token, chat_id, text):
            sent += 1
    if hot:
        print(f"[+] Telegram alerts: στάλθηκαν {sent}/{len(hot)}")
