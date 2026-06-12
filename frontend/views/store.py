from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
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
    return redirect("frontend:product_detail", pk=pk)


def affiliate_store(request, code):
    """Public mini-storefront for an affiliate or semi-affiliate"""
    profile = get_object_or_404(
        UserProfile, affiliate_code=code, is_approved=True
    )
    if profile.role not in (UserProfile.roleChoices.AFFILIATE, UserProfile.roleChoices.SEMI_AFFILIATE):
        from django.http import Http404
        raise Http404

    store = AffiliateStore.objects.filter(affiliate=profile, is_active=True).first()
    if not store:
        store = AffiliateStore.objects.create(
            affiliate=profile,
            store_name=profile.user.get_full_name() or profile.user.username,
        )

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

    # Store affiliate code in session for cart tracking
    request.session["affiliate_code"] = code
    request.session.modified = True

    # Ensure session key exists for tracking
    if not request.session.session_key:
        request.session.create()

    # Log visit
    StoreVisit.objects.create(
        store=store,
        visitor_ip=request.META.get("REMOTE_ADDR"),
        session_key=request.session.session_key or "",
    )

    return render(request, "affiliate_store.html", {
        "store": store,
        "profile": profile,
        "catalog": catalog,
        "title": store.store_name,
    })
