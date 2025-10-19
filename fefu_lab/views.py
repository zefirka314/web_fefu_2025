from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.views import View

# Mock данные для демонстрации
STUDENTS = {
    1: {'name': 'Иван Иванов', 'faculty': 'Информатика', 'year': 2},
    2: {'name': 'Петр Петров', 'faculty': 'Математика', 'year': 3},
}

COURSES = {
    'python-basic': {'title': 'Основы Python', 'description': 'Базовый курс программирования', 'duration': '3 месяца'},
    'django-advanced': {'title': 'Django Pro', 'description': 'Продвинутый веб-разработка', 'duration': '2 месяца'},
}

# Function-Based Views
def home(request):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Главная страница</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 40px;
                line-height: 1.6;
            }
            .container { 
                max-width: 800px; 
                margin: 0 auto;
                padding: 20px;
                background: #f9f9f9;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 { color: #333; }
            nav { 
                background: #007bff; 
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }
            nav a { 
                margin-right: 15px; 
                text-decoration: none; 
                color: white;
                font-weight: bold;
            }
            nav a:hover { text-decoration: underline; }
            .section { margin: 30px 0; }
            .card {
                background: white;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                border-left: 4px solid #007bff;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Добро пожаловать в учебную систему!</h1>
            
            <nav>
                <a href="/about/">О нас</a>
                <a href="/student/1/">Студент 1</a>
                <a href="/student/2/">Студент 2</a>
                <a href="/course/python-basic/">Курс Python</a>
                <a href="/course/django-advanced/">Курс Django</a>
            </nav>
            
            <div class="section">
                <h2>Наши студенты</h2>
                <div class="card">
                    <h3><a href="/student/1/">Иван Иванов</a></h3>
                    <p>Факультет: Информатика, 2 курс</p>
                </div>
                <div class="card">
                    <h3><a href="/student/2/">Петр Петров</a></h3>
                    <p>Факультет: Математика, 3 курс</p>
                </div>
            </div>
            
            <div class="section">
                <h2>Наши курсы</h2>
                <div class="card">
                    <h3><a href="/course/python-basic/">Основы Python</a></h3>
                    <p>Базовый курс программирования - 3 месяца</p>
                </div>
                <div class="card">
                    <h3><a href="/course/django-advanced/">Django Pro</a></h3>
                    <p>Продвинутый веб-разработка - 2 месяца</p>
                </div>
            </div>
            
            <p><em>Используйте навигацию выше для просмотра детальной информации.</em></p>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)

def student_detail(request, student_id):
    student = STUDENTS.get(student_id)
    if not student:
        raise Http404("Студент с таким ID не найден")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Студент {student_id}</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                margin: 40px;
                line-height: 1.6;
            }}
            .container {{ 
                max-width: 800px; 
                margin: 0 auto;
                padding: 20px;
                background: #f9f9f9;
                border-radius: 8px;
            }}
            .back-link {{ 
                color: #007bff; 
                text-decoration: none; 
                font-weight: bold;
            }}
            .back-link:hover {{ text-decoration: underline; }}
            .info-card {{
                background: white;
                padding: 20px;
                border-radius: 5px;
                margin: 20px 0;
                border-left: 4px solid #007bff;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Информация о студенте</h1>
            <div class="info-card">
                <p><strong>ID:</strong> {student_id}</p>
                <p><strong>Имя:</strong> {student['name']}</p>
                <p><strong>Факультет:</strong> {student['faculty']}</p>
                <p><strong>Курс:</strong> {student['year']}</p>
            </div>
            <a href="/" class="back-link">← На главную</a>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)

# Class-Based Views
class AboutView(View):
    def get(self, request):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>О нас</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 40px;
                    line-height: 1.6;
                }
                .container { 
                    max-width: 800px; 
                    margin: 0 auto;
                    padding: 20px;
                    background: #f9f9f9;
                    border-radius: 8px;
                }
                .back-link { 
                    color: #007bff; 
                    text-decoration: none; 
                    font-weight: bold;
                }
                .back-link:hover { text-decoration: underline; }
                ul { 
                    background: white;
                    padding: 20px;
                    border-radius: 5px;
                }
                li { margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>О нас</h1>
                <p>Мы - современное учебное заведение с инновационным подходом к образованию.</p>
                <p>Наши программы включают актуальные IT-технологии и практические навыки.</p>
                
                <h2>Наши преимущества:</h2>
                <ul>
                    <li>Качественное образование</li>
                    <li>Современные методики обучения</li>
                    <li>Практическая направленность</li>
                    <li>Опытные преподаватели</li>
                    <li>Современная инфраструктура</li>
                </ul>
                
                <a href="/" class="back-link">← На главную</a>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html)

class CourseDetailView(View):
    def get(self, request, course_slug):
        course = COURSES.get(course_slug)
        if not course:
            raise Http404("Курс с таким названием не найден")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{course['title']}</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 40px;
                    line-height: 1.6;
                }}
                .container {{ 
                    max-width: 800px; 
                    margin: 0 auto;
                    padding: 20px;
                    background: #f9f9f9;
                    border-radius: 8px;
                }}
                .back-link {{ 
                    color: #007bff; 
                    text-decoration: none; 
                    font-weight: bold;
                }}
                .back-link:hover {{ text-decoration: underline; }}
                .info-card {{
                    background: white;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                    border-left: 4px solid #28a745;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Информация о курсе</h1>
                <div class="info-card">
                    <p><strong>Slug:</strong> {course_slug}</p>
                    <p><strong>Название:</strong> {course['title']}</p>
                    <p><strong>Описание:</strong> {course['description']}</p>
                    <p><strong>Продолжительность:</strong> {course['duration']}</p>
                </div>
                <a href="/" class="back-link">← На главную</a>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html)

# Обработчик 404
def custom_404(request, exception):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Страница не найдена</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 40px; 
                text-align: center;
                background: #f8f9fa;
            }
            .container { 
                max-width: 600px; 
                margin: 100px auto;
                padding: 40px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .error-code { 
                font-size: 72px; 
                color: #dc3545; 
                margin: 0;
            }
            .home-link {
                display: inline-block;
                margin-top: 20px;
                padding: 10px 20px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
            }
            .home-link:hover {
                background: #0056b3;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="error-code">404</div>
            <h1>Страница не найдена</h1>
            <p>Запрошенная страница не существует или была перемещена.</p>
            <a href="/" class="home-link">Вернуться на главную</a>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html, status=404)
