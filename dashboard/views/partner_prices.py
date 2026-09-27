from django.db import models
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model
from django.conf import settings
from django.template.loader import render_to_string
from ..decorator import role_required
from ..models import Product, PartnerPrice, LoftPrice, AffiliateStore, AdminStore, SupplierPrice
from ..utils import notify_user
from user_auth.models import UserProfile

User = get_user_model()


_SEMI = UserProfile.roleChoices.SEMI_AFFILIATE
_AFF = UserProfile.roleChoices.AFFILIATE


@role_required(allowed_roles=[_AFF, _SEMI])
def my_catalog(request):
    """List only products the affiliate has added to their catalog"""
    profile = get_object_or_404(UserProfile, user=request.user)
    is_semi = profile.role == _SEMI
    prices = PartnerPrice.objects.filter(
        buyer=request.user, is_active=True,
    ).select_related("product", "product__loft_price").prefetch_related("product__gallery_images")
    parent_prices = {}
    if is_semi:
        if profile.parent_affiliate:
            prices = prices.filter(seller=profile.parent_affiliate.user)
            parent_prices = {
                parent_price.product_id: parent_price
                for parent_price in PartnerPrice.objects.filter(
                    buyer=profile.parent_affiliate.user,
                    is_active=True,
                    seller_id=models.F("product__user_id"),
                )
            }
        else:
            prices = prices.none()

    catalog = []
    for pp in prices:
        product = pp.product
        loft_price = getattr(product, "loft_price", None)
        parent_pp = parent_prices.get(product.pk) if is_semi else None
        if is_semi:
            wholesale_price = (
                parent_pp.wholesale_price
                if parent_pp and parent_pp.wholesale_price is not None
                else (loft_price.loft_default_wholesale_price if loft_price else None)
            )
            retail_price = (
                parent_pp.retail_price
                if parent_pp and parent_pp.retail_price is not None
                else (loft_price.loft_retail_price if loft_price else None)
            )
        else:
            wholesale_price = pp.wholesale_price
            retail_price = pp.retail_price or (loft_price.loft_retail_price if loft_price else None)

        catalog.append({
            "product": product,
            "partner_price": pp,
            "purchase_price": pp.purchase_price,
            "wholesale_price": wholesale_price,
            "retail_price": retail_price,
            "primary_image": product.gallery_images.first(),
        })

    return render(request, "products/my_catalog.html", {
        "catalog": catalog,
        "is_semi": is_semi,
    })


@role_required(allowed_roles=[_AFF, _SEMI])
def catalog_details(request, product_pk):
    """Detail page for a product in the affiliate catalog"""
    product = get_object_or_404(
        Product, pk=product_pk, status=Product.ProductStatus.APPROVED, is_active=True,
    )

    profile = get_object_or_404(UserProfile, user=request.user)
    is_semi = profile.role == _SEMI

    # Provider-created affiliate may only view the creating provider's products.
    if not is_semi and profile.created_by is not None:
        creator = profile.created_by
        if (
            creator.role == UserProfile.roleChoices.PROVIDER
            and product.user_id != creator.user_id
        ):
            return HttpResponseForbidden(_("This product is not available to you."))

    loft_price = getattr(product, "loft_price", None)

    parent_pp = None
    if is_semi and profile.parent_affiliate:
        parent_pp = PartnerPrice.objects.filter(
            product=product,
            seller=product.user,
            buyer=profile.parent_affiliate.user,
            is_active=True,
        ).first()

    pp_filter = {
        "product": product,
        "buyer": request.user,
        "is_active": True,
    }
    if is_semi:
        if profile.parent_affiliate:
            pp_filter["seller"] = profile.parent_affiliate.user
            pp = PartnerPrice.objects.filter(**pp_filter).first()
        else:
            pp = None
    else:
        pp = PartnerPrice.objects.filter(**pp_filter).first()

    available_qty = product.quantity

    if is_semi:
        if parent_pp:
            ref_purchase = parent_pp.wholesale_price or parent_pp.purchase_price
            ref_retail = (
                parent_pp.retail_price
                or parent_pp.wholesale_price
                or parent_pp.purchase_price
            )
        else:
            ref_purchase = None
            ref_retail = None
    else:
        ref_purchase = loft_price.loft_default_wholesale_price if loft_price else None
        ref_retail = loft_price.loft_retail_price if loft_price else None

    return render(request, "products/catalog_details.html", {
        "product": product,
        "loft_price": loft_price,
        "partner_price": pp,
        "parent_pp": parent_pp,
        "in_catalog": pp is not None,
        "available_qty": available_qty,
        "purchase_price": (
            ref_purchase
            if is_semi
            else (pp.purchase_price if pp else ref_purchase)
        ),
        "retail_price": (
            ref_retail
            if is_semi
            else (pp.retail_price if pp and pp.retail_price else ref_retail)
        ),
        "is_semi": is_semi,
        "price_configured": loft_price is not None,
        "gallery": list(product.gallery_images.all()),
        "tags": [t.strip() for t in product.tags.split(",") if t.strip()] if product.tags else [],
    })


