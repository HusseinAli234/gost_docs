from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.text import slugify
from django.conf import settings
from django.contrib import messages

from io import BytesIO
import os
import logging
import tempfile
import base64
import re
# Удаляем BeautifulSoup, так как html2docx будет парсить HTML
# from bs4 import BeautifulSoup 
import requests
from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx2pdf import convert
# Импорт DocxTemplate для работы с шаблонами
from docxtpl import DocxTemplate

# Импортируем html2docx правильно
from htmldocx import HtmlToDocx

# Попытка импортировать pythoncom для Windows
try:
    import pythoncom
except ImportError:
    pythoncom = None # Устанавливаем в None, если импорт не удался (не Windows)

from documents.models.sto import Document_sto
from documents.models.main import Document_main

# Импортируем модуль AI для получения стилей форматирования
import ai

# Настройка логгера
logger = logging.getLogger(__name__)

# Отображение типов работ на названия шаблонов
WORK_TYPE_TEMPLATES = {
    'MAG_DIPLOMA': 'magitr_dissertation',
    'DIPLOMA': 'diplom_work',
    'BACHELOR': 'bachelor_work',
    'COURSE': 'kursovaya',
    'CALC_GRAPH': 'diplo_project',  # используем общий шаблон
    'PRACTICE': 'otchet_praktika',
    'LAB': 'laba_work',
    'REF': 'referat',
}

# Импорты для низкоуровневой работы с OXML элементами
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl

def clean_html(html_content):
    """Очищает HTML от тегов и возвращает только текст"""
    if not html_content:
        return ""
    return BeautifulSoup(html_content, 'html.parser').get_text()

def process_html_to_docx(html_content, docx_document):
    """
    Преобразует HTML-контент в DOCX и добавляет его в существующий документ.
    Использует библиотеку html2docx для конвертации.
    
    Args:
        html_content (str): HTML-контент для преобразования.
        docx_document (Document): Существующий объект python-docx, куда будет добавлен контент.
    """
    if not html_content:
        logger.info("HTML контент пуст, нечего добавлять.")
        return

    logger.info(f"Обработка HTML контента длиной {len(html_content)} символов с использованием html2docx")
    
    try:
        # Создаем парсер html2docx
        parser = HtmlToDocx()
        
        # Добавляем HTML в существующий документ
        parser.add_html_to_document(html_content, docx_document)
        
        logger.info("HTML успешно преобразован и добавлен в документ с помощью html2docx")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке HTML с помощью html2docx: {e}", exc_info=True)
        # В случае ошибки добавляем просто текст как запасной вариант
        try:
            from bs4 import BeautifulSoup # Локальный импорт для запасного варианта
            plain_text = BeautifulSoup(html_content, 'html.parser').get_text()
            docx_document.add_paragraph(f"[Ошибка конвертации HTML, вставлен как текст]:\n{plain_text}")
        except Exception as fallback_e:
            logger.error(f"Ошибка при аварийной вставке HTML как текста: {fallback_e}")
            docx_document.add_paragraph("[Ошибка конвертации HTML, не удалось вставить даже как текст]")

def get_docx_template(template_name):
    """
    Возвращает путь к шаблону DOCX.
    
    Args:
        template_name (str): Название шаблона
        
    Returns:
        str: Путь к файлу шаблона или None, если шаблон не найден
    """
    template_path = os.path.join(settings.BASE_DIR, 'templates', 'docx', f"{template_name}.docx")
    if os.path.exists(template_path):
        logger.info(f"Шаблон найден: {template_path}")
        return template_path
    
    logger.warning(f"Шаблон не найден: {template_path}")
    # Используем стандартный шаблон, если нужный не найден
    default_path = os.path.join(settings.BASE_DIR, 'templates', 'docx', 'diplo_project.docx')
    if os.path.exists(default_path):
        logger.info(f"Используется стандартный шаблон: {default_path}")
        return default_path
    
    logger.error("Стандартный шаблон не найден")
    return None

