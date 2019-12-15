from django.urls import path
from django.http import HttpResponseBadRequest
from .rest import rest_routes
from . import views # pylint: disable=unused-import  # the routes are automatically registered


urlpatterns = [
    route.as_path() for route in rest_routes.values()
]
urlpatterns += [
    path("<path>", lambda _r, path: HttpResponseBadRequest()),
]
