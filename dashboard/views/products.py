from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils.translation import gettext as _
from django.db import transaction
from django.urls import reverse
from ..models import Product

@login_required
def product_list(request):
    """View to list all products"""
    query = request.GET.get("q", "")
    products = Product.objects.all()
    
    if query:
        products = products.filter(title__icontains=query)
        
    paginator = Paginator(products, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    context = {
        "page_obj": page_obj,
        "query": query,
        "title": _("Product Management")
    }
    return render(request, "products/list.html", context)

@login_required
def product_create(request):
    """View to create a new product with AJAX"""
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        price = request.POST.get("price")
        external_link = request.POST.get("external_link")
        tags = request.POST.get("tags")
        thumbnail = request.FILES.get("thumbnail")
        is_active = request.POST.get("is_active") == "on"
        
        errors = {}
        if not title: errors["title"] = _("Title is required")
        if not price: errors["price"] = _("Price is required")
        if not thumbnail: errors["thumbnail"] = _("Thumbnail is required")

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        try:
            Product.objects.create(
                title=title,
                description=description,
                price=price,
                external_link=external_link,
                tags=tags,
                thumbnail=thumbnail,
                is_active=is_active
            )
            return JsonResponse({
                "success": True, 
                "message": _("Product added successfully"),
                "redirect_url": reverse("dash:product_list")
            })
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
            
    return render(request, "products/create.html", {"values": {}})

@login_required
def product_update(request, pk):
    """View to update product with AJAX"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == "POST":
        product.title = request.POST.get("title")
        product.description = request.POST.get("description")
        product.price = request.POST.get("price")
        product.external_link = request.POST.get("external_link")
        product.tags = request.POST.get("tags")
        product.is_active = request.POST.get("is_active") == "on"
        
        if request.FILES.get("thumbnail"):
            product.thumbnail = request.FILES.get("thumbnail")
            
        try:
            product.save()
            return JsonResponse({
                "success": True, 
                "message": _("Product updated successfully"),
                "redirect_url": reverse("dash:product_list")
            })
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
            
    return render(request, "products/edit.html", {"product": product})

@login_required
def product_delete(request, pk):
    """AJAX delete for product"""
    if request.method == "POST":
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return JsonResponse({"success": True, "message": _("Product removed")})
    return JsonResponse({"success": False}, status=400)
