# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class LogItem(Model):
    """LogItem.

    :param messages:
    :type messages: object
    """

    _attribute_map = {
        'messages': {'key': 'messages', 'type': 'object'},
    }

    def __init__(self, messages=None):
        self.messages = messages
