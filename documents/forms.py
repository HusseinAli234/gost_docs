from django import forms
from .models import Document
from ckeditor.widgets import CKEditorWidget

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = '__all__'
        exclude = ['user', 'created_at']
        widgets = {
            'introduction': CKEditorWidget(),
            'goal': CKEditorWidget(),
            'tasks': CKEditorWidget(),
            'main_part': CKEditorWidget(),
            'conclusion': CKEditorWidget(),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})    
