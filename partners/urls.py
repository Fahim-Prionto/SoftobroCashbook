from django.urls import path
from . import views

app_name = 'partners'

urlpatterns = [
    # ── Partner CRUD ─────────────────────────────────────────────────────────
    path('', views.partner_list_view, name='partner_list'),
    path('new/', views.partner_create_view, name='partner_create'),
    path('<int:pk>/edit/', views.partner_edit_view, name='partner_edit'),
    path('<int:pk>/delete/', views.partner_delete_view, name='partner_delete'),
    path('<int:pk>/balance/', views.partner_balance_view, name='partner_balance'),

    # ── Ledger (Partner Entries) ──────────────────────────────────────────────
    path('ledger/', views.ledger_list_view, name='ledger_list'),
    path('ledger/new/', views.entry_create_view, name='entry_create'),
    path('ledger/<int:pk>/edit/', views.entry_edit_view, name='entry_edit'),
    path('ledger/<int:pk>/invoice/', views.invoice_print_view, name='invoice_print'),
]

