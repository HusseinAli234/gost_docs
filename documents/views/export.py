from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from io import BytesIO
import re
import requests
import tempfile
import os
import base64
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from django.conf import settings

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT

from documents.models.gost import Document as GostDocument
from documents.models.sto import Document_sto


def clean_html(html_content):
    """Удаляет HTML-теги из текста (устаревшая функция)"""
    if not html_content:
        return ""
    return re.sub(r'<.*?>', '', html_content)


def html_to_docx(html_content, docx_document, style='Normal'):
    """
    Преобразует HTML в форматированный DOCX с поддержкой изображений и таблиц
    
    Args:
        html_content (str): HTML-контент для преобразования
        docx_document (Document): Документ python-docx, куда будет добавлен контент
        style (str): Имя стиля для основного текста
    """
    if not html_content:
        return
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Функция для обработки текста с форматированием
    def process_text_with_formatting(element, paragraph):
        if element.name == 'strong' or element.name == 'b':
            run = paragraph.add_run(element.get_text())
            run.bold = True
        elif element.name == 'em' or element.name == 'i':
            run = paragraph.add_run(element.get_text())
            run.italic = True
        elif element.name == 'u':
            run = paragraph.add_run(element.get_text())
            run.underline = True
        elif element.name == 'a':
            url = element.get('href', '')
            text = element.get_text() or url
            run = paragraph.add_run(text)
            run.underline = True
            run.font.color.rgb = RGBColor(0, 0, 255)  # Синий цвет для ссылок
        else:
            # Рекурсивная обработка вложенных элементов
            for child in element.children:
                if isinstance(child, str):
                    paragraph.add_run(child)
                else:
                    process_text_with_formatting(child, paragraph)
    
    # Обрабатываем каждый элемент верхнего уровня
    for element in soup.children:
        if isinstance(element, str) and element.strip():
            # Простой текст
            p = docx_document.add_paragraph(style=style)
            p.add_run(element.strip())
        # Проверяем, что элемент — это тег, а не просто строка или комментарий
        elif element.name:
            # Параграфы
            if element.name == 'p':
                p = docx_document.add_paragraph(style=style)
                for child in element.children:
                    if isinstance(child, str):
                        p.add_run(child)
                    else:
                        process_text_with_formatting(child, p)
            
            # Заголовки
            elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(element.name[1])
                style_name = f"Heading {level}"
                p = docx_document.add_paragraph(style=style_name)
                p.add_run(element.get_text())
            
            # Списки
            elif element.name == 'ul' or element.name == 'ol':
                for li in element.find_all('li', recursive=False):
                    p = docx_document.add_paragraph(style=style)
                    if element.name == 'ul':
                        p.style = 'List Bullet'
                    else:
                        p.style = 'List Number'
                    
                    for child in li.children:
                        if isinstance(child, str):
                            p.add_run(child)
                        else:
                            process_text_with_formatting(child, p)
            
            # Изображения
            elif element.name == 'img':
                img_src = element.get('src', '')
                print(f"Обработка изображения со src: {img_src[:50]}{'...' if len(img_src) > 50 else ''}")
                
                if img_src:
                    try:
                        # Если изображение в формате data URL (Base64)
                        if img_src.startswith('data:image/'):
                            print(f"Обработка data URL изображения")
                            try:
                                # Извлекаем данные после префикса "data:image/XXX;base64,"
                                header, encoded = img_src.split(",", 1)
                                
                                # Декодируем Base64 напрямую в байты
                                img_data = base64.b64decode(encoded)
                                
                                # Создаем поток байтов и добавляем изображение напрямую
                                image_stream = BytesIO(img_data)
                                docx_document.add_picture(image_stream, width=Inches(5))
                                print(f"Изображение data URL успешно добавлено в документ")
                            except Exception as e:
                                print(f"Ошибка при обработке data URL: {str(e)}")
                            
                        # Если изображение из интернета (HTTP/HTTPS) или LaTeX сервиса
                        elif img_src.startswith('http') or 'shkolkovo.online/api/latex' in img_src or 'latex-service' in img_src:
                            url_type = "LaTeX" if ('shkolkovo.online/api/latex' in img_src or 'latex-service' in img_src) else "HTTP"
                            print(f"Загрузка {url_type} изображения по URL: {img_src[:30]}...")
                            
                            response = requests.get(img_src, stream=True)
                            if response.status_code == 200:
                                # Создаем поток байтов напрямую из ответа
                                image_stream = BytesIO(response.content)
                                
                                # Определяем размеры изображения из атрибутов
                                width_attr = element.get('width')
                                if width_attr and width_attr.isdigit():
                                    width_inches = float(width_attr) / 96
                                    docx_document.add_picture(image_stream, width=Inches(min(width_inches, 6)))
                                else:
                                    docx_document.add_picture(image_stream, width=Inches(5))
                                    
                                print(f"Изображение {url_type} успешно добавлено в документ")
                            else:
                                print(f"Ошибка при загрузке изображения: HTTP {response.status_code}")
                                p = docx_document.add_paragraph(style=style)
                                p.add_run(f"[Изображение не найдено: {img_src[:30]}...]")
                                
                        # Если изображение локальное из папки media
                        elif img_src.startswith('/media/'):
                            print(f"Обработка загруженного изображения из media: {img_src}")
                            # Получаем абсолютный путь к файлу
                            media_root = settings.MEDIA_ROOT
                            relative_path = img_src[7:]  # Убираем '/media/' из начала пути
                            img_path = os.path.join(media_root, relative_path)
                            
                            print(f"Путь к файлу изображения: {img_path}")
                            if os.path.exists(img_path):
                                # Читаем файл напрямую в поток байтов
                                with open(img_path, 'rb') as f:
                                    image_bytes = f.read()
                                
                                image_stream = BytesIO(image_bytes)
                                
                                # Определяем размер изображения на основе атрибутов width и height
                                width_attr = element.get('width')
                                if width_attr and width_attr.isdigit():
                                    # Преобразуем пиксели в дюймы (приблизительно)
                                    width_inches = float(width_attr) / 96
                                    docx_document.add_picture(image_stream, width=Inches(min(width_inches, 6)))
                                else:
                                    # Используем стандартную ширину 5 дюймов
                                    docx_document.add_picture(image_stream, width=Inches(5))
                                    
                                print(f"Загруженное изображение успешно добавлено в документ")
                            else:
                                print(f"Файл не найден по пути: {img_path}")
                                p = docx_document.add_paragraph(style=style)
                                p.add_run(f"[Изображение не найдено: {img_src}]")
                                
                        # Если изображение локальное, из других источников
                        else:
                            print(f"Обработка локального изображения: {img_src[:50]}...")
                            # Пробуем обработать относительный путь
                            img_path = os.path.join(settings.MEDIA_ROOT, img_src)
                            
                            print(f"Путь к файлу: {img_path}")
                            if os.path.exists(img_path):
                                # Читаем файл напрямую в поток байтов
                                with open(img_path, 'rb') as f:
                                    image_bytes = f.read()
                                
                                image_stream = BytesIO(image_bytes)
                                docx_document.add_picture(image_stream, width=Inches(5))
                                print(f"Локальное изображение успешно добавлено в документ")
                            else:
                                # Если не удалось найти изображение как локальный файл, 
                                # попробуем обработать как URL напрямую
                                try:
                                    print(f"Попытка загрузить изображение напрямую: {img_src}")
                                    response = requests.get(img_src, allow_redirects=True)
                                    if response.status_code == 200:
                                        # Создаем поток байтов напрямую из ответа
                                        image_stream = BytesIO(response.content)
                                        docx_document.add_picture(image_stream, width=Inches(5))
                                        print(f"Изображение успешно загружено и добавлено в документ")
                                    else:
                                        raise Exception(f"HTTP {response.status_code}")
                                except Exception as e:
                                    print(f"Ошибка при прямой загрузке изображения: {str(e)}")
                                    p = docx_document.add_paragraph(style=style)
                                    p.add_run(f"[Изображение не найдено: {img_src[:30]}...]")
                    except Exception as e:
                        print(f"Ошибка при добавлении изображения: {str(e)}")
                        p = docx_document.add_paragraph(style=style)
                        p.add_run(f"[Ошибка обработки изображения: {img_src[:30]}...]")
                else:
                    print("Элемент img не содержит атрибута src")
            
            # Таблицы
            elif element.name == 'table':
                try:
                    rows = element.find_all('tr')
                    if rows:
                        # Определяем количество столбцов по первой строке
                        cols = max(len(row.find_all(['td', 'th'])) for row in rows)
                        if cols > 0:
                            # Создаем таблицу в документе
                            table = docx_document.add_table(rows=len(rows), cols=cols)
                            table.style = 'Table Grid'
                            table.alignment = WD_TABLE_ALIGNMENT.CENTER
                            
                            # Заполняем таблицу
                            for i, row in enumerate(rows):
                                cells = row.find_all(['td', 'th'])
                                for j, cell in enumerate(cells):
                                    if j < cols:  # Проверяем, что не выходим за границы
                                        docx_cell = table.cell(i, j)
                                        # Обрабатываем содержимое ячейки с учетом форматирования
                                        docx_cell.text = ""  # Очищаем ячейку
                                        p = docx_cell.paragraphs[0]
                                        
                                        for cell_content in cell.contents:
                                            if isinstance(cell_content, str):
                                                p.add_run(cell_content)
                                            else:
                                                # Обрабатываем форматирование и вложенные элементы
                                                process_text_with_formatting(cell_content, p)
                                        
                                        # Если это заголовок таблицы
                                        if cell.name == 'th':
                                            for paragraph in docx_cell.paragraphs:
                                                for run in paragraph.runs:
                                                    run.bold = True
                except Exception as e:
                    print(f"Ошибка при добавлении таблицы: {str(e)}")
                    p = docx_document.add_paragraph(style=style)
                    p.add_run("[Ошибка при добавлении таблицы]")
            
            # Обработка блоков кода и цитат
            elif element.name == 'pre' or element.name == 'code':
                p = docx_document.add_paragraph(style=style)
                p.paragraph_format.left_indent = Inches(0.5)
                p.paragraph_format.right_indent = Inches(0.5)
                code_text = element.get_text(strip=True)
                run = p.add_run(code_text)
                run.font.name = 'Courier New'  # Моноширинный шрифт для кода
            
            elif element.name == 'blockquote':
                p = docx_document.add_paragraph(style=style)
                p.paragraph_format.left_indent = Inches(0.5)
                p.add_run(element.get_text(strip=True))
                
            # Горизонтальные линии
            elif element.name == 'hr':
                docx_document.add_paragraph('_' * 50, style=style)


