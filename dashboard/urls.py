from django.urls import path
from dashboard.views import dashboard, users, notifications, portfolio, products, orders, settings, partner_prices

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
    # Product Validation
    path("products/<int:pk>/approve/", products.product_approve, name="product_approve"),
    path("products/<int:pk>/reject/", products.product_reject, name="product_reject"),
    # Partner Pricing
    path("products/<int:product_pk>/prices/", products.partner_price_list, name="partner_price_list"),
    path("products/<int:product_pk>/prices/create/", products.partner_price_create, name="partner_price_create"),
    path("prices/<int:pk>/delete/", products.partner_price_delete, name="partner_price_delete"),
    # Affiliate Catalog
    path("affiliate/catalog/", partner_prices.affiliate_catalog, name="affiliate_catalog"),
    path("affiliate/my-catalog/", partner_prices.my_catalog, name="my_catalog"),
    path("affiliate/catalog/<int:product_pk>/detail/", partner_prices.catalog_details, name="catalog_details"),
    path("affiliate/catalog/<int:product_pk>/add/", partner_prices.affiliate_catalog_add, name="affiliate_catalog_add"),
    path("affiliate/catalog/<int:product_pk>/remove/", partner_prices.affiliate_catalog_remove, name="affiliate_catalog_remove"),
    path("affiliate/catalog/<int:product_pk>/pricing/", partner_prices.catalog_update_pricing, name="catalog_update_pricing"),
    path("affiliate/store/", partner_prices.store_settings, name="store_settings"),
    # Categories
    path("categories/", products.category_list, name="category_list"),
    path("categories/create/", products.category_create, name="category_create"),
    path("categories/<int:pk>/update/", products.category_update, name="category_update"),
    path("categories/<int:pk>/delete/", products.category_delete, name="category_delete"),
    # Site Settings & Leads
    path("settings/", settings.settings_update, name="settings_update"),
    path("leads/", settings.contact_request_list, name="contact_request_list"),
    path("leads/<int:pk>/delete/", settings.contact_request_delete, name="contact_request_delete"),
    # Orders
    path("orders/", orders.order_list, name="order_list"),
    path("orders/<int:pk>/", orders.order_detail, name="order_detail"),
    path("orders/<int:pk>/status/", orders.order_update_status, name="order_update_status"),
    path("orders/<int:pk>/delete/", orders.order_delete, name="order_delete"),
    path("orders/<int:pk>/toggle-commission/", orders.order_toggle_commission, name="order_toggle_commission"),

    # Users
    path("users/", users.user_list, name="user_list"),
    path("users/provider/create/", users.provider_create, name="provider_create"),
    path("users/<int:pk>/", users.user_details, name="user_details"),
    path("users/<int:pk>/delete/", users.user_delete, name="user_delete"),
    path("users/<int:pk>/approve/", users.user_approve, name="user_approve"),
    path("users/<int:pk>/toggle-block/", users.user_toggle_block, name="user_toggle_block"),
    path("profile/edit/", users.profile_update, name="profile_update"),
    # Affiliates
    path("affiliates/", users.affiliate_list, name="affiliate_list"),
    path("affiliates/<int:pk>/approve/", users.affiliate_approve, name="affiliate_approve"),
    path("semi-affiliates/", users.semi_affiliate_list, name="semi_affiliate_list"),
    path("semi-affiliates/create/", users.semi_affiliate_create, name="semi_affiliate_create"),
    path("semi-affiliates/<int:pk>/delete/", users.semi_affiliate_delete, name="semi_affiliate_delete"),
    # Notifications
    path("notifications/stream/",notifications.notifications_stream,name="notifications_stream"),
    path("notifications/unread-count/",notifications.get_unread_count,name="notifications_unread_count",),
    path("notifications/list/",notifications.get_notifications,name="notifications_list"),
    path("notifications/<int:notification_id>/read/",notifications.mark_as_read,name="notification_mark_read"),
    path("notifications/mark-all-read/",notifications.mark_all_as_read,name="notifications_mark_all_read"),
    path("notifications/<int:notification_id>/delete/",notifications.delete_notification,name="notification_delete"),
]
