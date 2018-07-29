using dynoris;
using Microsoft.Extensions.Logging;
using System;
using System.Collections.Generic;
using Xunit;
using Microsoft.Extensions.Configuration;
using System.Threading;
using StackExchange.Redis;
using dynoris.Providers;
using System.Threading.Tasks;
using System.Collections.Concurrent;

namespace tests
{
    public partial class DynamoRedisProviderTests
    {
        class RedisServiceRecordProviderTester : RedisServiceRecordProvider
        {
            private readonly IDatabase _db;

            public RedisServiceRecordProviderTester(ILogger<RedisServiceRecordProvider> log, IConfiguration config, IRedisConnectionFactory redis) 
                : base(log, config, redis)
            {
                // clean any test remains
                _db = _redis.GetDatabase();
                _db.KeyDelete(new RedisKey[] { _serviceKeySet, _serviceKeyHash });
            }

            public bool TestLinkBack()
            {
                ExpireTimeSpan = TimeSpan.FromSeconds(2);

                // create 2000 records
                for (int i = 0; i < 2000; i++)
                {
                    _db.StringSet($"TestRecord_{i}", $"TestValue_{i}");
                    LinkBackOnRead($"TestRecord_{i}", new DynamoLinkBag { table = "TestTable", storeKey = new List<(string, string)>() }).Wait();
                }

                // "commit" 1800 records
                for (int i = 0; i < 1800; i++)
                {
                    LinkBackOnWrite($"TestRecord_{i}").Wait();
                }

                // wait for all records to expire
                Thread.Sleep(TimeSpan.FromSeconds(8));

                // create a phony record to purge the expired ones
                LinkBackOnRead($"TestRecord_All", new DynamoLinkBag { table = "TestTable", storeKey = new List<(string, string)>() }).Wait();
                LinkBackOnRead($"TestRecord_All", new DynamoLinkBag { table = "TestTable", storeKey = new List<(string, string)>() }).Wait();
                LinkBackOnWrite($"TestRecord_All").Wait();

                var remainSet = _db.SortedSetRangeByRank(_serviceKeySet);
                var remainHash = _db.HashGetAll(_serviceKeyHash);

                Assert.Single(remainSet);
                Assert.Single(remainHash);

                // expire the remaning item
                Thread.Sleep(TimeSpan.FromSeconds(8));
                LinkBackOnWrite($"TestRecord_All").Wait();

                remainSet = _db.SortedSetRangeByRank(_serviceKeySet);
                remainHash = _db.HashGetAll(_serviceKeyHash);

                Assert.Empty(remainSet);
                Assert.Empty(remainHash);

                return true;
            }
        }
    }
}
