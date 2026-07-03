import json
import logging
import re
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from core.registry import ChatPlatform
from core import config
from database.models import IncrementalAnalysis, ChatMessage, Alert
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


def _format_conversation_with_ids(
    db: Session, platform: ChatPlatform, server_id: str, since_message_count: int
) -> tuple[str, int]:
    """
    Format conversation with message IDs prefixed to each message.
    Returns formatted conversation and total message count.
    """
    # Get all messages for this server
    all_messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.platform == platform,
            ChatMessage.server_id == server_id,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    total_count = len(all_messages)

    # Skip already processed messages, and get only new ones
    messages_to_process = all_messages[since_message_count:]

    lines = ["Conversation:"]
    for msg in messages_to_process:
        lines.append(f"[{msg.id}] {msg.content}")

    conversation = "\n".join(lines)
    return conversation, total_count


def _extract_json(raw: str) -> dict:
    """Extract JSON from response, handling markdown code fences."""
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    return json.loads(text)


def _get_or_create_incremental_analysis(
    db: Session,
    platform: ChatPlatform,
    server_id: str,
) -> IncrementalAnalysis:
    """Get or create an IncrementalAnalysis record."""
    record = (
        db.query(IncrementalAnalysis)
        .filter(
            IncrementalAnalysis.platform == platform,
            IncrementalAnalysis.server_id == server_id,
        )
        .first()
    )

    if record is None:
        record = IncrementalAnalysis(
            platform=platform,
            server_id=server_id,
            detected_stages=[],
            last_processed_message_count=0,
            unprocessed_message_count=0,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return record


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


def should_run_analysis(pending_message_count: int) -> bool:
    """Check if we should run analysis based on the number of pending new messages."""
    return pending_message_count >= 3


async def get_incremental_analysis(
    db: Session,
    platform: ChatPlatform,
    server_id: str,
) -> IncrementalAnalysisResponse | None:
    """
    Perform incremental grooming analysis.

    Returns only newly detected stages, or None if analysis failed.
    """
    incremental = _get_or_create_incremental_analysis(db, platform, server_id)

    # Get undetected stages
    undetected = _get_undetected_stages(incremental.detected_stages)
    if not undetected:
        # All stages already detected
        return IncrementalAnalysisResponse(new_stages=[])

    try:
        # Format conversation with only new messages since the last analysis.
        conversation, total_message_count = _format_conversation_with_ids(
            db, platform, server_id, incremental.last_processed_message_count
        )
        new_message_count = (
            total_message_count - incremental.last_processed_message_count
        )

        if not should_run_analysis(new_message_count):
            return None

        # Call LLM for incremental analysis on only the pending messages.
        response = await _call_groq_incremental(conversation, undetected)

        # Update detected stages and last processed count.
        # Convert detected_stages to set of stage names for comparison
        detected_stage_names = {
            stage.get("stage") if isinstance(stage, dict) else stage 
            for stage in incremental.detected_stages
        }
        
        # Build new stages list with full objects
        new_stages_list = list(incremental.detected_stages) if incremental.detected_stages else []
        for new_stage in response.new_stages:
            if new_stage.stage not in detected_stage_names:
                new_stages_list.append({
                    "stage": new_stage.stage,
                    "confidence": new_stage.confidence,
                    "message_id": new_stage.message_id,
                })
        
        # Reassign to trigger SQLAlchemy change detection
        incremental.detected_stages = new_stages_list

        incremental.last_processed_message_count = total_message_count
        incremental.unprocessed_message_count = 0
        incremental.updated_at = datetime.now(UTC)

        db.commit()
        db.refresh(incremental)
        
        # Also update the Alert object if it exists
        alert = (
            db.query(Alert)
            .filter(
                Alert.platform == platform,
                Alert.server_id == server_id,
            )
            .first()
        )
        if alert:
            alert.detected_stages = new_stages_list
            db.commit()

        return response

    except Exception:
        logger.exception(
            "Failed to generate incremental grooming analysis for server %s on %s",
            server_id,
            platform.value,
        )
        return None


def increment_unprocessed_count(
    db: Session,
    platform: ChatPlatform,
    server_id: str,
) -> None:
    """Increment the unprocessed message count for a server."""
    incremental = _get_or_create_incremental_analysis(db, platform, server_id)
    incremental.unprocessed_message_count += 1
    incremental.updated_at = datetime.now(UTC)
    db.commit()


def get_detected_stages(
    db: Session,
    platform: ChatPlatform,
    server_id: str,
) -> list:
    """Get list of already-detected stages for a server."""
    incremental = _get_or_create_incremental_analysis(db, platform, server_id)
    return incremental.detected_stages
