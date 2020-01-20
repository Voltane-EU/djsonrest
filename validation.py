from . import exceptions


def require_keys_in_dict(keys: tuple, d: dict):
    """
    Require all keys listed in `keys` to be included and set with a value in the dict `d`
    """
    for key in keys:
        if not d.get(key):
            raise exceptions.RequestError
