from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api import views

app_name = 'api'

router = DefaultRouter()
router.register(r'businesses', views.BusinessViewSet, basename='business')
router.register(r'cashbooks', views.CashbookViewSet, basename='cashbook')
router.register(r'transactions', views.TransactionViewSet, basename='transaction')
router.register(r'notifications', views.NotificationViewSet, basename='notification')

urlpatterns = [
    path('auth/login/', views.api_login, name='api_login'),
    path('auth/profile/', views.api_profile, name='api_profile'),
    path('summary/', views.api_financial_summary, name='api_summary'),
    path('subscription/', views.api_subscription_status, name='api_subscription'),
    path('payments/', views.api_payments, name='api_payments'),
    path('', include(router.urls)),
]

