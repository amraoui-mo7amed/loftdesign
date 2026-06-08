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
