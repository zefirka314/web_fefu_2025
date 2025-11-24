from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
import os

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('STUDENT', 'Студент'),
        ('TEACHER', 'Преподаватель'),
        ('ADMIN', 'Администратор'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='STUDENT',
        verbose_name='Роль'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Аватар'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Телефон'
    )
    bio = models.TextField(
        blank=True,
        verbose_name='О себе'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
        db_table = 'user_profiles'

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_role_display()})"

    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return '/static/fefu_lab/images/default-avatar.png'

    def is_student(self):
        return self.role == 'STUDENT'

    def is_teacher(self):
        return self.role == 'TEACHER'

    def is_admin(self):
        return self.role == 'ADMIN'

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Создание профиля пользователя при создании пользователя"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Сохранение профиля пользователя при сохранении пользователя"""
    if hasattr(instance, 'profile'):
        instance.profile.save()

class Student(models.Model):
    FACULTY_CHOICES = [
        ('CS', 'Кибербезопасность'),
        ('SE', 'Программная инженерия'),
        ('IT', 'Информационные технологии'),
        ('DS', 'Наука о данных'),
        ('WEB', 'Веб-технологии'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student',
        verbose_name='Пользователь'
    )
    faculty = models.CharField(
        max_length=3,
        choices=FACULTY_CHOICES,
        default='CS',
        verbose_name='Факультет'
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата рождения'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Студент'
        verbose_name_plural = 'Студенты'
        ordering = ['user__last_name', 'user__first_name']
        db_table = 'students'

    def __str__(self):
        return f"{self.user.get_full_name()}"

    def get_absolute_url(self):
        return reverse('student_profile', kwargs={'student_id': self.pk})

    @property
    def first_name(self):
        return self.user.first_name

    @property
    def last_name(self):
        return self.user.last_name

    @property
    def full_name(self):
        return self.user.get_full_name()

    @property
    def email(self):
        return self.user.email

    def get_faculty_display_name(self):
        return dict(self.FACULTY_CHOICES).get(self.faculty, 'Неизвестно')

    def get_age(self):
        if self.birth_date:
            from datetime import date
            today = date.today()
            return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return None

@receiver(post_save, sender=UserProfile)
def create_student_for_student_role(sender, instance, created, **kwargs):
    """Автоматическое создание записи Student при установке роли STUDENT"""
    if instance.role == 'STUDENT' and not hasattr(instance.user, 'student'):
        Student.objects.create(user=instance.user)

class Instructor(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='instructor',
        verbose_name='Пользователь'
    )
    specialization = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Специализация'
    )
    degree = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Ученая степень'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        verbose_name = 'Преподаватель'
        verbose_name_plural = 'Преподаватели'
        ordering = ['user__last_name', 'user__first_name']
        db_table = 'instructors'

    def __str__(self):
        return f"{self.user.get_full_name()}"

    @property
    def first_name(self):
        return self.user.first_name

    @property
    def last_name(self):
        return self.user.last_name

    @property
    def full_name(self):
        return self.user.get_full_name()

    @property
    def email(self):
        return self.user.email

    def get_courses_count(self):
        return self.course_set.filter(is_active=True).count()

@receiver(post_save, sender=UserProfile)
def create_instructor_for_teacher_role(sender, instance, created, **kwargs):
    """Автоматическое создание записи Instructor при установке роли TEACHER"""
    if instance.role == 'TEACHER' and not hasattr(instance.user, 'instructor'):
        Instructor.objects.create(user=instance.user)

class Course(models.Model):
    LEVEL_CHOICES = [
        ('BEGINNER', 'Начальный'),
        ('INTERMEDIATE', 'Средний'),
        ('ADVANCED', 'Продвинутый'),
    ]
    
    title = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='Название'
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name='URL-идентификатор'
    )
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
        verbose_name='Преподаватель',
        related_name='courses'
    )
    level = models.CharField(
        max_length=12,
        choices=LEVEL_CHOICES,
        default='BEGINNER',
        verbose_name='Уровень'
    )
    max_students = models.PositiveIntegerField(
        default=30,
        verbose_name='Максимум студентов'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Стоимость'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

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
        return self.enrollments.filter(status='ACTIVE').count()

    def available_spots(self):
        return self.max_students - self.enrolled_students_count()

    def get_level_display_name(self):
        return dict(self.LEVEL_CHOICES).get(self.level, 'Неизвестно')

class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Активен'),
        ('COMPLETED', 'Завершен'),
        ('DROPPED', 'Отчислен'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        verbose_name='Студент',
        related_name='enrollments'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        verbose_name='Курс',
        related_name='enrollments'
    )
    enrolled_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата записи'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        verbose_name='Статус'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата завершения'
    )
    grade = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='Оценка',
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    class Meta:
        verbose_name = 'Запись на курс'
        verbose_name_plural = 'Записи на курсы'
        unique_together = ['student', 'course']
        ordering = ['-enrolled_at']
        db_table = 'enrollments'

    def __str__(self):
        return f"{self.student} - {self.course}"

    def is_active(self):
        return self.status == 'ACTIVE'

    def is_completed(self):
        return self.status == 'COMPLETED'

    def get_status_badge_class(self):
        status_classes = {
            'ACTIVE': 'badge-active',
            'COMPLETED': 'badge-completed',
            'DROPPED': 'badge-dropped',
        }
        return status_classes.get(self.status, '')

# Сохранение старой модели UserProfile для обратной совместимости
class LegacyUserProfile(models.Model):
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'legacy_user_profiles'
        verbose_name = 'Устаревший профиль'
        verbose_name_plural = 'Устаревшие профили'

    def __str__(self):
        return self.username

    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)
    
    def save(self, *args, **kwargs):
        if not self.pk or not LegacyUserProfile.objects.filter(pk=self.pk, password=self.password).exists():
            self.set_password(self.password)
        super().save(*args, **kwargs)