def ensure_basic_styles(docx):
    """
    Проверяет наличие и создает базовые стили для документа.
    
    Args:
        docx (Document): Документ python-docx
    """
    logger.info("Проверка наличия базовых стилей в документе")
    
    # Проверяем и создаем стиль Heading 1, если его нет
    if 'Heading 1' not in docx.styles:
        logger.info("Создание стиля 'Heading 1'")
        try:
            heading1_style = docx.styles.add_style('Heading 1', WD_STYLE_TYPE.PARAGRAPH)
            heading1_style.font.name = 'Times New Roman'
            heading1_style.font.size = Pt(16)
            heading1_style.font.bold = True
            heading1_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            heading1_style.paragraph_format.space_before = Pt(12)
            heading1_style.paragraph_format.space_after = Pt(6)
            logger.info("Стиль 'Heading 1' успешно создан")
        except Exception as e:
            logger.error(f"Ошибка при создании стиля 'Heading 1': {e}")
    
    # Проверяем и создаем стиль Normal, если его нет
    if 'Normal' not in docx.styles:
        logger.info("Создание стиля 'Normal'")
        try:
            normal_style = docx.styles.add_style('Normal', WD_STYLE_TYPE.PARAGRAPH)
            normal_style.font.name = 'Times New Roman'
            normal_style.font.size = Pt(12)
            normal_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            normal_style.paragraph_format.first_line_indent = Pt(15)
            normal_style.paragraph_format.space_after = Pt(6)
            logger.info("Стиль 'Normal' успешно создан")
        except Exception as e:
            logger.error(f"Ошибка при создании стиля 'Normal': {e}")
    
    # Создаем другие необходимые стили
    for style_name, params in {
        'Heading 2': {'size': Pt(14), 'bold': True, 'align': WD_ALIGN_PARAGRAPH.LEFT},
        'Heading 3': {'size': Pt(13), 'bold': True, 'align': WD_ALIGN_PARAGRAPH.LEFT}
    }.items():
        if style_name not in docx.styles:
            logger.info(f"Создание стиля '{style_name}'")
            try:
                style = docx.styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH)
                style.font.name = 'Times New Roman'
                style.font.size = params['size']
                style.font.bold = params['bold']
                style.paragraph_format.alignment = params['align']
                style.paragraph_format.space_before = Pt(6)
                style.paragraph_format.space_after = Pt(6)
                logger.info(f"Стиль '{style_name}' успешно создан")
            except Exception as e:
                logger.error(f"Ошибка при создании стиля '{style_name}': {e}")
    
    # Добавляем стили для списков, которые использует html2docx
    list_styles = ['List Bullet', 'List Number']
    for list_style_name in list_styles:
        if list_style_name not in docx.styles:
            logger.info(f"Создание стиля '{list_style_name}'")
            try:
                style = docx.styles.add_style(list_style_name, WD_STYLE_TYPE.PARAGRAPH)
                style.font.name = 'Times New Roman'
                style.font.size = Pt(12)
                style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                style.paragraph_format.left_indent = Pt(18)  # Отступ слева для списка
                style.paragraph_format.first_line_indent = Pt(-18)  # Отрицательный отступ первой строки (для маркера)
                style.paragraph_format.space_after = Pt(6)
                logger.info(f"Стиль '{list_style_name}' успешно создан")
            except Exception as e:
                logger.error(f"Ошибка при создании стиля '{list_style_name}': {e}")

def replace_document_fields(docx, replacements):
    """
    Заменяет поля в шаблоне документа их значениями с сохранением форматирования.
    При замене поля на значение добавляет нужное количество пробелов для сохранения
    размера строки, если значение короче плейсхолдера.
    
    Args:
        docx (Document): Документ python-docx
        replacements (dict): Словарь с заменами {поле: значение}
    """
    logger.info("Замена полей в шаблоне с сохранением форматирования")
    
    # Заменяем поля в параграфах более умным способом
    for paragraph in docx.paragraphs:
        # Проверяем, содержит ли параграф какое-либо поле
        for field, value in replacements.items():
            if field in paragraph.text:
                # Преобразуем значение поля в строку и обрабатываем специальные случаи
                value_str = str(value) if value is not None else ""
                
                # Вычисляем разницу в длине между полем и значением
                length_diff = len(field) - len(value_str)
                
                # Если значение короче поля, добавляем пробелы для компенсации
                if length_diff > 0:
                    # Добавляем пробелы, чтобы сохранить форматирование
                    value_str = value_str + ' ' * length_diff
                
                # Заменяем поле на значение с компенсированной длиной
                paragraph.text = paragraph.text.replace(field, value_str)
    
    # Заменяем поля в таблицах с тем же подходом
    for table in docx.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    for field, value in replacements.items():
                        if field in paragraph.text:
                            # Преобразуем значение поля в строку
                            value_str = str(value) if value is not None else ""
                            
                            # Вычисляем разницу в длине
                            length_diff = len(field) - len(value_str)
                            
                            # Если значение короче поля, добавляем пробелы
                            if length_diff > 0:
                                value_str = value_str + ' ' * length_diff
                            
                            # Заменяем поле на компенсированное значение
                            paragraph.text = paragraph.text.replace(field, value_str)

