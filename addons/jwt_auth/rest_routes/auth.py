from djsonrest import rest
from ..models import Consumer
from ..auth import ConsumerAuth


class Auth(rest.RESTRouteGroup):
    @rest.route('/auth/consumer', method='POST', version=rest.RESTVersion(0.0, match=rest.RESTVersionMatch.FOLLOWING_MAJOR_MINOR))
    def auth_consumer_post(self, request, *args, **kwargs):
        return

    @rest.route('/auth/consumer', method='GET', version=rest.RESTVersion(0.0, match=rest.RESTVersionMatch.FOLLOWING_MAJOR_MINOR), auth=ConsumerAuth)
    def auth_consumer_get(self, request, *args, **kwargs):
        return
