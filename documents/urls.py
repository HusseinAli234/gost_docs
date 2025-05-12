from django.urls import path
from .views import gost

urlpatterns = [
    path('', gost.document_list, name='document_list'),
    path('new/', gost.document_create, name='document_create'),
    path('edit/<int:pk>/', gost.document_edit, name='document_edit'),
    # path('export/docx/<int:pk>/', views.document_export_docx, name='document_export_docx'),
    # path('export/pdf/<int:pk>/', views.document_export_pdf, name='document_export_pdf'),

]
