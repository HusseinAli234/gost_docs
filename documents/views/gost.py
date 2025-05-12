from django.shortcuts import render, redirect, get_object_or_404
from .models.gost import Document
from .forms import DocumentForm,AppendixFormSet,TermFormSet,AbbreviationFormSet,PerformerFormSet,ReferenceFormSet,TitlePageForm,AbstractForm
from django.contrib.auth.decorators import login_required
from docx import Document as DocxDocument 

@login_required
def document_list(request):
    documents = Document.objects.filter(user=request.user)
    return render(request, 'documents/document_list.html', {'documents': documents})




@login_required
def document_create(request):
    if request.method == 'POST':
        doc_form = DocumentForm(request.POST)
        title_form = TitlePageForm(request.POST)
        abstract_form = AbstractForm(request.POST)

        performer_formset = PerformerFormSet(request.POST, prefix='performers')
        term_formset = TermFormSet(request.POST, prefix='terms')
        abbrev_formset = AbbreviationFormSet(request.POST, prefix='abbrevs')
        reference_formset = ReferenceFormSet(request.POST, prefix='refs')
        appendix_formset = AppendixFormSet(request.POST, prefix='apps')

        if all([
            doc_form.is_valid(),
            title_form.is_valid(),
            abstract_form.is_valid(),
            performer_formset.is_valid(),
            term_formset.is_valid(),
            abbrev_formset.is_valid(),
            reference_formset.is_valid(),
            appendix_formset.is_valid(),
        ]):
            document = doc_form.save(commit=False)
            document.user = request.user
            document.save()

            title_page = title_form.save(commit=False)
            title_page.document = document
            title_page.save()

            abstract = abstract_form.save(commit=False)
            abstract.document = document
            abstract.save()

            for formset in [performer_formset, term_formset, abbrev_formset, reference_formset, appendix_formset]:
                instances = formset.save(commit=False)
                for obj in instances:
                    obj.document = document
                    obj.save()
                formset.save_m2m()

            return redirect('document_detail', pk=document.pk)

    else:
        doc_form = DocumentForm()
        title_form = TitlePageForm()
        abstract_form = AbstractForm()
        performer_formset = PerformerFormSet(prefix='performers')
        term_formset = TermFormSet(prefix='terms')
        abbrev_formset = AbbreviationFormSet(prefix='abbrevs')
        reference_formset = ReferenceFormSet(prefix='refs')
        appendix_formset = AppendixFormSet(prefix='apps')

    return render(request, 'documents/document_form.html', {
        'form': doc_form,
        'title_form': title_form,
        'abstract_form': abstract_form,
        'performer_formset': performer_formset,
        'term_formset': term_formset,
        'abbrev_formset': abbrev_formset,
        'reference_formset': reference_formset,
        'appendix_formset': appendix_formset,
    })

@login_required
def document_edit(request, pk):
    doc = get_object_or_404(Document, pk=pk, user=request.user)
    if request.method == 'POST':
        form = DocumentForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            return redirect('document_list')
    else:
        form = DocumentForm(instance=doc)
    return render(request, 'documents/document_form.html', {'form': form})


# @login_required
# def document_export_docx(request, pk):
#     # Убедитесь, что пользователь владеет документом
#     doc = get_object_or_404(Document, pk=pk, user=request.user)

#     # Создаем новый DOCX документ в памяти
#     document = DocxDocument()

#     # Добавляем заголовок
#     document.add_heading(doc.title, 0)

#     # Добавляем остальные поля.
#     # Важно: python-docx не умеет напрямую работать с HTML из CKEditor.
#     # Здесь мы просто добавляем текст из полей RichTextField.
#     # Для сохранения форматирования нужен более сложный подход (например, парсинг HTML
#     # или использование docxtpl с шаблоном, который умеет вставлять форматированный текст)
#     document.add_heading('Введение', level=1)
#     # strip_tags удалит все HTML-теги, оставив только текст.
#     # Для сохранения хотя бы абзацев, можно использовать что-то вроде BeautifulSoup или регулярных выражений
#     from django.utils.html import strip_tags
#     document.add_paragraph(strip_tags(doc.introduction))

#     document.add_heading('Цель', level=1)
#     document.add_paragraph(strip_tags(doc.goal))

#     document.add_heading('Задачи', level=1)
#     document.add_paragraph(strip_tags(doc.tasks))

#     document.add_heading('Основная часть', level=1)
#     document.add_paragraph(strip_tags(doc.main_part))

#     document.add_heading('Заключение', level=1)
#     document.add_paragraph(strip_tags(doc.conclusion))

#     # Можно добавить другие поля
#     document.add_paragraph(f'Год: {doc.year}')
#     document.add_paragraph(f'Кафедра: {doc.department}')
#     document.add_paragraph(f'Автор: {doc.author}')
#     document.add_paragraph(f'Тип документа: {doc.doc_type}')
#     document.add_paragraph(f'Шаблон: {doc.get_template_type_display()}')


#     # Сохраняем документ в буфер памяти
#     buffer = io.BytesIO()
#     document.save(buffer)
#     buffer.seek(0) # Перематываем в начало буфера

#     # Отправляем документ как HTTP ответ
#     response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
#     response['Content-Disposition'] = f'attachment; filename="{doc.title}.docx"'

#     return response
