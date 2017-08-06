﻿using System;
using System.Threading.Tasks;
using Amazon.DynamoDBv2;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using StackExchange.Redis;
using Amazon.DynamoDBv2.DocumentModel;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using Amazon.DynamoDBv2.Model;

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
    }

    public class DynamoRedisProvider : IDynamoRedisProvider
    {
        protected readonly ILogger<DynamoRedisProvider> _log;
        protected readonly ConnectionMultiplexer _redis;
        protected readonly IAmazonDynamoDB _dynamo;

        protected string _serviceKeySet = "dyno_bag:set";
        protected string _serviceKeyHash = "dyno_bag:hash";

        public TimeSpan ExpireTimeSpan { get; set; } = TimeSpan.FromMinutes(1); // default 1 minute

        public DynamoRedisProvider(ILogger<DynamoRedisProvider> log, IConfiguration config, IAmazonDynamoDB dynamo)
        {
            _log = log;
            _redis = ConnectionMultiplexer.Connect(config.GetConnectionString("Redis"));
            // var credentials = Amazon.Runtime.CredentialManagement.AWSCredentialsFactory
            _dynamo = dynamo; // new AmazonDynamoDBClient(dynamo.Config, RegionEndpoint.USEast1);
        }

        public async Task CacheHash(string cacheKey, string table, string indexName, string hashKey, IList<(string, string)> storeKey)
        {
            var t = Table.LoadTable(_dynamo, table);

            var query = new QueryRequest
            {
                IndexName = indexName,
                TableName = table,
                ExpressionAttributeNames = storeKey.ToDictionary(sk => sk.Item1, sk => $":{sk.Item1}"),
                ExpressionAttributeValues = storeKey.ToDictionary(sk => $":{sk.Item1}", sk => new AttributeValue(sk.Item2))
            };

            // var search = await _dynamo.QueryAsync(query);

            var queryFilter = new QueryFilter(storeKey.First().Item1, QueryOperator.Equal, storeKey.First().Item2);
            foreach (var key in storeKey)
            {
                queryFilter.AddCondition(key.Item1, new Amazon.DynamoDBv2.Model.Condition
                {
                    ComparisonOperator = ComparisonOperator.EQ,
                    AttributeValueList = new List<AttributeValue> { new AttributeValue(key.Item2) }
                });
            }

            var search = t.Query(new QueryOperationConfig {
                IndexName = indexName,
                Filter = queryFilter
            });

            // update redis
            var db = await LinkBackOnRead(cacheKey, table, storeKey);
            for (var batch = await search.GetNextSetAsync(); batch != null && batch.Count > 0; batch = await search.GetNextSetAsync())
            {
                var hashValues = batch.Select(b => new HashEntry(b[hashKey].AsString(), b.ToJson())).ToArray();
                // write values
                await db.HashSetAsync(cacheKey, hashValues);
            }
        }

        public Task CommitHash(string key)
        {
            throw new NotImplementedException();
        }

        protected async Task<IDatabase> LinkBackOnRead(string cacheKey, string table, IList<(string, string)> storeKey)
        {
            var bag = new DynamoLinkBag
            {
                table = table,
                storeKey = storeKey,
                lastRead = DateTime.UtcNow
            };

            var db = _redis.GetDatabase();

            var linkStr = JsonConvert.SerializeObject(bag);

            // update link back record, set score to infinity to avoid deletion
            var ssVal = new SortedSetEntry(cacheKey, double.MaxValue);
            await db.SortedSetAddAsync(_serviceKeySet, new SortedSetEntry[] { ssVal });
            await db.HashSetAsync(_serviceKeyHash, cacheKey, linkStr);

            return db;
        }

        protected async Task<DynamoLinkBag> LinkBackOnWrite(string cacheKey)
        {
            var now = DateTime.UtcNow;
            var db = _redis.GetDatabase();

            // purge old records first
            await PurgeServicerecords(db, now);

            // read service record
            var linkStr = await db.HashGetAsync(_serviceKeyHash, cacheKey);
            if (linkStr.HasValue)
            {
                var bag = JsonConvert.DeserializeObject<DynamoLinkBag>(linkStr);

                // update link back record
                bag.lastWrite = now;
                linkStr = JsonConvert.SerializeObject(bag);

                // store the service records
                var nowD = now.ToDouble();
                await db.SortedSetAddAsync(_serviceKeySet, cacheKey, nowD);
                await db.HashSetAsync(_serviceKeyHash, cacheKey, linkStr);

                // set item to expire in 1 minute
                await db.KeyExpireAsync(cacheKey, TimeSpan.FromMinutes(1));
                return bag;
            }

            return null;
        }

        protected async Task PurgeServicerecords(IDatabase db, DateTime now)
        {
            // purge old records
            var cutoffD = (now - ExpireTimeSpan).ToDouble();

            while (true)
            {
                var toPurge = await db.SortedSetRangeByScoreAsync(
                    _serviceKeySet,
                    0,
                    cutoffD,
                    Exclude.None,
                    Order.Ascending,
                    0,
                    64);

                if (toPurge.Length == 0)
                {
                    break;
                }
                var removedSet = await db.SortedSetRemoveAsync(_serviceKeySet, toPurge);
                var removedHash = await db.HashDeleteAsync(_serviceKeyHash, toPurge);
            }
        }

        public async Task CacheItem(string cacheKey, string table, IList<(string, string)> storeKey)
        {
            var response = await _dynamo.GetItemAsync(table,
                storeKey.ToDictionary(v => v.Item1, v => new AttributeValue(v.Item2)));

            var item = Document.FromAttributeMap(response.Item);

            var value = item.ToJson();

            // update link back record
            var db = await LinkBackOnRead(cacheKey, table, storeKey);

            // write value
            await db.StringSetAsync(cacheKey, value);
        }

        public async Task CommitItem(string cacheKey)
        {
            var db = _redis.GetDatabase();
            var value = await db.StringGetAsync(cacheKey);

            // read link back record
            var bag = await LinkBackOnWrite(cacheKey);

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
            var bag = await LinkBackOnWrite(cacheKey);
            if (bag != null)
            {
                await DeleteItem(bag.table, bag.storeKey);
            }
        }
    }
}