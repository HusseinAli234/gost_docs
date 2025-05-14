from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.forms import CustomAuthenticationForm
from django.contrib.auth import views as auth_views
from documents.views.landing import LandingPageView
from ckeditor_uploader import views as ck_views
from django.contrib.auth.decorators import login_required


urlpatterns = [
    path('ckeditor/upload/',
         login_required(ck_views.upload),
         name='ckeditor_upload'),

    # Браузер загруженных файлов (только для авторизованных)
    path('ckeditor/browse/',
         login_required(ck_views.browse),
         name='ckeditor_browse'),
    path('admin/', admin.site.urls),

    # Лендинг-страница
    path('', LandingPageView.as_view(), name='landing'),

    # ГОСТ-документы
    path('documents/', include('documents.urls', namespace='documents')),

    # Аутентификация
    # 1) Сначала наши кастомные view (register и т.п.)
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    # 2) Логин со своей формой
    path('accounts/login/',
         auth_views.LoginView.as_view(form_class=CustomAuthenticationForm),
         name='login'),
    # 3) Всё остальное из contrib.auth (logout, password_change и т.д.)
    path('accounts/', include('django.contrib.auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