@login_required
def gost_export_docx(request, pk):
    """
    Экспортирует документ ГОСТ 7.32-2017 в формат DOCX
    """
    try:
        document = get_object_or_404(GostDocument, pk=pk, user=request.user)
        
        # Создаем docx документ
        docx = Document()
        
        # Настройка общих стилей документа по ГОСТ 7.32-2017
        set_gost_styles(docx)
        
        # Формирование документа
        add_gost_title_page(docx, document)
        add_gost_abstract(docx, document)
        add_gost_toc(docx)
        add_gost_sections(docx, document)
        add_gost_references(docx, document)
        add_gost_appendices(docx, document)
        
        # Сохранение и отправка документа
        buffer = BytesIO()
        docx.save(buffer)
        buffer.seek(0)
        
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        file_name = f"ГОСТ_{document.title.replace(' ', '_')}.docx"
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        
        return response
    except Exception as e:
        return HttpResponse(f"Ошибка при экспорте документа: {str(e)}", status=500)


@login_required
def sto_export_docx(request, pk):
    """
    Экспортирует документ СТО СФУ 4.2-07-2008 в формат DOCX
    """
    try:
        document = get_object_or_404(Document_sto, pk=pk, owner=request.user)
        
        # Создаем docx документ
        docx = Document()
        
        # Настройка общих стилей документа по СТО СФУ
        set_sto_styles(docx)
        
        # Формирование документа
        add_sto_title_page(docx, document)
        # Добавляем реферат до оглавления
        try:
            abstract = document.abstract
            print(abstract.text)
            if abstract:
                p = docx.add_paragraph("РЕФЕРАТ", style='StoHeading1')
                # Метаданные реферата
                meta_table = docx.add_table(rows=6, cols=2)
                meta_table.style = 'Table Grid'
                
                # Первый ряд
                cell = meta_table.cell(0, 0)
                cell.text = "Количество страниц:"
                meta_table.cell(0, 1).text = str(abstract.page_count)
                
                # Второй ряд
                cell = meta_table.cell(1, 0)
                cell.text = "Количество иллюстраций:"
                meta_table.cell(1, 1).text = str(abstract.illustrations_count)
                
                # Третий ряд
                cell = meta_table.cell(2, 0)
                cell.text = "Количество таблиц:"
                meta_table.cell(2, 1).text = str(abstract.tables_count)
                
                # Четвёртый ряд
                cell = meta_table.cell(3, 0)
                cell.text = "Количество формул:"
                meta_table.cell(3, 1).text = str(abstract.formulas_count)
                
                # Пятый ряд
                cell = meta_table.cell(4, 0)
                cell.text = "Количество приложений:"
                meta_table.cell(4, 1).text = str(abstract.appendices_count)
                
                # Шестой ряд
                cell = meta_table.cell(5, 0)
                cell.text = "Количество источников:"
                meta_table.cell(5, 1).text = str(abstract.references_count)

                # Делаем ширину первой колонки больше
                for row in meta_table.rows:
                    row.cells[0].width = Inches(3)
                    row.cells[1].width = Inches(1)
                
                # Добавляем пробел после таблицы
                docx.add_paragraph()
                
                # Добавляем ключевые слова (при наличии)
                if abstract.keywords:
                    p = docx.add_paragraph()
                    p.style = 'Normal'
                    run = p.add_run("КЛЮЧЕВЫЕ СЛОВА: ")
                    run.bold = True
                    # Обрабатываем ключевые слова как HTML в документе, а не в параграфе
                    html_to_docx(abstract.keywords, docx)
                    docx.add_paragraph()

                # Добавляем текст реферата
                if abstract.text:
                    # Заголовок "Текст реферата" не нужен, т.к. весь документ - это реферат
                    html_to_docx(abstract.text, docx)
                
                docx.add_page_break()
        except Exception as e:
            print(f"Ошибка при добавлении реферата СТО: {str(e)}")
        
        add_sto_toc(docx)
        add_sto_sections(docx, document)
        add_sto_bibliography(docx, document)
        add_sto_appendices(docx, document)
        
        # Сохранение и отправка документа
        buffer = BytesIO()
        docx.save(buffer)
        buffer.seek(0)
        
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        file_name = f"СТО_{document.title.replace(' ', '_')}.docx"
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        
        return response
    except Exception as e:
        return HttpResponse(f"Ошибка при экспорте документа: {str(e)}", status=500)


