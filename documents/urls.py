from django.urls import path
from documents.views import (
    DocumentListView, DocumentDetailView,
    DocumentCreateView, DocumentUpdateView, DocumentDeleteView
)
from documents.views.gost import (
    DocumentListView, DocumentDetailView,
    DocumentCreateView, DocumentUpdateView
)

app_name = 'documents'

urlpatterns = [
    path('', DocumentListView.as_view(), name='document_list'),
    path('new/', DocumentCreateView.as_view(), name='document_create'),
    path('edit/<int:pk>/', DocumentUpdateView.as_view(), name='document_edit'),
    path('detail/<int:pk>/', DocumentDetailView.as_view(), name='document_detail'),


    
    path('sto/', DocumentListView.as_view(), name='list'),
    path('sto/<int:pk>/', DocumentDetailView.as_view(), name='detail'),
    path('sto/create/', DocumentCreateView.as_view(), name='create'),
    path('sto/<int:pk>/edit/', DocumentUpdateView.as_view(), name='edit'),
    path('sto/<int:pk>/delete/', DocumentDeleteView.as_view(), name='delete'),
]