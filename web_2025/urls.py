from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('fefu_lab.urls')),
]

handler404 = 'fefu_lab.views.custom_404'
