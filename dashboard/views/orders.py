from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils.translation import gettext as _
from ..models import Order

@login_required
def order_list(request):
    """View to list all orders"""
    status_filter = request.GET.get("status", "")
    orders = Order.objects.all()
    
    if status_filter:
        orders = orders.filter(status=status_filter)
        
    paginator = Paginator(orders, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    context = {
        "page_obj": page_obj,
        "status_filter": status_filter,
        "status_choices": Order.OrderStatus.choices,
        "title": _("Order Management")
    }
    return render(request, "orders/list.html", context)

@login_required
def order_update_status(request, pk):
    """AJAX view to update order status"""
    if request.method == "POST":
        order = get_object_or_404(Order, pk=pk)
        new_status = request.POST.get("status")
        if new_status in Order.OrderStatus.values:
            order.status = new_status
            order.save()
            return JsonResponse({"success": True, "message": _("Order status updated")})
    return JsonResponse({"success": False}, status=400)

@login_required
def order_delete(request, pk):
    """AJAX delete for order"""
    if request.method == "POST":
        order = get_object_or_404(Order, pk=pk)
        order.delete()
        return JsonResponse({"success": True, "message": _("Order removed")})
    return JsonResponse({"success": False}, status=400)
