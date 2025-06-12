# documents/views.py

from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView,
    CreateView, UpdateView, DeleteView
)
from django.contrib.auth.mixins import (
    LoginRequiredMixin, UserPassesTestMixin
)
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
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


def extract_text_from_file(file):
    """
    Извлекает текст из загруженного файла DOCX или PDF.
    
    Args:
        file: Загруженный файл
        
    Returns:
        str: Извлеченный текст из файла
    """
    import os
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
    
    # Сохраняем файл во временное хранилище
    file_name = file.name
    path = default_storage.save(f'temp/{file_name}', ContentFile(file.read()))
    file_path = default_storage.path(path)
    
    try:
        # Определяем тип файла по расширению
        file_ext = os.path.splitext(file_name)[1].lower()
        
        if file_ext == '.docx':
            # Для DOCX файлов используем python-docx
            # Примечание: требуется установка пакета python-docx
            from docx import Document
            doc = Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            extracted_text = '\n'.join(full_text)
            
        elif file_ext == '.pdf':
            # Для PDF файлов используем PyPDF2
            # Примечание: требуется установка пакета PyPDF2
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            full_text = []
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                full_text.append(page.extract_text())
            extracted_text = '\n'.join(full_text)
            
        else:
            extracted_text = "Неподдерживаемый формат файла. Пожалуйста, загрузите DOCX или PDF файл."
            
        return extracted_text
    
    except Exception as e:
        return f"Ошибка при извлечении текста из файла: {str(e)}"
    
    finally:
        # Удаляем временный файл
        default_storage.delete(path)


class Document_mainCreateView(LoginRequiredMixin, CreateView):
    model = Document_main
    form_class = Document_mainForm
    template_name = 'main/main_form.html'
    success_url = reverse_lazy('documents:main_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        
        # Проверяем метод ввода стандарта
        standard_input_method = form.cleaned_data.get('standard_input_method')
        standard_file = form.cleaned_data.get('standard_file')
        
        # Если выбран метод загрузки файла, извлекаем текст из файла
        if standard_input_method == 'file' and standard_file:
            extracted_text = extract_text_from_file(standard_file)
            form.instance.standart = extracted_text
        
        return super().form_valid(form)
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание документа'
        return context


class DocumentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Document_main
    form_class = Document_mainForm
    template_name = 'main/main_form.html'
    success_url = reverse_lazy('documents:main_list')

    def test_func(self):
        return self.get_object().owner == self.request.user
        
    def get_initial(self):
        """
        Устанавливает начальные значения для формы при редактировании документа.
        """
        initial = super().get_initial()
        # При редактировании документа по умолчанию выбираем метод ввода текста
        initial['standard_input_method'] = 'text'
        return initial
        
    def form_valid(self, form):
        form.instance.owner = self.request.user
        
        # Проверяем метод ввода стандарта
        standard_input_method = form.cleaned_data.get('standard_input_method')
        standard_file = form.cleaned_data.get('standard_file')
        
        # Если выбран метод загрузки файла, извлекаем текст из файла
        if standard_input_method == 'file' and standard_file:
            extracted_text = extract_text_from_file(standard_file)
            form.instance.standart = extracted_text
        
        return super().form_valid(form)


class DocumentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Document_main
    template_name = 'main/main_confirm_delete.html'
    success_url = reverse_lazy('documents:main_list')

    def test_func(self):
        return self.get_object().owner == self.request.user


@login_required
def update_references(request, pk):
    """
    Обновляет список DOI источников для документа.
    
    Args:
        request: HTTP запрос
        pk (int): ID документа
        
    Returns:
        redirect: Перенаправление на страницу деталей документа
    """
    document = get_object_or_404(Document_main, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        references_doi = request.POST.get('references_doi', '').strip()
        document.references_doi = references_doi
        document.save()
        
        messages.success(request, "Список источников успешно обновлен.")
    
    return redirect(reverse('documents:main_detail', kwargs={'pk': pk}))
