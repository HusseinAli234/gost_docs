from django.urls import path
from documents.views import gost
from documents.views.gost import (
    DocumentListView, DocumentDetailView,
    DocumentCreateView, DocumentUpdateView
)

urlpatterns = [
    path('', DocumentListView.as_view(), name='document_list'),
    path('new/', DocumentCreateView.as_view(), name='document_create'),
    path('edit/<int:pk>/', DocumentUpdateView.as_view(), name='document_edit'),
    path('detail/<int:pk>/', DocumentDetailView.as_view(), name='document_detail'),
    # path('export/docx/<int:pk>/', views.document_export_docx, name='document_export_docx'),
    # path('export/pdf/<int:pk>/', views.document_export_pdf, name='document_export_pdf'),
]