def apply_document_formatting(docx, standard_name):
    """
    Применяет стили форматирования к документу на основе стандарта.
    
    Args:
        docx (Document): Документ python-docx
        standard_name (str): Название стандарта (например, "ГОСТ 7.32-2017")
    """
    if not standard_name:
        logger.warning("Стандарт не указан, используются стили по умолчанию")
        return
    
    logger.info(f"Получение стилей форматирования для стандарта: {standard_name}")
    
    try:
        # Получаем стили форматирования от AI
        formatting = ai.generate(standard_name)
        
        if "error" in formatting:
            logger.warning(f"Не удалось получить стили для стандарта {standard_name}: {formatting['error']}")
            return
            
        logger.info(f"Стили для стандарта {standard_name} получены успешно")
        
        # Применяем стиль шрифта для основного текста (стиль Normal)
        if "font" in formatting:
            font_info = formatting["font"]
            # print(font_info) # Закомментируем отладочный вывод
            
            if "Normal" not in docx.styles:
                logger.info("Создание стиля 'Normal'")
                normal_style = docx.styles.add_style('Normal', WD_STYLE_TYPE.PARAGRAPH)
            else:
                normal_style = docx.styles["Normal"]
            
            if "family" in font_info:
                normal_style.font.name = font_info["family"]
                logger.info(f"Установлен шрифт: {font_info['family']}")
            
            if "size_pt" in font_info:
                normal_style.font.size = Pt(font_info["size_pt"])
                logger.info(f"Установлен размер шрифта: {font_info['size_pt']} pt")
            
            if "color" in font_info:
                color_str = font_info["color"].lower()
                if color_str == "black" or color_str == "черный":
                    normal_style.font.color.rgb = RGBColor(0, 0, 0)
                    logger.info(f"Установлен цвет шрифта: черный (0,0,0)")
                # Можно добавить обработку других распространенных цветов, если AI их возвращает
                # elif color_str == "red":
                #     normal_style.font.color.rgb = RGBColor(255, 0, 0)
                #     logger.info(f"Установлен цвет шрифта: красный (255,0,0)")
                else:
                    logger.warning(f"Неизвестный или неподдерживаемый цвет шрифта '{font_info['color']}', используется цвет по умолчанию (черный).")
                    normal_style.font.color.rgb = RGBColor(0, 0, 0) # По умолчанию черный
        
        # Применяем настройки отступов к документу
        if "margins_mm" in formatting:
            margins = formatting["margins_mm"]
            section = docx.sections[0]
            if "top" in margins:
                section.top_margin = Cm(margins["top"] / 10)
                logger.info(f"Установлен верхний отступ: {margins['top']} мм")
            if "bottom" in margins:
                section.bottom_margin = Cm(margins["bottom"] / 10)
                logger.info(f"Установлен нижний отступ: {margins['bottom']} мм")
            if "left" in margins:
                section.left_margin = Cm(margins["left"] / 10)
                logger.info(f"Установлен левый отступ: {margins['left']} мм")
            if "right" in margins:
                section.right_margin = Cm(margins["right"] / 10)
                logger.info(f"Установлен правый отступ: {margins['right']} мм")
        
        # Применяем настройки интервалов
        if "spacing" in formatting:
            spacing_info = formatting["spacing"]
            if "Normal" in docx.styles:
                normal_style = docx.styles["Normal"]
                if "line_spacing" in spacing_info:
                    line_spacing_str = str(spacing_info["line_spacing"]).replace(",", ".") # Замена запятой на точку
                    try:
                        line_spacing_val = float(line_spacing_str)
                        # python-docx использует значения: 1.0 для одинарного, 1.5, 2.0 и т.д.
                        normal_style.paragraph_format.line_spacing = line_spacing_val
                        logger.info(f"Установлен межстрочный интервал: {line_spacing_val}")
                    except ValueError:
                        logger.error(f"Некорректное значение для межстрочного интервала: '{spacing_info['line_spacing']}'. Используется одинарный.")
                        normal_style.paragraph_format.line_spacing = 1.0
                
                if "paragraph_spacing_pt" in spacing_info:
                    try:
                        paragraph_spacing = int(spacing_info["paragraph_spacing_pt"])
                        normal_style.paragraph_format.space_after = Pt(paragraph_spacing)
                        logger.info(f"Установлен интервал после абзаца: {paragraph_spacing} пт")
                    except ValueError:
                         logger.error(f"Некорректное значение для интервала после абзаца: '{spacing_info['paragraph_spacing_pt']}'. Используется 0.")
                         normal_style.paragraph_format.space_after = Pt(0)
        
        logger.info("Стили документа успешно применены")
        
    except Exception as e:
        logger.error(f"Ошибка при применении стилей к документу: {e}", exc_info=True)
        # В случае ошибки используем стили по умолчанию

