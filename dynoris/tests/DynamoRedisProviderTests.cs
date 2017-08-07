using Amazon.DynamoDBv2;
using dynoris;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Moq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using System;
using System.Collections.Generic;
using Xunit;
using Microsoft.Extensions.Configuration;
using System.Threading;
using StackExchange.Redis;
using dynoris.Providers;

namespace tests
{
    [Collection("Database collection")]
    public class DynamoRedisProviderTests
    {
        private readonly DatabaseFixture _fixture;

        public DynamoRedisProviderTests(DatabaseFixture fixture)
        {
            _fixture = fixture;
        }

        class RedisServiceRecordProviderTester : RedisServiceRecordProvider
        {
            public RedisServiceRecordProviderTester(ILogger<RedisServiceRecordProvider> log, IConfiguration config) : base(log, config)
            {
                // clean any test remains
                var db = _redis.GetDatabase();
                db.KeyDelete(new RedisKey[] { _serviceKeySet, _serviceKeyHash });
            }

            public bool TestLinkBack()
            {
                ExpireTimeSpan = TimeSpan.FromSeconds(5);

                // create 2000 records
                for (int i = 0; i < 2000; i++)
                {
                    LinkBackOnRead($"TestRecord_{i}", "TestTable", new List<(string, string)>()).Wait();
                }

                // "commit" 1800 records
                for (int i = 0; i < 1800; i++)
                {
                    LinkBackOnWrite($"TestRecord_{i}").Wait();
                }

                Thread.Sleep(TimeSpan.FromSeconds(7));

                // check for records
                var db = LinkBackOnRead($"TestRecord_All", "TestTable", new List<(string, string)>()).Result;
                LinkBackOnWrite($"TestRecord_All").Wait();

                var remainSet = db.SortedSetRangeByRank(_serviceKeySet);
                var remainHash = db.HashGetAll(_serviceKeyHash);

                Assert.True(remainSet.Length == 201);
                Assert.True(remainHash.Length == 201);

                // expire 100 out of 200 remaining
                for (int i = 1800; i < 1900; i++)
                {
                    LinkBackOnWrite($"TestRecord_{i}").Wait();
                }

                Thread.Sleep(TimeSpan.FromSeconds(5));

                for (int i = 1900; i < 2000; i++)
                {
                    LinkBackOnWrite($"TestRecord_{i}").Wait();
                }

                remainSet = db.SortedSetRangeByRank(_serviceKeySet);
                remainHash = db.HashGetAll(_serviceKeyHash);

                Assert.True(remainSet.Length == 100);
                Assert.True(remainHash.Length == 100);

                // expire the remaning 100
                Thread.Sleep(TimeSpan.FromSeconds(5));
                LinkBackOnWrite($"TestRecord_All").Wait();

                remainSet = db.SortedSetRangeByRank(_serviceKeySet);
                remainHash = db.HashGetAll(_serviceKeyHash);

                Assert.True(remainSet.Length == 0);
                Assert.True(remainHash.Length == 0);

                return true;
            }
        }

        [Fact]
        public void ServiceRecordTest()
        {
            var tester = new RedisServiceRecordProviderTester(
                _fixture._provider.GetService<ILogger<RedisServiceRecordProvider>>(),
                _fixture._provider.GetRequiredService<IConfiguration>()
                );

            Assert.True(tester.TestLinkBack());

        }

        [Fact]
        public void HashCacheTest()
        {
            var dynoris = _fixture._provider.GetRequiredService<IDynamoRedisProvider>();

            dynoris.CacheHash("Hash", "GidSet", "PollIndex", "gid", new List<(string, string)> { ("active", "true") }).Wait();
        }

        [Fact]
        public void StringCacheTest()
        {
            var gid = "115343447980845133514";
            var dynoris = _fixture._provider.GetRequiredService<IDynamoRedisProvider>();

            dynoris.CacheItem(gid, "GidSet", new List<(string, string)> { ("gid", gid) }).Wait();

            var db = _fixture._redis.GetDatabase();
            var item = db.StringGet(gid).ToString();

            Assert.False(string.IsNullOrEmpty(item));

            var obj = JObject.Parse(item);
            obj["active"] = "false";
            item = obj.ToString();
            db.StringSet(gid, item);

            dynoris.CommitItem(gid).Wait();

            db.KeyDelete(gid);

            item = db.StringGet(gid);
            Assert.True(string.IsNullOrEmpty(item));

            dynoris.CacheItem(gid, "GidSet", new List<(string, string)> { ("gid", gid) }).Wait();

            item = db.StringGet(gid);

            Assert.False(string.IsNullOrEmpty(item));

            obj = JObject.Parse(item);
            Assert.False(obj["active"].Value<bool>());
        }
    }
}
