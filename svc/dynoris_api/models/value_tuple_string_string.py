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


class ValueTupleStringString(object):
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
        'item1': 'str',
        'item2': 'str'
    }

    attribute_map = {
        'item1': 'item1',
        'item2': 'item2'
    }

    def __init__(self, item1=None, item2=None):  # noqa: E501
        """ValueTupleStringString - a model defined in Swagger"""  # noqa: E501

        self._item1 = None
        self._item2 = None
        self.discriminator = None

        if item1 is not None:
            self.item1 = item1
        if item2 is not None:
            self.item2 = item2

    @property
    def item1(self):
        """Gets the item1 of this ValueTupleStringString.  # noqa: E501


        :return: The item1 of this ValueTupleStringString.  # noqa: E501
        :rtype: str
        """
        return self._item1

    @item1.setter
    def item1(self, item1):
        """Sets the item1 of this ValueTupleStringString.


        :param item1: The item1 of this ValueTupleStringString.  # noqa: E501
        :type: str
        """

        self._item1 = item1

    @property
    def item2(self):
        """Gets the item2 of this ValueTupleStringString.  # noqa: E501


        :return: The item2 of this ValueTupleStringString.  # noqa: E501
        :rtype: str
        """
        return self._item2

    @item2.setter
    def item2(self, item2):
        """Sets the item2 of this ValueTupleStringString.


        :param item2: The item2 of this ValueTupleStringString.  # noqa: E501
        :type: str
        """

        self._item2 = item2

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
        if not isinstance(other, ValueTupleStringString):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other