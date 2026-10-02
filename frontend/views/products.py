from django.urls import reverse
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from dashboard.models import Product, Category, PartnerPrice, AffiliateStore, AdminStore
from user_auth.models import UserProfile
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.translation import gettext as _

def product_list(request):
    if request.session.get("affiliate_code"):
        del request.session["affiliate_code"]
        request.session.modified = True

    products = Product.objects.filter(
        is_active=True, show_in_global_store=True, status=Product.ProductStatus.APPROVED
    )
    categories = Category.objects.all()
    
    category_id = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort = request.GET.get('sort', '-created_at')
    query = request.GET.get('q')
    
    if query:
        products = products.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(tags__icontains=query)
        )
    
    if category_id and not str(category_id).isdigit():
        category_id = None  # stale or hand-typed link: ignore instead of a 500
    if category_id:
        products = products.filter(category_id=category_id)
    
    from decimal import Decimal, InvalidOperation

    def _num(v):
        try:
            d = Decimal(str(v).replace(",", "."))
            return d if d.is_finite() and d >= 0 else None
        except (InvalidOperation, ValueError):
            return None

    min_price, max_price = _num(min_price) if min_price else None, _num(max_price) if max_price else None
    if min_price is not None:
        products = products.filter(loft_retail_price__gte=min_price)
    if max_price is not None:
        products = products.filter(loft_retail_price__lte=max_price)

    sort_fields = {"-created_at": "-created_at", "price": "loft_retail_price",
                   "-price": "-loft_retail_price", "title": "title"}
    if sort not in sort_fields:
        sort = "-created_at"
    products = products.order_by(sort_fields[sort])

    from django.core.paginator import Paginator
    total_count = products.count()
    page_obj = Paginator(products, 24).get_page(request.GET.get("page"))
    keep = request.GET.copy()
    keep.pop("page", None)
    base_url = "?" + (keep.urlencode() + "&" if keep else "")
    
    category_options = [{"value": "", "label": _("All Collections")}]
    category_options += [{"value": str(c.id), "label": c.name} for c in categories]
    
    sort_options = [
        {"value": "-created_at", "label": _("Newest First")},
        {"value": "price", "label": _("Price: Low to High")},
        {"value": "-price", "label": _("Price: High to Low")},
        {"value": "title", "label": _("Name: A-Z")},
    ]

    current_category_label = _("All Collections")
    if category_id:
        try:
            current_category_label = Category.objects.get(id=category_id).name
        except Category.DoesNotExist:
            pass

    current_sort_label = next((opt["label"] for opt in sort_options if opt["value"] == sort), _("Newest First"))

    context = {
        "products": page_obj,
        "page_obj": page_obj,
        "base_url": base_url,
        "total_count": total_count,
        "categories": categories,
        "category_options": category_options,
        "sort_options": sort_options,
        "current_category": category_id,
        "current_category_label": current_category_label,
        "current_sort_label": current_sort_label,
        "min_price": min_price,
        "max_price": max_price,
        "sort": sort,
        "query": query,
    }
    return render(request, "products/products_list.html", context)

from dashboard.utils import get_algeria_locations

def product_detail(request, pk):
    # Check query param first (for shared links), fall back to session
    affiliate_code = request.GET.get("affiliate")
    admin_store_param = request.GET.get("admin_store")
    provider_username = request.GET.get("provider")
    product = get_object_or_404(
        Product, pk=pk, is_active=True, status=Product.ProductStatus.APPROVED
    )
    wilaya_options, communes_data = get_algeria_locations()
    if affiliate_code:
        request.session["affiliate_code"] = affiliate_code
        request.session.modified = True
    else:
        request.session.pop("affiliate_code", None)
        request.session.modified = True

    admin_store_obj = None
    if admin_store_param and product.show_in_admin_store:
        admin_store_obj = AdminStore.objects.filter(is_active=True).first()

    provider = None
    provider_store_obj = None
    if provider_username:
        try:
            user = User.objects.get(username=provider_username, is_active=True)
            profile = getattr(user, "profile", None)
            if (
                profile is not None
                and profile.is_approved
                and profile.role == UserProfile.roleChoices.PROVIDER
                and product.user_id == user.id
            ):
                provider = profile
                provider_store_obj, _ = AffiliateStore.objects.get_or_create(
                    affiliate=profile,
                    defaults={"store_name": user.get_full_name() or user.username},
                )
        except User.DoesNotExist:
            provider = provider_store_obj = None

    if affiliate_code:
        try:
            profile = UserProfile.objects.get(affiliate_code=affiliate_code, is_approved=True)
        except UserProfile.DoesNotExist:
            profile = None

        if profile:
            partner_price = PartnerPrice.objects.filter(
                product=product, buyer=profile.user, is_active=True
            ).first()
            if partner_price:
                store, _ = AffiliateStore.objects.get_or_create(
                    affiliate=profile,
                    defaults={"store_name": profile.user.get_full_name() or profile.user.username},
                )
                template = "products/affiliate_product_detail.html"
            else:
                profile = store = partner_price = None
                template = "products/product_detail.html"
        else:
            profile = store = partner_price = None
            template = "products/product_detail.html"
    elif provider_store_obj:
        store = provider_store_obj
        profile = provider
        partner_price = None
        template = "products/provider_product_detail.html"
    elif admin_store_obj:
        profile = store = partner_price = None
        template = "products/admin_product_detail.html"
    else:
        profile = store = partner_price = None
        template = "products/product_detail.html"

    items = product.items.filter(is_active=True).prefetch_related("gallery_images")

    return render(request, template, {
        "product": product,
        "wilaya_options": wilaya_options,
        "communes_data": communes_data,
        "profile": profile,
        "store": store,
        "partner_price": partner_price,
        "items": items,
        "admin_store": admin_store_obj,
    })


def product_by_boid(request, boid):
    """Permanent product link used inside BIM/IFC files and 360 hotspots."""
    from django.shortcuts import redirect
    product = get_object_or_404(Product, bilnov_object_id__iexact=boid.strip())
    url = reverse("frontend:product_detail", args=[product.pk])
    query = request.GET.urlencode()
    return redirect(f"{url}?{query}" if query else url)


def product_viewer_3d(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True, status=Product.ProductStatus.APPROVED)
    if not product.model_3d:
        raise Http404(_("No 3D model available for this product"))
    back = request.GET.get("back")
    code = request.GET.get("code")
    return render(request, "products/product_viewer_3d.html", {
        "product": product,
        "back": back,
        "code": code,
    })
