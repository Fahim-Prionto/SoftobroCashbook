from django.urls import path
from subscriptions import views

app_name = 'subscriptions'

urlpatterns = [
    path('plans/', views.plan_list_view, name='plan_list'),
    path('my-subscription/', views.my_subscription_view, name='my_subscription'),
    path('renew/', views.renew_view, name='renew'),

    # Super Admin plan CRUD
    path('admin/plans/', views.admin_plan_list_view, name='admin_plan_list'),
    path('admin/plans/new/', views.admin_plan_create_view, name='admin_plan_create'),
    path('admin/plans/<int:plan_id>/edit/', views.admin_plan_edit_view, name='admin_plan_edit'),
    path('admin/plans/<int:plan_id>/toggle/', views.admin_plan_toggle_view, name='admin_plan_toggle'),
    path('admin/plans/<int:plan_id>/delete/', views.admin_plan_delete_view, name='admin_plan_delete'),
]

