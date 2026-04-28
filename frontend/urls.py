from django.urls import path
from .views import main, portfolio, products

app_name = "frontend"

urlpatterns = [
    path("", main.home_view, name="home"),
    # Portfolio
    path("portfolio/", portfolio.portfolio_list, name="portfolio_list"),
    path("portfolio/<int:pk>/", portfolio.portfolio_detail, name="portfolio_detail"),
    # Products
    path("products/", products.product_list, name="product_list"),
    path("products/<int:pk>/", products.product_detail, name="product_detail"),
]
