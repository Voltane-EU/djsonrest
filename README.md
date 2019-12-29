# djsonREST
djsonREST provides simple powerful features to implement your own REST-API (data encoded as json) within minutes.

The routes are versioned by default.

It also includes an addon for authentication using JWTs using consumers and users.

Base Structure of a rest route url:
`your_path/` + `VersionMajor.Minor` + `/endpoint_url`

## Installation
Use the python package manager pip to install djsonrest.

```bash
pip install djsonrest
```

## Dependencies
`djutils`

## Usage
Add `djsonrest` to your `INSTALLED_APPS`.
```python
INSTALLED_APPS = [
    ...
    'djsonrest',
]
```
If you want to override default routes provided by djsonrest, order this app before your project app.

Add `djsonrest.middleware.RESTRoutesMiddleware` to your `MIDDLEWARE`.
```python
MIDDLEWARE = [
    ...
    'djsonrest.middleware.RESTRoutesMiddleware',
]
```
If you want to customize the exception handling of rest routes override the `RESTRoutesMiddleware` class and
configure your own middleware class instead.

Add a path for the api endpoints to your urls.py's `urlpatterns`.
```python
from djsonrest import rest

urlpatterns = [
    ...
    path('api/', rest.routes.urls),
]
```

Define your own rest route using the route decorator `@rest.route(...)`.
All rest routes have to be defined in a module inside your app/project called `rest_routes`.
Those module will be automatically loaded on django initialization and so the routes are being registered.
```python
from djsonrest import rest


class Users(rest.RESTRouteGroup):
    @rest.route('/users', version=1.0, method='GET')
    def users_get(self, request, *args, **kwargs):
        return [...] # Return any json-encodable object
```

Using routes defined as classmethods, you can override them in inherited classes. This way you can provide extendable routes.
To override the existing route, keep the route decorator the same. Change the route decorator if you want to add a second route.
```python
class MyUsers(Users):
    @rest.route('/users', version=1.0, method='GET')
    def users_get(self, request, *args, **kwargs):
        result = super().users_get(request, *args, **kwargs)
        result.append([...])
        return result


class MyUsersV2(Users):
    @rest.route('/users', version=2.0, method='GET')
    def users_get(self, request, *args, **kwargs):
        result = super().users_get(request, *args, **kwargs)
        return {"users": result}
```

## License
GNU GPLv3, see LICENSE

## Maintainer
This package is maintained by Manuel Stingl.
For more information see https://opensource.voltane.eu
