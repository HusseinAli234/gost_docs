from django import forms
from django.forms import inlineformset_factory
from documents.models import Document_sto, Abstract_sto, Section, BibliographyEntry, Appendix_sto

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document_sto
        fields = [
            'work_type', 'specialty_code', 'specialty_name', 'title',
            'supervisor', 'student_name', 'consultants', 'approval_note',
            'city', 'year',
        ]

class AbstractForm(forms.ModelForm):
    class Meta:
        model = Abstract_sto
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
        model = Appendix_sto
        fields = ['label', 'title', 'content']

# Inline formsets
SectionFormSet = inlineformset_factory(
    Document_sto, Section, form=SectionForm,
    extra=1, can_delete=True
)
BibliographyFormSet = inlineformset_factory(
    Document_sto, BibliographyEntry, form=BibliographyEntryForm,
    extra=1, can_delete=True
)
AppendixFormSet = inlineformset_factory(
    Document_sto, Appendix_sto, form=AppendixForm,
    extra=1, can_delete=True
)
