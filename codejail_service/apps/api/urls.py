"""
Root API URLs.

All API URLs should be versioned, so urlpatterns should only
contain namespaces for the active versions of the API.
"""
from django.urls import include, path

from codejail_service.apps.api.v0 import urls as v0_urls

app_name = 'api'
urlpatterns = [
    path('v0/', include(v0_urls)),
]
