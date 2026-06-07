from django.urls import path
from .views import main, portfolio, products, orders, cart

app_name = "frontend"

urlpatterns = [
    path("", main.home_view, name="home"),
    path("contact-submit/", main.contact_request_submit, name="contact_request_submit"),
    # Orders
    path("place-order/", orders.place_order, name="place_order"),
    # Portfolio
    path("portfolio/", portfolio.portfolio_list, name="portfolio_list"),
    path("portfolio/<int:pk>/", portfolio.portfolio_detail, name="portfolio_detail"),
    # Products
    path("products/", products.product_list, name="product_list"),
    path("products/<int:pk>/", products.product_detail, name="product_detail"),
    path("products/<int:pk>/view3d/", products.product_viewer_3d, name="product_viewer_3d"),
    # Cart
    path("cart/", cart.cart_view, name="cart"),
    path("cart/checkout/", cart.cart_checkout, name="checkout"),
    path("cart/add/", cart.cart_add, name="cart_add"),
    path("cart/update/", cart.cart_update, name="cart_update"),
    path("cart/remove/", cart.cart_remove, name="cart_remove"),
    path("cart/load/", cart.cart_load, name="cart_load"),
    # Affiliate
    path("affiliate/signup/", main.affiliate_signup, name="affiliate_signup"),
]
