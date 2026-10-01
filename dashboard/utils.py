from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext as _
from django_eventstream import send_event
from .models import Notification
import logging

logger = logging.getLogger(__name__)


from decouple import config


def send_account_activation_email(request, profile):
    """
    Sends an account activation email to the user after approval.
    """
    site_name = config("SITE_NAME", default="StarterKit")
    subject = _("Your %(site)s Account has been Activated!") % {"site": site_name}
    login_url = request.build_absolute_uri(reverse("user_auth:login"))

    context = {
        "profile": profile,
        "login_url": login_url,
        "LANGUAGE_CODE": getattr(request, "LANGUAGE_CODE", settings.LANGUAGE_CODE),
    }

    html_content = render_to_string("email/account_activation.html", context)
    text_content = strip_tags(html_content)

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")

    email = EmailMultiAlternatives(
        subject, text_content, from_email, [profile.user.email]
    )
    email.attach_alternative(html_content, "text/html")

    try:
        print(f"DEBUG: Attempting to send email to {profile.user.email}")
        print(f"DEBUG: Subject: {subject}")
        print(f"DEBUG: From: {from_email}")
        print(
            f"DEBUG: Email Backend: {settings.EMAIL_BACKEND if hasattr(settings, 'EMAIL_BACKEND') else 'Default'}"
        )

        email.send()
        print("DEBUG: Email sent successfully!")
        return True
    except Exception as e:
        # In a real production app, we would log this properly
        print(f"DEBUG: Failed to send email to {profile.user.email}")
        print(f"DEBUG: Exception type: {type(e).__name__}")
        print(f"DEBUG: Exception message: {str(e)}")
        import traceback

        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return False


def notify_user(user, title, message, notification_type="info", link=""):
    """
    Create a notification for a user and send it via eventstream.

    Args:
        user: The user to notify
        title: Notification title
        message: Notification message
        notification_type: One of 'info', 'success', 'warning', 'error'
        link: Optional link to navigate to when clicked

    Returns:
        The created Notification instance
    """
    try:
        # Create notification in database
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
        )

        # Send real-time event to user's channel
        channel = f"user-{user.id}"
        event_data = {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "type": notification.notification_type,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
            "link": notification.link,
        }

        send_event(channel, "notification", event_data)

        logger.info(f"Notification sent to user {user.username}: {title}")
        return notification

    except Exception as e:
        logger.error(
            f"Failed to create notification for user {user.username}: {str(e)}"
        )
        return None

from user_auth.models import UserProfile


def resolve_price(product, seller_user, buyer_user):
    """
    Resolve the correct price for a product transaction (spec Section 7).

    Priority:
    1. PartnerPrice for (product, seller, buyer) where is_active=True
    2. If seller is Loft admin and buyer is affiliate/semi-affiliate -> LoftPrice.loft_default_wholesale_price
    3. If buyer is final client or anonymous -> LoftPrice.loft_retail_price
    4. No match -> None

    Returns Decimal or None.
    """
    from .models import PartnerPrice, LoftPrice

    buyer_profile = None
    if buyer_user is not None and buyer_user.is_authenticated:
        try:
            buyer_profile = buyer_user.profile
        except (UserProfile.DoesNotExist, AttributeError):
            buyer_profile = None

    seller_profile = None
    if seller_user is not None and seller_user.is_authenticated:
        try:
            seller_profile = seller_user.profile
        except (UserProfile.DoesNotExist, AttributeError):
            seller_profile = None

    # 1. Check custom partner price (active only)
    partner = PartnerPrice.objects.filter(
        product=product, seller=seller_user, buyer=buyer_user, is_active=True
    ).first()
    if partner:
        return partner.purchase_price

    # 2. Seller is Loft admin, buyer is affiliate/semi-affiliate -> wholesale price
    is_seller_admin = seller_user and (seller_user.is_superuser or (
        seller_profile and seller_profile.role == UserProfile.roleChoices.ADMIN
    ))
    is_buyer_affiliate = buyer_profile and buyer_profile.role in [
        UserProfile.roleChoices.AFFILIATE, UserProfile.roleChoices.SEMI_AFFILIATE
    ]

    if is_seller_admin and is_buyer_affiliate:
        loft_price = LoftPrice.objects.filter(product=product, is_active=True).first()
        if loft_price and loft_price.loft_default_wholesale_price is not None:
            return loft_price.loft_default_wholesale_price

    # 3. Buyer is final client or anonymous -> retail price
    is_buyer_client = (
        buyer_user is None
        or not buyer_user.is_authenticated
        or (buyer_profile and buyer_profile.role == UserProfile.roleChoices.FINAL_CLIENT)
    )
    if is_buyer_client:
        loft_price = LoftPrice.objects.filter(product=product, is_active=True).first()
        if loft_price and loft_price.loft_retail_price is not None:
            return loft_price.loft_retail_price

    # 4. Legacy fallback: product-level loft_retail_price
    if product.loft_retail_price is not None:
        return product.loft_retail_price

    return None


