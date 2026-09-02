from django.urls import path
from .views import DemoSimulateView

urlpatterns = [
    path('demo/simulate/', DemoSimulateView.as_view(), name='demo-simulate'),
]
