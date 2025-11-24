from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.views import View
from django.db.models import Count, Q, F
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.decorators import method_decorator

from .forms import *
from .models import UserProfile, Student, Course, Enrollment, Instructor

# =============================================================================
# ДЕКОРАТОРЫ ДЛЯ ПРОВЕРКИ ПРАВ ДОСТУПА
# =============================================================================

def student_required(function=None):
    """Декоратор для проверки, что пользователь является студентом"""
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and hasattr(u, 'profile') and u.profile.role == 'STUDENT',
        login_url='/login/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def teacher_required(function=None):
    """Декоратор для проверки, что пользователь является преподавателем"""
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and hasattr(u, 'profile') and u.profile.role == 'TEACHER',
        login_url='/login/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def admin_required(function=None):
    """Декоратор для проверки, что пользователь является администратором"""
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and hasattr(u, 'profile') and u.profile.role == 'ADMIN',
        login_url='/login/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

# =============================================================================
# СИСТЕМА АУТЕНТИФИКАЦИИ
# =============================================================================

def register_view(request):
    """Регистрация нового пользователя в системе"""
    if request.user.is_authenticated:
        messages.info(request, 'Вы уже авторизованы в системе.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # ИСПРАВЛЕНИЕ: Аутентифицируем пользователя заново
            from django.contrib.auth import authenticate, login
            authenticated_user = authenticate(
                request, 
                username=user.username, 
                password=form.cleaned_data['password1']
            )
            if authenticated_user is not None:
                login(request, authenticated_user)
                messages.success(request, f'Регистрация прошла успешно! Добро пожаловать, {user.first_name}.')
                return redirect('dashboard')
            else:
                messages.error(request, 'Произошла ошибка при автоматическом входе. Пожалуйста, войдите вручную.')
                return redirect('login')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'fefu_lab/registration/register.html', {
        'form': form,
        'title': 'Регистрация'
    })

def login_view(request):
    """Аутентификация пользователя в системе"""
    if request.user.is_authenticated:
        messages.info(request, 'Вы уже авторизованы в системе.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {user.first_name}!')
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Неверные учетные данные. Пожалуйста, попробуйте снова.')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = UserLoginForm()
    
    return render(request, 'fefu_lab/registration/login.html', {
        'form': form,
        'title': 'Вход в систему'
    })

def logout_view(request):
    """Выход пользователя из системы"""
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('home')

# =============================================================================
# ПРОФИЛЬ И ЛИЧНЫЕ КАБИНЕТЫ
# =============================================================================

@login_required
def profile_view(request):
    """Редактирование профиля пользователя"""
    user = request.user
    profile = user.profile
    
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=user)
        profile_form = UserProfileExtendedForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('profile')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        user_form = UserProfileForm(instance=user)
        profile_form = UserProfileExtendedForm(instance=profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'title': 'Мой профиль'
    }
    
    # Добавляем специфичные данные в зависимости от роли
    if profile.role == 'STUDENT' and hasattr(user, 'student'):
        context['student'] = user.student
        context['enrollments'] = Enrollment.objects.filter(student=user.student).select_related('course')
    elif profile.role == 'TEACHER' and hasattr(user, 'instructor'):
        context['instructor'] = user.instructor
        context['courses'] = Course.objects.filter(instructor=user.instructor, is_active=True)
    
    return render(request, 'fefu_lab/registration/profile.html', context)

@login_required
def dashboard_view(request):
    """Перенаправление в соответствующий личный кабинет по роли"""
    profile = request.user.profile
    
    if profile.role == 'STUDENT':
        return redirect('student_dashboard')
    elif profile.role == 'TEACHER':
        return redirect('teacher_dashboard')
    elif profile.role == 'ADMIN':
        return redirect('admin_dashboard')
    else:
        return redirect('profile')

@login_required
@student_required
def student_dashboard(request):
    """Личный кабинет студента"""
    student = request.user.student
    enrollments = Enrollment.objects.filter(student=student).select_related('course')
    
    # Статистика для дашборда
    active_courses = enrollments.filter(status='ACTIVE').count()
    completed_courses = enrollments.filter(status='COMPLETED').count()
    
    return render(request, 'fefu_lab/dashboard/student_dashboard.html', {
        'student': student,
        'enrollments': enrollments,
        'active_courses': active_courses,
        'completed_courses': completed_courses,
        'title': 'Личный кабинет студента'
    })

@login_required
@teacher_required
def teacher_dashboard(request):
    """Личный кабинет преподавателя"""
    instructor = request.user.instructor
    courses = Course.objects.filter(instructor=instructor, is_active=True)
    
    # Статистика по курсам
    course_stats = []
    total_students = 0
    
    for course in courses:
        student_count = course.enrolled_students_count()
        total_students += student_count
        stats = {
            'course': course,
            'student_count': student_count,
            'available_spots': course.available_spots(),
            'completion_rate': course.enrollments.filter(status='COMPLETED').count()
        }
        course_stats.append(stats)
    
    return render(request, 'fefu_lab/dashboard/teacher_dashboard.html', {
        'instructor': instructor,
        'course_stats': course_stats,
        'total_courses': courses.count(),
        'total_students': total_students,
        'title': 'Личный кабинет преподавателя'
    })

