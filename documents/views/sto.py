from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from documents.models import Document_sto
from documents.forms import DocumentForm, AbstractForm, SectionFormSet, BibliographyFormSet, AppendixFormSet
from django.http import Http404
from django.http import HttpResponse
from docxtpl import DocxTemplate
import os
from io import BytesIO


def generate_title_page(request, pk):
    from documents.models import Document_sto

    try:
        doc = Document_sto.objects.get(pk=pk, owner=request.user)
    except Document_sto.DoesNotExist:
        raise Http404("Документ не найден.")

    # Путь к шаблону
    template_path = os.path.join('templates', 'docx', 'diplo_project.docx')
    tpl = DocxTemplate(template_path)

    context = {
        "institute_name": doc.institute_name or "________",
        "department_name": doc.department_name or "________",
        "specialty_code_and_name": f"{doc.specialty_code or '___'} {doc.specialty_name or '_________'}",
        "title": doc.title,
        "supervisor": doc.supervisor,
        "student_name": doc.student_name,
        "year": doc.year,
    }

    tpl.render(context)

    buffer = BytesIO()
    tpl.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = f'attachment; filename="Титульный_лист_{doc.student_name}.docx"'
    return response


class DocumentListView(LoginRequiredMixin, ListView):
    model = Document_sto
    template_name = 'sto/sto_list.html'
    context_object_name = 'sto_documents'
    paginate_by = 10

    def get_queryset(self):
        return Document_sto.objects.filter(owner=self.request.user)


class DocumentDetailView(LoginRequiredMixin, DetailView):
    model = Document_sto
    template_name = 'sto/sto_detail.html'
    context_object_name = 'sto'


class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = Document_sto
    form_class = DocumentForm
    template_name = 'sto/sto_form.html'
    success_url = reverse_lazy('documents:sto_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['abstract_form'] = AbstractForm(self.request.POST)
            ctx['sections'] = SectionFormSet(self.request.POST)
            ctx['biblio'] = BibliographyFormSet(self.request.POST)
            ctx['appendices'] = AppendixFormSet(self.request.POST)
        else:
            ctx['abstract_form'] = AbstractForm()
            ctx['sections'] = SectionFormSet()
            ctx['biblio'] = BibliographyFormSet()
            ctx['appendices'] = AppendixFormSet()
        return ctx

    def form_valid(self, form):
        context = self.get_context_data()
        if not (form.is_valid() and context['abstract_form'].is_valid() and context['sections'].is_valid() and context['biblio'].is_valid() and context['appendices'].is_valid()):
            return self.render_to_response(self.get_context_data(form=form))
        form.instance.owner = self.request.user
        self.object = form.save()
        abs_obj = context['abstract_form'].save(commit=False)
        abs_obj.document = self.object
        abs_obj.save()
        context['sections'].instance = self.object
        context['sections'].save()
        context['biblio'].instance = self.object
        context['biblio'].save()
        context['appendices'].instance = self.object
        context['appendices'].save()
        return redirect(self.success_url)


class DocumentUpdateView(LoginRequiredMixin, UpdateView):
    model = Document_sto
    form_class = DocumentForm
    template_name = 'sto/sto_form.html'

    def get_success_url(self):
        return reverse_lazy('documents:sto_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['abstract_form'] = AbstractForm(self.request.POST, instance=getattr(self.object, 'abstract', None))
            ctx['sections'] = SectionFormSet(self.request.POST, instance=self.object)
            ctx['biblio'] = BibliographyFormSet(self.request.POST, instance=self.object)
            ctx['appendices'] = AppendixFormSet(self.request.POST, instance=self.object)
        else:
            ctx['abstract_form'] = AbstractForm(instance=getattr(self.object, 'abstract', None))
            ctx['sections'] = SectionFormSet(instance=self.object)
            ctx['biblio'] = BibliographyFormSet(instance=self.object)
            ctx['appendices'] = AppendixFormSet(instance=self.object)
        return ctx

    def form_valid(self, form):
        context = self.get_context_data()
        if form.is_valid() and context['abstract_form'].is_valid() and context['sections'].is_valid() and context['biblio'].is_valid() and context['appendices'].is_valid():
            self.object = form.save()
            abs_obj = context['abstract_form'].save(commit=False)
            abs_obj.document = self.object
            abs_obj.save()
            context['sections'].instance = self.object
            context['sections'].save()
            context['biblio'].instance = self.object
            context['biblio'].save()
            context['appendices'].instance = self.object
            context['appendices'].save()
            return redirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(form=form))


class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = Document_sto
    template_name = 'sto/sto_confirm_delete.html'
    success_url = reverse_lazy('documents:sto_list')
