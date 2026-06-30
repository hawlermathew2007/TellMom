import logging
from typing import Tuple, List
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

from config import settings

logger = logging.getLogger(__name__)

# Global model cache
_model = None
_tokenizer = None


def load_model():
    """Load the fine-tuned grooming detection model."""
    global _model, _tokenizer

    if _model is not None:
        return _model, _tokenizer

    logger.info(f"[+] Loading grooming detection model from {settings.model_path}...")

    try:
        _tokenizer = AutoTokenizer.from_pretrained(settings.model_path)
        _model = AutoModelForSequenceClassification.from_pretrained(
            settings.model_path,
            num_labels=2  # Binary: grooming (1) vs. safe (0)
        )
        _model.eval()

        # Move to device
        device = torch.device(settings.device)
        _model.to(device)

        logger.info(f"[+] Model loaded successfully on device: {settings.device}")
    except Exception as e:
        logger.error(f"[*] Failed to load model: {e}")
        raise

    return _model, _tokenizer


def predict_grooming_risk(
    text: str,
    threshold: float = settings.risk_threshold
) -> Tuple[float, float, str, List[str]]:
    """
    Predict grooming risk for a message.

    Returns:
        - risk_score (0.0-1.0): Probability of grooming
        - confidence (0.0-1.0): Model confidence in prediction
        - explanation (str): Why it was flagged
        - flagged_phrases (list): Suspicious phrases identified
    """
    model, tokenizer = load_model()
    device = torch.device(settings.device)

    # Tokenize
    inputs = tokenizer(
        text,
        truncation=True,
        max_length=512,
        return_tensors="pt",
        padding=True
    ).to(device)

    # Inference
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=1)[0]

    # Extract predictions
    risk_score = float(probs[1].cpu().numpy())  # Probability of grooming class
    confidence = float(max(probs).cpu().numpy())

    # Explanation
    explanation = _generate_explanation(text, risk_score)
    flagged_phrases = _extract_flagged_phrases(text)

    logger.debug(
        f"[+] Analysis: score={risk_score:.2f}, confidence={confidence:.2f}, "
        f"phrases={flagged_phrases}"
    )

    return risk_score, confidence, explanation, flagged_phrases


def _generate_explanation(text: str, risk_score: float) -> str:
    """Generate explanation for why message was flagged."""
    if risk_score < 0.3:
        return "Message appears safe."
    elif risk_score < 0.6:
        return "Message contains some cautionary language. Review recommended."
    elif risk_score < 0.8:
        return "Message shows patterns consistent with grooming behavior."
    else:
        return "[*] URGENT: Message contains high-risk grooming indicators."


def _extract_flagged_phrases(text: str) -> List[str]:
    """
    Extract phrases that match known grooming patterns.

    This is a simple keyword-based approach.
    For production, use more sophisticated NLP.
    """
    # Known grooming keywords (case-insensitive)
    grooming_keywords = [
        "secret", "keep quiet", "private", "don't tell",
        "meet", "picture", "camera", "alone",
        "mature", "special", "unique", "different",
        "nobody understands", "trust me", "i like you",
        "parents won't understand", "age doesn't matter",
    ]

    text_lower = text.lower()
    found_phrases = []

    for keyword in grooming_keywords:
        if keyword in text_lower:
            found_phrases.append(keyword)

    return found_phrases
