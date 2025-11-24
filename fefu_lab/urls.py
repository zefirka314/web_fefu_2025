from django.urls import path
from . import views

urlpatterns = [
    # =========================================================================
    # ОСНОВНЫЕ СТРАНИЦЫ
    # =========================================================================
    path('', views.home, name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    
    # =========================================================================
    # СИСТЕМА АУТЕНТИФИКАЦИИ
    # =========================================================================
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # =========================================================================
    # ПРОФИЛЬ И ЛИЧНЫЕ КАБИНЕТЫ
    # =========================================================================
    path('profile/', views.profile_view, name='profile'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('dashboard/teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    
    # =========================================================================
    # ФУНКЦИОНАЛ СТУДЕНТОВ
    # =========================================================================
    path('student/<int:student_id>/', views.student_profile, name='student_profile'),
    path('students/', views.student_list, name='student_list'),
    path('course/<slug:course_slug>/enroll/', views.enroll_in_course, name='enroll_in_course'),
    
    # =========================================================================
    # ФУНКЦИОНАЛ ПРЕПОДАВАТЕЛЕЙ
    # =========================================================================
    path('teacher/course/<slug:course_slug>/manage/', views.teacher_course_management, name='teacher_course_management'),
    
    # =========================================================================
    # КУРСЫ И ОБУЧЕНИЕ
    # =========================================================================
    path('course/<slug:course_slug>/', views.course_detail, name='course_detail'),
    path('courses/', views.course_list, name='course_list'),
    
    # =========================================================================
    # ФОРМЫ И ОБРАТНАЯ СВЯЗЬ
    # =========================================================================
    path('feedback/', views.feedback_view, name='feedback'),
    
    # =========================================================================
    # API И СЛУЖЕБНЫЕ МАРШРУТЫ
    # =========================================================================
    path('api/user-info/', views.api_user_info, name='api_user_info'),
]

# =============================================================================
# ОБРАБОТЧИКИ ОШИБОК
# =============================================================================
handler404 = 'fefu_lab.views.custom_404'
handler500 = 'fefu_lab.views.custom_500'