@login_required
@admin_required
def admin_dashboard(request):
    """Панель администратора"""
    stats = {
        'total_users': User.objects.count(),
        'total_students': Student.objects.count(),
        'total_teachers': Instructor.objects.filter(is_active=True).count(),
        'total_courses': Course.objects.count(),
        'active_courses': Course.objects.filter(is_active=True).count(),
        'total_enrollments': Enrollment.objects.count(),
    }
    
    # Последние зарегистрированные пользователи
    recent_users = User.objects.order_by('-date_joined')[:5]
    
    # Курсы с низкой доступностью мест
    crowded_courses = Course.objects.filter(
        is_active=True
    ).annotate(
        enrolled_count=Count('enrollments')
    ).filter(
        enrolled_count__gte=F('max_students') - 5
    )[:5]
    
    return render(request, 'fefu_lab/dashboard/admin_dashboard.html', {
        'stats': stats,
        'recent_users': recent_users,
        'crowded_courses': crowded_courses,
        'title': 'Панель администратора'
    })

# =============================================================================
# СУЩЕСТВУЮЩИЕ ПРЕДСТАВЛЕНИЯ (ОБНОВЛЕННЫЕ ДЛЯ НОВОЙ СТРУКТУРЫ)
# =============================================================================

def home(request):
    """Главная страница с реальными данными из БД"""
    total_students = Student.objects.count()
    total_courses = Course.objects.filter(is_active=True).count()
    total_instructors = Instructor.objects.filter(is_active=True).count()
    recent_courses = Course.objects.filter(is_active=True).order_by('-created_at')[:3]
    
    # Проверяем аутентификацию для персональных рекомендаций
    user_courses = None
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        if request.user.profile.role == 'STUDENT' and hasattr(request.user, 'student'):
            user_courses = Enrollment.objects.filter(
                student=request.user.student, 
                status='ACTIVE'
            ).select_related('course')[:3]
    
    return render(request, 'fefu_lab/home.html', {
        'students': Student.objects.all()[:5],
        'courses': Course.objects.filter(is_active=True)[:5],
        'total_students': total_students,
        'total_courses': total_courses,
        'total_instructors': total_instructors,
        'recent_courses': recent_courses,
        'user_courses': user_courses,
    })

def student_profile(request, student_id):
    """Профиль студента с реальными данными из БД"""
    student = get_object_or_404(Student, pk=student_id)
    enrollments = Enrollment.objects.filter(student=student).select_related('course')
    
    # Проверяем права доступа (только свой профиль или администратор)
    if (request.user.is_authenticated and 
        hasattr(request.user, 'student') and 
        request.user.student.id != student_id and
        not (hasattr(request.user, 'profile') and request.user.profile.role in ['TEACHER', 'ADMIN'])):
        return HttpResponseForbidden("У вас нет прав для просмотра этого профиля")
    
    return render(request, 'fefu_lab/student_profile.html', {
        'student': student,
        'enrollments': enrollments,
    })

def course_detail(request, course_slug):
    """Детальная информация о курсе с реальными данными из БД"""
    course = get_object_or_404(Course, slug=course_slug, is_active=True)
    enrollments = Enrollment.objects.filter(course=course, status='ACTIVE').select_related('student')
    available_spots = course.available_spots()
    
    # Проверяем, записан ли текущий пользователь на курс
    is_enrolled = False
    if request.user.is_authenticated and hasattr(request.user, 'student'):
        is_enrolled = Enrollment.objects.filter(
            student=request.user.student, 
            course=course, 
            status='ACTIVE'
        ).exists()
    
    return render(request, 'fefu_lab/course_detail.html', {
        'course': course,
        'enrollments': enrollments,
        'available_spots': available_spots,
        'is_enrolled': is_enrolled,
    })

@login_required
@student_required
def enroll_in_course(request, course_slug):
    """Запись студента на курс"""
    course = get_object_or_404(Course, slug=course_slug, is_active=True)
    student = request.user.student
    
    # Проверяем, не записан ли уже студент
    if Enrollment.objects.filter(student=student, course=course).exists():
        messages.warning(request, f'Вы уже записаны на курс "{course.title}"')
        return redirect('course_detail', course_slug=course_slug)
    
    # Проверяем наличие свободных мест
    if course.available_spots() <= 0:
        messages.error(request, f'На курс "{course.title}" нет свободных мест')
        return redirect('course_detail', course_slug=course_slug)
    
    # Создаем запись о записи на курс
    Enrollment.objects.create(student=student, course=course)
    messages.success(request, f'Вы успешно записались на курс "{course.title}"')
    return redirect('student_dashboard')

def student_list(request):
    """Список всех студентов с фильтрацией по факультету"""
    students = Student.objects.all().order_by('user__last_name', 'user__first_name')
    faculty_filter = request.GET.get('faculty')
    
    if faculty_filter:
        students = students.filter(faculty=faculty_filter)
    
    return render(request, 'fefu_lab/student_list.html', {
        'students': students,
        'faculty_filter': faculty_filter,
    })

