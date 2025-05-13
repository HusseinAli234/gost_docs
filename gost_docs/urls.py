from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.forms import CustomAuthenticationForm
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # ГОСТ-документы
    path('', include('documents.urls', namespace='documents')),

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
