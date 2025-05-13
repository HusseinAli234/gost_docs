from django.urls import path
from .views.gost import (
    DocumentListView as GostDocumentListView,
    DocumentDetailView as GostDocumentDetailView,
    DocumentCreateView as GostDocumentCreateView,
    DocumentUpdateView as GostDocumentUpdateView,
)
from .views.sto import (
    DocumentListView as StoDocumentListView,
    DocumentDetailView as StoDocumentDetailView,
    DocumentCreateView as StoDocumentCreateView,
    DocumentUpdateView as StoDocumentUpdateView,
    DocumentDeleteView as StoDocumentDeleteView,
)

app_name = 'documents'

urlpatterns = [
    # ГОСТ 7.32
    path('gost/', GostDocumentListView.as_view(), name='gost_list'),
    path('gost/new/', GostDocumentCreateView.as_view(), name='gost_create'),
    path('gost/<int:pk>/', GostDocumentDetailView.as_view(), name='gost_detail'),
    path('gost/<int:pk>/edit/', GostDocumentUpdateView.as_view(), name='gost_edit'),

    # СТО СФУ 4.2
    path('sto/', StoDocumentListView.as_view(), name='sto_list'),
    path('sto/create/', StoDocumentCreateView.as_view(), name='sto_create'),
    path('sto/<int:pk>/', StoDocumentDetailView.as_view(), name='sto_detail'),
    path('sto/<int:pk>/edit/', StoDocumentUpdateView.as_view(), name='sto_edit'),
    path('sto/<int:pk>/delete/', StoDocumentDeleteView.as_view(), name='sto_delete'),
]
