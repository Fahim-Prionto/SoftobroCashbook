from django.urls import path
from tenants import views

app_name = 'tenants'

urlpatterns = [
    path('admin/list/', views.admin_tenant_list_view, name='admin_tenant_list'),
    path('admin/<int:tenant_id>/', views.admin_tenant_detail_view, name='admin_tenant_detail'),
    path('admin/<int:tenant_id>/reprovision/', views.admin_tenant_reprovision_view, name='admin_tenant_reprovision'),
    path('admin/<int:tenant_id>/delete/', views.admin_tenant_delete_view, name='admin_tenant_delete'),
    path('admin/audit-logs/', views.admin_audit_log_view, name='admin_audit_logs'),
]

