# documents/views/gost.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, View, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from documents.models.gost import Document, Abstract
from documents.forms.gost import (
    DocumentForm, AppendixFormSet, TermFormSet,
    AbbreviationFormSet, PerformerFormSet,
    ReferenceFormSet, TitlePageForm, AbstractForm
)


class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'documents/document_list.html'
    context_object_name = 'documents'

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user).order_by('-created_at')


class DocumentDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Document
    template_name = 'documents/document_detail.html'
    context_object_name = 'document'

    def test_func(self):
        return self.get_object().user == self.request.user


class DocumentCreateView(LoginRequiredMixin, View):
    template_name = 'documents/document_form.html'

    def get(self, request, *args, **kwargs):
        context = {
            'form': DocumentForm(),
            'title_form': TitlePageForm(),
            'abstract_form': AbstractForm(),
            'performer_formset': PerformerFormSet(prefix='performers'),
            'term_formset': TermFormSet(prefix='terms'),
            'abbrev_formset': AbbreviationFormSet(prefix='abbrevs'),
            'reference_formset': ReferenceFormSet(prefix='refs'),
            'appendix_formset': AppendixFormSet(prefix='apps'),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        doc_form = DocumentForm(request.POST)
        title_form = TitlePageForm(request.POST)
        abstract_form = AbstractForm(request.POST)
        performer_formset = PerformerFormSet(request.POST, request.FILES, prefix='performers')
        term_formset = TermFormSet(request.POST, request.FILES, prefix='terms')
        abbrev_formset = AbbreviationFormSet(request.POST, request.FILES, prefix='abbrevs')
        reference_formset = ReferenceFormSet(request.POST, request.FILES, prefix='refs')
        appendix_formset = AppendixFormSet(request.POST, request.FILES, prefix='apps')

        if all([
            doc_form.is_valid(), title_form.is_valid(), abstract_form.is_valid(),
            performer_formset.is_valid(), term_formset.is_valid(), abbrev_formset.is_valid(),
            reference_formset.is_valid(), appendix_formset.is_valid(),
        ]):
            document = doc_form.save(commit=False)
            document.user = request.user
            document.save()

            title = title_form.save(commit=False)
            title.document = document
            title.save()

            abstract = abstract_form.save(commit=False)
            abstract.document = document
            abstract.save()

            for fs in [performer_formset, term_formset, abbrev_formset, reference_formset, appendix_formset]:
                instances = fs.save(commit=False)
                for inst in instances:
                    inst.document = document
                    inst.save()
                fs.save_m2m()

            return redirect('documents:gost_detail', pk=document.pk)

        context = {
            'form': doc_form,
            'title_form': title_form,
            'abstract_form': abstract_form,
            'performer_formset': performer_formset,
            'term_formset': term_formset,
            'abbrev_formset': abbrev_formset,
            'reference_formset': reference_formset,
            'appendix_formset': appendix_formset,
            'error_message': 'Пожалуйста, исправьте ошибки в форме.'
        }
        return render(request, self.template_name, context)


class DocumentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = 'documents/document_form.html'
    pk_url_kwarg = 'pk'
    context_object_name = 'document'

    def test_func(self):
        return self.get_object().user == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.object
        if self.request.POST:
            context['title_form'] = TitlePageForm(self.request.POST, instance=getattr(obj, 'title_page', None))
            context['abstract_form'] = AbstractForm(self.request.POST, instance=getattr(obj, 'abstract', None))
            context['performer_formset'] = PerformerFormSet(self.request.POST, self.request.FILES, prefix='performers', queryset=obj.performers.all())
            context['term_formset'] = TermFormSet(self.request.POST, self.request.FILES, prefix='terms', queryset=obj.terms.all())
            context['abbrev_formset'] = AbbreviationFormSet(self.request.POST, self.request.FILES, prefix='abbrevs', queryset=obj.abbreviations.all())
            context['reference_formset'] = ReferenceFormSet(self.request.POST, self.request.FILES, prefix='refs', queryset=obj.references.all())
            context['appendix_formset'] = AppendixFormSet(self.request.POST, self.request.FILES, prefix='apps', queryset=obj.appendices.all())
        else:
            context['title_form'] = TitlePageForm(instance=getattr(obj, 'title_page', None))
            context['abstract_form'] = AbstractForm(instance=getattr(obj, 'abstract', None))
            context['performer_formset'] = PerformerFormSet(prefix='performers', queryset=obj.performers.all())
            context['term_formset'] = TermFormSet(prefix='terms', queryset=obj.terms.all())
            context['abbrev_formset'] = AbbreviationFormSet(prefix='abbrevs', queryset=obj.abbreviations.all())
            context['reference_formset'] = ReferenceFormSet(prefix='refs', queryset=obj.references.all())
            context['appendix_formset'] = AppendixFormSet(prefix='apps', queryset=obj.appendices.all())
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        if all([
            form.is_valid(), context['title_form'].is_valid(), context['abstract_form'].is_valid(),
            context['performer_formset'].is_valid(), context['term_formset'].is_valid(),
            context['abbrev_formset'].is_valid(), context['reference_formset'].is_valid(),
            context['appendix_formset'].is_valid(),
        ]):
            self.object = form.save()
            title = context['title_form'].save(commit=False)
            title.document = self.object
            title.save()
            abstract = context['abstract_form'].save(commit=False)
            abstract.document = self.object
            abstract.save()
            for fs in [context['performer_formset'], context['term_formset'], context['abbrev_formset'], context['reference_formset'], context['appendix_formset']]:
                instances = fs.save(commit=False)
                for inst in instances:
                    inst.document = self.object
                    inst.save()
                fs.save_m2m()
            return redirect('documents:gost_detail', pk=self.object.pk)
        return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('documents:gost_detail', kwargs={'pk': self.object.pk})