import json
import os

DASHBOARD_CART_SESSION_KEY = "dash_cart"


def get_dash_cart(request):
    return request.session.setdefault(DASHBOARD_CART_SESSION_KEY, {})


def save_dash_cart(request, cart):
    request.session[DASHBOARD_CART_SESSION_KEY] = cart
    request.session.modified = True


from decimal import Decimal
from .models import PartnerPrice, LoftPrice, SupplierPrice, PriceHistory


CENT = Decimal("0.01")


class PricingError(ValueError):
    """The price chain of a product is inconsistent (a level would earn a
    negative amount or the shares would not add up to the price paid)."""


def money(value):
    """Decimal rounded to the cent (ROUND_HALF_UP)."""
    from decimal import ROUND_HALF_UP
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def _active_referrer(code):
    if not code:
        return None
    return (
        UserProfile.objects.select_related("user", "parent_affiliate__user", "created_by")
        .filter(affiliate_code=code, is_approved=True, is_blocked=False)
        .first()
    )


def _partner_price(product, buyer_user):
    return (
        PartnerPrice.objects.filter(product=product, buyer=buyer_user, is_active=True)
        .order_by("-updated_at", "-pk")
        .first()
    )


def resolve_chain(product, referred_by_code):
    """
    Trace who sells to whom for one product and a referral code.

    The chain flows: Supplier -> Loft -> (provider network) -> Affiliate -> Semi -> Customer.
    Each level earns what it charges minus what it pays, so the shares always
    add up to the price paid by the customer.
    """
    levels = {
        "supplier_wholesale": None,      # SupplierPrice.loft_purchase_price
        "supplier_commission": None,     # provider commission %, None for admin products
        "supplier_user_id": None,
        "admin_supplier": False,
        "loft_wholesale": Decimal("0.00"),
        "provider_wholesale": None,      # provider network: price the provider's affiliate pays
        "affiliate_purchase": None,      # what the affiliate pays upstream
        "affiliate_wholesale": None,     # what the affiliate charges its semis
        "semi_purchase": None,           # what the semi pays the affiliate
        "semi_wholesale": None,          # kept for display (legacy key)
        "affiliate_user_id": None,
        "semi_user_id": None,
        "retail_price_charged": Decimal("0.00"),
    }

    supplier_price = SupplierPrice.objects.select_related("supplier").filter(product=product).first()
    if supplier_price:
        levels["supplier_wholesale"] = supplier_price.loft_purchase_price
        levels["supplier_user_id"] = supplier_price.supplier_id
        if supplier_price.supplier and not supplier_price.supplier.is_superuser:
            profile = getattr(supplier_price.supplier, "profile", None)
            commission = Decimal(str(profile.commission or 0)) if profile else Decimal("0")
            levels["supplier_commission"] = min(max(commission, Decimal("0")), Decimal("100"))
        else:
            levels["admin_supplier"] = True

    loft_price = LoftPrice.objects.filter(product=product, is_active=True).first()
    if loft_price:
        levels["loft_wholesale"] = loft_price.loft_default_wholesale_price

    referred = _active_referrer(referred_by_code)
    if referred is None:
        return levels

    if referred.role == UserProfile.roleChoices.SEMI_AFFILIATE:
        parent = referred.parent_affiliate
        semi_pp = _partner_price(product, referred.user)
        aff_pp = _partner_price(product, parent.user) if parent and not parent.is_blocked else None
        if semi_pp and aff_pp:
            levels["retail_price_charged"] = semi_pp.retail_price or semi_pp.purchase_price
            levels["semi_purchase"] = semi_pp.purchase_price
            levels["semi_wholesale"] = semi_pp.purchase_price
            levels["semi_user_id"] = referred.user_id
            levels["affiliate_purchase"] = aff_pp.purchase_price
            levels["affiliate_wholesale"] = aff_pp.wholesale_price or aff_pp.purchase_price
            levels["affiliate_user_id"] = parent.user_id
        node = parent
    elif referred.role == UserProfile.roleChoices.AFFILIATE:
        aff_pp = _partner_price(product, referred.user)
        if aff_pp:
            levels["retail_price_charged"] = aff_pp.retail_price or aff_pp.purchase_price
            levels["affiliate_purchase"] = aff_pp.purchase_price
            levels["affiliate_wholesale"] = aff_pp.wholesale_price or aff_pp.purchase_price
            levels["affiliate_user_id"] = referred.user_id
        node = referred
    else:
        node = None

    # Provider network: the affiliate was created by the provider who owns the
    # product and buys at the provider's affiliate wholesale price.
    creator = node.created_by if node else None
    if (
        levels["affiliate_user_id"]
        and creator is not None
        and creator.role == UserProfile.roleChoices.PROVIDER
        and supplier_price is not None
        and supplier_price.supplier_id == creator.user_id
        and supplier_price.affiliate_wholesale_price is not None
    ):
        levels["provider_wholesale"] = Decimal(str(supplier_price.affiliate_wholesale_price))

    return levels


