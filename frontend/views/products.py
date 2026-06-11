from django.shortcuts import render, get_object_or_404
from django.http import Http404
from dashboard.models import Product, Category, PartnerPrice, AffiliateStore
from user_auth.models import UserProfile
from django.db.models import Q
from django.utils.translation import gettext as _

def product_list(request):
    if request.session.get("affiliate_code"):
        del request.session["affiliate_code"]
        request.session.modified = True

    products = Product.objects.filter(is_active=True)
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
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    if min_price:
        products = products.filter(price__gte=min_price)
    
    if max_price:
        products = products.filter(price__lte=max_price)
        
    products = products.order_by(sort)
    
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
        "products": products,
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
    product = get_object_or_404(Product, pk=pk, is_active=True)
    wilaya_options, communes_data = get_algeria_locations()

    affiliate_code = request.session.get("affiliate_code")
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
    else:
        profile = store = partner_price = None
        template = "products/product_detail.html"

    return render(request, template, {
        "product": product,
        "wilaya_options": wilaya_options,
        "communes_data": communes_data,
        "profile": profile,
        "store": store,
        "partner_price": partner_price,
    })


def product_viewer_3d(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    if not product.model_3d:
        raise Http404(_("No 3D model available for this product"))
    return render(request, "products/product_viewer_3d.html", {"product": product})
