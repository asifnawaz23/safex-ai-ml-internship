"""
config.py — loads and exposes project-wide configuration from config/settings.json.

The label mapping defined here is the single source of truth used by the
analyzer post-processing, the anonymizer operators, the evaluation and the
reports.
"""
import json
from pathlib import Path

# Project root: src/pii_pipeline/config.py -> parents[2]
_ROOT = Path(__file__).resolve().parents[2]
_SETTINGS_PATH = _ROOT / "config" / "settings.json"


def load_settings() -> dict:
    """Load settings.json and return it as a dict."""
    if not _SETTINGS_PATH.exists():
        raise FileNotFoundError(f"Settings file not found: {_SETTINGS_PATH}")
    with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_settings = load_settings()


def get(key_path: str, default=None):
    """Retrieve a nested setting using dot notation, e.g. get('dataset.random_seed')."""
    node = _settings
    for k in key_path.split("."):
        if not isinstance(node, dict) or k not in node:
            return default
        node = node[k]
    return node


def get_path(key_path: str) -> Path:
    """Return a setting value as a Path resolved relative to the project root."""
    val = get(key_path)
    if val is None:
        raise KeyError(f"Setting not found: {key_path}")
    return _ROOT / val


def dataset_path(file_key: str) -> Path:
    """Path of a dataset file, e.g. dataset_path('documents_file')."""
    return get_path("dataset.output_dir") / get(f"dataset.{file_key}")


ROOT = _ROOT
SEED = get("dataset.random_seed", 42)
RECORD_COUNT = get("dataset.record_count", 850)
LANGUAGE = get("presidio.language", "en")
NLP_MODEL = get("presidio.nlp_model", "en_core_web_sm")
SCORE_THRESHOLD = get("presidio.score_threshold", 0.35)
IN_SCOPE_ENTITIES = list(get("entities.in_scope", []))
LABEL_MAPPING = dict(get("entities.label_mapping", {}))
REDACTION_MAP = dict(get("entities.redaction_map", {}))
FALLBACK_PLACEHOLDER = get("entities.fallback_placeholder", "[REDACTED]")
ALLOWED_EMAIL_DOMAINS = tuple(get("privacy.allowed_email_domains", []))
HMAC_KEY_ENV = get("privacy.hmac_key_env", "PII_PIPELINE_HMAC_KEY")
MAX_DOCUMENT_CHARS = get("privacy.max_document_chars", 50_000)
LOG_RAW_TEXT = bool(get("logging.log_raw_text", False))


def canonical_label(label: str) -> str:
    """Map a Presidio/recogniser label to the dataset's canonical entity type.

    Labels not in the mapping are returned unchanged (and are out of scope).
    """
    return LABEL_MAPPING.get(label, label)


def entities_for_mode(mode: str) -> list:
    """Entity types requested from Presidio for 'baseline' or 'improved'."""
    if mode not in ("baseline", "improved"):
        raise ValueError(f"mode must be 'baseline' or 'improved', got {mode!r}")
    return list(get(f"entities.{mode}_entities"))
