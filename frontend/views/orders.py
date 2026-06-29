from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from dashboard.models import Product, ProductItem, Order, Notification, PartnerPrice
from dashboard.utils import notify_user, resolve_price, check_low_stock, check_low_stock_product_item
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from django.db import transaction
from user_auth.models import UserProfile

def place_order(request):
    """AJAX view to handle product inquiry (order) submission"""
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        item_id = request.POST.get("item_id")
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        wilaya = request.POST.get("wilaya")
        commune = request.POST.get("commune")
        quantity = request.POST.get("quantity", 1)

        errors = {}
        if not name: errors["name"] = [_("Name is required")]
        if not phone: errors["phone"] = [_("Phone is required")]
        if not wilaya: errors["wilaya"] = [_("Wilaya is required")]
        if not commune: errors["commune"] = [_("Commune is required")]
        try:
            quantity = int(quantity)
            if quantity < 1:
                errors["quantity"] = [_("Quantity must be at least 1")]
        except ValueError:
            errors["quantity"] = [_("Invalid quantity value")]

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        product = get_object_or_404(Product, id=product_id)
        
        # Check stock — item-level or product-level
        item = None
        if item_id:
            item = get_object_or_404(ProductItem, pk=item_id, product=product, is_active=True)
            if item.stock_quantity < quantity:
                return JsonResponse({"success": False, "errors": {"quantity": [_("Requested quantity exceeds available stock for this variant.")]}})
        elif product.quantity < quantity:
            return JsonResponse({"success": False, "errors": {"quantity": [_("Requested quantity exceeds available stock.")]}})

        # Resolve price — use affiliate's retail price if referred
        affiliate_code = request.session.get("affiliate_code", "")
        resolved = None
        if affiliate_code:
            try:
                aff_profile = UserProfile.objects.get(affiliate_code=affiliate_code, is_approved=True)
                pp = PartnerPrice.objects.filter(
                    product=product, buyer=aff_profile.user, is_active=True
                ).first()
                if pp and pp.retail_price is not None:
                    resolved = pp.retail_price
            except UserProfile.DoesNotExist:
                pass
        if resolved is None:
            seller_user = product.user or User.objects.filter(is_superuser=True).first()
            buyer_user = request.user if request.user.is_authenticated else None
            resolved = resolve_price(product, seller_user, buyer_user)
        if resolved is None:
            return JsonResponse({
                "success": False,
                "errors": {"system": [_("Price not configured for this product. Please contact support.")]}
            })

        try:
            with transaction.atomic():
                product = Product.objects.select_for_update().get(pk=product.pk)
                order_item = {
                    "product_id": product.pk,
                    "title": product.title,
                    "price": str(resolved),
                    "quantity": quantity,
                    "thumbnail": product.thumbnail.url if product.thumbnail else "",
                }
                if item:
                    item = ProductItem.objects.select_for_update().get(pk=item.pk)
                    order_item["item_id"] = item.pk
                    order_item["item_name"] = item.name
                    order_item["item_thumbnail"] = item.thumbnail.url if item.thumbnail else ""
                    item.stock_quantity -= quantity
                    item.save()
                    check_low_stock_product_item(item)
                else:
                    product.quantity -= quantity
                    product.save()
                    check_low_stock(product)

                order = Order.objects.create(
                    items=[order_item],
                    customer_name=name,
                    customer_phone=phone,
                    customer_address=address,
                    wilaya=wilaya,
                    commune=commune,
                    status=Order.OrderStatus.PENDING,
                    referred_by=affiliate_code,
                )
 
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
        except Exception as e:
            return JsonResponse({"success": False, "errors": {"system": [str(e)]}})

    return JsonResponse({"success": False}, status=400)
