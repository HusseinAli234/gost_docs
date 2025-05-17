from django import forms
from django.contrib.auth.models import User
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _
from documents.models import Document_main

class Document_mainForm(ModelForm):

    class Meta:
        model = Document_main

        fields = [
            'standart',
            'university_name',
            'institute_name',
            'department_name',
            'document_name',
            'work_type',
            'specialty_code',
            'specialty_name',
            'title',
            'supervisor',
            'head_of_department',
            'student_name',
            'consultants',
            'factory_supervisor',
            'reviewer',
            'reviewer_position',
            'supervisor_position',
            'record_number',
            'approval_note',
            'city',
            'year',
            'data',
        ]
        widgets = {
            'consultants': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'university_name': _('Наименование университета'),
            'institute_name': _('Полное наименование института'),
            'department_name': _('Полное наименование кафедры'),
            'head_of_department': _('Заведующий кафедрой(ФИО)'),
            'factory_supervisor': _('Руководитель предприятия(ФИО) *Необязательное поле'),
            'reviewer': _('Рецензент (ФИО)*Необязательное поле'),
            'reviewer_position': _('Должность рецензента,ученая степень/звание *Необязательное поле'),
            'supervisor_position': _('Должность руководителя,ученая степень/звание'),
            'record_number': _('Номер зачётной книжки *Необязательное поле'),
            'document_name': _('Название документа'),
            'work_type': _('Вид работы'),
            'specialty_code': _('Код специальности'),
            'specialty_name': _('Наименование специальности/направления'),
            'title': _('Тема работы'),
            'supervisor': _('Руководитель (ФИО, ученая степень/звание)'),
            'student_name': _('Исполнитель (ФИО)'),
            'consultants': _('Консультанты (ФИО, должность)'),
            'approval_note': _('Гриф утверждения'),
            'city': _('Город выполнения'),
            'year': _('Год выполнения'),
            'data': _('Данные'),
        }
        help_texts = {
            'consultants': _('По пункту 6.2.2: консультанты и нормоконтролёр'),
            'approval_note': _('Заполняется для ВКР и отчётов'),
            'data': _('Все данные, которые будут отображаться в документе. \n'
                      'Реферат: \n'
                      'содержание, \n'
                      'введение, \n'
                      'основная часть, \n'
                      'заключение, \n'
                      'список использованных источников, \n'
                      'приложения. \n'),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control' })    