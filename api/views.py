"""Store Bilnov API v1, for BILNOV, BILNOV Desktop and CAD plugins.

Catalog reads are public (public prices and stock only). Creating a shopping
list or a cart link needs an API key: ``Authorization: Bearer sb_xxxx.yyyy``.
Documentation: docs/API-V1.md.
"""
import json
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.core import signing
from django.db.models import Q
from core.content_i18n import search_q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt

from dashboard import catalog_api as catalog
from dashboard.models import Product
from shopping.models import ListMember, Room, ShoppingList, ShoppingListItem

CART_SALT = "shopping-cart-link"
MAX_PAGE = 100
MAX_ITEMS = 500


def _json(data, status=200):
    response = JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Api-Key"
    response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def _error(message, status):
    return _json({"error": message}, status)


def endpoint(methods, auth=False):
    """Method check, CORS preflight and (optionally) API key check."""
    def deco(view):
        @csrf_exempt
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method == "OPTIONS":
                return _json({})
            if request.method not in methods:
                return _error("method not allowed", 405)
            header = request.headers.get("Authorization", "")
            raw = header[7:].strip() if header.lower().startswith("bearer ") else request.headers.get("X-Api-Key", "")
            from .models import ApiClient

            request.api_client = ApiClient.authenticate(raw) if raw else None
            if raw and request.api_client is None:
                return _error("invalid API key", 401)
            if auth and request.api_client is None:
                return _error("API key required", 401)
            if request.api_client is not None:
                ApiClient.objects.filter(pk=request.api_client.pk).update(last_used_at=timezone.now())
            try:
                return view(request, *args, **kwargs)
            except Http404:
                return _error("not found", 404)
        return wrapper
    return deco


def _body(request):
    try:
        data = json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _dec(value):
    if value in (None, ""):
        return None
    try:
        d = Decimal(str(value))
        return d if d.is_finite() and d >= 0 else None
    except InvalidOperation:
        return None


# ── Catalog ───────────────────────────────────────────────────

@endpoint(["GET"])
def products(request):
    """GET /products?q=&category=&format=&updatedSince=&page=&pageSize="""
    qs = catalog._published().filter(is_active=True).select_related("manufacturer")
    q = (request.GET.get("q") or "").strip()
    for word in q.split()[:8]:
        qs = qs.filter(
            Q(title__icontains=word) | Q(description__icontains=word) | Q(tags__icontains=word)
            | Q(brand__icontains=word) | Q(category__name__icontains=word) | Q(bpid__iexact=word)
            | Q(items__variant_id__iexact=word) | Q(items__sku__iexact=word) | Q(manufacturer_reference__iexact=word)
            | search_q(word, ("title", "description")) | search_q(word, ("name",), "category__")
        )
    if request.GET.get("category"):
        c = request.GET["category"]
        qs = qs.filter(Q(category__code__iexact=c) | Q(category__name__iexact=c))
    if request.GET.get("format"):
        qs = qs.filter(assets__file_format=request.GET["format"], assets__is_current=True)
    since = parse_datetime(request.GET.get("updatedSince") or "")
    if since:
        qs = qs.filter(updated_at__gte=since)
    try:
        page = max(1, int(request.GET.get("page", 1)))
        size = max(1, min(int(request.GET.get("pageSize", 24)), MAX_PAGE))
    except ValueError:
        return _error("page and pageSize must be integers", 400)
    qs = qs.distinct().order_by("pk")
    count = qs.count()
    start = (page - 1) * size
    results = [catalog.product_summary(request, p) for p in qs[start:start + size]]
    nxt = None
    if start + size < count:
        params = request.GET.copy()
        params["page"] = page + 1
        nxt = request.build_absolute_uri(f"{request.path}?{params.urlencode()}")
    return _json({"count": count, "page": page, "pageSize": size, "next": nxt, "results": results})


def _wrap_catalog(view):
    """The v1 product endpoints are the catalog views with CORS and key handling."""
    @endpoint(["GET"])
    def wrapped(request, bpid):
        response = view(request, bpid)
        response["Access-Control-Allow-Origin"] = "*"
        return response
    return wrapped


product = _wrap_catalog(catalog.product_detail)
variants = _wrap_catalog(catalog.product_variants)
assets = _wrap_catalog(catalog.product_assets)
availability = _wrap_catalog(catalog.product_availability)
price = _wrap_catalog(catalog.product_prices)


# ── Shopping lists ────────────────────────────────────────────

