from django.shortcuts import render, redirect, get_object_or_404
from ..models.gost import Documentss
from ..forms.gost import DocumentForm
from django.contrib.auth.decorators import login_required

@login_required
def document_list(request):
    documents = Documentss.objects.filter(user=request.user)
    return render(request, 'documents/document_list.html', {'documents': documents})

@login_required
def document_create(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.user = request.user
            doc.save()
            return redirect('document_list')
    else:
        form = DocumentForm()
    return render(request, 'documents/document_form.html', {'form': form})

@login_required
def document_edit(request, pk):
    doc = get_object_or_404(Documentss, pk=pk, user=request.user)
    if request.method == 'POST':
        form = DocumentForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            return redirect('document_list')
    else:
        form = DocumentForm(instance=doc)
    return render(request, 'documents/document_form.html', {'form': form})
