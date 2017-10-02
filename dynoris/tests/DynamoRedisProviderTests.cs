using dynoris;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json.Linq;
using System.Collections.Generic;
using Xunit;
using Microsoft.Extensions.Configuration;
using dynoris.Providers;
using System;
using StackExchange.Redis;

namespace tests
{
    [Collection("Database collection")]
    public partial class DynamoRedisProviderTests : IDisposable
    {
        private readonly DatabaseFixture _fixture;
        private readonly string _gid;
        private readonly string _cacheKey;
        private readonly IDynamoRedisProvider _dynoris;
        private readonly IDatabase _db;

        public DynamoRedisProviderTests(DatabaseFixture fixture)
        {
            _fixture = fixture;
            _gid = "123456789009876543210";
            _cacheKey = $"{_gid}:test";

            _dynoris = _fixture._provider.GetRequiredService<IDynamoRedisProvider>();
            _db = _fixture._redis.GetDatabase();

            _db.KeyDelete(_cacheKey);
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

        [Fact(Skip = "Magenta Specific")]
        public void HashCacheTest()
        {
            var cachedCount = _dynoris.CacheHash(_cacheKey, "GidSet", "PollIndex", "gid", new List<(string, string)> { ("active", "true") }).Result;
            var readCount = _db.HashLength(_cacheKey);

            Assert.True(cachedCount > 0);
            Assert.True(cachedCount == readCount);

            var writeCount = _dynoris.CommitItem(_cacheKey).Result;

            Assert.True(writeCount == readCount);
        }

        [Fact(Skip = "Magenta Specific")]
        public void HashDocumentCacheTest()
        {
            var cachedCount = _dynoris.CacheAsHash(_cacheKey, "GidLog", "rows", new List<(string, string)> { ("gid", "115343447980845133514") }).Result;
            var readCount = _db.HashLength(_cacheKey);

            Assert.True(cachedCount == 0);
            Assert.True(cachedCount == readCount);

            for (int i = 0; i < 100; ++i)
            {
                _db.HashSet(_cacheKey, $"Entry_{i}", $"{{ \"value\": {i}}}");
            }

            var writeCount = _dynoris.CommitItem(_cacheKey).Result;

            Assert.True(writeCount == 100);
        }

        [Fact]
        public void StringCacheTest()
        {
            _dynoris.CacheItem(_cacheKey, DatabaseFixture.TestTableName, new List<(string, string)> { ("gid", _gid) }).Wait();

            var item = _db.StringGet(_cacheKey).ToString();

            var objNull = JObject.Parse(item);

            Assert.False(objNull.HasValues);

            // add data
            var obj = JObject.FromObject(new Dictionary<string, string> { { "active", "false" } });
            item = obj.ToString();
            _db.StringSet(_cacheKey, item);

            // write to dynamo
            _dynoris.CommitItem(_cacheKey).Wait();

            // clean redis
            _db.KeyDelete(_cacheKey);
            item = _db.StringGet(_cacheKey);
            Assert.True(string.IsNullOrEmpty(item));

            // read back from dynamo
            _dynoris.CacheItem(_cacheKey, DatabaseFixture.TestTableName, new List<(string, string)> { ("gid", _gid) }).Wait();

            item = _db.StringGet(_cacheKey);

            Assert.False(string.IsNullOrEmpty(item));

            obj = JObject.Parse(item);
            Assert.False(obj["active"].Value<bool>());

            // cleanup
            _dynoris.DeleteItem(_cacheKey).Wait();
        }

        public void Dispose()
        {
           // _fixture.Dispose();
        }
    }
}
