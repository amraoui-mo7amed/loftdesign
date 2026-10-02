from decimal import Decimal

from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def dzd(value):
    """12500 -> '12 500 DZD' (same format as the cart)."""
    if value is None or value == "":
        return "—"
    amount = f"{Decimal(value):,.0f}".replace(",", "\u202f") + " DZD"
    return format_html('<bdi dir="ltr">{}</bdi>', amount)  # keeps "12 500 DZD" in order in Arabic


@register.filter
def absval(value):
    return abs(value) if value is not None else value
