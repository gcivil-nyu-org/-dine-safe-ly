from django.shortcuts import render

# from django.http import HttpResponse
# from django.http import HttpResponseNotFound
# from django.core.serializers.json import DjangoJSONEncoder
# import json
# import logging
# from django.contrib.auth.models import User

# logger = logging.getLogger(__name__)


def get_login_page(request):
    return render(request, "login.html")


def get_register_page(request):
    return render(request, "register.html")