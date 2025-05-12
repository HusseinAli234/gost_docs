from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView,
    CreateView, UpdateView, DeleteView,
)
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from documents.models import Document
from documents.forms import (
    DocumentForm, AbstractForm,
    SectionFormSet, BibliographyFormSet, AppendixFormSet
)


class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'sto/sto_list.html'
    context_object_name = 'sto_documents'
    paginate_by = 10

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)


class DocumentDetailView(LoginRequiredMixin, DetailView):
    model = Document
    template_name = 'sto/sto_detail.html'
    context_object_name = 'sto'


class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'sto/sto_form.html'
    success_url = reverse_lazy('documents:list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # если это GET-запрос — создаём пустые формы/формсеты
        if self.request.POST:
            ctx['abstract_form'] = AbstractForm(self.request.POST)
            ctx['sections']      = SectionFormSet(self.request.POST)
            ctx['biblio']        = BibliographyFormSet(self.request.POST)
            ctx['appendices']    = AppendixFormSet(self.request.POST)
        else:
            ctx['abstract_form'] = AbstractForm()
            ctx['sections']      = SectionFormSet()
            ctx['biblio']        = BibliographyFormSet()
            ctx['appendices']    = AppendixFormSet()
        return ctx

    def form_valid(self, form):
        # проверяем все формы/формсеты
        context = self.get_context_data()
        abstract_form = context['abstract_form']
        sections     = context['sections']
        biblio       = context['biblio']
        appendices   = context['appendices']

        valid = (
            form.is_valid() and abstract_form.is_valid()
            and sections.is_valid() and biblio.is_valid()
            and appendices.is_valid()
        )
        if not valid:
            return self.render_to_response(self.get_context_data(form=form))

        # сохраняем документ
        form.instance.owner = self.request.user
        self.object = form.save()

        # сохраняем реферат
        abs_obj = abstract_form.save(commit=False)
        abs_obj.document = self.object
        abs_obj.save()

        # сохраняем все inline formsets
        sections.instance = self.object
        sections.save()

        biblio.instance = self.object
        biblio.save()

        appendices.instance = self.object
        appendices.save()

        return redirect(self.success_url)


class DocumentUpdateView(LoginRequiredMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = 'sto/sto_form.html'

    def get_success_url(self):
        return reverse_lazy('documents:detail', args=[self.object.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # если нужно редактировать реферат только для документов с Abstract
        if self.request.POST:
            ctx['abstract_form'] = AbstractForm(self.request.POST, instance=self.object.abstract if hasattr(self.object, 'abstract') else None)
            ctx['sections']      = SectionFormSet(self.request.POST, instance=self.object)
            ctx['biblio']        = BibliographyFormSet(self.request.POST, instance=self.object)
            ctx['appendices']    = AppendixFormSet(self.request.POST, instance=self.object)
        else:
            ctx['abstract_form'] = AbstractForm(instance=getattr(self.object, 'abstract', None))
            ctx['sections']      = SectionFormSet(instance=self.object)
            ctx['biblio']        = BibliographyFormSet(instance=self.object)
            ctx['appendices']    = AppendixFormSet(instance=self.object)
        return ctx

    def form_valid(self, form):
        context = self.get_context_data()
        abstract_form = context['abstract_form']
        sections     = context['sections']
        biblio       = context['biblio']
        appendices   = context['appendices']
        valid = form.is_valid() and abstract_form.is_valid() and sections.is_valid() and biblio.is_valid() and appendices.is_valid()
        if valid:
            self.object = form.save()
            # save OneToOne abstract
            abs_obj = abstract_form.save(commit=False)
            abs_obj.document = self.object
            abs_obj.save()
            # save all inline formsets
            sections.instance = self.object
            sections.save()
            biblio.instance = self.object
            biblio.save()
            appendices.instance = self.object
            appendices.save()
            return redirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))


class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = Document
    template_name = 'sto/sto_confirm_delete.html'
    success_url = reverse_lazy('documents:list')
