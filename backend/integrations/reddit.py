from __future__ import annotations

import os
from typing import Any

REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "karpathys:sjhb-monitor:v1.0 (by /u/your_username)")

SUBREDDITS = [
    "Stockton",
    "Lodi",
    "SanJoaquin",
    "realestate",
    "personalfinance",
    "landlord",
    "RealEstate",
    "FirstTimeHomeBuyer",
    "divorce",
    "foreclosure",
]

KEYWORDS = [
    "sell my house",
    "selling my house",
    "need to sell",
    "sell fast",
    "cash buyer",
    "cash offer",
    "we buy houses",
    "tired landlord",
    "inherited property",
    "behind on mortgage",
    "facing foreclosure",
    "foreclosure",
    "probate",
    "divorce house",
    "sell as-is",
    "as-is",
    "motivated seller",
    "moving fast",
    "need to move",
    "can't afford repairs",
    "tax lien",
    "delinquent",
]


def score_intent(title: str, body: str) -> tuple[int, str]:
    text = (title + " " + body).lower()
    score = 0
    matched = []

    hot_keywords = [
        "sell my house", "need to sell fast", "cash buyer",
        "cash offer", "we buy houses", "facing foreclosure",
        "behind on mortgage", "tax lien"
    ]
    warm_keywords = [
        "tired landlord", "inherited", "probate", "divorce",
        "sell fast", "motivated", "as-is", "moving fast"
    ]

    for kw in hot_keywords:
        if kw in text:
            score += 4
            matched.append(kw)

    for kw in warm_keywords:
        if kw in text:
            score += 2
            matched.append(kw)

    if score >= 6:
        label = "hot"
    elif score >= 3:
        label = "warm"
    elif score > 0:
        label = "cold"
    else:
        label = "none"

    return score, label


def keyword_matches(title: str, body: str) -> bool:
    text = (title + " " + body).lower()
    return any(kw in text for kw in KEYWORDS)


def get_reddit_client():
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        return None
    import praw
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        read_only=True,
    )


def fetch_matches(limit: int = 25) -> list[dict[str, Any]]:
    reddit = get_reddit_client()
    if not reddit:
        return []

    matches = []
    for sub_name in SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)
            for post in subreddit.new(limit=limit):
                title = post.title or ""
                body = getattr(post, "selftext", "") or ""
                if not keyword_matches(title, body):
                    continue
                score, label = score_intent(title, body)
                if label == "none":
                    continue
                matches.append({
                    "reddit_id": post.id,
                    "subreddit": sub_name,
                    "title": title,
                    "body": body[:500],
                    "url": f"https://reddit.com{post.permalink}",
                    "author": str(post.author) if post.author else "deleted",
                    "created_utc": int(post.created_utc),
                    "score": post.score,
                    "intent_score": score,
                    "intent_label": label,
                })
        except Exception:
            continue

    matches.sort(key=lambda x: x["intent_score"], reverse=True)
    return matches