# documents/views/gost.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, View, UpdateView # Добавлены View и UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin # Используем миксины для CBV
from django.contrib.auth.decorators import login_required # Оставим для примера экспорта (если он будет)
from django.http import HttpResponse # Для экспорта
from docx import Document as DocxDocument
from docx.shared import Pt, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from io import BytesIO
import re

# Импортируем модели и формы (пути могут отличаться в зависимости от структуры вашего проекта)
# Убедитесь, что эти импорты верны для вашей структуры:
# from .models.gost import Document, Abstract, Performer, Term, Abbreviation, Reference, Appendix # Пример, если модели в models/gost.py
# from .forms.gost import DocumentForm, TitlePageForm, AbstractForm, PerformerFormSet, TermFormSet, AbbreviationFormSet, ReferenceFormSet, AppendixFormSet # Пример, если формы в forms/gost.py
# Если все в одном файле models.py и forms.py:
from documents.models.gost import Document,Abstract
from documents.forms.gost import DocumentForm,AppendixFormSet,TermFormSet,AbbreviationFormSet,PerformerFormSet,ReferenceFormSet,TitlePageForm,AbstractForm


# --- Классовые представления (CBV) ---

class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'documents/document_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user).order_by('-created_at')


class DocumentDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Document
    template_name = 'documents/document_detail.html'
    context_object_name = 'document'

    def test_func(self):
        return self.get_object().user == self.request.user


