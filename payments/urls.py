from django.urls import path
from payments import views

app_name = 'payments'

urlpatterns = [
    path('submit/', views.submit_payment_view, name='submit_payment'),
    path('pending/', views.payment_pending_view, name='payment_pending'),
    path('history/', views.payment_history_view, name='payment_history'),
    path('history/my/', views.payment_history_view, name='my_payment_history'),

    # Super Admin management
    path('admin/list/', views.admin_payment_list_view, name='admin_payment_list'),
    path('admin/settings/', views.admin_bkash_settings_view, name='admin_bkash_settings'),
    path('admin/verify/<int:payment_id>/', views.admin_payment_detail_view, name='admin_payment_detail'),
]

