from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
    # Public Pages
    path('', views.landing_view, name='landing'),
    path('about/', views.about_view, name='about'),
    path('features/', views.features_view, name='features'),
    path('pricing/', views.pricing_view, name='pricing'),
    path('how-it-works/', views.how_it_works_view, name='how_it_works'),
    path('contact/', views.contact_view, name='contact'),

    # Redirect helper
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),

    # Service Admin Dashboard
    path('app/dashboard/', views.serviceadmin_dashboard_view, name='serviceadmin_dashboard'),

    # Super Admin Dashboard & User Management
    path('superadmin/dashboard/', views.superadmin_dashboard_view, name='superadmin_dashboard'),
    path('superadmin/service-admins/', views.admin_service_admin_list_view, name='admin_service_admin_list'),
    path('superadmin/service-admins/<int:user_id>/', views.admin_service_admin_detail_view, name='admin_service_admin_detail'),
    path('superadmin/service-admins/<int:user_id>/status/', views.admin_service_admin_status_view, name='admin_service_admin_status'),
    path('superadmin/service-admins/<int:user_id>/delete/', views.admin_service_admin_delete_view, name='admin_service_admin_delete'),
]

