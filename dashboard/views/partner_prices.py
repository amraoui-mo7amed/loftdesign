from django.db import models
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model
from django.conf import settings
from django.template.loader import render_to_string
from ..decorator import role_required
from ..models import Product, PartnerPrice, LoftPrice, AffiliateStore
from ..utils import notify_user
from user_auth.models import UserProfile

User = get_user_model()


_SEMI = UserProfile.roleChoices.SEMI_AFFILIATE
_AFF = UserProfile.roleChoices.AFFILIATE


@role_required(allowed_roles=[_AFF, _SEMI])
def my_catalog(request):
    """List only products the affiliate has added to their catalog"""
    prices = PartnerPrice.objects.filter(
        buyer=request.user, is_active=True,
    ).select_related("product", "product__loft_price").prefetch_related("product__gallery_images")

    catalog = []
    for pp in prices:
        product = pp.product
        loft_price = getattr(product, "loft_price", None)
        catalog.append({
            "product": product,
            "partner_price": pp,
            "purchase_price": pp.purchase_price,
            "wholesale_price": pp.wholesale_price,
            "retail_price": pp.retail_price or (loft_price.loft_retail_price if loft_price else None),
            "primary_image": product.gallery_images.first(),
        })

    return render(request, "products/my_catalog.html", {"catalog": catalog})


@role_required(allowed_roles=[_AFF, _SEMI])
def catalog_details(request, product_pk):
    """Detail page for a product in the affiliate catalog"""
    product = get_object_or_404(
        Product, pk=product_pk, status=Product.ProductStatus.APPROVED, is_active=True,
    )
    loft_price = getattr(product, "loft_price", None)

    pp = PartnerPrice.objects.filter(
        product=product, buyer=request.user, is_active=True,
    ).first()

    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role == _SEMI and profile.parent_affiliate:
        parent_pp = PartnerPrice.objects.filter(
            product=product, buyer=profile.parent_affiliate.user, is_active=True,
        ).first()
        available_qty = product.quantity
    else:
        available_qty = product.quantity

    return render(request, "products/catalog_details.html", {
        "product": product,
        "loft_price": loft_price,
        "partner_price": pp,
        "in_catalog": pp is not None,
        "available_qty": available_qty,
        "purchase_price": pp.purchase_price if pp else (loft_price.loft_default_wholesale_price if loft_price else None),
        "retail_price": pp.retail_price if pp and pp.retail_price else (loft_price.loft_retail_price if loft_price else None),
        "price_configured": loft_price is not None,
        "gallery": list(product.gallery_images.all()),
        "tags": [t.strip() for t in product.tags.split(",") if t.strip()] if product.tags else [],
    })


