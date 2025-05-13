from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import RegisterForm

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # После регистрации перенаправляем на список ГОСТ-документов
            return redirect('documents:gost_list')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})
