"""Create storefront orders in one place: stock locked and checked, the
customer's price resolved server-side, the price chain frozen on the order."""
import logging
from decimal import Decimal

from django.db import transaction
from django.utils.translation import gettext as _

from dashboard.models import Order, Product, ProductItem
from dashboard.utils import PricingError, check_low_stock, check_low_stock_product_item, money, snapshot_order
from frontend.pricing import charge_eur, customer_price

logger = logging.getLogger(__name__)


class CheckoutError(Exception):
    """A message that can be shown to the customer."""


def create_customer_order(request, lines, customer):
    """
    lines: iterable of (product_id, variant_id or None, quantity)
    customer: dict with name, phone, address, wilaya, commune
    Returns the created Order or raises CheckoutError.
    """
    lines = [(pid, vid, int(qty)) for pid, vid, qty in lines]
    if not lines:
        raise CheckoutError(_("No valid items in cart."))
    if any(qty < 1 for _pid, _vid, qty in lines):
        raise CheckoutError(_("Quantity must be at least 1"))

    try:
        with transaction.atomic():
            items, code, eur_total, all_eur = [], None, Decimal("0"), True
            for pid, vid, qty in lines:
                product = (
                    Product.objects.select_for_update()
                    .filter(pk=pid, is_active=True, status=Product.ProductStatus.APPROVED)
                    .first()
                )
                if product is None:
                    raise CheckoutError(_("This product is no longer available."))
                variant = None
                if vid:
                    variant = ProductItem.objects.select_for_update().filter(pk=vid, product=product, is_active=True).first()
                    if variant is None:
                        raise CheckoutError(_("This variant is no longer available."))
                    if variant.stock_quantity < qty:
                        raise CheckoutError(_("Only %(stock)s available for %(title)s.") % {"stock": variant.stock_quantity, "title": f"{product.title} — {variant.name}"})
                elif product.quantity < qty:
                    raise CheckoutError(_("Only %(stock)s available for %(title)s.") % {"stock": product.quantity, "title": product.title})

                price = customer_price(request, product)
                if price["dzd"] is None:
                    raise CheckoutError(_("Price not configured for this product. Please contact support."))
                line_code = price["code"]
                if code is None:
                    code = line_code
                elif code != line_code:
                    code = ""  # mixed sources: no single referrer for this order
                eur = charge_eur(request, product)
                if eur is None:
                    all_eur = False
                else:
                    eur_total += eur * qty

                entry = {
                    "product_id": product.pk,
                    "title": product.title,
                    "price": str(money(price["dzd"])),
                    "quantity": qty,
                    "thumbnail": product.thumbnail.url if product.thumbnail else "",
                }
                if eur is not None:
                    entry["price_eur"] = str(money(eur))
                if variant is not None:
                    entry.update(item_id=variant.pk, item_name=variant.name,
                                 item_thumbnail=variant.thumbnail.url if variant.thumbnail else "")
                    variant.stock_quantity -= qty
                    variant.save()
                    check_low_stock_product_item(variant)
                else:
                    product.quantity -= qty
                    product.save()
                    check_low_stock(product)
                items.append(entry)

            in_eur = all_eur and eur_total > 0
            order = Order.objects.create(
                items=items,
                buyer=request.user if request.user.is_authenticated else None,
                customer_name=customer.get("name", ""),
                customer_phone=customer.get("phone", ""),
                customer_address=customer.get("address", "") or "",
                wilaya=customer.get("wilaya", "") or "",
                commune=customer.get("commune", "") or "",
                status=Order.OrderStatus.PENDING,
                referred_by=code or "",
                currency="EUR" if in_eur else "DZD",
                total_eur=money(eur_total) if in_eur else None,
            )
            snapshot_order(order)
            return order
    except PricingError:
        logger.exception("Inconsistent price chain at checkout")
        raise CheckoutError(_("The price of a product is being updated. Please try again later or contact us."))


def validate_customer(data, foreign=False):
    errors = {}
    if not (data.get("name") or "").strip():
        errors["name"] = [_("Name is required")]
    if not (data.get("phone") or "").strip():
        errors["phone"] = [_("Phone is required")]
    if not (data.get("wilaya") or "").strip():
        errors["wilaya"] = [_("Country is required") if foreign else _("Wilaya is required")]
    if not (data.get("commune") or "").strip():
        errors["commune"] = [_("City is required") if foreign else _("Commune is required")]
    return errors
