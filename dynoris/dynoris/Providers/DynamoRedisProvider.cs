using System;
using System.Threading.Tasks;
using Amazon.DynamoDBv2;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using StackExchange.Redis;
using Amazon.DynamoDBv2.Model;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;

namespace dynoris
{
    public class DynamoLinkBag
    {
        public string table;
        public IList<(string, string)> storeKey;
        public DateTime updated;
    }

    public class DynamoRedisProvider : IDynamoRedisProvider
    {
        private readonly ILogger<DynamoRedisProvider> _log;
        private readonly ConnectionMultiplexer _redis;
        private readonly IAmazonDynamoDB _dynamo;

        public DynamoRedisProvider(ILogger<DynamoRedisProvider> log, IConfiguration config, IAmazonDynamoDB dynamo)
        {
            _log = log;
            _redis = ConnectionMultiplexer.Connect(config.GetConnectionString("redis"));
            _dynamo = dynamo;
        }

        public async Task CacheItem(string cacheKey, string table, IList<(string, string)> storeKey)
        {
            var dbRequest = new GetItemRequest
            {
                TableName = table,
                Key = storeKey.ToDictionary(v => v.Item1, v => new AttributeValue(v.Item2))
            };
            var item = await _dynamo.GetItemAsync(dbRequest);

            var value = JsonConvert.SerializeObject(item.Item);

            var bag = new DynamoLinkBag
            {
                table = table,
                storeKey = storeKey,
                updated = DateTime.UtcNow
            };

            var db = _redis.GetDatabase();

            var linkStr = JsonConvert.SerializeObject(bag);

            // update link back record
            await db.HashSetAsync("dyno:link", cacheKey, linkStr);

            // write value
            await db.StringSetAsync(cacheKey, value);
        }

        public async Task CommitItem(string cacheKey)
        {
            var db = _redis.GetDatabase();
            var value = await db.StringGetAsync(cacheKey);
            var item = JsonConvert.DeserializeObject<Dictionary<string, AttributeValue>>(value);

            // read link back record
            var linkStr = await db.HashGetAsync("dyno:link", cacheKey);
            var bag = JsonConvert.DeserializeObject<DynamoLinkBag>(linkStr);

            var dbRequest = new UpdateItemRequest
            {
                TableName = bag.table,
                Key = bag.storeKey.ToDictionary(v => v.Item1, v => new AttributeValue(v.Item2))
            };
            var dbResponse = await _dynamo.UpdateItemAsync(dbRequest);
        }
    }
}