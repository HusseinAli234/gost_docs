from django.db import models
from django.contrib.auth.models import User
from ckeditor_uploader.fields import RichTextUploadingField


class Document(models.Model):
    """Основная модель для документа/отчета.""" # Добавил комментарий
    TEMPLATE_CHOICES = [
        ('gost', 'ГОСТ 7.32'),
        ('sto', 'СТО СФУ 4.2'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь') # Добавлено verbose_name
    title = models.CharField('Заголовок', max_length=255) # Добавлено verbose_name
    template_type = models.CharField('Тип шаблона', max_length=10, choices=TEMPLATE_CHOICES) # Добавлено verbose_name
    report_type = models.CharField('Тип отчета', max_length=20, choices=[('final', 'Заключительный'), ('intermediate', 'Промежуточный')], default='intermediate') # Добавлено verbose_name, исправлен default
    year = models.PositiveIntegerField('Год', default=2024) # Добавлено verbose_name
    created_at = models.DateTimeField('Дата создания', auto_now_add=True) # Добавлено verbose_name

    # Связи на другие части отчета
    introduction = RichTextUploadingField('Введение', blank=True, null=True) # Добавлено verbose_name
    main_part = RichTextUploadingField('Основная часть', blank=True, null=True) # Добавлено verbose_name
    conclusion = RichTextUploadingField('Заключение', blank=True, null=True) # Добавлено verbose_name

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Документ' # Изменено на просто "Документ" для общности
        verbose_name_plural = 'Документы' # Изменено на просто "Документы"


class TitlePage(models.Model):
    """Модель для титульного листа документа.""" # Добавил комментарий
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='title_page', verbose_name='Документ') # Добавлено verbose_name
    stage_name = models.CharField('Название этапа', max_length=255, blank=True) # Добавлено verbose_name
    udk = models.CharField('УДК', max_length=50, blank=True) # Добавлено verbose_name
    registration_number_nioktr = models.CharField('Рег. номер НИОКТР', max_length=100, blank=True) # Добавлено verbose_name
    registration_number_ikrbs = models.CharField('Рег. номер ИКРБС', max_length=100, blank=True) # Добавлено verbose_name
    program_code = models.CharField('Шифр программы', max_length=255, blank=True) # Добавлено verbose_name
    book_number = models.CharField('Номер книги (тома)', max_length=20, blank=True) # Добавлено verbose_name
    federal_program_name = models.CharField('Название фед. программы', max_length=255, blank=True) # Добавлено verbose_name
    department = models.CharField('Подразделение (отдел, кафедра)', max_length=255, blank=True) # Добавлено verbose_name
    head_full_name = models.CharField('ФИО руководителя', max_length=255, blank=True) # Добавлено verbose_name
    head_position = models.CharField('Должность руководителя', max_length=255, blank=True) # Добавлено verbose_name
    head_degree = models.CharField('Ученая степень руководителя', max_length=100, blank=True) # Добавлено verbose_name
    approval_date = models.DateField('Дата утверждения', blank=True, null=True) # Добавлено verbose_name


class Performer(models.Model):
    """Модель для исполнителей/участников работы.""" # Добавил комментарий
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='performers', verbose_name='Документ') # Добавлено verbose_name
    full_name = models.CharField('ФИО', max_length=255) # Добавлено verbose_name
    position = models.CharField('Должность', max_length=255) # Добавлено verbose_name
    degree = models.CharField('Ученая степень/звание', max_length=100) # Добавлено verbose_name
    participation = models.CharField('Участие / Вклад', max_length=500, blank=True) # Добавлено verbose_name
    signed = models.BooleanField('Подписано', default=False) # Добавлено verbose_name
    date_signed = models.DateField('Дата подписи', blank=True, null=True) # Добавлено verbose_name


class Abstract(models.Model):
    """Модель для реферата/аннотации.""" # Добавил комментарий
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='abstract', verbose_name='Документ') # Добавлено verbose_name
    content = RichTextUploadingField('Содержание реферата') # Добавлено verbose_name


class Term(models.Model):
    """Модель для терминов и определений.""" # Добавил комментарий
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='terms', verbose_name='Документ') # Добавлено verbose_name
    term = models.CharField('Термин', max_length=255) # Добавлено verbose_name
    definition = models.TextField('Определение') # Добавлено verbose_name


class Abbreviation(models.Model):
    """Модель для списка сокращений.""" # Добавил комментарий
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='abbreviations', verbose_name='Документ') # Добавлено verbose_name
    abbreviation = models.CharField('Сокращение', max_length=100) # Добавлено verbose_name
    meaning = models.TextField('Расшифровка') # Добавлено verbose_name


class Reference(models.Model):
    """Модель для элемента списка источников.""" # Добавил комментарий
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='references', verbose_name='Документ') # Добавлено verbose_name
    citation = models.TextField('Описание источника (по ГОСТ)') # Добавлено verbose_name
    order = models.PositiveIntegerField('Порядок в списке') # Добавлено verbose_name

    class Meta:
        ordering = ['order']
        verbose_name = 'Источник' # Добавлено
        verbose_name_plural = 'Список источников' # Добавлено


class Appendix(models.Model):
    """Модель для приложений.""" # Добавил комментарий
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='appendices', verbose_name='Документ') # Добавлено verbose_name
    label = models.CharField('Буквенный индекс (А, Б, В...)', max_length=10)  # Пример: А, Б, В # Добавлено verbose_name
    title = models.CharField('Заголовок приложения', max_length=255) # Добавлено verbose_name
    content = RichTextUploadingField('Содержание приложения') # Добавлено verbose_name
    order = models.PositiveIntegerField('Порядок') # Добавлено verbose_name

    class Meta:
        ordering = ['order']
        verbose_name = 'Приложение' # Добавлено
        verbose_name_plural = 'Приложения' # Добавлено