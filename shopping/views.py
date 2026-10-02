import secrets
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Max
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from dashboard.models import Product, ProductItem
from frontend.pricing import customer_price, visitor_currency
from frontend.views.cart import _get_cart, add_to_cart

from .models import Room, ShoppingList, ShoppingListItem

SESSION_KEY = "shopping_lists"


# ── Ownership ─────────────────────────────────────────────────
# A visitor without an account owns the lists created in their session; the
# private edit link (?cle=…) restores that right on another device.

def _remember(request, lst):
    codes = request.session.get(SESSION_KEY, [])
    if lst.code not in codes:
        request.session[SESSION_KEY] = codes + [lst.code]


def can_edit(request, lst):
    if request.user.is_authenticated and (lst.owner_id == request.user.id or request.user.is_superuser):
        return True
    return lst.code in request.session.get(SESSION_KEY, [])


def my_lists(request):
    qs = ShoppingList.objects.filter(code__in=request.session.get(SESSION_KEY, []))
    if request.user.is_authenticated:
        qs = qs | ShoppingList.objects.filter(owner=request.user)
    return qs.distinct()


def _claim_session_lists(request):
    """Lists created before signing in become the account's lists."""
    if request.user.is_authenticated:
        ShoppingList.objects.filter(code__in=request.session.get(SESSION_KEY, []), owner__isnull=True).update(owner=request.user)


def _dec(value):
    try:
        d = Decimal(str(value).replace(" ", "").replace(",", "."))
        return d if d.is_finite() and d >= 0 else None
    except (InvalidOperation, ValueError):
        return None


def _new_list(request, name):
    lst = ShoppingList.objects.create(
        name=(name or "").strip()[:120] or _("My project"),
        owner=request.user if request.user.is_authenticated else None,
    )
    _remember(request, lst)
    return lst


def _room(lst, name):
    name = (name or "").strip()[:80]
    if not name:
        return None
    room = lst.rooms.filter(name__iexact=name).first()
    if room is None:
        last = lst.rooms.aggregate(m=Max("position"))["m"] or 0
        room = Room.objects.create(shopping_list=lst, name=name, position=last + 1)
    return room


def _line_title(product, variant):
    if variant is None:
        return product.title
    if variant.name.lower().startswith(product.title.lower()):
        return variant.name[:255]  # variant names often repeat the product name
    return f"{product.title} — {variant.name}"[:255]


def add_item(request, lst, product, variant=None, quantity=1, room=None, status=None):
    price = customer_price(request, product)
    last = lst.items.aggregate(m=Max("position"))["m"] or 0
    if status is None:
        is_pro = request.user.is_authenticated and getattr(getattr(request.user, "profile", None), "role", "") == "professional_client"
        status = ShoppingListItem.Status.PROPOSED_ARCHITECT if is_pro else ShoppingListItem.Status.PROPOSED_CLIENT
    return ShoppingListItem.objects.create(
        shopping_list=lst, room=room, product=product, variant=variant, quantity=max(1, quantity),
        title_snapshot=_line_title(product, variant),
        bpid_snapshot=product.bpid or "", variant_id_snapshot=variant.variant_id if variant else "",
        price_snapshot=price["dzd"], price_eur_snapshot=price["eur"],
        status=status, added_by=request.user if request.user.is_authenticated else None, position=last + 1,
    )


# ── Pages ─────────────────────────────────────────────────────

def list_index(request):
    """'Mes projets': the visitor's shopping lists."""
    _claim_session_lists(request)
    if request.method == "POST":
        lst = _new_list(request, request.POST.get("name"))
        return redirect(lst)
    return render(request, "shopping/index.html", {"lists": my_lists(request).prefetch_related("items")})


