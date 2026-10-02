"""Bilnov Catalog API: the product referential shared by the Bilnov ecosystem.

Store Bilnov is the source of truth for products. Bilnov Project, the BIM/IFC
viewer, Bilnov 360 and the CAD plugins resolve a Bilnov Object ID (BOID) here.
The BOID identifies the catalog product; a SKU identifies a commercial variant;
an IFC GUID identifies one placed instance in a project and is never stored as
a product identity.

Read-only and public: only public data is exposed (retail and euro prices,
stock, files). Supplier purchase prices and commissions never leave the store.
"""
import json
from decimal import Decimal

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Product, ProductAsset

PSET_NAME = "Pset_BilnovProduct"
MAX_RESOLVE = 500


def _published():
    return Product.objects.filter(
        status=Product.ProductStatus.APPROVED, bilnov_object_id__isnull=False
    ).select_related("category", "user")


def _abs(request, url):
    return request.build_absolute_uri(url) if url else None


def _product_or_404(boid):
    return get_object_or_404(_published(), bilnov_object_id__iexact=boid.strip())


def product_summary(request, product):
    return {
        "bilnovObjectId": product.bilnov_object_id,
        "uuid": str(product.bilnov_uuid),
        "name": product.title,
        "category": product.category.name if product.category else None,
        "categoryCode": (product.category.code or None) if product.category else None,
        "brand": product.brand or None,
        "collection": product.collection or None,
        "image": _abs(request, product.thumbnail.url) if product.thumbnail else None,
        "price": {"dzd": _num(product.loft_retail_price), "eur": _num(product.price_eur)},
        "available": product.is_active and product.available_stock > 0,
        "modelVersion": product.model_version,
        "storeUrl": _abs(request, product.store_path),
    }


def _num(value):
    return float(value) if value is not None else None


def pset(product, variant=None, request=None):
    """Properties to write into Pset_BilnovProduct of an IFC object."""
    return {
        "BilnovObjectID": product.bilnov_object_id,
        "BilnovSKU": (variant.sku if variant and variant.sku else product.sku) or "",
        "BilnovProductName": product.title,
        "BilnovManufacturerID": str(product.user_id or ""),
        "BilnovManufacturerName": product.brand or "",
        "BilnovCategoryID": (product.category.code or "") if product.category else "",
        "BilnovCollectionID": product.collection or "",
        "BilnovStoreURL": _abs(request, product.store_path) if request else product.store_path,
        "BilnovProductVersion": product.model_version,
        "BilnovVariantID": str(variant.pk) if variant else "",
    }


def _variants(product):
    return [
        {
            "variantId": v.pk,
            "sku": v.sku or None,
            "name": v.name,
            "color": v.color or None,
            "dimensions": v.dimensions or None,
            "stock": v.stock_quantity,
        }
        for v in product.items.filter(is_active=True)
    ]


def _assets(request, product, all_versions=False):
    qs = product.assets.all()
    if not all_versions:
        qs = qs.filter(is_current=True)
    files = [
        {
            "format": a.file_format,
            "label": a.get_file_format_display(),
            "version": a.version,
            "current": a.is_current,
            "variantId": a.variant_id,
            "url": _abs(request, a.file.url),
        }
        for a in qs
    ]
    if product.model_3d and not any(f["format"] == ProductAsset.Format.GLB for f in files):
        files.append({"format": "glb", "label": "GLB / GLTF", "version": product.model_version,
                      "current": True, "variantId": None, "url": _abs(request, product.model_3d.url)})
    return files


@require_GET
def product_detail(request, boid):
    product = _product_or_404(boid)
    data = product_summary(request, product)
    data.update({
        "description": product.description,
        "sku": product.sku or None,
        "variants": _variants(product),
        "assets": _assets(request, product),
        "ifcPropertySet": {"name": PSET_NAME, "properties": pset(product, request=request)},
    })
    return JsonResponse(data)


@require_GET
def product_variants(request, boid):
    product = _product_or_404(boid)
    return JsonResponse({"bilnovObjectId": product.bilnov_object_id, "variants": _variants(product)})


@require_GET
def product_assets(request, boid):
    product = _product_or_404(boid)
    return JsonResponse({
        "bilnovObjectId": product.bilnov_object_id,
        "modelVersion": product.model_version,
        "assets": _assets(request, product, all_versions=request.GET.get("all") == "1"),
    })


