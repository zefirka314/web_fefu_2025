from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('student/<int:student_id>/', views.student_detail, name='student_detail'),
    path('course/<slug:course_slug>/', views.CourseDetailView.as_view(), name='course_detail'),
]