class DocumentCreateView(LoginRequiredMixin, View):
    template_name = 'documents/document_form.html'

    def get(self, request, *args, **kwargs):
        context = {
            'form': DocumentForm(),
            'title_form': TitlePageForm(),
            'abstract_form': AbstractForm(),
            'performer_formset': PerformerFormSet(prefix='performers'),
            'term_formset': TermFormSet(prefix='terms'),
            'abbrev_formset': AbbreviationFormSet(prefix='abbrevs'),
            'reference_formset': ReferenceFormSet(prefix='refs'),
            'appendix_formset': AppendixFormSet(prefix='apps'),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        doc_form = DocumentForm(request.POST)
        title_form = TitlePageForm(request.POST)
        abstract_form = AbstractForm(request.POST)
        performer_formset = PerformerFormSet(request.POST, request.FILES, prefix='performers')
        term_formset = TermFormSet(request.POST, request.FILES, prefix='terms')
        abbrev_formset = AbbreviationFormSet(request.POST, request.FILES, prefix='abbrevs')
        reference_formset = ReferenceFormSet(request.POST, request.FILES, prefix='refs')
        appendix_formset = AppendixFormSet(request.POST, request.FILES, prefix='apps')

        if all([
            doc_form.is_valid(), title_form.is_valid(), abstract_form.is_valid(),
            performer_formset.is_valid(), term_formset.is_valid(), abbrev_formset.is_valid(),
            reference_formset.is_valid(), appendix_formset.is_valid(),
        ]):
            document = doc_form.save(commit=False)
            document.user = request.user
            document.save()

            title = title_form.save(commit=False)
            title.document = document
            title.save()

            abstract = abstract_form.save(commit=False)
            abstract.document = document
            abstract.save()

            for fs in [performer_formset, term_formset, abbrev_formset, reference_formset, appendix_formset]:
                instances = fs.save(commit=False)
                for inst in instances:
                    inst.document = document
                    inst.save()
                fs.save_m2m()

            return redirect('documents:gost_detail', pk=document.pk)

        context = {
            'form': doc_form,
            'title_form': title_form,
            'abstract_form': abstract_form,
            'performer_formset': performer_formset,
            'term_formset': term_formset,
            'abbrev_formset': abbrev_formset,
            'reference_formset': reference_formset,
            'appendix_formset': appendix_formset,
            'error_message': 'Пожалуйста, исправьте ошибки в форме.'
        }
        return render(request, self.template_name, context)


class DocumentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = 'documents/document_form.html'
    pk_url_kwarg = 'pk'
    context_object_name = 'document'

    def test_func(self):
        return self.get_object().user == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.object
        if self.request.POST:
            context['title_form'] = TitlePageForm(self.request.POST, instance=getattr(obj, 'title_page', None))
            context['abstract_form'] = AbstractForm(self.request.POST, instance=getattr(obj, 'abstract', None))
            context['performer_formset'] = PerformerFormSet(self.request.POST, self.request.FILES, prefix='performers', queryset=obj.performers.all())
            context['term_formset'] = TermFormSet(self.request.POST, self.request.FILES, prefix='terms', queryset=obj.terms.all())
            context['abbrev_formset'] = AbbreviationFormSet(self.request.POST, self.request.FILES, prefix='abbrevs', queryset=obj.abbreviations.all())
            context['reference_formset'] = ReferenceFormSet(self.request.POST, self.request.FILES, prefix='refs', queryset=obj.references.all())
            context['appendix_formset'] = AppendixFormSet(self.request.POST, self.request.FILES, prefix='apps', queryset=obj.appendices.all())
        else:
            context['title_form'] = TitlePageForm(instance=getattr(obj, 'title_page', None))
            context['abstract_form'] = AbstractForm(instance=getattr(obj, 'abstract', None))
            context['performer_formset'] = PerformerFormSet(prefix='performers', queryset=obj.performers.all())
            context['term_formset'] = TermFormSet(prefix='terms', queryset=obj.terms.all())
            context['abbrev_formset'] = AbbreviationFormSet(prefix='abbrevs', queryset=obj.abbreviations.all())
            context['reference_formset'] = ReferenceFormSet(prefix='refs', queryset=obj.references.all())
            context['appendix_formset'] = AppendixFormSet(prefix='apps', queryset=obj.appendices.all())
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        if all([
            form.is_valid(), context['title_form'].is_valid(), context['abstract_form'].is_valid(),
            context['performer_formset'].is_valid(), context['term_formset'].is_valid(),
            context['abbrev_formset'].is_valid(), context['reference_formset'].is_valid(),
            context['appendix_formset'].is_valid(),
        ]):
            self.object = form.save()
            title = context['title_form'].save(commit=False)
            title.document = self.object
            title.save()
            abstract = context['abstract_form'].save(commit=False)
            abstract.document = self.object
            abstract.save()
            for fs in [context['performer_formset'], context['term_formset'], context['abbrev_formset'], context['reference_formset'], context['appendix_formset']]:
                instances = fs.save(commit=False)
                for inst in instances:
                    inst.document = self.object
                    inst.save()
                fs.save_m2m()
            return redirect('documents:gost_detail', pk=self.object.pk)
        return self.form_invalid(form)

    def get_success_url(self):
        """Возвращает URL для перенаправления после успешного обновления."""
        return reverse_lazy('document_detail', kwargs={'pk': self.object.pk})

# --- Функции для экспорта ---
@login_required
def document_export_docx(request, pk):
    """
    Экспортирует документ в формат DOCX
    """
    try:
        # Получаем документ из базы данных
        document = get_object_or_404(Document, pk=pk, user=request.user)
        
        # Создаем docx документ
        docx = DocxDocument()
        
        # Настройка стилей документа
        styles = docx.styles
        
        # Стиль для заголовков
        style_heading1 = styles.add_style('CustomHeading1', WD_STYLE_TYPE.PARAGRAPH)
        style_heading1.base_style = styles['Heading 1']
        font = style_heading1.font
        font.name = 'Times New Roman'
        font.size = Pt(16)
        font.bold = True
        
        # Стиль для текста
        style_normal = styles['Normal']
        font = style_normal.font
        font.name = 'Times New Roman'
        font.size = Pt(14)
        
        # Добавляем титульный лист
        add_title_page(docx, document)

        # Добавляем реферат
        add_abstract(docx, document)
        
        # Добавляем основные разделы
        add_sections(docx, document)
        
        # Сохраняем файл
        buffer = BytesIO()
        docx.save(buffer)
        buffer.seek(0)
        
        # Отправляем файл пользователю
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        file_name = f"{document.title.replace(' ', '_')}.docx"
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        
        return response
        
    except Exception as e:
        print(f"Ошибка при экспорте документа: {str(e)}")
        return HttpResponse(f"Ошибка при экспорте документа: {str(e)}", status=500)

def add_title_page(docx, document):
    """
    Добавляет титульный лист в docx документ
    """
    # Получаем объект титульного листа
    try:
        title_page = document.title_page
    except:
        title_page = None
    
    # Добавляем информацию титульного листа
    p = docx.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if title_page and title_page.department:
        p.add_run(title_page.department.upper()).bold = True
    
    # Добавляем отступ
    for _ in range(3):
        docx.add_paragraph()
    
    # Заголовок документа
    p = docx.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(document.title.upper()).bold = True
    
    # Тип отчета
    if document.report_type:
        p = docx.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        report_type_display = dict(document._meta.get_field('report_type').choices)[document.report_type]
        p.add_run(f"{report_type_display.upper()} ОТЧЁТ").bold = True
    
    # Добавляем информацию о руководителе и исполнителях в нижней части титульного листа
    for _ in range(5):
        docx.add_paragraph()
    
    # Информация о руководителе
    if title_page:
        table = docx.add_table(rows=2, cols=2)
        table.autofit = True
        
        # Левая сторона - руководитель
        if title_page.head_position or title_page.head_full_name:
            cell = table.cell(0, 0)
            cell.text = title_page.head_position or "Руководитель проекта"
            
            cell = table.cell(1, 0)
            cell.text = title_page.head_full_name or ""
    
    # Добавляем город и год в нижней части страницы
    for _ in range(3):
        docx.add_paragraph()
    
    p = docx.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"{document.year}").bold = True
    
    # Добавляем разрыв страницы
    docx.add_page_break()

