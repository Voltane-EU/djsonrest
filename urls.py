from django.urls import path
from django.http import HttpResponseBadRequest
from .rest import rest_routes


urlpatterns = [
    route.path() for route in rest_routes
]
urlpatterns += [
    path("<path>", lambda _r, path: HttpResponseBadRequest()),
]
