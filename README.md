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
### Add to your django project
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

### Define your routes
Define your own rest route using the route decorator `@rest.route(...)`.
All rest routes have to be defined in a module inside your app/project called `rest_routes`.
This module will be automatically loaded on django initialization and so the routes are being registered.

```python
from djsonrest import rest


class Users(rest.RESTRouteGroup):
    @rest.route('/users', version=1.0, method='GET')
    def users_get(self, request):
        return [...] # Return any json-encodable object
```

Using routes defined as classmethods, you can override them in inherited classes. This way you can provide extendable routes.
To override the existing route, keep the route decorator the same. Change the route decorator if you want to add a second route.
```python
class MyUsers(Users):
    @rest.route('/users', version=1.0, method='GET')
    def users_get(self, request):
        result = super().users_get(request)
        result.append([...])
        return result


class MyUsersV2(Users):
    @rest.route('/users', version=2.0, method='GET')
    def users_get(self, request):
        result = super().users_get(request)
        return {"users": result}
```

### Routes with authentication
The route decorator provides an `auth` argument to which an auth class (a subclass of `djsonrest.auth.Authentication`) can be passed.
The given auth class will be used to authenticate the request before its main processing.

There are the following authentication classes already given:
- `djsonrest.auth.Public` (default)
  Public route, no authentication will be performed
- `djsonrest.addons.jwt_auth.auth.AbstractJWTAuth` (abstract base class for JWT authentication)
  Expects a JWT token in the `Authentication` HTTP-Header with the type `Bearer`
- `djsonrest.addons.jwt_auth.auth.Consumer` (jwt_auth addon, extends `djsonrest.addons.jwt_auth.auth.AbstractJWTAuth`)
  Expects a JWT token with the audience `consumer`. The request user will be the user that is defined in the consumer record
- `djsonrest.addons.jwt_auth.auth.User` (jwt_auth addon, extends `djsonrest.addons.jwt_auth.auth.AbstractJWTAuth`)
  Base of `UserStrong` and `UserWeak` auth. Expects a JWT token with an audience `user_strong` or `user_weak`
  Tokens with the audience `user_strong` are only valid for 1 hour (default, can be canged in your settings), so you
  can use those tokens for high risk endpoints which should be only available short time after the initial authentication
  against the api
  Tokens with the audience `user_weak` are valid for 30 days (default, can be changed in your settings), so those tokens
  can be used for general interaction of a user with the api
- `djsonrest.addons.jwt_auth.auth.UserStrong` (jwt_auth addon, extends `djsonrest.addons.jwt_auth.auth.AbstractJWTAuth`)
  Like `User` auth, but only accepts tokens with the audience `user_strong`
- `djsonrest.addons.jwt_auth.auth.UserWeak` (jwt_auth addon, extends `djsonrest.addons.jwt_auth.auth.AbstractJWTAuth`)
  Like `User` auth, but only accepts tokens with the audience `user_weak`

```python
from djsonrest import rest
from djsonrest.addons.jwt_auth import auth


class Users(rest.RESTRouteGroup):
    @rest.route('/users', version=1.0, method='GET', auth=auth.UserWeak)
    def users_get(self, request):
        return [...]

    @rest.route('/users/<int:id>', version=1.0, method='PATCH', auth=auth.UserStrong)
    def user_edit(self, request, id):
        # high risk action, protected by a short life token
        ...
```

#### Multiple authentication methods
If multiple authentication methods should be available, they can be combined to a `HybridAuth` using the `|`-Operator.
Using a `HybridAuth` with the `|`-Operator, all of the combined authentication methods are tried after each other.
This way, multiple available methods can be defined for a single route.

```python
from djsonrest import rest, auth
from djsonrest.addons.jwt_auth import auth as jwt_auth


class Users(rest.RESTRouteGroup):
    @rest.route('/users', version=1.0, method='GET', auth=jwt_auth.UserWeak | auth.Public)
    def users_get(self, request):
        return [...]
```

#### Configure JWT Signing
To use the jwt_auth addon, some settings have to be set and files created.

Create private and public key files:
```bash
openssl ecparam -genkey -name secp521r1 -noout -out private.pem
openssl ec -in private.pem -pubout -out public.pem
```

Set the path to those files in your `settings.py`:
```python
JWT_PRIVATE_KEY_FILE = os.path.join(BASE_DIR, 'keys', 'private.pem')
JWT_PUBLIC_KEY_FILE = os.path.join(BASE_DIR, 'keys', 'public.pem')
```

### Remove an existing route
This is intended to be used for unwanted routes a other app registers

It is recommended that this is implemented in the `__init__.py` of the `rest_routes` module (or at the beginning if its just a file).
It is possible to remove all routes with a given `path` (always required) or filter it by adding the version and method of the route to remove.
```python
from djsonrest import rest

rest.remove('/unwanted/anything')
rest.remove('/unwanted/route_at_version', version=1.0)
rest.remove('/unwanted/method_route_at_version', version=1.0, method='GET')
```

## License
GNU GPLv3, see LICENSE

## Maintainer
This package is maintained by Manuel Stingl.
For more information see https://opensource.voltane.eu
