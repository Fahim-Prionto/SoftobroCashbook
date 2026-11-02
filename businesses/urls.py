from django.urls import path
from businesses import views

app_name = 'businesses'

urlpatterns = [
    path('', views.business_list_view, name='business_list'),
    path('new/', views.business_create_view, name='business_create'),
    path('<int:business_id>/', views.business_detail_view, name='business_detail'),
    path('<int:business_id>/edit/', views.business_edit_view, name='business_edit'),
    path('<int:business_id>/delete/', views.business_delete_view, name='business_delete'),
]

