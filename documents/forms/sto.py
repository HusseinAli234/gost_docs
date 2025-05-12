from django import forms
from django.forms import inlineformset_factory
from documents.models import Document, Abstract, Section, BibliographyEntry, Appendix

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = [
            'work_type', 'specialty_code', 'specialty_name', 'title',
            'supervisor', 'student_name', 'consultants', 'approval_note',
            'city', 'year',
        ]

class AbstractForm(forms.ModelForm):
    class Meta:
        model = Abstract
        exclude = ['document']

class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['type', 'order', 'title', 'content']

class BibliographyEntryForm(forms.ModelForm):
    class Meta:
        model = BibliographyEntry
        fields = ['order', 'entry_text']

class AppendixForm(forms.ModelForm):
    class Meta:
        model = Appendix
        fields = ['label', 'title', 'content']

# Inline formsets
SectionFormSet = inlineformset_factory(
    Document, Section, form=SectionForm,
    extra=1, can_delete=True
)
BibliographyFormSet = inlineformset_factory(
    Document, BibliographyEntry, form=BibliographyEntryForm,
    extra=1, can_delete=True
)
AppendixFormSet = inlineformset_factory(
    Document, Appendix, form=AppendixForm,
    extra=1, can_delete=True
)
