from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, HttpResponse
from django.views import View
from django.db.models import Count, Q
from django.core.exceptions import ObjectDoesNotExist

from .forms import FeedbackForm, RegistrationForm, LoginForm, StudentRegistrationForm, CourseEnrollmentForm
from .models import UserProfile, Student, Course, Enrollment, Instructor

def home(request):
    """Главная страница с реальными данными из БД"""
    total_students = Student.objects.count()
    total_courses = Course.objects.filter(is_active=True).count()
    total_instructors = Instructor.objects.filter(is_active=True).count()
    recent_courses = Course.objects.filter(is_active=True).order_by('-created_at')[:3]
    
    return render(request, 'fefu_lab/home.html', {
        'students': Student.objects.all()[:5],
        'courses': Course.objects.filter(is_active=True)[:5],
        'total_students': total_students,
        'total_courses': total_courses,
        'total_instructors': total_instructors,
        'recent_courses': recent_courses,
    })

def student_profile(request, student_id):
    """Профиль студента с реальными данными из БД"""
    student = get_object_or_404(Student, pk=student_id)
    enrollments = Enrollment.objects.filter(student=student).select_related('course')
    
    return render(request, 'fefu_lab/student_profile.html', {
        'student': student,
        'enrollments': enrollments,
        'student_id': student.id,
        'student_info': student.full_name,
        'faculty': student.get_faculty_display_name(),
        'status': 'Активный'
    })

def course_detail(request, course_slug):
    """Детальная информация о курсе с реальными данными из БД"""
    course = get_object_or_404(Course, slug=course_slug, is_active=True)
    enrollments = Enrollment.objects.filter(course=course, status='ACTIVE').select_related('student')
    available_spots = course.available_spots()
    
    return render(request, 'fefu_lab/course_detail.html', {
        'course': course,
        'enrollments': enrollments,
        'available_spots': available_spots,
        'course_slug': course.slug,
        'course_name': course.title,
        'duration': course.duration,
        'description': course.description,
        'instructor': course.instructor.full_name if course.instructor else 'Не назначен',
        'level': course.get_level_display(),
    })

def student_list(request):
    """Список всех студентов с фильтрацией по факультету"""
    students = Student.objects.all().order_by('last_name', 'first_name')
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

class AboutView(View):
    """Страница 'О нас' со статистикой из БД"""
    def get(self, request):
        stats = {
            'total_students': Student.objects.count(),
            'total_courses': Course.objects.filter(is_active=True).count(),
            'total_instructors': Instructor.objects.filter(is_active=True).count(),
        }
        return render(request, 'fefu_lab/about.html', {'stats': stats})

def feedback_view(request):
    """Обработка формы обратной связи"""
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
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

def register_view(request):
    """Регистрация пользователя в системе"""
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            user = UserProfile(username=username, email=email, password=password)
            user.save()
            
            return render(request, 'fefu_lab/success.html', {
                'message': 'Регистрация прошла успешно! Добро пожаловать в нашу систему.',
                'title': 'Регистрация'
            })
        else:
            return render(request, 'fefu_lab/register.html', {
                'form': form,
                'title': 'Регистрация',
                'errors': form.errors
            })
    else:
        form = RegistrationForm()
    
    return render(request, 'fefu_lab/register.html', {
        'form': form,
        'title': 'Регистрация'
    })

def student_registration_view(request):
    """Регистрация нового студента в университетской системе"""
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            student = form.save()
            return render(request, 'fefu_lab/success.html', {
                'message': f'Регистрация студента {student.full_name} прошла успешно!',
                'title': 'Регистрация студента'
            })
        else:
            return render(request, 'fefu_lab/student_registration.html', {
                'form': form,
                'title': 'Регистрация студента',
                'errors': form.errors
            })
    else:
        form = StudentRegistrationForm()
    
    return render(request, 'fefu_lab/student_registration.html', {
        'form': form,
        'title': 'Регистрация студента'
    })

def login_view(request):
    """Аутентификация пользователя"""
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            try:
                user = UserProfile.objects.get(username=username)
                if user.check_password(password):
                    request.session['user_id'] = user.id
                    request.session['username'] = user.username
                    return render(request, 'fefu_lab/success.html', {
                        'message': f'Вход выполнен успешно! Добро пожаловать, {user.username}.',
                        'title': 'Вход в систему'
                    })
                else:
                    form.add_error('password', 'Неверный пароль')
            except UserProfile.DoesNotExist:
                form.add_error('username', 'Пользователь с таким логином не найден')
        
        return render(request, 'fefu_lab/login.html', {
            'form': form,
            'title': 'Вход в систему',
            'errors': form.errors
        })
    else:
        form = LoginForm()
        return render(request, 'fefu_lab/login.html', {
            'form': form,
            'title': 'Вход в систему'
        })

def custom_404(request, exception):
    """Кастомная страница 404 ошибки"""
    return render(request, 'fefu_lab/404.html', status=404)
