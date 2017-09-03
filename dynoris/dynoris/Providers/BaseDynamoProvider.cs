using Amazon;
using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.Model;
using System.Collections.Generic;
using System.Linq;

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
            return storeKey.ToDictionary(sk => $":{sk.key}", sk => new AttributeValue(sk.value));
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
