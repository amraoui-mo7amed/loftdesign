from django.conf import settings
from django.utils.translation import gettext_lazy as _, get_language


def site_settings(request):
    """
    Returns global site configuration and branding details.
    """
    static_url = settings.STATIC_URL
    return {
        "site_config": {
            "name": _("LOFT Design"),
            "ar_name": "لوفت ديزاين",  # Keep for title fallback logic
            "tagline": _("Elevate Your Space with Modern Design"),
            "logo": f"{static_url}img/icon.jpeg",
            "favicon": f"{static_url}img/icon.jpeg",
            "contact_email": "info@loftdesign.com",
            "phone": "+213 555 123 456",
            "social": {
                "facebook": "https://facebook.com/loftdesign",
                "twitter": "https://twitter.com/loftdesign",
                "instagram": "https://instagram.com/loftdesign",
            },
            "seo": {
                "description": _(
                    _("LOFT Design - High-end interior design and architectural solutions.")
                ),
                "keywords": _(
                    _("interior design, loft, architecture, modern furniture, decor")
                ),
            },
            "branding": {
                "primary_color": "#FFD65A",  # Soft Yellow from logo
                "secondary_color": "#212121", # Dark Box from logo
                "accent_color": "#FFFFFF",    # White text
                "success_color": "#28a745",
                "danger_color": "#dc3545",
                "dark_color": "#1a1a1a",
                "light_color": "#f8f9fa",
            },
        }
    }
