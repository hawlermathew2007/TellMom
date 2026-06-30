import json
import logging
import re

import httpx
from sqlalchemy.orm import Session

from adapters.base import ChatPlatform
from core import config
from core.cache import explanation_cache
from database.models import FlagExplanation
from schemas.grooming import GroomingAnalysis
from services.grooming_prompt import GROOMING_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


def _format_conversation(
    platform: str,
    server_id: str,
    flagged_user_id: str,
    chat_group: dict[str, list[str]],
) -> str:
    lines = [
        f"Platform: {platform}",
        f"Server ID: {server_id}",
        f"Flagged user ID: {flagged_user_id}",
        "",
        "Conversation:",
    ]
    for user_id, messages in chat_group.items():
        marker = " (flagged user)" if user_id == flagged_user_id else ""
        lines.append(f"\nUser {user_id}{marker}:")
        for message in messages:
            lines.append(f"  - {message}")
    return "\n".join(lines)


def _extract_json(raw: str) -> dict:
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    return json.loads(text)


def _lookup_db(
    db: Session,
    platform: ChatPlatform,
    platform_user_id: str,
) -> GroomingAnalysis | None:
    row = (
        db.query(FlagExplanation)
        .filter(
            FlagExplanation.platform == platform,
            FlagExplanation.platform_user_id == platform_user_id,
        )
        .first()
    )
    if row is None:
        return None
    return GroomingAnalysis.model_validate(row.explanation)


def lookup_explanation_payload(
    db: Session,
    platform: ChatPlatform,
    platform_user_id: str,
) -> dict | None:
    analysis = _lookup_db(db, platform, platform_user_id)
    if analysis is None:
        return None
    return analysis.model_dump(mode="json")


def _save_db(
    db: Session,
    platform: ChatPlatform,
    platform_user_id: str,
    analysis: GroomingAnalysis,
) -> None:
    existing = (
        db.query(FlagExplanation)
        .filter(
            FlagExplanation.platform == platform,
            FlagExplanation.platform_user_id == platform_user_id,
        )
        .first()
    )
    payload = analysis.model_dump(mode="json")
    if existing:
        existing.explanation = payload
    else:
        db.add(
            FlagExplanation(
                platform=platform,
                platform_user_id=platform_user_id,
                explanation=payload,
            )
        )
    db.commit()


async def _call_groq(
    platform: str,
    server_id: str,
    flagged_user_id: str,
    chat_group: dict[str, list[str]],
) -> GroomingAnalysis:
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")

    conversation = _format_conversation(platform, server_id, flagged_user_id, chat_group)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            GROQ_CHAT_URL,
            headers={
                "Authorization": f"Bearer {config.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": GROOMING_SYSTEM_PROMPT},
                    {"role": "user", "content": conversation},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        body = response.json()

    content = body["choices"][0]["message"]["content"]
    parsed = _extract_json(content)
    return GroomingAnalysis.model_validate(parsed)


async def get_or_generate_explanation(
    db: Session,
    platform: ChatPlatform,
    flagged_user_id: str,
    server_id: str,
    chat_group: dict[str, list[str]],
) -> GroomingAnalysis | None:
    cache_key = (platform.value, flagged_user_id)

    cached = explanation_cache.get(cache_key)
    if cached is not None:
        return cached

    db_cached = _lookup_db(db, platform, flagged_user_id)
    if db_cached is not None:
        explanation_cache.set(cache_key, db_cached)
        return db_cached

    try:
        analysis = await _call_groq(
            platform.value,
            server_id,
            flagged_user_id,
            chat_group,
        )
    except Exception:
        logger.exception(
            "Failed to generate grooming explanation for %s on %s",
            flagged_user_id,
            platform.value,
        )
        return None

    explanation_cache.set(cache_key, analysis)
    _save_db(db, platform, flagged_user_id, analysis)
    return analysis
