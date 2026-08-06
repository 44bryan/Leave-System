from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('tracker/', views.leave_tracker, name='tracker'),
    path('retirement/', views.retirement_dashboard, name='retirement'),
    path('birthdays/', views.birthday_dashboard, name='birthdays'),
    path('search/', views.search, name='search'),
    path('admin-settings/', views.admin_settings, name='admin_settings'),
    path('admin-settings/reset-balances/', views.reset_leave_balances, name='reset_balances'),
    path('admin-settings/carry-forward/', views.carry_forward_leave, name='carry_forward'),
    path('admin-settings/export/', views.export_data, name='export_data'),
    path('admin-settings/import/', views.import_data, name='import_data'),
    path('admin-settings/reset-balance/<int:pk>/', views.reset_single_balance, name='reset_single_balance'),
    path('admin-settings/adjust-entitlement/<int:pk>/', views.adjust_entitlement, name='adjust_entitlement'),
    path('admin-settings/go-live-reset/', views.go_live_reset, name='go_live_reset'),
    path('admin-settings/seniority-entitlements/', views.apply_seniority_entitlements, name='seniority_entitlements'),
    path('admin-settings/factory-reset/full/', views.factory_reset_full, name='factory_reset_full'),
    path('admin-settings/factory-reset/soft/', views.factory_reset_soft, name='factory_reset_soft'),
    path('admin-settings/factory-reset/yearend/', views.factory_reset_yearend, name='factory_reset_yearend'),
    path('reports/leaves/', views.export_leaves_excel, name='export_leaves'),
    path('reports/contracts/', views.export_contracts_excel, name='export_contracts'),
    path('reports/discipline/', views.export_discipline_excel, name='export_discipline'),
    path('activity-log/', views.activity_log, name='activity_log'),
    path('admin-settings/toggle-module/', views.toggle_module, name='toggle_module'),
    path('admin-settings/run-auto-lock/', views.run_auto_lock, name='run_auto_lock'),
    path('admin-settings/bulk-set-entitlement/', views.bulk_set_entitlement, name='bulk_set_entitlement'),
    path('leave-calendar/', views.leave_calendar, name='leave_calendar'),
    path('org-chart/', views.org_chart, name='org_chart'),
    path('analytics/', views.analytics_dashboard, name='analytics'),
]
