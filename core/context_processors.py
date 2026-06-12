from functools import lru_cache
from django.conf import settings
from django.utils.translation import gettext_lazy as _, get_language


@lru_cache(maxsize=4)
def _build_site_config(lang):
    """Build site config cached by language code."""
    return {
        "site_config": {
            "name": _("LOFT Design"),
            "ar_name": "لوفت ديزاين",
            "tagline": _("Elevate Your Space"),
            "logo": f"{settings.STATIC_URL}img/icon.jpeg",
            "favicon": f"{settings.STATIC_URL}img/icon.jpeg",
            "contact_email": "Loftdesign@live.fr",
            "phone": "+213 776139475",
            "mobile": "+213 541960603",
            "working_hours": _("Lun-Ven: 09h - 18h"),
            "social": {
                "facebook": "https://www.facebook.com/profile.php?id=100067199886406",
                "instagram": "https://www.instagram.com/loftdesign_dz",
            },
            "seo": {
                "description": _(
                    "LOFT Design - High-end interior design and architectural solutions."
                ),
                "keywords": _(
                    "interior design, loft, architecture, modern furniture, decor"
                ),
            },
            "branding": {
                "primary_color": "#FFD65A",
                "secondary_color": "#212121",
                "accent_color": "#FFFFFF",
                "success_color": "#28a745",
                "danger_color": "#dc3545",
                "dark_color": "#1a1a1a",
                "light_color": "#f8f9fa",
            },
        }
    }


def site_settings(request):
    """
    Returns global site configuration and branding details (cached by language).
    """
    return _build_site_config(get_language())