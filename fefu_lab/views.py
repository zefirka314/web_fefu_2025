from django.shortcuts import render
from django.http import Http404
from django.views import View
from .forms import FeedbackForm, RegistrationForm, LoginForm
from .models import UserProfile

# Mock данные для демонстрации
STUDENTS = {
    1: {'name': 'Иван Иванов', 'faculty': 'Информатика', 'year': 2},
    2: {'name': 'Петр Петров', 'faculty': 'Математика', 'year': 3},
}

COURSES = {
    'python-basic': {'title': 'Основы Python', 'description': 'Базовый курс программирования', 'duration': '3 месяца'},
    'django-advanced': {'title': 'Django Pro', 'description': 'Продвинутый веб-разработка', 'duration': '2 месяца'},
}

# Новые данные по заданию
STUDENTS_DATA = {
    1: {
        'info': 'Иван Петров',
        'faculty': 'Кибербезопасность',
        'status': 'Активный',
        'year': 3
    },
    2: {
        'info': 'Мария Сидорова', 
        'faculty': 'Информатика',
        'status': 'Активный',
        'year': 2
    },
    3: {
        'info': 'Алексей Козлов',
        'faculty': 'Программная инженерия', 
        'status': 'Выпускник',
        'year': 5
    }
}

COURSES_DATA = {
    'python-basics': {
        'name': 'Основы программирования на Python',
        'duration': 36,
        'description': 'Базовый курс по программированию на языке Python для начинающих.',
        'instructor': 'Доцент Петров И.С.',
        'level': 'Начальный'
    },
    'web-security': {
        'name': 'Веб-безопасность',
        'duration': 48,
        'description': 'Курс по защите веб-приложений от современных угроз.',
        'instructor': 'Профессор Сидоров А.В.',
        'level': 'Продвинутый'
    },
    'network-defense': {
        'name': 'Защита сетей',
        'duration': 42,
        'description': 'Изучение методов и технологий защиты компьютерных сетей.',
        'instructor': 'Доцент Козлова М.П.',
        'level': 'Средний'
    }
}

# Function-Based Views
def home(request):
    return render(request, 'fefu_lab/home.html', {
        'students': STUDENTS_DATA,
        'courses': COURSES_DATA
    })

def student_profile(request, student_id):
    if student_id in STUDENTS_DATA:
        student_data = STUDENTS_DATA[student_id]
        return render(request, 'fefu_lab/student_profile.html', {
            'student_id': student_id,
            'student_info': student_data['info'],
            'faculty': student_data['faculty'],
            'status': student_data['status'],
            'year': student_data['year']
        })
    else:
        raise Http404("Студент с таким ID не найден")

def course_detail(request, course_slug):
    if course_slug in COURSES_DATA:
        course_data = COURSES_DATA[course_slug]
        return render(request, 'fefu_lab/course_detail.html', {
            'course_slug': course_slug,
            'course_name': course_data['name'],
            'duration': course_data['duration'],
            'description': course_data['description'],
            'instructor': course_data['instructor'],
            'level': course_data['level']
        })
    else:
        raise Http404("Курс с таким названием не найден")

# Class-Based Views
class AboutView(View):
    def get(self, request):
        return render(request, 'fefu_lab/about.html')

# Формы - ПЕРЕПИСАННАЯ ЛОГИКА
def feedback_view(request):
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            # Форма валидна - сохраняем данные и показываем успех
            return render(request, 'fefu_lab/success.html', {
                'message': 'Спасибо за ваш отзыв! Мы свяжемся с вами в ближайшее время.',
                'title': 'Обратная связь'
            })
        else:
            # Форма невалидна - показываем ошибки
            return render(request, 'fefu_lab/feedback.html', {
                'form': form,
                'title': 'Обратная связь',
                'errors': form.errors
            })
    else:
        # GET запрос - показываем пустую форму
        form = FeedbackForm()
    
    return render(request, 'fefu_lab/feedback.html', {
        'form': form,
        'title': 'Обратная связь'
    })

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            # Сохраняем пользователя в базу данных
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

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            return render(request, 'fefu_lab/success.html', {
                'message': 'Вход выполнен успешно! Добро пожаловать в систему.',
                'title': 'Вход в систему'
            })
        else:
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

# Обработчик 404
def custom_404(request, exception):
    return render(request, 'fefu_lab/404.html', status=404)
