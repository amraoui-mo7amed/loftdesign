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
from .models import PartnerPrice, LoftPrice, SupplierPrice


def resolve_chain(product, referred_by_code):
    """
    Trace the PartnerPrice chain for a product given a referral code.
    Returns a dict with supplier, loft, affiliate, semi pricing levels.

    The chain flows: Supplier -> Loft -> Affiliate -> Semi -> Customer
    Each level earns: (price_they_charge - price_they_pay) per unit sold.
    """
    levels = {
        "supplier_wholesale": Decimal("0.00"),
        "loft_wholesale": Decimal("0.00"),
        "affiliate_wholesale": None,
        "semi_wholesale": None,
        "retail_price_charged": Decimal("0.00"),
    }

    # 1. Supplier level
    supplier_price = SupplierPrice.objects.filter(product=product).first()
    if supplier_price:
        levels["supplier_wholesale"] = supplier_price.loft_purchase_price

    # 2. Loft level
    loft_price = LoftPrice.objects.filter(product=product, is_active=True).first()
    if loft_price:
        levels["loft_wholesale"] = loft_price.loft_default_wholesale_price

    # 3. Referral chain (if any)
    if referred_by_code:
        referred_profile = UserProfile.objects.filter(
            affiliate_code=referred_by_code, is_approved=True
        ).first()
        if referred_profile:
            from user_auth.models import UserProfile as UP

            if referred_profile.role == UP.roleChoices.SEMI_AFFILIATE:
                # Semi-affiliate referred the order — find the semi's PartnerPrice
                # Semi buys from affiliate at affiliate's wholesale
                semi_pp = PartnerPrice.objects.filter(
                    product=product, buyer=referred_profile.user, is_active=True
                ).first()
                if semi_pp:
                    levels["retail_price_charged"] = semi_pp.retail_price or semi_pp.purchase_price
                    levels["semi_wholesale"] = semi_pp.wholesale_price or semi_pp.purchase_price
                    # Find affiliate's PartnerPrice (affiliate buys from admin)
                    if semi_pp.seller:
                        aff_pp = PartnerPrice.objects.filter(
                            product=product, buyer=semi_pp.seller, is_active=True
                        ).first()
                        if aff_pp:
                            levels["affiliate_wholesale"] = aff_pp.wholesale_price or aff_pp.purchase_price
                        else:
                            # Upstream affiliate PartnerPrice missing — degrade chain
                            levels["semi_wholesale"] = None
                            levels["affiliate_wholesale"] = None
            else:
                # Affiliate referred the order directly
                aff_pp = PartnerPrice.objects.filter(
                    product=product, buyer=referred_profile.user, is_active=True
                ).first()
                if aff_pp:
                    levels["retail_price_charged"] = aff_pp.retail_price or aff_pp.purchase_price
                    levels["affiliate_wholesale"] = aff_pp.wholesale_price or aff_pp.purchase_price

    return levels


def compute_item_profit(product, price_paid, quantity, referred_by_code):
    """
    Compute profit distribution for a single order item.
    All levels in the chain earn at delivery per the per-sale model.

    Supplier:     supplier_wholesale × qty
    Loft:         (loft_wholesale − supplier_wholesale) × qty
    Affiliate:    (aff_wholesale − loft_wholesale) × qty  (if in chain)
    Semi:         (price − aff_wholesale) × qty            (if in chain)
    """
    chain = resolve_chain(product, referred_by_code)

    price = Decimal(str(price_paid))
    qty = int(quantity)

    supplier_base = chain["supplier_wholesale"]
    loft_base = chain["loft_wholesale"]
    aff_base = chain["affiliate_wholesale"]
    semi_base = chain["semi_wholesale"]

    supplier_share = supplier_base * qty

    if semi_base is not None and aff_base is not None:
        loft_share = (loft_base - supplier_base) * qty
        affiliate_share = (aff_base - loft_base) * qty
        semi_share = (price - aff_base) * qty
    elif aff_base is not None:
        loft_share = (loft_base - supplier_base) * qty
        affiliate_share = (aff_base - loft_base) * qty
        semi_share = Decimal("0.00")
    else:
        loft_share = (price - supplier_base) * qty
        affiliate_share = Decimal("0.00")
        semi_share = Decimal("0.00")

    return {
        "supplier_share": max(supplier_share, Decimal("0.00")),
        "loft_share": max(loft_share, Decimal("0.00")),
        "affiliate_share": max(affiliate_share, Decimal("0.00")),
        "semi_share": max(semi_share, Decimal("0.00")),
    }