def split_from_chain(chain, price_paid, quantity):
    """
    Share of each level for one order line, from a resolved chain.

    supplier  = supplier price x (1 - commission)      (provider products)
    provider  = provider wholesale - supplier price      (provider network only)
    loft      = what the first reseller pays - supplier net  (or price - supplier net)
    affiliate = what it charges - what it pays
    semi      = price paid - what it pays
    The shares always add up to price x quantity; a negative share raises
    PricingError instead of being silently clamped.
    """
    price = money(price_paid)
    qty = int(quantity)

    sb = chain["supplier_wholesale"]
    c = chain["supplier_commission"]
    sn = Decimal("0") if sb is None else (sb * (Decimal("1") - (c or Decimal("0")) / Decimal("100")))
    sn = money(sn)
    aff_buy = chain["affiliate_purchase"]
    semi_buy = chain["semi_purchase"]
    pw = chain["provider_wholesale"]

    shares = dict(supplier=sn, provider=Decimal("0"), loft=Decimal("0"), affiliate=Decimal("0"), semi=Decimal("0"))
    if aff_buy is None:
        shares["loft"] = price - sn
    else:
        if pw is not None and sb is not None:
            first_buy = money(pw)
            shares["provider"] = first_buy - money(sb)
            shares["loft"] = money(sb) - sn
        else:
            first_buy = money(aff_buy)
            shares["loft"] = first_buy - sn
        if semi_buy is not None:
            shares["affiliate"] = money(semi_buy) - first_buy
            shares["semi"] = price - money(semi_buy)
        else:
            shares["affiliate"] = price - first_buy

    shares = {k: money(v * qty) for k, v in shares.items()}
    negative = [k for k, v in shares.items() if v < 0]
    if negative or sum(shares.values()) != money(price * qty):
        raise PricingError(", ".join(negative) or "total")
    return shares


def compute_item_profit(product, price_paid, quantity, referred_by_code):
    """Shares of one order line (keys kept for the existing templates)."""
    s = split_from_chain(resolve_chain(product, referred_by_code), price_paid, quantity)
    return {
        "supplier_share": s["supplier"],
        "loft_share": s["loft"],
        "provider_share": s["provider"],
        "affiliate_share": s["affiliate"],
        "semi_share": s["semi"],
    }


def settlement_for_item(product, price_paid, quantity, referred_by_code):
    """Payees and amounts for one line, frozen at order time."""
    chain = resolve_chain(product, referred_by_code)
    s = split_from_chain(chain, price_paid, quantity)
    supplier_id = chain["supplier_user_id"]
    if chain["admin_supplier"] or supplier_id is None:
        # Loft's own stock: the supplier part stays with the platform.
        s["loft"] += s["supplier"]
        s["supplier"] = Decimal("0.00")
        supplier_id = None
    return {
        "supplier": str(s["supplier"]), "supplier_user": supplier_id,
        "provider": str(s["provider"]),
        "loft": str(s["loft"]),
        "affiliate": str(s["affiliate"]), "affiliate_user": chain["affiliate_user_id"],
        "semi": str(s["semi"]), "semi_user": chain["semi_user_id"],
        "commission": str(chain["supplier_commission"]) if chain["supplier_commission"] is not None else None,
    }


