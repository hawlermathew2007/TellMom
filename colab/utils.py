from datetime import datetime, timezone
from .config import RISK_THRESHOLDS


def log_section(logger, title: str) -> None:
    line = "=" * 60
    logger.info(line)
    logger.info(title)
    logger.info(line)


def clean_text(text: str) -> str:
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    tokens = text.split()
    filtered = [
        tok
        for tok in tokens
        if sum(1 for c in tok if ord(c) < 128) / max(len(tok), 1) >= 0.70
    ]
    return " ".join(filtered).strip()


def probability_to_risk(probability: float) -> str:
    if probability >= RISK_THRESHOLDS["high"]:
        return "high"
    if probability >= RISK_THRESHOLDS["medium"]:
        return "medium"
    return "normal"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