def add_to_list(request):
    """Add one product to a list (existing or new), in a room."""
    product = get_object_or_404(Product, pk=request.GET.get("product") or request.POST.get("product"),
                                is_active=True, status=Product.ProductStatus.APPROVED)
    variant_pk = request.GET.get("item") or request.POST.get("item")
    variant = ProductItem.objects.filter(pk=variant_pk, product=product, is_active=True).first() if variant_pk else None
    lists = list(my_lists(request).prefetch_related("rooms"))

    if request.method == "POST":
        code = request.POST.get("list")
        lst = next((l for l in lists if l.code == code), None)
        if lst is None:
            lst = _new_list(request, request.POST.get("new_list"))
        try:
            quantity = max(1, min(int(request.POST.get("quantity", 1)), 9999))
        except ValueError:
            quantity = 1
        add_item(request, lst, product, variant, quantity, _room(lst, request.POST.get("room")))
        messages.success(request, _("%(title)s added to %(list)s.") % {"title": product.title, "list": lst.name})
        return redirect(lst)

    rooms = sorted({r.name for l in lists for r in l.rooms.all()})
    return render(request, "shopping/add.html", {
        "product": product, "variant": variant, "lists": lists, "rooms": rooms,
        "price": customer_price(request, product)["dzd"],
        "suggested_rooms": [_("Living room"), _("Kitchen"), _("Bedroom"), _("Bathroom"), _("Office"), _("Entrance")],
    })


def _rows(request, lst):
    eur = visitor_currency(request) == "EUR"
    items = list(lst.items.select_related("product", "variant", "room", "product__category"))
    groups, by_room = [], {}
    for room in lst.rooms.all():
        by_room[room.pk] = {"room": room, "items": [], "total": Decimal("0")}
        groups.append(by_room[room.pk])
    loose = {"room": None, "items": [], "total": Decimal("0")}
    total = snapshot_total = Decimal("0")
    alerts = 0
    for it in items:
        it.state = it.availability()
        current = customer_price(request, it.product)["dzd"] if it.state != "unavailable" else None
        it.current_price = current
        it.delta = (current - it.price_snapshot) if current is not None and it.price_snapshot is not None else None
        it.line_total = (current if current is not None else (it.price_snapshot or 0)) * it.quantity
        group = by_room.get(it.room_id, loose)
        group["items"].append(it)
        if it.counts:
            group["total"] += it.line_total
            total += it.line_total
            snapshot_total += (it.price_snapshot or 0) * it.quantity
            if it.state != "available" or it.delta:
                alerts += 1
    if loose["items"]:
        groups.append(loose)
    for g in groups:
        budget = g["room"].budget if g["room"] else None
        g["budget"] = budget
        g["over"] = budget is not None and g["total"] > budget
        g["percent"] = min(int(g["total"] * 100 / budget), 100) if budget else None
    return {"groups": groups, "total": total, "snapshot_total": snapshot_total, "alerts": alerts, "eur": eur,
            "item_count": sum(1 for it in items if it.counts)}


def list_detail(request, code):
    lst = get_object_or_404(ShoppingList, code=code.upper())
    key = request.GET.get("cle")
    if key:
        if secrets.compare_digest(key, lst.edit_key):
            _remember(request, lst)
            _claim_session_lists(request)
        return redirect(lst)
    editable = can_edit(request, lst)
    ctx = {"lst": lst, "editable": editable, "statuses": ShoppingListItem.Status.choices,
           "share_url": request.build_absolute_uri(lst.get_absolute_url())}
    if editable:
        ctx["edit_url"] = request.build_absolute_uri(lst.get_absolute_url() + "?cle=" + lst.edit_key)
    ctx.update(_rows(request, lst))
    return render(request, "shopping/detail.html", ctx)


def list_print(request, code):
    import segno

    lst = get_object_or_404(ShoppingList, code=code.upper())
    url = request.build_absolute_uri(lst.get_absolute_url())
    qr = segno.make(url, error="m").svg_inline(scale=3, border=0, dark="#141414")
    ctx = {"lst": lst, "share_url": url, "qr": qr}
    ctx.update(_rows(request, lst))
    return render(request, "shopping/print.html", ctx)