def snapshot_order(order):
    """Freeze the price chain of every line on the order (call at creation).
    Raises PricingError when a product's prices are inconsistent."""
    from .models import Product

    items = []
    for item in order.items:
        item = dict(item)
        pid = item.get("product_id")
        product = Product.objects.filter(pk=pid).first() if pid else None
        if product is not None:
            ref_price = item.get("price_dzd", item.get("price", 0))
            item["settlement"] = settlement_for_item(product, ref_price, item.get("quantity", 1), order.referred_by)
        items.append(item)
    order.items = items
    order.save(update_fields=["items"])
    return order


def order_settlements(order):
    """Settlement of every line: the snapshot taken at order time, or the
    current prices for orders created before snapshots existed."""
    from .models import Product

    lines = []
    for item in order.items:
        settlement = item.get("settlement")
        if settlement is None:
            pid = item.get("product_id")
            product = Product.objects.filter(pk=pid).first() if pid else None
            if product is None:
                continue
            ref_price = item.get("price_dzd", item.get("price", 0))
            settlement = settlement_for_item(product, ref_price, item.get("quantity", 1), order.referred_by)
        lines.append((item, settlement))
    return lines


def compute_order_profit(order):
    """Store the total share of each level on the order and return them."""
    totals = {k: Decimal("0.00") for k in ("supplier", "loft", "affiliate", "semi", "provider")}
    for _item, st in order_settlements(order):
        for k in totals:
            totals[k] += Decimal(st[k])

    order.supplier_share = totals["supplier"]
    order.loft_share = totals["loft"]
    order.affiliate_share = totals["affiliate"]
    order.semi_share = totals["semi"]
    order.provider_share = totals["provider"]
    order.save(update_fields=[
        "supplier_share", "loft_share", "affiliate_share", "semi_share", "provider_share"
    ])
    return {f"{k}_share": v for k, v in totals.items()}


def platform_wallet_user():
    """The single account that receives Loft Design's share."""
    from django.conf import settings
    from django.contrib.auth.models import User

    uid = getattr(settings, "PLATFORM_WALLET_USER_ID", None)
    qs = User.objects.filter(is_superuser=True, is_active=True)
    return (qs.filter(pk=uid).first() if uid else None) or qs.order_by("pk").first()