def _list_data(request, lst):
    items = []
    for it in lst.items.select_related("product", "variant", "room"):
        state = it.availability()
        current = it.product.loft_retail_price if it.product is not None and state != "unavailable" else None
        items.append({
            "id": it.pk,
            "bpid": it.bpid_snapshot or None,
            "variantId": it.variant_id_snapshot or None,
            "name": it.title_snapshot,
            "room": it.room.name if it.room else None,
            "quantity": it.quantity,
            "status": it.status,
            "availability": state,
            "price": {"snapshot": catalog._num(it.price_snapshot), "current": catalog._num(current),
                      "snapshotAt": it.snapshot_at.isoformat()},
            "replacedBy": it.replaced_by_id,
            "note": it.note or None,
        })
    return {
        "id": lst.code,
        "name": lst.name,
        "client": lst.client_name or None,
        "status": lst.status,
        "ownerRole": lst.owner_role,
        "bilnovProjectId": lst.bilnov_project_id or None,
        "budget": catalog._num(lst.budget),
        "rooms": [{"name": r.name, "budget": catalog._num(r.budget)} for r in lst.rooms.all()],
        "items": items,
        "url": request.build_absolute_uri(lst.get_absolute_url()),
        "updatedAt": lst.updated_at.isoformat(),
    }


@endpoint(["POST"], auth=True)
def shopping_list_create(request):
    """POST /shopping-lists: create a list from a BILNOV project or a desktop scene."""
    data = _body(request)
    if data is None:
        return _error("invalid JSON", 400)
    items = data.get("items") or []
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        return _error(f"items must be a list of at most {MAX_ITEMS}", 400)
    role = data.get("ownerRole") if data.get("ownerRole") in ListMember.Role.values else "architect"
    lst = ShoppingList.objects.create(
        name=str(data.get("name") or "Projet BILNOV")[:120],
        client_name=str(data.get("client") or "")[:120],
        budget=_dec(data.get("budget")),
        bilnov_project_id=str(data.get("bilnovProjectId") or "")[:64],
        owner_role=role,
    )
    rooms = {}
    for r in data.get("rooms") or []:
        if isinstance(r, dict) and r.get("name"):
            name = str(r["name"])[:80]
            rooms[name.lower()] = Room.objects.create(shopping_list=lst, name=name, budget=_dec(r.get("budget")),
                                                      position=len(rooms) + 1)
    status = ShoppingListItem.Status.PROPOSED_ARCHITECT if role == "architect" else ShoppingListItem.Status.PROPOSED_CLIENT
    rejected = []
    published = {p.bpid.upper(): p for p in catalog._published().filter(
        bpid__in=[str(i.get("bpid") or "").upper() for i in items if isinstance(i, dict)])}
    for n, it in enumerate(items, start=1):
        if not isinstance(it, dict):
            rejected.append({"index": n - 1, "reason": "not an object"})
            continue
        product = published.get(str(it.get("bpid") or "").strip().upper())
        if product is None:
            rejected.append({"index": n - 1, "bpid": it.get("bpid"), "reason": "unknown BPID"})
            continue
        variant = product.items.filter(variant_id__iexact=str(it["variantId"])).first() if it.get("variantId") else None
        room_name = str(it.get("room") or "")[:80]
        room = None
        if room_name:
            room = rooms.get(room_name.lower())
            if room is None:
                room = rooms[room_name.lower()] = Room.objects.create(shopping_list=lst, name=room_name, position=len(rooms) + 1)
        try:
            quantity = max(1, min(int(it.get("quantity", 1)), 9999))
        except (TypeError, ValueError):
            quantity = 1
        line = ShoppingListItem.objects.create(
            shopping_list=lst, room=room, product=product, variant=variant, quantity=quantity,
            title_snapshot=(variant.name if variant else product.title)[:255], bpid_snapshot=product.bpid,
            variant_id_snapshot=variant.variant_id if variant else "",
            price_snapshot=product.loft_retail_price, price_eur_snapshot=product.price_eur,
            status=status, note=str(it.get("note") or "")[:255], position=n,
        )
        line.events.create(author=request.api_client.name[:120], role=role, new_status=status)
    out = _list_data(request, lst)
    out["editUrl"] = out["url"] + "?cle=" + lst.edit_key
    out["rejected"] = rejected
    return _json(out, 201)


@endpoint(["GET"])
def shopping_list_detail(request, code):
    lst = get_object_or_404(ShoppingList, code=code.upper())
    return _json(_list_data(request, lst))


@endpoint(["POST"], auth=True)
def cart_from_shopping_list(request):
    """POST /cart/from-shopping-list {"id": "CODE"}: a link that fills the visitor's cart in the browser."""
    data = _body(request)
    if data is None:
        return _error("invalid JSON", 400)
    lst = ShoppingList.objects.filter(code=str(data.get("id") or data.get("shoppingListId") or "").upper()).first()
    if lst is None:
        return _error("unknown shopping list", 404)
    token = signing.dumps({"c": lst.code}, salt=CART_SALT)
    lines = [i for i in _list_data(request, lst)["items"]
             if i["status"] not in ShoppingListItem.INACTIVE and i["availability"] != "unavailable"]
    total = sum(Decimal(str(i["price"]["current"] or 0)) * i["quantity"] for i in lines)
    return _json({
        "id": lst.code,
        "cartUrl": request.build_absolute_uri(reverse("shopping:cart_link", args=[lst.code]) + "?t=" + token),
        "lines": len(lines),
        "total": {"dzd": float(total)},
        "expiresInDays": 7,
    }, 201)
