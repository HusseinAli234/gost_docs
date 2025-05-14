from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from ckeditor_uploader.fields import RichTextUploadingField


class Document_sto(models.Model):
    """Общая «обёртка» для любого текстового документа по СТО 4.2–07–2008."""
    WORK_TYPES = [
        ('MAG_DIPLOMA', 'Магистерская диссертация'),
        ('DIPLOMA',    'Дипломная работа/проект'),
        ('BACHELOR',   'Бакалаврская работа'),
        ('COURSE',     'Курсовой проект/работа'),
        ('CALC_GRAPH', 'Расчётно-графическая работа'),
        ('PRACTICE',   'Отчёт по практике'),
        ('LAB',        'Отчёт по лабораторной работе'),
        ('REF',        'Реферат'),
    ]

    owner           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='docs')
    # --- титульный лист ---
    work_type       = models.CharField('Вид работы', max_length=20, choices=WORK_TYPES)
    specialty_code  = models.CharField('Код специальности', max_length=20, blank=True)
    specialty_name  = models.CharField('Наименование специальности/направления', max_length=200, blank=True)
    title           = models.CharField('Тема работы', max_length=255)
    supervisor      = models.CharField('Руководитель (ФИО, ученая степень/звание)', max_length=200)
    student_name    = models.CharField('Исполнитель (ФИО)', max_length=200)
    consultants     = RichTextUploadingField('Консультанты (ФИО, должность)', blank=True,
                                       help_text='По пункту 6.2.2: консультанты и нормоконтролёр')
    approval_note   = models.CharField('Гриф утверждения', max_length=200, blank=True,
                                       help_text='Заполняется для ВКР и отчётов')
    city            = models.CharField('Город выполнения', max_length=100, default='Бишкек')
    year            = models.PositiveSmallIntegerField('Год выполнения', default=2025)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Документ СТО'
        verbose_name_plural = 'Документы СТО'

    def __str__(self):
        return f"{self.get_work_type_display()} «{self.title}» — {self.student_name}"


class Abstract_sto(models.Model):
    """Реферат (аннотация) по разделу 6.3 СТО."""
    document            = models.OneToOneField(Document_sto, on_delete=models.CASCADE, related_name='abstract')
    page_count          = models.PositiveSmallIntegerField('Кол-во страниц')
    illustrations_count = models.PositiveSmallIntegerField('Кол-во иллюстраций')
    tables_count        = models.PositiveSmallIntegerField('Кол-во таблиц')
    formulas_count      = models.PositiveSmallIntegerField('Кол-во формул')
    appendices_count    = models.PositiveSmallIntegerField('Кол-во приложений')
    references_count    = models.PositiveSmallIntegerField('Кол-во источников')
    graphic_sheets      = models.PositiveSmallIntegerField('Листов графического материала')
    keywords            = models.TextField('Ключевые слова',
                                          help_text='До 15 слов/словосочетаний, прописными, через запятую')
    text                = RichTextUploadingField('Текст реферата')

    def __str__(self):
        return f"Реферат к {self.document}"
    
    class Meta:
        verbose_name = 'Реферат СТО'
        verbose_name_plural = 'Рефераты СТО'
        ordering = ['document__created_at']


class Section(models.Model):
    """Любой структурный элемент (введение, глава основной части, заключение)."""
    SECTION_TYPES = [
        ('INTRO', 'Введение'),
        ('MAIN',  'Основная часть'),
        ('CONCL', 'Заключение'),
        # можно добавить подпункты, если нужно
    ]

    document    = models.ForeignKey(Document_sto, on_delete=models.CASCADE, related_name='sections')
    type        = models.CharField('Тип раздела', max_length=5, choices=SECTION_TYPES)
    order       = models.PositiveSmallIntegerField('Порядок')
    title       = models.CharField('Заголовок раздела', max_length=200)
    content     = RichTextUploadingField('Содержимое (HTML или текст)')

    class Meta:
        ordering = ['order']
        verbose_name = 'Раздел СТО'
        verbose_name_plural = 'Разделы СТО'

    def __str__(self):
        return f"{self.get_type_display()} ({self.order}) — {self.document}"


class BibliographyEntry(models.Model):
    """Элемент списка использованных источников (6.8)."""
    document    = models.ForeignKey(Document_sto, on_delete=models.CASCADE, related_name='biblio')
    order       = models.PositiveSmallIntegerField('Порядок в списке')
    entry_text  = RichTextUploadingField('Оформление по ГОСТ 7.1–2003')

    class Meta:
        ordering = ['order']
        verbose_name = 'Элемент списка источников СТО'
        verbose_name_plural = 'Список использованных источников СТО'

    def __str__(self):
        return f"{self.order}. {self.entry_text[:50]}…"


class Appendix_sto(models.Model):
    """Приложения (6.9)."""
    document    = models.ForeignKey(Document_sto, on_delete=models.CASCADE, related_name='appendices')
    label       = models.CharField('Буквенный индекс (Приложение А, Б, …)', max_length=2)
    title       = models.CharField('Название приложения', max_length=200, blank=True)
    content     = models.TextField('Файл приложения')  # или TextField для текста

    class Meta:
        ordering = ['label']
        verbose_name = 'Приложение СТО'
        verbose_name_plural = 'Приложения СТО'

    def __str__(self):
        return f"Приложение {self.label} к {self.document}"
