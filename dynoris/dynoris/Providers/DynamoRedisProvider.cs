using System;
using System.Threading.Tasks;
using Amazon.DynamoDBv2;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using StackExchange.Redis;
using Amazon.DynamoDBv2.DocumentModel;
using System.Collections.Generic;
using System.Linq;
using Amazon.DynamoDBv2.Model;
using dynoris.Providers;

namespace dynoris
{
    public static class Extensions
    {
        public static double ToDouble(this DateTime instance)
        {
            const long DoubleDateOffset = 599264352000000000;
            const long TicksPerMillisecond = 10000;
            const long MillisPerDay = 86400000;

            var value = instance.ToBinary();

            long millis = (value - DoubleDateOffset) / TicksPerMillisecond;
            if (millis < 0)
            {
                long frac = millis % MillisPerDay;
                if (frac != 0) millis -= (MillisPerDay + frac) * 2;
            }
            return (double)millis / MillisPerDay;
        }
    }

    public class DynamoLinkBag
    {
        public string table;
        public IList<(string, string)> storeKey;
        public DateTime lastRead;
        public DateTime lastWrite;
        public string hashKey;
    }

    public class DynamoRedisProvider : IDynamoRedisProvider
    {
        protected readonly ILogger<DynamoRedisProvider> _log;
        protected readonly ConnectionMultiplexer _redis;
        protected readonly IAmazonDynamoDB _dynamo;

        protected readonly RedisServiceRecordProvider _serviceRecord;

        public DynamoRedisProvider(
            ILogger<DynamoRedisProvider> log,
            IConfiguration config,
            IAmazonDynamoDB dynamo,
            RedisServiceRecordProvider serviceRecordProvider)
        {
            _log = log;
            _redis = ConnectionMultiplexer.Connect(config.GetConnectionString("Redis"));
            _dynamo = dynamo;
            _serviceRecord = serviceRecordProvider;
        }

        public async Task<long> CacheHash(string cacheKey, string table, string indexName, string hashKey, IList<(string, string)> storeKey)
        {
            var conditionExpression = string.Join("AND", storeKey.Select(sk => $"#{sk.Item1} = :{sk.Item1}"));

            var query = new QueryRequest
            {
                IndexName = indexName,
                TableName = table,
                KeyConditionExpression = conditionExpression,
                ExpressionAttributeNames = storeKey.ToDictionary(sk => $"#{sk.Item1}", sk => $"{sk.Item1}"),
                ExpressionAttributeValues = storeKey.ToDictionary(sk => $":{sk.Item1}", sk => new AttributeValue(sk.Item2))
            };
            var count = 0;

            // update service record
            var db = await _serviceRecord.LinkBackOnRead(cacheKey, table, storeKey, hashKey);

            // loop through results
            for (
                var search = await _dynamo.QueryAsync(query);
                search.Count > 0;
                query.ExclusiveStartKey = search.LastEvaluatedKey,
                search = await _dynamo.QueryAsync(query))
            {
                // store items
                var hashValues = search.Items
                    .Select(item => Document.FromAttributeMap(item))
                    .Select(doc => new HashEntry(doc[hashKey].AsString(), doc.ToJson()))
                    .ToArray();

                // write values
                count += hashValues.Length;
                await db.HashSetAsync(cacheKey, hashValues);

                // break if no pagination
                if (search.LastEvaluatedKey.Count == 0)
                {
                    break;
                }
            }

            return count;
        }

        public async Task<long> CommitHash(string cacheKey)
        {
            // read service record
            var db = _redis.GetDatabase();
            var dlb = await _serviceRecord.LinkBackOnWrite(cacheKey);
            var table = dlb.table;
            var count = 0;

            foreach (var item in db.HashScan(cacheKey))
            {
                var doc = Document.FromJson(item.Value);
                var updateMap = doc.ToAttributeUpdateMap(false);
                updateMap.Remove(dlb.hashKey);

                var resp = await _dynamo.UpdateItemAsync(
                    table,
                    new Dictionary<string, AttributeValue>
                    {
                        { dlb.hashKey, new AttributeValue(doc[dlb.hashKey]) }
                    },
                    updateMap
                );

                count += resp.HttpStatusCode == System.Net.HttpStatusCode.OK ? 1 : 0;
            }

            return count;
        }

        public async Task CacheItem(string cacheKey, string table, IList<(string, string)> storeKey)
        {
            var response = await _dynamo.GetItemAsync(table,
                storeKey.ToDictionary(v => v.Item1, v => new AttributeValue(v.Item2)));

            var item = Document.FromAttributeMap(response.Item);

            var value = item.ToJson();

            // update link back record
            var db = await _serviceRecord.LinkBackOnRead(cacheKey, table, storeKey);

            // write value
            await db.StringSetAsync(cacheKey, value);
        }

        public async Task CommitItem(string cacheKey)
        {
            var db = _redis.GetDatabase();
            var value = await db.StringGetAsync(cacheKey);

            // read link back record
            var bag = await _serviceRecord.LinkBackOnWrite(cacheKey);

            //var t = Table.LoadTable(_dynamo, bag.table);
            //var dbResponse = await t.UpdateItemAsync(item, bag.storeKey.ToDictionary(v => v.Item1, v => (DynamoDBEntry)v.Item2));
            var item = Document.FromJson(value);

            // remove index keys as these can not be a part of the update query
            foreach (var key in bag.storeKey)
            {
                item.Remove(key.Item1);
            }

            // update the DB
            var dbResponse = await _dynamo.UpdateItemAsync(
                bag.table,
                bag.storeKey.ToDictionary(v => v.Item1, v => new AttributeValue(v.Item2)),
                item.ToAttributeUpdateMap(true));
        }

        public async Task DeleteItem(string table, IList<(string, string)> storeKey)
        {
            var dbResponse = await _dynamo.DeleteItemAsync(
                table,
                storeKey.ToDictionary(v => v.Item1, v => new AttributeValue(v.Item2)));
        }

        public async Task DeleteItem(string cacheKey)
        {
            var bag = await _serviceRecord.LinkBackOnWrite(cacheKey);
            if (bag != null)
            {
                await DeleteItem(bag.table, bag.storeKey);
            }
        }
    }
}