def add_page_numbers(docx):
    """
    Добавляет нумерацию страниц в документ в нижней части страницы по центру.
    
    Args:
        docx (Document): Документ python-docx
    """
    logger.info("Добавление нумерации страниц")
    
    try:
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
        
        section = docx.sections[0]
        footer = section.footer
        
        # Очищаем существующее содержимое колонтитула
        for p in footer.paragraphs:
            p._element.getparent().remove(p._element)
            p._p = None
            p._element = None
        
        paragraph = footer.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Функция для создания номера страницы в Word
        def create_element(name):
            return OxmlElement(name)
        
        def create_attribute(element, name, value):
            element.set(qn(name), value)
        
        # Добавляем номер страницы
        run = paragraph.add_run()
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        
        # Создаем поле PAGE
        fldChar1 = create_element('w:fldChar')
        create_attribute(fldChar1, 'w:fldCharType', 'begin')
        
        instrText = create_element('w:instrText')
        create_attribute(instrText, 'xml:space', 'preserve')
        instrText.text = "PAGE"
        
        fldChar2 = create_element('w:fldChar')
        create_attribute(fldChar2, 'w:fldCharType', 'end')
        
        # Получаем элемент для запуска 
        r_element = run._r
        r_element.append(fldChar1)
        r_element.append(instrText)
        r_element.append(fldChar2)
        
        logger.info("Нумерация страниц успешно добавлена")
    except Exception as e:
        logger.error(f"Ошибка при добавлении нумерации страниц: {e}")

