from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import UserProfile, Student, Instructor, Course, Enrollment

# ЗАЧЕМ: Эта форма заменяет старую RegistrationForm и интегрируется со встроенной системой пользователей Django
class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваш email'
        }),
        label='Email'
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваше имя'
        }),
        label='Имя'
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите вашу фамилию'
        }),
        label='Фамилия'
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваш телефон'
        }),
        label='Телефон'
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Расскажите о себе'
        }),
        label='О себе'
    )
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        initial='STUDENT',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Роль'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Придумайте имя пользователя'
            }),
        }
        labels = {
            'username': 'Имя пользователя',
        }

    # ЗАЧЕМ: Эта валидация гарантирует уникальность email в системе
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с таким email уже существует")
        return email

    # ЗАЧЕМ: Эта валидация проверяет, что имя пользователя не слишком короткое
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if len(username) < 3:
            raise ValidationError("Имя пользователя должно содержать минимум 3 символа")
        return username

    # ЗАЧЕМ: Этот метод сохраняет пользователя и автоматически создает связанные профили
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            
            # Обновляем профиль пользователя с дополнительными данными
            profile = user.profile
            profile.phone = self.cleaned_data['phone']
            profile.bio = self.cleaned_data['bio']
            profile.role = self.cleaned_data['role']
            profile.save()

            # ЗАЧЕМ: Автоматически создаем запись Student или Instructor в зависимости от роли
            if profile.role == 'STUDENT':
                Student.objects.get_or_create(user=user)
            elif profile.role == 'TEACHER':
                Instructor.objects.get_or_create(user=user)

        return user

# ЗАЧЕМ: Эта форма обеспечивает вход в систему с использованием email или username
class UserLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email или имя пользователя'
        }),
        label='Логин или Email'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваш пароль'
        }),
        label='Пароль'
    )

# ЗАЧЕМ: Эта форма позволяет редактировать основные данные пользователя из модели User
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'email': 'Email',
        }

    # ЗАЧЕМ: Эта валидация проверяет, что email остается уникальным при редактировании
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Пользователь с таким email уже существует")
        return email

# ЗАЧЕМ: Эта форма позволяет редактировать дополнительные данные из профиля UserProfile
class UserProfileExtendedForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone', 'bio', 'avatar']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+7 (XXX) XXX-XX-XX'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Расскажите о своих интересах, навыках и опыте...'
            }),
        }
        labels = {
            'phone': 'Телефон',
            'bio': 'О себе',
            'avatar': 'Аватар',
        }

# ЗАЧЕМ: Эта форма сохраняется для обратной совместимости со старым функционалом обратной связи
class FeedbackForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        label='Имя',
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваше имя'
        })
    )
    email = forms.EmailField(
        label='Email',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваш email'
        })
    )
    subject = forms.CharField(
        max_length=200,
        label='Тема сообщения',
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите тему сообщения'
        })
    )
    message = forms.CharField(
        label='Текст сообщения',
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Введите ваше сообщение'
        })
    )

    # ЗАЧЕМ: Эти валидации обеспечивают минимальные требования к данным обратной связи
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2:
            raise ValidationError("Имя должно содержать минимум 2 символа")
        return name

    def clean_message(self):
        message = self.cleaned_data.get('message', '').strip()
        if len(message) < 10:
            raise ValidationError("Сообщение должно содержать минимум 10 символов")
        return message

# ЗАЧЕМ: Эта форма сохраняется для обратной совместимости со старой системой регистрации студентов
class StudentRegistrationForm(forms.ModelForm):
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторите пароль'
        }),
        label='Подтверждение пароля'
    )
    
    class Meta:
        model = Student
        fields = ['faculty', 'birth_date']
        widgets = {
            'faculty': forms.Select(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'faculty': 'Факультет',
            'birth_date': 'Дата рождения',
        }

# ЗАЧЕМ: Эта форма позволяет студентам записываться на курсы
class CourseEnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['student', 'course']
        widgets = {
            'student': forms.HiddenInput(),
            'course': forms.HiddenInput(),
        }

# ЗАЧЕМ: Эта форма позволяет преподавателям управлять статусами записей на курсы
class EnrollmentStatusForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['status', 'grade', 'completed_at']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'grade': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '5',
                'step': '0.1'
            }),
            'completed_at': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'status': 'Статус',
            'grade': 'Оценка',
            'completed_at': 'Дата завершения',
        }

# ЗАЧЕМ: Эта форма позволяет создавать и редактировать курсы (для преподавателей и администраторов)
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'slug', 'description', 'duration', 'instructor', 'level', 'max_students', 'price', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'duration': forms.NumberInput(attrs={'class': 'form-control'}),
            'instructor': forms.Select(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-control'}),
            'max_students': forms.NumberInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'title': 'Название курса',
            'slug': 'URL-идентификатор',
            'description': 'Описание',
            'duration': 'Продолжительность (часов)',
            'instructor': 'Преподаватель',
            'level': 'Уровень сложности',
            'max_students': 'Максимальное количество студентов',
            'price': 'Стоимость (руб.)',
            'is_active': 'Активный курс',
        }

    # ЗАЧЕМ: Эта валидация гарантирует, что slug будет в правильном формате
    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if ' ' in slug:
            raise ValidationError("URL-идентификатор не должен содержать пробелов")
        return slug.lower()

# ЗАЧЕМ: Эта форма позволяет фильтровать студентов по факультету
class StudentFilterForm(forms.Form):
    faculty = forms.ChoiceField(
        choices=[('', 'Все факультеты')] + Student.FACULTY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'onchange': 'this.form.submit()'
        }),
        label='Факультет'
    )

# ЗАЧЕМ: Эта форма позволяет фильтровать курсы по уровню сложности
class CourseFilterForm(forms.Form):
    level = forms.ChoiceField(
        choices=[('', 'Все уровни')] + Course.LEVEL_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'onchange': 'this.form.submit()'
        }),
        label='Уровень сложности'
    )
