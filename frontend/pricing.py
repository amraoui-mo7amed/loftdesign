"""Prices shown to and charged to storefront customers.

One place decides the price of a product for the current visitor:
affiliate / semi-affiliate retail price when the visit comes from their link,
professional price for approved professional clients, otherwise the public
retail price. Visitors outside Algeria see the euro price when one is set.
"""
from decimal import Decimal

from django.contrib.auth.models import User

from dashboard.models import PartnerPrice
from dashboard.utils import resolve_price
from user_auth.models import UserProfile

COUNTRY_HEADERS = (
    "HTTP_CF_IPCOUNTRY",
    "HTTP_CLOUDFRONT_VIEWER_COUNTRY",
    "HTTP_X_COUNTRY_CODE",
    "HTTP_X_APPENGINE_COUNTRY",
)
CURRENCY_COOKIE = "store_devise"


def visitor_currency(request):
    """'EUR', 'DZD', or 'auto' when the server cannot tell (the page then
    decides with the browser time zone and remembers it in a cookie)."""
    forced = (request.GET.get("devise") or "").lower()
    if forced in ("eur", "da", "dzd"):
        return "EUR" if forced == "eur" else "DZD"
    cookie = (request.COOKIES.get(CURRENCY_COOKIE) or "").lower()
    if cookie in ("eur", "dzd"):
        return cookie.upper()
    for header in COUNTRY_HEADERS:
        code = (request.META.get(header) or "").strip().upper()
        if len(code) == 2 and code not in ("XX", "T1"):
            return "DZD" if code == "DZ" else "EUR"
    return "auto"


def _referrer(request):
    code = request.session.get("affiliate_code") or ""
    if not code:
        return None, ""
    profile = UserProfile.objects.filter(affiliate_code=code, is_approved=True, is_blocked=False).first()
    return profile, (code if profile else "")


def is_professional(user):
    if not getattr(user, "is_authenticated", False):
        return False
    profile = getattr(user, "profile", None)
    return bool(
        profile
        and profile.role == UserProfile.roleChoices.PROFESSIONAL_CLIENT
        and profile.is_approved
        and not profile.is_blocked
    )


def customer_price(request, product):
    """{'dzd': Decimal|None, 'eur': Decimal|None, 'code': referral code, 'pro': bool}"""
    profile, code = _referrer(request)
    dzd = None
    if profile is not None:
        pp = (
            PartnerPrice.objects.filter(product=product, buyer=profile.user, is_active=True)
            .order_by("-updated_at", "-pk")
            .first()
        )
        if pp and pp.retail_price is not None:
            dzd = pp.retail_price
        else:
            code = ""
    pro = False
    if dzd is None and is_professional(request.user) and product.pro_price:
        dzd, pro = product.pro_price, True
    if dzd is None:
        seller = product.user or User.objects.filter(is_superuser=True).order_by("pk").first()
        buyer = request.user if request.user.is_authenticated else None
        dzd = resolve_price(product, seller, buyer)
    return {"dzd": dzd, "eur": product.price_eur, "code": code, "pro": pro}


def charge_eur(request, product):
    """Euro price to charge, or None when the order is in dinars."""
    if visitor_currency(request) == "EUR" and product.price_eur:
        return Decimal(product.price_eur)
    return None
