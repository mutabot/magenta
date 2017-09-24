using Amazon;
using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;
using System.Collections.Generic;
using System.Linq;
using System;

namespace dynoris.Providers
{
    public class BaseDynamoProvider
    {
        protected readonly IAmazonDynamoDB _dynamo;

        public static string TableName(string name)
        {
            return $"{AWSConfigsDynamoDB.Context.TableNamePrefix}{name}";
        }

        public BaseDynamoProvider(IAmazonDynamoDB dynamo)
        {
            _dynamo = dynamo;
        }

        protected static Dictionary<string, string> GetExpressionAttributeNames(IEnumerable<(string key, string value)> storeKey)
        {
            return storeKey.ToDictionary(sk => $"#{sk.key}", sk => $"{sk.key}");
        }

        protected static Dictionary<string, AttributeValue> GetExpressionAttributeValues(IEnumerable<(string key, string value)> storeKey)
        {
            return storeKey.ToDictionary(sk => $":{sk.key}", sk => ParseAttributeValue(sk.value));
        }

        private static AttributeValue ParseAttributeValue(string value)
        {
            var result = new AttributeValue();
            if (bool.TryParse(value, out bool boolValue))
            {
                result.BOOL = boolValue;
            }
            else if (decimal.TryParse(value, out decimal nValue))
            {
                result.N = nValue.ToString();
            }
            else
            {
                result.S = value;
            }
            return result;
        }

        protected static string GetConditionExpression(IEnumerable<(string key, string value)> storeKey, string sign = "=")
        {
            return string.Join("AND", storeKey.Select(sk => $"#{sk.key} {sign} :{sk.key}"));
        }

        protected string GetConditionExpression((string key, string value) stampKey, string sign = "=")
        {
            return $"#{stampKey.key} {sign} :{stampKey.key}";
        }

    }
}
