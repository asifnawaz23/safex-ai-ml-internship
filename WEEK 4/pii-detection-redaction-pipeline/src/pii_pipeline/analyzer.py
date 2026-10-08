"""
analyzer.py
-----------
Builds the two Presidio AnalyzerEngine configurations and normalises their
output.

baseline (Experiment A)
    RecognizerRegistry + load_predefined_recognizers(languages=["en"]) — the
    default supported recognisers of the installed presidio-analyzer — and the
    entity list PERSON, PHONE_NUMBER, EMAIL_ADDRESS, LOCATION.
improved (Experiment B)
    The same registry plus the custom recognisers in recognizers.py, and the
    entity list extended with CNIC, ADDRESS, POSTAL_CODE, CUSTOMER_ID.

Both use the same NLP engine: spaCy en_core_web_sm, built from Presidio's own
conf/default.yaml with only the model name overridden, so Presidio's NER label
mapping and ignore list stay intact. Presidio's default would load
en_core_web_lg (and download it if missing); this module refuses to do that
and raises if the small model is not installed.

Offline guard: Presidio's EmailRecognizer calls tldextract, whose default
extractor may fetch the public-suffix list from the internet. ``_force_offline``
replaces it with an extractor that uses only the snapshot bundled with
tldextract. No document text is ever sent anywhere.
"""

from __future__ import annotations

import functools
import logging
import platform
import re
from importlib import metadata
from pathlib import Path
from typing import Dict, List, Optional

from pii_pipeline import config
from pii_pipeline.evaluation import Prediction
from pii_pipeline.recognizers import (
    CUSTOM_RECOGNIZER_NAMES, NON_PII_CODE_REGEX, get_all_custom_recognizers,
)

logger = logging.getLogger(__name__)

MODES = ("baseline", "improved")

# Placeholders produced by the redactor; detections inside them are ignored so
# that re-running the pipeline on redacted text does not nest placeholders.
_PLACEHOLDER_RE = re.compile(
    "|".join(re.escape(v) for v in sorted(set(config.REDACTION_MAP.values()) | {config.FALLBACK_PLACEHOLDER},
                                          key=len, reverse=True))
)


def _force_offline() -> None:
    import tldextract.tldextract as _tld
    if getattr(_tld.TLD_EXTRACTOR, "_pii_pipeline_offline", False):
        return
    extractor = _tld.TLDExtract(suffix_list_urls=(), cache_dir=None, fallback_to_snapshot=True)
    extractor._pii_pipeline_offline = True
    _tld.TLD_EXTRACTOR = extractor


@functools.lru_cache(maxsize=1)
def build_nlp_engine():
    """spaCy NLP engine with the configured small model (never auto-downloads)."""
    import presidio_analyzer
    import spacy
    import yaml
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    model = config.NLP_MODEL
    if not spacy.util.is_package(model):
        raise RuntimeError(
            f"spaCy model '{model}' is not installed. Install the pinned wheel with: "
            r".\.venv\Scripts\python.exe -m pip install -r requirements.txt")
    conf_path = Path(presidio_analyzer.__file__).parent / "conf" / "default.yaml"
    with open(conf_path, "r", encoding="utf-8") as f:
        nlp_conf = yaml.safe_load(f)
    nlp_conf["models"] = [{"lang_code": config.LANGUAGE, "model_name": model}]
    engine = NlpEngineProvider(nlp_configuration=nlp_conf).create_engine()
    logger.info("NLP engine ready (spacy/%s)", model)
    return engine


@functools.lru_cache(maxsize=2)
def build_analyzer(mode: str = "improved"):
    """Return a cached AnalyzerEngine for 'baseline' or 'improved'."""
    if mode not in MODES:
        raise ValueError(f"mode must be 'baseline' or 'improved', got {mode!r}")
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry

    _force_offline()
    nlp_engine = build_nlp_engine()
    registry = RecognizerRegistry(supported_languages=[config.LANGUAGE])
    registry.load_predefined_recognizers(languages=[config.LANGUAGE], nlp_engine=nlp_engine)
    if mode == "improved":
        for rec in get_all_custom_recognizers():
            registry.add_recognizer(rec)
    engine = AnalyzerEngine(registry=registry, nlp_engine=nlp_engine,
                            supported_languages=[config.LANGUAGE])
    logger.info("AnalyzerEngine built (%s, %d recognisers)", mode, len(registry.recognizers))
    return engine


