from django.urls import path

from . import catalog_api as api

app_name = "catalog"

urlpatterns = [
    path("products/<str:bpid>/", api.product_detail, name="product"),
    path("products/<str:bpid>/variants/", api.product_variants, name="variants"),
    path("products/<str:bpid>/assets/", api.product_assets, name="assets"),
    path("products/<str:bpid>/availability/", api.product_availability, name="availability"),
    path("products/<str:bpid>/prices/", api.product_prices, name="prices"),
    path("products/<str:bpid>/suppliers/", api.product_suppliers, name="suppliers"),
    path("products/<str:bpid>/alternatives/", api.product_alternatives, name="alternatives"),
    path("search/", api.search, name="search"),
    path("bim/resolve/", api.bim_resolve, name="bim_resolve"),
]