def course_list(request):
    """Список всех курсов с фильтрацией по уровню"""
    courses = Course.objects.filter(is_active=True).order_by('-created_at')
    level_filter = request.GET.get('level')
    
    if level_filter:
        courses = courses.filter(level=level_filter)
    
    return render(request, 'fefu_lab/course_list.html', {
        'courses': courses,
        'level_filter': level_filter,
    })

# =============================================================================
# ПРЕДСТАВЛЕНИЯ ДЛЯ ПРЕПОДАВАТЕЛЕЙ
# =============================================================================

@login_required
@teacher_required
def teacher_course_management(request, course_slug):
    """Управление курсом для преподавателя"""
    course = get_object_or_404(Course, slug=course_slug, is_active=True)
    
    # Проверяем, что текущий пользователь - преподаватель этого курса
    if course.instructor != request.user.instructor:
        return HttpResponseForbidden("У вас нет прав для управления этим курсом")
    
    enrollments = Enrollment.objects.filter(course=course).select_related('student')
    
    if request.method == 'POST':
        # Обработка изменения статусов записей
        for enrollment in enrollments:
            new_status = request.POST.get(f'status_{enrollment.id}')
            new_grade = request.POST.get(f'grade_{enrollment.id}')
            
            if new_status and new_status != enrollment.status:
                enrollment.status = new_status
                if new_status == 'COMPLETED' and not enrollment.completed_at:
                    from django.utils import timezone
                    enrollment.completed_at = timezone.now()
                enrollment.save()
            
            if new_grade and new_grade != enrollment.grade:
                enrollment.grade = new_grade
                enrollment.save()
        
        messages.success(request, 'Изменения успешно сохранены')
        return redirect('teacher_course_management', course_slug=course_slug)
    
    return render(request, 'fefu_lab/teacher/course_management.html', {
        'course': course,
        'enrollments': enrollments,
        'title': f'Управление курсом: {course.title}'
    })

# =============================================================================
# ФОРМЫ И ОБРАТНАЯ СВЯЗЬ (СОХРАНЕНЫ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ)
# =============================================================================

def feedback_view(request):
    """Обработка формы обратной связи"""
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            # В реальном приложении здесь была бы отправка email или сохранение в БД
            return render(request, 'fefu_lab/success.html', {
                'message': 'Спасибо за ваш отзыв! Мы свяжемся с вами в ближайшее время.',
                'title': 'Обратная связь'
            })
        else:
            return render(request, 'fefu_lab/feedback.html', {
                'form': form,
                'title': 'Обратная связь',
                'errors': form.errors
            })
    else:
        form = FeedbackForm()
    
    return render(request, 'fefu_lab/feedback.html', {
        'form': form,
        'title': 'Обратная связь'
    })

# =============================================================================
# КЛАССЫ-ПРЕДСТАВЛЕНИЯ И СПЕЦИАЛЬНЫЕ ОБРАБОТЧИКИ
# =============================================================================

class AboutView(View):
    """Страница 'О нас' со статистикой из БД"""
    
    def get(self, request):
        stats = {
            'total_students': Student.objects.count(),
            'total_courses': Course.objects.filter(is_active=True).count(),
            'total_instructors': Instructor.objects.filter(is_active=True).count(),
        }
        return render(request, 'fefu_lab/about.html', {'stats': stats})

def custom_404(request, exception):
    """Кастомная страница 404 ошибки"""
    return render(request, 'fefu_lab/404.html', status=404)

def custom_500(request):
    """Кастомная страница 500 ошибки"""
    return render(request, 'fefu_lab/500.html', status=500)

# =============================================================================
# API-ПРЕДСТАВЛЕНИЯ ДЛЯ AJAX (ОПЦИОНАЛЬНО)
# =============================================================================

@login_required
def api_user_info(request):
    """API для получения информации о текущем пользователе"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        user = request.user
        data = {
            'username': user.username,
            'full_name': user.get_full_name(),
            'email': user.email,
            'role': user.profile.role if hasattr(user, 'profile') else 'UNKNOWN',
        }
        return JsonResponse(data)
    return HttpResponseForbidden()

# =============================================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# =============================================================================

def check_permissions(user, required_role):
    """Утилитарная функция для проверки прав доступа"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == required_role

def get_user_statistics(user):
    """Получение статистики пользователя в зависимости от роли"""
    if not user.is_authenticated or not hasattr(user, 'profile'):
        return None
    
    profile = user.profile
    stats = {}
    
    if profile.role == 'STUDENT' and hasattr(user, 'student'):
        student = user.student
        enrollments = Enrollment.objects.filter(student=student)
        stats.update({
            'total_courses': enrollments.count(),
            'active_courses': enrollments.filter(status='ACTIVE').count(),
            'completed_courses': enrollments.filter(status='COMPLETED').count(),
        })
    elif profile.role == 'TEACHER' and hasattr(user, 'instructor'):
        instructor = user.instructor
        courses = Course.objects.filter(instructor=instructor, is_active=True)
        stats.update({
            'total_courses': courses.count(),
            'total_students': sum(course.enrolled_students_count() for course in courses),
        })
    
    return stats
