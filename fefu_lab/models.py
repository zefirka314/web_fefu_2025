from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator

# Существующая модель - сохраняем
class UserProfile(models.Model):
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def set_password(self, raw_password):
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
    
    def save(self, *args, **kwargs):
        if not self.pk or UserProfile.objects.get(pk=self.pk).password != self.password:
            self.set_password(self.password)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.username

# Новые модели по заданию
class Student(models.Model):
    FACULTY_CHOICES = [
        ('CS', 'Кибербезопасность'),
        ('SE', 'Программная инженерия'),
        ('IT', 'Информационные технологии'),
        ('DS', 'Наука о данных'),
        ('WEB', 'Веб-технологии'),
    ]
    
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    email = models.EmailField(unique=True, verbose_name='Email')
    birth_date = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    faculty = models.CharField(max_length=3, choices=FACULTY_CHOICES, default='CS', verbose_name='Факультет')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Студент'
        verbose_name_plural = 'Студенты'
        ordering = ['last_name', 'first_name']
        db_table = 'students'
    
    def __str__(self):
        return f"{self.last_name} {self.first_name}"
    
    def get_absolute_url(self):
        return reverse('student_profile', kwargs={'pk': self.pk})
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_faculty_display_name(self):
        return dict(self.FACULTY_CHOICES).get(self.faculty, 'Неизвестно')

class Instructor(models.Model):
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    email = models.EmailField(unique=True, verbose_name='Email')
    specialization = models.CharField(max_length=200, blank=True, verbose_name='Специализация')
    degree = models.CharField(max_length=100, blank=True, verbose_name='Ученая степень')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Преподаватель'
        verbose_name_plural = 'Преподаватели'
        ordering = ['last_name', 'first_name']
        db_table = 'instructors'
    
    def __str__(self):
        return f"{self.last_name} {self.first_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Course(models.Model):
    LEVEL_CHOICES = [
        ('BEGINNER', 'Начальный'),
        ('INTERMEDIATE', 'Средний'),
        ('ADVANCED', 'Продвинутый'),
    ]
    
    title = models.CharField(max_length=200, unique=True, verbose_name='Название')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='URL-идентификатор')
    description = models.TextField(verbose_name='Описание')
    duration = models.PositiveIntegerField(
        verbose_name='Продолжительность (часов)',
        validators=[MinValueValidator(1), MaxValueValidator(500)]
    )
    instructor = models.ForeignKey(
        Instructor, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='Преподаватель'
    )
    level = models.CharField(max_length=12, choices=LEVEL_CHOICES, default='BEGINNER', verbose_name='Уровень')
    max_students = models.PositiveIntegerField(default=30, verbose_name='Максимум студентов')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Стоимость')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        ordering = ['-created_at']
        db_table = 'courses'
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('course_detail', kwargs={'slug': self.slug})
    
    def enrolled_students_count(self):
        return self.enrollment_set.filter(status='ACTIVE').count()
    
    def available_spots(self):
        return self.max_students - self.enrolled_students_count()

class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Активен'),
        ('COMPLETED', 'Завершен'),
        ('DROPPED', 'Отчислен'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name='Студент')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name='Курс')
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата записи')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE', verbose_name='Статус')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата завершения')
    
    class Meta:
        verbose_name = 'Запись на курс'
        verbose_name_plural = 'Записи на курсы'
        unique_together = ['student', 'course']
        ordering = ['-enrolled_at']
        db_table = 'enrollments'
    
    def __str__(self):
        return f"{self.student} - {self.course}"
