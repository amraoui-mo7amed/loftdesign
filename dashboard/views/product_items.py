from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required
from dashboard.models import Product, ProductItem, ProductItemImage
from dashboard.decorator import role_required
from user_auth.models import UserProfile


_RC = UserProfile.roleChoices

@login_required
@role_required(allowed_roles=[_RC.ADMIN, _RC.PROVIDER])
def item_list(request, product_pk):
    product = get_object_or_404(Product, pk=product_pk)
    if not request.user.is_superuser and product.user != request.user:
        return JsonResponse({"success": False, "error": _("Permission denied.")}, status=403)
    items = product.items.filter(is_active=True).prefetch_related("gallery_images")
    data = []
    for item in items:
        thumb_url = item.thumbnail.url if item.thumbnail else ""
        images = [
            {"id": img.id, "url": img.image.url, "order": img.order}
            for img in item.gallery_images.all()
        ]
        data.append({
            "id": item.id,
            "name": item.name,
            "color": item.color,
            "dimensions": item.dimensions,
            "thumbnail": thumb_url,
            "stock_quantity": item.stock_quantity,
            "order": item.order,
            "gallery_images": images,
        })
    return JsonResponse({"success": True, "items": data})


def _sync_product_stock(product):
    total = sum(
        item.stock_quantity
        for item in product.items.filter(is_active=True)
    )
    Product.objects.filter(pk=product.pk).update(quantity=total)
    product.quantity = total


@login_required
@role_required(allowed_roles=[_RC.ADMIN, _RC.PROVIDER])
def item_create(request, product_pk):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)
    product = get_object_or_404(Product, pk=product_pk)
    if not request.user.is_superuser and product.user != request.user:
        return JsonResponse({"success": False, "error": _("Permission denied.")}, status=403)

    name = request.POST.get("name", "").strip()
    if not name:
        return JsonResponse({"success": False, "errors": {"name": [_("Item name is required.")]}})

    item = ProductItem.objects.create(
        product=product,
        name=name,
        color=request.POST.get("color", "").strip(),
        dimensions=request.POST.get("dimensions", "").strip(),
        stock_quantity=int(request.POST.get("stock_quantity", 0)),
    )

    if request.FILES.get("thumbnail"):
        item.thumbnail = request.FILES["thumbnail"]
        item.save()

    for i, img in enumerate(request.FILES.getlist("gallery_images")):
        ProductItemImage.objects.create(item=item, image=img, order=i)

    _sync_product_stock(product)

    return JsonResponse({
        "success": True,
        "message": _("Item added."),
        "product_quantity": product.quantity,
        "item": {
            "id": item.id,
            "name": item.name,
            "color": item.color,
            "dimensions": item.dimensions,
            "thumbnail": item.thumbnail.url if item.thumbnail else "",
            "stock_quantity": item.stock_quantity,
        }
    })


@login_required
@role_required(allowed_roles=[_RC.ADMIN, _RC.PROVIDER])
def item_update(request, pk):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)
    item = get_object_or_404(ProductItem, pk=pk)
    product = item.product
    if not request.user.is_superuser and product.user != request.user:
        return JsonResponse({"success": False, "error": _("Permission denied.")}, status=403)

    name = request.POST.get("name", "").strip()
    if not name:
        return JsonResponse({"success": False, "errors": {"name": [_("Item name is required.")]}})

    item.name = name
    item.color = request.POST.get("color", "").strip()
    item.dimensions = request.POST.get("dimensions", "").strip()
    item.stock_quantity = int(request.POST.get("stock_quantity", 0))

    if request.FILES.get("thumbnail"):
        item.thumbnail = request.FILES["thumbnail"]

    item.save()

    remove_images = request.POST.get("remove_image_ids", "")
    if remove_images:
        ids = [int(x) for x in remove_images.split(",") if x.strip()]
        ProductItemImage.objects.filter(id__in=ids, item=item).delete()

    existing_ids = set(item.gallery_images.values_list("id", flat=True))
    next_order = max(existing_ids) + 1 if existing_ids else 0
    for i, img in enumerate(request.FILES.getlist("gallery_images")):
        ProductItemImage.objects.create(item=item, image=img, order=next_order + i)

    _sync_product_stock(product)

    return JsonResponse({
        "success": True,
        "message": _("Item updated."),
        "product_quantity": product.quantity,
        "item": {
            "id": item.id,
            "name": item.name,
            "color": item.color,
            "dimensions": item.dimensions,
            "thumbnail": item.thumbnail.url if item.thumbnail else "",
            "stock_quantity": item.stock_quantity,
        }
    })


@login_required
@role_required(allowed_roles=[_RC.ADMIN, _RC.PROVIDER])
def item_delete(request, pk):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)
    item = get_object_or_404(ProductItem, pk=pk)
    product = item.product
    if not request.user.is_superuser and product.user != request.user:
        return JsonResponse({"success": False, "error": _("Permission denied.")}, status=403)
    item.is_active = False
    item.save()
    _sync_product_stock(product)
    return JsonResponse({"success": True, "message": _("Item removed."), "product_quantity": product.quantity})
