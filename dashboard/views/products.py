import re
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.utils.translation import gettext as _
from django.urls import reverse
from ..models import Product, Category, ProductImage, ProductItem, ProductItemImage, PartnerPrice, Notification, SupplierPrice, LoftPrice, ProductAsset, Manufacturer
from dashboard.decorator import role_required
from dashboard.utils import notify_user
from user_auth.models import UserProfile
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

def _category_code(request):
    """3 uppercase letters used in new Bilnov Object IDs (existing IDs never change)."""
    return re.sub(r"[^A-Z]", "", (request.POST.get("code") or "").upper())[:3]


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def category_list(request):
    """View to list and manage categories with pagination"""
    categories_list = Category.objects.all().order_by("-created_at")
    paginator = Paginator(categories_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "categories/list.html", {"categories": page_obj})

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def category_update(request, pk):
    """AJAX view to update category name"""
    if request.method == "POST":
        category = get_object_or_404(Category, pk=pk)
        name = request.POST.get("name")
        if not name:
            return JsonResponse({"success": False, "errors": [_("Category name is required")]})
        try:
            category.name = name
            category.code = _category_code(request)
            category.save()
            return JsonResponse({
                "success": True,
                "message": _("Category updated successfully"),
                "redirect_url": reverse("dash:category_list")
            })
        except Exception as e:
            logger.exception("dashboard/views/products.py: request failed")
            return JsonResponse({"success": False, "errors": [_("Something went wrong. Please try again.")]})
    return JsonResponse({"success": False}, status=400)

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def category_delete(request, pk):
    """AJAX view to delete category"""
    if request.method == "POST":
        category = get_object_or_404(Category, pk=pk)
        category.delete()
        return JsonResponse({
            "success": True,
            "message": _("Category deleted successfully"),
            "redirect_url": reverse("dash:category_list")
        })
    return JsonResponse({"success": False}, status=400)

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def category_create(request):
    """AJAX view to create a new category"""
    if request.method == "POST":
        name = request.POST.get("name")
        if not name:
            return JsonResponse({"success": False, "errors": [_("Category name is required")]})
        try:
            category = Category.objects.create(name=name, code=_category_code(request))
            return JsonResponse({
                "success": True,
                "message": _("Category created successfully"),
                "category": {"id": category.id, "name": category.name},
                "redirect_url": reverse("dash:category_list")
            })
        except Exception as e:
            logger.exception("dashboard/views/products.py: request failed")
            return JsonResponse({"success": False, "errors": [_("Something went wrong. Please try again.")]})
    return JsonResponse({"success": False}, status=400)

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.PROVIDER])
def product_list(request):
    """View to list products (filtered by user if not admin)"""
    if not request.user.is_superuser:
        profile = getattr(request.user, "profile", None)
        if not profile or not profile.is_trusted:
            raise PermissionDenied(_("Only trusted providers can access this page."))

    query = request.GET.get("q", "")

    if request.user.is_superuser:
        products = Product.objects.all()
    else:
        products = Product.objects.filter(user=request.user)

    if query:
        products = products.filter(title__icontains=query)
    paginator = Paginator(products, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    categories = [{"value": c.id, "label": c.name} for c in Category.objects.all()]

    context = {
        "page_obj": page_obj, "query": query, "categories": categories,
        "title": _("Product Management"),
    }
    return render(request, "products/list.html", context)

def _dec(value, field, errors, required=False, allow_zero=False):
    """Parse a money field from POST into a Decimal (or None when empty)."""
    from decimal import Decimal, InvalidOperation
    value = (value or "").strip().replace(",", ".")
    if not value:
        if required:
            errors[field] = [_("This field is required")]
        return None
    try:
        d = Decimal(value).quantize(Decimal("0.01"))
    except InvalidOperation:
        errors[field] = [_("Invalid number")]
        return None
    if d < 0 or (d == 0 and not allow_zero):
        errors[field] = [_("Must be greater than zero")]
        return None
    return d


def _parse_pricing(post, is_provider):
    """Read and validate the pricing block of the product form.

    Rules: purchase <= wholesale <= retail, the supplier's affiliate price sits
    between purchase and retail, and the professional price between wholesale
    and retail, otherwise commissions computed later would be negative.
    """
    errors = {}
    p = {
        "purchase": _dec(post.get("loft_purchase_price"), "loft_purchase_price", errors,
                         required=is_provider, allow_zero=not is_provider),
        "wholesale": _dec(post.get("loft_wholesale_price"), "loft_wholesale_price", errors, required=is_provider),
        "retail": _dec(post.get("loft_retail_price"), "loft_retail_price", errors, required=is_provider),
        "affiliate": _dec(post.get("affiliate_wholesale_price"), "affiliate_wholesale_price", errors),
        "pro": _dec(post.get("pro_price"), "pro_price", errors),
        "eur": _dec(post.get("price_eur"), "price_eur", errors),
    }
    purchase = p["purchase"] or 0
    w, r = p["wholesale"], p["retail"]
    if w is not None and w < purchase:
        errors.setdefault("loft_wholesale_price", [_("Wholesale price must be at least the purchase price")])
    if w is not None and r is not None and r < w:
        errors.setdefault("loft_retail_price", [_("Retail price must be at least the wholesale price")])
    a = p["affiliate"]
    if a is not None and (a < purchase or (r is not None and a > r)):
        errors.setdefault("affiliate_wholesale_price", [_("Affiliate price must be between the purchase and retail prices")])
    pro = p["pro"]
    if pro is not None and ((w is not None and pro < w) or (r is not None and pro > r)):
        errors.setdefault("pro_price", [_("Professional price must be between the wholesale and retail prices")])
    if p["purchase"] is None:
        p["purchase"] = 0
    return p, errors

def _manufacturer_from_post(post):
    """Fabricant saisi par nom : réutilise la fiche existante (même nom) ou la crée."""
    name = (post.get("manufacturer") or "").strip()[:255]
    if not name:
        return None
    found = Manufacturer.objects.filter(name__iexact=name).first()
    return found or Manufacturer.objects.create(name=name)


def _save_asset(request, product):
    """Attach the uploaded design file (if any) as a new version."""
    upload = request.FILES.get("asset_file")
    fmt = request.POST.get("asset_format")
    if not upload or fmt not in ProductAsset.Format.values:
        return
    post = request.POST
    unit = post.get("asset_unit")
    polygons = (post.get("asset_polygons") or "").strip()
    ProductAsset.objects.create(
        product=product, file_format=fmt, file=upload,
        unit=unit if unit in ProductAsset.Unit.values else ProductAsset.Unit.MM,
        scale=(post.get("asset_scale") or "1:1").strip()[:20] or "1:1",
        polygon_count=int(polygons) if polygons.isdigit() else None,
        compatibility=(post.get("asset_compatibility") or "").strip()[:120],
    )


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.PROVIDER])
def product_create(request):
    """View to create a new product with pricing workflow"""
    is_provider = not request.user.is_superuser

    if is_provider:
        profile = getattr(request.user, "profile", None)
        if not profile or not profile.is_trusted:
            raise PermissionDenied(_("Only trusted providers can create products."))

    if request.method == "POST":
        title = request.POST.get("title")
        category_id = request.POST.get("category")
        description = request.POST.get("description")
        quantity = request.POST.get("quantity", 1)
        external_link = request.POST.get("external_link")
        tags = request.POST.get("tags")
        thumbnail = request.FILES.get("thumbnail")
        model_3d = request.FILES.get("model_3d")

        errors = {}
        if not title:
            errors["title"] = [_("Title is required")]
        if not thumbnail:
            errors["thumbnail"] = [_("Thumbnail is required")]

        pricing, price_errors = _parse_pricing(request.POST, is_provider)
        errors.update(price_errors)
        purchase_price, wholesale, retail = pricing["purchase"], pricing["wholesale"], pricing["retail"]
        if errors:
            return JsonResponse({"success": False, "errors": errors})

        try:
            category = None
            if category_id:
                category = Category.objects.get(id=category_id)

            product_kwargs = {
                "user": request.user,
                "title": title,
                "category": category,
                "description": description,
                "loft_purchase_price": purchase_price or 0,
                "price_eur": pricing["eur"],
                "pro_price": pricing["pro"],
                "quantity": quantity,
                "external_link": external_link,
                "tags": tags,
                "thumbnail": thumbnail,
                "model_3d": model_3d,
                "is_featured": request.POST.get("is_featured") == "on",
                "brand": (request.POST.get("brand") or "").strip()[:255],
                "collection": (request.POST.get("collection") or "").strip()[:255],
                "manufacturer": _manufacturer_from_post(request.POST),
                "manufacturer_reference": (request.POST.get("manufacturer_reference") or "").strip()[:100],
            }

            product_kwargs["status"] = Product.ProductStatus.APPROVED
            product_kwargs["is_active"] = request.POST.get("is_active") == "on"
            product_kwargs["loft_wholesale_price"] = wholesale or None
            product_kwargs["loft_retail_price"] = retail or None

            product = Product.objects.create(**product_kwargs)

            for i, img in enumerate(request.FILES.getlist("gallery_images")):
                ProductImage.objects.create(product=product, image=img, order=i)
            _save_asset(request, product)

            LoftPrice.objects.update_or_create(
                product=product,
                defaults={
                    "loft_purchase_price": purchase_price or 0,
                    "loft_default_wholesale_price": wholesale or 0,
                    "loft_retail_price": retail or 0,
                    "is_active": True,
                }
            )
            SupplierPrice.objects.update_or_create(
                product=product,
                defaults={
                    "supplier": product.user or request.user,
                    "loft_purchase_price": purchase_price or 0,
                    "affiliate_wholesale_price": pricing["affiliate"] or wholesale or None,
                }
            )

            # Create variants (items) if submitted
            i = 0
            while request.POST.get(f"items[{i}][name]"):
                name = request.POST.get(f"items[{i}][name]")
                if name.strip():
                    color = request.POST.get(f"items[{i}][color]", "")
                    dimensions = request.POST.get(f"items[{i}][dimensions]", "")
                    stock = request.POST.get(f"items[{i}][stock_quantity]", 0)
                    thumb = request.FILES.get(f"items[{i}][thumbnail]")

                    item = ProductItem.objects.create(
                        product=product,
                        name=name.strip(),
                        color=color,
                        dimensions=dimensions,
                        stock_quantity=stock or 0,
                        thumbnail=thumb,
                        order=i,
                    )

                    for j, img in enumerate(request.FILES.getlist(f"items[{i}][gallery]")):
                        ProductItemImage.objects.create(item=item, image=img, order=j)
                i += 1

            items_qs = product.items.filter(is_active=True)
            if items_qs.exists():
                product.quantity = sum(item.stock_quantity for item in items_qs)
                product.save(update_fields=["quantity"])

            return JsonResponse({
                "success": True, "message": _("Product added successfully"),
                "redirect_url": reverse("dash:product_list")
            })
        except Exception:
            logger.exception("product_create failed")
            return JsonResponse({"success": False, "errors": {"system": [_("The product could not be saved. Please try again.")]}})

    categories = [{"value": c.id, "label": c.name} for c in Category.objects.all()]
    return render(request, "products/create.html", {
        "categories": categories, "values": {}, "is_provider": is_provider,
        "asset_formats": ProductAsset.Format.choices,
        "asset_units": ProductAsset.Unit.choices,
        "manufacturers": Manufacturer.objects.values_list("name", flat=True),
    })

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.PROVIDER])
def product_update(request, pk):
    """View to update product (checks ownership)"""
    if not request.user.is_superuser:
        profile = getattr(request.user, "profile", None)
        if not profile or not profile.is_trusted:
            raise PermissionDenied(_("Only trusted providers can access this page."))

    is_admin = request.user.is_superuser
    if is_admin:
        product = get_object_or_404(Product, pk=pk)
    else:
        product = get_object_or_404(Product, pk=pk, user=request.user)

    # Snapshot old prices for PriceHistory
    old_purchase = product.loft_purchase_price
    old_wholesale = product.loft_wholesale_price
    old_retail = product.loft_retail_price

    if request.method == "POST":
        product.title = request.POST.get("title")
        category_id = request.POST.get("category")
        product.description = request.POST.get("description")
        items_qs = product.items.filter(is_active=True)
        if items_qs.exists():
            product.quantity = sum(item.stock_quantity for item in items_qs)
        else:
            product.quantity = request.POST.get("quantity") or product.quantity
        product.external_link = request.POST.get("external_link")
        product.tags = request.POST.get("tags")
        product.is_featured = request.POST.get("is_featured") == "on"
        product.brand = (request.POST.get("brand") or "").strip()[:255]
        product.collection = (request.POST.get("collection") or "").strip()[:255]
        product.manufacturer = _manufacturer_from_post(request.POST)
        product.manufacturer_reference = (request.POST.get("manufacturer_reference") or "").strip()[:100]

        pricing, price_errors = _parse_pricing(request.POST, not is_admin)
        if price_errors:
            return JsonResponse({"success": False, "errors": price_errors})
        product.loft_purchase_price = pricing["purchase"]
        product.loft_wholesale_price = pricing["wholesale"]
        product.loft_retail_price = pricing["retail"]
        product.price_eur = pricing["eur"]
        product.pro_price = pricing["pro"]

        if is_admin:

            product.is_active = request.POST.get("is_active") == "on"

            # Auto-approve if product is PENDING and wholesale + retail are set
            if (product.status == Product.ProductStatus.PENDING
                    and product.loft_wholesale_price and product.loft_retail_price):
                product.status = Product.ProductStatus.APPROVED
                product.is_active = True
                if product.user:
                    notify_user(
                        product.user,
                        _("Product Approved!"),
                        _("Your product '%(product)s' has been approved and is now live.")
                        % {"product": product.title},
                        notification_type=Notification.NotificationType.SUCCESS,
                        link=reverse("dash:product_list")
                    )

            LoftPrice.objects.update_or_create(
                product=product,
                defaults={
                    "loft_purchase_price": product.loft_purchase_price or 0,
                    "loft_default_wholesale_price": product.loft_wholesale_price or 0,
                    "loft_retail_price": product.loft_retail_price or 0,
                    "is_active": True,
                }
            )
            if product.user:
                SupplierPrice.objects.update_or_create(
                    product=product,
                    defaults={
                        "supplier": product.user,
                        "loft_purchase_price": product.loft_purchase_price or 0,
                        "affiliate_wholesale_price": pricing["affiliate"],
                    }
                )
        else:
            # Trusted providers set their own prices; _parse_pricing keeps them coherent.
            LoftPrice.objects.update_or_create(
                product=product,
                defaults={
                    "loft_purchase_price": product.loft_purchase_price or 0,
                    "loft_default_wholesale_price": product.loft_wholesale_price or 0,
                    "loft_retail_price": product.loft_retail_price or 0,
                    "is_active": True,
                }
            )
            if product.user:
                SupplierPrice.objects.update_or_create(
                    product=product,
                    defaults={
                        "supplier": product.user,
                        "loft_purchase_price": product.loft_purchase_price or 0,
                        "affiliate_wholesale_price": pricing["affiliate"],
                    }
                )

        if category_id:
            product.category = Category.objects.get(id=category_id)
        else:
            product.category = None

        if request.FILES.get("thumbnail"):
            product.thumbnail = request.FILES.get("thumbnail")
        if request.FILES.get("model_3d"):
            product.model_3d = request.FILES.get("model_3d")

        remove_ids = request.POST.get("remove_gallery_ids", "")
        if remove_ids:
            ProductImage.objects.filter(
                id__in=[int(x) for x in remove_ids.split(",") if x.strip()],
                product=product
            ).delete()

        for i, img in enumerate(request.FILES.getlist("gallery_images")):
            ProductImage.objects.create(product=product, image=img, order=i)

        # Log price changes
        from dashboard.utils import log_price_change
        if is_admin:
            if product.loft_purchase_price != old_purchase:
                log_price_change(product, request.user, "loft_purchase_price", old_purchase, product.loft_purchase_price)
            if product.loft_wholesale_price != old_wholesale:
                log_price_change(product, request.user, "loft_wholesale", old_wholesale, product.loft_wholesale_price)
            if product.loft_retail_price != old_retail:
                log_price_change(product, request.user, "loft_retail", old_retail, product.loft_retail_price)
        else:
            if product.loft_purchase_price != old_purchase:
                log_price_change(product, request.user, "loft_purchase_price", old_purchase, product.loft_purchase_price)
            if product.loft_wholesale_price != old_wholesale:
                log_price_change(product, request.user, "loft_wholesale", old_wholesale, product.loft_wholesale_price)
            if product.loft_retail_price != old_retail:
                log_price_change(product, request.user, "loft_retail", old_retail, product.loft_retail_price)

        try:
            product.save()
            _save_asset(request, product)
            return JsonResponse({
                "success": True, "message": _("Product updated successfully"),
                "redirect_url": reverse("dash:product_list")
            })
        except Exception:
            logger.exception("product_update failed")
            return JsonResponse({"success": False, "errors": {"system": [_("The product could not be saved. Please try again.")]}})

    categories = [{"value": c.id, "label": c.name} for c in Category.objects.all()]
    price_history = product.price_history.select_related("user").order_by("-created_at")[:20]
    items = product.items.filter(is_active=True).prefetch_related("gallery_images")
    return render(request, "products/edit.html", {
        "product": product, "categories": categories, "is_admin": is_admin,
        "price_history": price_history, "items": items,
        "asset_formats": ProductAsset.Format.choices,
        "asset_units": ProductAsset.Unit.choices,
        "manufacturers": Manufacturer.objects.values_list("name", flat=True),
    })

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.PROVIDER])
def product_delete(request, pk):
    """AJAX delete for product (checks ownership)"""
    if not request.user.is_superuser:
        profile = getattr(request.user, "profile", None)
        if not profile or not profile.is_trusted:
            return JsonResponse({"success": False, "message": _("Permission denied.")}, status=403)

    if request.method == "POST":
        if request.user.is_superuser:
            product = get_object_or_404(Product, pk=pk)
        else:
            product = get_object_or_404(Product, pk=pk, user=request.user)
        product.delete()
        return JsonResponse({"success": True, "message": _("Product removed")})
    return JsonResponse({"success": False}, status=400)


