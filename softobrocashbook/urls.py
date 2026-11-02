from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Core & Landing
    path('', include('core.urls')),

    # Auth & Accounts
    path('auth/', include('accounts.urls')),

    # Subscriptions & Plans
    path('subscriptions/', include('subscriptions.urls')),

    # Payments & bKash
    path('payments/', include('payments.urls')),

    # Tenants & Multi-database Management
    path('tenants/', include('tenants.urls')),

    # Business Management
    path('businesses/', include('businesses.urls')),

    # Cashbook Management
    path('cashbooks/', include('cashbooks.urls')),

    # Transactions
    path('transactions/', include('transactions.urls')),

    # Reports & Printing
    path('reports/', include('reports.urls')),

    # In-App Notifications
    path('notifications/', include('notifications.urls')),

    # REST API for Mobile and Web
    path('api/v1/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
