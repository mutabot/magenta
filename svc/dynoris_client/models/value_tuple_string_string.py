# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class ValueTupleStringString(Model):
    """ValueTupleStringString.

    :param item1:
    :type item1: str
    :param item2:
    :type item2: str
    """

    _attribute_map = {
        'item1': {'key': 'item1', 'type': 'str'},
        'item2': {'key': 'item2', 'type': 'str'},
    }

    def __init__(self, item1=None, item2=None):
        self.item1 = item1
        self.item2 = item2
