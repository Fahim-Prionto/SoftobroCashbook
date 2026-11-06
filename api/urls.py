from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from api import views
from partners import views as partner_views

app_name = 'api'

router = DefaultRouter()
router.register(r'businesses', views.BusinessViewSet, basename='business')
router.register(r'cashbooks', views.CashbookViewSet, basename='cashbook')
router.register(r'transactions', views.TransactionViewSet, basename='transaction')
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'partners', partner_views.PartnerViewSet, basename='partner')
router.register(r'partner-entries', partner_views.PartnerEntryViewSet, basename='partner-entry')
router.register(r'invoice-templates', partner_views.InvoiceTemplateViewSet, basename='invoice-template')

urlpatterns = [
    # ── Authentication ────────────────────────────────────────────────────────
    path('auth/login/', views.api_login, name='api_login'),         # POST: returns access+refresh JWT
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # POST: refresh access token
    path('auth/verify/', TokenVerifyView.as_view(), name='token_verify'),     # POST: verify token validity
    path('auth/logout/', views.api_logout, name='api_logout'),      # POST: blacklist refresh token
    path('auth/profile/', views.api_profile, name='api_profile'),   # GET/PATCH: user profile

    # ── Dashboard ─────────────────────────────────────────────────────────────
    path('dashboard/', views.api_dashboard, name='api_dashboard'),  # GET: combined dashboard snapshot

    # ── Financials ────────────────────────────────────────────────────────────
    path('summary/', views.api_financial_summary, name='api_summary'),

    # ── Subscription ──────────────────────────────────────────────────────────
    path('subscription/', views.api_subscription_status, name='api_subscription'),

    # ── Payments ──────────────────────────────────────────────────────────────
    path('payments/', views.api_payments, name='api_payments'),

    # ── ViewSets (businesses, cashbooks, transactions, notifications) ─────────
    path('', include(router.urls)),
]