def get_entity_list(mode: str) -> List[str]:
    return config.entities_for_mode(mode)


def analyze_raw(engine, text: str, entities: Optional[List[str]] = None,
                score_threshold: Optional[float] = None) -> list:
    """Presidio RecognizerResults, sorted by start."""
    if score_threshold is None:
        score_threshold = config.SCORE_THRESHOLD
    results = engine.analyze(text=text, language=config.LANGUAGE, entities=entities,
                             score_threshold=score_threshold)
    return sorted(results, key=lambda r: (r.start, r.end))


def _recognizer_name(r) -> str:
    meta = getattr(r, "recognition_metadata", None) or {}
    return str(meta.get("recognizer_name", ""))


# Span hygiene for NER/regex spans that swallow neighbouring form syntax.
# Added after the first evaluation (dangerous-miss review); applied in BOTH
# modes because it is part of the shared post-processing, not a recogniser.
_FIELD_KEY_PREFIX = re.compile(r"^[A-Za-z][A-Za-z_\-]{1,20}=")
_LEADING_LABELS = re.compile(
    r"^(?:(?:customer\s+name|full\s+name|name|customer|subscriber|recipient|driver|from|to|"
    r"contact|attn|dear|hello|hi|mr|mrs|ms)\b\.?\s*[:=\-]?\s*)+", re.IGNORECASE)
_PERSON_STOP = re.compile(r"[|;\n\r()<>\[\]{}=@\d]")
_ADDRESS_STOP = re.compile(r"[|;\n\r<>\[\]{}=@]")
_EDGE_PUNCT = " \t,.:;-'\""


def _trim(text: str, p: Prediction) -> Optional[Prediction]:
    s, e = p.start, p.end
    span = text[s:e]
    if p.label == "EMAIL_ADDRESS":
        m = _FIELD_KEY_PREFIX.match(span)
        if m and "@" in span[m.end():]:
            s += m.end()
    elif p.label in ("PERSON", "ADDRESS"):
        if p.label == "PERSON":
            m = _LEADING_LABELS.match(span)
            if m and m.end() < len(span):
                s += m.end()
        stop = (_PERSON_STOP if p.label == "PERSON" else _ADDRESS_STOP).search(text, s, e)
        if stop:
            e = stop.start()
        while s < e and text[s] in _EDGE_PUNCT:
            s += 1
        while e > s and text[e - 1] in _EDGE_PUNCT:
            e -= 1
        if e - s < 2:
            return None
    if (s, e) == (p.start, p.end):
        return p
    return Prediction(s, e, p.label, p.score, p.raw_label, p.recognizer)


def _custom_rank(p: Prediction) -> int:
    return 0 if p.recognizer in CUSTOM_RECOGNIZER_NAMES else 1


