from django.urls import path
from django.http import HttpResponseBadRequest
from .rest import rest_routes


urlpatterns = [
    route.as_view() for route in rest_routes.values()
]
urlpatterns += [
    path("<path>", lambda _r, path: HttpResponseBadRequest()),
]
