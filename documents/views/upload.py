# views.py
from ckeditor_uploader.views import upload
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# Разрешаем доступ авторизованным (не обязательно админам)
@method_decorator([login_required, csrf_exempt], name='dispatch')
def ckeditor_upload(request):
    return upload(request)