# --- Функции настройки стилей ---

def set_gost_styles(docx):
    """Устанавливает стили документа по ГОСТ 7.32-2017"""
    # Устанавливаем размеры полей страницы
    sections = docx.sections
    for section in sections:
        section.left_margin = Cm(3.0)   # 30 мм
        section.right_margin = Cm(1.5)  # 15 мм
        section.top_margin = Cm(2.0)    # 20 мм
        section.bottom_margin = Cm(2.0) # 20 мм
    
    # Основной стиль текста
    style_normal = docx.styles['Normal']
    font = style_normal.font
    font.name = 'Times New Roman'
    font.size = Pt(14)
    font.color.rgb = RGBColor(0, 0, 0)  # Черный цвет
    paragraph_format = style_normal.paragraph_format
    paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE  # 1.5 интервал
    paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY  # По ширине
    paragraph_format.first_line_indent = Pt(15)  # 1.25 см отступ (15pt ≈ 1.25 см)
    
    # Стиль заголовка 1
    heading1_style = docx.styles.add_style('GostHeading1', WD_STYLE_TYPE.PARAGRAPH)
    heading1_style.base_style = docx.styles['Heading 1']
    font = heading1_style.font
    font.name = 'Times New Roman'
    font.size = Pt(16)
    font.bold = True
    font.color.rgb = RGBColor(0, 0, 0)
    paragraph_format = heading1_style.paragraph_format
    paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph_format.space_before = Pt(12)
    paragraph_format.space_after = Pt(12)
    
    # Стиль заголовка 2
    heading2_style = docx.styles.add_style('GostHeading2', WD_STYLE_TYPE.PARAGRAPH)
    heading2_style.base_style = docx.styles['Heading 2']
    font = heading2_style.font
    font.name = 'Times New Roman'
    font.size = Pt(14)
    font.bold = True
    font.color.rgb = RGBColor(0, 0, 0)
    paragraph_format = heading2_style.paragraph_format
    paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph_format.space_before = Pt(12)
    paragraph_format.space_after = Pt(6)
    paragraph_format.first_line_indent = Pt(15)


