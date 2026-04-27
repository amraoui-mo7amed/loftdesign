from django.urls import path
from dashboard.views import dashboard, users, notifications, portfolio

app_name = "dash"

urlpatterns = [
    path("home/", dashboard.dash_home, name="dash_home"),
    # Portfolio
    path("portfolio/", portfolio.portfolio_list, name="portfolio_list"),
    path("portfolio/create/", portfolio.portfolio_create, name="portfolio_create"),
    path("portfolio/<int:pk>/update/", portfolio.portfolio_update, name="portfolio_update"),
    path("portfolio/<int:pk>/delete/", portfolio.portfolio_delete, name="portfolio_delete"),
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
