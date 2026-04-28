from django.shortcuts import render, get_object_or_404
from dashboard.models import Portfolio

def portfolio_list(request):
    portfolios = Portfolio.objects.all()
    return render(request, "portfolio/portfolio_list.html", {"portfolios": portfolios})

def portfolio_detail(request, pk):
    portfolio = get_object_or_404(Portfolio, pk=pk)
    return render(request, "portfolio/portfolio_detail.html", {"portfolio": portfolio})
