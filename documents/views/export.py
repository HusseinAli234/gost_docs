from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.text import slugify
from django.conf import settings
from django.contrib import messages

from io import BytesIO, StringIO
import os
import logging
import tempfile
import base64
import re
import mimetypes
import json
import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx2pdf import convert
# Импорт DocxTemplate для работы с шаблонами
from docxtpl import DocxTemplate

# Импортируем htmldocx вместо mammoth
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

def django_mammoth_image_converter(image):
    """
    Пользовательская функция-конвертер изображений для mammoth.
    Mammoth вызывает ее для каждого тега <img>.
    Получает объект mammoth.images.Image, представляющий тег.
    Должна вернуть словарь с ключами 'data' (байты изображения) и 'contentType' (MIME-тип).
    Обрабатывает пути к медиа-файлам Django.
    """
    src = image.src
    logger.debug(f"Mammoth встретил изображение с src: {src}")

    try:
        # Проверяем различные типы источников изображений
        if src and src.startswith(settings.MEDIA_URL):
            # 1. Изображение из медиа-хранилища Django
            relative_media_path = src[len(settings.MEDIA_URL):]
            file_path = os.path.join(settings.MEDIA_ROOT, relative_media_path)

            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    image_data = f.read()
                content_type, _ = mimetypes.guess_type(file_path)
                logger.debug(f"Загружено изображение из медиа: {file_path}, тип: {content_type}")
            else:
                logger.warning(f"Файл изображения не найден: {file_path}")
                return None

        elif src and src.startswith('data:image/'):
            # 2. Изображение в формате base64
            try:
                header, encoded = src.split(",", 1)
                content_type = header.split(";")[0].split(":")[1]
                image_data = base64.b64decode(encoded)
                logger.debug(f"Декодировано base64 изображение, тип: {content_type}")
            except Exception as e:
                logger.error(f"Ошибка при декодировании base64 изображения: {e}")
                return None

        elif src and (src.startswith('http://') or src.startswith('https://')):
            # 3. Изображение по внешнему URL
            try:
                response = requests.get(src, stream=True, timeout=10)
                if response.status_code == 200:
                    image_data = response.content
                    content_type = response.headers.get('Content-Type', 'image/jpeg')
                    logger.debug(f"Загружено изображение по URL: {src}, тип: {content_type}")
                else:
                    logger.warning(f"Не удалось загрузить изображение по URL: {src}, статус: {response.status_code}")
                    return None
            except Exception as e:
                logger.error(f"Ошибка при загрузке изображения по URL {src}: {e}")
                return None
        else:
            logger.warning(f"Неподдерживаемый формат src изображения: {src}")
            return None

        # Проверяем, что мы определили MIME-тип
        if content_type is None:
            logger.warning(f"Не удалось определить MIME-тип изображения: {src}. Изображение будет пропущено.")
            return None

        # Возвращаем данные в формате, который ожидает mammoth
        return {
            'src': src,
            'alt': image.alt,
            'data': image_data,
            'contentType': content_type
        }

    except Exception as e:
        logger.error(f"Общая ошибка при обработке изображения {src}: {e}", exc_info=True)
        return None

