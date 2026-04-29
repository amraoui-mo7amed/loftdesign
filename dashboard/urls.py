from django.urls import path
from dashboard.views import dashboard, users, notifications, portfolio, products, orders

app_name = "dash"

urlpatterns = [
    path("home/", dashboard.dash_home, name="dash_home"),
    # Portfolio
    path("portfolio/", portfolio.portfolio_list, name="portfolio_list"),
    path("portfolio/create/", portfolio.portfolio_create, name="portfolio_create"),
    path("portfolio/<int:pk>/update/", portfolio.portfolio_update, name="portfolio_update"),
    path("portfolio/<int:pk>/delete/", portfolio.portfolio_delete, name="portfolio_delete"),
    # Products
    path("products/", products.product_list, name="product_list"),
    path("products/create/", products.product_create, name="product_create"),
    path("products/<int:pk>/update/", products.product_update, name="product_update"),
    path("products/<int:pk>/delete/", products.product_delete, name="product_delete"),
    path("products/categories/create/", products.category_create, name="category_create"),
    # Orders
    path("orders/", orders.order_list, name="order_list"),
    path("orders/<int:pk>/status/", orders.order_update_status, name="order_update_status"),
    path("orders/<int:pk>/delete/", orders.order_delete, name="order_delete"),
    # Users
    path("users/", users.user_list, name="user_list"),
    path("users/<int:pk>/", users.user_details, name="user_details"),
    path("users/<int:pk>/delete/", users.user_delete, name="user_delete"),
    path("users/<int:pk>/approve/", users.user_approve, name="user_approve"),
    # Notifications
    path("notifications/stream/",notifications.notifications_stream,name="notifications_stream"),
    path("notifications/unread-count/",notifications.get_unread_count,name="notifications_unread_count",),
    path("notifications/list/",notifications.get_notifications,name="notifications_list"),
    path("notifications/<int:notification_id>/read/",notifications.mark_as_read,name="notification_mark_read"),
    path("notifications/mark-all-read/",notifications.mark_all_as_read,name="notifications_mark_all_read"),
    path("notifications/<int:notification_id>/delete/",notifications.delete_notification,name="notification_delete"),
]
