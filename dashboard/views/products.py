from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.utils.translation import gettext as _
from django.db import transaction
from django.urls import reverse
from ..models import Product, Category, ProductImage, PartnerPrice, Notification, SupplierPrice, LoftPrice
from dashboard.decorator import role_required
from dashboard.utils import notify_user
from user_auth.models import UserProfile
from django.contrib.auth.models import User

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
            category.save()
            return JsonResponse({
                "success": True,
                "message": _("Category updated successfully"),
                "redirect_url": reverse("dash:category_list")
            })
        except Exception as e:
            return JsonResponse({"success": False, "errors": [str(e)]})
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
            category = Category.objects.create(name=name)
            return JsonResponse({
                "success": True,
                "message": _("Category created successfully"),
                "category": {"id": category.id, "name": category.name},
                "redirect_url": reverse("dash:category_list")
            })
        except Exception as e:
            return JsonResponse({"success": False, "errors": [str(e)]})
    return JsonResponse({"success": False}, status=400)

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.PROVIDER])
def product_list(request):
    """View to list products (filtered by user if not admin)"""
    query = request.GET.get("q", "")
    status_filter = request.GET.get("status", "")

    if request.user.is_superuser:
        products = Product.objects.all()
        if status_filter:
            products = products.filter(status=status_filter)
    else:
        products = Product.objects.filter(user=request.user)

    if query:
        products = products.filter(title__icontains=query)
    paginator = Paginator(products, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    categories = [{"value": c.id, "label": c.name} for c in Category.objects.all()]

    pending_count = Product.objects.filter(status=Product.ProductStatus.PENDING).count() if request.user.is_superuser else 0

    status_options = []
    if request.user.is_superuser:
        status_options = [
            ("", _("All")),
            ("pending", _("Pending")),
            ("approved", _("Approved")),
            ("rejected", _("Rejected")),
        ]

    context = {
        "page_obj": page_obj, "query": query, "categories": categories,
        "title": _("Product Management"),
        "status_filter": status_filter, "status_options": status_options,
        "pending_count": pending_count,
    }
    return render(request, "products/list.html", context)

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

        purchase_price = request.POST.get("loft_purchase_price", "0")
        if is_provider and not purchase_price:
            errors["loft_purchase_price"] = [_("Purchase price is required")]

        wholesale = request.POST.get("loft_wholesale_price")
        retail = request.POST.get("loft_retail_price")

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
                "quantity": quantity,
                "external_link": external_link,
                "tags": tags,
                "thumbnail": thumbnail,
                "model_3d": model_3d,
                "is_featured": request.POST.get("is_featured") == "on",
            }

            if is_provider:
                # Provider: auto-pending
                product_kwargs["status"] = Product.ProductStatus.PENDING
                product_kwargs["is_active"] = False
                product_kwargs["loft_wholesale_price"] = wholesale or None
                product_kwargs["loft_retail_price"] = retail or None
            else:
                # Admin can set everything directly
                product_kwargs["status"] = Product.ProductStatus.APPROVED
                product_kwargs["is_active"] = request.POST.get("is_active") == "on"
                product_kwargs["loft_wholesale_price"] = wholesale or None
                product_kwargs["loft_retail_price"] = retail or None

            product = Product.objects.create(**product_kwargs)

            for i, img in enumerate(request.FILES.getlist("gallery_images")):
                ProductImage.objects.create(product=product, image=img, order=i)

            # Create LoftPrice + SupplierPrice for admin-created products
            if not is_provider:
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
                        "supplier": request.user,
                        "loft_purchase_price": purchase_price or 0,
                    }
                )

            # Notify admins if provider created a pending product
            if is_provider:
                admins = User.objects.filter(is_superuser=True)
                for admin in admins:
                    notify_user(
                        admin,
                        _("New Product Requires Validation"),
                        _("%(name)s added '%(product)s' — set wholesale/retail prices to activate.")
                        % {"name": request.user.get_full_name() or request.user.username, "product": product.title},
                        notification_type=Notification.NotificationType.INFO,
                        link=reverse("dash:product_list") + "?status=pending"
                    )

            msg = _("Product submitted for review.") if is_provider else _("Product added successfully")
            return JsonResponse({
                "success": True, "message": msg,
                "redirect_url": reverse("dash:product_list")
            })
        except Exception as e:
            return JsonResponse({"success": False, "errors": {"system": [str(e)]}})

    categories = [{"value": c.id, "label": c.name} for c in Category.objects.all()]
    return render(request, "products/create.html", {
        "categories": categories, "values": {}, "is_provider": is_provider
    })

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.PROVIDER])
def product_update(request, pk):
    """View to update product (checks ownership)"""
    is_admin = request.user.is_superuser
    if is_admin:
        product = get_object_or_404(Product, pk=pk)
    else:
        product = get_object_or_404(Product, pk=pk, user=request.user)

    if request.method == "POST":
        product.title = request.POST.get("title")
        category_id = request.POST.get("category")
        product.description = request.POST.get("description")
        product.quantity = request.POST.get("quantity", 1)
        product.external_link = request.POST.get("external_link")
        product.tags = request.POST.get("tags")
        product.is_featured = request.POST.get("is_featured") == "on"

        if is_admin:
            product.loft_purchase_price = request.POST.get("loft_purchase_price", 0)
            product.loft_wholesale_price = request.POST.get("loft_wholesale_price") or None
            product.loft_retail_price = request.POST.get("loft_retail_price") or None
            product.is_active = request.POST.get("is_active") == "on"
        else:
            # Provider can only update their purchase price
            product.loft_purchase_price = request.POST.get("loft_purchase_price", 0)

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

        try:
            product.save()
            return JsonResponse({
                "success": True, "message": _("Product updated successfully"),
                "redirect_url": reverse("dash:product_list")
            })
        except Exception as e:
            return JsonResponse({"success": False, "errors": {"system": [str(e)]}})

    categories = [{"value": c.id, "label": c.name} for c in Category.objects.all()]
    return render(request, "products/edit.html", {
        "product": product, "categories": categories, "is_admin": is_admin
    })

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.PROVIDER])
def product_delete(request, pk):
    """AJAX delete for product (checks ownership)"""
    if request.method == "POST":
        if request.user.is_superuser:
            product = get_object_or_404(Product, pk=pk)
        else:
            product = get_object_or_404(Product, pk=pk, user=request.user)
        product.delete()
        return JsonResponse({"success": True, "message": _("Product removed")})
    return JsonResponse({"success": False}, status=400)