@role_required(allowed_roles=[_AFF, _SEMI])
def affiliate_catalog(request):
    """List approved products available to resell.
    Affiliates see all approved products.
    Semi-affiliates see only products in their parent affiliate's catalog.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    is_semi = profile.role == _SEMI

    base_qs = Product.objects.filter(
        status=Product.ProductStatus.APPROVED,
        is_active=True,
    ).select_related("user", "loft_price").prefetch_related("gallery_images")

    if is_semi and profile.parent_affiliate:
        # Semi-affiliate: only products in the parent affiliate's catalog
        parent_product_ids = list(
            PartnerPrice.objects.filter(
                buyer=profile.parent_affiliate.user,
                is_active=True,
            ).values_list("product_id", flat=True)
        )
        if parent_product_ids:
            products = base_qs.filter(pk__in=parent_product_ids)
        else:
            products = base_qs
    else:
        products = base_qs

    existing_prices = {
        pp.product_id: pp
        for pp in PartnerPrice.objects.filter(
            buyer=request.user, is_active=True
        ).select_related("product")
    }

    parent_prices = {}
    if is_semi and profile.parent_affiliate:
        parent_prices = {
            pp.product_id: pp
            for pp in PartnerPrice.objects.filter(
                buyer=profile.parent_affiliate.user, is_active=True
            )
        }

    catalog = []
    for product in products:
        pp = existing_prices.get(product.pk)
        loft_price = getattr(product, "loft_price", None)

        if is_semi and profile.parent_affiliate:
            parent_pp = parent_prices.get(product.pk)
            available_qty = product.quantity
        else:
            available_qty = product.quantity

        catalog.append({
            "product": product,
            "in_catalog": pp is not None,
            "partner_price": pp,
            "available_qty": available_qty,
            "purchase_price": (
                pp.purchase_price
                if pp
                else (loft_price.loft_default_wholesale_price if loft_price else None)
            ),
            "retail_price": (
                pp.retail_price
                if pp and pp.retail_price
                else (loft_price.loft_retail_price if loft_price else None)
            ),
            "price_configured": loft_price is not None,
            "primary_image": product.gallery_images.first(),
        })

    return render(request, "products/affiliate_catalog.html", {
        "catalog": catalog,
    })


@role_required(allowed_roles=[_AFF, _SEMI])
def affiliate_catalog_add(request, product_pk):
    """AJAX: Create PartnerPrice — affiliate adds product to their catalog with quantity"""
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    product = get_object_or_404(
        Product, pk=product_pk, status=Product.ProductStatus.APPROVED
    )
    loft_price = getattr(product, "loft_price", None)

    if not loft_price:
        return JsonResponse({
            "success": False,
            "errors": {"system": [_("Price not configured for this product.")]},
        })

    # Determine seller and purchase price
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role == _SEMI and profile.parent_affiliate:
        seller = profile.parent_affiliate.user
        parent_pp = PartnerPrice.objects.filter(
            product=product, buyer=seller, is_active=True
        ).first()
        purchase_price = (
            parent_pp.wholesale_price or parent_pp.purchase_price
            if parent_pp
            else loft_price.loft_default_wholesale_price
        )
    else:
        seller = product.user
        purchase_price = loft_price.loft_default_wholesale_price

    is_semi = profile.role == _SEMI
    pp, created = PartnerPrice.objects.update_or_create(
        product=product,
        seller=seller,
        buyer=request.user,
        defaults={
            "purchase_price": purchase_price,
            "wholesale_price": purchase_price if is_semi else loft_price.loft_retail_price,
            "retail_price": loft_price.loft_retail_price,
            "is_active": True,
        }
    )

    notify_user(
        request.user,
        _("Product Added!"),
        _('"%(product)s" has been added to your catalog with purchase price DZD%(price)s.')
        % {"product": product.title, "price": purchase_price},
        notification_type="success",
        link=reverse("dash:affiliate_catalog"),
    )

    if seller and seller != request.user:
        notify_user(
            seller,
            _("New Catalog Addition"),
            _('%(affiliate)s added "%(product)s" to their catalog.')
            % {
                "affiliate": request.user.get_full_name() or request.user.username,
                "product": product.title,
            },
            notification_type="info",
            link=reverse("dash:partner_price_list", kwargs={"product_pk": product.pk}),
        )

    return JsonResponse({
        "success": True,
        "message": _("Product added to your catalog."),
    })


@role_required(allowed_roles=[_AFF, _SEMI])
def catalog_update_pricing(request, product_pk):
    """AJAX: Update the affiliate's wholesale/retail prices for a product"""
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    pp = PartnerPrice.objects.filter(
        product_id=product_pk, buyer=request.user, is_active=True,
    ).first()

    if not pp:
        return JsonResponse({
            "success": False,
            "errors": {"system": [_("Product not in your catalog.")]},
        })

    wholesale = request.POST.get("wholesale_price")
    retail = request.POST.get("retail_price")

    changes = []
    if wholesale is not None and wholesale != "":
        wholesale = float(wholesale) if wholesale else None
        if wholesale != pp.wholesale_price:
            pp.wholesale_price = wholesale
            changes.append("wholesale")
    if retail is not None and retail != "":
        retail = float(retail) if retail else None
        if retail != pp.retail_price:
            pp.retail_price = retail
            changes.append("retail")
    pp.save()

    if changes:
        admins = User.objects.filter(
            models.Q(is_superuser=True) | models.Q(profile__role="admin"),
            is_active=True,
        ).exclude(pk=request.user.pk).distinct()
        for admin in admins:
            notify_user(
                admin,
                _("Affiliate Prices Updated"),
                _('%(affiliate)s updated %(field)s prices for "%(product)s".')
                % {
                    "affiliate": request.user.get_full_name() or request.user.username,
                    "field": " & ".join(changes),
                    "product": pp.product.title,
                },
                notification_type="info",
                link=reverse("dash:partner_price_list", kwargs={"product_pk": product_pk}),
            )

    return JsonResponse({
        "success": True,
        "message": _("Prices updated successfully."),
    })


@role_required(allowed_roles=[_AFF, _SEMI])
def affiliate_catalog_remove(request, product_pk):
    """AJAX: Deactivate PartnerPrice — remove product from catalog only.
    No stock or profit reversals — earnings stay as earned."""
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    product = get_object_or_404(Product, pk=product_pk)
    pp = PartnerPrice.objects.filter(
        product=product, buyer=request.user, is_active=True
    ).first()

    if not pp:
        return JsonResponse({"success": False, "errors": {"system": [_("Product not in your catalog.")]}})

    pp.is_active = False
    pp.save()

    return JsonResponse({
        "success": True,
        "message": _("Product removed from your catalog."),
    })


@role_required(allowed_roles=[_AFF, _SEMI])
def store_settings(request):
    """Affiliate store settings page (GET) + AJAX update (POST)"""
    profile = get_object_or_404(UserProfile, user=request.user)

    store, created = AffiliateStore.objects.get_or_create(
        affiliate=profile,
        defaults={"store_name": request.user.get_full_name() or request.user.username}
    )

    if request.method == "POST":
        store.store_name = request.POST.get("store_name", store.store_name)
        store.store_description = request.POST.get("store_description", "")
        store.header_bg_color = request.POST.get("header_bg_color", "#1a1a2e")

        if request.FILES.get("store_logo"):
            store.store_logo = request.FILES["store_logo"]
        elif request.POST.get("remove_logo") == "1":
            store.store_logo.delete(save=False)
            store.store_logo = None

        if request.FILES.get("store_banner"):
            store.store_banner = request.FILES["store_banner"]
        elif request.POST.get("remove_banner") == "1":
            store.store_banner.delete(save=False)
            store.store_banner = None

        store.save()
        return JsonResponse({
            "success": True,
            "message": _("Store settings saved."),
        })

    return render(request, "products/store_settings.html", {
        "store": store,
        "profile": profile,
        "title": _("My Store"),
    })


from django.db.models import Count
from dashboard.models import AffiliateStore, StoreVisit, Order
