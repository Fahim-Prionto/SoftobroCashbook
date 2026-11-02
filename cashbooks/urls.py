from django.urls import path
from cashbooks import views

app_name = 'cashbooks'

urlpatterns = [
    path('', views.cashbook_list_view, name='cashbook_list'),
    path('business/<int:business_id>/new/', views.cashbook_create_view, name='cashbook_create'),
    path('<int:cashbook_id>/', views.cashbook_detail_view, name='cashbook_detail'),
    path('<int:cashbook_id>/edit/', views.cashbook_edit_view, name='cashbook_edit'),
    path('<int:cashbook_id>/delete/', views.cashbook_delete_view, name='cashbook_delete'),
    path('<int:cashbook_id>/print/', views.cashbook_print_view, name='cashbook_print'),
]

