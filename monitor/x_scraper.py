"""X/Twitter Scraper για εθνικά θέματα - χωρίς επίσημο API"""
import asyncio
from datetime import datetime, timezone, timedelta
from twscrape import API, gather
from twscrape.logger import set_log_level

from monitor.collector import item_id, matches_keywords

set_log_level("ERROR")

async def scrape_x_accounts(keywords: list, known_ids: set, hours_back: int = 6):
    """Scrapes specific accounts + keyword searches"""
    api = API()
    
    # TODO: Εδώ θα προσθέσεις τα accounts σου (θα τα βάλουμε σε config)
    accounts = [
        # Ελληνικά επίσημα / αναλυτές
        "HellenicNavy", "HellenicAirForce", "mod_greece", "GreeceMFA",
        # Τουρκικά
        "tcsavunma", "TC_Disisleri", "TurkishNavy", 
        # Ισραηλινά
        "IDF", "IsraelMFA", 
        # Άλλα χρήσιμα
        # "NATO", "EU_EEAS", κλπ.
    ]
    
    fresh = []
    since = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).strftime("%Y-%m-%d")
    
    try:
        for username in accounts:
            try:
                tweets = await gather(api.search(f"from:{username} since:{since}", limit=20))
                for t in tweets:
                    iid = item_id(t.url)
                    if iid in known_ids:
                        continue
                        
                    text = f"{t.rawContent} {t.user.username}"
                    hits = matches_keywords(text, keywords)
                    
                    if hits:
                        fresh.append({
                            "id": iid,
                            "title": t.rawContent[:140] + "..." if len(t.rawContent) > 140 else t.rawContent,
                            "link": t.url,
                            "summary_raw": t.rawContent,
                            "source": f"X @{t.user.username}",
                            "side": "neutral",  # μπορείς να βάλεις logic
                            "lang": "el" if "Greece" in t.user.username else "tr" if "TC" in t.user.username or "Turkish" in t.user.username else "en",
                            "published": t.date.isoformat(),
                            "collected": datetime.now(timezone.utc).isoformat(),
                            "keywords_hit": hits[:8],
                            "x_data": {"username": t.user.username, "likes": t.likeCount, "retweets": t.retweetCount}
                        })
            except Exception as e:
                print(f"[!] X @{username}: {e}")
                continue
                
    except Exception as e:
        print(f"[!] X Scraper error: {e}")
    
    return fresh
