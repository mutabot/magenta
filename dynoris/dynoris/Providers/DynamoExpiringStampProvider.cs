using Amazon.DynamoDBv2;
using Amazon.DynamoDBv2.DocumentModel;
using Amazon.DynamoDBv2.Model;
using Microsoft.Extensions.Logging;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace dynoris.Providers
{
    public class DynamoExpiringStampProvider : BaseDynamoProvider, IDynamoExpiringStampProvider
    {
        private readonly ILogger<DynamoRedisProvider> _log;

        public DynamoExpiringStampProvider(ILogger<DynamoRedisProvider> log, IAmazonDynamoDB dynamo)
            : base(dynamo)
        {
            _log = log;
        }

        public async Task<List<string>> Next(
            string table,
            string indexName,
            IList<(string key, string value)> storeKey,
            (string key, string value) stampKey)
        {
            var conditionExpression =
                GetConditionExpression(storeKey) +
                " AND " +
                GetConditionExpression((stampKey.key, stampKey.value.ToString()), "<");

            QueryRequest query = new QueryRequest
            {
                TableName = TableName(table),
                IndexName = indexName,
                Select = Select.ALL_ATTRIBUTES,
                ExpressionAttributeNames = GetExpressionAttributeNames(storeKey.Append(stampKey)),
                ExpressionAttributeValues = GetExpressionAttributeValues(storeKey.Append(stampKey)),
                KeyConditionExpression = conditionExpression
            };

            // collect through results
            var result = new List<string>();
            for (
                var search = await _dynamo.QueryAsync(query);
                search.Count > 0;
                query.ExclusiveStartKey = search.LastEvaluatedKey,
                search = await _dynamo.QueryAsync(query)
            )
            {
                // store items
                var items = search.Items
                    .Select(item => Document.FromAttributeMap(item))
                    .Select(doc => doc.ToJson());

                result.AddRange(items);

                // break if no pagination
                if (search.LastEvaluatedKey.Count == 0)
                {
                    break;
                }
            }

            return result;
        }

        public async Task CommitItem(string table, IList<(string key, string value)> storeKeys, string itemJson)
        {
            var item = Document.FromJson(itemJson);

            // remove index keys as these can not be a part of the update query
            foreach (var key in storeKeys)
            {
                item.Remove(key.key);
            }

            // update the DB
            var uir = new UpdateItemRequest
            {
                TableName = table,
                ExpressionAttributeNames = GetExpressionAttributeNames(storeKeys),
                ExpressionAttributeValues = GetExpressionAttributeValues(storeKeys),
                Key = GetExpressionAttributeValues(storeKeys),
                AttributeUpdates = item.ToAttributeUpdateMap(true),
                ReturnConsumedCapacity = ReturnConsumedCapacity.TOTAL
            };

            var resp = await _dynamo.UpdateItemAsync(uir);
        }

    }
}
