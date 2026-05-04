from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils.translation import gettext as _
from django.db import transaction
from django.urls import reverse
from ..models import Product, Category

@login_required
def category_list(request):
    """View to list and manage categories with pagination"""
    categories_list = Category.objects.all().order_by("-created_at")
    paginator = Paginator(categories_list, 10)  # 10 categories per page
    
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    return render(request, "categories/list.html", {"categories": page_obj})

@login_required
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

@login_required
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

@login_required
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

@login_required
def product_list(request):
    """View to list all products"""
    query = request.GET.get("q", "")
    products = Product.objects.all()
    
    if query:
        products = products.filter(title__icontains=query)
        
    paginator = Paginator(products, 10)  # 10 products per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    categories = [{"value": c.id, "label": c.name} for c in Category.objects.all()]
    context = {
        "page_obj": page_obj,
        "query": query,
        "categories": categories,
        "title": _("Product Management")
    }
    return render(request, "products/list.html", context)

@login_required
def product_create(request):
    """View to create a new product with AJAX"""
    if request.method == "POST":
        title = request.POST.get("title")
        category_id = request.POST.get("category")
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
            category = None
            if category_id:
                category = Category.objects.get(id=category_id)

            Product.objects.create(
                title=title,
                category=category,
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
    
    categories = [{"value": c.id, "label": c.name} for c in Category.objects.all()]
    return render(request, "products/create.html", {"categories": categories, "values": {}})

@login_required
def product_update(request, pk):
    """View to update product with AJAX"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == "POST":
        product.title = request.POST.get("title")
        category_id = request.POST.get("category")
        product.description = request.POST.get("description")
        product.price = request.POST.get("price")
        product.external_link = request.POST.get("external_link")
        product.tags = request.POST.get("tags")
        product.is_active = request.POST.get("is_active") == "on"
        
        if category_id:
            product.category = Category.objects.get(id=category_id)
        else:
            product.category = None

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
            
    categories = [{"value": c.id, "label": c.name} for c in Category.objects.all()]
    return render(request, "products/edit.html", {"product": product, "categories": categories})

@login_required
def product_delete(request, pk):
    """AJAX delete for product"""
    if request.method == "POST":
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return JsonResponse({"success": True, "message": _("Product removed")})
    return JsonResponse({"success": False}, status=400)
