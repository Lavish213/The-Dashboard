from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session_context
from integrations.reddit import fetch_matches


POLL_INTERVAL = int(os.environ.get("REDDIT_POLL_INTERVAL", "1800"))


async def run_once(session: AsyncSession) -> int:
    from models.reddit_match import RedditMatch

    matches = await asyncio.to_thread(fetch_matches, 25)
    if not matches:
        return 0

    new_count = 0
    for m in matches:
        existing = await session.execute(
            select(RedditMatch).where(RedditMatch.reddit_id == m["reddit_id"])
        )
        if existing.scalar_one_or_none():
            continue

        record = RedditMatch(
            reddit_id=m["reddit_id"],
            subreddit=m["subreddit"],
            title=m["title"],
            body=m["body"],
            url=m["url"],
            author=m["author"],
            created_utc=m["created_utc"],
            post_score=m["score"],
            intent_score=m["intent_score"],
            intent_label=m["intent_label"],
            status="new",
        )
        session.add(record)
        new_count += 1

    if new_count > 0:
        await session.commit()
        logger.info("reddit_monitor new_matches={}", new_count)

    return new_count


async def run_forever() -> None:
    logger.info("reddit_monitor starting poll_interval={}s", POLL_INTERVAL)
    while True:
        try:
            async with get_session_context() as session:
                count = await run_once(session)
                logger.info("reddit_monitor poll complete new={}", count)
        except Exception as error:
            logger.exception("reddit_monitor error={}", str(error))
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run_forever())