from django.urls import path, include
from fefu_lab import views

urlpatterns = [
    path('', include('fefu_lab.urls')),
]

handler404 = 'fefu_lab.views.custom_404'
