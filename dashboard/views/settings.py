from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.urls import reverse
from dashboard.models import SiteSettings, SiteSettingsSliderImage, ContactRequest
from dashboard.decorator import role_required
from user_auth.models import UserProfile

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def settings_update(request):
    """View to update home page slider images dynamically"""
    settings_obj, created = SiteSettings.objects.get_or_create(id=1)
    
    if request.method == "POST":
        # Handle deletions
        delete_ids = request.POST.getlist("delete_slider_image")
        if delete_ids:
            SiteSettingsSliderImage.objects.filter(id__in=delete_ids, settings=settings_obj).delete()
            
        # Handle additions
        new_images = request.FILES.getlist("new_slider_image")
        for img in new_images:
            SiteSettingsSliderImage.objects.create(
                settings=settings_obj,
                image=img
            )
            
        try:
            settings_obj.save()
            return JsonResponse({
                "success": True,
                "message": _("Site settings updated successfully."),
                "redirect_url": reverse("dash:settings_update")
            })
        except Exception as e:
            return JsonResponse({"success": False, "errors": {"system": [str(e)]}})

    context = {
        "settings": settings_obj,
        "settings_images": settings_obj.slider_images.all()
    }
    return render(request, "settings/update.html", context)

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def contact_request_list(request):
    """View to list customer contact leads for admins"""
    leads = ContactRequest.objects.all()
    return render(request, "leads/list.html", {"leads": leads})

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def contact_request_delete(request, pk):
    """AJAX view to delete a contact lead"""
    if request.method == "POST":
        lead = get_object_or_404(ContactRequest, pk=pk)
        lead.delete()
        return JsonResponse({"success": True, "message": _("Contact request removed.")})
    return JsonResponse({"success": False}, status=400)
