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


class CacheItemRequest(object):
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
        'cache_key': 'str',
        'table': 'str',
        'store_key': 'list[ValueTupleStringString]',
        'index_name': 'str',
        'hash_key': 'str'
    }

    attribute_map = {
        'cache_key': 'cacheKey',
        'table': 'table',
        'store_key': 'storeKey',
        'index_name': 'indexName',
        'hash_key': 'hashKey'
    }

    def __init__(self, cache_key=None, table=None, store_key=None, index_name=None, hash_key=None):  # noqa: E501
        """CacheItemRequest - a model defined in Swagger"""  # noqa: E501

        self._cache_key = None
        self._table = None
        self._store_key = None
        self._index_name = None
        self._hash_key = None
        self.discriminator = None

        if cache_key is not None:
            self.cache_key = cache_key
        if table is not None:
            self.table = table
        if store_key is not None:
            self.store_key = store_key
        if index_name is not None:
            self.index_name = index_name
        if hash_key is not None:
            self.hash_key = hash_key

    @property
    def cache_key(self):
        """Gets the cache_key of this CacheItemRequest.  # noqa: E501


        :return: The cache_key of this CacheItemRequest.  # noqa: E501
        :rtype: str
        """
        return self._cache_key

    @cache_key.setter
    def cache_key(self, cache_key):
        """Sets the cache_key of this CacheItemRequest.


        :param cache_key: The cache_key of this CacheItemRequest.  # noqa: E501
        :type: str
        """

        self._cache_key = cache_key

    @property
    def table(self):
        """Gets the table of this CacheItemRequest.  # noqa: E501


        :return: The table of this CacheItemRequest.  # noqa: E501
        :rtype: str
        """
        return self._table

    @table.setter
    def table(self, table):
        """Sets the table of this CacheItemRequest.


        :param table: The table of this CacheItemRequest.  # noqa: E501
        :type: str
        """

        self._table = table

    @property
    def store_key(self):
        """Gets the store_key of this CacheItemRequest.  # noqa: E501


        :return: The store_key of this CacheItemRequest.  # noqa: E501
        :rtype: list[ValueTupleStringString]
        """
        return self._store_key

    @store_key.setter
    def store_key(self, store_key):
        """Sets the store_key of this CacheItemRequest.


        :param store_key: The store_key of this CacheItemRequest.  # noqa: E501
        :type: list[ValueTupleStringString]
        """

        self._store_key = store_key

    @property
    def index_name(self):
        """Gets the index_name of this CacheItemRequest.  # noqa: E501


        :return: The index_name of this CacheItemRequest.  # noqa: E501
        :rtype: str
        """
        return self._index_name

    @index_name.setter
    def index_name(self, index_name):
        """Sets the index_name of this CacheItemRequest.


        :param index_name: The index_name of this CacheItemRequest.  # noqa: E501
        :type: str
        """

        self._index_name = index_name

    @property
    def hash_key(self):
        """Gets the hash_key of this CacheItemRequest.  # noqa: E501


        :return: The hash_key of this CacheItemRequest.  # noqa: E501
        :rtype: str
        """
        return self._hash_key

    @hash_key.setter
    def hash_key(self, hash_key):
        """Sets the hash_key of this CacheItemRequest.


        :param hash_key: The hash_key of this CacheItemRequest.  # noqa: E501
        :type: str
        """

        self._hash_key = hash_key

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
        if not isinstance(other, CacheItemRequest):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other
