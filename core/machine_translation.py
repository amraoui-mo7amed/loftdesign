"""Optional machine translation (DeepL). Used only to pre-fill translation
fields that a person then checks; nothing is published without a click."""
import requests
from django.conf import settings

DEEPL_LANG = {"fr": "FR", "en": "EN-GB", "ar": "AR"}


def available():
    return bool(getattr(settings, "DEEPL_API_KEY", ""))


def translate(texts, target, source=None):
    """List of strings -> list of strings in `target`. Raises RuntimeError on failure."""
    if not available():
        raise RuntimeError("machine translation is not configured")
    texts = [t or "" for t in texts]
    if not any(texts):
        return texts
    data = {"text": texts, "target_lang": DEEPL_LANG.get(target, target.upper())}
    if source:
        data["source_lang"] = DEEPL_LANG.get(source, source.upper()).split("-")[0]
    try:
        r = requests.post(settings.DEEPL_API_URL, data=data, timeout=20,
                          headers={"Authorization": f"DeepL-Auth-Key {settings.DEEPL_API_KEY}"})
        r.raise_for_status()
        return [t["text"] for t in r.json()["translations"]]
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise RuntimeError(f"machine translation failed: {exc}") from exc
