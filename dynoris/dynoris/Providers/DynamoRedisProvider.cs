﻿using System;
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

    public enum RecordType
    {
        String,
        Hash,
        HashDocument
    }

    public struct DynamoLinkBag
    {
        public RecordType recordType;
        public string table;
        public IList<(string, string)> storeKey;
        public DateTime lastRead;
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
            // update service record
            var exists = await _serviceRecord.LinkBackOnRead(
                cacheKey, 
                new DynamoLinkBag
                {
                    recordType = RecordType.Hash, table = table, storeKey = storeKey, hashKey = hashKey
                }
            );
            var db = _redis.GetDatabase();

            if (exists)
            {
                await _serviceRecord.TouchKey(cacheKey);
                _log.LogInformation($"Read skipped for {cacheKey}");
                return await db.HashLengthAsync(cacheKey);
            }

            // read and cache
            // TODO: RACE CONDITIONS HERE
            // (1) where two actors can read same data, this can be ignored as soon as it does not add too much read overhead
            // (2) competing actor detect a key before it is completely written as the non existent key is created after first dynamo read
            // 
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
            // loop through results
            for (
                var search = await _dynamo.QueryAsync(query);
                search.Count > 0;
                query.ExclusiveStartKey = search.LastEvaluatedKey,
                search = await _dynamo.QueryAsync(query)
            )
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

            await _serviceRecord.TouchKey(cacheKey);
            return count;
        }

        public async Task<long> CacheAsHash(string cacheKey, string table, string hashKey, IList<(string, string)> storeKey)
        {
            var db = _redis.GetDatabase();
            // update link back record
            var exists = await _serviceRecord.LinkBackOnRead(
                cacheKey,
                new DynamoLinkBag
                {
                    recordType = RecordType.HashDocument,
                    table = table,
                    storeKey = storeKey,
                    hashKey = hashKey
                }
            );

            if (exists)
            {
                _log.LogInformation($"Read skipped for {cacheKey}");
                return await db.HashLengthAsync(cacheKey);
            }

            var response = await _dynamo.GetItemAsync(
                table,
                storeKey.ToDictionary(v => v.Item1, v => new AttributeValue(v.Item2))
            );

            var item = Document.FromAttributeMap(response.Item);

            // write values            
            if (item.Contains(hashKey))
            {
                var hashSet = item[hashKey].AsDocument();
                if (hashSet != null && hashSet.Count > 0)
                {
                    var values = hashSet.Select(v => new HashEntry(v.Key, v.Value.ToString())).ToArray();
                    await db.HashSetAsync(cacheKey, values);
                }
            }
            await _serviceRecord.TouchKey(cacheKey);
            return await db.HashLengthAsync(cacheKey);
        }

        public async Task CacheItem(string cacheKey, string table, IList<(string, string)> storeKey)
        {
            // update link back record
            var exists = await _serviceRecord.LinkBackOnRead(cacheKey, new DynamoLinkBag { recordType = RecordType.String, table = table, storeKey = storeKey });

            if (exists)
            {
                await _serviceRecord.TouchKey(cacheKey);
                _log.LogInformation($"Read skipped for {cacheKey}");
                return;
            }

            var db = _redis.GetDatabase();
            var response = await _dynamo.GetItemAsync(
                table,
                storeKey.ToDictionary(v => v.Item1, v => new AttributeValue(v.Item2))
            );

            var item = Document.FromAttributeMap(response.Item);

            var value = item.ToJson();            

            // write value
            await db.StringSetAsync(cacheKey, value);
            await _serviceRecord.TouchKey(cacheKey);
        }

        public async Task<long> CommitItem(string cacheKey)
        {
            var db = _redis.GetDatabase();

            // read link back record
            var dlbRef = await _serviceRecord.LinkBackOnWrite(cacheKey);
            if (dlbRef == null)
            {
                _log.LogInformation($"Commit skipped for {cacheKey}, key expired.");
            }
            else
            {
                var dlb = dlbRef.Value;
                // apply commit based onrecord type
                switch (dlb.recordType)
                {
                    case RecordType.String:
                        await CommitAsString(cacheKey, db, dlb);
                        return 1;
                    case RecordType.Hash:
                        return await CommitAsHash(cacheKey, db, dlb);
                    case RecordType.HashDocument:
                        return await CommitAsHashDocument(cacheKey, db, dlb);
                }
            }
            return 0;
        }

        private async Task<long> CommitAsHashDocument(string cacheKey, IDatabase db, DynamoLinkBag dlb)
        {
            var rootDoc = new Document();

            foreach (var item in db.HashScan(cacheKey))
            {
                rootDoc.Add(item.Name, item.Value.ToString());
            }

            // result doc
            var resultDoc = new Document(new Dictionary<string, DynamoDBEntry> { { dlb.hashKey, rootDoc } });

            // update the DB
            var dbResponse = await _dynamo.UpdateItemAsync(
                dlb.table,
                dlb.storeKey.ToDictionary(v => v.Item1, v => new AttributeValue(v.Item2)),
                resultDoc.ToAttributeUpdateMap(true));

            return await db.HashLengthAsync(cacheKey);
        }

        private async Task<long> CommitAsHash(string cacheKey, IDatabase db, DynamoLinkBag dlb)
        {
            // read service record
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

        private async Task CommitAsString(string cacheKey, IDatabase db, DynamoLinkBag dlb)
        {
            var value = await db.StringGetAsync(cacheKey);
            var item = Document.FromJson(value);

            // remove index keys as these can not be a part of the update query
            foreach (var key in dlb.storeKey)
            {
                item.Remove(key.Item1);
            }

            // update the DB
            var dbResponse = await _dynamo.UpdateItemAsync(
                dlb.table,
                dlb.storeKey.ToDictionary(v => v.Item1, v => new AttributeValue(v.Item2)),
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
            try
            {
                var bag = await _serviceRecord.LinkBackOnWrite(cacheKey);
                await DeleteItem(bag.Value.table, bag.Value.storeKey);
            }
            catch(Exception ex)
            {
                _log.LogError($"Failed to delele: {cacheKey}, ex: {ex.Message}");
            }
        }
    }
}