@login_required
def main_export_docx(request, pk):
    """
    Экспорт документа Main в формат DOCX.
    
    Args:
        request: HTTP запрос
        pk (int): ID документа
        
    Returns:
        HttpResponse: Ответ с DOCX файлом
    """
    logger.info(f"Начат экспорт документа Main (ID: {pk}) в DOCX")
    
    try:
        # Получаем документ
        document = get_object_or_404(Document_main, pk=pk, owner=request.user)
        logger.info(f"Документ найден: {document.title}")
        
        # Определяем шаблон на основе типа работы
        template_name = WORK_TYPE_TEMPLATES.get(document.work_type, 'diplo_project')
        template_path = get_docx_template(template_name)
        
        if not template_path:
            messages.error(request, "Не удалось найти шаблон для документа.")
            return redirect('documents:main_detail', pk=pk)
        
        # Используем DocxTemplate для заполнения шаблона вместо ручной замены
        doc_template = DocxTemplate(template_path)
        
        # Подготавливаем контекст для шаблона
        # Ключи должны соответствовать переменным в шаблоне (например, {{ TITLE }})
        context = {
            'TITLE': document.title.upper(),
            'TitleContinue': "",
            'YEAR': str(document.year),
            'YearShort': str(document.year)[-2:] if document.year else '__',
            'STUDENT_NAME': document.student_name or '',
            'SUPERVISOR': document.supervisor or '',
            'SupervisorPosition': getattr(document, 'supervisor_position', ''),
            'SupervisorSignature': '_________',
            'StudentSignature': '_________',
            'Institut': document.institute_name or 'Институт космических и информационных технологий',
            'institut': document.institute_name or 'Институт космических и информационных технологий',  # вариант с маленькой буквы
            'Kafedra': document.department_name or '',
            'ZavKaf': getattr(document, 'head_of_department', ''),
            'Podpis': '_________',
            'Day': getattr(document, 'day', '___'),
            'Month': getattr(document, 'month', '________'),
            'Speciality': f"{document.specialty_code} {document.specialty_name}".strip(),
            'UNIVERSITY': (document.university_name or 'СИБИРСКИЙ ФЕДЕРАЛЬНЫЙ УНИВЕРСИТЕТ').upper(),
            'code': document.specialty_code,
            'head_of_department': getattr(document, 'head_of_department', ''),
            'speciality_full': f"{document.specialty_code_full} {document.specialty_name}".strip(),
            'record_number': document.record_number,
            'reviewer': document.reviewer or '',
            'reviewer_position': getattr(document, 'reviewer_position', ''),
            'factory_supervisor': document.factory_supervisor or '',
        }
        
        # Рендерим документ с указанным контекстом
        logger.info("Заполнение шаблона через DocxTemplate")
        doc_template.render(context)
        
        # Сохраняем в BytesIO
        buffer = BytesIO()
        doc_template.save(buffer)
        
        # Теперь нам нужно добавить основное содержимое и применить стили
        # Для этого создаем обычный Document из сохраненного буфера
        buffer.seek(0)
        docx = Document(buffer)
        
        # Проверяем и создаем базовые стили только для основного текста
        ensure_basic_styles(docx)
        
        # Применяем стили форматирования на основе стандарта (только для основного текста)
        if document.standart:
            logger.info(f"Применение стилей форматирования для стандарта: {document.standart}")
            apply_document_formatting(docx, document.standart)
        
        # Добавляем содержимое документа
        if document.data:
            logger.info("Добавление содержимого документа")
            process_html_to_docx(document.data, docx)
        else:
            docx.add_paragraph("Документ не содержит данных")
            
        # Добавляем нумерацию страниц
        add_page_numbers(docx)
        
        # Сохраняем документ в BytesIO для передачи пользователю
        final_buffer = BytesIO()
        docx.save(final_buffer)
        final_buffer.seek(0)
        
        # Формируем имя файла
        safe_filename = slugify(document.document_name or document.title)
        if not safe_filename:  # Дополнительная проверка на пустое имя
            safe_filename = f"document_{pk}"
        filename = f"{safe_filename}.docx"
        
        # Отправляем файл пользователю с правильным Content-Disposition
        response = HttpResponse(
            final_buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"Экспорт документа Main в DOCX успешно завершен. Имя файла: {filename}")
        return response
        
    except Exception as e:
        logger.error(f"Ошибка при экспорте документа Main в DOCX: {e}")
        messages.error(request, f"Ошибка при экспорте документа: {str(e)}")
        return redirect('documents:main_detail', pk=pk)

