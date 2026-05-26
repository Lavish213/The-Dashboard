from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from security.auth import get_current_active_user

router = APIRouter(dependencies=[Depends(get_current_active_user)])

ANGELO_VOICE = """
You write social media content for Angelo Washington, owner of San Joaquin House Buyers in Stockton/Lodi CA.

Angelo's voice rules:
- casual Central Valley / 209 style
- short sentences, no fluff
- contractions always (it's, don't, we'll)
- lowercase sometimes
- local references (209, Stockton, Lodi, Central Valley)
- "we" for the business, not "I"
- fragments are fine
- friendly but not fake
- real estate savvy but not showy
- NEVER use: "absolutely", "certainly", "valuable", "dive into", "it's worth noting"

Generate exactly 3 Facebook group post variants. Each should:
- be 2-4 sentences
- have a clear CTA (comment OFFER, DM me, etc.)
- sound like a real person from the 209 wrote it
- be meaningfully different from each other

Return ONLY a JSON array of 3 strings, no other text.
"""


async def _fetch_url_content(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; bot)"}
            res = await client.get(url, headers=headers)
            text = res.text[:3000]
            return text
    except Exception:
        return ""


async def _call_claude(prompt: str) -> list[str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return [
            "thinking about selling your place in Stockton? we buy as-is, cash, fast. DM me your address",
            "hey 209 — if your house needs work and you just want out, we handle it. comment OFFER below",
            "we just closed another one in the area. if you're ready to sell without the hassle, reach out today",
        ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 800,
                "system": ANGELO_VOICE,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        data = res.json()
        text = data["content"][0]["text"].strip()
        import json
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)


@router.post("/process")
async def process_curator(
    body: dict,
    session: AsyncSession = Depends(get_session),
) -> dict:
    input_type = body.get("type", "text")
    content = body.get("content", "")
    url = body.get("url", "")

    extracted = content

    if url and input_type in ("url", "article", "tiktok", "instagram", "youtube"):
        fetched = await _fetch_url_content(url)
        if fetched:
            extracted = f"URL: {url}\n\nContent preview:\n{fetched[:1500]}"
        else:
            extracted = f"URL: {url}\n\nTopic: {content}"

    prompt = f"""Here is content to rewrite as Facebook group posts for motivated sellers in Stockton/Lodi CA:

{extracted}

Generate 3 post variants targeting homeowners who might want to sell fast for cash."""

    try:
        variants = await _call_claude(prompt)
    except Exception:
        variants = [
            "thinking about selling your place in Stockton? we buy as-is, cash, fast. DM me your address",
            "hey 209 — if your house needs work and you just want out, we handle it. comment OFFER below",
            "we just closed another one in the area. if you're ready to sell without the hassle, reach out today",
        ]

    return {
        "status": "ok",
        "input_type": input_type,
        "variants": variants,
        "source_url": url or None,
    }