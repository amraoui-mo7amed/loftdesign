"""Bilnov Catalog API: the product referential shared by the Bilnov ecosystem.

Store Bilnov is the source of truth for products. Bilnov Project, the BIM/IFC
viewer, Bilnov 360, BILNOV Desktop and the CAD plugins resolve a BILNOV Product
ID (BPID) here. The BPID identifies the catalog product; a Variant ID
(BPID-…-V01) and its SKU identify a commercial variant; an IFC GUID identifies
one placed instance in a project and is never stored as a product identity.

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
        status=Product.ProductStatus.APPROVED, bpid__isnull=False
    ).select_related("category", "user")


def _abs(request, url):
    return request.build_absolute_uri(url) if url else None


def _product_or_404(bpid):
    return get_object_or_404(_published(), bpid__iexact=bpid.strip())


def product_summary(request, product):
    return {
        "bpid": product.bpid,
        "uuid": str(product.bilnov_uuid),
        "name": product.title,
        "category": product.category.name if product.category else None,
        "categoryCode": (product.category.code or None) if product.category else None,
        "brand": product.brand or None,
        "manufacturer": _manufacturer(product),
        "manufacturerReference": product.manufacturer_reference or None,
        "supplierId": product.supplier_id,
        "collection": product.collection or None,
        "image": _abs(request, product.thumbnail.url) if product.thumbnail else None,
        "price": {"dzd": _num(product.loft_retail_price), "eur": _num(product.price_eur)},
        "available": product.is_active and product.available_stock > 0,
        "modelVersion": product.model_version,
        "storeUrl": _abs(request, product.store_path),
    }


def _manufacturer(product):
    m = product.manufacturer
    return {"id": m.manufacturer_id, "name": m.name} if m else None


def _num(value):
    return float(value) if value is not None else None


def pset(product, variant=None, request=None):
    """Properties to write into Pset_BilnovProduct of an IFC object (also used for SKP attributes and GLB extras)."""
    return {
        "BilnovProductID": product.bpid,
        "BilnovVariantID": variant.variant_id if variant else "",
        "Manufacturer": product.manufacturer.name if product.manufacturer else (product.brand or ""),
        "ManufacturerReference": (variant.manufacturer_reference if variant and variant.manufacturer_reference else product.manufacturer_reference) or "",
        "StoreURL": _abs(request, product.store_path) if request else product.store_path,
        "ModelVersion": product.model_version,
        "ProductName": product.title,
        "SKU": (variant.sku if variant and variant.sku else product.sku) or "",
        "CategoryCode": (product.category.code or "") if product.category else "",
    }


def _variants(product):
    return [
        {
            "variantId": v.variant_id,
            "sku": v.sku or None,
            "manufacturerReference": v.manufacturer_reference or None,
            "name": v.name,
            "color": v.color or None,
            "dimensions": v.dimensions or None,
            "stock": v.stock_quantity,
        }
        for v in product.items.filter(is_active=True)
    ]


def _size(field):
    try:
        return field.size
    except (OSError, ValueError):
        return None


def _assets(request, product, all_versions=False):
    qs = product.assets.select_related("variant")
    if not all_versions:
        qs = qs.filter(is_current=True)
    files = [
        {
            "format": a.file_format,
            "label": a.get_file_format_display(),
            "version": a.version,
            "current": a.is_current,
            "variantId": a.variant.variant_id if a.variant_id else None,
            "url": _abs(request, a.file.url),
            "unit": a.unit,
            "scale": a.scale,
            "polygons": a.polygon_count,
            "size": a.file_size,
            "sha256": a.sha256 or None,
            "compatibility": a.compatibility or None,
            "date": a.created_at.isoformat(),
        }
        for a in qs
    ]
    if product.model_3d and not any(f["format"] == ProductAsset.Format.GLB for f in files):
        files.append({"format": "glb", "label": "GLB / GLTF", "version": product.model_version,
                      "current": True, "variantId": None, "url": _abs(request, product.model_3d.url),
                      "unit": "m", "scale": "1:1", "polygons": None, "size": _size(product.model_3d),
                      "sha256": None, "compatibility": None, "date": product.updated_at.isoformat() if product.updated_at else None})
    return files


@require_GET
def product_detail(request, bpid):
    product = _product_or_404(bpid)
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
def product_variants(request, bpid):
    product = _product_or_404(bpid)
    return JsonResponse({"bpid": product.bpid, "variants": _variants(product)})


@require_GET
def product_assets(request, bpid):
    product = _product_or_404(bpid)
    return JsonResponse({
        "bpid": product.bpid,
        "modelVersion": product.model_version,
        "assets": _assets(request, product, all_versions=request.GET.get("all") == "1"),
    })


@require_GET
def product_availability(request, bpid):
    product = _product_or_404(bpid)
    return JsonResponse({
        "bpid": product.bpid,
        "available": product.is_active and product.available_stock > 0,
        "stock": product.available_stock,
        "variants": [{"variantId": v["variantId"], "sku": v["sku"], "stock": v["stock"]} for v in _variants(product)],
    })


@require_GET
def product_prices(request, bpid):
    product = _product_or_404(bpid)
    return JsonResponse({
        "bpid": product.bpid,
        "retail": {"dzd": _num(product.loft_retail_price), "eur": _num(product.price_eur)},
    })


@require_GET
def product_suppliers(request, bpid):
    product = _product_or_404(bpid)
    owner = product.user
    supplier = None
    if owner and not owner.is_superuser:
        supplier = {"id": owner.pk, "name": owner.get_full_name() or owner.username}
    return JsonResponse({
        "bpid": product.bpid,
        "brand": product.brand or None,
        "suppliers": [supplier] if supplier else [{"id": None, "name": "Store Bilnov"}],
    })


@require_GET
def product_alternatives(request, bpid):
    product = _product_or_404(bpid)
    qs = _published().filter(is_active=True).exclude(pk=product.pk)
    if product.category_id:
        qs = qs.filter(category_id=product.category_id)
    if product.loft_retail_price:
        price = product.loft_retail_price
        qs = qs.filter(loft_retail_price__gte=price * Decimal("0.5"), loft_retail_price__lte=price * Decimal("1.5"))
    return JsonResponse({
        "bpid": product.bpid,
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
            | Q(category__name__icontains=word) | Q(bpid__iexact=word) | Q(items__variant_id__iexact=word) | Q(manufacturer_reference__iexact=word)
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
    """Resolve BPIDs read from an IFC/SketchUp/360 scene.

    Body: {"bpid": "BPID-..."} or {"objects": [{"bpid", "variantId", "ifcGuid", "sku"}, ...]}.
    Each object comes back with its product (or null when unknown), so the
    viewer can sort identified, generic (no BPID) and unavailable products.
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

    bpids = {str(o.get("bpid") or "").strip().upper() for o in objects if isinstance(o, dict)}
    products = {p.bpid.upper(): p for p in _published().filter(bpid__in=bpids - {""})}
    out = []
    for o in objects:
        if not isinstance(o, dict):
            continue
        bpid = str(o.get("bpid") or "").strip().upper()
        product = products.get(bpid)
        if not bpid:
            status = "generic"
        elif product is None:
            status = "unknown"
        elif not (product.is_active and product.available_stock > 0):
            status = "unavailable"
        else:
            status = "identified"
        variant = None
        if product is not None and o.get("variantId"):
            variant = product.items.filter(variant_id__iexact=str(o["variantId"])).first()
        if product is not None and variant is None and o.get("sku"):
            variant = product.items.filter(sku__iexact=str(o["sku"])).first()
        out.append({
            "ifcGuid": o.get("ifcGuid"),
            "bpid": bpid or None,
            "status": status,
            "product": product_summary(request, product) if product else None,
            "variantId": variant.variant_id if variant else None,
        })
    return JsonResponse({"objects": out})
