from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("products", views.products, name="products"),
    path("products/<str:bpid>", views.product, name="product"),
    path("products/<str:bpid>/variants", views.variants, name="variants"),
    path("products/<str:bpid>/assets", views.assets, name="assets"),
    path("products/<str:bpid>/availability", views.availability, name="availability"),
    path("products/<str:bpid>/price", views.price, name="price"),
    path("shopping-lists", views.shopping_list_create, name="shopping_lists"),
    path("shopping-lists/<str:code>", views.shopping_list_detail, name="shopping_list"),
    path("cart/from-shopping-list", views.cart_from_shopping_list, name="cart_from_list"),
]
