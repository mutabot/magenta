using System;
using Xunit;

namespace tests
{
    [Collection("Database collection")]
    public class DynamoRedisProviderTests
    {
        private readonly DatabaseFixture fixture;

        public DynamoRedisProviderTests(DatabaseFixture fixture)
        {
            this.fixture = fixture;
        }

        [Fact]
        public void StringCacheTest()
        {
        }
    }
}
