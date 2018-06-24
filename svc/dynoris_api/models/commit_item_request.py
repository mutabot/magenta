# coding: utf-8

"""
    Dynoris API

    No description provided (generated by Swagger Codegen https://github.com/swagger-api/swagger-codegen)  # noqa: E501

    OpenAPI spec version: v1
    
    Generated by: https://github.com/swagger-api/swagger-codegen.git
"""


import pprint
import re  # noqa: F401

import six

from dynoris_api.models.value_tuple_string_string import ValueTupleStringString  # noqa: F401,E501


class CommitItemRequest(object):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    """
    Attributes:
      swagger_types (dict): The key is attribute name
                            and the value is attribute type.
      attribute_map (dict): The key is attribute name
                            and the value is json key in definition.
    """
    swagger_types = {
        'table': 'str',
        'store_key': 'list[ValueTupleStringString]',
        'item_json': 'str'
    }

    attribute_map = {
        'table': 'table',
        'store_key': 'storeKey',
        'item_json': 'itemJson'
    }

    def __init__(self, table=None, store_key=None, item_json=None):  # noqa: E501
        """CommitItemRequest - a model defined in Swagger"""  # noqa: E501

        self._table = None
        self._store_key = None
        self._item_json = None
        self.discriminator = None

        if table is not None:
            self.table = table
        if store_key is not None:
            self.store_key = store_key
        if item_json is not None:
            self.item_json = item_json

    @property
    def table(self):
        """Gets the table of this CommitItemRequest.  # noqa: E501


        :return: The table of this CommitItemRequest.  # noqa: E501
        :rtype: str
        """
        return self._table

    @table.setter
    def table(self, table):
        """Sets the table of this CommitItemRequest.


        :param table: The table of this CommitItemRequest.  # noqa: E501
        :type: str
        """

        self._table = table

    @property
    def store_key(self):
        """Gets the store_key of this CommitItemRequest.  # noqa: E501


        :return: The store_key of this CommitItemRequest.  # noqa: E501
        :rtype: list[ValueTupleStringString]
        """
        return self._store_key

    @store_key.setter
    def store_key(self, store_key):
        """Sets the store_key of this CommitItemRequest.


        :param store_key: The store_key of this CommitItemRequest.  # noqa: E501
        :type: list[ValueTupleStringString]
        """

        self._store_key = store_key

    @property
    def item_json(self):
        """Gets the item_json of this CommitItemRequest.  # noqa: E501


        :return: The item_json of this CommitItemRequest.  # noqa: E501
        :rtype: str
        """
        return self._item_json

    @item_json.setter
    def item_json(self, item_json):
        """Sets the item_json of this CommitItemRequest.


        :param item_json: The item_json of this CommitItemRequest.  # noqa: E501
        :type: str
        """

        self._item_json = item_json

    def to_dict(self):
        """Returns the model properties as a dict"""
        result = {}

        for attr, _ in six.iteritems(self.swagger_types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            else:
                result[attr] = value

        return result

    def to_str(self):
        """Returns the string representation of the model"""
        return pprint.pformat(self.to_dict())

    def __repr__(self):
        """For `print` and `pprint`"""
        return self.to_str()

    def __eq__(self, other):
        """Returns true if both objects are equal"""
        if not isinstance(other, CommitItemRequest):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other
