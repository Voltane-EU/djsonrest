from djsonrest import rest


@rest.route('/test', version=1.0, method='GET')
def test(request, *args, **kwargs):
    return {}