def add_abstract(docx, document):
    """
    Добавляет реферат в docx документ
    """
    # Заголовок
    p = docx.add_paragraph("РЕФЕРАТ", style='CustomHeading1')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Получаем объект реферата
    try:
        abstract = document.abstract
        
        # Добавляем содержимое реферата
        if abstract and abstract.content:
            # Очищаем HTML теги
            clean_text = re.sub(r'<.*?>', '', abstract.content)
            p = docx.add_paragraph(clean_text)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    except:
        # Если реферат не найден, добавляем пустой параграф
        docx.add_paragraph()
    
    # Разрыв страницы
    docx.add_page_break()

def add_sections(docx, document):
    """
    Добавляет основные разделы документа
    """
    # Содержание
    p = docx.add_paragraph("СОДЕРЖАНИЕ", style='CustomHeading1')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # TODO: Автоматически генерировать содержание
    docx.add_paragraph()
    docx.add_page_break()
    
    # Введение
    p = docx.add_paragraph("ВВЕДЕНИЕ", style='CustomHeading1')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    if document.introduction:
        # Очищаем HTML теги
        clean_text = re.sub(r'<.*?>', '', document.introduction)
        p = docx.add_paragraph(clean_text)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    else:
        docx.add_paragraph()
    
    docx.add_page_break()
    
    # Основная часть
    p = docx.add_paragraph("ОСНОВНАЯ ЧАСТЬ", style='CustomHeading1')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    if document.main_part:
        # Очищаем HTML теги
        clean_text = re.sub(r'<.*?>', '', document.main_part)
        p = docx.add_paragraph(clean_text)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    else:
        docx.add_paragraph()
    
    docx.add_page_break()
    
    # Заключение
    p = docx.add_paragraph("ЗАКЛЮЧЕНИЕ", style='CustomHeading1')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    if document.conclusion:
        # Очищаем HTML теги
        clean_text = re.sub(r'<.*?>', '', document.conclusion)
        p = docx.add_paragraph(clean_text)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    else:
        docx.add_paragraph()
    
    docx.add_page_break()
    
    # Список использованных источников
    p = docx.add_paragraph("СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ", style='CustomHeading1')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Добавляем список источников
    try:
        references = document.references.all().order_by('order')
        if references.exists():
            for i, ref in enumerate(references, 1):
                p = docx.add_paragraph(f"{i}. {ref.citation}")
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        else:
            docx.add_paragraph()
    except:
        docx.add_paragraph()
    
    # Добавляем приложения, если они есть
    try:
        appendices = document.appendices.all().order_by('order')
        if appendices.exists():
            docx.add_page_break()
            
            for appendix in appendices:
                p = docx.add_paragraph(f"ПРИЛОЖЕНИЕ {appendix.label}", style='CustomHeading1')
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                if appendix.title:
                    p = docx.add_paragraph(appendix.title)
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.style = 'CustomHeading1'
                
                if appendix.content:
                    # Очищаем HTML теги
                    clean_text = re.sub(r'<.*?>', '', appendix.content)
                    p = docx.add_paragraph(clean_text)
                    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                
                docx.add_page_break()
    except:
        pass