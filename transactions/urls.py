from django.urls import path
from transactions import views

app_name = 'transactions'

urlpatterns = [
    path('cashbook/<int:cashbook_id>/new/', views.transaction_create_view, name='transaction_create'),
    path('<int:transaction_id>/edit/', views.transaction_edit_view, name='transaction_edit'),
    path('<int:transaction_id>/delete/', views.transaction_delete_view, name='transaction_delete'),
]

