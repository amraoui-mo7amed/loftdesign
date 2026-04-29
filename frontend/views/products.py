from django.shortcuts import render, get_object_or_404
from dashboard.models import Product, Category
from django.db.models import Q

def product_list(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.all()
    
    category_id = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort = request.GET.get('sort', '-created_at')
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    if min_price:
        products = products.filter(price__gte=min_price)
    
    if max_price:
        products = products.filter(price__lte=max_price)
        
    products = products.order_by(sort)
    
    context = {
        "products": products,
        "categories": categories,
        "current_category": int(category_id) if category_id else None,
        "min_price": min_price,
        "max_price": max_price,
        "sort": sort,
    }
    return render(request, "products/products_list.html", context)

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    return render(request, "products/product_detail.html", {"product": product})