def compute_order_profit(order):
    """
    Compute total profit distribution for an entire order.
    Stores the result in the order's profit fields and saves.
    """
    referred_code = order.referred_by or ""

    total_supplier = Decimal("0.00")
    total_loft = Decimal("0.00")
    total_affiliate = Decimal("0.00")
    total_semi = Decimal("0.00")

    for item in order.items:
        product_id = item.get("product_id")
        price = item.get("price", 0)
        quantity = item.get("quantity", 1)
        if product_id:
            try:
                from .models import Product
                product = Product.objects.get(pk=product_id)
                profit = compute_item_profit(product, price, quantity, referred_code)
                total_supplier += profit["supplier_share"]
                total_loft += profit["loft_share"]
                total_affiliate += profit["affiliate_share"]
                total_semi += profit["semi_share"]
            except Product.DoesNotExist:
                pass

    order.supplier_share = total_supplier
    order.loft_share = total_loft
    order.affiliate_share = total_affiliate
    order.semi_share = total_semi
    order.save(update_fields=[
        "supplier_share", "loft_share", "affiliate_share", "semi_share"
    ])

    return {
        "supplier_share": total_supplier,
        "loft_share": total_loft,
        "affiliate_share": total_affiliate,
        "semi_share": total_semi,
    }


def build_order_chain_breakdown(order):
    """
    Build a full chain breakdown for an order with intermediate prices.
    Returns a dict suitable for JSON serialization.
    """
    from .models import Product

    referred_code = order.referred_by or ""
    items_breakdown = []

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
        profit = compute_item_profit(product, price, qty, referred_code)

        items_breakdown.append({
            "title": title,
            "qty": qty,
            "price": float(price),
            "subtotal": float(price * qty),
            "chain": {
                "supplier_wholesale": float(chain["supplier_wholesale"]),
                "loft_wholesale": float(chain["loft_wholesale"]),
                "affiliate_wholesale": float(chain["affiliate_wholesale"]) if chain["affiliate_wholesale"] is not None else None,
                "semi_wholesale": float(chain["semi_wholesale"]) if chain["semi_wholesale"] is not None else None,
                "retail_price_charged": float(chain["retail_price_charged"]) if chain["retail_price_charged"] else None,
            },
            "profits": {
                "supplier": float(profit["supplier_share"]),
                "loft": float(profit["loft_share"]),
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
            "affiliate_share": float(order.affiliate_share),
            "semi_share": float(order.semi_share),
        },
    }


def credit_wallets_for_order(order):
    """
    Credit wallets when an order is marked DELIVERED.
    Creates Transaction records and detailed notifications for all levels.
    """
    from user_auth.models import Wallet, Transaction
    from django.contrib.auth.models import User

    if order.status != "delivered":
        return

    referred_code = order.referred_by or ""

    referred_profile = None
    if referred_code:
        referred_profile = UserProfile.objects.filter(
            affiliate_code=referred_code, is_approved=True
        ).first()

    # Gather product-level breakdown for notifications
    product_details = []
    for item in order.items:
        product_id = item.get("product_id")
        price = item.get("price", 0)
        qty = item.get("quantity", 1)
        if product_id:
            try:
                from .models import Product
                product = Product.objects.get(pk=product_id)
                profit = compute_item_profit(product, price, qty, referred_code)
                product_details.append({
                    "title": product.title,
                    "qty": qty,
                    "price": price,
                    "supplier": profit["supplier_share"],
                    "loft": profit["loft_share"],
                    "affiliate": profit["affiliate_share"],
                    "semi": profit["semi_share"],
                })
            except Product.DoesNotExist:
                pass

    # Find supplier users from order items
    supplier_users = set()
    for item in order.items:
        product_id = item.get("product_id")
        if product_id:
            try:
                from .models import Product
                product = Product.objects.get(pk=product_id)
                sp = SupplierPrice.objects.filter(product=product).first()
                if sp and sp.supplier:
                    supplier_users.add(sp.supplier)
            except Product.DoesNotExist:
                pass

    # Build a readable order number
    order_label = order.order_number or f"#{order.id}"

    # Determine who gets what
    credit_entries = []

    # 1. Supplier
    if order.supplier_share > 0:
        for user in supplier_users:
            if user:
                credit_entries.append((
                    user, order.supplier_share,
                    _("Supplier payment for order %(num)s") % {"num": order_label},
                ))

    # 2. Loft (admin)
    if order.loft_share > 0:
        for admin in User.objects.filter(is_superuser=True):
            credit_entries.append((
                admin, order.loft_share,
                _("Loft Design profit for order %(num)s") % {"num": order_label},
            ))

    # 3. Affiliate
    if order.affiliate_share > 0 and referred_profile:
        if referred_profile.role == UserProfile.roleChoices.AFFILIATE:
            credit_entries.append((
                referred_profile.user, order.affiliate_share,
                _("Affiliate commission for order %(num)s") % {"num": order_label},
            ))
        elif referred_profile.role == UserProfile.roleChoices.SEMI_AFFILIATE and referred_profile.parent_affiliate:
            credit_entries.append((
                referred_profile.parent_affiliate.user, order.affiliate_share,
                _("Affiliate commission for order %(num)s") % {"num": order_label},
            ))

    # 4. Semi-affiliate
    if order.semi_share > 0 and referred_profile and referred_profile.role == UserProfile.roleChoices.SEMI_AFFILIATE:
        credit_entries.append((
            referred_profile.user, order.semi_share,
            _("Semi-affiliate commission for order %(num)s") % {"num": order_label},
        ))

    # Create wallet transactions + notifications
    customer_name = order.customer_name or _("Guest")

    for user, amount, desc in credit_entries:
        wallet, _wcreated = Wallet.objects.get_or_create(user=user)
        wallet.balance += amount
        wallet.save(update_fields=["balance"])
        Transaction.objects.create(
            wallet=wallet,
            transaction_type=Transaction.TransactionType.EARNING,
            amount=amount,
            description=desc,
            order=order,
            status=Transaction.TransactionStatus.COMPLETED,
        )

    # ── Detailed notifications ──────────────────────────────────
    for pd in product_details:
        lines = [
            _("Order %(num)s — Delivered ✓") % {"num": order_label},
            _("Customer: %(name)s") % {"name": customer_name},
            "",
            _("Product: %(title)s × %(qty)s") % {"title": pd["title"], "qty": pd["qty"]},
            _("  Supplier:    DZD%(amount)s") % {"amount": f"{pd['supplier']:,.2f}"},
            _("  Loft Design: DZD%(amount)s") % {"amount": f"{pd['loft']:,.2f}"},
        ]
        if pd["affiliate"] > 0:
            lines.append(_("  Affiliate:   DZD%(amount)s") % {"amount": f"{pd['affiliate']:,.2f}"})
        if pd["semi"] > 0:
            lines.append(_("  Semi:        DZD%(amount)s") % {"amount": f"{pd['semi']:,.2f}"})
        total = pd["supplier"] + pd["loft"] + pd["affiliate"] + pd["semi"]
        lines.append(_("  Total:       DZD%(amount)s") % {"amount": f"{total:,.2f}"})

        msg = "\n".join(lines)

        # Notify all admins with full breakdown
        for admin in User.objects.filter(is_superuser=True):
            notify_user(
                admin,
                _("Profit Distribution — %(title)s") % {"title": pd["title"]},
                msg,
                notification_type="success",
                link=reverse("dash:order_detail", kwargs={"pk": order.pk}),
            )

    # Notify non-admin participants
    if referred_profile and order.affiliate_share > 0:
        if referred_profile.role == UserProfile.roleChoices.AFFILIATE:
            aff_user = referred_profile.user
        elif referred_profile.role == UserProfile.roleChoices.SEMI_AFFILIATE and referred_profile.parent_affiliate:
            aff_user = referred_profile.parent_affiliate.user
        else:
            aff_user = None
        if aff_user and not aff_user.is_superuser:
            product_list = ", ".join(pd["title"] for pd in product_details)
            notify_user(
                aff_user,
                _("Commission Earned — Order %(num)s") % {"num": order_label},
                _('You earned DZD%(amount)s commission on "%(products)s" for order %(num)s.')
                % {
                    "amount": f"{order.affiliate_share:,.2f}",
                    "products": product_list,
                    "num": order_label,
                },
                notification_type="success",
                link=reverse("dash:wallet_detail"),
            )

    if referred_profile and order.semi_share > 0 and referred_profile.role == UserProfile.roleChoices.SEMI_AFFILIATE:
        semi_user = referred_profile.user
        if not semi_user.is_superuser:
            product_list = ", ".join(pd["title"] for pd in product_details)
            notify_user(
                semi_user,
                _("Commission Earned — Order %(num)s") % {"num": order_label},
                _('You earned DZD%(amount)s commission on "%(products)s" for order %(num)s.')
                % {
                    "amount": f"{order.semi_share:,.2f}",
                    "products": product_list,
                    "num": order_label,
                },
                notification_type="success",
                link=reverse("dash:wallet_detail"),
            )

    for supplier_user in supplier_users:
        if supplier_user and not supplier_user.is_superuser:
            product_list = ", ".join(pd["title"] for pd in product_details)
            notify_user(
                supplier_user,
                _("Payment Received — Order %(num)s") % {"num": order_label},
                _('You received DZD%(amount)s for "%(products)s" (order %(num)s).')
                % {
                    "amount": f"{order.supplier_share:,.2f}",
                    "products": product_list,
                    "num": order_label,
                },
                notification_type="success",
                link=reverse("dash:wallet_detail"),
            )


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
