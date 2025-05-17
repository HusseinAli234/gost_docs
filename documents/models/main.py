from django.db import models
from django.contrib.auth.models import User
from ckeditor_uploader.fields import RichTextUploadingField


class Document_main(models.Model):
    standart = models.CharField('Стандарт', max_length=255, null=True, blank=True,)
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

    university_name = models.CharField('Наименование университета', max_length=255, null =True, blank=True)
    institute_name = models.CharField('Полное наименование института', max_length=255, null =True, blank=True)
    department_name = models.CharField('Полное наименование кафедры', max_length=255, null =True, blank=True)
    document_name = models.CharField('Название документа', max_length=255, null =True, blank=True,)
    head_of_department = models.CharField('Заведующий кафедрой', max_length=255, null =True, blank=True,)
    # --- титульный лист ---
    work_type       = models.CharField('Вид работы', max_length=20, choices=WORK_TYPES)
    specialty_code  = models.CharField('Код специальности', max_length=100, blank=True)
    specialty_name  = models.CharField('Наименование специальности/направления', max_length=200, blank=True)
    specialty_code_full  = models.CharField('Код специальности Магистерской программы', max_length=200, blank=True)
    title           = models.CharField('Тема работы', max_length=255)
    record_number   = models.CharField('Номер зачётной книжки', max_length=200, blank=True)
    supervisor      = models.CharField('Руководитель (ФИО)', max_length=200)
    supervisor_position = models.CharField('Должность руководителя,ученая степень/звание', max_length=200, blank=True)
    factory_supervisor = models.CharField('Руководитель предприятия', max_length=200, blank=True)
    reviewer = models.CharField('Рецензент (ФИО)', max_length=200, blank=True)
    reviewer_position = models.CharField('Должность рецензента,ученая степень/звание', max_length=200, blank=True)
    student_name    = models.CharField('Исполнитель (ФИО)', max_length=200)
    consultants     = RichTextUploadingField('Консультанты (ФИО, должность)', blank=True,
                                       help_text='По пункту 6.2.2: консультанты и нормоконтролёр')
    approval_note   = models.CharField('Гриф утверждения', max_length=200, blank=True,
                                       help_text='Заполняется для ВКР и отчётов')
    city            = models.CharField('Город выполнения', max_length=100, default='Москва')
    year            = models.PositiveSmallIntegerField('Год выполнения', default=2025)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    data = RichTextUploadingField('Данные', blank=True, 
                                   help_text='Все данные, которые будут отображаться в документе. \n'
                                            'Реферат: \n'
                                            'содержание, \n'
                                            'введение, \n'
                                            'основная часть, \n'
                                            'заключение, \n'
                                            'список использованных источников, \n'
                                            'приложения. \n')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Главный Документ'
        verbose_name_plural = 'Главные Документы'

    def __str__(self):
        return f"{self.title} ({self.student_name})"
    