def set_sto_styles(docx):
    """Устанавливает стили документа по СТО СФУ 4.2-07-2008"""
    # Устанавливаем размеры полей страницы
    sections = docx.sections
    for section in sections:
        section.left_margin = Cm(2.5)   # 25 мм
        section.right_margin = Cm(1.0)  # 10 мм
        section.top_margin = Cm(2.0)    # 20 мм
        section.bottom_margin = Cm(2.0) # 20 мм
    
    # Основной стиль текста
    style_normal = docx.styles['Normal']
    font = style_normal.font
    font.name = 'Times New Roman'
    font.size = Pt(14)
    font.color.rgb = RGBColor(0, 0, 0)  # Черный цвет
    paragraph_format = style_normal.paragraph_format
    paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE  # 1.5 интервал
    paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY  # По ширине
    paragraph_format.first_line_indent = Pt(15)  # 1.25 см отступ
    
    # Стиль заголовка 1
    heading1_style = docx.styles.add_style('StoHeading1', WD_STYLE_TYPE.PARAGRAPH)
    heading1_style.base_style = docx.styles['Heading 1']
    font = heading1_style.font
    font.name = 'Times New Roman'
    font.size = Pt(16)
    font.bold = True
    font.color.rgb = RGBColor(0, 0, 0)
    paragraph_format = heading1_style.paragraph_format
    paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph_format.space_before = Pt(12)
    paragraph_format.space_after = Pt(12)


