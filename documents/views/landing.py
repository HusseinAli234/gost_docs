from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class LandingPageView(LoginRequiredMixin, TemplateView):
    """
    Представление лендинг-страницы, которая показывается после входа пользователя.
    Здесь пользователь может выбрать тип документа (ГОСТ или СТО).
    """
    template_name = 'landing/index.html'
    login_url = '/accounts/login/' 