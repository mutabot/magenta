using dynoris;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json.Linq;
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
                    LinkBackOnRead($"TestRecord_{i}", new DynamoLinkBag { table = "TestTable", storeKey = new List<(string, string)>() }).Wait();
                }

                // "commit" 1800 records
                for (int i = 0; i < 1800; i++)
                {
                    LinkBackOnWrite($"TestRecord_{i}").Wait();
                }

                Thread.Sleep(TimeSpan.FromSeconds(7));

                // check for records
                var db = _redis.GetDatabase();
                LinkBackOnRead($"TestRecord_All", new DynamoLinkBag { table = "TestTable", storeKey = new List<(string, string)>() }).Wait();
                LinkBackOnRead($"TestRecord_All", new DynamoLinkBag { table = "TestTable", storeKey = new List<(string, string)>() }).Wait();
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

                Assert.True(remainSet.Length == 101);
                Assert.True(remainHash.Length == 101);

                // expire the remaning 100
                Thread.Sleep(TimeSpan.FromSeconds(5));
                LinkBackOnWrite($"TestRecord_All").Wait();

                remainSet = db.SortedSetRangeByRank(_serviceKeySet);
                remainHash = db.HashGetAll(_serviceKeyHash);

                Assert.True(remainSet.Length == 1);
                Assert.True(remainHash.Length == 1);

                return true;
            }

            public void TestRaceLink()
            {
                ExpireTimeSpan = TimeSpan.FromSeconds(1);
                var counterIn = new ConcurrentBag<long>();
                var counterOut = new ConcurrentBag<long>();

                var db = _redis.GetDatabase();
                db.StringSet("TestRecord_Race", "Test Value");
                // seed
                for (int i = 0; i < 8; ++i)
                {
                    var refSeed = LinkBackOnRead($"TestRecord_Race", new DynamoLinkBag { table = "TestTable", storeKey = new List<(string, string)>() }).Result;
                    counterIn.Add(refSeed);
                }

                var run = Parallel.For(
                    0,
                    8,
                    i =>
                    {
                        for (int j = 0; j < 10; ++j)
                        {
                            var r = new Random(DateTime.Now.Millisecond + i);
                            if (r.Next(100) > 50)
                            {
                                var refCount = LinkBackOnRead($"TestRecord_Race", new DynamoLinkBag { table = "TestTable", storeKey = new List<(string, string)>() }).Result;
                                counterIn.Add(refCount);
                            }
                            else
                            {
                                var dlb = LinkBackOnWrite($"TestRecord_Race").Result;
                                counterOut.Add(dlb.refCount);
                            }
                        }
                    });

                Assert.True(run.IsCompleted);

                Assert.True(db.StringGet("TestRecord_Race") == "Test Value");
                Thread.Sleep(TimeSpan.FromSeconds(2));
                Assert.True(db.StringGet("TestRecord_Race") == "Test Value");

                while (true)
                {
                    var dlb2 = LinkBackOnWrite($"TestRecord_Race").Result;
                    if (dlb2.refCount == 0)
                    {
                        break;
                    }
                }

                Thread.Sleep(TimeSpan.FromSeconds(2));
                Assert.False(db.StringGet("TestRecord_Race") == "Test Value");

                Assert.ThrowsAnyAsync<InvalidOperationException>(() => LinkBackOnWrite($"TestRecord_Race")).Wait();

            }
        }

        [Fact]
        public void RaceConditionTest()
        {
            var tester = new RedisServiceRecordProviderTester(
                _fixture._provider.GetService<ILogger<RedisServiceRecordProvider>>(),
                _fixture._provider.GetRequiredService<IConfiguration>()
                );

            tester.TestRaceLink();        
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
            var db = _fixture._redis.GetDatabase();

            var cachedCount = dynoris.CacheHash("GidSetHash", "GidSet", "PollIndex", "gid", new List<(string, string)> { ("active", "true") }).Result;
            var readCount = db.HashLength("GidSetHash");

            Assert.True(cachedCount > 0);
            Assert.True(cachedCount == readCount);

            var writeCount = dynoris.CommitItem("GidSetHash").Result;

            Assert.True(writeCount == readCount);
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

            dynoris.CommitItem(gid).Wait();
        }

        [Fact]
        public void HashDocumentCacheTest()
        {
            var dynoris = _fixture._provider.GetRequiredService<IDynamoRedisProvider>();
            var db = _fixture._redis.GetDatabase();

            var cachedCount = dynoris.CacheAsHash("HashDocument", "GidLog", "rows", new List<(string, string)> { ("gid", "115343447980845133514") }).Result;
            var readCount = db.HashLength("HashDocument");

            Assert.True(cachedCount == 0);
            Assert.True(cachedCount == readCount);

            for (int i = 0; i < 100; ++i)
            {
                db.HashSet("HashDocument", $"Entry_{i}", $"{{ \"value\": {i}}}");
            }

            var writeCount = dynoris.CommitItem("HashDocument").Result;

            Assert.True(writeCount == 100);
        }
    }
}
