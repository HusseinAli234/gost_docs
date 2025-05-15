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
    generate_title_page,
)
from .views.export import gost_export_docx, sto_export_docx
from .views.main import (
    DocumentListView as MainDocumentListView,
    DocumentDetailView as MainDocumentDetailView,
    DocumentCreateView as MainDocumentCreateView,
    DocumentUpdateView as MainDocumentUpdateView,
    DocumentDeleteView as MainDocumentDeleteView,
)

app_name = 'documents'

urlpatterns = [
    # ГОСТ 7.32
    path('gost/', GostDocumentListView.as_view(), name='gost_list'),
    path('gost/new/', GostDocumentCreateView.as_view(), name='gost_create'),
    path('gost/<int:pk>/', GostDocumentDetailView.as_view(), name='gost_detail'),
    path('gost/<int:pk>/edit/', GostDocumentUpdateView.as_view(), name='gost_edit'),
    path('gost/<int:pk>/export/docx/', gost_export_docx, name='gost_export_docx'),

    # СТО СФУ 4.2
    path('sto/', StoDocumentListView.as_view(), name='sto_list'),
    path('sto/create/', StoDocumentCreateView.as_view(), name='sto_create'),
    path('sto/<int:pk>/', StoDocumentDetailView.as_view(), name='sto_detail'),
    path('sto/<int:pk>/edit/', StoDocumentUpdateView.as_view(), name='sto_edit'),
    path('sto/<int:pk>/delete/', StoDocumentDeleteView.as_view(), name='sto_delete'),
    path('sto/<int:pk>/export/docx/', sto_export_docx, name='sto_export_docx'),
    path('sto/<int:pk>/download_title_page/', generate_title_page, name='generate_title_page'),


    path('main/', MainDocumentListView.as_view(), name='main_list'),
    path('main/create/', MainDocumentCreateView.as_view(), name='main_create'),
    path('main/<int:pk>/', MainDocumentDetailView.as_view(), name='main_detail'),
    path('main/<int:pk>/edit/', MainDocumentUpdateView.as_view(), name='main_edit'),
    path('main/<int:pk>/delete/', MainDocumentDeleteView.as_view(), name='main_delete'),
]

