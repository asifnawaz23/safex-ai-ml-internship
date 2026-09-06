from functools import lru_cache
from typing import Dict, Any
from .config import MODEL_NAME, INTENTS, RESPONSES, CONFIDENCE_THRESHOLD, MAX_INPUT_LENGTH


class InputValidationError(ValueError):
    """Raised when a user message does not meet validation rules."""


def clean_input(user_text: str) -> str:
    if not isinstance(user_text, str):
        raise InputValidationError("Input must be text.")

    cleaned = " ".join(user_text.strip().split())

    if not cleaned:
        raise InputValidationError("Message cannot be empty.")
    if len(cleaned) < 3:
        raise InputValidationError("Message is too short. Please describe the problem.")
    if len(cleaned) > MAX_INPUT_LENGTH:
        raise InputValidationError(
            f"Message is too long. Please keep it under {MAX_INPUT_LENGTH} characters."
        )

    return cleaned


@lru_cache(maxsize=1)
def get_classifier():
    """
    Load the Hugging Face zero-shot classification pipeline once.
    First run downloads the pretrained model from Hugging Face.
    """
    from transformers import pipeline

    return pipeline(
        "zero-shot-classification",
        model=MODEL_NAME,
        device=-1,
    )


def classify_query(user_text: str) -> Dict[str, Any]:
    text = clean_input(user_text)
    classifier = get_classifier()

    result = classifier(
        text,
        candidate_labels=INTENTS,
        hypothesis_template="This customer support request is about {}.",
        multi_label=False,
    )

    intent = result["labels"][0]
    confidence = float(result["scores"][0])

    if confidence < CONFIDENCE_THRESHOLD:
        return {
            "input": text,
            "intent": "general account question",
            "confidence": round(confidence, 4),
            "response": (
                "I'm not fully confident about the request category. Please rephrase your question "
                "with a little more detail, or contact human support for account-specific help."
            ),
            "fallback": True,
        }

    return {
        "input": text,
        "intent": intent,
        "confidence": round(confidence, 4),
        "response": RESPONSES[intent],
        "fallback": False,
    }
