from django.urls import path
from . import views

urlpatterns = [
    path('', views.document_list, name='document_list'),
    path('new/', views.document_create, name='document_create'),
    path('edit/<int:pk>/', views.document_edit, name='document_edit'),
    path('export/docx/<int:pk>/', views.document_export_docx, name='document_export_docx'),
    path('export/pdf/<int:pk>/', views.document_export_pdf, name='document_export_pdf'),

]
