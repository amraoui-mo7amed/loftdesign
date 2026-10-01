from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from dashboard.models import Product, ProductItem, Order, Notification, PartnerPrice
from dashboard.utils import notify_user, resolve_price, check_low_stock, check_low_stock_product_item
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from django.db import transaction
from user_auth.models import UserProfile
from frontend.checkout import CheckoutError, create_customer_order, validate_customer
from frontend.pricing import visitor_currency
import logging

logger = logging.getLogger(__name__)

def place_order(request):
    """AJAX view to handle product inquiry (order) submission"""
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        item_id = request.POST.get("item_id") or None
        foreign = visitor_currency(request) == "EUR"
        customer = {k: (request.POST.get(k) or "").strip() for k in ("name", "phone", "address", "wilaya", "commune")}
        errors = validate_customer(customer, foreign)
        try:
            quantity = int(request.POST.get("quantity", 1))
            if quantity < 1:
                errors["quantity"] = [_("Quantity must be at least 1")]
        except (TypeError, ValueError):
            errors["quantity"] = [_("Invalid quantity value")]
        if errors:
            return JsonResponse({"success": False, "errors": errors})

        try:
            order = create_customer_order(request, [(product_id, item_id, quantity)], customer)
        except CheckoutError as e:
            return JsonResponse({"success": False, "errors": {"quantity": [str(e)]}})
        except Exception:
            logger.exception("place_order failed")
            return JsonResponse({"success": False, "errors": {"system": [_("Something went wrong. Please try again.")]}})

        product = Product.objects.get(pk=order.items[0]["product_id"])
        name = customer["name"]
        affiliate_code = order.referred_by
        # Notify Admins
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            notify_user(
                user=admin,
                title=_("New Lead Received"),
                message=_("New inquiry from %(name)s for product: %(product)s") % {
                    "name": name,
                    "product": product.title
                },
                notification_type=Notification.NotificationType.SUCCESS,
                link="/dashboard/orders/"
            )

        # Notify the referring affiliate (if any)
        if affiliate_code:
            try:
                aff_profile = UserProfile.objects.get(affiliate_code=affiliate_code, is_approved=True)
                notify_user(
                    user=aff_profile.user,
                    title=_("New Lead via Your Store"),
                    message=_("%(name)s placed an inquiry for %(product)s through your store.")
                    % {"name": name, "product": product.title},
                    notification_type=Notification.NotificationType.INFO,
                    link="/dashboard/orders/",
                )
                # If semi-affiliate, also notify parent affiliate
                if aff_profile.role == UserProfile.roleChoices.SEMI_AFFILIATE and aff_profile.parent_affiliate:
                    notify_user(
                        user=aff_profile.parent_affiliate.user,
                        title=_("New Lead via Semi-Affiliate"),
                        message=_("%(name)s placed an inquiry for %(product)s through %(semi)s's store.")
                        % {"name": name, "product": product.title, "semi": aff_profile.user.get_full_name() or aff_profile.user.username},
                        notification_type=Notification.NotificationType.INFO,
                        link="/dashboard/orders/",
                    )
            except UserProfile.DoesNotExist:
                pass

        request.session.pop("affiliate_code", None)
        request.session.modified = True

        return JsonResponse({
            "success": True,
            "message": _("Your inquiry has been sent successfully. Our team will contact you soon.")
        })

    return JsonResponse({"success": False}, status=400)
