from django import forms
from django.contrib.auth.models import User
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _
from documents.models import Document_main
from ckeditor.widgets import CKEditorWidget

class Document_mainForm(ModelForm):
    # Добавляем поле для выбора способа ввода стандарта
    STANDARD_INPUT_CHOICES = [
        ('text', 'Ввести текст вручную'),
        ('file', 'Загрузить файл (DOCX/PDF)')
    ]
    
    standard_input_method = forms.ChoiceField(
        choices=STANDARD_INPUT_CHOICES,
        widget=forms.RadioSelect,
        initial='text',
        label=_('Способ ввода стандарта')
    )
    
    # Поле для загрузки файла стандарта
    standard_file = forms.FileField(
        required=False,
        label=_('Загрузить файл стандарта'),
        help_text=_('Поддерживаются форматы DOCX и PDF'),
        widget=forms.FileInput(attrs={'accept': '.docx,.pdf'})
    )

    class Meta:
        model = Document_main
        data = forms.CharField(widget=CKEditorWidget(config_name='default'), required=False)

        fields = [
            'standart',
            'university_name',
            'institute_name',
            'department_name',
            'document_name',
            'work_type',
            'specialty_code',
            'specialty_name',
            'specialty_code_full',
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
            'standart': forms.Textarea(attrs={'rows': 5}),
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
            'specialty_code_full': _('Код специальности Магистерской программы'),
            'title': _('Тема работы'),
            'supervisor': _('Руководитель (ФИО, ученая степень/звание)'),
            'student_name': _('Исполнитель (ФИО)'),
            'consultants': _('Консультанты (ФИО, должность)'),
            'approval_note': _('Гриф утверждения'),
            'city': _('Город выполнения'),
            'year': _('Год выполнения'),
            'data': _('Данные'),
            'standart': _('Стандарт оформления'),
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
            'standart': _('Введите требования к оформлению документа или загрузите файл со стандартом'),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
            
        # Специальный класс для радио-кнопок
        self.fields['standard_input_method'].widget.attrs.update({'class': 'form-check-input'})
        
    def clean(self):
        cleaned_data = super().clean()
        standard_input_method = cleaned_data.get('standard_input_method')
        standard_file = cleaned_data.get('standard_file')
        standart = cleaned_data.get('standart')
        
        # Проверяем, что если выбран метод загрузки файла, то файл действительно загружен
        if standard_input_method == 'file' and not standard_file:
            self.add_error('standard_file', _('Необходимо загрузить файл стандарта'))
            
        # Проверяем, что если выбран метод ввода текста, то текст действительно введен
        if standard_input_method == 'text' and not standart:
            self.add_error('standart', _('Необходимо ввести текст стандарта'))
            
        return cleaned_data    