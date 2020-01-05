from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import authenticate
from djsonrest import rest, exceptions
from ..models import Consumer, user_create_token
from .. import app_settings, auth


class Auth(rest.RESTRouteGroup):
    @rest.route('/auth/consumer', method='POST', version=rest.RESTVersion(0.0, match=rest.RESTVersionMatch.FOLLOWING_MAJOR_MINOR))
    def auth_consumer_post(self, request, *args, **kwargs):
        if not request.JSON.get('uid') or not request.JSON.get('key'):
            raise exceptions.RequestError

        try:
            consumer = Consumer.objects.get(uid=request.JSON.get('uid'))
        except ObjectDoesNotExist as error:
            raise exceptions.AuthenticationError from error

        if not consumer.check_key(request.JSON.get('key')):
            raise exceptions.AuthenticationError

        token = consumer.create_token()
        jwt_token = token.as_jwt()
        return {
            "token": jwt_token[0],
            "subject": jwt_token[1],
        }

    @rest.route('/auth/consumer', method='GET', version=rest.RESTVersion(0.0, match=rest.RESTVersionMatch.FOLLOWING_MAJOR_MINOR), auth=auth.Consumer)
    def auth_consumer_get(self, request, *args, **kwargs):
        return {
            "consumer": request.rest_consumer.uid,
            "user": str(request.user),
        }

    @rest.route('/auth/user', method='POST', version=rest.RESTVersion(0.0, match=rest.RESTVersionMatch.FOLLOWING_MAJOR_MINOR), auth=auth.Consumer)
    def auth_user_post(self, request):
        if not request.JSON.get('username') or not request.JSON.get('password'):
            raise exceptions.RequestError

        user = authenticate(username=request.JSON.get('username'), password=request.JSON.get('password'))
        if not user:
            raise exceptions.AuthenticationError

        data = {}

        if request.JSON.get('issue_weak', True):
            token = user_create_token(user, obtained_by=request.rest_consumer)
            jwt_token = token.as_jwt()

            data['weak'] = {
                "token": jwt_token[0],
                "subject": jwt_token[1],
            }

        if app_settings.USER_LOGIN_ISSUE_WEAK_AND_STRONG_TOKEN:
            strong_token = user_create_token(user, audience='user_strong', obtained_by=request.rest_consumer)
            jwt_strong_token = strong_token.as_jwt()

            data['strong'] = {
                "token": jwt_strong_token[0],
                "subject": jwt_strong_token[1],
            }

        return data

    @rest.route('/auth/user', method='GET', version=rest.RESTVersion(0.0, match=rest.RESTVersionMatch.FOLLOWING_MAJOR_MINOR), auth=auth.User)
    def auth_user_get(self, request):
        return {
            "user": str(request.user),
        }