# ─── Admin Validation Views ─────────────────────────────────────────

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def product_approve(request, pk):
    """Approve a pending product — admin sets wholesale & retail prices"""
    if request.method == "POST":
        product = get_object_or_404(Product, pk=pk, status=Product.ProductStatus.PENDING)
        wholesale = request.POST.get("loft_wholesale_price")
        retail = request.POST.get("loft_retail_price")

        errors = {}
        if not wholesale:
            errors["loft_wholesale_price"] = [_("Wholesale price is required")]
        if not retail:
            errors["loft_retail_price"] = [_("Retail price is required")]
        try:
            if wholesale and float(wholesale) <= 0:
                errors["loft_wholesale_price"] = [_("Must be greater than zero")]
        except ValueError:
            errors["loft_wholesale_price"] = [_("Invalid number")]
        try:
            if retail and float(retail) <= 0:
                errors["loft_retail_price"] = [_("Must be greater than zero")]
        except ValueError:
            errors["loft_retail_price"] = [_("Invalid number")]

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        try:
            with transaction.atomic():
                product.loft_wholesale_price = wholesale
                product.loft_retail_price = retail
                product.status = Product.ProductStatus.APPROVED
                product.save()

                # Create/update LoftPrice
                LoftPrice.objects.update_or_create(
                    product=product,
                    defaults={
                        "loft_purchase_price": product.loft_purchase_price or 0,
                        "loft_default_wholesale_price": wholesale,
                        "loft_retail_price": retail,
                        "is_active": True,
                    }
                )

                # Create/update SupplierPrice
                if product.user:
                    SupplierPrice.objects.update_or_create(
                        product=product,
                        defaults={
                            "supplier": product.user,
                            "loft_purchase_price": product.loft_purchase_price or 0,
                        }
                    )

                # Notify the provider
                if product.user:
                    notify_user(
                        product.user,
                        _("Product Approved!"),
                        _("Your product '%(product)s' has been approved and is now live.")
                        % {"product": product.title},
                        notification_type=Notification.NotificationType.SUCCESS,
                        link=reverse("dash:product_list")
                    )

            return JsonResponse({
                "success": True,
                "message": _("Product approved successfully."),
                "redirect_url": reverse("dash:product_list") + "?status=approved"
            })
        except Exception as e:
            return JsonResponse({"success": False, "errors": {"system": [str(e)]}})

    return JsonResponse({"success": False}, status=400)


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def product_reject(request, pk):
    """Reject a pending product with optional reason"""
    if request.method == "POST":
        product = get_object_or_404(Product, pk=pk, status=Product.ProductStatus.PENDING)
        reason = request.POST.get("reason", "")

        try:
            with transaction.atomic():
                product.status = Product.ProductStatus.REJECTED
                product.rejection_reason = reason
                product.is_active = False
                product.save()

                if product.user:
                    notify_user(
                        product.user,
                        _("Product Rejected"),
                        _("Your product '%(product)s' was not approved.%(reason)s")
                        % {"product": product.title,
                           "reason": (_(" Reason: %s") % reason) if reason else ""},
                        notification_type=Notification.NotificationType.ERROR,
                        link=reverse("dash:product_list")
                    )

            return JsonResponse({
                "success": True,
                "message": _("Product rejected."),
                "redirect_url": reverse("dash:product_list") + "?status=rejected"
            })
        except Exception as e:
            return JsonResponse({"success": False, "errors": {"system": [str(e)]}})

    return JsonResponse({"success": False}, status=400)


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
