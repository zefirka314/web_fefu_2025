from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    # Сохраняем старые URL для обратной совместимости
    path('student/<int:student_id>/', views.student_profile, name='student_profile'),
    path('course/<slug:course_slug>/', views.course_detail, name='course_detail'),
    # Добавляем новые URL для работы с БД
    path('students/', views.student_list, name='student_list'),
    path('courses/', views.course_list, name='course_list'),
    # Существующие URL
    path('feedback/', views.feedback_view, name='feedback'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
]

handler404 = 'fefu_lab.views.custom_404'
