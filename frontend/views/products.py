from django.shortcuts import render, get_object_or_404
from dashboard.models import Product, Category
from django.db.models import Q
from django.utils.translation import gettext as _

def product_list(request):
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

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    return render(request, "products/product_detail.html", {"product": product})
