from django.core.exceptions import ObjectDoesNotExist
from djsonrest import rest, exceptions
from ..models import Consumer
from ..auth import ConsumerAuth


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
            raise exceptions.AuthenticationError from error

        token = consumer.create_token()
        jwt_token = token.as_jwt()
        return {
            "token": jwt_token[0],
            "subject": jwt_token[1],
        }

    @rest.route('/auth/consumer', method='GET', version=rest.RESTVersion(0.0, match=rest.RESTVersionMatch.FOLLOWING_MAJOR_MINOR), auth=ConsumerAuth)
    def auth_consumer_get(self, request, *args, **kwargs):
        return {
            "consumer": request.rest_consumer.uid,
            "user": str(request.user),
        }
