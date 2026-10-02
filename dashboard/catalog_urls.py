from django.urls import path

from . import catalog_api as api

app_name = "catalog"

urlpatterns = [
    path("products/<str:boid>/", api.product_detail, name="product"),
    path("products/<str:boid>/variants/", api.product_variants, name="variants"),
    path("products/<str:boid>/assets/", api.product_assets, name="assets"),
    path("products/<str:boid>/availability/", api.product_availability, name="availability"),
    path("products/<str:boid>/prices/", api.product_prices, name="prices"),
    path("products/<str:boid>/suppliers/", api.product_suppliers, name="suppliers"),
    path("products/<str:boid>/alternatives/", api.product_alternatives, name="alternatives"),
    path("search/", api.search, name="search"),
    path("bim/resolve/", api.bim_resolve, name="bim_resolve"),
]