# --- Функции формирования ГОСТ документа ---

def add_gost_title_page(docx, document):
    """Добавляет титульный лист ГОСТ документа"""
    try:
        title_page = document.title_page
    except:
        title_page = None
    
    # Добавляем верхний колонтитул (если есть)
    p = docx.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if title_page and title_page.department:
        p.add_run(title_page.department.upper()).bold = True
    
    # Добавляем отступ
    for _ in range(5):
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
    
    # Добавляем информацию о руководителе и исполнителях
    for _ in range(10):
        docx.add_paragraph()
    
    # Информация об исполнителях в таблице
    if title_page:
        table = docx.add_table(rows=1, cols=2)
        table.autofit = True
        
        # Левая колонка - руководитель
        if title_page.head_position or title_page.head_full_name:
            cell = table.cell(0, 0)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.add_run(f"{title_page.head_position or 'Руководитель'}").bold = True
            p.add_run(f"\n{title_page.head_full_name or ''}")
    
    # Город и год в нижней части страницы
    for _ in range(5):
        docx.add_paragraph()
    
    p = docx.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"{document.year}").bold = True
    
    # Добавляем разрыв страницы
    docx.add_page_break()


def add_gost_abstract(docx, document):
    """Добавляет реферат ГОСТ документа"""
    p = docx.add_paragraph("РЕФЕРАТ", style='GostHeading1')
    
    try:
        abstract = document.abstract
        if abstract and abstract.content:
            html_to_docx(abstract.content, docx)
    except:
        docx.add_paragraph()
    
    docx.add_page_break()


