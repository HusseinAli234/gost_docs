from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm # Импортируем стандартную форму входа

class RegisterForm(UserCreationForm):


    username = forms.CharField(label='Имя пользователя', max_length=150, required=True)
    email = forms.EmailField(label='Email адрес', required=True)
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput, required=True)
    password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='Имя пользователя', max_length=150, required=True)
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput, required=True)
    class Meta:
        model = User
        fields = ['username','password']


    """
    Пользовательская форма входа для добавления Bootstrap классов к полям.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем класс 'form-control' ко всем полям виджетов
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
