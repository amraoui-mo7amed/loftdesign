from django.urls import path

from . import views

app_name = "shopping"

urlpatterns = [
    path("my-projects/", views.list_index, name="index"),
    path("list/add/", views.add_to_list, name="add"),
    path("list/from-cart/", views.list_from_cart, name="from_cart"),
    path("list/<str:code>/", views.list_detail, name="detail"),
    path("list/<str:code>/print/", views.list_print, name="print"),
    path("list/<str:code>/edit/", views.list_action, name="action"),
    path("list/<str:code>/to-cart/", views.list_to_cart, name="to_cart"),
    path("list/<str:code>/cart/", views.list_cart_link, name="cart_link"),
]