def normalise_predictions(results, text: Optional[str] = None, mode: str = "baseline") -> List[Prediction]:
    """Apply the documented label mapping, span hygiene and de-duplication.

    1. Map each label through settings.json entities.label_mapping
       (e.g. LOCATION -> ADDRESS); drop labels outside the in-scope list.
    2. If ``text`` is given:
       a. drop detections lying entirely inside a redaction placeholder
          such as "[PHONE]" (keeps re-redaction idempotent);
       b. span hygiene: EMAIL_ADDRESS loses a "key=" prefix ("email=a@b.org");
          PERSON loses leading form labels ("Subscriber ", "Name: "); PERSON
          and ADDRESS spans end at the first field delimiter or line break
          (PERSON also at a digit); surrounding spaces/punctuation trimmed;
       c. improved mode only: drop detections inside a company code from the
          allow-list (recognizers.NON_PII_CODE_REGEX).
    3. Same span + same label: keep one (custom recogniser, then higher score,
       then recogniser name).
    4. A detection fully contained in another of the SAME label is dropped.
       Precedence: a custom recogniser's span beats a built-in one; otherwise
       the larger span wins (ties: higher score, then recogniser name).
       (Before the first-evaluation fixes the larger span always won, which
       let a built-in "(0321-1234567" override the custom "0321-1234567".)
    Overlaps between DIFFERENT labels are kept: evaluation counts them, and
    the redactor resolves them with REMOVE_INTERSECTIONS.
    """
    preds: List[Prediction] = []
    for r in results:
        label = config.canonical_label(r.entity_type)
        if label not in config.IN_SCOPE_ENTITIES:
            continue
        preds.append(Prediction(int(r.start), int(r.end), label, float(r.score),
                                r.entity_type, _recognizer_name(r)))
    if text is not None:
        ph_spans = [(m.start(), m.end()) for m in _PLACEHOLDER_RE.finditer(text)]
        preds = [p for p in preds
                 if not any(s <= p.start and p.end <= e for s, e in ph_spans)]
        preds = [q for q in (_trim(text, p) for p in preds) if q is not None]
        if mode == "improved":
            code_spans = [(m.start(), m.end()) for m in NON_PII_CODE_REGEX.finditer(text)]
            preds = [p for p in preds
                     if not any(s <= p.start and p.end <= e for s, e in code_spans)]

    ordered = sorted(preds, key=lambda p: (_custom_rank(p), -(p.end - p.start), -p.score, p.recognizer, p.start))
    kept: List[Prediction] = []
    for p in ordered:
        if any(k.label == p.label and k.start <= p.start and p.end <= k.end for k in kept):
            continue
        kept.append(p)
    # A built-in span that contains an already kept custom span of the same
    # label is dropped as well (custom precedence, rule 4).
    final = [p for p in kept
             if not (_custom_rank(p) == 1 and any(
                 k is not p and k.label == p.label and _custom_rank(k) == 0
                 and p.start <= k.start and k.end <= p.end for k in kept))]
    return sorted(final, key=lambda p: (p.start, p.end, p.label))


def analyze_text(engine, text: str, mode: str) -> List[Prediction]:
    """Analyse one document and return normalised predictions."""
    raw = analyze_raw(engine, text, entities=get_entity_list(mode))
    return normalise_predictions(raw, text, mode)


def _version(pkg: str) -> str:
    try:
        return metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return "not installed"


def describe_engine(engine, mode: str) -> Dict[str, object]:
    """Engine metadata recorded with every experiment run."""
    requested = get_entity_list(mode)
    supported = sorted(engine.get_supported_entities(config.LANGUAGE))
    nlp = engine.nlp_engine
    model_meta = {}
    try:
        model_meta = nlp.nlp[config.LANGUAGE].meta
    except Exception:  # pragma: no cover - metadata only
        pass
    return {
        "mode": mode,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "presidio_analyzer_version": _version("presidio-analyzer"),
        "presidio_anonymizer_version": _version("presidio-anonymizer"),
        "spacy_version": _version("spacy"),
        "nlp_engine": type(nlp).__name__,
        "nlp_model": model_meta.get("lang", "en") + "_" + model_meta.get("name", "?"),
        "nlp_model_version": model_meta.get("version", "?"),
        "ner_config_source": config.get("presidio.ner_config_source"),
        "language": config.LANGUAGE,
        "score_threshold": config.SCORE_THRESHOLD,
        "requested_entities": requested,
        "requested_but_unsupported": sorted(set(requested) - set(supported)),
        "supported_entities": supported,
        "recognizers": sorted(r.name for r in engine.registry.recognizers),
        "custom_recognizers": sorted(r.name for r in get_all_custom_recognizers()) if mode == "improved" else [],
        "label_mapping": config.LABEL_MAPPING,
        "context_enhancer": type(engine.context_aware_enhancer).__name__,
        "tldextract_offline_snapshot": True,
    }
