# coding: utf-8
#

import json


def _data_handler(obj):
    return obj.isoformat() if hasattr(obj, "isoformat") else obj


def jsondate_dumps(data):
    assert isinstance(data, dict)
    return json.dumps(data, default=_data_handler)
