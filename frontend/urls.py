from django.urls import path
from django.utils.translation import activate
from django.http import HttpResponseRedirect
from django.conf.urls.i18n import i18n_patterns
from django.templatetags.static import static
from django.urls import reverse
from .views import main

app_name = "frontend"

urlpatterns = [
    path('', main.home_view, name='home'),
]
