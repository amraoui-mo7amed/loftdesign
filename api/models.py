import hashlib
import secrets

from django.db import models
from django.utils.translation import gettext_lazy as _


def hash_key(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


class ApiClient(models.Model):
    """An application allowed to write through the Store API (BILNOV, BILNOV Desktop, a CAD plugin).

    Only the SHA-256 of the key is stored; the key itself is shown once, at creation.
    """

    name = models.CharField(_("Name"), max_length=120)
    prefix = models.CharField(max_length=12, unique=True, editable=False)
    key_hash = models.CharField(max_length=64, editable=False)
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = _("API client")
        verbose_name_plural = _("API clients")

    def __str__(self):
        return f"{self.name} ({self.prefix}…)"

    @classmethod
    def create(cls, name):
        """Returns (client, raw_key)."""
        prefix = "sb_" + secrets.token_hex(4)
        raw = f"{prefix}.{secrets.token_urlsafe(32)}"
        return cls.objects.create(name=name, prefix=prefix, key_hash=hash_key(raw)), raw

    @classmethod
    def authenticate(cls, raw):
        if not raw or "." not in raw:
            return None
        client = cls.objects.filter(prefix=raw.split(".", 1)[0], is_active=True).first()
        if client and secrets.compare_digest(client.key_hash, hash_key(raw)):
            return client
        return None
