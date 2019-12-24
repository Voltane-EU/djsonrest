from djsonrest import rest


class Test(rest.RESTRouteGroup):
    @rest.route('/test', version=1.0, method='GET')
    def test_v1(self, request, *args, **kwargs):
        return {
            "test": "v1",
        }

    @rest.route('/test', version=1.5, method='GET')
    def test_v1_5(self, request, *args, **kwargs):
        return {
            "test": "v1.5",
        }

    @rest.route('/test', version=2.0, method='GET')
    def test_v2(self, request, *args, **kwargs):
        return {
            "test": "v2",
        }
