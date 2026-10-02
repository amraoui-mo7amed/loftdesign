"""Translations of database content (product names, descriptions, categories…).

Each translatable model keeps its main text in its own fields (written in
CONTENT_SOURCE_LANGUAGE) and the other languages in a JSON field ``i18n``:
{"ar": {"title": "…"}, "en": {"title": "…"}}. Pages show the visitor's
language when it is filled in, otherwise the main text. Editing forms keep
working on the main text, so nothing changes for people who only write one
language. Translations are entered in Dashboard → Translations, on the
product form, or filled by machine translation when a key is configured.
"""
from django.conf import settings
from django.db import models
from django.utils.translation import get_language, gettext_lazy as _


def source_language():
    return getattr(settings, "CONTENT_SOURCE_LANGUAGE", settings.LANGUAGE_CODE).split("-")[0]


def target_languages():
    src = source_language()
    return [code for code, _ in settings.LANGUAGES if code != src]


def current_language():
    return (get_language() or settings.LANGUAGE_CODE).split("-")[0]


class Translatable(models.Model):
    TRANSLATABLE_FIELDS = ()

    i18n = models.JSONField(_("Translations"), default=dict, blank=True)

    class Meta:
        abstract = True

    def tr(self, field, lang=None):
        lang = lang or current_language()
        if lang != source_language():
            value = ((self.i18n or {}).get(lang) or {}).get(field)
            if value:
                return value
        return getattr(self, field)

    def get_tr(self, lang, field):
        return ((self.i18n or {}).get(lang) or {}).get(field, "")

    def set_tr(self, lang, field, value):
        data = dict(self.i18n or {})
        entry = dict(data.get(lang) or {})
        value = (value or "").strip()
        if value:
            entry[field] = value
        else:
            entry.pop(field, None)
        if entry:
            data[lang] = entry
        else:
            data.pop(lang, None)
        self.i18n = data

    def missing_languages(self):
        """Languages where a field that has a main text has no translation yet."""
        fields = [f for f in self.TRANSLATABLE_FIELDS if (getattr(self, f) or "").strip()]
        return [lang for lang in target_languages() if any(not self.get_tr(lang, f) for f in fields)]


def tr(obj, field):
    """Template/code helper that also accepts plain dicts and objects without translations."""
    if obj is None:
        return ""
    if hasattr(obj, "tr"):
        return obj.tr(field)
    if isinstance(obj, dict):
        return obj.get(field, "")
    return getattr(obj, field, "")


def translation_langs(obj, fields):
    """Rows for a form: one per target language with its name, direction and current values."""
    names = dict(settings.LANGUAGES)
    bidi = getattr(settings, "LANGUAGES_BIDI", ("ar", "he", "fa", "ur"))
    rows = []
    for code in target_languages():
        row = {"code": code, "name": names.get(code, code), "dir": "rtl" if code in bidi else "ltr"}
        for field in fields:
            row[field] = obj.get_tr(code, field) if obj is not None else ""
        rows.append(row)
    return rows


def search_q(word, fields, prefix=""):
    """Q matching ``word`` in the translations of ``fields`` (works on SQLite and PostgreSQL)."""
    from django.db.models import Q
    q = Q()
    for lang in target_languages():
        for field in fields:
            q |= Q(**{f"{prefix}i18n__{lang}__{field}__icontains": word})
    return q
