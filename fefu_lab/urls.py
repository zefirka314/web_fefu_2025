from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('student/<int:student_id>/', views.student_profile, name='student_profile'),
    path('course/<slug:course_slug>/', views.course_detail, name='course_detail'),
    path('feedback/', views.feedback_view, name='feedback'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
]
