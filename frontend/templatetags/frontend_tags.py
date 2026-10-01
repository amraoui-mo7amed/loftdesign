from decimal import Decimal

from django import template
from django.utils.html import format_html

from frontend.pricing import customer_price, visitor_currency
from frontend.utils import get_website_name

register = template.Library()


@register.simple_tag
def website_name():
    """
    Returns the dynamic website name based on current language.
    Usage: {% website_name %}
    """
    return get_website_name()


def _fmt_dzd(value):
    return f"{Decimal(value):,.0f}".replace(",", " ") + " DZD"


def _fmt_eur(value):
    return f"{Decimal(value):,.2f}".replace(",", " ").replace(".", ",") + " €"


@register.simple_tag(takes_context=True)
def shop_amount(context, dzd, eur=None, css=""):
    """An amount in DZD, or in euros for visitors outside Algeria when a euro
    amount exists. When the country is unknown the page script picks the
    currency from the browser time zone (data-eur)."""
    request = context.get("request")
    currency = visitor_currency(request) if request else "DZD"
    if dzd in (None, "") and eur in (None, ""):
        return ""
    if currency == "EUR" and eur not in (None, ""):
        text = _fmt_eur(eur)
    elif dzd not in (None, ""):
        text = _fmt_dzd(dzd)
    else:
        return ""
    attrs = ""
    if eur not in (None, "") and dzd not in (None, ""):
        attrs = format_html(' data-dzd="{}" data-eur="{}"', _fmt_dzd(dzd), _fmt_eur(eur))
    return format_html('<span class="js-price {}"{}>{}</span>', css, attrs, text)


@register.simple_tag(takes_context=True)
def shop_price(context, product, css=""):
    """Price of a product for the current visitor (affiliate link, professional
    account, public price) in DZD or EUR."""
    request = context.get("request")
    if request is None:
        return shop_amount(context, product.loft_retail_price, None, css)
    p = customer_price(request, product)
    return shop_amount(context, p["dzd"], p["eur"], css)