@role_required(allowed_roles=[_AFF, _SEMI])
def affiliate_catalog(request):
    """List approved products available to resell.
    Affiliates see all approved products, unless they were created by a
    provider — then they see only that provider's products.
    Semi-affiliates see only products in their parent affiliate's catalog.
    """
    profile = get_object_or_404(UserProfile, user=request.user)
    is_semi = profile.role == _SEMI

    base_qs = Product.objects.filter(
        status=Product.ProductStatus.APPROVED,
        is_active=True,
    ).select_related("user", "loft_price").prefetch_related("gallery_images")

    # Provider-created affiliate: only the creating provider's products.
    provider_scope = None
    if not is_semi:
        creator = profile.created_by
        if (
            creator is not None
            and creator.role == UserProfile.roleChoices.PROVIDER
        ):
            provider_scope = creator.user

    if provider_scope is not None:
        products = base_qs.filter(user=provider_scope)
    elif is_semi and profile.parent_affiliate:
        # Semi-affiliate: only products in the parent affiliate's catalog
        parent_product_ids = list(
            PartnerPrice.objects.filter(
                buyer=profile.parent_affiliate.user,
                is_active=True,
                seller_id=models.F("product__user_id"),
            ).values_list("product_id", flat=True)
        )
        if parent_product_ids:
            products = base_qs.filter(pk__in=parent_product_ids)
        elif is_semi:
            products = Product.objects.none()
        else:
            products = base_qs
    else:
        products = base_qs

    existing_price_query = PartnerPrice.objects.filter(
        buyer=request.user,
        is_active=True,
    )
    if is_semi:
        if profile.parent_affiliate:
            existing_price_query = existing_price_query.filter(
                seller=profile.parent_affiliate.user,
            )
        else:
            existing_price_query = existing_price_query.none()

    existing_prices = {
        pp.product_id: pp
        for pp in existing_price_query.select_related("product")
    }

    parent_prices = {}
    if is_semi and profile.parent_affiliate:
        parent_prices = {
            pp.product_id: pp
            for pp in PartnerPrice.objects.filter(
                buyer=profile.parent_affiliate.user,
                is_active=True,
                seller_id=models.F("product__user_id"),
            )
        }

    catalog = []
    for product in products:
        pp = existing_prices.get(product.pk)
        loft_price = getattr(product, "loft_price", None)

        parent_pp = parent_prices.get(product.pk) if is_semi else None
        available_qty = product.quantity

        if is_semi:
            purchase_price = (
                parent_pp.wholesale_price
                if parent_pp and parent_pp.wholesale_price is not None
                else (loft_price.loft_default_wholesale_price if loft_price else None)
            )
            retail_price = (
                parent_pp.retail_price
                if parent_pp and parent_pp.retail_price is not None
                else (loft_price.loft_retail_price if loft_price else None)
            )
        else:
            purchase_price = (
                pp.purchase_price
                if pp
                else (loft_price.loft_default_wholesale_price if loft_price else None)
            )
            retail_price = (
                pp.retail_price
                if pp and pp.retail_price
                else (loft_price.loft_retail_price if loft_price else None)
            )

        catalog.append({
            "product": product,
            "in_catalog": pp is not None,
            "partner_price": pp,
            "available_qty": available_qty,
            "purchase_price": purchase_price,
            "retail_price": retail_price,
            "price_configured": loft_price is not None,
            "primary_image": product.gallery_images.first(),
        })

    return render(request, "products/affiliate_catalog.html", {
        "catalog": catalog,
        "is_semi": is_semi,
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
    if profile.role == _SEMI:
        if not profile.parent_affiliate:
            return JsonResponse({
                "success": False,
                "errors": {"system": [_("No parent affiliate is assigned to your account.")]},
            })

        parent_pp = PartnerPrice.objects.filter(
            product=product,
            seller=product.user,
            buyer=profile.parent_affiliate.user,
            is_active=True,
        ).first()
        if not parent_pp:
            return JsonResponse({
                "success": False,
                "errors": {"system": [_("This product is not in your parent affiliate's catalog.")]},
            })

        purchase_price = parent_pp.wholesale_price or parent_pp.purchase_price
        seller = profile.parent_affiliate.user
    else:
        seller = product.user
        purchase_price = loft_price.loft_default_wholesale_price

        # Provider network: affiliate created by the provider who owns the product
        # buys at the provider-set wholesale price, so the provider earns the
        # network margin in place of Loft's.
        creator = profile.created_by
        if (
            creator is not None
            and creator.role == UserProfile.roleChoices.PROVIDER
            and product.user_id == creator.user_id
        ):
            sp = getattr(product, "supplier_price", None)
            if sp and sp.affiliate_wholesale_price:
                purchase_price = sp.affiliate_wholesale_price
            else:
                return JsonResponse({
                    "success": False,
                    "errors": {"system": [_("No wholesale price is set for your affiliates on this product.")]},
                })

    pp, created = PartnerPrice.objects.update_or_create(
        product=product,
        seller=seller,
        buyer=request.user,
        defaults={
            "purchase_price": purchase_price,
            "wholesale_price": loft_price.loft_retail_price,
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

    profile = get_object_or_404(UserProfile, user=request.user)
    pp_query = PartnerPrice.objects.filter(
        product_id=product_pk, buyer=request.user, is_active=True,
    )
    if profile.role == _SEMI:
        if profile.parent_affiliate:
            pp_query = pp_query.filter(seller=profile.parent_affiliate.user)
        else:
            pp_query = pp_query.none()
    pp = pp_query.first()

    if not pp:
        return JsonResponse({
            "success": False,
            "errors": {"system": [_("Product not in your catalog.")]},
        })

    wholesale = request.POST.get("wholesale_price")
    retail = request.POST.get("retail_price")

    changes = []
    old_wholesale = pp.wholesale_price
    old_retail = pp.retail_price
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
    if changes:
        from dashboard.utils import log_price_change
        if "wholesale" in changes:
            log_price_change(pp.product, request.user, "partner_wholesale", old_wholesale, pp.wholesale_price)
        if "retail" in changes:
            log_price_change(pp.product, request.user, "partner_retail", old_retail, pp.retail_price)
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
    profile = get_object_or_404(UserProfile, user=request.user)
    pp_query = PartnerPrice.objects.filter(
        product=product, buyer=request.user, is_active=True
    )
    if profile.role == _SEMI:
        if profile.parent_affiliate:
            pp_query = pp_query.filter(seller=profile.parent_affiliate.user)
        else:
            pp_query = pp_query.none()
    pp = pp_query.first()

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


@role_required(allowed_roles=[UserProfile.roleChoices.PROVIDER])
def provider_store_settings(request):
    """Provider store settings page (GET) + AJAX update (POST) — reuses AffiliateStore"""
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

    return render(request, "products/provider_store_settings.html", {
        "store": store,
        "profile": profile,
        "title": _("My Store"),
    })


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def admin_store_settings(request):
    """Admin store settings page (GET) + AJAX update (POST)"""
    store, created = AdminStore.objects.get_or_create(
        user=request.user,
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

    return render(request, "products/admin_store_settings.html", {
        "store": store,
        "title": _("My Store"),
    })


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def admin_store_catalog(request):
    """Product picker for admin store — toggle which products appear"""
    products = Product.objects.filter(status=Product.ProductStatus.APPROVED).order_by("-created_at")

    return render(request, "products/admin_store_catalog.html", {
        "products": products,
        "title": _("Store Products"),
    })


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def admin_store_catalog_toggle(request, product_pk):
    """AJAX toggle show_in_admin_store for a product"""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": _("Invalid request.")})

    product = get_object_or_404(Product, pk=product_pk)
    product.show_in_admin_store = not product.show_in_admin_store
    product.save(update_fields=["show_in_admin_store"])

    return JsonResponse({
        "success": True,
        "show_in_admin_store": product.show_in_admin_store,
        "message": _("Product updated."),
    })


from django.db.models import Count
from dashboard.models import AffiliateStore, StoreVisit, Order
