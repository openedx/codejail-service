"""
URL routing for the v0 API.
"""

from django.urls import path

from . import views

app_name = 'v0'
urlpatterns = [
    path('code-exec', views.code_exec),
]
