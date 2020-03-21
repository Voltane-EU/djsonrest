from . import exceptions


def dict_require_keys(d: dict, required: tuple):
    """
    Require all keys listed in `required` to be included and set with a value in the dict `d`

    :param d: dict: Dictionary to check
    :param required: tuple: List of keys that are required to be set with a value
    """
    for key in required:
        if not d.get(key) or (d.get(key).__class__ == str and not d.get(key).strip()):
            raise exceptions.RequestError

def dict_clean_others(d: dict, use: tuple):
    """
    Use values from `d` when the key exists in `d` and transfer them to a new dict.
    Only keys listed in `use` will be in the new dict which will be returned by this function.
    If a key listed in `use` is not included in `d`, it will be skipped and is not included in the new dict.

    :param d: dict: Dictionary to clean
    :param use: tuple: List of keys that will be transfered to the new dict.
                Alternatively if the key should be changed in the new returned dict,
                a tuple containing ('oldkey', 'newkey') can be passed.

    Example:
    d = {
        'firstkey': 'firstvalue',
        'second': 2,
        'third': None,
        'otherkey': 'hackyvalue',
    }

    dict_clean_others(d, ('firstkey', 'second', 'third', 'otherkey'))
    => {
        'firstkey': 'firstvalue',
        'second': 2,
        'third': None,
    }
    """
    values = {}

    for key in use:
        try:
            if isinstance(key, tuple):
                o_key, v_key = key
            else:
                v_key = o_key = key

            values[v_key] = d[o_key]
        except KeyError:
            pass

    return values

def dict_clean_empty(d: dict, keys_to_keep: tuple = ()):
    """
    Recursively remove keys with empty values from the dict `d`.
    If a parameter evalueates to a boolean False, it will be set to Null.

    :param d: dict: Dictionary to clean
    :param keys_to_keep: tuple: List of keys to keep even when empty
    """
    if isinstance(d, dict):
        return {k: dict_clean_empty(v) for k, v in d.items() if v or k in keys_to_keep}

    if not d:
        return None

    return d

def request_offset_limit(request):
    offset = int(request.GET.get('offset', 0))
    limit = None
    if request.GET.get('limit'):
        limit = offset + int(request.GET.get('limit'))

    return offset, limit
