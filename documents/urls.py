from django.urls import path
from .views import gost
from documents.views import (
    DocumentListView, DocumentDetailView,
    DocumentCreateView, DocumentUpdateView, DocumentDeleteView
)

app_name = 'documents'

urlpatterns = [
    path('', gost.document_list, name='document_list'),
    path('new/', gost.document_create, name='document_create'),
    path('edit/<int:pk>/', gost.document_edit, name='document_edit'),


    
    path('sto/', DocumentListView.as_view(), name='list'),
    path('sto/<int:pk>/', DocumentDetailView.as_view(), name='detail'),
    path('sto/create/', DocumentCreateView.as_view(), name='create'),
    path('sto/<int:pk>/edit/', DocumentUpdateView.as_view(), name='edit'),
    path('sto/<int:pk>/delete/', DocumentDeleteView.as_view(), name='delete'),

]