@require_GET
def product_availability(request, boid):
    product = _product_or_404(boid)
    return JsonResponse({
        "bilnovObjectId": product.bilnov_object_id,
        "available": product.is_active and product.available_stock > 0,
        "stock": product.available_stock,
        "variants": [{"variantId": v["variantId"], "sku": v["sku"], "stock": v["stock"]} for v in _variants(product)],
    })


@require_GET
def product_prices(request, boid):
    product = _product_or_404(boid)
    return JsonResponse({
        "bilnovObjectId": product.bilnov_object_id,
        "retail": {"dzd": _num(product.loft_retail_price), "eur": _num(product.price_eur)},
    })


@require_GET
def product_suppliers(request, boid):
    product = _product_or_404(boid)
    owner = product.user
    supplier = None
    if owner and not owner.is_superuser:
        supplier = {"id": owner.pk, "name": owner.get_full_name() or owner.username}
    return JsonResponse({
        "bilnovObjectId": product.bilnov_object_id,
        "brand": product.brand or None,
        "suppliers": [supplier] if supplier else [{"id": None, "name": "Store Bilnov"}],
    })


@require_GET
def product_alternatives(request, boid):
    product = _product_or_404(boid)
    qs = _published().filter(is_active=True).exclude(pk=product.pk)
    if product.category_id:
        qs = qs.filter(category_id=product.category_id)
    if product.loft_retail_price:
        price = product.loft_retail_price
        qs = qs.filter(loft_retail_price__gte=price * Decimal("0.5"), loft_retail_price__lte=price * Decimal("1.5"))
    return JsonResponse({
        "bilnovObjectId": product.bilnov_object_id,
        "alternatives": [product_summary(request, p) for p in qs[:12]],
    })


@require_GET
def search(request):
    q = (request.GET.get("q") or "").strip()
    qs = _published().filter(is_active=True)
    for word in q.split()[:8]:
        qs = qs.filter(
            Q(title__icontains=word) | Q(description__icontains=word) | Q(tags__icontains=word)
            | Q(brand__icontains=word) | Q(collection__icontains=word)
            | Q(category__name__icontains=word) | Q(bilnov_object_id__iexact=word)
            | Q(items__sku__iexact=word) | Q(items__color__icontains=word)
        )
    category = request.GET.get("category")
    if category:
        qs = qs.filter(Q(category__code__iexact=category) | Q(category__name__iexact=category))
    fmt = request.GET.get("format")
    if fmt:
        qs = qs.filter(assets__file_format=fmt, assets__is_current=True)
    try:
        limit = max(1, min(int(request.GET.get("limit", 24)), 100))
    except ValueError:
        limit = 24
    results = [product_summary(request, p) for p in qs.distinct()[:limit]]
    return JsonResponse({"query": q, "count": len(results), "results": results})


@csrf_exempt
@require_POST
def bim_resolve(request):
    """Resolve BOIDs read from an IFC/SketchUp/360 scene.

    Body: {"bilnovObjectId": "BLV-..."} or {"objects": [{"bilnovObjectId", "ifcGuid", "sku"}, ...]}.
    Each object comes back with its product (or null when unknown), so the
    viewer can sort identified, generic (no BOID) and unavailable products.
    """
    try:
        body = json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid JSON"}, status=400)
    objects = body.get("objects")
    if objects is None:
        objects = [body]
    if not isinstance(objects, list) or len(objects) > MAX_RESOLVE:
        return JsonResponse({"error": f"objects must be a list of at most {MAX_RESOLVE}"}, status=400)

    boids = {str(o.get("bilnovObjectId") or "").strip().upper() for o in objects if isinstance(o, dict)}
    products = {p.bilnov_object_id.upper(): p for p in _published().filter(bilnov_object_id__in=boids - {""})}
    out = []
    for o in objects:
        if not isinstance(o, dict):
            continue
        boid = str(o.get("bilnovObjectId") or "").strip().upper()
        product = products.get(boid)
        if not boid:
            status = "generic"
        elif product is None:
            status = "unknown"
        elif not (product.is_active and product.available_stock > 0):
            status = "unavailable"
        else:
            status = "identified"
        variant = None
        if product is not None and o.get("sku"):
            variant = product.items.filter(sku__iexact=str(o["sku"])).first()
        out.append({
            "ifcGuid": o.get("ifcGuid"),
            "bilnovObjectId": boid or None,
            "status": status,
            "product": product_summary(request, product) if product else None,
            "variantId": variant.pk if variant else None,
        })
    return JsonResponse({"objects": out})
