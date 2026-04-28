from django.shortcuts import render
from dashboard.models import Portfolio, Product


def home_view(request):
    latest_portfolios = Portfolio.objects.all()[:4]
    latest_products = Product.objects.filter(is_active=True)[:4]
    context = {
        "latest_portfolios": latest_portfolios,
        "latest_products": latest_products,
    }
    return render(request, "home.html", context)
