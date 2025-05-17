from django import forms
from documents.models.gost import Document,TitlePage, Performer,Abstract,Abbreviation,Appendix,Term,Reference
from django.forms import inlineformset_factory

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = '__all__'
        exclude = ['user', 'created_at']
       
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})    


class TitlePageForm(forms.ModelForm):
    class Meta:
        model = TitlePage
        exclude = ['document']
        widgets = {
            'approval_date': forms.DateInput(attrs={'type': 'date'})
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control'})      

class AbstractForm(forms.ModelForm):
    class Meta:
        model = Abstract
        fields = ['content']
      
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})  
class PerformerForm(forms.ModelForm):
    class Meta:
        model = Performer
        exclude = ['document']
        widgets = {
            'date_signed': forms.DateInput(attrs={'type': 'date'}),
            'signed': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.DateInput)):
                field.widget.attrs.update({'class': 'form-control'})  
class TermForm(forms.ModelForm):
    class Meta:
        model = Term
        exclude = ['document']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})  
class AbbreviationForm(forms.ModelForm):
    class Meta:
        model = Abbreviation
        exclude = ['document']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})  
class ReferenceForm(forms.ModelForm):
    class Meta:
        model = Reference
        exclude = ['document']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})  
class AppendixForm(forms.ModelForm):
    class Meta:
        model = Appendix
        exclude = ['document']
   
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})  
# Inline formsets
PerformerFormSet = inlineformset_factory(Document, Performer, form=PerformerForm, extra=1, can_delete=True)
TermFormSet = inlineformset_factory(Document, Term, form=TermForm, extra=1, can_delete=True)
AbbreviationFormSet = inlineformset_factory(Document, Abbreviation, form=AbbreviationForm, extra=1, can_delete=True)
ReferenceFormSet = inlineformset_factory(Document, Reference, form=ReferenceForm, extra=1, can_delete=True)
AppendixFormSet = inlineformset_factory(Document, Appendix, form=AppendixForm, extra=1, can_delete=True)
