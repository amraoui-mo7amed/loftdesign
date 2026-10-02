"""Dashboard → Translations: enter the other languages of every product,
variant, category and store text, with an optional machine pre-fill."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _, gettext_lazy
from django.views.decorators.http import require_POST

from core import machine_translation
from core.content_i18n import search_q, source_language, target_languages
from dashboard.decorator import role_required
from user_auth.models import UserProfile

from ..models import AdminStore, AffiliateStore, Category, Product, ProductItem

SECTIONS = [
    ("products", gettext_lazy("Products"), Product, lambda qs: qs.order_by("-created_at")),
    ("variants", gettext_lazy("Variants"), ProductItem, lambda qs: qs.select_related("product").order_by("product__title", "pk")),
    ("categories", gettext_lazy("Categories"), Category, lambda qs: qs.order_by("name")),
    ("stores", gettext_lazy("Store texts"), None, None),
]
FIELD_LABELS = {"title": gettext_lazy("Title"), "name": gettext_lazy("Name"),
                "description": gettext_lazy("Description"), "store_description": gettext_lazy("Store description")}


def _objects(key):
    if key == "stores":
        return list(AdminStore.objects.all()) + list(AffiliateStore.objects.select_related("affiliate__user"))
    for k, _label, model, order in SECTIONS:
        if k == key:
            return order(model.objects.all())
    return []


def _label(obj):
    if isinstance(obj, ProductItem):
        return f"{obj.product.title} — {obj.name}"
    if isinstance(obj, (AdminStore, AffiliateStore)):
        return obj.store_name
    return getattr(obj, "title", None) or getattr(obj, "name", "")


def _find(key, pk, kind=""):
    if key == "stores":
        model = AdminStore if kind == "admin" else AffiliateStore
    else:
        model = next(m for k, _l, m, _o in SECTIONS if k == key)
    return model.objects.get(pk=pk)


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def translations(request):
    key = request.GET.get("section", "products")
    if key not in [s[0] for s in SECTIONS]:
        key = "products"
    only_missing = request.GET.get("missing", "1") == "1"
    q = (request.GET.get("q") or "").strip()
    objects = _objects(key)
    if q and hasattr(objects, "filter"):
        field = "title" if key == "products" else "name"
        objects = objects.filter(Q(**{f"{field}__icontains": q}) | search_q(q, (field,)))
    objects = list(objects)
    counts = {}
    for k, *_rest in SECTIONS:
        counts[k] = sum(1 for o in _objects(k) if o.missing_languages())
    if only_missing:
        objects = [o for o in objects if o.missing_languages()]
    page = Paginator(objects, 20).get_page(request.GET.get("page"))
    langs = target_languages()
    rows = []
    for obj in page:
        rows.append({
            "obj": obj,
            "kind": "admin" if isinstance(obj, AdminStore) else "",
            "label": _label(obj),
            "fields": [{"name": f, "label": FIELD_LABELS.get(f, f), "source": getattr(obj, f) or "",
                        "long": f in ("description", "store_description"),
                        "values": [(lang, obj.get_tr(lang, f)) for lang in langs]}
                       for f in obj.TRANSLATABLE_FIELDS if (getattr(obj, f) or "").strip()],
        })
    return render(request, "translations/list.html", {
        "sections": [(k, label, counts[k]) for k, label, *_rest in SECTIONS], "section": key,
        "rows": rows, "page_obj": page, "only_missing": only_missing, "q": q,
        "langs": langs, "source": source_language(), "auto": machine_translation.available(),
        "title": _("Translations"),
    })


@require_POST
@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def translation_save(request):
    key = request.POST.get("section")
    try:
        obj = _find(key, request.POST.get("pk"), request.POST.get("kind", ""))
    except Exception:
        return JsonResponse({"success": False}, status=404)
    for lang in target_languages():
        for f in obj.TRANSLATABLE_FIELDS:
            name = f"{f}__{lang}"
            if name in request.POST:
                obj.set_tr(lang, f, request.POST[name][:5000])
    obj.save(update_fields=["i18n"])
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": True, "missing": obj.missing_languages()})
    messages.success(request, _("Translations saved."))
    back = request.META.get("HTTP_REFERER")
    if back and url_has_allowed_host_and_scheme(back, {request.get_host()}, request.is_secure()):
        return redirect(back)
    return redirect("dash:translations")


@require_POST
@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def translation_auto(request):
    """Machine pre-fill of one row: returns suggestions, saves nothing."""
    key = request.POST.get("section")
    try:
        obj = _find(key, request.POST.get("pk"), request.POST.get("kind", ""))
    except Exception:
        return JsonResponse({"success": False}, status=404)
    fields = [f for f in obj.TRANSLATABLE_FIELDS if (getattr(obj, f) or "").strip()]
    out = {}
    try:
        for lang in target_languages():
            done = machine_translation.translate([getattr(obj, f) for f in fields], lang, source_language())
            for f, text in zip(fields, done):
                out[f"{f}__{lang}"] = text
    except RuntimeError as exc:
        return JsonResponse({"success": False, "message": str(exc)}, status=502)
    return JsonResponse({"success": True, "values": out})
