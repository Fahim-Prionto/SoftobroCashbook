from django.urls import path
from reports import views

app_name = 'reports'

urlpatterns = [
    path('', views.report_dashboard_view, name='report_dashboard'),
    path('cashbook/<int:cashbook_id>/', views.cashbook_report_view, name='cashbook_report'),
    path('business/<int:business_id>/', views.business_summary_report_view, name='business_summary'),
    path('date-range/', views.date_range_report_view, name='date_range_report'),
]