def process_html_to_docx(html_content, docx_document):
    """
    Преобразует HTML-контент в DOCX и добавляет его в существующий документ.
    Изображения загружаются напрямую по URL и вставляются в правильные места,
    сохраняя текст вокруг изображений.
    
    Args:
        html_content (str): HTML-контент для преобразования.
        docx_document (Document): Существующий объект python-docx, куда будет добавлен контент.
    """
    if not html_content:
        logger.info("HTML контент пуст, нечего добавлять.")
        return

    logger.info(f"Обработка HTML контента длиной {len(html_content)} символов")
    
    try:
        # Создаем временную директорию для хранения изображений
        with tempfile.TemporaryDirectory() as temp_dir:
            # Модифицируем HTML для обработки изображений
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Словарь для хранения информации об изображениях
            # Ключ - уникальный идентификатор, значение - путь к сохраненному изображению
            images_map = {}
            
            # Находим все изображения
            images = soup.find_all('img')
            for i, img in enumerate(images):
                src = img.get('src', '')
                if not src:
                    continue
                
                logger.info(f"Обрабатываю изображение {i+1}/{len(images)}: {src[:50]}...")
                
                # Генерируем уникальный идентификатор для этого изображения
                img_id = f"IMG_PLACEHOLDER_{i}"
                
                # Пытаемся загрузить изображение
                img_path = None
                
                try:
                    # Обрабатываем различные форматы src
                    if src.startswith(('http://', 'https://')):
                        # Внешний URL
                        logger.info(f"Загрузка изображения по URL: {src}")
                        response = requests.get(src, stream=True, timeout=10)
                        if response.status_code == 200:
                            # Определяем расширение файла из Content-Type или URL
                            content_type = response.headers.get('Content-Type', '')
                            ext = mimetypes.guess_extension(content_type) or '.png'
                            if ext == '.jpe':
                                ext = '.jpg'
                            
                            # Сохраняем изображение во временную директорию
                            img_path = os.path.join(temp_dir, f"image_{i}{ext}")
                            with open(img_path, 'wb') as f:
                                f.write(response.content)
                            logger.info(f"Изображение сохранено: {img_path}")
                        else:
                            logger.warning(f"Не удалось загрузить изображение, статус: {response.status_code}")
                    
                    elif src.startswith('data:image/'):
                        # Data URL (base64)
                        logger.info("Обработка Data URL изображения")
                        try:
                            header, encoded = src.split(",", 1)
                            content_type = header.split(";")[0].split(":")[1]
                            ext = mimetypes.guess_extension(content_type) or '.png'
                            if ext == '.jpe':
                                ext = '.jpg'
                            
                            # Декодируем base64 и сохраняем изображение
                            img_path = os.path.join(temp_dir, f"image_{i}{ext}")
                            with open(img_path, 'wb') as f:
                                f.write(base64.b64decode(encoded))
                            logger.info(f"Base64 изображение сохранено: {img_path}")
                        except Exception as e:
                            logger.error(f"Ошибка при декодировании base64: {e}")
                    
                    elif src.startswith('/'):
                        # Локальный путь от корня сайта
                        logger.info(f"Обработка локального пути: {src}")
                        
                        # Если путь начинается с /media/, используем MEDIA_ROOT
                        if src.startswith('/media/'):
                            file_path = os.path.join(settings.MEDIA_ROOT, src[7:])
                        # Иначе пробуем относительно BASE_DIR
                        else:
                            file_path = os.path.join(settings.BASE_DIR, src[1:])
                        
                        if os.path.exists(file_path):
                            # Копируем файл во временную директорию
                            ext = os.path.splitext(file_path)[1] or '.png'
                            img_path = os.path.join(temp_dir, f"image_{i}{ext}")
                            with open(file_path, 'rb') as src_file, open(img_path, 'wb') as dst_file:
                                dst_file.write(src_file.read())
                            logger.info(f"Локальное изображение скопировано: {img_path}")
                        else:
                            # Если файл не найден, пробуем построить URL и загрузить через HTTP
                            try:
                                full_url = f"http://localhost:8000{src}"
                                logger.info(f"Пробую загрузить через HTTP: {full_url}")
                                response = requests.get(full_url, stream=True, timeout=10)
                                if response.status_code == 200:
                                    content_type = response.headers.get('Content-Type', '')
                                    ext = mimetypes.guess_extension(content_type) or '.png'
                                    if ext == '.jpe':
                                        ext = '.jpg'
                                    
                                    img_path = os.path.join(temp_dir, f"image_{i}{ext}")
                                    with open(img_path, 'wb') as f:
                                        f.write(response.content)
                                    logger.info(f"Изображение загружено через HTTP: {img_path}")
                                else:
                                    logger.warning(f"Не удалось загрузить через HTTP, статус: {response.status_code}")
                            except Exception as e:
                                logger.error(f"Ошибка при HTTP загрузке: {e}")
                    
                    # Если удалось загрузить изображение, сохраняем информацию
                    if img_path and os.path.exists(img_path):
                        images_map[img_id] = img_path
                        # НЕ заменяем тег img на плейсхолдер, а добавляем к нему атрибут data-img-id
                        img['data-img-id'] = img_id
                
                except Exception as e:
                    logger.error(f"Ошибка при обработке изображения {src}: {e}", exc_info=True)
            
            # Преобразуем модифицированный HTML в строку
            modified_html = str(soup)
            
            # Создаем парсер htmldocx
            parser = HtmlToDocx()
            parser.table_style = 'TableGrid'
            
            # Добавляем HTML в документ
            parser.add_html_to_document(modified_html, docx_document)
            
            # После добавления HTML, заменяем изображения
            for paragraph in docx_document.paragraphs:
                # Проверяем, содержит ли параграф изображение
                img_id_match = re.search(r'data-img-id="(IMG_PLACEHOLDER_\d+)"', paragraph.text)
                if img_id_match:
                    img_id = img_id_match.group(1)
                    img_path = images_map.get(img_id)
                    
                    if img_path and os.path.exists(img_path):
                        logger.info(f"Заменяю изображение с ID {img_id} на {img_path}")
                        
                        # Сохраняем текст до и после тега изображения
                        full_text = paragraph.text
                        img_tag_pattern = r'<img[^>]*data-img-id="' + img_id + r'"[^>]*>'
                        img_tag_match = re.search(img_tag_pattern, full_text)
                        
                        if img_tag_match:
                            before_text = full_text[:img_tag_match.start()].strip()
                            after_text = full_text[img_tag_match.end():].strip()
                            
                            # Очищаем параграф
                            paragraph.clear()
                            
                            # Добавляем текст до изображения, если он есть
                            if before_text:
                                paragraph.add_run(before_text)
                            
                            # Добавляем изображение
                            run = paragraph.add_run()
                            run.add_picture(img_path, width=Inches(5.0))
                            
                            # Добавляем текст после изображения, если он есть
                            if after_text:
                                paragraph.add_run(after_text)
                        else:
                            # Если не нашли точное положение тега, просто добавляем изображение
                            # и сохраняем весь текст, очищенный от HTML тегов
                            clean_text = re.sub(r'<[^>]*>', '', full_text).strip()
                            paragraph.clear()
                            
                            if clean_text:
                                paragraph.add_run(clean_text)
                                
                            # Добавляем изображение в новый параграф
                            p = docx_document.add_paragraph()
                            run = p.add_run()
                            run.add_picture(img_path, width=Inches(5.0))
                    else:
                        logger.warning(f"Не удалось найти изображение для ID {img_id}")
                        
                        # Очищаем текст от HTML тегов
                        clean_text = re.sub(r'<[^>]*>', '', paragraph.text).strip()
                        if clean_text:
                            paragraph.text = clean_text
                
                # Для параграфов без изображений, очищаем от HTML тегов
                elif '<' in paragraph.text and '>' in paragraph.text:
                    clean_text = re.sub(r'<[^>]*>', '', paragraph.text).strip()
                    if clean_text:
                        paragraph.text = clean_text
            
            logger.info("HTML успешно преобразован и добавлен в документ")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке HTML: {e}", exc_info=True)
        # В случае ошибки добавляем просто текст как запасной вариант
        try:
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
        
        # Добавляем раздел "Работа с источниками" и список литературы
        docx.add_paragraph("", style='Normal')  # Пустая строка для разделения
        heading = docx.add_paragraph("1.5 Работа с источниками", style='Heading 2')
        
        # Добавляем описание функционала работы с источниками
        p1 = docx.add_paragraph(style='Normal')
        p1.add_run("• Ввод DOI → Получение метаданных через CrossRef API")
        
        p2 = docx.add_paragraph(style='Normal')
        p2.add_run("• Автоматическая генерация библиографической ссылки")
        
        p3 = docx.add_paragraph(style='Normal')
        p3.add_run("• Список литературы в формате ГОСТ 7.1-2003")
        
        # Добавляем список литературы
        add_references_section(docx, document)
            
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
    logger.info(f"Начат экспорт документа Main (ID: {pk}) в PDF") 
    
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
            docx_path = os.path.join(temp_dir, f"temp_{pk}.docx") 
            pdf_path = os.path.join(temp_dir, f"temp_{pk}.pdf")
            
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
            logger.info("Заполнение шаблона через DocxTemplate")
            doc_template.render(context)
            
            # Сохраняем результат DocxTemplate в файл
            logger.info(f"Сохранение результата DocxTemplate в {docx_path}")
            doc_template.save(docx_path)
            
            # Загружаем документ для добавления содержимого и стилей
            docx = Document(docx_path)
            
            # Проверяем и создаем базовые стили
            ensure_basic_styles(docx)
            
            # Применяем стили форматирования на основе стандарта
            if document_obj.standart:
                logger.info(f"Применение стилей форматирования для стандарта: {document_obj.standart}")
                apply_document_formatting(docx, document_obj.standart)
            
            # Добавляем содержимое документа
            if document_obj.data:
                logger.info("Добавление содержимого документа")
                process_html_to_docx(document_obj.data, docx)
            else:
                docx.add_paragraph("Документ не содержит данных")
            
            
            # Добавляем список литературы
            add_references_section(docx, document_obj)
                
            # Добавляем нумерацию страниц
            add_page_numbers(docx)
            
            # Сохраняем обновленный документ
            docx.save(docx_path)
            
            # Конвертация в PDF
            logger.info(f"Конвертация DOCX в PDF из файла: {docx_path}")
            convert(docx_path, pdf_path)
            logger.info(f"PDF файл создан: {pdf_path}")
            
            safe_filename = slugify(document_obj.document_name or document_obj.title or "document")
            if not safe_filename:
                safe_filename = f"document_{pk}"
            filename = f"{safe_filename}.pdf" 
            
            with open(pdf_path, 'rb') as pdf_file:
                response = HttpResponse(pdf_file.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                
                logger.info(f"Экспорт документа Main в PDF успешно завершен. Имя файла: {filename}")
                return response
                
    except Exception as e:
        logger.error(f"Ошибка при экспорте документа Main в PDF: {e}", exc_info=True)
        messages.error(request, f"Ошибка при экспорте документа: {str(e)}")
        return redirect('documents:main_detail', pk=pk)
    finally:
        if com_initialized:
            try:
                pythoncom.CoUninitialize()
                logger.info("COM успешно деинициализирован.")
            except Exception as e:
                logger.warning(f"Ошибка при деинициализации COM: {e}")

def get_metadata_from_doi(doi):
    """
    Получает метаданные публикации по DOI через CrossRef API.
    
    Args:
        doi (str): DOI публикации
        
    Returns:
        dict: Словарь с метаданными или None в случае ошибки
    """
    logger.info(f"Получение метаданных для DOI: {doi}")
    
    try:
        # Формируем URL для запроса к CrossRef API
        url = f"https://api.crossref.org/works/{doi}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "GostDocsApp/1.0 (mailto:admin@example.com)"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if 'message' in data:
                logger.info(f"Метаданные для DOI {doi} успешно получены")
                return data['message']
            else:
                logger.warning(f"В ответе CrossRef API отсутствует поле 'message' для DOI {doi}")
                return None
        else:
            logger.warning(f"Ошибка при запросе к CrossRef API для DOI {doi}: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка при получении метаданных для DOI {doi}: {e}", exc_info=True)
        return None

def format_citation_gost(metadata):
    """
    Форматирует библиографическую ссылку по ГОСТ 7.1-2003 на основе метаданных CrossRef.
    
    Args:
        metadata (dict): Метаданные публикации из CrossRef API
        
    Returns:
        str: Отформатированная библиографическая ссылка
    """
    try:
        # Получаем основные данные из метаданных
        title = metadata.get('title', [''])[0] if isinstance(metadata.get('title', []), list) else metadata.get('title', '')
        
        # Получаем авторов
        authors = []
        if 'author' in metadata:
            for author in metadata['author']:
                given = author.get('given', '')
                family = author.get('family', '')
                if given and family:
                    # Формат: Фамилия И.О.
                    initials = ''.join([name[0] + '.' for name in given.split()])
                    authors.append(f"{family} {initials}")
                elif family:
                    authors.append(family)
        
        # Формируем строку авторов по ГОСТ
        authors_str = ""
        if authors:
            if len(authors) == 1:
                authors_str = authors[0]
            elif len(authors) <= 3:
                authors_str = ", ".join(authors)
            else:
                authors_str = f"{authors[0]} и др."
        
        # Получаем данные о журнале или издательстве
        container_title = metadata.get('container-title', [''])[0] if isinstance(metadata.get('container-title', []), list) else metadata.get('container-title', '')
        publisher = metadata.get('publisher', '')
        
        # Получаем данные о выпуске
        volume = metadata.get('volume', '')
        issue = metadata.get('issue', '')
        page = metadata.get('page', '')
        
        # Получаем год публикации
        year = ""
        if 'published' in metadata and 'date-parts' in metadata['published']:
            year = str(metadata['published']['date-parts'][0][0]) if metadata['published']['date-parts'][0] else ""
        
        # Формируем ссылку по ГОСТ 7.1-2003
        citation = ""
        
        # Добавляем авторов
        if authors_str:
            citation += f"{authors_str}. "
        
        # Добавляем название
        if title:
            citation += f"{title}"
            # Добавляем точку, если название не заканчивается знаком препинания
            if not title[-1] in ['.', '!', '?']:
                citation += ". "
            else:
                citation += " "
        
        # Добавляем данные о журнале/издательстве
        if container_title:
            citation += f"// {container_title}. "
        elif publisher:
            citation += f"// {publisher}. "
        
        # Добавляем год
        if year:
            citation += f"{year}. "
        
        # Добавляем данные о выпуске
        if volume:
            citation += f"Т. {volume}"
            if issue or page:
                citation += ", "
        
        if issue:
            citation += f"№ {issue}"
            if page:
                citation += ", "
        
        if page:
            citation += f"С. {page}"
        
        # Добавляем DOI
        if 'DOI' in metadata:
            citation += f". DOI: {metadata['DOI']}"
        
        return citation
        
    except Exception as e:
        logger.error(f"Ошибка при форматировании ссылки по ГОСТ: {e}", exc_info=True)
        return f"Ошибка форматирования ссылки: {str(e)}"

def add_references_section(docx_document, document_obj):
    """
    Добавляет раздел со списком литературы в документ.
    
    Args:
        docx_document (Document): Документ python-docx
        document_obj: Объект документа из базы данных
    """
    logger.info("Добавление раздела со списком литературы")
    
    try:
        # Добавляем заголовок раздела
        docx_document.add_paragraph("", style='Normal')  # Пустая строка перед разделом
        heading = docx_document.add_paragraph("Список литературы", style='Heading 1')
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Получаем список DOI из документа
        # Предполагаем, что DOI хранятся в поле references_doi как строка с разделителями
        doi_list = []
        if hasattr(document_obj, 'references_doi') and document_obj.references_doi:
            # Разбиваем строку на отдельные DOI
            doi_list = [doi.strip() for doi in document_obj.references_doi.split(',') if doi.strip()]
        
        # Если список DOI пуст, добавляем информационное сообщение
        if not doi_list:
            docx_document.add_paragraph("Список литературы не содержит источников.", style='Normal')
            return
        
        # Обрабатываем каждый DOI и добавляем ссылку в документ
        for i, doi in enumerate(doi_list, 1):
            # Получаем метаданные по DOI
            metadata = get_metadata_from_doi(doi)
            
            if metadata:
                # Форматируем ссылку по ГОСТ
                citation = format_citation_gost(metadata)
                # Добавляем ссылку в документ с номером
                p = docx_document.add_paragraph(style='Normal')
                p.add_run(f"{i}. ").bold = True
                p.add_run(citation)
            else:
                # Если не удалось получить метаданные, добавляем только DOI
                p = docx_document.add_paragraph(style='Normal')
                p.add_run(f"{i}. ").bold = True
                p.add_run(f"DOI: {doi} (не удалось получить метаданные)")
        
        logger.info(f"Добавлено {len(doi_list)} источников в список литературы")
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении раздела со списком литературы: {e}", exc_info=True)
        docx_document.add_paragraph("Ошибка при формировании списка литературы", style='Normal')
