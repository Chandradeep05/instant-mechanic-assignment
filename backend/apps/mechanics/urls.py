from django.urls import path
from .views import MechanicListView, MechanicDetailView

urlpatterns = [
    path('', MechanicListView.as_view(), name='mechanic-list'),
    path('<int:pk>/', MechanicDetailView.as_view(), name='mechanic-detail'),
]