def add_gost_toc(docx):
    """Добавляет оглавление ГОСТ документа"""
    p = docx.add_paragraph("СОДЕРЖАНИЕ", style='GostHeading1')
    
    # Добавляем заглушку для оглавления
    # В python-docx нет прямой поддержки автоматического оглавления
    # Для продакшена можно использовать внешние библиотеки или макросы Word
    docx.add_paragraph("(Содержание формируется автоматически в MS Word)")
    
    docx.add_page_break()


def add_gost_sections(docx, document):
    """Добавляет основные разделы ГОСТ документа"""
    # Введение
    p = docx.add_paragraph("ВВЕДЕНИЕ", style='GostHeading1')
    
    if document.introduction:
        html_to_docx(document.introduction, docx)
    
    docx.add_page_break()
    
    # Термины и определения
    if document.terms.exists():
        p = docx.add_paragraph("ТЕРМИНЫ И ОПРЕДЕЛЕНИЯ", style='GostHeading1')
        
        for term in document.terms.all().order_by('order'):
            p = docx.add_paragraph()
            p.style = 'Normal'
            r = p.add_run(f"{term.term} – ")
            r.bold = True
            p.add_run(term.definition)
        
        docx.add_page_break()
    
    # Сокращения
    if document.abbreviations.exists():
        p = docx.add_paragraph("СОКРАЩЕНИЯ", style='GostHeading1')
        
        for abbr in document.abbreviations.all().order_by('order'):
            p = docx.add_paragraph()
            p.style = 'Normal'
            r = p.add_run(f"{abbr.abbreviation} – ")
            r.bold = True
            p.add_run(abbr.meaning)
        
        docx.add_page_break()
    
    # Основная часть
    p = docx.add_paragraph("ОСНОВНАЯ ЧАСТЬ", style='GostHeading1')
    
    if document.main_part:
        html_to_docx(document.main_part, docx)
    
    docx.add_page_break()
    
    # Заключение
    p = docx.add_paragraph("ЗАКЛЮЧЕНИЕ", style='GostHeading1')
    
    if document.conclusion:
        html_to_docx(document.conclusion, docx)
    
    docx.add_page_break()


def add_gost_references(docx, document):
    """Добавляет список использованных источников ГОСТ документа"""
    p = docx.add_paragraph("СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ", style='GostHeading1')
    
    try:
        references = document.references.all().order_by('order')
        if references.exists():
            for i, ref in enumerate(references, 1):
                p = docx.add_paragraph(f"{i}. {ref.citation}")
                p.style = 'Normal'
                p.paragraph_format.first_line_indent = 0
                p.paragraph_format.left_indent = Pt(12)
                p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        else:
            docx.add_paragraph("Список литературы отсутствует.")
    except:
        docx.add_paragraph("Список литературы отсутствует.")
    
    docx.add_page_break()


def add_gost_appendices(docx, document):
    """Добавляет приложения ГОСТ документа"""
    try:
        appendices = document.appendices.all().order_by('order')
        if appendices.exists():
            for appendix in appendices:
                p = docx.add_paragraph(f"ПРИЛОЖЕНИЕ {appendix.label}", style='GostHeading1')
                
                if appendix.title:
                    p = docx.add_paragraph(appendix.title, style='GostHeading2')
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                if appendix.content:
                    html_to_docx(appendix.content, docx)
                
                docx.add_page_break()
    except Exception as e:
        print(f"Ошибка при добавлении приложений ГОСТ: {str(e)}")


# --- Функции формирования СТО документа ---