@login_required
def main_export_pdf(request, pk):
    """
    Экспорт документа Main в формат PDF.
    
    Args:
        request: HTTP запрос
        pk (int): ID документа
        
    Returns:
        HttpResponse: Ответ с PDF файлом
    """
    logger.info(f"Начат экспорт документа Main (ID: {pk}) в PDF (ДИАГНОСТИКА - ЭТАП 2)") 
    
    com_initialized = False
    if pythoncom:
        try:
            pythoncom.CoInitialize()
            com_initialized = True
            logger.info("COM успешно инициализирован.")
        except Exception as e:
            logger.warning(f"Ошибка при инициализации COM: {e}")
            pass
            
    try:
        document_obj = get_object_or_404(Document_main, pk=pk, owner=request.user)
        logger.info(f"Документ найден: {document_obj.title}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = os.path.join(temp_dir, f"temp_{pk}_diag2.docx") 
            pdf_path = os.path.join(temp_dir, f"temp_{pk}_diag2.pdf")
            
            template_name = WORK_TYPE_TEMPLATES.get(document_obj.work_type, 'diplo_project')
            template_path = get_docx_template(template_name)
            
            if not template_path:
                messages.error(request, "Не удалось найти шаблон для документа.")
                return redirect('documents:main_detail', pk=pk)
            
            # 1. Рендеринг шаблона DocxTemplate
            doc_template = DocxTemplate(template_path)
            context = {
                'TITLE': document_obj.title.upper(),
                'TitleContinue': "",
                'YEAR': str(document_obj.year),
                'YearShort': str(document_obj.year)[-2:] if document_obj.year else '__',
                'STUDENT_NAME': document_obj.student_name or '',
                'SUPERVISOR': document_obj.supervisor or '',
                'SupervisorPosition': getattr(document_obj, 'supervisor_position', ''),
                'SupervisorSignature': '_________',
                'StudentSignature': '_________',
                'Institut': document_obj.institute_name or 'Институт космических и информационных технологий',
                'institut': document_obj.institute_name or 'Институт космических и информационных технологий',
                'Kafedra': document_obj.department_name or '',
                'ZavKaf': getattr(document_obj, 'head_of_department', ''),
                'Podpis': '_________',
                'Day': getattr(document_obj, 'day', '___'),
                'Month': getattr(document_obj, 'month', '________'),
                'Speciality': f"{document_obj.specialty_code} {document_obj.specialty_name}".strip(),
                'UNIVERSITY': (document_obj.university_name or 'СИБИРСКИЙ ФЕДЕРАЛЬНЫЙ УНИВЕРСИТЕТ').upper(),
                'code': document_obj.specialty_code,
                'head_of_department': getattr(document_obj, 'head_of_department', ''),
                'speciality_full': f"{document_obj.specialty_code_full} {document_obj.specialty_name}".strip(),
                'record_number': document_obj.record_number,
                'reviewer': document_obj.reviewer or '',
                'reviewer_position': getattr(document_obj, 'reviewer_position', ''),
                'factory_supervisor': document_obj.factory_supervisor or '',
            }
            logger.info("Заполнение шаблона через DocxTemplate (ДИАГНОСТИКА - ЭТАП 2)")
            doc_template.render(context)
            
            # --- НАЧАЛО БЛОКА ДИАГНОСТИКИ ЭТАП 2: --- 
            # Сохраняем результат DocxTemplate НАПРЯМУЮ в файл, минуя Document(buffer)
            logger.info(f"ДИАГНОСТИКА - ЭТАП 2: Сохранение результата DocxTemplate напрямую в {docx_path}")
            doc_template.save(docx_path) # <--- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ ДЛЯ ДИАГНОСТИКИ
            # --- КОНЕЦ БЛОКА ДИАГНОСТИКИ ЭТАП 2 --- 
            
            # 6. Конвертация в PDF
            logger.info(f"Конвертация DOCX в PDF из файла: {docx_path} (ДИАГНОСТИКА - ЭТАП 2)")
            convert(docx_path, pdf_path)
            logger.info(f"PDF файл создан: {pdf_path} (ДИАГНОСТИКА - ЭТАП 2)")
            
            safe_filename = slugify(document_obj.document_name or document_obj.title or "document")
            if not safe_filename:
                safe_filename = f"document_{pk}"
            filename = f"{safe_filename}_diag2.pdf" 
            
            with open(pdf_path, 'rb') as pdf_file:
                response = HttpResponse(pdf_file.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                
                logger.info(f"Экспорт документа Main в PDF успешно завершен. Имя файла: {filename} (ДИАГНОСТИКА - ЭТАП 2)")
                return response
                
    except Exception as e:
        logger.error(f"Ошибка при экспорте документа Main в PDF (ДИАГНОСТИКА - ЭТАП 2): {e}", exc_info=True)
        messages.error(request, f"Ошибка при экспорте документа (диагностика - этап 2): {str(e)}")
        return redirect('documents:main_detail', pk=pk)
    finally:
        if com_initialized:
            try:
                pythoncom.CoUninitialize()
                logger.info("COM успешно деинициализирован.")
            except Exception as e:
                logger.warning(f"Ошибка при деинициализации COM: {e}")
