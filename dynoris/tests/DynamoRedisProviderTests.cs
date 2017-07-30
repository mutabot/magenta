using dynoris;
using Microsoft.Extensions.DependencyInjection;
using System;
using System.Collections.Generic;
using Xunit;

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

        [Fact]
        public void StringCacheTest()
        {
            var dynoris = _fixture._provider.GetRequiredService<IDynamoRedisProvider>();

            dynoris.CacheItem("115343447980845133514", "GidSet", new List<(string, string)> { ("115343447980845133514", null) }).Wait();

            dynoris.CommitItem("115343447980845133514").Wait();
        }
    }
}
