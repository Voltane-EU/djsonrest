from django.urls import path, re_path
from .rest import rest_routes
from . import views # pylint: disable=unused-import  # the routes are automatically registered
from . import app_settings


urlpatterns = [
    route.as_path() for route in rest_routes.values()
]
urlpatterns += [
    re_path(r"^(?P<path>.*)$", app_settings.ROUTE_NOT_FOUND_VIEW),
    path("", app_settings.ROUTE_NOT_FOUND_VIEW),
]