@require_POST
def list_action(request, code):
    lst = get_object_or_404(ShoppingList, code=code.upper())
    if not can_edit(request, lst):
        raise Http404
    action = request.POST.get("action")
    post = request.POST
    if action == "update_list":
        lst.name = (post.get("name") or lst.name).strip()[:120] or lst.name
        lst.client_name = (post.get("client_name") or "").strip()[:120]
        lst.budget = _dec(post.get("budget")) if post.get("budget") else None
        lst.bilnov_project_id = (post.get("bilnov_project_id") or "").strip()[:64]
        lst.save()
    elif action == "add_room":
        _room(lst, post.get("name"))
    elif action in ("update_room", "delete_room"):
        room = get_object_or_404(Room, pk=post.get("room"), shopping_list=lst)
        if action == "delete_room":
            room.delete()  # its products stay in the list, without a room
        else:
            room.name = (post.get("name") or room.name).strip()[:80] or room.name
            room.budget = _dec(post.get("budget")) if post.get("budget") else None
            room.save()
    elif action in ("update_item", "remove_item", "refresh_price"):
        item = get_object_or_404(ShoppingListItem, pk=post.get("item"), shopping_list=lst)
        if action == "remove_item":
            item.delete()
        elif action == "refresh_price":
            # Explicit choice of the owner: accept today's price as the new reference.
            if item.product is not None:
                price = customer_price(request, item.product)
                item.price_snapshot, item.price_eur_snapshot = price["dzd"], price["eur"]
                item.save(update_fields=["price_snapshot", "price_eur_snapshot"])
        else:
            try:
                item.quantity = max(1, min(int(post.get("quantity", item.quantity)), 9999))
            except ValueError:
                pass
            room_pk = post.get("room")
            item.room = lst.rooms.filter(pk=room_pk).first() if room_pk else None
            item.note = (post.get("note") or "").strip()[:255]
            if post.get("status") in ShoppingListItem.Status.values:
                item.status = post["status"]
            item.save()
    elif action == "delete_list":
        lst.delete()
        messages.success(request, _("The list has been deleted."))
        return redirect("shopping:index")
    lst.save(update_fields=["updated_at"])
    return redirect(reverse("shopping:detail", args=[lst.code]) + (f"#{post.get('anchor')}" if post.get("anchor") else ""))


@require_POST
def list_to_cart(request, code):
    """Put every line still counting and available into the cart, at today's price."""
    lst = get_object_or_404(ShoppingList, code=code.upper())
    added, skipped = 0, []
    for it in lst.items.select_related("product", "variant"):
        if not it.counts:
            continue
        state = it.availability()
        error = _("No longer available") if state == "unavailable" else None
        if error is None:
            error = add_to_cart(request, it.product, it.variant, it.quantity)
        if error:
            skipped.append(f"{it.title_snapshot} ({error})")
        else:
            added += 1
    if added:
        messages.success(request, _("%(count)s product(s) of %(list)s added to the cart.") % {"count": added, "list": lst.name})
    for line in skipped:
        messages.warning(request, _("Not added: %(line)s") % {"line": line})
    return redirect("frontend:cart")


@require_POST
def list_from_cart(request):
    """Save the current cart as a new list."""
    cart = _get_cart(request)
    if not cart:
        return redirect("frontend:cart")
    lst = _new_list(request, request.POST.get("name") or _("My cart"))
    for line in cart.values():
        product = Product.objects.filter(pk=line["product_id"]).first()
        if product is None:
            continue
        variant = ProductItem.objects.filter(pk=line.get("item_id"), product=product).first() if line.get("item_id") else None
        add_item(request, lst, product, variant, int(line.get("quantity", 1)))
    messages.success(request, _("Your cart has been saved as a list."))
    return redirect(lst)
