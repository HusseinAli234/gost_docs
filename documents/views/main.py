# documents/views.py

from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView,
    CreateView, UpdateView, DeleteView
)
from django.contrib.auth.mixins import (
    LoginRequiredMixin, UserPassesTestMixin
)
from documents.models import Document_main
from documents.forms import Document_mainForm


class DocumentListView(LoginRequiredMixin, ListView):
    model = Document_main
    template_name = 'main/main_list.html'
    context_object_name = 'mains'

    def get_queryset(self):
        # Возвращаем только документы текущего пользователя
        return Document_main.objects.filter(owner=self.request.user)


class DocumentDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Document_main
    template_name = 'main/main_detail.html'
    context_object_name = 'main'

    def test_func(self):
        # Проверяем, что текущий пользователь — владелец документа
        return self.get_object().owner == self.request.user


class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = Document_main
    form_class = Document_mainForm
    template_name = 'main/main_form.html'
    success_url = reverse_lazy('documents:main_list')

    def form_valid(self, form):
        # Перед сохранением привязываем owner к текущему пользователю
        form.instance.owner = self.request.user
        return super().form_valid(form)


class DocumentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Document_main
    form_class = Document_mainForm
    template_name = 'main/main_form.html'
    success_url = reverse_lazy('documents:main_list')

    def test_func(self):
        return self.get_object().owner == self.request.user


class DocumentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Document_main
    template_name = 'main/main_confirm_delete.html'
    success_url = reverse_lazy('documents:main_list')

    def test_func(self):
        return self.get_object().owner == self.request.user
