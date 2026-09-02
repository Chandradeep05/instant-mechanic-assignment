from django.urls import path
from .views import (
    BookingListView,
    BookingDetailView,
    BookingTransitionView,
    BookingAssignView,
    ServiceCategoryListView,
)

urlpatterns = [
    path('', BookingListView.as_view(), name='booking-list'),
    path('services/', ServiceCategoryListView.as_view(), name='service-category-list'),
    path('<int:pk>/', BookingDetailView.as_view(), name='booking-detail'),
    path('<int:pk>/transition/', BookingTransitionView.as_view(), name='booking-transition'),
    path('<int:pk>/assign/', BookingAssignView.as_view(), name='booking-assign'),
]
