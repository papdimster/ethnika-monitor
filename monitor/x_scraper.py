"""X/Twitter Scraper για εθνικά θέματα - χωρίς επίσημο API"""
import asyncio
from datetime import datetime, timezone, timedelta
from twscrape import API, gather
from twscrape.logger import set_log_level

from monitor.collector import item_id, matches_keywords

set_log_level("ERROR")
async def scrape_x_accounts(accounts: list, keywords: list, known_ids: set, hours_back: int = 6):
    """Scrapes given X accounts"""
    api = API()
    fresh = []
    since = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).strftime("%Y-%m-%d")

    try:
        for username in accounts:
            try:
                tweets = await gather(api.search(f"from:{username} since:{since}", limit=15))
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
                            "side": "neutral",
                            "lang": "el" if any(x in t.user.username.lower() for x in ["greece", "hellenic"]) else 
                                   "tr" if any(x in t.user.username.lower() for x in ["tc", "turkish"]) else "en",
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
