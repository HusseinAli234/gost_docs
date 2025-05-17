from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from documents.models.main import Document_main
# Импортируй функции из твоего модуля
from ai import check_standard


@login_required
def check_standard_view(request,pk):
    if request.method == 'GET':
        try:
            document = get_object_or_404(Document_main, pk=pk, owner=request.user)
            standard_text = document.standart
            document_text = document.data

            if not standard_text or not document_text:
                return JsonResponse({'error': 'Missing standard_text or document_text'}, status=400)

            result = check_standard(standard_text, document_text)
            if isinstance(result, str):
                result = json.loads(result)
            return JsonResponse(result, safe=False)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Only GET method is allowed'}, status=405)