def add_sto_title_page(docx, document):
    """Добавляет титульный лист СТО документа"""
    # Верхний колонтитул
    p = docx.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("СИБИРСКИЙ ФЕДЕРАЛЬНЫЙ УНИВЕРСИТЕТ").bold = True
    
    # Добавляем отступ
    for _ in range(5):
        docx.add_paragraph()
    
    # Заголовок документа
    p = docx.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(document.title.upper()).bold = True
    
    # Тип документа
    p = docx.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Отчет для СТО СФУ 4.2").bold = True
    
    # Автор и руководитель
    for _ in range(10):
        docx.add_paragraph()
    
    # Таблица с автором и руководителем
    table = docx.add_table(rows=2, cols=2)
    table.autofit = True
    
    # Левая колонка - автор
    cell = table.cell(0, 0)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.add_run("Автор:").bold = True
    
    # Правая колонка - руководитель
    cell = table.cell(0, 1)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.add_run("Руководитель:").bold = True
    
    # Добавляем ФИО
    cell = table.cell(1, 0)
    p = cell.paragraphs[0]
    p.add_run(document.student_name)
    
    # Добавляем руководителя в правой колонке
    cell = table.cell(1, 1)
    p = cell.paragraphs[0]
    p.add_run(document.supervisor)
    
    # Город и год
    for _ in range(5):
        docx.add_paragraph()
    
    p = docx.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(f"Красноярск {document.year}").bold = True
    
    docx.add_page_break()


def add_sto_toc(docx):
    """Добавляет оглавление СТО документа"""
    p = docx.add_paragraph("СОДЕРЖАНИЕ", style='StoHeading1')
    
    # Заглушка для оглавления
    docx.add_paragraph("(Содержание формируется автоматически в MS Word)")
    
    docx.add_page_break()


def add_sto_sections(docx, document):
    """Добавляет разделы СТО документа"""
    # Добавляем разделы документа
    try:
        sections = document.sections.all().order_by('order')
        for section in sections:
            p = docx.add_paragraph(section.title.upper(), style='StoHeading1')
            
            if section.content:
                html_to_docx(section.content, docx)
            
            docx.add_page_break()
    except Exception as e:
        print(f"Ошибка при добавлении разделов СТО: {str(e)}")
        # Если разделов нет, добавляем стандартную структуру
        sections = ["ВВЕДЕНИЕ", "ОСНОВНАЯ ЧАСТЬ", "ЗАКЛЮЧЕНИЕ"]
        for section in sections:
            p = docx.add_paragraph(section, style='StoHeading1')
            docx.add_paragraph()
            docx.add_page_break()


def add_sto_bibliography(docx, document):
    """Добавляет библиографию СТО документа"""
    p = docx.add_paragraph("БИБЛИОГРАФИЧЕСКИЙ СПИСОК", style='StoHeading1')
    
    try:
        bibliography = document.biblio.all().order_by('order')
        if bibliography.exists():
            for i, ref in enumerate(bibliography, 1):
                p = docx.add_paragraph(f"{i}. {ref.entry_text}")
                p.style = 'Normal'
                p.paragraph_format.first_line_indent = 0
                p.paragraph_format.left_indent = Pt(12)
                p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        else:
            docx.add_paragraph("Список литературы отсутствует.")
    except:
        docx.add_paragraph("Список литературы отсутствует.")
    
    docx.add_page_break()


def add_sto_appendices(docx, document):
    """Добавляет приложения СТО документа"""
    try:
        appendices = document.appendices.all().order_by('label')
        if appendices.exists():
            for appendix in appendices:
                p = docx.add_paragraph(f"ПРИЛОЖЕНИЕ {appendix.label}", style='StoHeading1')
                
                if appendix.title:
                    p = docx.add_paragraph(appendix.title)
                    p.style = 'Normal'
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                # Для приложений СТО content - это файл, а не текст
                p = docx.add_paragraph(f"[Ссылка на файл: {appendix.content.url}]")
                p.style = 'Normal'
                
                docx.add_page_break()
    except Exception as e:
        print(f"Ошибка при добавлении приложений: {str(e)}") 