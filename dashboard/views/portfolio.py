from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils.translation import gettext as _
from django.db import transaction
from ..models import Portfolio, PortfolioGallery
from django.urls import reverse

@login_required
def portfolio_list(request):
    """View to list all portfolio projects"""
    query = request.GET.get("q", "")
    portfolios = Portfolio.objects.all()
    
    if query:
        portfolios = portfolios.filter(title__icontains=query)
        
    paginator = Paginator(portfolios, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    context = {
        "page_obj": page_obj,
        "query": query,
        "title": _("Portfolio Management")
    }
    return render(request, "portfolio/list.html", context)

@login_required
def portfolio_create(request):
    """View to create a new portfolio project with manual HTML form"""
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        tags = request.POST.get("tags")
        thumbnail = request.FILES.get("thumbnail")
        img_360 = request.FILES.get("img_360")
        
        # Gallery images
        gallery_images = request.FILES.getlist("gallery_images")
        
        errors = {}
        
        if not all([title, description, thumbnail, img_360, gallery_images]):
            errors["title"] = _("All fields are required")

        if errors:
            return JsonResponse({
                "success": False,
                "errors": errors
            })
        try:
            with transaction.atomic():
                portfolio = Portfolio.objects.create(
                    title=title,
                    description=description,
                    tags=tags,
                    thumbnail=thumbnail,
                    img_360=img_360
                )
                
                for img in gallery_images:
                    PortfolioGallery.objects.create(
                        portfolio=portfolio,
                        image=img
                    )
                
                return JsonResponse({
                    "success": True,
                    "message": _("Project created successfully"),
                    "redirect_url": reverse("dash:portfolio_list")
                })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            })
    
    return render(request, "portfolio/create.html")

@login_required
def portfolio_update(request, pk):
    """View to update an existing portfolio project with manual HTML form and AJAX"""
    portfolio = get_object_or_404(Portfolio, pk=pk)
    
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        tags = request.POST.get("tags")
        thumbnail = request.FILES.get("thumbnail")
        img_360 = request.FILES.get("img_360")
        
        # Gallery images (Add new ones)
        new_gallery_images = request.FILES.getlist("gallery_images")
        # Handle deletions
        delete_images = request.POST.getlist("delete_images")
        
        errors = {}
        if not all([title, description]):
            errors["title"] = _("Title and Description are required")

        if errors:
            return JsonResponse({
                "success": False,
                "errors": errors
            })

        try:
            with transaction.atomic():
                portfolio.title = title
                portfolio.description = description
                portfolio.tags = tags
                
                if thumbnail:
                    portfolio.thumbnail = thumbnail
                if img_360:
                    portfolio.img_360 = img_360
                
                portfolio.save()
                
                # Delete selected images
                if delete_images:
                    PortfolioGallery.objects.filter(id__in=delete_images, portfolio=portfolio).delete()
                    
                # Add new images
                for img in new_gallery_images:
                    PortfolioGallery.objects.create(
                        portfolio=portfolio,
                        image=img
                    )
                    
                return JsonResponse({
                    "success": True,
                    "message": _("Project updated successfully"),
                    "redirect_url": reverse("dash:portfolio_list")
                })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            })
            
    return render(request, "portfolio/edit.html", {
        "portfolio": portfolio,
        "title": _("Edit Project")
    })

@login_required
def portfolio_delete(request, pk):
    """AJAX view to delete a portfolio project"""
    if request.method == "POST":
        portfolio = get_object_or_404(Portfolio, pk=pk)
        portfolio.delete()
        return JsonResponse({
            "success": True,
            "message": _("Project deleted successfully")
        })
    return JsonResponse({"success": False, "message": _("Invalid request")}, status=400)
