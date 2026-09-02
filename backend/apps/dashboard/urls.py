from django.urls import path
from .views import (
    DashboardOverviewView,
    DashboardAttentionView,
    AnalyticsBookingsView,
    AnalyticsRevenueView,
    AnalyticsStatusView,
    AnalyticsServicesView,
)

urlpatterns = [
    path('dashboard/overview/', DashboardOverviewView.as_view(), name='dashboard-overview'),
    path('dashboard/attention/', DashboardAttentionView.as_view(), name='dashboard-attention'),
    path('analytics/bookings/', AnalyticsBookingsView.as_view(), name='analytics-bookings'),
    path('analytics/revenue/', AnalyticsRevenueView.as_view(), name='analytics-revenue'),
    path('analytics/status/', AnalyticsStatusView.as_view(), name='analytics-status'),
    path('analytics/services/', AnalyticsServicesView.as_view(), name='analytics-services'),
]