def build_order_chain_breakdown(order):
    """
    Build a full chain breakdown for an order with intermediate prices.
    Returns a dict suitable for JSON serialization.
    """
    from .models import Product

    referred_code = order.referred_by or ""
    items_breakdown = []
    has_admin_supplier = False

    for item in order.items:
        pid = item.get("product_id")
        price = Decimal(str(item.get("price", 0)))
        qty = int(item.get("quantity", 1))
        title = item.get("title", "")
        if not pid:
            continue

        try:
            product = Product.objects.get(pk=pid)
        except Product.DoesNotExist:
            continue

        chain = resolve_chain(product, referred_code)
        pricing_error = False
        st = item.get("settlement")
        if st is None:
            try:
                st = settlement_for_item(product, item.get("price_dzd", price), qty, referred_code)
            except PricingError:
                pricing_error = True
                st = {k: "0" for k in ("supplier", "loft", "provider", "affiliate", "semi")}
        profit = {f"{k}_share": Decimal(st[k]) for k in ("supplier", "loft", "provider", "affiliate", "semi")}

        supplier_price = SupplierPrice.objects.filter(product=product).first()
        is_admin_supplier = supplier_price and supplier_price.supplier and supplier_price.supplier.is_superuser

        if is_admin_supplier:
            has_admin_supplier = True
            chain["admin_cost_basis"] = float(supplier_price.loft_purchase_price)
        else:
            chain["admin_cost_basis"] = None

        # Commission amount + net for display
        if chain["supplier_commission"] is not None and chain["supplier_wholesale"] is not None:
            wholesale_dec = Decimal(str(chain["supplier_wholesale"]))
            commission_amt = float(wholesale_dec * chain["supplier_commission"] / Decimal("100.00"))
            supplier_net = float(wholesale_dec * (Decimal("1.00") - chain["supplier_commission"] / Decimal("100.00")))
        else:
            commission_amt = None
            supplier_net = None

        items_breakdown.append({
            "title": title,
            "qty": qty,
            "price": float(price),
            "subtotal": float(price * qty),
            "chain": {
                "supplier_wholesale": float(chain["supplier_wholesale"]) if chain["supplier_wholesale"] is not None else None,
                "supplier_commission": float(chain["supplier_commission"]) if chain["supplier_commission"] is not None else None,
                "commission_amount": commission_amt,
                "supplier_net": supplier_net,
                "loft_wholesale": float(chain["loft_wholesale"]),
                "provider_wholesale": float(chain["provider_wholesale"]) if chain["provider_wholesale"] is not None else None,
                "affiliate_wholesale": float(chain["affiliate_wholesale"]) if chain["affiliate_wholesale"] is not None else None,
                "semi_wholesale": float(chain["semi_wholesale"]) if chain["semi_wholesale"] is not None else None,
                "retail_price_charged": float(chain["retail_price_charged"]) if chain["retail_price_charged"] else None,
                "admin_cost_basis": chain["admin_cost_basis"],
            },
            "pricing_error": pricing_error,
            "profits": {
                "supplier": float(profit["supplier_share"]),
                "loft": float(profit["loft_share"]),
                "provider": float(profit["provider_share"]),
                "affiliate": float(profit["affiliate_share"]),
                "semi": float(profit["semi_share"]),
            },
        })

    return {
        "order_number": order.order_number or f"#{order.id}",
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "customer_address": order.customer_address,
        "wilaya": order.wilaya,
        "commune": order.commune,
        "status": order.status,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "referred_by": order.referred_by,
        "items": items_breakdown,
        "totals": {
            "total": float(order.total_price()),
            "supplier_share": float(order.supplier_share),
            "loft_share": float(order.loft_share),
            "provider_share": float(order.provider_share),
            "affiliate_share": float(order.affiliate_share),
            "semi_share": float(order.semi_share),
        },
    }


def credit_wallets_for_order(order):
    """
    Credit every participant once when an order is DELIVERED.

    Idempotent: the order's commission_paid flag is switched with a
    conditional UPDATE, so two simultaneous "Delivered" clicks cannot pay twice.
    Each supplier only receives the lines of its own products, and Loft's share
    goes to one platform wallet.
    """
    from collections import defaultdict
    from django.contrib.auth.models import User
    from django.db import transaction as db_transaction
    from django.db.models import F
    from user_auth.models import Wallet, Transaction
    from .models import Order

    if order.status != Order.OrderStatus.DELIVERED:
        return False

    order_label = order.order_number or f"#{order.id}"
    lines = order_settlements(order)

    with db_transaction.atomic():
        claimed = Order.objects.filter(pk=order.pk, commission_paid=False).update(commission_paid=True)
        if not claimed:
            return False
        order.commission_paid = True

        payouts = defaultdict(lambda: defaultdict(Decimal))
        platform = platform_wallet_user()
        for _item, st in lines:
            supplier_id = st.get("supplier_user")
            if Decimal(st["supplier"]) > 0:
                payouts[supplier_id or (platform and platform.pk)]["supplier"] += Decimal(st["supplier"])
            if Decimal(st["provider"]) > 0 and supplier_id:
                payouts[supplier_id]["provider"] += Decimal(st["provider"])
            if Decimal(st["loft"]) > 0 and platform:
                payouts[platform.pk]["loft"] += Decimal(st["loft"])
            if Decimal(st["affiliate"]) > 0 and st.get("affiliate_user"):
                payouts[st["affiliate_user"]]["affiliate"] += Decimal(st["affiliate"])
            if Decimal(st["semi"]) > 0 and st.get("semi_user"):
                payouts[st["semi_user"]]["semi"] += Decimal(st["semi"])

        labels = {
            "supplier": _("Supplier payment for order %(num)s"),
            "provider": _("Provider network profit for order %(num)s"),
            "loft": _("Loft Design profit for order %(num)s"),
            "affiliate": _("Affiliate commission for order %(num)s"),
            "semi": _("Semi-affiliate commission for order %(num)s"),
        }
        credited = []
        for user_id, parts in payouts.items():
            if not user_id:
                continue
            user = User.objects.filter(pk=user_id).first()
            if user is None:
                continue
            wallet, _created = Wallet.objects.get_or_create(user=user)
            for kind, amount in parts.items():
                amount = money(amount)
                if amount <= 0:
                    continue
                Wallet.objects.filter(pk=wallet.pk).update(balance=F("balance") + amount)
                Transaction.objects.create(
                    wallet=wallet,
                    transaction_type=Transaction.TransactionType.EARNING,
                    amount=amount,
                    description=labels[kind] % {"num": order_label},
                    order=order,
                    status=Transaction.TransactionStatus.COMPLETED,
                )
                credited.append((user, kind, amount))

        db_transaction.on_commit(lambda: _notify_order_credits(order, credited))
    return True


