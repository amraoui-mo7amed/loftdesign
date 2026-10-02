from django.urls import path
from user_auth import views as auth_views
from .views import main, products, orders, cart, store, client

app_name = "frontend"

urlpatterns = [
    path("", main.home_view, name="home"),
    path("contact-submit/", main.contact_request_submit, name="contact_request_submit"),
    # Orders
    path("place-order/", orders.place_order, name="place_order"),
    # Products
    path("products/", products.product_list, name="product_list"),
    path("products/<int:pk>/", products.product_detail, name="product_detail"),
    path("store/product/<str:boid>/", products.product_by_boid, name="product_by_boid"),
    path("products/<int:pk>/view3d/", products.product_viewer_3d, name="product_viewer_3d"),
    # Cart
    path("cart/", cart.cart_view, name="cart"),
    path("cart/checkout/", cart.cart_checkout, name="checkout"),
    path("cart/add/", cart.cart_add, name="cart_add"),
    path("cart/update/", cart.cart_update, name="cart_update"),
    path("cart/remove/", cart.cart_remove, name="cart_remove"),
    path("cart/load/", cart.cart_load, name="cart_load"),
    path("cart/switch-variant/", cart.cart_switch_variant, name="cart_switch_variant"),
    # Affiliate
    path("signup/", auth_views.signup_view, name="affiliate_signup_page"),
    path("affiliate/signup/", main.affiliate_signup, name="affiliate_signup"),
    # Affiliate & Semi-Affiliate Storefronts
    path("a/<slug:code>/", store.affiliate_store, name="affiliate_store"),
    path("s/<slug:code>/", store.semi_affiliate_store, name="semi_affiliate_store"),
    # Legacy redirect: /store/{code}/ -> /a/{code}/
    path("store/<slug:code>/", store.legacy_store_redirect, name="legacy_store_redirect"),
    # Short redirect for share links
    path("go/<slug:code>/<int:pk>/", store.affiliate_redirect, name="affiliate_redirect"),
    # Admin storefront
    path("admin-store/", store.admin_store, name="admin_store"),
    path("loftdesign/", store.admin_store, name="admin_store_slugged"),
    # Provider storefront
    path("p/<str:username>/", store.provider_store, name="provider_store"),
    # End Client
    path("client/", client.client_home, name="client_home"),
    path("client/catalog/", client.client_catalog, name="client_catalog"),
    path("client/order/", client.client_order_create, name="client_order_create"),
    path("client/orders/", client.client_orders, name="client_orders"),
]
