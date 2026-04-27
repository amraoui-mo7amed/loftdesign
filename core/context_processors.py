from django.conf import settings
from django.utils.translation import gettext_lazy as _, get_language


def site_settings(request):
    """
    Returns global site configuration and branding details.
    """
    return {
        "site_config": {
            "name": _("SnapStore"),
            "ar_name": "سناب ستور",  # Keep for title fallback logic
            "tagline": _("AI-Powered Landing Pages"),
            "logo": None,  # Add custom logo path here
            "favicon": None,  # Add custom favicon path here
            "contact_email": "info@snapstore.com",
            "phone": "+213 555 000 000",
            "social": {
                "facebook": "https://facebook.com/snapstore",
                "twitter": "https://twitter.com/snapstore",
                "instagram": "https://instagram.com/snapstore",
            },
            "seo": {
                "description": _(
                    _("Generate high-converting landing pages in seconds with Gemini AI.")
                ),
                "keywords": _(
                    _("landing page, ai, gemini, merchant, ecommerce, conversion")
                ),
            },
            "branding": {
                "primary_color": "#0d6efd",
                "secondary_color": "#6c757d",
                "accent_color": "#ffc107",
                "success_color": "#198754",
                "danger_color": "#dc3545",
                "dark_color": "#212529",
                "light_color": "#f8f9fa",
            },
        }
    }