def _notify_order_credits(order, credited):
    """One notification per credited person, after the money is committed."""
    from collections import defaultdict

    order_label = order.order_number or f"#{order.id}"
    titles = ", ".join(str(i.get("title", "")) for i in order.items if i.get("title"))
    per_user = defaultdict(Decimal)
    users = {}
    for user, _kind, amount in credited:
        per_user[user.pk] += amount
        users[user.pk] = user
    for uid, amount in per_user.items():
        notify_user(
            users[uid],
            _("Payment Received — Order %(num)s") % {"num": order_label},
            _('You received DZD%(amount)s for "%(products)s" (order %(num)s).')
            % {"amount": f"{amount:,.2f}", "products": titles, "num": order_label},
            notification_type="success",
            link=reverse("dash:wallet_detail"),
        )


def restock_order(order):
    """Put the quantities of a cancelled order back in stock."""
    from django.db.models import F
    from .models import Product, ProductItem

    for item in order.items or []:
        try:
            qty = int(item.get("quantity") or 0)
        except (TypeError, ValueError):
            continue
        if qty <= 0:
            continue
        if item.get("item_id"):
            ProductItem.objects.filter(pk=item["item_id"]).update(stock_quantity=F("stock_quantity") + qty)
        elif item.get("product_id"):
            Product.objects.filter(pk=item["product_id"]).update(quantity=F("quantity") + qty)


def check_low_stock(product, threshold=5):
    """Check if product stock is below threshold and notify admin"""
    from django.contrib.auth.models import User
    if product.quantity <= threshold:
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            notify_user(
                admin,
                _("Low Stock Alert"),
                _('"%(product)s" has only %(qty)s units left.') % {
                    "product": product.title,
                    "qty": product.quantity,
                },
                notification_type="warning",
                link=reverse("dash:product_list"),
            )


def check_low_stock_product_item(item, threshold=5):
    """Check if product variant stock is below threshold and notify admin"""
    from django.contrib.auth.models import User
    if item.stock_quantity <= threshold:
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            notify_user(
                admin,
                _("Low Stock Alert — Variant"),
                _('"%(product)s — %(variant)s" has only %(qty)s units left.') % {
                    "product": item.product.title,
                    "variant": item.name,
                    "qty": item.stock_quantity,
                },
                notification_type="warning",
                link=reverse("dash:product_list"),
            )


def log_price_change(product, user, field_name, old_value, new_value):
    """Record a price change in PriceHistory"""
    PriceHistory.objects.create(
        product=product,
        user=user,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
    )


def get_algeria_locations():
    """
    Returns a dictionary of Wilayas and their corresponding Communes.
    Data is loaded from algeria.json.
    """
    json_path = os.path.join(settings.BASE_DIR, 'algeria.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return [], {}

    wilayas_dict = {}
    for item in data:
        code = item['wilaya_code']
        name = item['wilaya_name_ascii']
        if code not in wilayas_dict:
            wilayas_dict[code] = {
                'name': name,
                'communes': set()
            }
        wilayas_dict[code]['communes'].add(item['commune_name_ascii'])

    wilaya_options = []
    communes_data = {}

    for code in sorted(wilayas_dict.keys()):
        wilaya_options.append({
            "value": code,
            "label": f"{code} - {wilayas_dict[code]['name']}"
        })
        communes_data[code] = [
            {"value": c, "label": c} for c in sorted(list(wilayas_dict[code]['communes']))
        ]

    return wilaya_options, communes_data