# ─── Global Store Toggle ────────────────────────────────────────────

@login_required
@require_POST
def product_toggle_global_store(request, pk):
    """AJAX: toggle show_in_global_store for a product (admin only)"""
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "message": _("Permission denied.")}, status=403)
    product = get_object_or_404(Product, pk=pk)
    product.show_in_global_store = not product.show_in_global_store
    product.save(update_fields=["show_in_global_store"])
    return JsonResponse({"success": True, "show_in_global_store": product.show_in_global_store})


# ─── PartnerPrice CRUD ──────────────────────────────────────────────

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def partner_price_list(request, product_pk):
    """List and manage custom partner prices for a product"""
    product = get_object_or_404(Product, pk=product_pk)
    prices = PartnerPrice.objects.filter(product=product).select_related("seller", "buyer")
    affiliate_profiles = UserProfile.objects.filter(
        role=UserProfile.roleChoices.AFFILIATE, is_approved=True
    ).select_related("user")
    affiliate_options = [
        {"value": p.user.id, "label": f"{p.user.get_full_name() or p.user.username} ({p.affiliate_code})"}
        for p in affiliate_profiles
    ]
    return render(request, "products/partner_price_list.html", {
        "product": product, "prices": prices, "affiliate_options": affiliate_options
    })


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def partner_price_create(request, product_pk):
    """AJAX: create a custom partner price"""
    if request.method == "POST":
        product = get_object_or_404(Product, pk=product_pk)
        buyer_id = request.POST.get("buyer_id")
        purchase_price = request.POST.get("purchase_price")

        errors = {}
        if not buyer_id:
            errors["buyer_id"] = [_("Affiliate is required")]
        if not purchase_price:
            errors["purchase_price"] = [_("Purchase price is required")]

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        try:
            buyer = User.objects.get(pk=buyer_id)
        except User.DoesNotExist:
            return JsonResponse({"success": False, "errors": {"buyer_id": [_("User not found")]}})

        PartnerPrice.objects.update_or_create(
            product=product, seller=request.user, buyer=buyer,
            defaults={
                "purchase_price": purchase_price,
                "wholesale_price": request.POST.get("wholesale_price") or None,
                "retail_price": request.POST.get("retail_price") or None,
                "is_active": True,
            }
        )

        notify_user(
            buyer,
            _("Custom Price Set!"),
            _('Admin set a custom price for "%(product)s" — DZD%(price)s.')
            % {"product": product.title, "price": purchase_price},
            notification_type="info",
            link=reverse("dash:catalog_details", kwargs={"product_pk": product_pk}),
        )

        return JsonResponse({
            "success": True,
            "message": _("Custom price set for %(name)s.") % {"name": buyer.get_full_name() or buyer.username},
            "redirect_url": reverse("dash:partner_price_list", kwargs={"product_pk": product_pk})
        })

    return JsonResponse({"success": False}, status=400)


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def partner_price_delete(request, pk):
    """AJAX: delete a partner price"""
    if request.method == "POST":
        pp = get_object_or_404(PartnerPrice, pk=pk)
        product_pk = pp.product.pk
        pp.delete()
        return JsonResponse({
            "success": True,
            "message": _("Custom price removed."),
            "redirect_url": reverse("dash:partner_price_list", kwargs={"product_pk": product_pk})
        })
    return JsonResponse({"success": False}, status=400)
