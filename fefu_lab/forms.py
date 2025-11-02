from django import forms
from django.core.exceptions import ValidationError
from .models import UserProfile

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

class RegistrationForm(forms.Form):
    username = forms.CharField(
        max_length=50,
        label='Логин',
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Придумайте логин'
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
    password = forms.CharField(
        label='Пароль',
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Придумайте пароль'
        })
    )
    password_confirm = forms.CharField(
        label='Подтверждение пароля',
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторите пароль'
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if len(username) < 3:
            raise ValidationError("Логин должен содержать минимум 3 символа")
        
        if UserProfile.objects.filter(username=username).exists():
            raise ValidationError("Пользователь с таким логином уже существует")
        
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        
        if UserProfile.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с таким email уже существует")
        
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if len(password) < 8:
            raise ValidationError("Пароль должен содержать минимум 8 символов")
        
        if password.isdigit():
            raise ValidationError("Пароль не должен состоять только из цифр")
        
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise ValidationError("Пароли не совпадают")

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=50,
        label='Логин',
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваш логин'
        })
    )
    password = forms.CharField(
        label='Пароль',
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваш пароль'
        })
    )
