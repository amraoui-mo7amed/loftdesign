from django.shortcuts import render, get_object_or_404
from dashboard.models import Product

def product_list(request):
    products = Product.objects.filter(is_active=True)
    return render(request, "products/products_list.html", {"products": products})

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    return render(request, "products/product_detail.html", {"product": product})
