import json
import logging
import re
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from core.cache import message_cache, sync_message_cache
from core import config
from database.models import IncrementalAnalysis, Alert
from schemas.grooming import IncrementalAnalysisResponse, NewlyDetectedStage

logger = logging.getLogger(__name__)

# All grooming stages in order
ALL_STAGES = [
    "Victim Selection",
    "Access and Relationship Building",
    "Trust Development",
    "Isolation",
    "Boundary Testing",
    "Desensitization",
    "Maintaining Control",
]


def _extract_json(raw: str) -> dict:
    """Extract JSON from response, handling markdown code fences."""
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    return json.loads(text)


def _get_incremental_analysis(db: Session, alert_id: str) -> IncrementalAnalysis | None:
    incremental = (
        db.query(IncrementalAnalysis)
        .filter(IncrementalAnalysis.alert_id == alert_id)
        .first()
    )
    return incremental


def _get_undetected_stages(detected_stages: list) -> list[str]:
    """Return list of stages that have not yet been detected."""
    # detected_stages is now a list of dicts with 'stage', 'confidence', 'message_id'
    detected_stage_names = {
        stage.get("stage") if isinstance(stage, dict) else stage
        for stage in detected_stages
    }
    return [s for s in ALL_STAGES if s not in detected_stage_names]


def _build_incremental_prompt(undetected_stages: list[str]) -> str:
    """Build a prompt with only undetected stages listed."""
    stages_text = "\n".join(f"- {stage}" for stage in undetected_stages)

    return f"""
    You are analyzing a conversation for grooming behaviors. Some stages have already been detected and should be IGNORED.

    Only evaluate these remaining stages:
    {stages_text}

    For each stage, if observed, return the message ID that best supports it.

    Return JSON in this format:
    {{"new_stages": [{{"stage": "Stage Name", "confidence": "High", "message_id": 123}}]}}

    Return empty array if no stages detected: {{"new_stages": []}}
    """


async def _call_groq_incremental(
    conversation: str,
    undetected_stages: list[str],
) -> IncrementalAnalysisResponse:
    """Call Groq to analyze only undetected stages."""
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")

    prompt = _build_incremental_prompt(undetected_stages)
    GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

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
                    {
                        "role": "system",
                        "content": prompt,
                    },
                    {
                        "role": "user",
                        "content": conversation,
                    },
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        body = response.json()

    content = body["choices"][0]["message"]["content"]
    parsed = _extract_json(content)

    # Validate response structure
    if "new_stages" not in parsed:
        logger.warning(f"Unexpected response format: {parsed}")
        return IncrementalAnalysisResponse(new_stages=[])

    # Convert to NewlyDetectedStage objects
    new_stages = []
    for stage_data in parsed.get("new_stages", []):
        try:
            new_stages.append(NewlyDetectedStage.model_validate(stage_data))
        except Exception as e:
            logger.warning(f"Failed to parse stage data: {stage_data}, error: {e}")

    return IncrementalAnalysisResponse(new_stages=new_stages)


# TODO: fix this one though, outdated since last update
async def get_incremental_analysis(
    db: Session, alert: Alert
) -> IncrementalAnalysisResponse | None:
    """
    Perform incremental grooming analysis.

    Returns only newly detected stages, or None if analysis failed.
    """
    # Format conversation with only new messages since the last analysis.
    incremental = _get_incremental_analysis(db, str(alert.id))

    if incremental is None:
        logger.warning(f"Stray alert with no analysis associated: {alert.id}")
        return None

    # Get undetected stages
    undetected = _get_undetected_stages(incremental.detected_stages)
    if not undetected:
        # All stages already detected
        return IncrementalAnalysisResponse(new_stages=[])

    try:
        if incremental.unprocessed_message_count < 3:
            return

        sync_message_cache(db, alert.platform, alert.server_id)
        cache_entry = message_cache.get(alert.server_id)
        assert cache_entry is not None
        msg_map = cache_entry["map"]

        lines = ["Conversation:"]
        messages = msg_map[alert.child_account_id] + msg_map[alert.target_id]
        messages = messages[incremental.last_processed_count :]

        for msg in messages:
            lines.append(f"[{msg.id}] {msg.content}")
        conversation = "\n".join(lines)

        # Call LLM for incremental analysis on only the pending messages.
        response = await _call_groq_incremental(conversation, undetected)

        # Update detected stages and last processed count.
        # Convert detected_stages to set of stage names for comparison
        detected_stage_names = {
            stage.get("stage") if isinstance(stage, dict) else stage
            for stage in incremental.detected_stages
        }

        # Build new stages list with full objects
        new_stages_list = (
            list(incremental.detected_stages) if incremental.detected_stages else []
        )
        for new_stage in response.new_stages:
            if new_stage.stage not in detected_stage_names:
                new_stages_list.append(
                    {
                        "stage": new_stage.stage,
                        "confidence": new_stage.confidence,
                        "message_id": new_stage.message_id,
                    }
                )

        # Reassign to trigger SQLAlchemy change detection
        incremental.detected_stages = new_stages_list
        incremental.last_processed_count += len(messages)
        incremental.unprocessed_message_count = 0
        incremental.updated_at = datetime.now(UTC)

        db.commit()
        db.refresh(incremental)

        # Also update the Alert object if it exists
        alert.detected_stages = new_stages_list
        db.commit()

        return response

    except Exception:
        logger.exception(
            "Failed to generate incremental grooming analysis for server %s on %s",
            alert.server_id,
            alert.platform.value,
        )
        return None


def increment_unprocessed_count(db: Session, alert_id: str) -> None:
    """Increment the unprocessed message count for a server."""
    incremental = _get_incremental_analysis(db, alert_id)
    assert incremental is not None
    incremental.unprocessed_message_count += 1
    incremental.updated_at = datetime.now(UTC)
    db.commit()
