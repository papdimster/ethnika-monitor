async def scrape_x_accounts(accounts: list, keywords: list, known_ids: set, hours_back: int = 6):
    """Scrapes given X accounts with logging"""
    api = API()
    fresh = []
    since = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).strftime("%Y-%m-%d")

    print(f"[X] Ξεκινά scraping {len(accounts)} accounts από {since}")

    try:
        for username in accounts:
            try:
                tweets = await gather(api.search(f"from:{username} since:{since}", limit=15))
                matched = 0

                for t in tweets:
                    iid = item_id(t.url)
                    if iid in known_ids:
                        continue

                    text = f"{t.rawContent} {t.user.username}"
                    hits = matches_keywords(text, keywords)

                    if hits:
                        matched += 1
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

                print(f"[X] @{username}: {len(tweets)} tweets, {matched} matched keywords")

            except Exception as e:
                print(f"[!] X @{username} error: {e}")
                continue

    except Exception as e:
        print(f"[!] X Scraper general error: {e}")

    print(f"[X] Συνολικά νέα X items: {len(fresh)}")
    return fresh
