from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.urls import reverse
from django.utils.translation import gettext as _
from user_auth.models import UserProfile
from dashboard.models import PartnerPrice, AffiliateStore, StoreVisit, Product


def affiliate_redirect(request, code, pk):
    """Short redirect URL for sharing: /go/CODE/PK/"""
    profile = get_object_or_404(
        UserProfile, affiliate_code=code, is_approved=True
    )
    product = get_object_or_404(Product, pk=pk)
    if not PartnerPrice.objects.filter(
        product=product, buyer=profile.user, is_active=True
    ).exists():
        raise Http404(_("Product not available through this affiliate."))
    request.session["affiliate_code"] = code
    request.session.modified = True
    return redirect(f"{reverse('frontend:product_detail', args=[pk])}?affiliate={code}")


def _get_store_context(code):
    """Shared helper to load store context for affiliate or semi-affiliate"""
    profile = get_object_or_404(
        UserProfile, affiliate_code=code, is_approved=True
    )
    if profile.role not in (UserProfile.roleChoices.AFFILIATE, UserProfile.roleChoices.SEMI_AFFILIATE):
        raise Http404

    store = AffiliateStore.objects.filter(affiliate=profile, is_active=True).first()
    if not store:
        store = AffiliateStore.objects.create(
            affiliate=profile,
            store_name=profile.user.get_full_name() or profile.user.username,
        )
    return profile, store


def _build_catalog(profile):
    """Build catalog list from PartnerPrice records"""
    prices = PartnerPrice.objects.filter(
        buyer=profile.user, is_active=True,
    ).select_related(
        "product", "product__loft_price"
    ).prefetch_related("product__gallery_images")

    catalog = []
    for pp in prices:
        product = pp.product
        loft_price = getattr(product, "loft_price", None)
        catalog.append({
            "product": product,
            "partner_price": pp,
            "retail_price": pp.retail_price or (loft_price.loft_retail_price if loft_price else None),
            "primary_image": product.gallery_images.first(),
        })
    return catalog


def _log_store_visit(request, store):
    """Log a visit to an affiliate/semi store"""
    request.session["affiliate_code"] = store.affiliate.affiliate_code
    request.session.modified = True
    if not request.session.session_key:
        request.session.create()
    StoreVisit.objects.create(
        store=store,
        visitor_ip=request.META.get("REMOTE_ADDR"),
        session_key=request.session.session_key or "",
    )


def affiliate_store(request, code):
    """Public mini-storefront for an affiliate (/a/CODE/)"""
    profile, store = _get_store_context(code)
    if profile.role == UserProfile.roleChoices.SEMI_AFFILIATE:
        return redirect("frontend:semi_affiliate_store", code=code)
    if profile.role != UserProfile.roleChoices.AFFILIATE:
        raise Http404
    catalog = _build_catalog(profile)
    _log_store_visit(request, store)
    return render(request, "affiliate_store.html", {
        "store": store,
        "profile": profile,
        "catalog": catalog,
        "title": store.store_name,
    })


def semi_affiliate_store(request, code):
    """Public mini-storefront for a semi-affiliate (/s/CODE/)"""
    profile, store = _get_store_context(code)
    if profile.role != UserProfile.roleChoices.SEMI_AFFILIATE:
        raise Http404
    catalog = _build_catalog(profile)
    _log_store_visit(request, store)
    return render(request, "affiliate_store.html", {
        "store": store,
        "profile": profile,
        "catalog": catalog,
        "title": store.store_name,
        "is_semi_affiliate": True,
    })


def legacy_store_redirect(request, code):
    """Redirect from /store/CODE/ to /a/CODE/"""
    return redirect("frontend:affiliate_store", code=code)
